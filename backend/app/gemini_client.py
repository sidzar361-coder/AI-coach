import os
from typing import Protocol


GEMINI_MODEL = "gemini-3.6-flash"


class GeminiClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GoogleGeminiClient:
    def __init__(self, api_key: str | None = None, model: str = GEMINI_MODEL) -> None:
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise RuntimeError("GEMINI_API_KEY environment variable is not configured")
        self.model = model

    def generate(self, prompt: str) -> str:
        from google import genai

        client = genai.Client(api_key=self.api_key)
        try:
            response = client.interactions.create(model=self.model, input=prompt)
            return response.output_text
        finally:
            close = getattr(client, "close", None)
            if close is not None:
                close()
