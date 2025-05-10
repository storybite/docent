from anthropic import Anthropic
from prompt_templates import system_prompt


class LLM:

    _instances: dict[str, "LLM"] = {}

    def __new__(cls, model_name: str, system_prompt: str, *args, **kwargs):
        if model_name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[model_name] = instance
        return cls._instances[model_name]

    def __init__(self, model_name: str, system_prompt: str):
        if getattr(self, "_initialized", False):
            return

        self.client = Anthropic()
        self.model = model_name
        self.system_prompt = system_prompt
        self._initialized = True  # 인스턴스 단위 초기화 완료 플래그

    def create_response(
        self,
        messages: list,
        temperature: float = 0,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
        tools: list | None = None,
    ):
        tools = tools or []
        try:
            return self.client.messages.create(
                max_tokens=max_tokens,
                temperature=temperature,
                tools=tools,
                system=system_prompt or self.system_prompt,
                messages=messages,
                model=self.model,
            )
        except Exception as e:
            print(f"[LLM ERROR] {e}")
            raise

    def create_response_text(
        self,
        messages: list,
        temperature: float = 0.5,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
    ) -> str:
        response = self.create_response(
            messages, temperature, max_tokens, system_prompt
        )
        return response.content[0].text


# 모델별 싱글턴 인스턴스 생성
claude_3_7 = LLM(model_name="claude-3-7-sonnet-20250219", system_prompt=system_prompt)
claude_3_5 = LLM(model_name="claude-3-5-sonnet-20240620", system_prompt=system_prompt)
