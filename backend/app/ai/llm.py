"""LLM Client Module for MediMatch AI.

Groq wrapper (OpenAI-compatible API) with timeouts, retries,
and structured Pydantic response generation.
Crucial Rule: Message contents are NEVER logged, and never placed in exceptions.
"""

import json
import logging
import time
from types import UnionType
from typing import Any, Literal, TypeVar, Union, get_args, get_origin

import httpx
from pydantic import BaseModel

from app.core.config import settings

logger = logging.getLogger("medimatch.ai.llm")

T = TypeVar("T", bound=BaseModel)

RETRY_WAIT_SECONDS = 1.0
MAX_RETRY_WAIT_SECONDS = 10.0
RETRYABLE_STATUS = {429, 500, 502, 503, 504}
# Groq answers 400 when the model produces something it cannot parse, which a second try fixes
RETRYABLE_ERROR = b"output_parse_failed"


class LLMUnavailableError(Exception):
    """The provider could not produce a reply. Callers fall back to safe deterministic behaviour."""


def _retry_after(response: httpx.Response) -> float | None:
    """Reads how long a rate-limited provider asks us to wait, in seconds."""
    try:
        return max(float(response.headers.get("retry-after", "")), 0.0)
    except ValueError:
        return None


def _type_shape(annotation: Any) -> Any:
    """Describes one field in as few tokens as possible."""
    origin = get_origin(annotation)
    args = get_args(annotation)
    if origin is Literal:
        return "|".join(str(arg) for arg in args)
    if origin in (Union, UnionType):
        return " or ".join("null" if arg is type(None) else str(_type_shape(arg)) for arg in args)
    if origin is list:
        return [_type_shape(args[0])]
    if origin is dict:
        return f"object of {_type_shape(args[1])}"
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return response_shape(annotation)
    return getattr(annotation, "__name__", str(annotation))


def response_shape(model: type[BaseModel]) -> dict[str, Any]:
    """The reply's fields and types. Far smaller than a JSON Schema, which is sent every turn."""
    return {name: _type_shape(field.annotation) for name, field in model.model_fields.items()}


class LLMClient:
    """Interface and implementation for Groq LLM requests."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str = "https://api.groq.com/openai/v1",
        transport: httpx.BaseTransport | None = None,
    ):
        self.api_key = settings.GROQ_API_KEY if api_key is None else api_key
        self.model = model or settings.GROQ_MODEL
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            timeout=httpx.Timeout(settings.LLM_TIMEOUT_SECONDS, connect=5.0),
            transport=transport,
        )

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _read_within_deadline(self, body: dict[str, Any]) -> tuple[int, bytes, float | None]:
        """Sends a request and enforces a limit on the whole call.

        httpx's read timeout restarts with every chunk, so a provider that sends keep-alive bytes
        while a model is busy once held a call for two minutes under a 12 second read timeout.
        """
        deadline = time.monotonic() + settings.LLM_TIMEOUT_SECONDS
        url = f"{self.base_url}/chat/completions"
        with self._http.stream("POST", url, headers=self._get_headers(), json=body) as resp:
            chunks: list[bytes] = []
            for chunk in resp.iter_bytes():
                chunks.append(chunk)
                if time.monotonic() > deadline:
                    raise httpx.ReadTimeout("LLM call exceeded its deadline")
            return resp.status_code, b"".join(chunks), _retry_after(resp)

    def _post(self, body: dict[str, Any]) -> bytes:
        """Sends one request, retrying only failures that can succeed on another attempt."""
        last_error = "no attempt made"
        for attempt in range(1, settings.LLM_MAX_ATTEMPTS + 1):
            wait = RETRY_WAIT_SECONDS * attempt
            try:
                status_code, content, retry_after = self._read_within_deadline(body)
            except (httpx.TimeoutException, httpx.TransportError) as e:
                last_error = type(e).__name__
            else:
                if status_code < 400:
                    return content
                last_error = f"HTTP {status_code}"
                if status_code not in RETRYABLE_STATUS and RETRYABLE_ERROR not in content:
                    break
                if retry_after is not None:
                    if retry_after > MAX_RETRY_WAIT_SECONDS:
                        break
                    wait = retry_after

            logger.warning(f"LLM attempt {attempt} failed: {last_error}")
            if attempt < settings.LLM_MAX_ATTEMPTS:
                time.sleep(wait)

        raise LLMUnavailableError(last_error)

    def generate(
        self,
        messages: list[dict[str, str]],
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
        reasoning_effort: str | None = None,
    ) -> str:
        """Sends a chat completion request to Groq and returns the reply text."""
        if not self.api_key:
            raise LLMUnavailableError("GROQ_API_KEY is not set")

        logger.info(f"Submitting LLM request to model '{self.model}' with {len(messages)} messages")

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        body: dict[str, Any] = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if reasoning_effort:
            body["reasoning_effort"] = reasoning_effort

        raw = self._post(body)
        try:
            content = json.loads(raw)["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise LLMUnavailableError("Unexpected response shape") from e

        if not content or not content.strip():
            raise LLMUnavailableError("Empty reply")

        logger.info("LLM completion received successfully")
        return content.strip()

    def generate_structured(
        self,
        messages: list[dict[str, str]],
        response_model: type[T],
        system_prompt: str | None = None,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
    ) -> T:
        """Generates structured output validated against a Pydantic schema."""
        shape = json.dumps(response_shape(response_model), separators=(",", ":"))
        system_instruction = (
            f"{system_prompt or ''}\n\n"
            f"Respond ONLY with one JSON object of this shape:\n{shape}\n"
            "No markdown, commentary or any text other than raw JSON."
        ).strip()

        raw_output = self.generate(
            messages=messages,
            system_prompt=system_instruction,
            temperature=settings.LLM_TEMPERATURE if temperature is None else temperature,
            reasoning_effort=reasoning_effort,
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
            logger.warning(
                f"Structured output did not parse as {response_model.__name__}; attempting repair"
            )

        try:
            import json_repair

            return response_model.model_validate(
                json_repair.repair_json(cleaned, return_objects=True)
            )
        except Exception:
            raise ValueError(
                f"Failed to parse LLM structured output into {response_model.__name__}"
            ) from None


_DEFAULT_LLM_CLIENT: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Returns the default LLM client singleton, or initializes one."""
    global _DEFAULT_LLM_CLIENT
    if _DEFAULT_LLM_CLIENT is None:
        _DEFAULT_LLM_CLIENT = LLMClient()
    return _DEFAULT_LLM_CLIENT


def set_llm_client(client: LLMClient | None) -> None:
    """Overrides the LLM client (used in testing for deterministic mocks)."""
    global _DEFAULT_LLM_CLIENT
    _DEFAULT_LLM_CLIENT = client
