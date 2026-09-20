import os
from typing import Protocol
from groq import Groq

# Use a fast, free-tier-friendly Groq model like Llama 3.3
# Change to a currently active Groq model
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


class GeminiClient(Protocol):
    def generate(self, prompt: str) -> str:
        ...


class GoogleGeminiClient:
    def __init__(self, api_key: str | None = None, model: str = GROQ_MODEL) -> None:
        # Hardcoding your provided key or falling back to environment variable
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise RuntimeError("GROQ_API_KEY environment variable is not configured")
        self.model = model
        self.client = Groq(api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.choices[0].message.content
        except Exception as error:
            raise RuntimeError(f"Groq request failed: {error}") from error