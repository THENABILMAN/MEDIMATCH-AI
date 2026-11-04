"""The API contract, checked against what the web app actually calls."""

import re
from pathlib import Path

import pytest

from app.main import app

WEB_CLIENT = Path(__file__).resolve().parents[2] / "web" / "src" / "api" / "client.ts"
UNDOCUMENTED_BODY_OK = {("delete", "/doctors/me/slots/{slot_id}")}


@pytest.fixture(scope="module")
def schema() -> dict:
    return app.openapi()


def web_paths() -> set:
    source = WEB_CLIENT.read_text(encoding="utf-8")
    found = set(
        re.findall(r"""request<[^(]*\(\s*[`'"](/[^`'"?$]*(?:\$\{[^}]+\}[^`'"?$]*)*)""", source)
    )
    found |= set(re.findall(r"\$\{API_BASE\}(/[a-z/-]+)", source))
    return {re.sub(r"\$\{[^}]+\}", "{id}", path.split("${query")[0]) for path in found}


def normalize(path: str) -> str:
    return re.sub(r"\{[^}]+\}", "{id}", path)


def test_web_client_paths_were_found():
    assert len(web_paths()) > 25


def test_every_path_the_web_app_calls_exists(schema):
    available = {normalize(path) for path in schema["paths"]}
    assert web_paths() - available == set()


def test_every_operation_has_a_typed_response(schema):
    untyped = []
    for path, methods in schema["paths"].items():
        for method, operation in methods.items():
            success = [code for code in operation["responses"] if code.startswith("2")]
            content = operation["responses"][success[0]].get("content", {})
            body = content.get("application/json", {}).get("schema", {})
            if (
                (method, path) in UNDOCUMENTED_BODY_OK
                or path == "/ready"
                or path.startswith("/test-")
            ):
                continue
            if not body or body == {"type": "object"} or body.get("additionalProperties") is True:
                untyped.append(f"{method.upper()} {path}")
    assert untyped == []


def test_errors_are_documented(schema):
    operation = schema["paths"]["/appointments"]["post"]
    assert "#/components/schemas/ErrorResponse" in str(operation["responses"]["409"])
    assert "#/components/schemas/ErrorResponse" in str(operation["responses"]["401"])


def test_docs_list_each_operation_once(schema):
    assert not any(path.startswith("/api/v1") for path in schema["paths"])


def test_v1_paths_still_work(client):
    assert client.get("/api/v1/health").status_code == 200


def test_operation_ids_are_unique(schema):
    ids = [op["operationId"] for methods in schema["paths"].values() for op in methods.values()]
    assert len(ids) == len(set(ids))


def test_conversations_do_not_expose_saved_state(client, patient_token):
    headers = {"Authorization": f"Bearer {patient_token}"}
    client.post("/chat/conversations", headers=headers, json={})
    rows = client.get("/chat/conversations", headers=headers).json()
    assert rows
    assert "graph_state" not in rows[0]


def test_public_doctor_never_exposes_private_fields(client):
    doctor = client.get("/doctors/search").json()["items"][0]
    for field in ("user_id", "phone", "sync_status", "file_path", "credentials"):
        assert field not in doctor
