from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import json
import base64
from anthropic import Anthropic
from dotenv import load_dotenv
import os
from typing import Optional
from pydantic import BaseModel, Field


load_dotenv()

client = Anthropic()

config = {
    "token": os.getenv("slack_bot_token"),
}
# Encode config in base64
config_json = json.dumps(config, separators=(",", ":")).encode()
config_b64 = base64.urlsafe_b64encode(config_json).decode()  # str
smithery_api_key = os.getenv("smithery_api_key")

# Create server URL
url = f"https://server.smithery.ai/@smithery-ai/slack/mcp?config={config_b64}&api_key={smithery_api_key}"

from datetime import timedelta


def request_model(tools: list[str], system_prompt: str, messages: list[dict]):
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=1024,
        temperature=0.0,
        tools=tools,
        tool_choice={"type": "any"},
        system=system_prompt,
        messages=messages,
    )
    print(response.usage.model_dump_json())
    return response


async def make_reservation(
    system: str,
    messages: list[dict],
    tools: list[str] = [],
    session: ClientSession | None = None,
):

    response = request_model(tools, system, messages)

    tool_name, tries = "", 0
    while tool_name != "report_reservation":
        # while True:
        tool_content = next(
            content for content in response.content if content.type == "tool_use"
        )
        tool_name, tool_args = tool_content.name, tool_content.input

        # if tool_name == "report_reservation":
        #     return tool_args

        tool_result = await session.call_tool(tool_name, tool_args)
        print(tool_result)
        messages.extend(
            [
                {"role": "assistant", "content": response.content},
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": tool_content.id,
                            "content": str(tool_result),
                        }
                    ],
                },
            ]
        )
        response = request_model(tools, system_prompt, messages)
        if tries > 10:
            raise ValueError("Too many tries")
        tries += 1

    return tool_args


def filter_input_schema(input_schema):
    if "properties" in input_schema:
        if "required" not in input_schema or not isinstance(
            input_schema["required"], list
        ):
            input_schema["required"] = list(input_schema["properties"].keys())
        else:
            for key in input_schema["properties"].keys():
                if key not in input_schema["required"]:
                    input_schema["required"].append(key)

        for key, value in input_schema["properties"].items():
            if "default" in value:
                del value["default"]

    return input_schema


class Report(BaseModel):
    is_success: bool = Field(description="예약 성공 여부")
    thread_ts: str = Field(description="스레드의 timestamp")
    channel_id: str = Field(description="스레드가 있는 채널의 id")
    docent_name: Optional[str] = Field(description="예약된 경우 도슨트의 이름")
    docent_email: Optional[str] = Field(description="예약된 경우 도슨트의 이메일")


report_reservation = {
    "name": "report_reservation",
    "description": "예약 작업 수행 결과",
    "input_schema": Report.model_json_schema(),
}


system_prompt = """
당신은 슬랙을 통해 박물관 도슨트들과 다음과 같이 소통하여 예약을 도와주는 역할을 합니다. 
1. 관람객의 방문 예정 시각을 도슨트 채널에 공지합니다. 
2. 도슨트들의 응답을 스레드를 통해 확인합니다. 이때 이미 예약처리가 완료된 스레드는 제외합니다.
3. 해설 가능하다고 가장 먼저 응답한 도슨트의 슬랙에서의 real_name과 email을 확인합니다. 응답한 도슨트가 없으면 최종 응답을 합니다.
4. 다음 메시지를 스레드에 댓글로 작성합니다: "@real_name님 해설 잘 부탁드립니다. 이메일로 고객님의 연락처 전달드리겠습니다."
5. 최종 응답은 'report_reservation' 도구를 사용합니다.
""".strip()

from contextlib import AsyncExitStack

exit_stack = AsyncExitStack()


async def main():
    streams = await exit_stack.enter_async_context(streamablehttp_client(url))
    session = await exit_stack.enter_async_context(ClientSession(*streams))
    # ──────────── 몽키 패치 구간 ──────────
    if callable(getattr(session, "_session_read_timeout_seconds", None)):
        # 필요하면 원하는 시간으로 수정 (예: 10초)
        session._session_read_timeout_seconds = timedelta(seconds=10)
    # ───────────────────────────────────────
    await session.initialize()
    session_tools = await session.list_tools()
    print("Tools:", ", ".join(t.name for t in session_tools.tools))
    print("=" * 100)
    tools = [
        {
            "name": tool.name,
            "description": tool.description,
            "input_schema": filter_input_schema(tool.inputSchema),
        }
        for tool in (await session.list_tools()).tools
    ] + [report_reservation]

    input_messages = []

    # chat 함수를 polling 방식으로 외부에서 호출
    polling_complete = False
    while not polling_complete:
        if not input_messages:
            input_messages = [
                {
                    "role": "user",
                    "content": "2025년 5월 29일 오전 10시에 한국인 5명이 문화해설을 요청하셨습니다. 가능한 도슨트님께서는 메시지에 댓글 부탁 드립니다.",
                },
            ]

        response = await make_reservation(
            tools=tools,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=input_messages,
            session=session,
        )
        # print(response)

        # 완료 여부 확인 (여기서 적절한 완료 조건을 설정)
        if response["is_success"]:
            polling_complete = True
            input_messages = []
        else:
            # # 잠시 대기 후 다시 시도
            input_messages.append(
                {
                    "role": "user",
                    "content": "완료 처리되지 않은 예약 건이 있는지 확인하세요.",
                },
            )
            await asyncio.sleep(2)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
