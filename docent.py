from anthropic import Anthropic
import base64
import json
import os
import tools
from PIL import Image
from pathlib import Path
from prompt_templates import (
    guide_instruction,
    revisit_instruction,
    caching_info,
    cached_info_ref_instruction,
)
from utils import get_base64_data
from llm import claude
from tools import use_tools

client = Anthropic()


class Relics:

    def __init__(self):
        self._load_database()
        self.index = -1

    def _load_database(self):
        try:
            file_path = Path("scrap2") / "database" / "relic_index.json"
            with open(file_path, "r", encoding="utf-8") as f:
                self.database: dict = json.load(f)
                for key, value in self.database.items():
                    value["img_path"] = str(
                        Path("scrap2", "database", key, Path(value["img"]).name)
                    )
                    value["title"] = f"{value['label']['명칭']} ({key})"
                    value["is_presented"] = False
                    value["is_cached"] = False
                self.ids = list(self.database.keys())
        except Exception as e:
            import traceback

            msg = f"Error loading relic_index.json: {traceback.format_exc()}"
            print(msg)
            raise e

    @property
    def current_id(self):
        return self.ids[self.index]

    @property
    def current(self):
        current_relic = self.database[self.current_id]
        return current_relic

    @property
    def next(self):
        self.index += 1
        return self.current

    @property
    def previous(self):
        if self.index == 0:
            raise ValueError("첫 번째 작품입니다.")
        else:
            self.index -= 1
        return self.current

    @property
    def header(self):
        prefix = "검색된 작품" if isinstance(self, SearchedRelics) else ""
        return f"{prefix} {len(self.database)}점 중 {self.index + 1}번째 전시물입니다."

    def set_presented(self, is_presented: bool):
        self.database[self.current_id]["is_presented"] = is_presented

    def current_to_card(self):
        return {
            "header": self.header,
            "img_path": self.current["img_path"],
            "title": self.current["title"],
        }

    def __getitem__(self, key):
        if isinstance(key, slice):
            indices = range(*key.indices(len(self.ids)))
            return [self.database[self.ids[i]] for i in indices]
        else:
            raise Exception("Invalid slicing key type")


class SearchedRelics(Relics):

    def __init__(self, searched_database: dict, original: Relics):
        self.original = original
        self.database = searched_database
        self.index = -1
        self.ids = list(self.database.keys())


class InstructionHandler:

    def __init__(self):
        self.last_guide_id = ""

    def add_guide_with_cache(self, size, relics: Relics, messages: list):
        for relic in relics[:size]:
            caching_prompt = caching_info.format(
                title=relic["title"], label=relic["label"], content=relic["content"]
            )
            messages.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": get_base64_data(relic["img_path"]),
                            },
                        },
                        {"type": "text", "text": caching_prompt},
                    ],
                }
            )
            relic["is_cached"] = True
        messages[-1]["content"][1]["cache_control"] = {"type": "ephemeral"}

    def add_guide(self, relics: Relics, messages: list):

        guide_instruction_prompt = guide_instruction.format(
            label=relics.current["label"],
            content=relics.current["content"],
        )
        messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": get_base64_data(relics.current["img_path"]),
                        },
                    },
                    {"type": "text", "text": guide_instruction_prompt},
                ],
            }
        )
        self.last_guide_id = relics.current_id

    def add_cache_ref_prompt(self, relics: Relics, messages: list):
        cached_info_ref_prompt = cached_info_ref_instruction.format(
            title=relics.current["title"]
        )
        messages.append({"role": "user", "content": cached_info_ref_prompt})
        self.last_guide_id = relics.current_id

    def check_and_add(self, relics: Relics, messages: list):
        if self.last_guide_id == relics.current_id:
            return
        self.add_guide(relics, messages)
        messages.append({"role": "user", "content": revisit_instruction})


class ExceptionHandler:

    @staticmethod
    def overvlow(messages: list, relics: Relics):
        if isinstance(relics, SearchedRelics):
            messages.append(
                {
                    "role": "assistant",
                    "content": "검색된 작품을 모두 소개했습니다. 다음 작품을 소개하겠습니다.",
                }
            )
            relics.original.index += 1
            return relics.original
        else:
            messages.append(
                {"role": "assistant", "content": "준비한 작품울 모두 소개했습니다."}
            )
            relics.index = 0
            return relics

    @staticmethod
    def underflow(messages: list, relics: Relics):
        messages.append({"role": "assistant", "content": "첫 번째 작품입니다.1"})
        relics.index = 0


class DocentBot:

    def __init__(self, model_name="claude-3-5-sonnet-20240620"):
        self.model = model_name
        self.messages = []
        self.relics = Relics()
        self.instruction = InstructionHandler()

    def _present_relic(self):
        self.instruction.add_guide(self.relics, self.messages)
        response_message = claude.create_response_text(messages=self.messages)
        self.messages.append({"role": "assistant", "content": response_message})
        self.relics.set_presented(True)

    def move(self, is_next: bool):
        if is_next:
            try:
                _ = self.relics.next
            except IndexError:
                self.relics = ExceptionHandler.overvlow(self.messages, self.relics)
        else:
            try:
                _ = self.relics.previous
            except ValueError:
                ExceptionHandler.underflow(self.messages, self.relics)

        if not self.relics.current["is_presented"]:
            self._present_relic()

    def answer(self, user_input: str) -> str:
        self.instruction.check_and_add(self.relics, self.messages)
        self.messages.append({"role": "user", "content": user_input})
        searched_database, tool_message = use_tools(
            self.get_conversation(), self.relics.database
        )
        if searched_database:
            self.relics = SearchedRelics(searched_database, self.relics)
        if tool_message:
            self.messages.append({"role": "assistant", "content": tool_message})
            response_message = tool_message
        else:
            response_message = claude.create_response_text(messages=self.messages)
            self.messages.append({"role": "assistant", "content": response_message})
        return response_message

    def get_conversation(self):
        conversation = []
        for message in self.messages:
            if isinstance(message["content"], list):
                text_message: str = message["content"][1]["text"].strip()
            else:
                text_message = message["content"].strip()
            if text_message.startswith("<system_command>"):
                continue
            conversation.append({"role": message["role"], "content": text_message})
        return conversation
