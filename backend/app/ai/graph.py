"""LangGraph Symptom Consultation Workflow.

Predictable, safe conversation workflow collecting symptoms and generating
structured doctor-search criteria without diagnosing or prescribing.
"""

import logging
from typing import Any, Dict, List, Optional
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from app.ai.llm import get_llm_client
from app.ai.privacy import redact_pii
from app.ai.safety import check_emergency, get_emergency_response, output_guard
from app.ai.state import ConversationState, ExtractedSymptoms, SearchCriteria
from app.core.config import settings
from app.core.supabase import get_supabase_admin_client, get_supabase_client

logger = logging.getLogger("medimatch.ai.graph")


def _get_verified_specialty_names() -> List[str]:
    """Fetch all verified specialty names directly from the Supabase database."""
    client = get_supabase_admin_client() or get_supabase_client()
    default_specialties = ["Neurology", "Cardiology", "General Medicine"]
    if not client:
        return default_specialties

    try:
        res = client.table("specialties").select("name").execute()
        if res.data:
            return [row["name"] for row in res.data]
    except Exception as e:
        logger.warning(f"Could not load specialties from DB, using defaults: {e}")

    return default_specialties


# ------------------------------------------------------------------------------
# Node 1: Safety Check (Rule-based deterministic emergency triage)
# ------------------------------------------------------------------------------

def safety_check_node(state: ConversationState) -> Dict[str, Any]:
    """Inspects the most recent patient message for emergency patterns."""
    messages = state.get("messages", [])
    if not messages:
        return {"safety_status": "safe", "current_step": "safety_check"}

    latest_msg = messages[-1].get("content", "")
    is_emergency, category, matched = check_emergency(latest_msg)

    if is_emergency:
        alert_msg = get_emergency_response()
        return {
            "safety_status": "emergency",
            "current_step": "emergency_escalated",
            "assistant_reply": alert_msg,
            "search_criteria": None,
        }

    return {"safety_status": "safe", "current_step": "safety_check"}


def should_escalate_emergency(state: ConversationState) -> str:
    """Conditional edge router: short-circuits workflow immediately on emergency."""
    if state.get("safety_status") == "emergency":
        return "escalate"
    return "continue"


# ------------------------------------------------------------------------------
# Node 2: Extract Symptoms (PII-redacted structured extraction)
# ------------------------------------------------------------------------------

def extract_symptoms_node(state: ConversationState) -> Dict[str, Any]:
    """Redacts PII and extracts structured symptoms via LLM."""
    raw_messages = state.get("messages", [])

    # Redact all messages before submitting to LLM
    sanitized_messages = [
        {"role": m.get("role", "user"), "content": redact_pii(m.get("content", ""))}
        for m in raw_messages
    ]

    system_prompt = (
        "You are an assistant for MediMatch AI, a doctor-matching platform in Bangladesh.\n"
        "Your task is to extract clinical symptoms, duration, severity, patient age group, "
        "location/city (default Dhaka if in Bangladesh), and candidate specialties.\n"
        "Available specialties are: Neurology, Cardiology, General Medicine.\n"
        "CRITICAL RULE: NEVER diagnose a disease, NEVER prescribe medication, and NEVER reassure "
        "that symptoms are harmless."
    )

    llm = get_llm_client()
    try:
        extraction: ExtractedSymptoms = llm.generate_structured(
            messages=sanitized_messages,
            response_model=ExtractedSymptoms,
            system_prompt=system_prompt,
        )
    except Exception as e:
        logger.error(f"Structured extraction fallback: {e}")
        extraction = ExtractedSymptoms(
            symptoms=[sanitized_messages[-1]["content"][:100]] if sanitized_messages else [],
            candidate_specialty_names=["General Medicine"],
        )

    # Merge newly extracted details into existing state
    existing_symptoms = list(state.get("symptoms", []))
    for s in extraction.symptoms:
        if s and s not in existing_symptoms:
            existing_symptoms.append(s)

    duration = extraction.duration or state.get("duration")
    severity = extraction.severity or state.get("severity")
    location = extraction.location or state.get("location")
    max_fee = extraction.preferred_max_fee or state.get("preferred_max_fee")

    return {
        "symptoms": existing_symptoms,
        "duration": duration,
        "severity": severity,
        "location": location,
        "preferred_max_fee": max_fee,
        "current_step": "extract_symptoms",
    }


# ------------------------------------------------------------------------------
# Node 3: Check Missing Fields (Deterministic Python code, NOT LLM)
# ------------------------------------------------------------------------------

def check_missing_node(state: ConversationState) -> Dict[str, Any]:
    """Evaluates whether essential information is missing to formulate search criteria."""
    missing: List[str] = []

    symptoms = state.get("symptoms", [])
    if not symptoms:
        missing.append("symptoms")

    if not state.get("duration"):
        missing.append("duration")

    if not state.get("location"):
        missing.append("location")

    return {
        "missing_fields": missing,
        "current_step": "check_missing",
    }


def route_after_check_missing(state: ConversationState) -> str:
    """Decides whether to ask a follow-up or finalize criteria."""
    missing = state.get("missing_fields", [])
    followup_count = state.get("followup_count", 0)

    # If info is missing and we haven't reached the 3-round cap, ask follow-up
    if missing and followup_count < 3:
        return "ask_followup"
    return "build_search_criteria"


# ------------------------------------------------------------------------------
# Node 4: Ask Follow-up (Single question, max 3 rounds, output guarded)
# ------------------------------------------------------------------------------

def ask_followup_node(state: ConversationState) -> Dict[str, Any]:
    """Generates ONE single clarifying question for the highest-priority missing field."""
    missing = state.get("missing_fields", [])
    target_field = missing[0] if missing else "duration"
    followup_count = state.get("followup_count", 0) + 1

    question_templates = {
        "symptoms": "Could you please describe what specific symptoms or discomfort you are experiencing?",
        "duration": "How long have you been experiencing these symptoms (e.g. hours, days, weeks)?",
        "location": "Which city or area in Bangladesh are you looking to visit a doctor in (e.g. Dhaka, Chittagong)?",
        "severity": "How severe is your discomfort right now (mild, moderate, or severe)?",
    }

    base_question = question_templates.get(
        target_field,
        "Could you tell me a little more about how long this has been happening and your preferred location?",
    )

    # Always pass through output guard to ensure non-diagnostic phrasing
    safe_question = output_guard(base_question)

    return {
        "followup_count": followup_count,
        "assistant_reply": safe_question,
        "current_step": "ask_followup",
    }


# ------------------------------------------------------------------------------
# Node 5: Build Search Criteria (Mapped ONLY to verified DB specialties)
# ------------------------------------------------------------------------------

def build_search_criteria_node(state: ConversationState) -> Dict[str, Any]:
    """Finalizes search criteria mapped strictly to DB specialties with General Medicine fallback."""
    verified_specialties = _get_verified_specialty_names()
    symptoms = state.get("symptoms", [])
    location = state.get("location") or "Dhaka"
    max_fee = state.get("preferred_max_fee")

    # Map symptoms to verified specialties
    candidate_specialties: List[str] = []
    symptoms_text = " ".join(symptoms).lower()

    # Rule-based / semantic mapping to verified specialties
    if any(k in symptoms_text for k in ["headache", "migraine", "dizziness", "seizure", "numbness", "nerve", "neuro", "brain"]):
        for spec in verified_specialties:
            if "neuro" in spec.lower() and spec not in candidate_specialties:
                candidate_specialties.append(spec)

    if any(k in symptoms_text for k in ["heart", "cardio", "chest", "palpitation", "high blood pressure", "hypertension"]):
        for spec in verified_specialties:
            if "cardio" in spec.lower() and spec not in candidate_specialties:
                candidate_specialties.append(spec)

    # General Medicine fallback if no specialty identified or as co-candidate
    if not candidate_specialties or any(k in symptoms_text for k in ["fever", "cough", "cold", "pain", "fatigue", "general"]):
        for spec in verified_specialties:
            if "general" in spec.lower() or "medicine" in spec.lower():
                if spec not in candidate_specialties:
                    candidate_specialties.append(spec)

    # Absolute fallback
    if not candidate_specialties:
        candidate_specialties = ["General Medicine"]

    criteria = SearchCriteria(
        candidate_specialties=candidate_specialties,
        city=location,
        max_fee=max_fee,
        keywords=symptoms[:5],
    )

    specialty_names = ", ".join(candidate_specialties)
    reply = (
        f"Thank you for sharing your symptoms. Based on what you described, I recommend consulting a "
        f"specialist in **{specialty_names}** in **{location}**.\n\n"
        f"I have prepared your search criteria. You can now browse verified doctors and book an appointment."
    )

    return {
        "search_criteria": criteria.model_dump(),
        "assistant_reply": reply,
        "current_step": "completed",
    }


# ------------------------------------------------------------------------------
# Workflow Graph Construction & Checkpointer
# ------------------------------------------------------------------------------

def build_symptom_graph(checkpointer: Optional[Any] = None) -> Any:
    """Builds and compiles the LangGraph symptom assessment state machine."""
    workflow = StateGraph(ConversationState)

    # Register nodes
    workflow.add_node("safety_check", safety_check_node)
    workflow.add_node("extract_symptoms", extract_symptoms_node)
    workflow.add_node("check_missing", check_missing_node)
    workflow.add_node("ask_followup", ask_followup_node)
    workflow.add_node("build_search_criteria", build_search_criteria_node)

    # Entry point
    workflow.set_entry_point("safety_check")

    # Conditional safety routing
    workflow.add_conditional_edges(
        "safety_check",
        should_escalate_emergency,
        {
            "escalate": END,
            "continue": "extract_symptoms",
        },
    )

    # extract_symptoms -> check_missing
    workflow.add_edge("extract_symptoms", "check_missing")

    # check_missing -> ask_followup OR build_search_criteria
    workflow.add_conditional_edges(
        "check_missing",
        route_after_check_missing,
        {
            "ask_followup": "ask_followup",
            "build_search_criteria": "build_search_criteria",
        },
    )

    # ask_followup -> END
    workflow.add_edge("ask_followup", END)

    # build_search_criteria -> END
    workflow.add_edge("build_search_criteria", END)

    # Default to MemorySaver if no checkpointer provided
    cp = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=cp)


# Singleton compiled graph
_COMPILED_GRAPH = None


def get_symptom_graph() -> Any:
    """Returns the compiled symptom graph."""
    global _COMPILED_GRAPH
    if _COMPILED_GRAPH is None:
        _COMPILED_GRAPH = build_symptom_graph()
    return _COMPILED_GRAPH

