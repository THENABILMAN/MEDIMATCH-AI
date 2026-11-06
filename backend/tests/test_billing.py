"""Doctor billing against local Supabase: charges, prices, access and row-level security."""

import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta

import psycopg2
import pytest
from conftest import create_mock_jwt
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.supabase import get_supabase_admin_client
from app.models.enums import UserRole

DOCTOR_USER_ID = "a0000000-0000-0000-0000-000000000003"
DOCTOR_ID = "d0000000-0000-0000-0000-000000000000"
PATIENT_USER_ID = "a0000000-0000-0000-0000-000000000002"
ADMIN_USER_ID = "a0000000-0000-0000-0000-000000000001"


def bearer(user_id: str, role: UserRole) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_mock_jwt(user_id, 'x@tests.invalid', role)}"}


DOCTOR = bearer(DOCTOR_USER_ID, UserRole.DOCTOR)
PATIENT = bearer(PATIENT_USER_ID, UserRole.PATIENT)
ADMIN = bearer(ADMIN_USER_ID, UserRole.ADMIN)


@pytest.fixture(autouse=True)
def clean_billing() -> Iterator[None]:
    def reset() -> None:
        with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM public.billing_charges")
            cur.execute("DELETE FROM public.doctor_billing_plans")
            cur.execute(
                "UPDATE public.billing_settings "
                "SET booking_fee_bdt = NULL, subscription_monthly_bdt = NULL"
            )

    reset()
    yield
    reset()


def set_prices(client: TestClient, booking: int | None, monthly: int | None) -> None:
    body = {"booking_fee_bdt": booking, "subscription_monthly_bdt": monthly}
    assert client.put("/admin/billing/pricing", headers=ADMIN, json=body).status_code == 200


def choose(client: TestClient, plan: str) -> dict:
    res = client.put("/billing/me/plan", headers=DOCTOR, json={"plan": plan})
    assert res.status_code == 200, res.text
    return res.json()


def new_appointment(start: datetime) -> str:
    row = {
        "patient_id": PATIENT_USER_ID,
        "doctor_id": DOCTOR_ID,
        "scheduled_start": start.isoformat(),
        "scheduled_end": (start + timedelta(minutes=30)).isoformat(),
        "status": "booked",
    }
    res = get_supabase_admin_client().table("appointments").insert(row).execute()
    return res.data[0]["id"]


def started_appointment() -> str:
    """An appointment that began at least an hour ago, so it can be completed."""
    return new_appointment(datetime.now(UTC) - timedelta(minutes=60 + uuid.uuid4().int % 100000))


def complete(client: TestClient, appointment_id: str) -> None:
    res = client.post(f"/appointments/{appointment_id}/complete", headers=DOCTOR)
    assert res.status_code == 200, res.text


def my_billing(client: TestClient) -> dict:
    return client.get("/billing/me", headers=DOCTOR).json()


def test_pricing_is_public_and_starts_unset(client: TestClient):
    res = client.get("/billing/pricing")
    assert res.status_code == 200
    assert res.json() == {"booking_fee_bdt": None, "subscription_monthly_bdt": None}


def test_only_an_admin_sets_prices(client: TestClient):
    body = {"booking_fee_bdt": 100, "subscription_monthly_bdt": 2000}
    assert client.put("/admin/billing/pricing", json=body).status_code == 401
    assert client.put("/admin/billing/pricing", headers=DOCTOR, json=body).status_code == 403
    assert client.put("/admin/billing/pricing", headers=PATIENT, json=body).status_code == 403


@pytest.mark.parametrize("price", [0, -5, 1.5, 2_000_000])
def test_bad_prices_are_refused(client: TestClient, price: float):
    body = {"booking_fee_bdt": price, "subscription_monthly_bdt": None}
    assert client.put("/admin/billing/pricing", headers=ADMIN, json=body).status_code == 422


def test_only_a_doctor_has_billing(client: TestClient):
    assert client.get("/billing/me").status_code == 401
    assert client.get("/billing/me", headers=PATIENT).status_code == 403
    plan = {"plan": "booking_fee"}
    assert client.put("/billing/me/plan", headers=PATIENT, json=plan).status_code == 403


def test_a_completed_appointment_charges_the_booking_fee_once(client: TestClient):
    set_prices(client, 150, None)
    choose(client, "booking_fee")
    appointment = started_appointment()
    complete(client, appointment)

    billing = my_billing(client)
    assert billing["total_owed_bdt"] == 150
    assert [(c["kind"], c["amount_bdt"], c["status"]) for c in billing["charges"]] == [
        ("booking_fee", 150, "owed")
    ]
    assert client.post(f"/appointments/{appointment}/complete", headers=DOCTOR).status_code == 400
    assert len(my_billing(client)["charges"]) == 1


def test_nothing_is_charged_while_the_price_is_unset(client: TestClient):
    choose(client, "booking_fee")
    complete(client, started_appointment())
    assert my_billing(client)["charges"] == []


def test_nothing_is_charged_before_a_doctor_chooses_a_plan(client: TestClient):
    set_prices(client, 150, 2000)
    complete(client, started_appointment())
    assert my_billing(client)["plan"] is None
    assert my_billing(client)["charges"] == []


def test_a_cancelled_appointment_is_not_charged(client: TestClient):
    set_prices(client, 150, None)
    choose(client, "booking_fee")
    appointment = new_appointment(datetime.now(UTC) + timedelta(days=30))
    res = client.post(f"/appointments/{appointment}/cancel", headers=DOCTOR, json={"reason": "x"})
    assert res.status_code == 200, res.text
    assert my_billing(client)["charges"] == []


def test_subscribers_pay_no_booking_fee(client: TestClient):
    set_prices(client, 150, 2000)
    choose(client, "subscription")
    complete(client, started_appointment())
    assert [c["kind"] for c in my_billing(client)["charges"]] == ["subscription"]


def test_choosing_the_subscription_charges_this_month_only_once(client: TestClient):
    set_prices(client, 150, 2000)
    assert choose(client, "subscription")["total_owed_bdt"] == 2000
    choose(client, "booking_fee")
    assert choose(client, "subscription")["total_owed_bdt"] == 2000


def test_the_monthly_run_can_repeat_and_charges_only_approved_doctors(client: TestClient):
    set_prices(client, None, 2000)
    choose(client, "subscription")
    database = get_supabase_admin_client()
    assert database.rpc("bill_subscriptions", {}).execute().data == 0

    with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute("DELETE FROM public.billing_charges")
        cur.execute(
            "UPDATE public.doctor_profiles SET verification_status = 'suspended' WHERE id = %s",
            (DOCTOR_ID,),
        )
    try:
        assert database.rpc("bill_subscriptions", {}).execute().data == 0
    finally:
        with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
            cur.execute(
                "UPDATE public.doctor_profiles SET verification_status = 'approved' WHERE id = %s",
                (DOCTOR_ID,),
            )
    assert database.rpc("bill_subscriptions", {}).execute().data == 1
    assert database.rpc("bill_subscriptions", {}).execute().data == 0


def test_a_price_change_keeps_what_is_already_owed(client: TestClient):
    set_prices(client, 150, None)
    choose(client, "booking_fee")
    complete(client, started_appointment())
    set_prices(client, 300, None)
    complete(client, started_appointment())
    assert sorted(c["amount_bdt"] for c in my_billing(client)["charges"]) == [150, 300]
    assert my_billing(client)["total_owed_bdt"] == 450


def test_an_admin_settles_a_charge_once(client: TestClient):
    set_prices(client, 150, None)
    choose(client, "booking_fee")
    complete(client, started_appointment())

    charges = client.get("/admin/billing/charges?status=owed", headers=ADMIN).json()
    assert charges["total"] == 1
    assert charges["items"][0]["doctor_name"]
    charge = charges["items"][0]["id"]

    url = f"/admin/billing/charges/{charge}/settle"
    assert client.post(url, headers=DOCTOR, json={"status": "paid"}).status_code == 403
    assert client.post(url, headers=ADMIN, json={"status": "owed"}).status_code == 422
    res = client.post(url, headers=ADMIN, json={"status": "paid"})
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "paid"
    assert res.json()["settled_at"]
    assert client.post(url, headers=ADMIN, json={"status": "waived"}).status_code == 409
    assert my_billing(client)["total_owed_bdt"] == 0

    missing = f"/admin/billing/charges/{uuid.uuid4()}/settle"
    assert client.post(missing, headers=ADMIN, json={"status": "paid"}).status_code == 404


def test_a_client_cannot_touch_billing_tables_directly():
    """RLS: an ordinary signed-in role writes nothing, and reads no one else's charges."""
    set_up = """
        INSERT INTO public.billing_charges (doctor_id, kind, amount_bdt, appointment_id)
        VALUES (%s, 'booking_fee', 150, NULL)
    """
    with psycopg2.connect(settings.DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(set_up, (DOCTOR_ID,))
        cur.execute("SET LOCAL ROLE authenticated")
        cur.execute(
            "SELECT set_config('request.jwt.claims', %s, true)",
            (f'{{"sub": "{PATIENT_USER_ID}", "role": "authenticated"}}',),
        )
        cur.execute("SELECT count(*) FROM public.billing_charges")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM public.doctor_billing_plans")
        assert cur.fetchone()[0] == 0
        cur.execute("SELECT count(*) FROM public.billing_settings")
        assert cur.fetchone()[0] == 0
        cur.execute("UPDATE public.billing_charges SET status = 'paid'")
        assert cur.rowcount == 0
        cur.execute(
            "SELECT set_config('request.jwt.claims', %s, true)",
            (f'{{"sub": "{DOCTOR_USER_ID}", "role": "authenticated"}}',),
        )
        cur.execute("SELECT count(*) FROM public.billing_charges")
        assert cur.fetchone()[0] == 1
        cur.execute("UPDATE public.billing_charges SET status = 'paid'")
        assert cur.rowcount == 0
        cur.execute("SAVEPOINT before_insert")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute(
                "INSERT INTO public.doctor_billing_plans (doctor_id, plan) VALUES (%s, 'subscription')",
                (DOCTOR_ID,),
            )
        cur.execute("ROLLBACK TO SAVEPOINT before_insert")
        cur.execute("SAVEPOINT before_call")
        with pytest.raises(psycopg2.errors.InsufficientPrivilege):
            cur.execute("SELECT public.bill_subscriptions()")
        conn.rollback()
