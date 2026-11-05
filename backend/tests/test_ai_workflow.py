"""The conversation workflow. The model reads and writes; Python decides. Offline."""

import logging
from types import SimpleNamespace
from typing import Any

import pytest
from scripted_llm import NoModel, ScriptedLLM, analysis

from app.ai import graph as graph_module
from app.ai.graph import ESCAPE, build_symptom_graph, repeated_sentences
from app.ai.llm import LLMClient, LLMUnavailableError, set_llm_client
from app.ai.routing import ANY_CITY, EMOTIONAL_SPECIALTIES
from app.ai.safety import get_crisis_response, get_emergency_response, guard_fallback
from app.ai.state import PERSISTED_STATE_FIELDS, TurnAnalysis, WriterChip, WriterTurn
from app.core.config import settings
from app.search.recommend import _fits_request

VERIFIED = [
    "Neurology",
    "Cardiology",
    "General Medicine",
    "Psychiatry",
    "Clinical Psychology",
    "Counselling",
]
CONFIDENT = {"Neurology": 0.9, "General Medicine": 0.2}
HEADACHE = {
    "symptoms": ["headache"],
    "duration": "3 days",
    "location": "Dhaka",
    "urgency": "routine",
    "specialty_confidence": CONFIDENT,
}
STILL_UNSURE = {"symptoms": ["headache"], "location": "Dhaka", "urgency": "routine"}
HEARTBREAK = {
    "symptoms": ["breakup"],
    "duration": "2 weeks",
    "location": "Dhaka",
    "urgency": "routine",
    "care_preference": "talking",
    "specialty_confidence": {"Counselling": 0.8, "General Medicine": 0.3},
}


@pytest.fixture(autouse=True)
def database_facts(monkeypatch):
    monkeypatch.setattr(graph_module, "_get_verified_specialty_names", lambda: VERIFIED)
    monkeypatch.setattr(graph_module, "_known_cities", lambda: ["Dhaka", "Sylhet"])
    yield
    set_llm_client(None)


class Searches(list):
    """What the recommender was asked. It finds one doctor unless a test empties `found`."""

    def __init__(self):
        super().__init__()
        self.found = [SimpleNamespace(model_dump=lambda: {"id": "d1"})]


@pytest.fixture
def doctors(monkeypatch) -> Searches:
    searches = Searches()

    def recommend(criteria, top_k=5):
        searches.append(criteria)
        return SimpleNamespace(recommendations=searches.found)

    monkeypatch.setattr("app.search.recommend.recommend_doctors", recommend)
    return searches


class Conversation:
    """Runs turns the way the API does, keeping only what the API keeps."""

    def __init__(self, llm: LLMClient, **state: Any):
        set_llm_client(llm)
        self.state = dict(state)
        self.messages: list[dict[str, str]] = state.pop("history", [])
        self.state.pop("history", None)
        self.graph = build_symptom_graph()

    def say(self, text: str) -> dict:
        self.messages.append({"role": "user", "content": text})
        result = self.graph.invoke({**self.state, "messages": list(self.messages)})
        self.state = {k: result[k] for k in PERSISTED_STATE_FIELDS if k in result}
        self.messages.append({"role": "assistant", "content": result["assistant_reply"]})
        return result


def say(llm: LLMClient, text: str, **state: Any) -> dict:
    return Conversation(llm, **state).say(text)


# ------------------------------------------------------------------------------
# The two steps
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "reply",
    [
        "I can help you find the right kind of doctor. What's been going on?",
        "আমি আপনাকে সঠিক ডাক্তার খুঁজে দিতে পারি। কী হচ্ছে?",
    ],
)
def test_the_writers_words_reach_the_patient(reply):
    assert say(ScriptedLLM(replies=reply), "what can you do")["assistant_reply"] == reply


def test_every_normal_turn_runs_the_analysis_then_the_writer():
    llm = ScriptedLLM()
    say(llm, "hello")
    assert len(llm.prompts) == 2
    assert "You read a conversation" in llm.prompts[0]
    assert "MediMatch assistant persona" in llm.prompts[1]


def test_the_writer_runs_warmer_than_the_analysis():
    llm = ScriptedLLM()
    say(llm, "hello")
    assert llm.temperatures[0] is None
    assert llm.temperatures[1] == settings.LLM_WRITER_TEMPERATURE


def test_the_analysis_never_reaches_the_patient(doctors):
    secret = "patient seems to be avoiding the question"
    llm = ScriptedLLM(analysis(symptoms=[secret], answer_basis=[secret]), replies="How long?")
    result = say(llm, "headache")
    assert secret not in result["assistant_reply"]


def test_every_call_is_redacted():
    llm = ScriptedLLM(replies="Thanks.")
    say(llm, "My name is Rahim Uddin, 01712345678, rahim@gmail.com")
    for sent in llm.sent:
        assert "01712345678" not in str(sent) and "rahim@gmail.com" not in str(sent)


def test_a_failed_model_in_either_step_is_reported_not_hidden():
    class FailsOnWriter(ScriptedLLM):
        def generate_structured(
            self, messages, response_model, system_prompt=None, temperature=None
        ):
            if response_model is WriterTurn:
                raise LLMUnavailableError("down")
            return super().generate_structured(messages, response_model, system_prompt)

    with pytest.raises(LLMUnavailableError):
        say(FailsOnWriter(), "hello")


def test_an_unreadable_analysis_is_reported_not_hidden():
    class Unreadable(ScriptedLLM):
        def generate_structured(
            self, messages, response_model, system_prompt=None, temperature=None
        ):
            raise ValueError("bad json")

    with pytest.raises(LLMUnavailableError):
        say(Unreadable(), "hello")


# ------------------------------------------------------------------------------
# Ambiguity: "broken heart"
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "phrase",
    [
        "I have a broken heart",
        "my heart hurts",
        "my chest feels heavy",
        "feeling empty",
        "my heart is racing",
        "burning inside",
        "আমার মন ভেঙে গেছে",
        "mon bhenge geche",
    ],
)
def test_an_ambiguous_phrase_gets_a_question_even_if_the_model_misses_it(phrase, doctors):
    # This model is sure of a specialty and sees no ambiguity. Python still waits
    llm = ScriptedLLM(analysis(**HEADACHE))
    result = say(llm, phrase)
    assert result["asking_about"] == "clarify_meaning"
    assert result.get("search_criteria") is None
    assert doctors == []
    assert "clarify_meaning" in llm.writer_prompts[0]


def test_the_model_can_flag_an_ambiguity_the_list_misses(doctors):
    llm = ScriptedLLM(analysis(**HEADACHE, ambiguous_phrases=["a_stone_on_my_chest"]))
    assert say(llm, "there is a stone on me")["asking_about"] == "clarify_meaning"
    assert doctors == []


def test_clarifying_chips_reach_the_response():
    chips = [
        WriterChip(label="Emotional pain", meaning="emotional"),
        WriterChip(label="Physical chest pain", meaning="physical"),
        WriterChip(label="Both", meaning="both"),
    ]
    llm = ScriptedLLM(analysis(symptoms=["heartbreak"]), WriterTurn(reply="Which?", chips=chips))
    result = say(llm, "I have a broken heart")
    assert result["chips"][:3] == ["Emotional pain", "Physical chest pain", "Both"]


def asked_about_a_broken_heart(llm: LLMClient) -> Conversation:
    conversation = Conversation(llm)
    conversation.say("I have a broken heart")
    return conversation


CLARIFYING = WriterTurn(
    reply="Do you mean an emotional loss, or pain in your chest?",
    chips=[
        WriterChip(label="Emotional", meaning="emotional"),
        WriterChip(label="In my chest", meaning="physical"),
        WriterChip(label="Both", meaning="both"),
    ],
)


@pytest.mark.parametrize("label", ["In my chest", "Both", "both"])
def test_a_tapped_physical_answer_gets_the_alert_with_no_model(label):
    conversation = asked_about_a_broken_heart(
        ScriptedLLM(analysis(symptoms=["heartbreak"]), CLARIFYING)
    )
    set_llm_client(NoModel())
    result = conversation.say(label)
    assert result["safety_status"] == "emergency"
    assert result["safety_kind"] == "physical"
    assert result["assistant_reply"] == get_emergency_response()
    assert not result["recommendations"]


def test_a_typed_physical_answer_gets_the_alert():
    llm = ScriptedLLM(
        [analysis(symptoms=["heartbreak"]), analysis(ambiguity_answer="physical")], CLARIFYING
    )
    conversation = asked_about_a_broken_heart(llm)
    result = conversation.say("it really aches behind my ribs")
    assert result["safety_kind"] == "physical"
    assert result["assistant_reply"] == get_emergency_response()


def test_an_emotional_answer_moves_on_to_emotional_care(doctors):
    llm = ScriptedLLM(
        [analysis(symptoms=["heartbreak"]), analysis(**HEARTBREAK)], [CLARIFYING, "Noted."]
    )
    conversation = asked_about_a_broken_heart(llm)
    result = conversation.say("Emotional")
    assert result["ambiguity_flags"]["broken_heart"] == "emotional"
    assert doctors[0]["candidate_specialties"] == ["Counselling"]


def test_a_physical_answer_to_a_non_chest_phrase_routes_normally():
    llm = ScriptedLLM(
        [analysis(symptoms=["empty feeling"]), analysis(ambiguity_answer="physical")], "How long?"
    )
    conversation = Conversation(llm)
    conversation.say("feeling empty")
    assert conversation.say("in my stomach")["safety_status"] == "safe"


def test_an_explained_phrase_is_not_asked_about_again():
    llm = ScriptedLLM(
        [analysis(symptoms=["heartbreak"]), analysis(ambiguity_answer="emotional")],
        ["Which?", "Thank you."],
    )
    conversation = Conversation(llm)
    conversation.say("my heart is broken")
    conversation.say("emotional")
    assert conversation.say("my heart is broken")["asking_about"] != "clarify_meaning"


def test_an_unclear_answer_is_asked_at_most_twice(doctors):
    llm = ScriptedLLM(analysis(**HEADACHE, ambiguity_answer=None), ["One?", "Two?", "Three."])
    conversation = Conversation(llm)
    assert conversation.say("my heart is broken")["asking_about"] == "clarify_meaning"
    assert conversation.say("hmm")["asking_about"] == "clarify_meaning"
    assert conversation.say("hmm")["asking_about"] != "clarify_meaning"


# ------------------------------------------------------------------------------
# Questions: no fixed cap, a soft limit, stopping when confident
# ------------------------------------------------------------------------------


def test_the_assistant_stops_as_soon_as_it_is_confident(doctors):
    result = say(ScriptedLLM(analysis(**HEADACHE)), "headache for 3 days in Dhaka")
    assert result["current_step"] == "completed"
    assert result["question_count"] == 0
    assert doctors[0]["candidate_specialties"] == ["Neurology"]


def test_two_close_specialties_mean_another_question(doctors):
    close = {**STILL_UNSURE, "specialty_confidence": {"Neurology": 0.7, "General Medicine": 0.6}}
    result = say(ScriptedLLM(analysis(**close, next_question="duration")), "headache")
    assert result["asking_about"] == "duration"
    assert doctors == []


def test_a_low_score_means_another_question(doctors):
    low = {**STILL_UNSURE, "specialty_confidence": {"Neurology": 0.5}}
    assert say(ScriptedLLM(analysis(**low, next_question="duration")), "x")["action"] == "ask"
    assert doctors == []


def test_with_nothing_left_to_ask_the_best_match_is_searched(doctors):
    close = {**HEADACHE, "specialty_confidence": {"Neurology": 0.6, "General Medicine": 0.5}}
    result = say(ScriptedLLM(analysis(**close)), "headache")
    assert result["search_reason"] == "out_of_questions"
    assert doctors[0]["candidate_specialties"] == ["Neurology", "General Medicine"]


def test_unknown_urgency_is_asked_before_stopping(doctors):
    unknown = {**HEADACHE, "urgency": "unknown"}
    assert say(ScriptedLLM(analysis(**unknown)), "headache")["asking_about"] == "severity"
    assert doctors == []


def test_the_thresholds_are_configurable(doctors, monkeypatch):
    monkeypatch.setattr(settings, "ROUTING_MIN_CONFIDENCE", 0.95)
    llm = ScriptedLLM(analysis(**{**STILL_UNSURE, "specialty_confidence": CONFIDENT}))
    assert say(llm, "headache")["current_step"] != "completed"


def test_there_is_no_cap_of_three_questions(doctors):
    llm = ScriptedLLM(analysis(symptoms=["tired"], next_question="duration"), "And then?")
    result = say(llm, "still tired", question_count=7, asked_questions=[])
    assert result["action"] == "ask"
    assert result["question_count"] == 8
    assert doctors == []


def test_the_soft_limit_offers_matches_and_asks_to_continue(doctors):
    llm = ScriptedLLM(analysis(**{**HEADACHE, "specialty_confidence": {"Neurology": 0.5}}))
    limit = settings.CONVERSATION_SOFT_QUESTION_LIMIT
    result = say(llm, "same", question_count=limit)
    assert result["soft_limit_reached"] is True
    assert result["current_step"] == "completed"
    assert "keep narrowing" in llm.writer_prompts[0]
    assert len(doctors) == 1


def test_the_soft_limit_is_configurable(doctors, monkeypatch):
    monkeypatch.setattr(settings, "CONVERSATION_SOFT_QUESTION_LIMIT", 2)
    llm = ScriptedLLM(analysis(symptoms=["x"], location="Dhaka"))
    assert say(llm, "same", question_count=2)["soft_limit_reached"] is True


def test_a_patient_can_choose_to_keep_refining(doctors):
    limit = settings.CONVERSATION_SOFT_QUESTION_LIMIT
    llm = ScriptedLLM(
        analysis(symptoms=["x"], next_question="duration", wants_to_keep_refining=True)
    )
    result = say(llm, "yes, keep going", question_count=limit)
    assert result["action"] == "ask"
    assert result["question_count"] == 1


def test_an_answered_question_is_never_asked_again():
    llm = ScriptedLLM(analysis(symptoms=["headache"], duration="2 days", next_question="duration"))
    assert say(llm, "2 days")["asking_about"] != "duration"


def test_an_already_asked_question_is_never_chosen_again():
    llm = ScriptedLLM(analysis(symptoms=["headache"], next_question="duration"))
    result = say(llm, "not sure", asked_questions=["duration"])
    assert result["asking_about"] != "duration"
    assert result["asked_questions"].count("duration") == 1


def test_i_dont_know_counts_as_answered_and_moves_on():
    llm = ScriptedLLM(analysis(symptoms=["headache"]), ["How long?", "How bad is it?"])
    conversation = Conversation(llm)
    assert conversation.say("headache")["asking_about"] == "duration"
    assert conversation.say("i don't know")["asking_about"] == "severity"


def test_off_topic_chat_is_answered_without_a_question():
    result = say(ScriptedLLM(analysis(), "It's a nice day."), "how is the weather")
    assert result["action"] == "talk"
    assert result["chips"] == []


def test_questions_are_recorded_as_labels_only():
    result = say(ScriptedLLM(analysis(symptoms=["headache"], next_question="duration")), "ow")
    assert result["asked_questions"] == ["duration"]


def test_no_search_runs_without_a_city(doctors):
    confident = {**HEADACHE, "location": None}
    result = say(ScriptedLLM(analysis(**confident)), "headache")
    assert result["asking_about"] == "location"
    assert doctors == []


def test_details_carry_over_between_turns():
    llm = ScriptedLLM([analysis(symptoms=["headache"], duration="2 days"), analysis()])
    conversation = Conversation(llm)
    conversation.say("headache for 2 days")
    result = conversation.say("I see")
    assert result["symptoms"] == ["headache"]
    assert result["duration"] == "2 days"


def test_what_is_known_and_asked_is_given_to_the_analysis():
    llm = ScriptedLLM()
    say(llm, "yes", symptoms=["headache"], asked_questions=["duration"])
    assert '"headache"' in llm.prompts[0]
    assert "Already asked: ['duration']" in llm.prompts[0]


def test_specialties_and_cities_come_from_the_database():
    llm = ScriptedLLM()
    say(llm, "hello")
    assert "Clinical Psychology" in llm.prompts[0]
    assert "Sylhet" in llm.prompts[0]


# ------------------------------------------------------------------------------
# "Show me doctors now"
# ------------------------------------------------------------------------------


def test_asking_for_doctors_searches_at_once_and_notes_the_precision(doctors):
    low = {**HEADACHE, "specialty_confidence": {"Neurology": 0.4}}
    llm = ScriptedLLM(analysis(**low, wants_doctors_now=True))
    result = say(llm, "just show me doctors")
    assert result["current_step"] == "completed"
    assert result["search_reason"] == "patient_asked"
    assert "less precise" in llm.writer_prompts[0]
    assert len(doctors) == 1


def test_the_escape_chip_works_by_exact_match(doctors):
    llm = ScriptedLLM(analysis(symptoms=["headache"], location="Dhaka"))
    chip = {"label": "Show me doctors now", "meaning": ESCAPE}
    result = say(llm, "show me doctors NOW ", pending_chips=[chip], symptoms=["headache"])
    assert result["current_step"] == "completed"


def test_the_first_question_does_not_offer_the_escape():
    llm = ScriptedLLM(analysis(symptoms=["headache"], next_question="duration"))
    assert say(llm, "x")["chips"] == []


def test_the_escape_is_offered_on_every_later_question():
    llm = ScriptedLLM(analysis(symptoms=["headache"], next_question="duration"))
    assert "Show me doctors now" in say(llm, "x", question_count=1)["chips"]


@pytest.mark.parametrize(
    ("text", "language_chip"),
    [("just doctors please", "Any city"), ("শুধু ডাক্তার দেখান", "যেকোনো শহর")],
)
def test_with_no_city_the_escape_asks_once_and_offers_any_city(text, language_chip, doctors):
    llm = ScriptedLLM(analysis(symptoms=["rash"], wants_doctors_now=True))
    result = say(llm, text)
    assert result["asking_about"] == "location"
    assert language_chip in result["chips"]
    assert doctors == []


def test_a_city_answer_finishes_the_escape(doctors):
    llm = ScriptedLLM(
        [analysis(symptoms=["rash"], wants_doctors_now=True), analysis(location="Sylhet")]
    )
    conversation = Conversation(llm)
    conversation.say("just doctors")
    assert conversation.say("Sylhet")["current_step"] == "completed"
    assert doctors[0]["city"] == "Sylhet"


def test_pressing_the_escape_again_searches_all_of_bangladesh(doctors):
    llm = ScriptedLLM(analysis(symptoms=["rash"], wants_doctors_now=True))
    conversation = Conversation(llm)
    conversation.say("just doctors")
    result = conversation.say("just show them")
    assert result["current_step"] == "completed"
    assert doctors[0]["city"] == ANY_CITY
    assert "all of Bangladesh" in llm.writer_prompts[-1]


def test_the_any_city_chip_searches_all_of_bangladesh(doctors):
    llm = ScriptedLLM(analysis(**{**HEADACHE, "location": None}))
    chip = {"label": "Any city", "meaning": "any_city"}
    assert say(llm, "any city", pending_chips=[chip])["location"] == ANY_CITY
    assert doctors[0]["city"] == ANY_CITY


def test_the_escape_waits_for_an_ambiguity_to_be_asked_once(doctors):
    llm = ScriptedLLM(analysis(**HEADACHE, wants_doctors_now=True))
    conversation = Conversation(llm)
    assert conversation.say("my heart is broken")["asking_about"] == "clarify_meaning"
    assert doctors == []
    result = conversation.say("just show me")
    assert result["current_step"] == "completed"
    assert "call 999 now" in llm.writer_prompts[-1]


# ------------------------------------------------------------------------------
# Routing
# ------------------------------------------------------------------------------


def test_emotional_distress_never_defaults_to_general_medicine(doctors):
    say(ScriptedLLM(analysis(**HEARTBREAK)), "she left me")
    assert "General Medicine" not in doctors[0]["candidate_specialties"]
    assert doctors[0]["strict_specialty"] is True


def test_a_general_doctor_joins_only_when_there_are_physical_symptoms_too(doctors):
    llm = ScriptedLLM(analysis(**HEARTBREAK, physical_symptoms_too=True))
    say(llm, "she left me and I can't eat")
    assert doctors[0]["candidate_specialties"] == ["Counselling", "General Medicine"]
    assert "physical_symptoms_too" in llm.writer_prompts[0]


def test_emotional_care_asks_about_the_kind_of_help_first(doctors):
    no_preference = {**HEARTBREAK, "care_preference": None}
    result = say(ScriptedLLM(analysis(**no_preference)), "she left me")
    assert result["asking_about"] == "care_preference"
    assert doctors == []


def test_general_medicine_is_chosen_only_when_the_information_supports_it(doctors):
    stomach = {**HEADACHE, "specialty_confidence": {"General Medicine": 0.8}}
    say(ScriptedLLM(analysis(**stomach)), "stomach pain for 3 days")
    assert doctors[0]["candidate_specialties"] == ["General Medicine"]


def test_invented_specialties_are_discarded(doctors):
    invented = {**HEADACHE, "specialty_confidence": {"Astrology": 1.0, "neurology": 0.9}}
    say(ScriptedLLM(analysis(**invented)), "headache")
    assert doctors[0]["candidate_specialties"] == ["Neurology"]


def test_scores_are_held_between_zero_and_one(doctors):
    wild = {**HEADACHE, "specialty_confidence": {"Neurology": 7.0}}
    assert say(ScriptedLLM(analysis(**wild)), "x")["specialty_confidence"]["Neurology"] == 1.0


@pytest.mark.parametrize(
    ("specialties", "candidates", "expected"),
    [
        (["General Medicine"], ["Clinical Psychology"], False),
        (["Clinical Psychology"], ["Clinical Psychology"], True),
        (["General Medicine"], ["General Medicine"], True),
    ],
)
def test_a_strict_search_shows_general_medicine_only_when_chosen(specialties, candidates, expected):
    assert _fits_request(specialties, candidates, "Dhaka", "Dhaka", strict=True) is expected


def test_the_direct_search_still_keeps_general_doctors():
    assert _fits_request(["General Medicine"], ["Neurology"], "Dhaka", "Dhaka") is True


def test_the_mental_health_specialties_are_marked_in_the_map():
    assert {"Psychiatry", "Clinical Psychology", "Counselling"} == EMOTIONAL_SPECIALTIES


def test_the_routing_reason_is_recorded_without_patient_text(doctors, caplog):
    secret = "my husband left and I told nobody"
    llm = ScriptedLLM(analysis(**HEADACHE, answer_basis=["duration", "severity"]))
    with caplog.at_level(logging.DEBUG):
        result = say(llm, secret)
    record = result["routing_log"][0]
    assert record["specialties"] == ["Neurology"]
    assert record["confidence"] == 0.9
    assert record["margin"] == 0.7
    assert record["reason"] == "confident"
    assert record["driven_by"] == ["duration", "severity"]
    assert secret not in str(result["routing_log"])
    assert secret not in caplog.text


def test_the_reply_is_written_after_the_search_and_knows_the_count(doctors):
    llm = ScriptedLLM(analysis(**HEADACHE))
    result = say(llm, "headache")
    assert '"doctors_listed_below_your_reply": 1' in llm.writer_prompts[0]
    assert result["recommendations"] == [{"id": "d1"}]


def test_no_doctors_found_is_said_honestly_with_no_substitute(doctors):
    doctors.found.clear()
    llm = ScriptedLLM(analysis(**HEARTBREAK))
    result = say(llm, "she left me")
    assert result["recommendations"] == []
    assert "No matching doctors were found" in llm.writer_prompts[0]
    assert len(doctors) == 1


def test_a_failed_search_still_gets_a_reply(monkeypatch):
    def broken(*_args, **_kwargs):
        raise RuntimeError("no database")

    monkeypatch.setattr("app.search.recommend.recommend_doctors", broken)
    result = say(ScriptedLLM(analysis(**HEADACHE), "I couldn't find anyone."), "headache")
    assert result["recommendations"] == []
    assert result["assistant_reply"]


# ------------------------------------------------------------------------------
# Safety
# ------------------------------------------------------------------------------


def test_rules_catch_an_emergency_before_any_model_call():
    result = say(NoModel(), "I have crushing chest pain")
    assert result["safety_kind"] == "physical"
    assert result["assistant_reply"] == get_emergency_response()


def test_a_self_harm_reply_is_fixed_and_never_touches_a_model():
    result = say(NoModel(), "I don't want to live anymore")
    assert result["safety_kind"] == "self_harm"
    assert result["assistant_reply"] == get_crisis_response("I don't want to live anymore")
    assert result["crisis_active"] is True
    assert not result["recommendations"]


def test_a_self_harm_reply_is_the_same_every_time():
    first = say(NoModel(), "i want to die")["assistant_reply"]
    assert say(NoModel(), "i want to die")["assistant_reply"] == first


def test_the_model_can_add_an_alert_the_rules_missed():
    llm = ScriptedLLM(analysis(possible_emergency="physical", symptoms=["x"]))
    result = say(llm, "something unusual")
    assert result["assistant_reply"] == get_emergency_response()
    assert len(llm.prompts) == 1


def test_the_model_can_raise_the_crisis_response_but_never_write_it():
    llm = ScriptedLLM(analysis(possible_emergency="self_harm"), "UNSAFE MODEL TEXT")
    result = say(llm, "everyone would be happier if I left for good")
    assert result["safety_kind"] == "self_harm"
    assert "UNSAFE MODEL TEXT" not in result["assistant_reply"]
    assert len(llm.prompts) == 1


def test_a_repeated_crisis_gets_the_short_fixed_message():
    conversation = Conversation(NoModel())
    first = conversation.say("i want to die")["assistant_reply"]
    second = conversation.say("i want to die")["assistant_reply"]
    assert second == get_crisis_response("i want to die", repeat=True)
    assert second != first


def test_after_a_crisis_the_assistant_supports_and_shows_no_doctors(doctors):
    llm = ScriptedLLM(analysis(**HEARTBREAK, next_question="duration"), "I'm here to help.")
    conversation = Conversation(llm)
    conversation.say("i want to die")
    result = conversation.say("I don't know")
    assert result["action"] == "support"
    assert result["chips"] == []
    assert doctors == []
    assert "not_wanting_to_live" in llm.writer_prompts[0]


def test_after_a_crisis_the_patient_can_ask_for_someone_to_talk_to(doctors):
    llm = ScriptedLLM(analysis(**HEARTBREAK, wants_doctors_now=True))
    conversation = Conversation(llm)
    conversation.say("i want to die")
    assert conversation.say("yes please find a counsellor")["current_step"] == "completed"
    assert doctors[0]["candidate_specialties"] == ["Counselling"]


def test_risk_in_an_emotional_conversation_gets_the_crisis_response():
    conversation = Conversation(ScriptedLLM(analysis(symptoms=["heartbreak"]), "How long?"))
    conversation.say("emotional, she left me")
    assert conversation.say("i want to end it all")["safety_kind"] == "self_harm"


def test_heartbreak_alone_is_not_an_emergency():
    result = say(ScriptedLLM(analysis(symptoms=["heartbreak"]), "Which?"), "I have a broken heart")
    assert result["safety_status"] == "safe"


# ------------------------------------------------------------------------------
# The reply checks
# ------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "unsafe",
    [
        "You have depression.",
        "Take sertraline.",
        "It's nothing serious.",
        "I feel your pain.",
        "I've been through this too.",
    ],
)
def test_an_unsafe_reply_gets_one_rewrite(unsafe):
    llm = ScriptedLLM(replies=[unsafe, "That sounds painful. How long has it been?"])
    result = say(llm, "I feel low")
    assert result["assistant_reply"] == "That sounds painful. How long has it been?"
    assert len(llm.writer_prompts) == 2
    assert "rejected" in llm.writer_prompts[1]


@pytest.mark.parametrize(
    ("text", "language"),
    [("I feel low", "en"), ("আমার মন খারাপ", "bn")],
)
def test_a_reply_unsafe_twice_becomes_the_fixed_reply_in_their_language(text, language):
    llm = ScriptedLLM(analysis(language=language), "You have dengue.")
    result = say(llm, text)
    assert result["assistant_reply"] == guard_fallback(language)
    assert len(llm.writer_prompts) == 2


def test_the_fixed_reply_for_banglish_is_in_banglish():
    llm = ScriptedLLM(analysis(language="banglish"), "You have dengue.")
    assert say(llm, "amar mon kharap")["assistant_reply"] == guard_fallback("banglish")


def test_a_repeated_sentence_is_rewritten():
    repeat = "I'm sorry you're going through this."
    llm = ScriptedLLM(replies=[f"{repeat} How long?", "That sounds hard. How long?"])
    history = [{"role": "assistant", "content": repeat}]
    result = say(llm, "still bad", history=history)
    assert result["assistant_reply"] == "That sounds hard. How long?"


def test_a_repeated_sentence_that_survives_the_rewrite_is_removed():
    repeat = "I'm sorry you're going through this."
    llm = ScriptedLLM(replies=[f"{repeat} How long?"])
    history = [{"role": "assistant", "content": repeat}]
    assert say(llm, "still bad", history=history)["assistant_reply"] == "How long?"


def test_repetition_ignores_case_and_punctuation():
    assert repeated_sentences("THANK you for telling me!", ["Thank you for telling me."])


def test_short_ordinary_sentences_are_not_repetition():
    assert repeated_sentences("Thank you.", ["Thank you."]) == []


def test_bangla_script_answered_in_english_is_rewritten():
    llm = ScriptedLLM(analysis(language="bn"), ["How long?", "কতদিন ধরে?"])
    assert say(llm, "আমার জ্বর")["assistant_reply"] == "কতদিন ধরে?"


def test_banglish_answered_in_bangla_script_is_rewritten():
    llm = ScriptedLLM(analysis(language="banglish"), ["কতদিন ধরে?", "Koto din dhore?"])
    assert say(llm, "amar jor")["assistant_reply"] == "Koto din dhore?"


def test_a_clean_reply_makes_no_extra_call():
    llm = ScriptedLLM()
    say(llm, "hello")
    assert len(llm.writer_prompts) == 1


def test_an_unsafe_chip_is_dropped():
    chips = [WriterChip(label="You have dengue"), WriterChip(label="A few days")]
    llm = ScriptedLLM(
        analysis(symptoms=["x"], next_question="duration"),
        WriterTurn(reply="How long?", chips=chips),
    )
    assert say(llm, "fever")["chips"] == ["A few days"]


def test_there_are_never_more_than_four_chips():
    chips = [WriterChip(label=str(n)) for n in range(9)]
    llm = ScriptedLLM(
        analysis(symptoms=["x"], next_question="location"),
        WriterTurn(reply="Which city?", chips=chips),
    )
    assert len(say(llm, "fever", question_count=2)["chips"]) == 4


def test_a_reply_that_asks_nothing_offers_no_chips(doctors):
    llm = ScriptedLLM(
        analysis(**HEADACHE), WriterTurn(reply="Listed below.", chips=[WriterChip(label="Hi")])
    )
    assert say(llm, "headache")["chips"] == []


# ------------------------------------------------------------------------------
# State
# ------------------------------------------------------------------------------


def test_the_emotional_state_is_never_saved():
    assert "emotional_state" not in PERSISTED_STATE_FIELDS


def test_a_conversation_saved_before_question_count_keeps_its_progress():
    llm = ScriptedLLM(analysis(symptoms=["x"], next_question="duration"))
    assert say(llm, "same", followup_count=3)["question_count"] == 4


def test_the_analysis_schema_has_every_state_the_brief_lists():
    assert {"language", "emotional_state", "specialty_confidence"} <= set(TurnAnalysis.model_fields)


@pytest.mark.parametrize(
    "rule",
    [
        "never diagnose",
        "Never name or suggest a medicine",
        "Never say symptoms are harmless",
        "You are an AI assistant",
        "at most one question",
    ],
)
def test_the_persona_keeps_its_rules(rule):
    assert rule.lower() in graph_module.PERSONA.lower()
