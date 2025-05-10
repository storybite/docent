from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
import json
import base64
from openai import OpenAI

client = OpenAI()

config = {
    "token": "",
}
# Encode config in base64
config_json = json.dumps(config, separators=(",", ":")).encode()
config_b64 = base64.urlsafe_b64encode(config_json).decode()  # str
smithery_api_key = ""

# Create server URL
url = f"https://server.smithery.ai/@smithery-ai/slack/mcp?config={config_b64}&api_key={smithery_api_key}"

from datetime import timedelta


async def chat(
    input_messages: list[dict],
    tools: list[str] = [],
    max_turns: int = 10,
    session: ClientSession | None = None,
):

    # return_messages: list[dict] = []
    chat_messages = input_messages[:]
    for _ in range(max_turns):
        result = client.chat.completions.create(
            model="gpt-4o",
            messages=chat_messages,
            tools=tools,
            response_format={"type": "json_object"},
        )

        if result.choices[0].finish_reason == "tool_calls":
            chat_messages.append(result.choices[0].message)

            for tool_call in result.choices[0].message.tool_calls:
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                if tool_name == "slack_get_thread_replies":
                    print("sleep...")
                    # await asyncio.sleep(10)

                # Get server name for the tool just for logging
                server_name = "slack"

                # Log tool call
                log_message = f"**Tool Call**  \n**Tool Name:** `{tool_name}` from **MCP Server**: `{server_name}`  \n**Input:**  \n```json\n{json.dumps(tool_args, indent=2, ensure_ascii=False)}\n```"
                print(f"Tool Call: {log_message}")

                # Call the tool and log its observation
                result = await session.call_tool(tool_name, tool_args)
                observation = result.content[0].text
                log_message = f"**Tool Observation**  \n**Tool Name:** `{tool_name}` from **MCP Server**: `{server_name}`  \n**Output:**  \n```json\n{json.dumps(observation, indent=2, ensure_ascii=False)}\n```  \n---"
                print(f"Observation: {log_message}")

                chat_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(observation),
                    }
                )
        else:
            return_messages = [
                {"role": "assistant", "content": result.choices[0].message.content}
            ]
            return return_messages

    return_messages = [
        {"role": "assistant", "content": '{"name": "없음", "email": "없음"}'}
    ]
    return return_messages


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

        if "additionalProperties" not in input_schema:
            input_schema["additionalProperties"] = False
    return input_schema


system_prompt = """
당신은 슬랙을 통해 박물관 도슨트들과 다음과 같이 소통하고 예약을 도와주는 역할을 합니다. 
1. 관람객의 방문 예정 시각을 도슨트 채널에 공지합니다. 
2. 도슨트들의 응답을 스레드를 통해 확인합니다. 이때 이미 예약처리가 완료된 스레드는 제외합니다.
3. 해설 가능하다고 가장 먼저 응답한 도슨트의 슬랙에서의 real_name과 email을 확인합니다.
4. 다음 메시지를 스레드에 댓글로 작성합니다: "@real_name님 해설 잘 부탁드립니다. 이메일로 고객님의 연락처 전달드리겠습니다."
5. 최종 응답은 다음 JSON 포맷을 따릅니다: {{"name": <대상자가 없으면 "없음">, "email": <대상자가 없으면 "없음">}}

최종 목표에 도달할 때까지 도구룰 계속 사용하세요.

""".strip()


async def main():
    async with streamablehttp_client(url) as streams:
        async with ClientSession(*streams) as session:
            # ──────────── 몽키 패치 구간 ──────────
            if callable(getattr(session, "_session_read_timeout_seconds", None)):
                # 필요하면 원하는 시간으로 수정 (예: 10초)
                session._session_read_timeout_seconds = timedelta(seconds=10)
            # ───────────────────────────────────────

            await session.initialize()
            tools = await session.list_tools()
            print("Tools:", ", ".join(t.name for t in tools.tools))
            print("=" * 100)
            tools = [
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "strict": True,
                        "parameters": filter_input_schema(tool.inputSchema),
                    },
                }
                for tool in (await session.list_tools()).tools
            ]
            input_messages = [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": "2025년 5월 30일 오전 10시에 한국인 5명이 문화해설을 요청하셨습니다. 가능한 도슨트님께서는 메시지에 댓글 부탁 드립니다.",
                },
                # {
                #     "role": "user",
                #     "content": "처리되지 않은 예약 건이 있는지 확인하세요.",
                # },
            ]

            # chat 함수를 polling 방식으로 외부에서 호출
            return_messages = []
            polling_complete = False

            while not polling_complete:
                response = await chat(
                    input_messages=input_messages,
                    tools=tools,
                    session=session,
                )

                # 응답 처리
                response_json = json.loads(response[0]["content"])
                docent_name, docent_email = (
                    response_json["name"],
                    response_json["email"],
                )
                # 완료 여부 확인 (여기서 적절한 완료 조건을 설정)
                if docent_name != "없음":
                    polling_complete = True
                else:
                    # 잠시 대기 후 다시 시도
                    await asyncio.sleep(2)

            print(docent_name, docent_email)

            # result = await session.call_tool(
            #     "slack_post_message",
            #     arguments={
            #         "channel_id": "C08RBKTGZ7H",
            #         # "text": f"➡️ 가능하신 분은 이 메시지에 스레드 답글 달아 주세요. ({datetime.datetime.now().strftime('%H:%M:%S')})",
            #         "text": "hi",
            #     },
            # )
            # print(result)
            # print(json.loads(result.content[0].text)['ts'])

            # result = await session.call_tool(
            #     "slack_get_thread_replies",
            #     arguments={
            #         "channel_id": "C08RBKTGZ7H",
            #         # "text": f"➡️ 가능하신 분은 이 메시지에 스레드 답글 달아 주세요. ({datetime.datetime.now().strftime('%H:%M:%S')})",
            #         "thread_ts": "1746858793.438609",
            #     },
            # )
            # print(result)

            # result = await session.call_tool(
            #     "slack_get_user_profile",
            #     arguments={
            #         "user_id": "U08SE5PHDQQ",
            #         # "text": f"➡️ 가능하신 분은 이 메시지에 스레드 답글 달아 주세요. ({datetime.datetime.now().strftime('%H:%M:%S')})",
            #     },
            # )
            # print(result)

            # result = await session.call_tool(
            #     "slack_reply_to_thread",
            #     arguments={
            #         "channel_id": "C08RBKTGZ7H",
            #         "thread_ts": "1746858793.438609",
            #         "text": "@김민지 네 감사합니다!",
            #     },
            # )
            # print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
