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
당신은 박물관 도슨트입니다. 관람객의 질문에 친절하게 설명하세요.
채팅 창에 글씨가 너무 많으면 읽기 어려우니 가급적 5문장 이내로 답하세요.
채팅이 아니라 현장에서 설명하는 것이므로 번호, 대시, 불릿 포인트 등을 사용하지 마세요.
"""

context_prompt = """
<context>
지금 제공된 국보/보물 이미지에 대해 설명을 진행해야 합니다.
</context>

<relic_information>
    <label>{label}</label>
    <content>{content}</content>
</relic_information>

<instructions>
if 사용자가 현재 작품에 대해 설명을 요청하면:
    <relic_information/>과 지금 제공된 국보/보물 이미지를 바탕으로 설명을 제공할 것
elif 사용자가 다음 작품을 보여달라고 요청하면:
    '[네] 다음 작품을 소개해드리겠습니다.'라고 답할 것([네]라는 문자열은 후속처리를 위해 사용되므로 변경하지 말것)
    
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
                self.relic_ids = list(self.relics.keys())
        except Exception as e:
            import traceback

            msg = f"Error loading combined_relics.json: : {traceback.format_exc()}"
            print(msg)
            raise e

    def get_relic(self):
        self.relic_id = str(self.relic_ids[self.index])
        return (
            self.relics[self.relic_id]["label"],
            self.relics[self.relic_id]["content"],
            self.relics[self.relic_id]["img"],
        )

    def next_relic(self):
        self.index += 1
        return self.get_relic()


class DocentBot:

    hello = "안녕하세요! 도슨트봇입니다. 작품에 대해 궁금한 점이 있으시면 편하게 질문해주세요."

    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):
        self.model = model_name
        self.messages = [{"role": "assistant", "content": self.hello}]
        self.relics = Relics()
        self.add_instruction()

    def get_image_path(self):
        return self.relics.get_relic()[2]

    def add_instruction(self):
        label, content, image_path = self.relics.next_relic()
        print(image_path)
        __context_prompt__ = context_prompt.format(label=label, content=content)
        self.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": get_base64_data(image_path),
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

    def create_response(self) -> str:
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
            return response_message
        except Exception as e:
            return f"Error: {str(e)}"

    def answer(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        response_message: str = self.create_response()
        if "[네]" in response_message:
            self.add_instruction()
        self.messages.append({"role": "assistant", "content": response_message})
        return response_message

    def get_conversation(self):
        conversation = []
        for message in self.messages:
            if isinstance(message["content"], list):
                text_message = message["content"][1]["text"].strip()
            else:
                text_message = message["content"].strip()
            if text_message.startswith("<context>"):
                continue
            conversation.append({"role": message["role"], "text": text_message})
        return conversation
