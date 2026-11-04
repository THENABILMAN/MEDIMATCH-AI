"""Assistant progress lives with the conversation, not in the server process."""

import uuid

import pytest
from conftest import create_mock_jwt

from app.ai import graph
from app.ai.llm import LLMClient, set_llm_client
from app.ai.state import AssistantTurn
from app.core.supabase import get_supabase_admin_client
from app.models.enums import UserRole


class NoDetailsLLM(LLMClient):
    """Never finds a duration or location, so every turn needs a follow-up."""

    def __init__(self):
        super().__init__(api_key="mock", model="mock")

    def generate_structured(self, messages, response_model, system_prompt=None):
        return AssistantTurn(
            reply="How long has this been going on?",
            symptoms=["itchy skin"],
            candidate_specialty_names=["General Medicine"],
            asking_about="duration",
        )


@pytest.fixture
def patient_headers() -> dict:
    token = create_mock_jwt(str(uuid.uuid4()), "p@tests.invalid", UserRole.PATIENT, "Pat")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def mock_llm():
    set_llm_client(NoDetailsLLM())
    yield
    set_llm_client(None)


def restart_server(monkeypatch) -> None:
    """Throws away everything held in process, as a restart or a different worker would."""
    monkeypatch.setattr(graph, "_COMPILED_GRAPH", None)


def send(client, headers, conversation, text="itchy skin"):
    res = client.post(
        f"/chat/conversations/{conversation}/messages", headers=headers, json={"content": text}
    )
    assert res.status_code == 200
    return res.json()


def test_follow_up_limit_survives_a_restart(client, patient_headers, monkeypatch):
    conversation = client.post("/chat/conversations", headers=patient_headers, json={}).json()["id"]

    for _ in range(3):
        assert send(client, patient_headers, conversation)["current_step"] == "ask_followup"
        restart_server(monkeypatch)

    assert send(client, patient_headers, conversation)["current_step"] == "completed"


def test_saved_state_holds_progress_but_no_messages(client, patient_headers):
    conversation = client.post("/chat/conversations", headers=patient_headers, json={}).json()["id"]
    send(client, patient_headers, conversation)

    row = (
        get_supabase_admin_client()
        .table("conversations")
        .select("graph_state")
        .eq("id", conversation)
        .execute()
    )
    state = row.data[0]["graph_state"]
    assert state["followup_count"] == 1
    assert "messages" not in state


def test_erasing_history_removes_saved_state(client, patient_headers):
    conversation = client.post("/chat/conversations", headers=patient_headers, json={}).json()["id"]
    send(client, patient_headers, conversation)
    assert client.delete("/me/conversations", headers=patient_headers).status_code == 200

    admin = get_supabase_admin_client()
    assert admin.table("conversations").select("id").eq("id", conversation).execute().data == []
    assert (
        admin.table("messages").select("id").eq("conversation_id", conversation).execute().data
        == []
    )
