"""A scripted model for both steps of a turn, so tests never call a real provider."""

from typing import Any

from app.ai.llm import LLMClient
from app.ai.state import TurnAnalysis, WriterTurn


class ScriptedLLM(LLMClient):
    """Returns the next scripted step, and records everything it was sent.

    The last script of each kind repeats, so short scripts can cover long conversations.
    """

    def __init__(
        self,
        analyses: list[TurnAnalysis] | TurnAnalysis | None = None,
        replies: list[WriterTurn | str] | str | None = None,
    ):
        super().__init__(api_key="mock", model="mock")
        self.analyses = analyses if isinstance(analyses, list) else [analyses or TurnAnalysis()]
        self.replies = replies if isinstance(replies, list) else [replies or "Tell me more."]
        self.prompts: list[str] = []
        self.sent: list[list[dict[str, str]]] = []
        self.temperatures: list[float | None] = []

    def generate_structured(
        self, messages, response_model, system_prompt=None, temperature=None
    ) -> Any:
        self.prompts.append(system_prompt or "")
        self.sent.append(messages)
        self.temperatures.append(temperature)
        if response_model is TurnAnalysis:
            return self.analyses.pop(0) if len(self.analyses) > 1 else self.analyses[0]
        reply = self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]
        return WriterTurn(reply=reply) if isinstance(reply, str) else reply

    @property
    def writer_prompts(self) -> list[str]:
        return [prompt for prompt in self.prompts if "Notes for this turn" in prompt]


class NoModel(LLMClient):
    """Fails the test if any model step runs."""

    def __init__(self):
        super().__init__(api_key="mock", model="mock")

    def generate_structured(
        self, messages, response_model, system_prompt=None, temperature=None
    ) -> Any:
        raise AssertionError("This turn must not call a model")


def analysis(**fields: Any) -> TurnAnalysis:
    return TurnAnalysis(**fields)
