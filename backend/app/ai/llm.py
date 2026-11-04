"""LLM Client Module for MediMatch AI.

OpenRouter wrapper (OpenAI-compatible API) with timeouts, retries,
and structured Pydantic response generation.
Crucial Rule: Message contents are NEVER logged, and never placed in exceptions.
"""

import json
import logging
import time
from typing import Any, Dict, List, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("medimatch.ai.llm")

T = TypeVar("T", bound=BaseModel)

RETRY_WAIT_SECONDS = 1.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}


class LLMUnavailable(Exception):
    """The provider could not produce a reply. Callers fall back to safe deterministic behaviour."""


class LLMClient:
    """Interface and implementation for OpenRouter LLM requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        transport: Optional[httpx.BaseTransport] = None,
    ):
        self.api_key = settings.OPENROUTER_API_KEY if api_key is None else api_key
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            timeout=httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, connect=5.0),
            transport=transport,
        )

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://medimatch.ai",
            "X-Title": "MediMatch AI Assistant",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _post(self, body: Dict[str, Any]) -> httpx.Response:
        """Sends one request, retrying only failures that can succeed on another attempt."""
        last_error = "no attempt made"
        for attempt in range(1, settings.LLM_MAX_ATTEMPTS + 1):
            try:
                resp = self._http.post(
                    f"{self.base_url}/chat/completions", headers=self._get_headers(), json=body
                )
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = type(e).__name__
            else:
                if resp.status_code < 400:
                    return resp
                last_error = f"HTTP {resp.status_code}"
                if resp.status_code not in RETRYABLE_STATUS:
                    break

            logger.warning(f"LLM attempt {attempt} failed: {last_error}")
            if attempt < settings.LLM_MAX_ATTEMPTS:
                time.sleep(RETRY_WAIT_SECONDS * attempt)

        raise LLMUnavailable(last_error)

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        """Sends chat completion request to OpenRouter and returns string reply."""
        if not self.api_key:
            raise LLMUnavailable("OPENROUTER_API_KEY is not set")

        logger.info(f"Submitting LLM request to model '{self.model}' with {len(messages)} messages")

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        body: Dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if settings.ENVIRONMENT == "production":
            body["provider"] = {"data_collection": "deny"}

        resp = self._post(body)
        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMUnavailable("Unexpected response shape") from e

        if not content or not content.strip():
            raise LLMUnavailable("Empty reply")

        logger.info("LLM completion received successfully")
        return content.strip()

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        """Generates structured output validated against a Pydantic schema."""
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        system_instruction = (
            f"{system_prompt or ''}\n\n"
            "You MUST respond ONLY with a valid JSON object conforming exactly to this JSON Schema:\n"
            f"{schema_json}\n"
            "Do not output markdown code blocks (```json), commentary, or any text other than raw JSON."
        ).strip()

        raw_output = self.generate(
            messages=messages,
            system_prompt=system_instruction,
            temperature=0.1,
        )

        # Clean possible markdown wrapping if the LLM provided it
        cleaned = raw_output.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

        try:
            return response_model.model_validate(json.loads(cleaned))
        except Exception:
            logger.warning(f"Structured output did not parse as {response_model.__name__}; attempting repair")

        try:
            import json_repair

            return response_model.model_validate(json_repair.repair_json(cleaned, return_objects=True))
        except Exception:
            raise ValueError(f"Failed to parse LLM structured output into {response_model.__name__}") from None


_DEFAULT_LLM_CLIENT: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Returns the default LLM client singleton, or initializes one."""
    global _DEFAULT_LLM_CLIENT
    if _DEFAULT_LLM_CLIENT is None:
        _DEFAULT_LLM_CLIENT = LLMClient()
    return _DEFAULT_LLM_CLIENT


def set_llm_client(client: Optional[LLMClient]) -> None:
    """Overrides the LLM client (used in testing for deterministic mocks)."""
    global _DEFAULT_LLM_CLIENT
    _DEFAULT_LLM_CLIENT = client
