"""The assistant: talk, ask until it is sure what is wrong, then suggest doctors.

Each turn:
1. safety  - fixed rules catch an emergency before any model runs
2. assess  - the model reads the chat and matching medical book passages, and says what it may be
3. search  - once sure, doctors are found with MongoDB vector search
4. reply   - the model talks to the patient

Python decides when to stop asking. The model decides what the patient's answers mean.
"""

import json
import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from app.ai.llm import get_llm_client
from app.ai.safety import (
    check_emergency,
    emergency_kind,
    get_crisis_response,
    get_emergency_response,
    has_bangla_script,
)
from app.ai.state import Assessment, ConversationState, SearchCriteria
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.search.vector_store import search_books

logger = logging.getLogger("medimatch.ai.graph")

PROMPTS = Path(__file__).resolve().parent / "prompts"
ASSESS_PROMPT = (PROMPTS / "assess.md").read_text(encoding="utf-8")
PERSONA = (PROMPTS / "persona.md").read_text(encoding="utf-8")

ANY_CITY = "Bangladesh"
GENERAL_MEDICINE = "General Medicine"
# The web app matches these labels exactly
SHOW_DOCTORS = {
    "English": "Show me doctors now",
    "Bangla": "এখনই ডাক্তার দেখান",
    "Banglish": "Ekhon doctor dekhan",
}
ANY_CITY_LABEL = {"English": "Any city", "Bangla": "যেকোনো শহর", "Banglish": "Je kono shohor"}
MOST_FINDINGS = 20
MOST_CITY_ASKS = 2

CACHE_SECONDS = 300
_lookup_cache: dict[str, tuple[float, list[str]]] = {}


def _cached(name: str, load: Callable[[], list[str]]) -> list[str]:
    """Cities and specialties rarely change, so a turn need not fetch them. Failures are not kept."""
    saved = _lookup_cache.get(name)
    if saved and time.monotonic() - saved[0] < CACHE_SECONDS:
        return saved[1]
    values = load()
    if values:
        _lookup_cache[name] = (time.monotonic(), values)
    return values


def _column(table: str, column: str) -> list[str]:
    client = get_supabase_admin_client()
    if not client:
        return []
    try:
        rows = client.table(table).select(column).execute().data or []
        return sorted({row[column] for row in rows if row.get(column)})
    except Exception as e:
        logger.warning(f"Could not load {table}: {type(e).__name__}")
        return []


def _known_cities() -> list[str]:
    return _cached("cities", lambda: _column("doctor_cities", "city"))


def _get_verified_specialty_names() -> list[str]:
    return _cached("specialties", lambda: _column("specialties", "name"))


# 1. Safety


def safety_node(state: ConversationState) -> dict[str, Any]:
    """Fixed rules only, so an emergency is answered at once and never depends on the model."""
    latest = state["messages"][-1]["content"]
    is_emergency, category, _ = check_emergency(latest)
    if not is_emergency:
        return {"safety_status": "safe", "safety_kind": None}

    kind = emergency_kind(category)
    self_harm = kind == "self_harm"
    crisis_active = bool(state.get("crisis_active"))
    return {
        "safety_status": "emergency",
        "safety_kind": kind,
        "current_step": "emergency_escalated",
        "search_criteria": None,
        "recommendations": [],
        "chips": [],
        "asking_about": None,
        "crisis_active": crisis_active or self_harm,
        "assistant_reply": (
            get_crisis_response(latest, repeat=crisis_active)
            if self_harm
            else get_emergency_response()
        ),
    }


# 2. Assess


def _assessment_schema(specialties: list[str]) -> dict[str, Any]:
    """The model can only name a specialty that exists, and its lists stay short."""
    schema = Assessment.model_json_schema()
    fields = schema["properties"]
    for name, most in (("new_findings", 6), ("possible_conditions", 3), ("answer_options", 3)):
        fields[name]["maxItems"] = most
    if specialties:
        fields["specialty"] = {"anyOf": [{"enum": specialties}, {"type": "null"}]}
    return schema


def _assess_prompt(state: ConversationState, specialties: list[str], passages: list[str]) -> str:
    known = {
        key: state.get(key)
        for key in ("findings", "city", "possible_conditions", "confidence")
        if state.get(key)
    }
    books = "\n---\n".join(passages) or "None. Use your own medical knowledge."
    return (
        f"{ASSESS_PROMPT}\n"
        f"Specialties: {'; '.join(specialties)}\n"
        f"Cities: {', '.join(_known_cities())}\n\n"
        f"Your notes so far: {json.dumps(known, ensure_ascii=False)}\n\n"
        f"Medical book passages:\n{books}"
    )


def _recent(state: ConversationState) -> list[dict[str, str]]:
    return state["messages"][-settings.LLM_HISTORY_MESSAGES :]


def _matches(text: str, labels: dict[str, str]) -> bool:
    return text.strip().casefold() in {label.casefold() for label in labels.values()}


def decide(
    state: ConversationState, findings: list[str], confidence: int, city: str | None, wants: bool
) -> str:
    """When to stop asking. The model's confidence counts only after enough questions."""
    asked = state.get("question_count", 0)
    if state.get("crisis_active") and not wants:
        return "support"
    if not findings and not wants:
        return "chat"
    sure = confidence >= settings.SURE_CONFIDENCE and asked >= settings.MIN_QUESTIONS
    if not (sure or wants or asked >= settings.MAX_QUESTIONS):
        return "ask"
    if not city and state.get("city_asks", 0) < MOST_CITY_ASKS:
        return "ask_city"
    return "search"


def _chips(action: str, language: str, options: list[str], asked: int) -> list[str]:
    if action == "ask_city":
        return [ANY_CITY_LABEL[language]]
    if action != "ask":
        return []
    chips = [option.strip()[:40] for option in options if option.strip()][:3]
    return [*chips, SHOW_DOCTORS[language]] if asked else chips


def assess_node(state: ConversationState) -> dict[str, Any]:
    latest = state["messages"][-1]["content"]
    before = state.get("findings") or []
    specialties = _get_verified_specialty_names()
    passages = search_books(" ".join([*before, latest]))

    result = get_llm_client().generate_structured(
        _recent(state),
        _assess_prompt(state, specialties, passages),
        Assessment,
        _assessment_schema(specialties),
    )

    language: str = result.language
    if has_bangla_script(latest):
        language = "Bangla"
    elif language == "Bangla":
        language = "Banglish"
    findings = list(
        dict.fromkeys([*before, *(result.new_findings if result.has_health_problem else [])])
    )[-MOST_FINDINGS:]
    city = ANY_CITY if _matches(latest, ANY_CITY_LABEL) else result.city or state.get("city")
    max_fee = result.max_fee or state.get("max_fee")
    specialty = result.specialty if result.specialty in specialties else state.get("specialty")
    conditions = [c.model_dump() for c in result.possible_conditions]

    tapped_show = _matches(latest, SHOW_DOCTORS)
    action = decide(
        state, findings, result.confidence, city, tapped_show or result.wants_doctors_now
    )
    # The same cards are already on screen, so talk instead of showing them again
    key = [specialty or GENERAL_MEDICINE, city or ANY_CITY, str(max_fee or "")]
    if action == "search" and state.get("shown_search") == key and not tapped_show:
        action = "chat"

    asked = state.get("question_count", 0)
    logger.info(f"Assessed: {action} at confidence {result.confidence}")
    return {
        "language": language,
        "findings": findings,
        "city": city,
        "max_fee": max_fee,
        "possible_conditions": conditions or state.get("possible_conditions") or [],
        "confidence": result.confidence,
        "specialty": specialty,
        "next_question": result.next_question,
        "passages": passages,
        "action": action,
        "question_count": asked + (action == "ask"),
        "city_asks": state.get("city_asks", 0) + (action == "ask_city"),
        "asking_about": "location" if action == "ask_city" else None,
        "chips": _chips(action, language, result.answer_options, asked),
        "search_criteria": None,
        "recommendations": [],
    }


# 3. Search


def search_node(state: ConversationState) -> dict[str, Any]:
    from app.search.recommend import recommend_doctors

    specialty = state.get("specialty") or GENERAL_MEDICINE
    city = state.get("city") or ANY_CITY
    max_fee = state.get("max_fee")
    conditions = [c["name"] for c in state.get("possible_conditions") or []]
    criteria = SearchCriteria(
        candidate_specialties=[specialty],
        city=city,
        max_fee=max_fee,
        keywords=[*conditions, *(state.get("findings") or [])[:5]],
    ).model_dump()
    try:
        doctors = [d.model_dump() for d in recommend_doctors(criteria, top_k=5).recommendations]
    except Exception as e:
        logger.warning(f"Doctor search failed: {type(e).__name__}")
        doctors = []
    return {
        "search_criteria": criteria,
        "recommendations": doctors,
        "shown_bookable": any(doctor.get("online_booking") for doctor in doctors),
        # Nothing was shown, so the next message may search again
        "shown_search": [specialty, city, str(max_fee or "")] if doctors else [],
    }


# 4. Reply


def _reach(state: ConversationState) -> str:
    if state.get("shown_bookable"):
        return (
            "Cards with a booking button are booked here. For the others, the patient contacts "
            "the hospital on the card."
        )
    return (
        "None can be booked online. The patient contacts the hospital named on the card. Cards "
        "have no booking button and no phone number."
    )


def _task(state: ConversationState) -> str:
    action = state["action"]
    if action == "ask":
        return (
            "React to what they said, then ask this one question in your own words: "
            f"{state['next_question']}"
        )
    if action == "ask_city":
        return "Say you have a good idea of what is going on, and ask which city they want a doctor in."
    if action == "support":
        return (
            "They have spoken about not wanting to live. Be gentle and present, with no jokes and "
            "no questions. Offer to help find someone to talk to."
        )
    if action == "search":
        explain = (
            "Name the first condition of your assessment as the most likely one, explain it in plain words and why their symptoms point there, "
            "name the next possibility, and say a doctor should confirm it. Ask nothing. "
        )
        doctors = len(state.get("recommendations") or [])
        if not doctors:
            return f"{explain}No doctor was found in that city, so offer to try another city."
        specialty = state.get("specialty") or GENERAL_MEDICINE
        return (
            f"{explain}Then say {doctors} {specialty} doctors are in the cards below. Do not list or "
            f"name them, the cards do that. {_reach(state)}"
        )
    if state.get("shown_search"):
        return f"Answer what they just said. Doctors are already in cards above. {_reach(state)}"
    return "Chat about what they said, and find out how they are feeling."


def _reply_prompt(state: ConversationState) -> str:
    parts = [PERSONA]
    if state["action"] == "search" or state.get("shown_search"):
        conditions = json.dumps(state.get("possible_conditions") or [], ensure_ascii=False)
        parts.append(f"Your assessment: {conditions}")
        if state.get("passages"):
            parts.append("From the medical books:\n" + "\n---\n".join(state["passages"][:2]))
    parts.append(f"Your task now: {_task(state)}\nWrite in {state['language']}.")
    return "\n\n".join(parts)


STEPS = {"search": "completed", "ask": "ask_followup", "ask_city": "ask_followup"}


def reply_node(state: ConversationState) -> dict[str, Any]:
    reply = get_llm_client().generate(
        _recent(state), _reply_prompt(state), temperature=settings.LLM_TEMPERATURE
    )
    return {"assistant_reply": reply, "current_step": STEPS.get(state["action"], "conversation")}


# Workflow


def build_symptom_graph() -> Any:
    workflow = StateGraph(ConversationState)
    workflow.add_node("safety", safety_node)
    workflow.add_node("assess", assess_node)
    workflow.add_node("search", search_node)
    workflow.add_node("reply", reply_node)
    workflow.set_entry_point("safety")
    workflow.add_conditional_edges(
        "safety", lambda s: END if s["safety_status"] == "emergency" else "assess"
    )
    workflow.add_conditional_edges(
        "assess", lambda s: "search" if s["action"] == "search" else "reply"
    )
    workflow.add_edge("search", "reply")
    workflow.add_edge("reply", END)
    return workflow.compile()


_COMPILED_GRAPH = None


def get_symptom_graph() -> Any:
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_symptom_graph()
    return _COMPILED_GRAPH


def warm_up() -> None:
    """Loads the models into memory at startup, so the first patient does not wait."""
    try:
        get_symptom_graph()
        _known_cities()
        _get_verified_specialty_names()
        search_books("fever")
        get_llm_client().generate([{"role": "user", "content": "hi"}], "Reply with one word.")
    except Exception as e:
        logger.warning(f"Warm up failed: {type(e).__name__}")
