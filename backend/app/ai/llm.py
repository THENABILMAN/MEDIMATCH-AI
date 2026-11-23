"""The local language model, served by Ollama from a Hugging Face GGUF file.

Message contents are never logged and never placed in exceptions.
"""

import json
import logging
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("medimatch.ai.llm")

T = TypeVar("T", bound=BaseModel)


class LLMUnavailableError(Exception):
    """The model could not answer."""


class LLMClient:
    def __init__(self, transport: httpx.BaseTransport | None = None):
        self._http = httpx.Client(
            base_url=settings.OLLAMA_URL,
            timeout=httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, connect=5.0),
            limits=httpx.Limits(keepalive_expiry=120),
            transport=transport,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        temperature: float = 0.8,
        schema: dict[str, Any] | None = None,
    ) -> str:
        body: dict[str, Any] = {
            "model": settings.LLM_MODEL,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "stream": False,
            "think": False,
            "keep_alive": "1h",
            "options": {
                "temperature": temperature,
                "num_ctx": settings.LLM_CONTEXT_TOKENS,
                "num_predict": settings.LLM_MAX_TOKENS,
            },
        }
        if schema:
            body["format"] = schema
        try:
            response = self._http.post("/api/chat", json=body)
            response.raise_for_status()
            content = response.json()["message"]["content"].strip()
        except (httpx.HTTPError, ValueError, KeyError) as e:
            raise LLMUnavailableError(type(e).__name__) from None
        if not content:
            raise LLMUnavailableError("Empty reply")
        return str(content)

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        system_prompt: str,
        response_model: type[T],
        schema: dict[str, Any] | None = None,
    ) -> T:
        """Ollama holds the model to the schema while it writes, so the JSON keeps its shape."""
        for _ in range(2):
            raw = self.generate(
                messages,
                system_prompt,
                temperature=0.1,
                schema=schema or response_model.model_json_schema(),
            )
            try:
                return response_model.model_validate(json.loads(raw))
            except ValueError:
                logger.warning(f"Model output did not parse as {response_model.__name__}")
        raise LLMUnavailableError("The model's answer could not be read")


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client


def set_llm_client(client: LLMClient | None) -> None:
    """Replaces the model in tests."""
    global _client
    _client = client
