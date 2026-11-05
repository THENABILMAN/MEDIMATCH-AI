"""LangGraph Symptom Consultation Workflow.

Each turn runs two model steps. A hidden analysis reads the conversation, then a writer speaks to
the patient in persona. Between them Python decides what happens, because stopping, searching and
safety must not depend on the model. Emergencies are checked first by fixed rules, the model can
only add an alert, and every reply passes the output guard.
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

from langgraph.graph import END, StateGraph

from app.ai.llm import LLMUnavailableError, get_llm_client
from app.ai.privacy import redact_pii
from app.ai.routing import (
    ANY_CITY,
    CHEST_PHRASE_IDS,
    LOCATION,
    chest_is_possible,
    find_ambiguous_phrases,
    is_emotional,
    open_flags,
    phrases_prompt,
    plan_turn,
    routing_record,
    specialties_to_search,
    specialty_guide,
)
from app.ai.safety import (
    check_emergency,
    emergency_kind,
    get_crisis_response,
    get_emergency_response,
    guard_fallback,
    has_bangla_script,
    reply_violation,
)
from app.ai.state import ConversationState, SearchCriteria, TurnAnalysis, WriterTurn
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client

logger = logging.getLogger("medimatch.ai.graph")

PROMPTS = Path(__file__).resolve().parent / "prompts"
PERSONA = (PROMPTS / "persona.md").read_text(encoding="utf-8")
ANALYSIS_PROMPT = (PROMPTS / "analysis.md").read_text(encoding="utf-8")

MAX_MODEL_CHIPS = 3
# Sentences this short ("Thank you.") are ordinary speech, not repetition
SHORTEST_REPEATED_WORDS = 3
# Share of words two sentences have in common for them to count as the same sentence
REPEAT_OVERLAP = 0.7
_SENTENCE_END = re.compile(r"(?<=[.!?।])\s+|\n+")
_NOT_A_WORD = re.compile(r"[^\w\s]")

# These stay the same every time, so a patient can always find them
ESCAPE = "show_doctors"
SHOW_DOCTORS_LABEL = {
    "en": "Show me doctors now",
    "bn": "এখনই ডাক্তার দেখান",
    "banglish": "Ekhon doctor dekhan",
}
ANY_CITY_LABEL = {"en": "Any city", "bn": "যেকোনো শহর", "banglish": "Je kono shohor"}


def _recent_messages(
    messages: list[dict[str, str]], limit: int | None = None
) -> list[dict[str, str]]:
    """The latest messages, redacted. This is all an LLM provider ever sees of a conversation."""
    return [
        {"role": m.get("role", "user"), "content": redact_pii(m.get("content", ""))}
        for m in messages[-(limit or settings.LLM_HISTORY_MESSAGES) :]
    ]


def _known_cities() -> list[str]:
    """Cities with an approved doctor."""
    client = get_supabase_admin_client()
    if not client:
        return []
    try:
        res = client.table("public_doctors").select("city").execute()
        return sorted({row["city"] for row in res.data or [] if row.get("city")})
    except Exception as e:
        logger.warning(f"Could not load cities: {type(e).__name__}")
        return []


def _get_verified_specialty_names() -> list[str]:
    """Fetch all verified specialty names directly from the Supabase database."""
    client = get_supabase_admin_client()
    if not client:
        return []
    try:
        res = client.table("specialties").select("name").execute()
        return [row["name"] for row in res.data or []]
    except Exception as e:
        logger.warning(f"Could not load specialties: {type(e).__name__}")
        return []


def _match_verified_specialties(names: list[str], verified: list[str]) -> list[str]:
    """Keeps only names that exist in the database, using their stored spelling."""
    by_lower = {v.lower(): v for v in verified}
    matched: list[str] = []
    for name in names:
        spec = by_lower.get(name.strip().lower())
        if spec and spec not in matched:
            matched.append(spec)
    return matched


def _verified_confidence(scores: dict[str, float], verified: list[str]) -> dict[str, float]:
    """Keeps only scores for specialties in the database, held between 0 and 1."""
    by_lower = {v.lower(): v for v in verified}
    return {
        by_lower[name.strip().lower()]: min(max(float(score), 0.0), 1.0)
        for name, score in scores.items()
        if name.strip().lower() in by_lower
    }


KNOWN_FIELDS = (
    "symptoms",
    "duration",
    "severity",
    "daily_impact",
    "location",
    "preferred_max_fee",
    "care_preference",
)


def _known_details(state: ConversationState) -> dict[str, Any]:
    return {field: state.get(field) for field in KNOWN_FIELDS if state.get(field)}


def build_analysis_prompt(state: ConversationState, specialties: list[str]) -> str:
    return (
        f"{ANALYSIS_PROMPT}\n"
        f"Specialties available:\n{specialty_guide(specialties)}\n\n"
        f"Phrases to watch:\n{phrases_prompt()}\n\n"
        f"Cities with doctors: {', '.join(_known_cities())}\n"
        f"Details known so far: {json.dumps(_known_details(state), ensure_ascii=False)}\n"
        f"Unclear phrases not yet explained: {open_flags(state.get('ambiguity_flags') or {})}\n"
        f"Already asked: {state.get('asked_questions') or []}"
    )


# ------------------------------------------------------------------------------
# Node 1: Safety Check (Rule-based deterministic emergency triage)
# ------------------------------------------------------------------------------


def _emergency_update(state: ConversationState, kind: str) -> dict[str, Any]:
    """The fixed response. No model writes any part of it, and no doctors follow it."""
    update: dict[str, Any] = {
        "safety_status": "emergency",
        "safety_kind": kind,
        "current_step": "emergency_escalated",
        "search_criteria": None,
        "recommendations": [],
        "chips": [],
        "pending_chips": [],
        "asking_about": None,
    }
    if kind == "self_harm":
        latest = (state.get("messages") or [{}])[-1].get("content", "")
        update["assistant_reply"] = get_crisis_response(
            latest, repeat=bool(state.get("crisis_active"))
        )
        update["crisis_active"] = True
    else:
        update["assistant_reply"] = get_emergency_response()
    return update


def safety_check_node(state: ConversationState) -> dict[str, Any]:
    """Inspects the most recent patient message for emergency patterns."""
    messages = state.get("messages", [])
    latest = messages[-1].get("content", "") if messages else ""
    is_emergency, category, _ = check_emergency(latest)
    if is_emergency:
        return _emergency_update(state, emergency_kind(category))
    return {"safety_status": "safe", "safety_kind": None, "current_step": "safety_check"}


def route_after_safety(state: ConversationState) -> str:
    """Short-circuits the workflow on an emergency, before any model is called."""
    return "escalate" if state.get("safety_status") == "emergency" else "continue"


# ------------------------------------------------------------------------------
# Node 2: Analyze (hidden step: read the conversation, then Python decides)
# ------------------------------------------------------------------------------


def _tapped_chip(state: ConversationState, latest: str) -> str | None:
    """What a tapped chip means, by exact match. This works with no model at all."""
    text = latest.strip().casefold()
    for chip in state.get("pending_chips") or []:
        if chip.get("label", "").strip().casefold() == text:
            return chip.get("meaning")
    return None


def _apply_explanation(flags: dict[str, str], answer: str | None) -> dict[str, str]:
    """Records how the patient explained every open phrase."""
    if answer not in {"emotional", "physical", "both", "unclear"}:
        return flags
    return {phrase: (answer if status == "open" else status) for phrase, status in flags.items()}


def _chest_answered_physical(before: dict[str, str], after: dict[str, str]) -> bool:
    """A physical answer about the chest goes to the fixed alert, not to a doctor list."""
    return any(
        phrase in CHEST_PHRASE_IDS
        and before.get(phrase) == "open"
        and after[phrase] in {"physical", "both"}
        for phrase in after
    )


def analyze_node(state: ConversationState) -> dict[str, Any]:
    """Runs the hidden analysis, then decides this turn's action in Python."""
    messages = state.get("messages", [])
    latest = messages[-1].get("content", "") if messages else ""
    flags = dict(state.get("ambiguity_flags") or {})
    for phrase in find_ambiguous_phrases(latest):
        flags.setdefault(phrase, "open")

    # A tapped "physical" must reach the alert even if the model is down
    chip = _tapped_chip(state, latest)
    if chip in {"physical", "both", "emotional"}:
        explained = _apply_explanation(flags, chip)
        if _chest_answered_physical(flags, explained):
            return {**_emergency_update(state, "physical"), "ambiguity_flags": explained}
        flags = explained

    verified = _get_verified_specialty_names()
    try:
        analysis: TurnAnalysis = get_llm_client().generate_structured(
            messages=_recent_messages(messages),
            response_model=TurnAnalysis,
            system_prompt=build_analysis_prompt({**state, "ambiguity_flags": flags}, verified),
        )
    except ValueError as e:
        raise LLMUnavailableError("The model's reply could not be read") from e

    # The model can only add an alert, never remove one, because the rules have already run
    if analysis.possible_emergency != "none":
        logger.warning("[SAFETY ESCALATION] Emergency flagged by the model")
        return {
            **_emergency_update(state, analysis.possible_emergency),
            "ambiguity_flags": flags,
        }

    for phrase in analysis.ambiguous_phrases:
        if phrase and phrase not in flags:
            flags[phrase] = "open"
    explained = _apply_explanation(flags, analysis.ambiguity_answer)
    if _chest_answered_physical(flags, explained):
        logger.warning("[SAFETY ESCALATION] Patient described a physical chest symptom")
        return {**_emergency_update(state, "physical"), "ambiguity_flags": explained}
    flags = explained

    symptoms = list(state.get("symptoms") or [])
    symptoms += [s for s in analysis.symptoms if s and s not in symptoms]
    location = ANY_CITY if chip == "any_city" else analysis.location or state.get("location")
    confidence = _verified_confidence(analysis.specialty_confidence, verified) or dict(
        state.get("specialty_confidence") or {}
    )
    physical_too = analysis.physical_symptoms_too or bool(state.get("physical_symptoms_too"))
    urgency = analysis.urgency if analysis.urgency != "unknown" else state.get("urgency", "unknown")
    if has_bangla_script(latest):
        language = "bn"
    else:
        language = "banglish" if analysis.language == "bn" else analysis.language

    details: ConversationState = {
        "symptoms": symptoms,
        "duration": analysis.duration or state.get("duration"),
        "severity": analysis.severity or state.get("severity"),
        "daily_impact": analysis.daily_impact or state.get("daily_impact"),
        "age_group": analysis.age_group or state.get("age_group"),
        "location": location,
        "preferred_max_fee": analysis.preferred_max_fee or state.get("preferred_max_fee"),
        "care_preference": analysis.care_preference or state.get("care_preference"),
    }

    asked = list(state.get("asked_questions") or [])
    question_count = state.get("question_count", state.get("followup_count", 0))
    # Only an offer of matches can be accepted, so the model cannot quietly reset the limit
    if (
        analysis.wants_to_keep_refining
        and question_count >= settings.CONVERSATION_SOFT_QUESTION_LIMIT
    ):
        question_count = 0
    wants_now = bool(chip == ESCAPE or analysis.wants_doctors_now or state.get("escape_pending"))
    known = {field for field in KNOWN_FIELDS if details.get(field)}
    if urgency != "unknown":
        known.add("severity")

    plan = plan_turn(
        symptoms=symptoms,
        location=location,
        confidence=confidence,
        urgency_known=urgency != "unknown",
        flags=flags,
        asked=asked,
        known=known,
        question_count=question_count,
        wants_now=wants_now,
        suggested=analysis.next_question,
        crisis_active=bool(state.get("crisis_active")),
    )

    update: dict[str, Any] = {
        **details,
        "language": language,
        "emotional_state": analysis.emotional_state,
        "urgency": urgency,
        "physical_symptoms_too": physical_too,
        "specialty_confidence": confidence,
        "candidate_specialty_names": specialties_to_search(
            confidence, physical_too, details.get("care_preference")
        ),
        "ambiguity_flags": flags,
        "asked_questions": asked + ([plan.goal] if plan.goal else []),
        "question_count": question_count + (1 if plan.goal else 0),
        "escape_pending": wants_now and plan.action != "search",
        "action": plan.action,
        "search_reason": plan.reason,
        "searched_everywhere": plan.any_city or location == ANY_CITY,
        "soft_limit_reached": plan.reason == "soft_limit",
        "asking_about": plan.goal,
        "search_criteria": None,
        "recommendations": [],
    }
    if plan.action == "search":
        record = routing_record(
            specialties=update["candidate_specialty_names"],
            confidence=confidence,
            reason=plan.reason,
            answer_basis=analysis.answer_basis,
            flags=flags,
        )
        update["routing_log"] = list(state.get("routing_log") or []) + [record]
        # Labels and numbers only, with no ids, so this cannot be tied to a patient
        logger.info(
            f"Routed to {record['specialties']} at {record['confidence']} ({record['reason']})"
        )
    return update


def route_after_analysis(state: ConversationState) -> str:
    if state.get("safety_status") == "emergency":
        return "escalate"
    return "search" if state.get("action") == "search" else "write"


# ------------------------------------------------------------------------------
# Node 3: Search (Mapped ONLY to verified DB specialties, read from Supabase)
# ------------------------------------------------------------------------------


def build_search_criteria_node(state: ConversationState) -> dict[str, Any]:
    """Searches before the reply is written, so the reply can truthfully say what was found."""
    from app.search.recommend import recommend_doctors

    verified = _get_verified_specialty_names()
    specialties = _match_verified_specialties(state.get("candidate_specialty_names", []), verified)
    criteria = SearchCriteria(
        candidate_specialties=specialties or verified,
        city=state.get("location") or ANY_CITY,
        max_fee=state.get("preferred_max_fee"),
        keywords=state.get("symptoms", [])[:5],
    ).model_dump()

    try:
        found = recommend_doctors(criteria, top_k=5).recommendations
        recommendations = [doctor.model_dump() for doctor in found]
    except Exception as e:
        logger.warning(f"Could not generate recommendations during chat: {type(e).__name__}")
        recommendations = []
    return {"search_criteria": criteria, "recommendations": recommendations}


# ------------------------------------------------------------------------------
# Node 4: Write (the model speaks to the patient, in persona)
# ------------------------------------------------------------------------------


def _search_notes(state: ConversationState) -> dict[str, Any]:
    doctors = len(state.get("recommendations") or [])
    notes: dict[str, Any] = {
        "doctors_listed_below_your_reply": doctors,
        "kinds_of_specialist": state.get("candidate_specialty_names", []),
    }
    if doctors:
        notes["do"] = (
            "Say something kind about what they shared, naming a detail, then say in plain words "
            "that people who can help are listed below. Two sentences. Do not list specialties."
        )
    else:
        notes["do"] = (
            "No matching doctors were found. Say so honestly, and offer to look in another city. "
            "Do not suggest a different kind of doctor."
        )
    if state.get("search_reason") == "patient_asked":
        notes["also_say"] = "In one sentence, say the match may be less precise."
    if state.get("soft_limit_reached"):
        notes["also_do"] = (
            "Briefly sum up what you understood, and ask if they would like to keep narrowing it "
            "down."
        )
    if state.get("searched_everywhere"):
        notes["searched"] = "all of Bangladesh"
    if chest_is_possible(state.get("ambiguity_flags") or {}):
        notes["must_say"] = (
            f"If they have pain or pressure in their chest, they should call "
            f"{settings.EMERGENCY_NUMBER} now."
        )
    return notes


def _turn_notes(state: ConversationState) -> str:
    """Tells the writer what to do this turn. The patient never sees these."""
    action = state.get("action", "talk")
    language = {"en": "English", "bn": "Bangla script", "banglish": "Banglish in English letters"}
    notes: dict[str, Any] = {
        "write_in": language.get(state.get("language", "en"), "English"),
        "patient_seems": state.get("emotional_state", "calm"),
        "details_known": _known_details(state),
    }

    if state.get("crisis_active"):
        notes["patient_has_spoken_about_not_wanting_to_live"] = True
    if action == "ask":
        notes["ask_about"] = state.get("asking_about")
        if state.get("asking_about") == "clarify_meaning":
            notes["unclear_phrases"] = open_flags(state.get("ambiguity_flags") or {})
            notes["chips_should_offer"] = "emotional, physical, and both"
        if state.get("asking_about") == "care_preference":
            notes["chips_should_offer"] = "talking therapy, a medical evaluation, and either"
    elif action == "search":
        notes.update(_search_notes(state))
    elif action == "support":
        notes["do"] = "Stay gentle and present. Ask nothing. Offer help finding someone when ready."
    else:
        notes["do"] = "Respond to what they said. If it fits, ask what's been going on."

    if is_emotional(state.get("specialty_confidence") or {}) and state.get("physical_symptoms_too"):
        notes["physical_symptoms_too"] = True
    return f"{PERSONA}\n\n## Notes for this turn\n\n{json.dumps(notes, ensure_ascii=False)}"


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_END.split(text) if part.strip()]


def _sentence_key(sentence: str) -> str:
    return " ".join(_NOT_A_WORD.sub("", sentence.casefold()).split())


def _overlap(first: set[str], second: set[str]) -> float:
    return len(first & second) / len(first | second)


def repeated_sentences(reply: str, earlier: list[str]) -> list[str]:
    """Sentences in a reply that the assistant has already said, or nearly said."""
    said = [set(_sentence_key(s).split()) for text in earlier for s in _sentences(text)]
    repeats = []
    for sentence in _sentences(reply):
        words = set(_sentence_key(sentence).split())
        if len(words) >= SHORTEST_REPEATED_WORDS and any(
            _overlap(words, old) >= REPEAT_OVERLAP for old in said
        ):
            repeats.append(sentence)
    return repeats


def _wrong_language(reply: str, language: str) -> bool:
    return has_bangla_script(reply) != (language == "bn")


def _reply_problem(reply: str, earlier: list[str], language: str) -> str | None:
    """Why a reply must be rewritten. Only rule names here, never reply text."""
    violation = reply_violation(reply)
    if violation:
        return violation
    if repeated_sentences(reply, earlier):
        return "repeated_sentence"
    if _wrong_language(reply, language):
        return "wrong_language"
    return None


REWRITE_NOTES = {
    "diagnosis": "It named a condition or a possible cause. Name none.",
    "reassurance": "It reassured them. Do not say they will be fine or that it is not serious.",
    "prescription": "It named a medicine or treatment. Name none.",
    "human_claim": "It claimed feelings, a body or a human life. You are an AI. Claim none.",
    "repeated_sentence": "It repeated a sentence you already said. Use completely new words.",
    "wrong_language": "It was written in the wrong language or script. Follow write_in exactly.",
}


def _ask_writer(system_prompt: str, state: ConversationState) -> WriterTurn:
    try:
        return get_llm_client().generate_structured(
            messages=_recent_messages(
                state.get("messages", []), settings.LLM_WRITER_HISTORY_MESSAGES
            ),
            response_model=WriterTurn,
            system_prompt=system_prompt,
            temperature=settings.LLM_WRITER_TEMPERATURE,
            reasoning_effort=settings.LLM_WRITER_REASONING_EFFORT or None,
        )
    except ValueError as e:
        raise LLMUnavailableError("The model's reply could not be read") from e


def _final_reply(turn: WriterTurn, state: ConversationState, earlier: list[str]) -> WriterTurn:
    """A reply gets one rewrite. Unsafe text never goes out, and a repeat loses the sentence."""
    language = state.get("language", "en")
    problem = _reply_problem(turn.reply, earlier, language)
    if problem is None:
        return turn

    logger.warning(f"[OUTPUT GUARD] Rewriting a reply: {problem}")
    rewritten = _ask_writer(
        f"{_turn_notes(state)}\n\nYour last reply was rejected. {REWRITE_NOTES[problem]}", state
    )

    if reply_violation(rewritten.reply):
        logger.warning("[OUTPUT GUARD] Rewrite failed, using the fixed reply")
        return WriterTurn(reply=guard_fallback(language))

    repeats = repeated_sentences(rewritten.reply, earlier)
    kept = [sentence for sentence in _sentences(rewritten.reply) if sentence not in repeats]
    if repeats and kept:
        return rewritten.model_copy(update={"reply": " ".join(kept)})
    return rewritten


def _chips_for(turn: WriterTurn, state: ConversationState) -> list[dict[str, str]]:
    """At most four chips. Fixed labels mean the city and escape chips can always be matched."""
    if state.get("action") != "ask":
        return []
    language = state.get("language", "en")
    chips = [chip.model_dump() for chip in turn.chips if not reply_violation(chip.label)]
    chips = chips[:MAX_MODEL_CHIPS]
    if state.get("asking_about") == LOCATION:
        chips = [chip for chip in chips if chip["meaning"] != "any_city"][: MAX_MODEL_CHIPS - 1]
        chips.append(
            {"label": ANY_CITY_LABEL.get(language, ANY_CITY_LABEL["en"]), "meaning": "any_city"}
        )
    # question_count already includes this question, so the first one has no escape to offer
    if state.get("question_count", 0) >= 2:
        escape = SHOW_DOCTORS_LABEL.get(language, SHOW_DOCTORS_LABEL["en"])
        chips.append({"label": escape, "meaning": ESCAPE})
    return chips


def write_node(state: ConversationState) -> dict[str, Any]:
    """Writes the reply. With no model there is no reply to give, so this raises."""
    earlier = [
        m.get("content", "") for m in state.get("messages", []) if m.get("role") == "assistant"
    ]
    turn = _final_reply(_ask_writer(_turn_notes(state), state), state, earlier)
    chips = _chips_for(turn, state)

    action = state.get("action")
    if action == "search":
        step = "completed"
    elif action == "ask":
        step = "ask_followup"
    else:
        step = "conversation"

    return {
        "assistant_reply": turn.reply,
        "chips": [chip["label"] for chip in chips],
        "pending_chips": chips,
        "current_step": step,
    }


# ------------------------------------------------------------------------------
# Workflow Graph Construction
# ------------------------------------------------------------------------------


def build_symptom_graph(checkpointer: Any | None = None) -> Any:
    """Builds the symptom state machine. The API saves progress on the conversation row instead."""
    workflow = StateGraph(ConversationState)

    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("analyze", analyze_node)
    workflow.add_node("build_search_criteria", build_search_criteria_node)
    workflow.add_node("write", write_node)

    workflow.set_entry_point("safety_check")
    workflow.add_conditional_edges(
        "safety_check", route_after_safety, {"escalate": END, "continue": "analyze"}
    )
    workflow.add_conditional_edges(
        "analyze",
        route_after_analysis,
        {"escalate": END, "search": "build_search_criteria", "write": "write"},
    )
    workflow.add_edge("build_search_criteria", "write")
    workflow.add_edge("write", END)

    return workflow.compile(checkpointer=checkpointer)


# Singleton compiled graph
_COMPILED_GRAPH = None


def get_symptom_graph() -> Any:
    """Returns the compiled symptom graph."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_symptom_graph()
    return _COMPILED_GRAPH
