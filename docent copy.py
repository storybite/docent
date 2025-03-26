from anthropic import Anthropic
from typing import List, Dict
import base64
import json
import os

system_prompt = """
당신은 박물관 도슨트입니다. 관람객의 질문에 친절하게 설명하세요.
채팅 창에 글씨가 너무 많으면 읽기 어려우니 가급적 5문장 이내로 답하세요.
"""

user_prompt = """
<relic_information>
    <label>{label}</label>
    <content>{content}</content>
</relic_information>

<instructions>
사용자 의도 'A': 작품 설명 요청
사용자 의도 'B': 다음 그림 출력 요청
<user_message/>에 대해 <response_format/>에 따라 응답하세요:
</instructions>

<response_format>
<json> 태그로 감싸 다음의 JSON 포맷으로 응답하세요:
{{"사용자 의도": <'A','B' 중 택 1>, "답변":<'B'인 경우는 ''>}}
</response_format>

<user_message>
{user_message}
</user_message>
"""


# 로컬 파일을 base64로 인코딩
def get_base64_data(file_path):
    with open(file_path, "rb") as f:
        base64_data = base64.standard_b64encode(f.read()).decode("utf-8")
    return base64_data


client = Anthropic()


class Relics:
    def __init__(self):
        self.load_relics()
        self.index = 0

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


class Conversation:

    hello = "안녕하세요! 도슨트봇입니다. 작품에 대해 궁금한 점이 있으시면 편하게 질문해주세요."

    def __init__(self):
        self.messages = []
        self.add_assistant_message(self.hello)
        self.image_path = ""
        self.request_message = None

    def add_user_message(self, user_message: str, **args) -> None:
        user_prompt_ = user_prompt.format(
            user_message=user_message, label=args["label"], content=args["content"]
        )
        if self.image_path != args["image_path"]:
            self.request_message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": get_base64_data(args["image_path"]),
                            },
                        },
                        {
                            "type": "text",
                            "text": user_prompt_,
                        },
                    ],
                    # "message": user_message,
                },
                {"role": "assistant", "content": "<json>", "message": None},
            ]
            self.image_path = args["image_path"]
        else:
            self.request_message = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt_,
                        }
                    ],
                    # "message": user_message,
                },
                {"role": "assistant", "content": "<json>", "message": None},
            ]

        self.messages.extend(self.request_message)

    # def get_context(self):
    #     context = []
    #     for message in self.context:
    #         temp_context = {
    #             "role": message["role"],
    #             "content": message["content"]
    #         }
    #         if temp_context["content"][0]["type"] == "image":
    #             temp_context["content"][1]["text"] = temp_context["message"]
    #         else:
    #             message["content"][0]["text"] = message["message"]
    #         context.append(message)
    #     return context

    def add_assistant_message(self, response_message: str, label: dict) -> None:
        json_data = json.loads(response_message)
        if json_data["사용자 의도"] == "A":
            assistant_message = json_data["답변"]
        elif json_data["사용자 의도"] == "B":
            assistant_message = f"다음 작품은 {label['명칭']}입니다."
        self.messages.append({"role": "assistant", "content": assistant_message})
        return assistant_message

    def update_request_message(self, text_message: str):
        if len(self.request_message[0]["content"]) == 1:
            self.request_message[0]["content"][0]["text"] = text_message
        else:
            self.request_message[0]["content"][1]["text"] = text_message
        self.request_message[1]["content"] = ""

    def get_history(self) -> List[Dict]:
        simplified_history = []
        for message in self.messages:
            if message["role"] == "user":
                if message["content"][0]["type"] == "image":
                    simplified_history.append(
                        {"role": message["role"], "text": message["content"][1]["text"]}
                    )
                else:
                    simplified_history.append(
                        {"role": message["role"], "text": message["content"][0]["text"]}
                    )
            else:
                if message["content"] == "</json>":
                    continue
                simplified_history.append(
                    {"role": message["role"], "text": message["content"]}
                )

        return simplified_history


class DocentBot:

    def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):

        self.model = model_name
        self.conversation = Conversation()

        self.relics = Relics()
        # self.image_path = "images/image_readtop.png"
        # self.image_path = "scrap/relics/348/bon001958-00-01.jpg"
        # self.image_index = 0
        # self.image_list = [
        #     # "images/image_readtop.jpg",
        #     "scrap/relics/348/bon001958-00-01.jpg",
        #     "scrap/relics/349/bon001959-00-01.jpg",
        #     "scrap/relics/350/bon001981-00-03.jpg",
        # ]

    def get_image_path(self):
        # 디렉터리의 끝 파일 명명
        # relics_id = self.relics.relic_ids[self.relics.index]
        # self.current_image = os.path.join(
        #     "scrap", "relics", relics_id, "bon001958-000-0001.jpg"
        # )
        # return self.current_image
        return self.relics.get_relic()[2]

    # def add_message(self, role: str, content: str) -> None:
    #     """대화 기록에 메시지 추가"""
    #     self.context.append({"role": role, "content": content})

    def create_response(self) -> str:
        try:
            # API 호출
            response = client.messages.create(
                max_tokens=1024,
                system=system_prompt,
                messages=self.context,
                model=self.model,
                stop_sequences=["</json>"],
            )
            # 응답 저장
            response_message = response.content[0].text
            return response_message
        except Exception as e:
            return f"Error: {str(e)}"

    def answer(self, user_input: str) -> str:
        # 사용자 입력 추가
        label, content, image_path = self.relics.get_relic()
        self.conversation.add_user_message(
            user_input, label=label, content=content, image_path=image_path
        )
        response_message = self.create_response()
        self.conversation.update_request_message(user_input)
        assistant_message = self.conversation.add_assistant_message(
            response_message, label
        )
        return assistant_message

    def get_conversation_history(self) -> List[Dict]:
        """전체 대화 기록 반환"""
        return self.conversation.messages

    def get_history(self) -> List[Dict]:
        return self.conversation.get_history()
