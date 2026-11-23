"""A scripted model, so tests never call a real one."""

from typing import Any

from app.ai.llm import LLMClient
from app.ai.state import Assessment


def assessment(**fields: Any) -> Assessment:
    blank = {
        "language": "English",
        "has_health_problem": bool(fields.get("findings")),
        "new_findings": [],
        "city": None,
        "max_fee": None,
        "wants_doctors_now": False,
        "possible_conditions": [],
        "confidence": 0,
        "specialty": None,
        "next_question": "When did it start?",
        "answer_options": [],
    }
    if "findings" in fields:
        fields["new_findings"] = fields.pop("findings")
    return Assessment(**(blank | fields))


class ScriptedLLM(LLMClient):
    """Gives each assessment in turn, repeating the last, and records every prompt."""

    def __init__(self, *assessments: Assessment, reply: str = "Tell me more."):
        super().__init__()
        self.assessments = list(assessments) or [assessment()]
        self.reply = reply
        self.assess_prompts: list[str] = []
        self.reply_prompts: list[str] = []
        self.schemas: list[dict[str, Any] | None] = []

    def generate_structured(self, messages, system_prompt, response_model, schema=None) -> Any:
        self.assess_prompts.append(system_prompt)
        self.schemas.append(schema)
        return self.assessments.pop(0) if len(self.assessments) > 1 else self.assessments[0]

    def generate(self, messages, system_prompt, temperature=0.8, schema=None) -> str:
        self.reply_prompts.append(system_prompt)
        return self.reply


class NoModel(LLMClient):
    """Fails the test if the model runs."""

    def generate(self, *_args, **_kwargs) -> str:
        raise AssertionError("This turn must not call a model")
