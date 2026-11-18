"""OpenAI provider for the chatbot (spec section 8, ADR-0008): embeddings and answer wording.

Plain HTTPS calls with the standard library (no extra package). The API key comes from the
OPENAI_API_KEY setting and is only sent in the Authorization header to api.openai.com.
What is sent: the masked question and public clinic passages. Never patient data.
"""

import json
import logging
import urllib.request
from collections.abc import Callable

from app.chatbot.knowledge import Passage
from app.chatbot.writer import SYSTEM_PROMPT, build_user_message
from app.core.config import settings

BASE_URL = "https://api.openai.com/v1"
LANGUAGE_NAMES = {"fr": "French", "en": "English"}
log = logging.getLogger(__name__)


class OpenAIError(Exception):
    pass


class OpenAIClient:
    def __init__(
        self,
        api_key: str,
        chat_model: str,
        embedding_model: str,
        timeout: float = 15,
        opener: Callable = urllib.request.urlopen,
    ) -> None:
        self._api_key = api_key
        self.chat_model = chat_model
        self.embedding_model = embedding_model
        self._timeout = timeout
        self._open = opener

    def _post(self, path: str, payload: dict) -> dict:
        request = urllib.request.Request(  # noqa: S310 - fixed https address, not user input
            f"{BASE_URL}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with self._open(request, timeout=self._timeout) as response:  # nosec B310
                return json.loads(response.read().decode("utf-8"))
        except Exception as error:
            # Only the error type is logged: never the key, the question or the answer.
            raise OpenAIError(type(error).__name__) from None

    def embed(self, texts: list[str]) -> list[list[float]]:
        """One embedding vector per text, in the same order."""
        data = self._post("/embeddings", {"model": self.embedding_model, "input": texts})
        rows = sorted(data["data"], key=lambda row: row["index"])
        return [row["embedding"] for row in rows]

    def chat(self, system: str, user: str) -> str:
        data = self._post(
            "/chat/completions",
            {
                "model": self.chat_model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_completion_tokens": 400,
            },
        )
        return data["choices"][0]["message"]["content"] or ""


class OpenAIWriter:
    """Words the answer from the given passages only (the result is checked by writer.accept)."""

    def __init__(self, client: OpenAIClient) -> None:
        self._client = client

    def write(self, question: str, language: str, passages: list[Passage]) -> str | None:
        system = SYSTEM_PROMPT.format(language_name=LANGUAGE_NAMES[language])
        return self._client.chat(system, build_user_message(question, passages))


def client_from_settings() -> OpenAIClient | None:
    """The configured client, or None when OPENAI_API_KEY is empty (keyword mode)."""
    if not settings.openai_api_key:
        return None
    return OpenAIClient(
        settings.openai_api_key,
        settings.openai_chat_model,
        settings.openai_embedding_model,
        settings.openai_timeout_seconds,
    )
