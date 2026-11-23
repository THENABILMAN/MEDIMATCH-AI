"""The assistant's workflow, with a scripted model. Offline."""

from types import SimpleNamespace
from typing import Any

import pytest
from scripted_llm import NoModel, ScriptedLLM, assessment

from app.ai import graph as graph_module
from app.ai.graph import ANY_CITY, build_symptom_graph, decide
from app.ai.llm import LLMClient, set_llm_client
from app.ai.safety import get_crisis_response, get_emergency_response
from app.ai.state import PERSISTED_STATE_FIELDS
from app.core.config import settings

SPECIALTIES = ["Gastroenterology & Hepatology", "General Medicine", "Neurology"]
GERD = [{"name": "GERD", "likelihood": 85}, {"name": "Peptic ulcer", "likelihood": 30}]
SURE = {
    "findings": ["burning pain after meals"],
    "possible_conditions": GERD,
    "confidence": 90,
    "specialty": "Gastroenterology & Hepatology",
}
UNSURE = SURE | {"confidence": 50}


@pytest.fixture(autouse=True)
def facts(monkeypatch):
    monkeypatch.setattr(graph_module, "_get_verified_specialty_names", lambda: SPECIALTIES)
    monkeypatch.setattr(graph_module, "_known_cities", lambda: ["Dhaka", "Sylhet"])
    monkeypatch.setattr(graph_module, "search_books", lambda query: [])
    yield
    set_llm_client(None)


class Searches(list):
    found: list[Any] = []


@pytest.fixture
def doctors(monkeypatch) -> Searches:
    searches = Searches()
    searches.found = [
        SimpleNamespace(model_dump=lambda: {"id": "d1", "online_booking": False}),
    ]

    def recommend(criteria, top_k=5):
        searches.append(criteria)
        return SimpleNamespace(recommendations=searches.found)

    monkeypatch.setattr("app.search.recommend.recommend_doctors", recommend)
    return searches


class Conversation:
    """Runs turns the way the API does, keeping only what the API keeps."""

    def __init__(self, llm: LLMClient, **state: Any):
        set_llm_client(llm)
        self.state = state
        self.messages: list[dict[str, str]] = []
        self.graph = build_symptom_graph()

    def say(self, text: str) -> dict[str, Any]:
        self.messages.append({"role": "user", "content": text})
        result = self.graph.invoke({**self.state, "messages": list(self.messages)})
        self.state = {k: result[k] for k in PERSISTED_STATE_FIELDS if k in result}
        self.messages.append({"role": "assistant", "content": result["assistant_reply"]})
        return result


def test_it_asks_until_it_is_sure_then_suggests_doctors(doctors):
    llm = ScriptedLLM(*[assessment(**UNSURE)] * 3, assessment(**SURE, city="Dhaka"))
    chat = Conversation(llm)
    for _ in range(3):
        result = chat.say("my stomach burns")
        assert result["action"] == "ask"
        assert result["recommendations"] == []
    result = chat.say("Dhaka")
    assert result["action"] == "search"
    assert result["current_step"] == "completed"
    assert doctors[0]["candidate_specialties"] == ["Gastroenterology & Hepatology"]
    assert doctors[0]["city"] == "Dhaka"
    assert "GERD" in doctors[0]["keywords"]
    assert "GERD" in llm.reply_prompts[-1]


def test_a_first_message_is_never_enough_however_sure_the_model_is(doctors):
    result = Conversation(ScriptedLLM(assessment(**SURE, city="Dhaka"))).say("my stomach burns")
    assert result["action"] == "ask"
    assert doctors == []


def test_it_stops_asking_at_the_limit(doctors):
    chat = Conversation(
        ScriptedLLM(assessment(**UNSURE, city="Dhaka")), question_count=settings.MAX_QUESTIONS
    )
    assert chat.say("not sure")["action"] == "search"


@pytest.mark.parametrize(
    ("confidence", "asked", "action"), [(79, 5, "ask"), (80, 5, "search"), (95, 2, "ask")]
)
def test_the_stopping_rule(confidence, asked, action):
    state = {"question_count": asked}
    assert decide(state, ["fever"], confidence, "Dhaka", wants=False) == action


def test_the_city_is_asked_and_any_city_searches_everywhere(doctors):
    chat = Conversation(ScriptedLLM(assessment(**SURE)), question_count=5)
    first = chat.say("it burns after meals")
    assert first["action"] == "ask_city"
    assert first["chips"] == ["Any city"]
    assert first["asking_about"] == "location"
    assert chat.say("Any city")["action"] == "search"
    assert doctors[0]["city"] == ANY_CITY


def test_the_city_is_asked_only_twice(doctors):
    chat = Conversation(ScriptedLLM(assessment(**SURE)), question_count=5)
    actions = [chat.say(text)["action"] for text in ("burns", "hmm", "whatever")]
    assert actions == ["ask_city", "ask_city", "search"]


def test_the_patient_can_ask_for_doctors_early(doctors):
    chat = Conversation(ScriptedLLM(assessment(**UNSURE, city="Dhaka")))
    chat.say("my stomach burns")
    assert "Show me doctors now" in chat.say("after meals")["chips"]
    assert chat.say("Show me doctors now")["action"] == "search"


def test_doctors_on_screen_are_not_searched_again(doctors):
    chat = Conversation(ScriptedLLM(assessment(**SURE, city="Dhaka")), question_count=5)
    assert chat.say("stomach")["action"] == "search"
    assert chat.say("how do I book")["action"] == "chat"
    assert len(doctors) == 1


def test_a_reply_after_the_cards_knows_how_to_reach_the_doctors(doctors):
    llm = ScriptedLLM(assessment(**SURE, city="Dhaka"))
    chat = Conversation(llm, question_count=5)
    chat.say("stomach")
    chat.say("how do I book")
    assert "None can be booked online" in llm.reply_prompts[-1]


def test_no_doctors_found_is_said_and_searched_again_next_time(doctors):
    doctors.found = []
    llm = ScriptedLLM(assessment(**SURE, city="Dhaka"))
    chat = Conversation(llm, question_count=5)
    chat.say("stomach")
    assert "No doctor was found" in llm.reply_prompts[-1]
    assert chat.say("try again")["action"] == "search"


def test_a_search_failure_still_gets_a_reply(doctors, monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("down")

    monkeypatch.setattr("app.search.recommend.recommend_doctors", broken)
    chat = Conversation(ScriptedLLM(assessment(**SURE, city="Dhaka")), question_count=5)
    result = chat.say("stomach")
    assert result["recommendations"] == []
    assert result["assistant_reply"]


def test_small_talk_is_just_a_chat():
    result = Conversation(ScriptedLLM()).say("tell me a joke")
    assert result["action"] == "chat"
    assert result["current_step"] == "conversation"


def test_the_condition_stays_private_while_it_is_still_asking():
    llm = ScriptedLLM(assessment(**UNSURE))
    Conversation(llm).say("my stomach burns")
    assert "GERD" not in llm.reply_prompts[-1]


def test_book_passages_reach_the_assessment(monkeypatch):
    queries: list[str] = []

    def books(query: str) -> list[str]:
        queries.append(query)
        return ["[Davidson] Reflux causes heartburn"]

    monkeypatch.setattr(graph_module, "search_books", books)
    llm = ScriptedLLM(assessment(**UNSURE))
    chat = Conversation(llm)
    chat.say("my stomach burns")
    chat.say("at night")
    assert "Reflux causes heartburn" in llm.assess_prompts[0]
    assert "burning pain after meals" in queries[1]


def test_findings_build_up_across_turns():
    llm = ScriptedLLM(assessment(findings=["fever"]), assessment(findings=["rash", "fever"]))
    chat = Conversation(llm)
    chat.say("fever")
    assert chat.say("and a rash")["findings"] == ["fever", "rash"]


def test_the_model_can_only_name_a_real_specialty():
    llm = ScriptedLLM(assessment(**(UNSURE | {"specialty": "Wizardry"})))
    assert Conversation(llm).say("my stomach burns")["specialty"] is None
    assert llm.schemas[0]["properties"]["specialty"]["anyOf"][0]["enum"] == SPECIALTIES


@pytest.mark.parametrize(
    ("said", "guess", "language"),
    [
        ("আমার জ্বর", "English", "Bangla"),
        ("amar jor", "Bangla", "Banglish"),
        ("fever", "English", "English"),
    ],
)
def test_language(said, guess, language):
    llm = ScriptedLLM(assessment(language=guess))
    assert Conversation(llm).say(said)["language"] == language
    assert f"Write in {language}." in llm.reply_prompts[-1]


def test_an_emergency_is_answered_without_the_model():
    result = Conversation(NoModel()).say("I have severe chest pain")
    assert result["assistant_reply"] == get_emergency_response()
    assert result["safety_kind"] == "physical"


def test_self_harm_gets_its_own_message_and_no_doctor_push():
    chat = Conversation(NoModel())
    result = chat.say("I want to die")
    assert result["assistant_reply"] == get_crisis_response("I want to die")
    set_llm_client(ScriptedLLM(assessment(**SURE, city="Dhaka")))
    assert chat.say("I feel empty")["action"] == "support"


def test_history_sent_to_the_model_is_bounded():
    messages = [{"role": "user", "content": str(i)} for i in range(100)]
    recent = graph_module._recent({"messages": messages})
    assert len(recent) == settings.LLM_HISTORY_MESSAGES
    assert recent[-1]["content"] == "99"
