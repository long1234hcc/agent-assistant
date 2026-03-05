from abc import ABC, abstractmethod
from google import genai
from google.genai import types


class BaseLLM(ABC):
    def __init__(self, model_name: str, api_key: str):

        self.model_name = model_name
        self.api_key = api_key
        self.client = self.create_client()

    @abstractmethod
    def create_client(self):
        pass

    @abstractmethod
    def generate_response(self, messages: list[dict], system_prompt: str, tools: list = None) -> str:
        pass


class GenAIModel(BaseLLM):

    def create_client(self):
        client = genai.Client(api_key=self.api_key)
        return client

    def generate_response(self, messages: list[dict], system_prompt: str, tools: list = None) -> str:
        contents = []
        for msg in messages:
            contents.append(
                types.Content(
                    role=msg["role"],
                    parts=[types.Part.from_text(text=msg["content"])]
                )
            )

        response = self.client.models.generate_content(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                tools=tools or [],
                automatic_function_calling=types.AutomaticFunctionCallingConfig(
                    disable=True  # ← Agent tự handle, không để Gemini tự gọi
                )
            ),
            contents=contents
        )

        return response
