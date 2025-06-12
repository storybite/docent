import sys
import os

from typing import Optional
from contextlib import AsyncExitStack
import traceback
from fastmcp import Client
import json
import os
from pydantic import BaseModel, Field
import asyncio
import base64

from llm import claude_3_7 as claude
from llm.prompt_templates import slackbot_system_prompt, slackbot_message
from .email_sender import send_success_mail, send_fail_mail

slack_config = {
    "token": os.getenv("slack_bot_token"),
}

slack_config_b64 = base64.b64encode(json.dumps(slack_config).encode()).decode()
weather_config_b64 = base64.b64encode(json.dumps({}).encode()).decode()
smithery_api_key = os.getenv("smithery_api_key")

slack_url = f"https://server.smithery.ai/@smithery-ai/slack/mcp?config={slack_config_b64}&api_key={smithery_api_key}"
weather_url = f"https://server.smithery.ai/@isdaniel/mcp_weather_server/mcp?config={weather_config_b64}&api_key={smithery_api_key}"

config = {}
# Encode config in base64
config_b64 = base64.b64encode(json.dumps(config).encode())


config = {
    "mcpServers": {
        "slack": {"url": slack_url, "transport": "streamable-http"},
        "weather": {"url": weather_url, "transport": "streamable-http"},
    }
}

application_template = """
🏺 프로그램: {program}
📅 방문일자: {visit_date}
⏰ 방문시간: {visit_hours}
👥 방문인원: {visitors}
""".strip()


def modify_input_schema(input_schema):
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


class ReservationAgent:

    def __init__(self):
        self.exit_stack = AsyncExitStack()
        self.tools: list[dict] = []
        self._lock = asyncio.Lock()
        print(config)

    async def connect_server(self, timeout: float = 30.0):
        try:
            self.session = await self.exit_stack.enter_async_context(
                Client(config, timeout=timeout)
            )
            await self.setup_context()
            print("MCP 서버 연결 완료")
        except Exception as e:
            print(f"MCP 서버 연결 실패: {e}")
            traceback.print_exc()
            raise RuntimeError(str(e))

    async def setup_context(self):
        try:
            mcp_tools = await self.session.list_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": modify_input_schema(tool.inputSchema),
                }
                for tool in mcp_tools
            ] + [report_reservation]
            print(f"도구 목록: {[tool['name'] for tool in self.tools]}")

        except Exception as e:
            print(f"도구 Setup 실패: {e}")
            traceback.print_exc()
            raise e

    def _call_llm(self, messages: list[dict]):
        response = claude.create_tool_response(
            messages=messages,
            temperature=0.0,
            max_tokens=1024,
            tools=self.tools,
            tool_system_prompt=slackbot_system_prompt,
        )
        return response

    async def _polling_result(self, tool_name, tool_args, tool_result):
        try:
            for _ in range(1, 10):
                message = json.loads(tool_result[0].text)["messages"]
                if len(message) >= 1:
                    return tool_result
                await asyncio.sleep(1)
                tool_result = await self.session.call_tool(tool_name, tool_args)
            raise ValueError("Too many tries")
        except Exception as e:
            print(f"폴링 중 오류 발생: {e}")
            traceback.print_exc()
            raise e

    async def _delegate_to_slackbot(self, messages: list[dict]):
        response = self._call_llm(messages)
        tries = 0
        while True:
            tool_content = next(
                content for content in response.content if content.type == "tool_use"
            )
            tool_name, tool_args = tool_content.name, tool_content.input
            print("call_tool", tool_name, tool_args)

            if tool_name == "report_reservation":
                return tool_args

            tool_result = await self.session.call_tool(tool_name, tool_args)
            print("tool_result", tool_name, tool_args, tool_result)

            if tool_name == "slack_get_thread_replies":
                tool_result = await self._polling_result(
                    tool_name, tool_args, tool_result
                )

            print(f"tool_result: {tool_result}")
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
            response = self._call_llm(messages)
            if tries > 10:
                raise ValueError("Too many tries")
            tries += 1

    async def _make_reservation(self, application: dict):
        application_without_email = {
            k: v for k, v in application.items() if k != "applicant_email"
        }
        application_form = application_template.format(**application_without_email)
        input_messages = [
            {
                "role": "user",
                "content": slackbot_message.format(application_form=application_form),
            },
        ]

        slackbot_response = await self._delegate_to_slackbot(input_messages)
        receiver = application["applicant_email"]
        if slackbot_response["is_success"]:
            send_success_mail(application_form, receiver, slackbot_response)
        else:
            send_fail_mail(receiver)

    async def make_reservation(self, application: dict):
        async with self._lock:
            await self._make_reservation(application)

    async def cleanup(self):
        try:
            await self.exit_stack.aclose()
            print("MCP 서버 연결 해제")
        except Exception as e:
            print(f"정리 중 오류 발생: {e}")
            traceback.print_exc()
            raise e


async def main():
    agent = ReservationAgent()
    await agent.connect_server()
    await agent.make_reservation(
        {
            "program": "대표 유물 해설",
            "visit_date": "2025-06-09 (월)",
            "visit_hours": "11:00",
            "visitors": 1,
            "applicant_email": "heyjin337@gmail.com",
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
