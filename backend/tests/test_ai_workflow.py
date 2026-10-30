"""Workflow Tests for LangGraph Symptom Assistant.

Verifies:
1. Scripted end-to-end conversation extracting symptoms, duration, location, and producing search criteria.
2. Missing information correctly triggers single follow-up questions.
3. Max 3 follow-up rounds before falling back to default search criteria.
4. Emergency input immediately bypasses extraction and triggers emergency alert.
5. Specialty mapping strictly uses verified database specialties with General Medicine fallback.
"""

from typing import Any, Dict, List, Optional, Type
import pytest
from app.ai.graph import build_symptom_graph
from app.ai.llm import LLMClient, set_llm_client
from app.ai.state import ExtractedSymptoms
from langgraph.checkpoint.memory import MemorySaver


class MockLLMClient(LLMClient):
    """Deterministic Mock LLM client for testing the workflow."""

    def __init__(self, extraction_response: Optional[ExtractedSymptoms] = None):
        super().__init__(api_key="mock", model="mock")
        self.extraction_response = extraction_response or ExtractedSymptoms(
            symptoms=["headache"],
            duration="3 days",
            location="Dhaka",
            candidate_specialty_names=["Neurology"],
        )

    def generate_structured(
        self,
        messages: List[Dict[str, str]],
        response_model: Type[Any],
        system_prompt: Optional[str] = None,
    ) -> Any:
        return self.extraction_response


@pytest.fixture(autouse=True)
def restore_default_llm():
    """Ensure LLM client is reset after each test."""
    yield
    set_llm_client(LLMClient())


def test_complete_symptom_flow_produces_search_criteria():
    """When patient provides symptoms, duration, and location in one message,

    the workflow immediately forms search criteria with candidate specialty.
    """
    mock_client = MockLLMClient(
        ExtractedSymptoms(
            symptoms=["severe migraine", "throbbing head pain"],
            duration="4 days",
            severity="severe",
            location="Dhaka",
            candidate_specialty_names=["Neurology"],
        )
    )
    set_llm_client(mock_client)

    graph = build_symptom_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_conv_complete_1"}}

    state_input = {
        "conversation_id": "test_conv_complete_1",
        "patient_id": "test_patient_1",
        "messages": [
            {
                "role": "user",
                "content": "I have had a severe throbbing headache for 4 days in Dhaka.",
            }
        ],
    }

    result = graph.invoke(state_input, config=config)

    assert result["safety_status"] == "safe"
    assert result["current_step"] == "completed"
    assert result["search_criteria"] is not None
    criteria = result["search_criteria"]
    assert criteria["city"] == "Dhaka"
    assert "Neurology" in criteria["candidate_specialties"]
    assert "severe migraine" in criteria["keywords"] or "throbbing head pain" in criteria["keywords"]
    assert "Neurology" in result["assistant_reply"]


def test_missing_fields_trigger_followup_question():
    """When patient message is missing duration and location,

    the workflow asks ONE follow-up question and does not complete search criteria yet.
    """
    mock_client = MockLLMClient(
        ExtractedSymptoms(
            symptoms=["mild nausea"],
            duration=None,
            location=None,
            candidate_specialty_names=["General Medicine"],
        )
    )
    set_llm_client(mock_client)

    graph = build_symptom_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_conv_missing_1"}}

    state_input = {
        "conversation_id": "test_conv_missing_1",
        "patient_id": "test_patient_2",
        "messages": [
            {
                "role": "user",
                "content": "I feel nauseous and dizzy.",
            }
        ],
    }

    result = graph.invoke(state_input, config=config)

    assert result["current_step"] == "ask_followup"
    assert result["followup_count"] == 1
    assert result.get("search_criteria") is None
    # Follow-up should inquire about missing info (duration or location)
    reply = result["assistant_reply"]
    assert "?" in reply
    assert "how long" in reply.lower() or "duration" in reply.lower() or "when" in reply.lower()


def test_max_three_followup_rounds_enforcement():
    """After 3 follow-up attempts without all info,

    the workflow stops asking and proceeds to build search criteria using defaults.
    """
    mock_client = MockLLMClient(
        ExtractedSymptoms(
            symptoms=["persistent cough"],
            duration=None,
            location=None,
            candidate_specialty_names=["General Medicine"],
        )
    )
    set_llm_client(mock_client)

    graph = build_symptom_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_conv_max_rounds"}}

    # Simulate state at 3 previous follow-up questions
    state_input = {
        "conversation_id": "test_conv_max_rounds",
        "patient_id": "test_patient_3",
        "symptoms": ["persistent cough"],
        "duration": None,
        "location": None,
        "followup_count": 3,  # Already asked 3 questions
        "messages": [
            {"role": "user", "content": "I just keep coughing."},
        ],
    }

    result = graph.invoke(state_input, config=config)

    # Workflow must now proceed to completed instead of asking a 4th question
    assert result["current_step"] == "completed"
    assert result["search_criteria"] is not None
    criteria = result["search_criteria"]
    # Falls back to default city Dhaka and General Medicine
    assert criteria["city"] == "Dhaka"
    assert "General Medicine" in criteria["candidate_specialties"]


def test_emergency_message_short_circuits_workflow():
    """When an emergency phrase is detected, the graph terminates immediately

    at safety_check, returns the emergency escalation alert, and generates NO search criteria.
    """
    graph = build_symptom_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_conv_emergency"}}

    state_input = {
        "conversation_id": "test_conv_emergency",
        "patient_id": "test_patient_4",
        "messages": [
            {"role": "user", "content": "I have severe crushing chest pain and cannot breathe!"},
        ],
    }

    result = graph.invoke(state_input, config=config)

    assert result["safety_status"] == "emergency"
    assert result["current_step"] == "emergency_escalated"
    assert result.get("search_criteria") is None
    assert "EMERGENCY ALERT" in result["assistant_reply"]
    assert "999" in result["assistant_reply"]


def test_specialty_mapping_fallback_to_general_medicine():
    """Unrecognized or vague symptoms safely map to General Medicine."""
    mock_client = MockLLMClient(
        ExtractedSymptoms(
            symptoms=["general fatigue and low energy"],
            duration="1 week",
            location="Sylhet",
            candidate_specialty_names=[],
        )
    )
    set_llm_client(mock_client)

    graph = build_symptom_graph(checkpointer=MemorySaver())
    config = {"configurable": {"thread_id": "test_conv_fallback"}}

    state_input = {
        "conversation_id": "test_conv_fallback",
        "patient_id": "test_patient_5",
        "messages": [
            {"role": "user", "content": "Feeling very tired for 1 week in Sylhet"},
        ],
    }

    result = graph.invoke(state_input, config=config)

    assert result["current_step"] == "completed"
    criteria = result["search_criteria"]
    assert "General Medicine" in criteria["candidate_specialties"]
    assert criteria["city"] == "Sylhet"

