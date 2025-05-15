from typing import Optional
from contextlib import AsyncExitStack
import traceback

# from utils.logger import logger
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from datetime import datetime
import json
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from anthropic.types import Message
from pydantic import BaseModel, Field
from datetime import timedelta
import asyncio
import base64
import smtplib
from email.mime.text import MIMEText


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


application_template = """
🏺 프로그램: {program}
📅 방문일자: {visit_date}
⏰ 방문시간: {visit_hours}
👥 방문인원: {visitors}
""".strip()

email_template = """
안녕하세요? 문화해설사 예약이 완료되었습니다.

1. 신청 내용: 
{신청서}

2. 문화해설사 정보:
👤 이름: {문화해설사_이름}
📧 연락처: {문화해설사_이메일}
🔴 부득이한 사정으로 예약 취소 시 방문일 전일까지 문화해설사님 이메일로 통지 부탁드립니다.

3. 만날 장소: 
🏛 국립중앙박물관 1층 기획전시실 앞

✨ 유익하고 즐거운 시간되시길 바랍니다. 감사합니다!
"""


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

슬랙에 메시지를 전달할 때는 항상 친근한 말투를 사용하세요.

""".strip()


class ReservationAgent:

    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.llm = Anthropic()
        self.tools = []

    async def connect_sse_server(self):
        try:
            streams = await self.exit_stack.enter_async_context(
                streamablehttp_client(url)
            )
            self.session = await self.exit_stack.enter_async_context(
                ClientSession(*streams)
            )
            # ──────────── 몽키 패치 구간 ──────────
            if callable(getattr(self.session, "_session_read_timeout_seconds", None)):
                # 필요하면 원하는 시간으로 수정 (예: 10초)
                self.session._session_read_timeout_seconds = timedelta(seconds=10)
            # ───────────────────────────────────────
            await self.session.initialize()
            print("Connected to MCP server")
            mcp_tools = await self.session.list_tools()
            self.tools = [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": filter_input_schema(tool.inputSchema),
                }
                for tool in mcp_tools.tools
            ] + [report_reservation]
            print(f"Available tools: {[tool['name'] for tool in self.tools]}")

        except Exception as e:
            print(f"Error connecting to MCP server: {e}")
            traceback.print_exc()
            raise e

    async def polling_result(self, tool_name, tool_args, tool_result):
        for _ in range(1, 10):
            message = json.loads(tool_result.model_dump()["content"][0]["text"])[
                "messages"
            ]
            if len(message) >= 1:
                return tool_result
            await asyncio.sleep(1)
            tool_result = await self.session.call_tool(tool_name, tool_args)
        raise ValueError("Too many tries")

    async def _delegate_to_slackbot(
        self,
        system: list[dict],
        messages: list[dict],
    ):
        response = request_model(self.tools, system, messages)
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
                tool_result = await self.polling_result(
                    tool_name, tool_args, tool_result
                )

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
            response = request_model(self.tools, system_prompt, messages)
            if tries > 10:
                raise ValueError("Too many tries")
            tries += 1

    async def make_reservation(self, application: dict):
        raise Exception("test")
        input_messages = []
        polling_complete = False
        application_without_email = {
            k: v for k, v in application.items() if k != "applicant_email"
        }
        application_form = application_template.format(**application_without_email)

        while not polling_complete:
            if not input_messages:
                input_messages = [
                    {
                        "role": "user",
                        "content": f"아래 신청서로 문화해설을 요청하셨습니다. 가능한 문화해설사님께서는 메시지에 댓글 부탁 드립니다.\n{application_form}",
                    },
                ]

            bot_response = await self._delegate_to_slackbot(
                system=[
                    {
                        "type": "text",
                        "text": system_prompt,
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
                messages=input_messages,
            )

            if bot_response["is_success"]:
                polling_complete = True
                input_messages = []
                self.send_mail(application_form, application, bot_response)
            else:
                input_messages.append(
                    {
                        "role": "user",
                        "content": "완료 처리되지 않은 예약 건이 있는지 확인하세요.",
                    },
                )
                await asyncio.sleep(2)

    @staticmethod
    def send_mail(application_form: str, applicatoin: dict, bot_response: dict):
        body = email_template.format(
            신청서=application_form,
            문화해설사_이름=bot_response["docent_name"],
            문화해설사_이메일=bot_response["docent_email"],
        )

        sender = os.getenv("sender_email")
        receiver = applicatoin["applicant_email"]
        subject = "안녕하세요, 문화해설사 예약이 완료되었습니다."
        cc = bot_response["docent_email"]

        recipients = [receiver, cc]
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = os.getenv("sender_email")
        msg["To"] = receiver
        msg["Cc"] = cc

        # # Gmail SMTP: smtp.gmail.com, 포트 587(STARTTLS) 사용
        smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
        smtp_server.ehlo()  # 서버 연결 식별
        smtp_server.starttls()  # TLS(보안) 연결 시작
        smtp_server.login(sender, os.getenv("smtp_key"))

        smtp_server.sendmail(sender, recipients, msg.as_string())
        smtp_server.quit()
        print("메일 전송 완료")

    async def cleanup(self):
        try:
            await self.exit_stack.aclose()
            print("Disconnected from MCP server")
        except Exception as e:
            print(f"Error during cleanup: {e}")
            traceback.print_exc()
            raise e
