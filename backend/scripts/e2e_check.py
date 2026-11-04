"""End-to-end check of the whole product journey against a running server.

Uses real tokens, the real embedding provider and index, and the real LLM. Point it at a local stack:
the API must be on localhost and the database must be local Supabase. The one doctor it indexes in
Pinecone is removed again when it suspends that doctor at the end.

Usage:
    python backend/scripts/e2e_check.py --api http://127.0.0.1:8010
"""

import argparse
import concurrent.futures
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.search.sync import get_pinecone_index

PASSWORD = "e2e-long-password-1"
ADMIN = ("admin@medimatch.test", "Admin123!Safe")
SUSPENDED_DOCTOR = "d2000000-0000-0000-0000-000000000009"
NEUROLOGY = "11111111-0000-0000-0000-000000000001"
PDF = b"%PDF-1.4 end to end test document"


class Journey:
    def __init__(self, api: str) -> None:
        self.http = httpx.Client(base_url=api, timeout=90)
        self.failures = 0

    def step(self, label: str, passed: bool, detail: Any = "") -> None:
        print(f"[{'PASS' if passed else 'FAIL'}] {label} {detail}")
        self.failures += 0 if passed else 1

    def sign_in(self, email: str, password: str) -> dict[str, str]:
        res = self.http.post("/auth/login", json={"email": email, "password": password})
        res.raise_for_status()
        return {"Authorization": f"Bearer {res.json()['access_token']}"}

    def register(self, kind: str, **extra: Any) -> dict[str, Any]:
        email = f"e2e-{kind}-{uuid.uuid4().hex[:10]}@example.com"
        body = {"email": email, "password": PASSWORD, "full_name": f"E2E {kind.title()}", **extra}
        res = self.http.post(f"/auth/register-{kind}", json=body)
        self.step(f"register {kind}", res.status_code == 201, res.status_code)
        res.raise_for_status()
        return {
            "id": res.json()["user_id"],
            "email": email,
            "headers": self.sign_in(email, PASSWORD),
        }


def wait_for(condition: Any, seconds: float = 45) -> bool:
    deadline = time.time() + seconds
    while time.time() < deadline:
        if condition():
            return True
        time.sleep(1)
    return False


def vector_exists(doctor_id: str) -> bool:
    return doctor_id in get_pinecone_index().fetch(ids=[doctor_id]).vectors


def run(api: str) -> int:
    j = Journey(api)
    created: list[str] = []
    try:
        return journey(j, created)
    finally:
        # A run that stops early must not leave its doctor in the real index
        if created:
            get_pinecone_index().delete(ids=created)


def journey(j: Journey, created: list[str]) -> int:
    admin = j.sign_in(*ADMIN)

    # Doctor signs up, completes a profile and uploads a credential
    doctor = j.register("doctor", city="Dhaka", specialty_ids=[NEUROLOGY])
    res = j.http.put(
        "/doctors/me/profile",
        headers=doctor["headers"],
        json={
            "bio": "Consultant neurologist treating migraine, headache, seizures and nerve pain.",
            "qualifications": ["MBBS", "FCPS (Neurology)"],
            "years_experience": 14,
            "consultation_fee": 1200,
            "clinic_name": "E2E Clinic",
            "city": "Dhaka",
            "specialty_ids": [NEUROLOGY],
        },
    )
    j.step("doctor saves profile", res.status_code == 200, res.status_code)
    doctor_id = res.json()["id"]
    created.append(doctor_id)

    res = j.http.post(
        "/doctors/me/credentials",
        headers=doctor["headers"],
        data={"document_type": "bmdc_license"},
        files={"file": ("licence.pdf", PDF, "application/pdf")},
    )
    j.step("doctor uploads credential", res.status_code == 200, res.status_code)
    credential = res.json()["id"]

    j.step("pending doctor is not public", j.http.get(f"/doctors/{doctor_id}").status_code == 404)

    # Admin reviews the file and approves
    link = j.http.get(f"/doctors/credentials/{credential}/url", headers=admin)
    j.step("admin gets a signed link", link.status_code == 200, link.status_code)
    url = link.json()["url"]
    if url.startswith("/"):
        url = os.environ["SUPABASE_URL"] + "/storage/v1" + url
    j.step("signed link opens the file", httpx.get(url).content == PDF)

    res = j.http.post(f"/admin/doctors/{doctor_id}/approve", headers=admin, json={})
    j.step("admin approves doctor", res.status_code == 200, res.status_code)
    j.step("approved doctor is public", j.http.get(f"/doctors/{doctor_id}").status_code == 200)
    j.step("vector appears in Pinecone", wait_for(lambda: vector_exists(doctor_id)))

    # Doctor opens a slot
    start = time.time() + 86400 * 3
    iso = lambda t: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(t))  # noqa: E731
    res = j.http.post(
        "/doctors/me/slots",
        headers=doctor["headers"],
        json={"start_time": iso(start), "end_time": iso(start + 1800)},
    )
    j.step("doctor creates a slot", res.status_code == 201, res.status_code)
    slot = res.json()["id"]

    # Patient chats and gets recommendations
    patient = j.register("patient")
    chat = j.http.post("/chat/conversations", headers=patient["headers"], json={}).json()["id"]
    url_chat = f"/chat/conversations/{chat}/messages"
    refused = j.http.post(url_chat, headers=patient["headers"], json={"content": "headache"})
    j.step("chat refused before consent", refused.status_code == 403, refused.status_code)

    j.http.patch("/me", headers=patient["headers"], json={"ai_consent": True})
    reply: dict[str, Any] = {}
    for text in (
        "I have had a throbbing headache on one side",
        "for about two weeks",
        "I am in Dhaka",
        "moderate",
    ):
        reply = j.http.post(url_chat, headers=patient["headers"], json={"content": text}).json()
        print(f"       step={reply.get('current_step')} followup={reply.get('followup_field')}")
        if reply.get("current_step") == "completed":
            break
    j.step("assistant reaches recommendations", reply.get("current_step") == "completed")

    recommended = [r["id"] for r in reply.get("recommendations") or []]
    j.step("recommendations returned", bool(recommended), f"{len(recommended)} doctors")
    j.step("suspended doctor absent", SUSPENDED_DOCTOR not in recommended)
    res = j.http.post(
        "/recommendations",
        headers=patient["headers"],
        json={
            "candidate_specialties": ["Neurology"],
            "city": "Dhaka",
            "keywords": ["migraine"],
            "top_k": 10,
        },
    )
    direct = res.json()
    j.step("search used vectors", direct["retrieval_mode"] == "hybrid", direct["retrieval_mode"])
    ids = [r["id"] for r in direct["recommendations"]]
    j.step("new doctor is recommended", doctor_id in ids)
    j.step("suspended doctor absent from direct search", SUSPENDED_DOCTOR not in ids)

    emergency = j.http.post(
        url_chat, headers=patient["headers"], json={"content": "my chest hurts and I can't breathe"}
    ).json()
    j.step(
        "emergency gets the alert and no doctors",
        emergency.get("is_emergency") is True and not emergency.get("recommendations"),
    )

    # Booking, and a double-booking attempt
    res = j.http.post("/appointments", headers=patient["headers"], json={"slot_id": slot})
    j.step("patient books the slot", res.status_code == 201, res.status_code)
    appointment = res.json()["id"]

    rival = j.register("patient")
    with concurrent.futures.ThreadPoolExecutor(10) as pool:
        codes = list(
            pool.map(
                lambda _: (
                    j.http.post(
                        "/appointments", headers=rival["headers"], json={"slot_id": slot}
                    ).status_code
                ),
                range(10),
            )
        )
    j.step("double booking refused", set(codes) == {409}, codes)

    # Patient removes their data
    res = j.http.post(f"/appointments/{appointment}/cancel", headers=patient["headers"], json={})
    j.step("patient cancels", res.status_code == 200, res.status_code)
    res = j.http.delete("/me/conversations", headers=patient["headers"])
    j.step("chat history erased", res.status_code == 200, res.json())
    res = j.http.get(f"/chat/conversations/{chat}", headers=patient["headers"])
    j.step("messages are gone", res.status_code == 404, res.status_code)
    res = j.http.delete("/me", headers=patient["headers"])
    j.step("account closed", res.status_code == 200, res.status_code)
    res = j.http.post("/auth/login", json={"email": patient["email"], "password": PASSWORD})
    j.step("closed account cannot sign in", res.status_code == 401, res.status_code)

    # Suspension removes the doctor everywhere
    res = j.http.post(
        f"/admin/doctors/{doctor_id}/suspend", headers=admin, json={"reason": "E2E end"}
    )
    j.step("admin suspends doctor", res.status_code == 200, res.status_code)
    j.step("suspended doctor is not public", j.http.get(f"/doctors/{doctor_id}").status_code == 404)
    j.step("vector removed from Pinecone", wait_for(lambda: not vector_exists(doctor_id)))

    res = j.http.get("/admin/audit-logs?limit=100", headers=admin).json()
    actions = {item["action"] for item in res["items"]}
    expected = {"APPROVE_DOCTOR", "SUSPEND_DOCTOR", "VIEW_CREDENTIAL", "APPOINTMENT_BOOKED"}
    j.step("admin actions are audited", expected <= actions, sorted(expected - actions))

    print(f"\n{j.failures} failure(s)")
    return 1 if j.failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="End-to-end product check")
    parser.add_argument("--api", default="http://127.0.0.1:8010")
    arguments = parser.parse_args()

    if urlsplit(arguments.api).hostname not in {"127.0.0.1", "localhost"}:
        sys.exit("This creates and deletes accounts, so it only runs against a local API.")
    sys.exit(run(arguments.api))
