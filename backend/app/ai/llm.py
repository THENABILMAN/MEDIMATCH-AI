"""LLM Client Module for MediMatch AI.

OpenRouter wrapper (OpenAI-compatible API) with timeouts, retries,
and structured Pydantic response generation.
Crucial Rule: Message contents are NEVER logged at INFO level.
"""

import json
import logging
from typing import Any, Dict, List, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential
from app.core.config import settings

logger = logging.getLogger("medimatch.ai.llm")

T = TypeVar("T", bound=BaseModel)


class LLMClient:
    """Interface and implementation for OpenRouter LLM requests."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: str = "https://openrouter.ai/api/v1",
        timeout_seconds: float = 30.0,
    ):
        self.api_key = api_key or settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "HTTP-Referer": "https://medimatch.ai",
            "X-Title": "MediMatch AI Assistant",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    @retry(
        retry=retry_if_exception_type((httpx.NetworkError, httpx.TimeoutException)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=4),
        reraise=True,
    )
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 1000,
    ) -> str:
        """Sends chat completion request to OpenRouter and returns string reply."""
        # Clean logging: do NOT log prompt contents at INFO level
        logger.info(f"Submitting LLM request to model '{self.model}' with {len(messages)} messages")

        payload_messages = []
        if system_prompt:
            payload_messages.append({"role": "system", "content": system_prompt})
        payload_messages.extend(messages)

        body = {
            "model": self.model,
            "messages": payload_messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(
                f"{self.base_url}/chat/completions",
                headers=self._get_headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
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
            parsed_dict = json.loads(cleaned)
            return response_model.model_validate(parsed_dict)
        except Exception as e:
            logger.warning(f"Structured JSON parsing failed, attempting repair: {e}")
            # Try parsing with json_repair if available
            try:
                import json_repair
                repaired = json_repair.repair_json(cleaned, return_objects=True)
                return response_model.model_validate(repaired)
            except Exception:
                raise ValueError(f"Failed to parse LLM structured output into {response_model.__name__}: {cleaned}")


_DEFAULT_LLM_CLIENT: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """Returns the default LLM client singleton, or initializes one."""
    global _DEFAULT_LLM_CLIENT
    if _DEFAULT_LLM_CLIENT is None:
        _DEFAULT_LLM_CLIENT = LLMClient()
    return _DEFAULT_LLM_CLIENT


def set_llm_client(client: LLMClient) -> None:
    """Overrides the LLM client (used in testing for deterministic mocks)."""
    global _DEFAULT_LLM_CLIENT
    _DEFAULT_LLM_CLIENT = client
