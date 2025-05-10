class Relics:

    def __init__(self):
        self._load_relics()
        self.index = -1

    def _load_relics(self):
        self.relics = {
            "1": {
                "header": "100점 중 1번째 이미지",
                "img_path": "images/relic1.png",
                "title": "1번 전시물",
                "is_presented": False,
            },
            "2": {
                "header": "100점 중 2번째 이미지 ",
                "img_path": "images/relic2.png",
                "title": "2번 전시물 ",
                "is_presented": False,
            },
        }
        self.relic_ids = list(self.relics.keys())

    @property
    def current(self):
        self.relic_id = self.relic_ids[self.index]
        return self.relics[self.relic_id]

    def next(self):
        self.index += 1
        return self.current

    def previous(self):
        if self.index == 0:
            raise ValueError("첫 번째 작품입니다.")
        else:
            self.index -= 1
        return self.current

    @property
    def header(self):
        return f"{len(self.relics)}점 중 {self.index + 1}번째 전시물입니다."

    def set_presented(self, is_presented: bool):
        self.relics[self.relic_id]["is_presented"] = is_presented

    def current_to_card(self):
        return {
            "header": self.header,
            "img_path": self.current["img_path"],
            "title": self.current["title"],
        }


class DocentBot:

    def __init__(self):
        self.messages = []
        self.relics = Relics()

    def move(self, is_next: bool):
        if is_next:
            try:
                self.relics.next()
            except IndexError as e:
                self._is_last()
        else:
            try:
                self.relics.previous()
            except ValueError as e:
                self._is_first()

        if not self.relics.current["is_presented"]:
            self._present_relic()

    def _present_relic(self):
        response_message = f" 이 작품은 {self.relics.current['title']} 입니다."
        self.messages.append({"role": "assistant", "content": response_message})
        self.relics.set_presented(True)

    def _is_last(self):
        self.messages.append(
            {"role": "assistant", "content": "준비한 작품울 모두 소개했습니다."}
        )

    def _is_first(self):
        self.messages.append({"role": "assistant", "content": "첫 번째 작품입니다."})
        self.relics.index = 0

    def answer(self, user_input: str) -> str:
        self.messages.append({"role": "user", "content": user_input})
        response_message = (
            f"{self.relics.current['title']}에 대해 대화를 나누고 있습니다."
        )
        self.messages.append({"role": "assistant", "content": response_message})
        return response_message

    def get_conversation(self):
        conversation = []
        for message in self.messages:
            text_message = message["content"].strip()
            conversation.append({"role": message["role"], "text": text_message})
        return conversation
