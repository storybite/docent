from anthropic import Anthropic
from typing import List, Dict
import base64
import json
import os

client = Anthropic()


# 로컬 파일을 base64로 인코딩
def get_base64_data(file_path):
    with open(file_path, "rb") as f:
        base64_data = base64.standard_b64encode(f.read()).decode("utf-8")
    return base64_data


system_prompt = """
- 당신은 e-박물관 도슨트입니다. 사용자의 질문에 친절하게 설명하세요.
- 사용자는 채팅 창에서 왼쪽의 박물관 이미지를 감상 중입니다. 이미지 아래의 [이전]과 [다음]버튼으로 내비케이션 할 수 있습니다.
- 채팅 창에 글씨가 너무 많으면 읽기 어려우니 가급적 5문장 이내로 답하세요.
- 현장에서 설명하는 것처럼 말해야 하므로 번호, 대시, 불릿 포인트 등을 사용하지 마세요.
"""

context_prompt = """
<context>
[시스템 운영자]지금 제공된 국보/보물 이미지에 대해 설명을 진행해야 합니다.
</context>

<relic_information>
    <label>{label}</label>
    <content>{content}</content>
</relic_information>

<instructions>
- <relic_information/>과 지금 제공된 국보/보물 이미지를 바탕으로 설명을 제공할 것
- 사용자 대화 중 [시스템 운영자]라는 말머리는 챗봇 시스템 운영자가 당신에게 내리는 명령을 뜻하므로 사용자에게는 이와 관련한 답변을 하지 말 것 
</instructions>
"""


class Relics:
    def __init__(self):
        self.load_relics()
        self.index = -1

    def load_relics(self):
        try:
            file_path = os.path.join("scrap", "combined_relics.json")
            with open(file_path, "r", encoding="utf-8") as f:
                self.relics: dict = json.load(f)
                for key, value in self.relics.items():
                    value["img"] = os.path.join(
                        "scrap", "relics", key, os.path.basename(value["img"])
                    )
                    value["title"] = f"{value['label']['명칭']} ({key})"
                    value["is_presented"] = False
                self.relic_ids = list(self.relics.keys())
        except Exception as e:
            import traceback

            msg = f"Error loading combined_relics.json: : {traceback.format_exc()}"
            print(msg)
            raise e

    def get_current_relic(self):
        self.relic_id = str(self.relic_ids[self.index])
        return self.relics[self.relic_id]
        # return (
        #     self.relics[self.relic_id]["label"],
        #     self.relics[self.relic_id]["content"],
        #     self.relics[self.relic_id]["img"],
        #     self.relics[self.relic_id]["is_presented"],
        # )

    def get_title(self):
        return f"{self.relics[self.relic_id]['label']['명칭']} ({self.relic_id})"

    def set_presented(self, is_presented: bool):
        self.relics[self.relic_id]["is_presented"] = is_presented

    def previous_relic(self):
        self.index -= 1
        return self.get_current_relic()

    def next_relic(self):
        self.index += 1
        return self.get_current_relic()

    def first_relic(self):
        self.index = 0
        return self.get_current_relic()


class DocentBot:

    hello = "안녕하세요! 도슨트봇입니다. 작품에 대해 궁금한 점이 있으시면 편하게 질문해주세요."

    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):
        self.model = model_name
        self.messages = [{"role": "assistant", "content": self.hello}]
        self.relics = Relics()
        self.has_moved = False
        self.has_entered = False
        self.visitor_status = "NotEntered"
        # self.add_instruction()

    # def get_title_image_path(self):
    #     label, _, image_path, _ = self.relics.get_relic()
    #     return f"{label['명칭']} ({self.relics.relic_id})", image_path

    def add_instruction(self):
        # label, content, image_path = self.relics.next_relic()
        current_relic = self.relics.get_current_relic()
        print(current_relic["img"])
        __context_prompt__ = context_prompt.format(
            label=current_relic["label"], content=current_relic["content"]
        )
        self.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": get_base64_data(current_relic["img"]),
                        },
                    },
                    {
                        "type": "text",
                        "text": __context_prompt__,
                    },
                ],
            }
        )
        self.messages.append(
            {
                "role": "assistant",
                "content": "<context>네, 지금 제공된 정보를 바탕으로 설명하겠습니다.</context>",
            }
        )

    def notify_navigation(self, title: str):
        self.messages.append(
            {
                "role": "assistant",
                "content": f"<context>[시스템 운영자]사용자가 {title} 작품을 다시 관림하고 있습니다(1).</context>",
            }
        )
        self.messages.append(
            {
                "role": "assistant",
                "content": "<context>네, 알겠습니다(1).</context>",
            }
        )

    def create_response(self) -> str:
        import time

        # time.sleep(1)
        # return "테스트입니다."
        try:
            # API 호출
            response = client.messages.create(
                max_tokens=1024,
                system=system_prompt,
                messages=self.messages,
                model=self.model,
            )
            # 응답 저장
            response_message = response.content[0].text
            print(f"response_message: {response_message}")
            return response_message
        except Exception as e:
            return f"Error: {str(e)}"

    def answer(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        response_message: str = self.create_response()
        # if "[네]" in response_message:
        #     self.add_instruction()
        self.messages.append({"role": "assistant", "content": response_message})
        return response_message

    def present_relic(self):
        self.add_instruction()
        response_message: str = self.create_response()
        self.messages.append({"role": "assistant", "content": response_message})
        self.relics.set_presented(True)
        return response_message

    def move(self, next: bool):
        if next:
            self.relics.next_relic()
        else:
            self.relics.previous_relic()

    def request_presentaion(self):
        current_relic = self.relics.get_current_relic()
        if current_relic["is_presented"]:
            self.notify_navigation(current_relic["title"])
            return None
        else:
            return self.present_relic()

        # else:
        #     self.present_relic()
        # return current_relic

    def get_conversation(self):
        conversation = []
        for message in self.messages:
            if isinstance(message["content"], list):
                text_message = message["content"][1]["text"].strip()
            else:
                text_message = message["content"].strip()
            if text_message.startswith("<context>"):
                continue

            if "<context>" in text_message:
                print(text_message)
            conversation.append({"role": message["role"], "text": text_message})
        return conversation

    def previous_relic(self):
        return self.relics.previous_relic()

    def next_relic(self):
        return self.relics.next_relic()

    def first_relic(self):
        self.messages = []
        return self.relics.first_relic()

    def get_current_relic(self):
        return self.relics.get_current_relic()
