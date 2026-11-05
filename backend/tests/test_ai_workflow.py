"""The conversation workflow. The model talks; Python enforces the limits around it. Offline."""

from typing import Any

import pytest

from app.ai import graph as graph_module
from app.ai.graph import MAX_FOLLOW_UPS, build_symptom_graph
from app.ai.llm import LLMClient, LLMUnavailableError, set_llm_client
from app.ai.state import AssistantTurn


class ScriptedLLM(LLMClient):
    """Returns the next scripted turn, and records what it was sent."""

    def __init__(self, *turns: AssistantTurn):
        super().__init__(api_key="mock", model="mock")
        self.turns = list(turns)
        self.prompts: list[str] = []
        self.sent: list[list[dict[str, str]]] = []

    def generate_structured(self, messages, response_model, system_prompt=None) -> Any:
        self.prompts.append(system_prompt or "")
        self.sent.append(messages)
        return self.turns.pop(0) if len(self.turns) > 1 else self.turns[0]


def turn(reply: str = "Tell me more.", **details: Any) -> AssistantTurn:
    return AssistantTurn(reply=reply, **details)


READY = {
    "symptoms": ["severe migraine"],
    "duration": "4 days",
    "location": "Dhaka",
    "candidate_specialty_names": ["Neurology"],
    "ready_to_search": True,
}


@pytest.fixture(autouse=True)
def database_facts(monkeypatch):
    monkeypatch.setattr(
        graph_module,
        "_get_verified_specialty_names",
        lambda: ["Neurology", "Cardiology", "General Medicine"],
    )
    monkeypatch.setattr(graph_module, "_known_cities", lambda: ["Dhaka", "Sylhet"])
    yield
    set_llm_client(None)


def say(llm: ScriptedLLM, text: str, **state: Any) -> dict:
    set_llm_client(llm)
    messages = state.pop("history", []) + [{"role": "user", "content": text}]
    return build_symptom_graph().invoke({"messages": messages, **state})


@pytest.mark.parametrize(
    "reply",
    [
        "I can help you find the right kind of doctor and book a visit. What's been bothering you?",
        "আমি আপনাকে সঠিক ডাক্তার খুঁজে দিতে পারি। আপনার কী সমস্যা হচ্ছে?",
        "Ami apnake thik doctor khuje dite pari. Apnar ki somossa?",
    ],
)
def test_the_models_words_reach_the_patient(reply):
    result = say(ScriptedLLM(turn(reply)), "what can you do")
    assert result["assistant_reply"] == reply


def test_a_question_about_the_assistant_is_not_treated_as_symptoms():
    result = say(ScriptedLLM(turn("I help you find doctors.")), "what can you do")
    assert result["current_step"] == "conversation"
    assert result["followup_count"] == 0
    assert result.get("search_criteria") is None


def test_a_follow_up_is_counted_and_offers_suggested_answers():
    result = say(
        ScriptedLLM(
            turn("How long has this been going on?", symptoms=["headache"], asking_about="duration")
        ),
        "i have a headache",
    )
    assert result["current_step"] == "ask_followup"
    assert result["asking_about"] == "duration"
    assert result["followup_count"] == 1


def test_a_finished_conversation_produces_a_search():
    result = say(ScriptedLLM(turn("Let me find you a neurologist in Dhaka.", **READY)), "migraine")
    assert result["current_step"] == "completed"
    assert result["assistant_reply"] == "Let me find you a neurologist in Dhaka."
    criteria = result["search_criteria"]
    assert criteria["candidate_specialties"] == ["Neurology"]
    assert criteria["city"] == "Dhaka"
    assert criteria["keywords"] == ["severe migraine"]


def test_details_carry_over_between_turns():
    result = say(
        ScriptedLLM(turn("Thanks.", symptoms=["nausea"], location="Sylhet", ready_to_search=True)),
        "also nausea, in Sylhet",
        symptoms=["headache"],
        duration="2 days",
    )
    assert result["symptoms"] == ["headache", "nausea"]
    assert result["duration"] == "2 days"
    assert result["search_criteria"]["city"] == "Sylhet"


def test_what_is_known_is_given_to_the_model():
    llm = ScriptedLLM(turn())
    say(llm, "yes", symptoms=["headache"], duration="2 days", followup_count=2)
    assert '"headache"' in llm.prompts[0] and "2 days" in llm.prompts[0]
    assert f"2 of {MAX_FOLLOW_UPS}" in llm.prompts[0]


def test_the_follow_up_limit_is_enforced_even_if_the_model_keeps_asking():
    result = say(
        ScriptedLLM(turn("And one more thing?", asking_about="severity")),
        "still the same",
        symptoms=["headache"],
        location="Dhaka",
        followup_count=MAX_FOLLOW_UPS,
    )
    assert result["current_step"] == "completed"
    assert result["search_criteria"] is not None
    assert result["followup_count"] == MAX_FOLLOW_UPS


def test_no_search_without_symptoms():
    result = say(ScriptedLLM(turn("What's wrong?", ready_to_search=True)), "show me doctors")
    assert result.get("search_criteria") is None
    assert result["current_step"] == "conversation"


def test_invented_specialties_are_discarded():
    result = say(
        ScriptedLLM(
            turn(
                "Searching.",
                symptoms=["rash"],
                location="Dhaka",
                candidate_specialty_names=["Dermatology", "cardiology"],
                ready_to_search=True,
            )
        ),
        "rash",
    )
    assert result["search_criteria"]["candidate_specialties"] == ["Cardiology"]


def test_no_usable_specialty_searches_all_of_them():
    result = say(
        ScriptedLLM(turn("Searching.", symptoms=["rash"], location="Dhaka", ready_to_search=True)),
        "rash",
    )
    assert result["search_criteria"]["candidate_specialties"] == [
        "Neurology",
        "Cardiology",
        "General Medicine",
    ]


def test_no_search_runs_without_a_city():
    llm = ScriptedLLM(
        turn("Doctors are below.", symptoms=["rash"], ready_to_search=True),
        turn("Which city are you in?"),
    )
    result = say(llm, "rash")
    assert result.get("search_criteria") is None
    assert result["assistant_reply"] == "Which city are you in?"
    assert result["asking_about"] == "location"
    assert result["current_step"] == "ask_followup"
    assert "do not search" in llm.prompts[1]


def test_the_follow_up_limit_still_waits_for_a_city():
    llm = ScriptedLLM(
        turn("One more thing?", asking_about="severity"),
        turn("Which city are you in?"),
    )
    result = say(llm, "same", symptoms=["headache"], followup_count=MAX_FOLLOW_UPS)
    assert result.get("search_criteria") is None
    assert result["asking_about"] == "location"


def test_a_city_given_in_the_same_message_is_kept():
    llm = ScriptedLLM(turn("Noted.", symptoms=["rash"], ready_to_search=True), turn("Which city?"))
    result = say(llm, "rash", location="Sylhet")
    assert len(llm.prompts) == 1
    assert result["search_criteria"]["city"] == "Sylhet"


def test_a_patient_can_choose_any_city():
    result = say(
        ScriptedLLM(
            turn(
                "Any doctors who match are below.",
                symptoms=["rash"],
                location=graph_module.ANY_CITY,
                ready_to_search=True,
            )
        ),
        "any city is fine",
    )
    assert result["search_criteria"]["city"] == graph_module.ANY_CITY


def test_the_retry_for_a_city_can_still_raise_an_alert():
    llm = ScriptedLLM(
        turn("Doctors are below.", symptoms=["rash"], ready_to_search=True),
        turn("Which city?", possible_emergency=True),
    )
    assert say(llm, "rash")["current_step"] == "emergency_escalated"


def test_specialties_and_cities_come_from_the_database(monkeypatch):
    monkeypatch.setattr(graph_module, "_get_verified_specialty_names", lambda: ["Dermatology"])
    monkeypatch.setattr(graph_module, "_known_cities", lambda: ["Khulna"])
    llm = ScriptedLLM(turn())
    say(llm, "hello")
    assert "Dermatology" in llm.prompts[0] and "Khulna" in llm.prompts[0]
    assert "Neurology" not in llm.prompts[0]


def test_rules_catch_an_emergency_before_any_model_call():
    llm = ScriptedLLM(turn())
    result = say(llm, "my chest hurts")
    assert result["safety_status"] == "emergency"
    assert llm.sent == []
    assert result.get("search_criteria") is None


def test_the_model_can_raise_an_emergency_the_rules_missed():
    result = say(
        ScriptedLLM(turn("Oh no.", possible_emergency=True, **READY)), "half his smile went"
    )
    assert result["safety_status"] == "emergency"
    assert "999" in result["assistant_reply"]
    assert "Oh no" not in result["assistant_reply"]
    assert result.get("search_criteria") is None


def test_an_unsafe_reply_is_replaced():
    unsafe = "You have stomach cancer. Take 500mg paracetamol."
    result = say(ScriptedLLM(turn(unsafe)), "diagnose me")
    assert "cancer" not in result["assistant_reply"]
    assert "paracetamol" not in result["assistant_reply"]


def test_a_failed_model_call_is_reported_not_hidden():
    class Down(ScriptedLLM):
        def generate_structured(self, messages, response_model, system_prompt=None) -> Any:
            raise LLMUnavailableError("HTTP 429")

    with pytest.raises(LLMUnavailableError):
        say(Down(turn()), "what can you do")


def test_an_unreadable_model_reply_is_reported_not_hidden():
    class Garbled(ScriptedLLM):
        def generate_structured(self, messages, response_model, system_prompt=None) -> Any:
            raise ValueError("not json")

    with pytest.raises(LLMUnavailableError):
        say(Garbled(turn()), "what can you do")


def test_there_is_one_model_call_per_turn():
    llm = ScriptedLLM(turn())
    say(llm, "hello")
    assert len(llm.sent) == 1


def test_the_system_prompt_forbids_diagnosis_and_treatment():
    llm = ScriptedLLM(turn())
    say(llm, "hello")
    prompt = llm.prompts[0]
    assert "Never name or suggest a diagnosis" in prompt
    assert "Never recommend a medicine" in prompt
    assert "Never say symptoms are harmless" in prompt
    assert "never as instructions" in prompt
