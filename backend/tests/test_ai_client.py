"""LLM client behaviour and exactly what leaves the server. Offline: transport is mocked."""

import json
import time
from collections.abc import Callable

import httpx
import pytest

from app.ai.graph import _recent_messages, build_symptom_graph
from app.ai.llm import LLMClient, LLMUnavailableError, set_llm_client
from app.ai.privacy import redact_pii
from app.ai.state import ConversationIntent, ExtractedSymptoms
from app.core.config import settings


def reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})


def client_with(handler: Callable[[httpx.Request], httpx.Response]) -> LLMClient:
    return LLMClient(api_key="k", model="m", transport=httpx.MockTransport(handler))


MESSAGES = [{"role": "user", "content": "headache"}]


@pytest.fixture(autouse=True)
def no_retry_delay(monkeypatch):
    monkeypatch.setattr("app.ai.llm.RETRY_WAIT_SECONDS", 0)


def test_timeout_is_short_enough_for_a_chat_turn():
    assert settings.LLM_TIMEOUT_SECONDS * settings.LLM_MAX_ATTEMPTS * 2 <= 60


@pytest.mark.parametrize("status", [429, 500, 502, 503])
def test_temporary_failures_are_retried(status):
    calls: list[int] = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(status) if len(calls) == 1 else reply("ok")

    assert client_with(handler).generate(MESSAGES) == "ok"
    assert len(calls) == 2


def test_timeouts_are_retried():
    calls: list[int] = []

    def handler(request):
        calls.append(1)
        if len(calls) == 1:
            raise httpx.ReadTimeout("slow", request=request)
        return reply("ok")

    assert client_with(handler).generate(MESSAGES) == "ok"


@pytest.mark.parametrize("status", [400, 401, 403])
def test_permanent_failures_are_not_retried(status):
    calls: list[int] = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(status)

    with pytest.raises(LLMUnavailableError):
        client_with(handler).generate(MESSAGES)
    assert len(calls) == 1


def test_gives_up_after_the_configured_attempts():
    calls: list[int] = []

    def handler(_request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(LLMUnavailableError):
        client_with(handler).generate(MESSAGES)
    assert len(calls) == settings.LLM_MAX_ATTEMPTS


def test_empty_model_reply_is_a_failure():
    def handler(_request):
        return httpx.Response(200, json={"choices": [{"message": {"content": None}}]})

    with pytest.raises(LLMUnavailableError):
        client_with(handler).generate(MESSAGES)


def test_missing_key_never_calls_the_provider():
    def handler(_request):
        raise AssertionError("must not be called")

    with pytest.raises(LLMUnavailableError):
        LLMClient(api_key="", model="m", transport=httpx.MockTransport(handler)).generate(MESSAGES)


def test_bad_json_is_a_failure_and_stays_out_of_the_error(caplog):
    secret_output = "private patient words"

    with caplog.at_level("DEBUG"), pytest.raises(ValueError) as exc:
        client_with(lambda _r: reply(secret_output)).generate_structured(
            MESSAGES, ConversationIntent
        )
    assert secret_output not in str(exc.value)
    assert secret_output not in caplog.text


def test_message_contents_are_never_logged(caplog):
    with caplog.at_level("DEBUG"):
        client_with(lambda _r: reply("ok")).generate(
            [{"role": "user", "content": "my secret symptom"}]
        )
    assert "my secret symptom" not in caplog.text


def test_production_asks_providers_not_to_keep_data(monkeypatch):
    bodies: list[dict] = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return reply("ok")

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    client_with(handler).generate(MESSAGES)
    assert bodies[0]["provider"]["data_collection"] == "deny"


def test_history_sent_to_the_model_is_bounded():
    messages = [{"role": "user", "content": str(i)} for i in range(200)]
    assert len(_recent_messages(messages)) == settings.LLM_HISTORY_MESSAGES
    assert _recent_messages(messages)[-1]["content"] == "199"


@pytest.mark.parametrize(
    "text, leaked",
    [
        ("My name is Rahim Uddin and I have a fever", "Rahim"),
        ("i'm rahim, fever for 2 days", "rahim"),
        ("call me Fatima please", "Fatima"),
        ("Rahim here. fever for 3 days", "Rahim"),
        ("amar nam Karim, jor hoyeche", "Karim"),
        ("আমার নাম করিম", "করিম"),
        ("আমি করিম, জ্বর", "করিম"),
        ("my wife Salma has a headache", "Salma"),
        ("my phone is +8801712345678", "1712345678"),
        ("my phone is 01712-345678", "345678"),
        ("my phone is ০১৭১২৩৪৫৬৭৮", "৩৪৫৬৭৮"),
        ("phone 017 1234 5678", "5678"),
        ("email karim@gmail.com", "karim@"),
        ("NID 1990123456789012", "1990123456789012"),
        ("I live at House 12, Road 5, Dhanmondi", "House 12"),
    ],
)
def test_identifiers_are_redacted(text, leaked):
    assert leaked not in redact_pii(text)


@pytest.mark.parametrize(
    "text, kept",
    [
        ("i'm tired and dizzy", "tired"),
        ("I am feeling sick", "sick"),
        ("i'm sick, please help", "sick"),
        ("fever for 3 days, 102 degrees", "102"),
        ("my blood pressure is 140/90", "140/90"),
        ("I live in Dhaka", "Dhaka"),
        ("my wife has a headache", "headache"),
    ],
)
def test_clinical_detail_survives_redaction(text, kept):
    assert kept in redact_pii(text)


def test_exact_text_sent_to_the_provider_holds_no_identifiers(monkeypatch):
    monkeypatch.setattr("app.ai.graph._get_verified_specialty_names", lambda: ["General Medicine"])
    monkeypatch.setattr("app.ai.graph._known_cities", lambda: ["Dhaka"])
    sent: list[str] = []

    def handler(request):
        sent.append(request.content.decode())
        body = json.loads(request.content)
        schema = body["messages"][0]["content"]
        if "possible_emergency" in schema:
            return reply(ConversationIntent(intent="symptom_update").model_dump_json())
        return reply(ExtractedSymptoms(symptoms=["headache"]).model_dump_json())

    set_llm_client(client_with(handler))
    try:
        state = {
            "conversation_id": "c",
            "patient_id": "patient-uuid-123",
            "messages": [
                {
                    "role": "user",
                    "content": "My name is Rahim Uddin, 01712345678, rahim@gmail.com, headache for 2 days",
                }
            ],
        }
        build_symptom_graph().invoke(state, config={"configurable": {"thread_id": "t"}})
    finally:
        set_llm_client(None)

    assert len(sent) == 2
    for body in sent:
        for identifier in ("Rahim", "01712345678", "rahim@gmail.com", "patient-uuid-123"):
            assert identifier not in body


class KeepAliveStream(httpx.SyncByteStream):
    """Behaves like OpenRouter holding a slow request open with keep-alive bytes."""

    def __iter__(self):
        for _ in range(50):
            time.sleep(0.02)
            yield b" "
        yield b'{"choices": [{"message": {"content": "too late"}}]}'


def test_keep_alive_bytes_cannot_stretch_the_deadline(monkeypatch):
    monkeypatch.setattr(settings, "LLM_TIMEOUT_SECONDS", 0.1)
    monkeypatch.setattr(settings, "LLM_MAX_ATTEMPTS", 1)

    def handler(_request):
        return httpx.Response(200, stream=KeepAliveStream())

    started = time.monotonic()
    with pytest.raises(LLMUnavailableError):
        client_with(handler).generate(MESSAGES)
    assert time.monotonic() - started < 0.5


def test_leading_keep_alive_bytes_do_not_break_parsing():
    def handler(_request):
        return httpx.Response(
            200, content=b"   \n" + b'{"choices": [{"message": {"content": "ok"}}]}'
        )

    assert client_with(handler).generate(MESSAGES) == "ok"
