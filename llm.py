from anthropic import Anthropic
from prompt_templates import system_prompt


class LLM:

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(LLM, cls).__new__(cls)
        return cls._instance

    def __init__(self, model_name: str, system_prompt: str):
        if self._initialized:
            return

        self.client = Anthropic()
        self.system_prompt = system_prompt
        self.model = model_name
        self._initialized = True

    def create_response(
        self, messages: list, temperature=0, max_tokens=2048, system_prompt=None
    ):
        try:
            response = self.client.messages.create(
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt or self.system_prompt,
                messages=messages,
                model=self.model,
            )
            return response

        except Exception as e:
            print(f"Error: {str(e)}")
            raise e

    def create_response_text(
        self, messages: list, temperature=0.5, max_tokens=2048, system_prompt=None
    ):
        return (
            self.create_response(messages, temperature, max_tokens, system_prompt)
            .content[0]
            .text
        )


# claude = LLM(model_name="claude-3-7-sonnet-20250219", system_prompt=system_prompt)
claude = LLM(model_name="claude-3-5-sonnet-20240620", system_prompt=system_prompt)
