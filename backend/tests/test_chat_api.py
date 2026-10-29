"""API Integration Tests for AI Symptom Assistant Chat.

Verifies:
1. Unauthenticated requests to /chat/* return 401 Unauthorized.
2. Non-patient roles (e.g. Doctor) return 403 Forbidden.
3. POST /chat/conversations creates a conversation and returns initial message with mandatory disclaimer.
4. POST /chat/conversations/{id}/messages processes symptom consultation with LangGraph and returns assistant reply.
5. Emergency message triggers immediate 999 escalation with NO search criteria.
6. Patient isolation: Patient B cannot read or post to Patient A's conversation (403 Forbidden).
"""

import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient
import psycopg2
from conftest import create_mock_jwt
from app.ai.llm import LLMClient, set_llm_client
from app.ai.state import ExtractedSymptoms
from app.core.config import settings
from app.models.enums import UserRole


class MockChatLLMClient(LLMClient):
    """Deterministic Mock LLM client for API tests."""

    def __init__(self, extraction: ExtractedSymptoms):
        super().__init__(api_key="mock", model="mock")
        self.extraction = extraction

    def generate_structured(self, messages, response_model, system_prompt=None):
        return self.extraction


@pytest.fixture(scope="module")
def db_conn():
    conn = psycopg2.connect(settings.DATABASE_URL)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture
def chat_patients(db_conn):
    """Provisions two isolated test patients in auth.users and public.profiles."""
    patient_a_id = str(uuid.uuid4())
    patient_b_id = str(uuid.uuid4())
    email_a = f"chat_pat_a_{uuid.uuid4().hex[:8]}@medimatch.test"
    email_b = f"chat_pat_b_{uuid.uuid4().hex[:8]}@medimatch.test"

    cur = db_conn.cursor()
    cur.execute(
        """
        INSERT INTO auth.users (id, aud, role, email)
        VALUES 
            (%s, 'authenticated', 'authenticated', %s),
            (%s, 'authenticated', 'authenticated', %s)
        ON CONFLICT (id) DO NOTHING;
        """,
        (patient_a_id, email_a, patient_b_id, email_b),
    )
    cur.execute(
        """
        INSERT INTO public.profiles (id, role, full_name)
        VALUES 
            (%s, 'patient', 'Chat Patient Alice'),
            (%s, 'patient', 'Chat Patient Bob')
        ON CONFLICT (id) DO NOTHING;
        """,
        (patient_a_id, patient_b_id),
    )
    db_conn.commit()

    token_a = create_mock_jwt(patient_a_id, email_a, UserRole.PATIENT, "Chat Patient Alice")
    token_b = create_mock_jwt(patient_b_id, email_b, UserRole.PATIENT, "Chat Patient Bob")

    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    yield {
        "patient_a": {"id": patient_a_id, "headers": headers_a},
        "patient_b": {"id": patient_b_id, "headers": headers_b},
    }

    # Teardown
    try:
        cur.execute("DELETE FROM public.messages WHERE conversation_id IN (SELECT id FROM public.conversations WHERE patient_id IN (%s, %s));", (patient_a_id, patient_b_id))
        cur.execute("DELETE FROM public.patient_symptom_sessions WHERE patient_id IN (%s, %s);", (patient_a_id, patient_b_id))
        cur.execute("DELETE FROM public.conversations WHERE patient_id IN (%s, %s);", (patient_a_id, patient_b_id))
        cur.execute("DELETE FROM public.profiles WHERE id IN (%s, %s);", (patient_a_id, patient_b_id))
        cur.execute("DELETE FROM auth.users WHERE id IN (%s, %s);", (patient_a_id, patient_b_id))
        db_conn.commit()
    except Exception:
        db_conn.rollback()


@pytest.fixture(autouse=True)
def reset_llm():
    yield
    set_llm_client(LLMClient())


def test_unauthenticated_chat_endpoints_return_401(client: TestClient):
    """Anonymous requests to chat endpoints must be rejected with 401."""
    fake_conv_id = "00000000-0000-0000-0000-000000000000"

    res1 = client.post("/chat/conversations")
    assert res1.status_code == status.HTTP_401_UNAUTHORIZED

    res2 = client.post(f"/chat/conversations/{fake_conv_id}/messages", json={"content": "hello"})
    assert res2.status_code == status.HTTP_401_UNAUTHORIZED

    res3 = client.get(f"/chat/conversations/{fake_conv_id}")
    assert res3.status_code == status.HTTP_401_UNAUTHORIZED


def test_non_patient_role_forbidden_on_chat(client: TestClient, doctor_token: str):
    """Doctors must receive 403 Forbidden when attempting to start a symptom chat."""
    headers = {"Authorization": f"Bearer {doctor_token}"}
    res = client.post("/chat/conversations", headers=headers, json={"title": "Test Chat"})
    assert res.status_code == status.HTTP_403_FORBIDDEN


def test_create_conversation_returns_medical_disclaimer(client: TestClient, chat_patients: dict):
    """Creating a conversation seeds the initial message with the mandatory medical disclaimer."""
    patient = chat_patients["patient_a"]
    payload = {"title": "Headache Consultation"}

    res = client.post("/chat/conversations", headers=patient["headers"], json=payload)
    assert res.status_code == status.HTTP_201_CREATED
    data = res.json()

    assert data["patient_id"] == patient["id"]
    assert data["title"] == "Headache Consultation"
    assert "id" in data
    assert "initial_message" in data

    # Verify disclaimer contents
    init_msg = data["initial_message"]
    assert "Medical Disclaimer" in init_msg
    assert "AI assistant" in init_msg
    assert "not provide medical diagnosis" in init_msg
    assert "999" in init_msg

    # Also verify GET /chat/conversations/{id} returns this initial message
    conv_id = data["id"]
    get_res = client.get(f"/chat/conversations/{conv_id}", headers=patient["headers"])
    assert get_res.status_code == status.HTTP_200_OK
    history = get_res.json()
    assert len(history["messages"]) == 1
    assert history["messages"][0]["sender"] == "assistant"
    assert "Medical Disclaimer" in history["messages"][0]["content"]


def test_send_patient_message_processes_workflow(client: TestClient, chat_patients: dict):
    """Sending patient symptoms runs the LangGraph workflow and returns assistant recommendation."""
    patient = chat_patients["patient_a"]

    # 1. Create conversation
    create_res = client.post("/chat/conversations", headers=patient["headers"], json={"title": "Neurology Query"})
    assert create_res.status_code == status.HTTP_201_CREATED
    conv_id = create_res.json()["id"]

    # 2. Configure deterministic mock LLM
    mock_llm = MockChatLLMClient(
        ExtractedSymptoms(
            symptoms=["persistent migraine", "head throbbing"],
            duration="3 days",
            severity="moderate",
            location="Dhaka",
            candidate_specialty_names=["Neurology"],
        )
    )
    set_llm_client(mock_llm)

    # 3. Send message
    msg_payload = {"content": "I have had a throbbing migraine for 3 days in Dhaka."}
    msg_res = client.post(f"/chat/conversations/{conv_id}/messages", headers=patient["headers"], json=msg_payload)
    assert msg_res.status_code == status.HTTP_200_OK
    data = msg_res.json()

    assert data["conversation_id"] == conv_id
    assert data["current_step"] == "completed"
    assert data["search_criteria"] is not None
    assert "Neurology" in data["search_criteria"]["candidate_specialties"]
    assert data["search_criteria"]["city"] == "Dhaka"
    assert "Neurology" in data["assistant_reply"]


def test_emergency_message_triggers_immediate_alert(client: TestClient, chat_patients: dict):
    """Emergency phrases in patient message immediately return the 999 escalation alert."""
    patient = chat_patients["patient_a"]

    # 1. Create conversation
    create_res = client.post("/chat/conversations", headers=patient["headers"], json={"title": "Urgent Triage"})
    assert create_res.status_code == status.HTTP_201_CREATED
    conv_id = create_res.json()["id"]

    # 2. Send emergency message
    emergency_payload = {"content": "I have severe crushing chest pain radiating to left arm and cannot breathe!"}
    res = client.post(f"/chat/conversations/{conv_id}/messages", headers=patient["headers"], json=emergency_payload)
    assert res.status_code == status.HTTP_200_OK
    data = res.json()

    assert data["current_step"] == "emergency_escalated"
    assert data["search_criteria"] is None
    assert "EMERGENCY ALERT" in data["assistant_reply"]
    assert "999" in data["assistant_reply"]


def test_patient_isolation_forbidden_access(client: TestClient, chat_patients: dict):
    """Patient B must not be able to view or send messages to Patient A's conversation."""
    patient_a = chat_patients["patient_a"]
    patient_b = chat_patients["patient_b"]

    # 1. Patient A creates conversation
    create_res = client.post("/chat/conversations", headers=patient_a["headers"], json={"title": "Patient A Private Chat"})
    assert create_res.status_code == status.HTTP_201_CREATED
    conv_id_a = create_res.json()["id"]

    # 2. Patient B tries to read Patient A's conversation
    get_res = client.get(f"/chat/conversations/{conv_id_a}", headers=patient_b["headers"])
    assert get_res.status_code == status.HTTP_403_FORBIDDEN
    assert "You do not own this conversation" in get_res.json()["detail"]

    # 3. Patient B tries to post a message into Patient A's conversation
    post_res = client.post(
        f"/chat/conversations/{conv_id_a}/messages",
        headers=patient_b["headers"],
        json={"content": "Intruder message"},
    )
    assert post_res.status_code == status.HTTP_403_FORBIDDEN
    assert "You do not own this conversation" in post_res.json()["detail"]
