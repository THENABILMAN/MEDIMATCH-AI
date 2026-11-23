"""The local model client and text redaction. Offline: transport is mocked."""

import json
from collections.abc import Callable

import httpx
import pytest
from scripted_llm import assessment

from app.ai.llm import LLMClient, LLMUnavailableError
from app.ai.privacy import redact_pii
from app.ai.state import Assessment
from app.core.config import settings

MESSAGES = [{"role": "user", "content": "private headache"}]


def reply(content: str) -> httpx.Response:
    return httpx.Response(200, json={"message": {"content": content}})


def client_with(handler: Callable[[httpx.Request], httpx.Response]) -> LLMClient:
    return LLMClient(transport=httpx.MockTransport(handler))


def test_it_calls_the_configured_local_model():
    seen: list[dict] = []

    def handler(request):
        seen.append(json.loads(request.content))
        assert str(request.url).startswith(settings.OLLAMA_URL)
        return reply(" hello ")

    assert client_with(handler).generate(MESSAGES, "be kind") == "hello"
    assert seen[0]["model"] == settings.LLM_MODEL
    assert seen[0]["messages"][0] == {"role": "system", "content": "be kind"}


def test_structured_output_sends_its_schema_and_is_validated():
    answer = assessment(findings=["fever"])

    def handler(request):
        assert json.loads(request.content)["format"]["properties"]["new_findings"]
        return reply(answer.model_dump_json())

    assert client_with(handler).generate_structured(MESSAGES, "x", Assessment) == answer


def test_bad_json_is_tried_twice_then_fails_without_leaking(caplog):
    calls: list[int] = []

    def handler(_request):
        calls.append(1)
        return reply("{secret words")

    with caplog.at_level("DEBUG"), pytest.raises(LLMUnavailableError) as error:
        client_with(handler).generate_structured(MESSAGES, "x", Assessment)
    assert len(calls) == 2
    assert "secret" not in caplog.text + str(error.value)
    assert "headache" not in caplog.text


@pytest.mark.parametrize("answer", [httpx.Response(500), reply(""), httpx.Response(200, text="no")])
def test_a_failed_call_is_unavailable(answer):
    with pytest.raises(LLMUnavailableError):
        client_with(lambda _r: answer).generate(MESSAGES, "x")


def test_ollama_not_running_is_unavailable():
    def handler(_request):
        raise httpx.ConnectError("refused")

    with pytest.raises(LLMUnavailableError):
        client_with(handler).generate(MESSAGES, "x")


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
