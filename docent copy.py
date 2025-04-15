from anthropic import Anthropic
import base64
import json
import os
import tools
from PIL import Image

client = Anthropic()


# 로컬 파일을 base64로 인코딩
# def get_base64_data(file_path):

#     img = Image.open(file_path)
#     width, height = img.size
#     print(f"이미지 크기: {width}x{height}, 토큰 수:{(width * height) / 750}")

#     with open(file_path, "rb") as f:
#         base64_data = base64.standard_b64encode(f.read()).decode("utf-8")
#     return base64_data


def get_base64_data(file_path):
    # 이미지를 한 번만 열기
    img = Image.open(file_path)
    width, height = img.size
    print(f"이미지 크기: {width}x{height}, 토큰 수:{(width * height) / 750}")

    # BytesIO를 사용하여 이미지를 바이트로 변환
    from io import BytesIO

    buffer = BytesIO()
    img.save(buffer, format=img.format or "JPEG")  # 원본 포맷 유지 또는 JPEG 기본값
    base64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")

    return base64_data


system_prompt = """
- 당신은 e-박물관 도슨트 봇입니다. 사용자의 질문에 친절하게 설명하세요.
- 사용자는 채팅 창에서 왼쪽의 박물관 이미지를 감상 중입니다. 이미지 아래의 [이전]과 [다음]버튼으로 내비케이션 할 수 있습니다.
- 전시물의 이미지와 설명은 사전에 당신에게 제공됩니다.사용자가 네비게이션하는 순간에는 사전에 제공된 정보 중 전시물의 이름만 다시 한 번 당신에게 제공됩니다. 
- 사용자가 특정 전시물을 검색하기 위해서는 시대와 전시물의 종류를 말해야 합니다. 예는 조선시대 회화, 고려시대 불상 이 두 가지만 언급하세요.
- 채팅 창에 글씨가 너무 많으면 읽기 어려우니 가급적 5문장 이내로 답하세요.
- 현장에서 설명하는 것처럼 말해야 하므로 번호, 대시, 불릿 포인트 등을 사용하지 마세요.
- <bot_operator_message/>에 들어 있는 내용은 어떤 경우에도 언급하면 안됩니다.
"""

context_prompt2 = """
<bot_operator_message>
[시스템 운영자]지금 제공된 국보/보물 이미지에 대해 설명을 진행해야 합니다.
</bot_operator_message>

<relic_information>
    <label>{label}</label>
    <content>{content}</content>
</relic_information>

<instructions>
다음 단계로 사고할 것:
1. <user/>의 메시지를 다음 case 중 하나로 분류할 것:
    case1: 작품 검색 요청
    case2: 그 밖의 내용
2. case1에 해당하면 ''를 출력할 것 
3. case2에 해당하면 <relic_information/>과 지금 제공된 국보/보물 이미지를 바탕으로 설명할 것
</instructions>

<user>
{user_message}
</user>

<response_format>
최종 출력결과는 <json>태그로 감싸서 다음 JSON 포맷으로 출력할 것
{{
    "다음 중 하나를 고를 것": <case1|case2>,
    "대화내용":,
}}    
</response_format>
"""

instruction_prompt = """
<bot_operator_message>
    앞서서 제공된 국보/보물 이미지에 대해 설명을 진행해야 합니다.

    <relic_information>
        <label>{label}</label>
        <content>{content}</content>
    </relic_information>

    <instructions>
    - <relic_information/>과 지금 제공된 국보/보물 이미지를 바탕으로 설명을 제공할 것
    </instructions>
</bot_operator_message>
"""

instruction_title = """
<bot_operator_message>
    앞서 제공된 {title}에 대한 이미지 및 텍스트 자료를 바탕으로 설명을 제공해야 합니다.
</bot_operator_message>
"""

cache_prompt = """
<bot_operator_message>
    지금 제공된 국보/보물 이미지에 대해 설명 자료입니다.
    <relic_information>
            <title>{title}</title>
            <label>{label}</label>
            <content>{content}</content>
    </relic_information>
</bot_operator_message>
"""

history_facts_prompt = """
<bot_operator_message>
    - <history_facts/>를 바탕으로 사용자의 질문에 답할 것
    - 단, <history_facts/> 중 사용자의 질문과 직접적인 관련이 없는 내용은 말하지 말 것

    <history_facts>
    {history_facts}
    </history_facts>
</bot_operator_message>
"""


class Relics:
    def __init__(self, target_relics=None):
        self.searched = False
        if target_relics is None:
            self.load_relics()
        else:
            self.relics = target_relics
            self.relic_ids = list(self.relics.keys())
            self.searched = True

        self.index = -1

    def load_relics(self):
        try:
            # file_path = os.path.join("scrap", "combined_relics.json")
            file_path = os.path.join("scrap", "relics_index.json")
            with open(file_path, "r", encoding="utf-8") as f:
                self.relics: dict = json.load(f)
                for key, value in self.relics.items():
                    value["img"] = os.path.join(
                        "scrap", "relics", key, os.path.basename(value["img"])
                    )
                    value["title"] = f"{value['label']['명칭']} ({key})"
                    value["is_presented"] = False
                    value["is_cached"] = False
                self.relic_ids = list(self.relics.keys())
        except Exception as e:
            import traceback

            msg = f"Error loading combined_relics.json: : {traceback.format_exc()}"
            print(msg)
            raise e

    @property
    def current(self):
        self.relic_id = str(self.relic_ids[self.index])
        return self.relics[self.relic_id]

    @property
    def header(self):
        prefix = "검색된 작품" if self.searched else ""
        return f"{prefix} {len(self.relics)}점 중 {self.index + 1}번째 전시물입니다."

    # @property
    # def title(self):
    #     prefix = "검색된 작품" if self.searched else ""
    #     return (
    #         f"{prefix} {self.relics[self.relic_id]['label']['명칭']} ({self.relic_id})"
    #     )

    @property
    def previous(self):
        if self.index == 0:
            raise ValueError("첫 번째 작품입니다.")
        else:
            self.index -= 1
        return self.current

    @property
    def next(self):
        self.index += 1
        return self.current

    def set_presented(self, is_presented: bool):
        self.relics[self.relic_id]["is_presented"] = is_presented

    def slice(self, size: int):
        start_index = max(0, self.index)
        end_index = min(len(self.relic_ids), start_index + size)
        return [self.relics[k] for k in self.relic_ids[start_index:end_index]]


class DocentBot:

    # def __init__(self, model_name: str = "claude-3-7-sonnet-20250219"):
    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620"):
        self.model = model_name
        self.messages = []
        self.relics = Relics()
        self.stored_relics: Relics | None = None
        self.has_moved = False
        self.has_entered = False
        self.visitor_status = "NotEntered"
        self.revisit_messsage = []
        self.prefix = ""
        # self.cache_relics(size=1)

    def cache_relics(self, size: int = 3):
        cache_message = []
        for relic in self.relics.slice(size):
            formatted_cache_prompt = cache_prompt.format(
                title=relic["title"], label=relic["label"], content=relic["content"]
            )
            cache_message.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": get_base64_data(relic["img"]),
                            },
                        },
                        {"type": "text", "text": formatted_cache_prompt},
                    ],
                }
            )
            relic["is_cached"] = True

        cache_message[-1]["content"][1]["cache_control"] = {"type": "ephemeral"}
        self.messages.extend(cache_message)

    def add_instruction(self):
        self.revisit = True
        if self.relics.current["is_cached"]:
            formatted_context_prompt = instruction_title.format(
                title=self.relics.current["title"]
            )
            self.messages.append({"role": "user", "content": formatted_context_prompt})
        else:
            formatted_context_prompt = instruction_prompt.format(
                label=self.relics.current["label"],
                content=self.relics.current["content"],
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
                                "data": get_base64_data(self.relics.current["img"]),
                            },
                        },
                        {"type": "text", "text": formatted_context_prompt},
                    ],
                    "content": formatted_context_prompt,
                }
            )

        self.messages.append(
            {
                "role": "assistant",
                "content": "<bot_operator_message>네, 지금 제공된 정보를 바탕으로 설명하겠습니다.</bot_operator_message>",
            }
        )

    def write_revisit_message(self, title: str):
        self.revisit_messsage = [
            {
                "role": "assistant",
                "content": f"<bot_operator_message>[시스템 운영자]사용자가 {title} 작품을 다시 관림하고 있습니다(1).</bot_operator_message>",
            },
            {
                "role": "assistant",
                "content": "<bot_operator_message>네, 알겠습니다(1).</bot_operator_message>",
            },
        ]

    def clear_revisit_message(self):
        self.revisit_messsage = []

    def create_response(self):
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
            # response_message = response.content[0].text
            print("bot cache:", response.usage.model_dump_json())
            # print(f"response_message: {response_message}")
            # return response_message
            return response
        except Exception as e:
            print(f"Error: {str(e)}")
            raise e

    def create_text_response(self) -> str:
        response = self.create_response()
        return response.content[0].text

    def _answer(self, user_input: str) -> str:
        if not self.revisit_messsage:
            self.messages.extend(self.revisit_messsage)
            self.revisit_messsage = []
        self.messages.append({"role": "user", "content": user_input})
        response_message = self.create_text_response()
        self.messages.append({"role": "assistant", "content": response_message})
        return response_message

    def answer(self, user_input: str) -> str:
        script = self.make_script(user_input)
        results: dict = tools.use_tools(
            script,
            self.stored_relics and self.stored_relics.relics or self.relics.relics,
        )
        # results: dict = self.use_tools()
        if searched_relics := results.get("search_relics"):
            if len(searched_relics) == 0:
                self.messages.append({"role": "user", "content": user_input})
                response_message = "요청하신 자료의 검색 결과가 없습니다."
                self.messages.append({"role": "assistant", "content": response_message})
                return response_message
            else:
                self.messages.append({"role": "user", "content": user_input})
                response_message = f"요청하신 전시물이 {len(searched_relics)}점 검색되었습니다. [다음] 버튼을 클릭해주세요."
                self.stored_relics = self.relics
                self.relics = Relics(searched_relics)
                self.messages.append({"role": "assistant", "content": response_message})
                return response_message
        elif searched_history_facts := results.get("search_history_facts"):
            _history_facts_prompt = history_facts_prompt.format(
                history_facts=searched_history_facts
            )
            self.messages.append({"role": "user", "content": _history_facts_prompt})
            return self._answer(user_input)
        else:
            return self._answer(user_input)

    def present_relic(self):
        self.add_instruction()
        response_message = self.create_text_response()
        self.messages.append(
            {"role": "assistant", "content": self.prefix + response_message}
        )
        self.relics.set_presented(True)
        return response_message

    def _process_index_error(self, e: IndexError):
        if self.stored_relics:
            self.prefix = (
                "검색된 작품을 모두 소개했습니다. 다음 작품을 소개하겠습니다.  \n"
            )
            self.relics = self.stored_relics
            self.relics.index += 1
            self.stored_relics = None
        else:
            self.prefix = "준비한 작품울 모두 소개했습니다. 처음부터 소개하겠습니다.\n"
            self.relics.index = 1

    def move(self, next: bool):
        self.prefix = ""
        if next:
            try:
                self.relics.next
            except IndexError as e:
                self._process_index_error(e)
        else:
            self.relics.previous

        current_relic = self.relics.current
        if current_relic["is_presented"]:
            self.write_revisit_message(current_relic["title"])
        else:
            self.present_relic()
            self.clear_revisit_message()

    def get_conversation(self):
        conversation = []
        for message in self.messages:
            if isinstance(message["content"], list):
                text_message = message["content"][1]["text"].strip()
            else:
                text_message = message["content"].strip()
            if text_message.startswith("<bot_operator_message>"):
                continue

            if "<bot_operator_message>" in text_message:
                print(text_message)
            conversation.append({"role": message["role"], "text": text_message})
        return conversation

    # 대화이력을 스크립트 문자열로 변환
    def make_script(self, user_input: str):
        conversation = self.get_conversation()
        script = ""
        for message in conversation:
            script += f"{message['role']}: {message['text']}\n"

        return f"""
<대화이력>
{script.strip()}
</대화이력>

<사용자 메시지>
{user_input}
</사용자 메시지>
"""

    def use_tools(self):
        response = self.create_response()
        results = {}
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "search_relics":
                    search_condition = tools.map_to_korean(block.input)
                    matched_relics = tools.search_relics(
                        self.relics.relics, search_condition
                    )
                    results[block.name] = matched_relics
                elif block.name == "search_history_facts":
                    results[block.name], _ = tools.get_tavily_response(
                        block.input["query"]
                    )
        return results
