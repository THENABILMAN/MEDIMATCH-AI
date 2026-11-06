"""Doctor billing. This records what doctors owe: no money moves through the app."""

from typing import Any

from fastapi import HTTPException, status
from postgrest import SyncPostgrestClient

from app.core.supabase import get_supabase_admin_client
from app.models.enums import BillingPlan, ChargeStatus
from app.schemas.billing import (
    AdminBillingCharge,
    AdminBillingChargePage,
    BillingCharge,
    BillingPricing,
    BillingPricingUpdate,
    MyBilling,
)
from app.services.audit_service import log_audit_event
from app.services.doctor_service import get_doctor_profile_by_user_id

MY_CHARGES_SHOWN = 100


def _client() -> Any:
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database service unavailable"
        )
    return client


def get_pricing() -> BillingPricing:
    res = _client().table("billing_settings").select("*").eq("id", True).execute()
    return BillingPricing.model_validate(res.data[0]) if res.data else BillingPricing()


def update_pricing(admin_id: str, update: BillingPricingUpdate) -> BillingPricing:
    """Sets the prices for future charges. Charges already recorded keep their amount."""
    previous = get_pricing()
    _client().table("billing_settings").update(update.model_dump()).eq("id", True).execute()
    log_audit_event(
        actor_id=admin_id,
        action="BILLING_PRICING_UPDATED",
        target_type="billing_settings",
        metadata={"previous": previous.model_dump(), "current": update.model_dump()},
    )
    return BillingPricing(**update.model_dump())


def get_my_billing(user_id: str, db: SyncPostgrestClient) -> MyBilling:
    """The doctor's plan and charges, read as the caller so RLS also applies."""
    doctor = get_doctor_profile_by_user_id(user_id)
    plan = db.table("doctor_billing_plans").select("*").eq("doctor_id", doctor.id).execute()
    charges = (
        db.table("billing_charges")
        .select("*")
        .eq("doctor_id", doctor.id)
        .order("created_at", desc=True)
        .limit(MY_CHARGES_SHOWN)
        .execute()
    )
    owed = (
        db.table("billing_charges")
        .select("amount_bdt")
        .eq("doctor_id", doctor.id)
        .eq("status", ChargeStatus.OWED.value)
        .execute()
    )
    row: dict[str, Any] = plan.data[0] if plan.data else {}  # type: ignore[assignment]
    owed_rows: list[dict[str, Any]] = owed.data or []  # type: ignore[assignment]
    return MyBilling(
        plan=row.get("plan"),
        chosen_at=row.get("chosen_at"),
        pricing=get_pricing(),
        total_owed_bdt=sum(int(item["amount_bdt"]) for item in owed_rows),
        charges=[BillingCharge.model_validate(item) for item in charges.data or []],
    )


def choose_plan(user_id: str, plan: BillingPlan, db: SyncPostgrestClient) -> MyBilling:
    """Saves the doctor's plan.

    Choosing the subscription charges the current month at once, so a doctor cannot leave the
    booking fee mid-month and pay for nothing until the next run. A month is charged only once,
    however often the plan changes.
    """
    doctor = get_doctor_profile_by_user_id(user_id)
    client = _client()
    client.table("doctor_billing_plans").upsert(
        {"doctor_id": doctor.id, "plan": plan.value, "chosen_at": "now()"}
    ).execute()
    if plan == BillingPlan.SUBSCRIPTION:
        client.rpc("bill_subscriptions", {"p_doctor_id": doctor.id}).execute()
    log_audit_event(
        actor_id=user_id,
        action="BILLING_PLAN_CHOSEN",
        target_type="doctor_profiles",
        target_id=doctor.id,
        metadata={"plan": plan.value},
    )
    return get_my_billing(user_id, db)


def list_charges(
    status_filter: ChargeStatus | None, limit: int, offset: int
) -> AdminBillingChargePage:
    query = (
        _client()
        .table("billing_charges")
        .select("*, doctor_profiles(profiles!inner(full_name))", count="exact")
        .order("created_at", desc=True)
    )
    if status_filter:
        query = query.eq("status", status_filter.value)
    res = query.range(offset, offset + limit - 1).execute()
    items = []
    for row in res.data or []:
        doctor = row.pop("doctor_profiles", None) or {}
        name = (doctor.get("profiles") or {}).get("full_name")
        items.append(AdminBillingCharge.model_validate({**row, "doctor_name": name}))
    return AdminBillingChargePage(items=items, total=res.count or 0, limit=limit, offset=offset)


def settle_charge(admin_id: str, charge_id: str, outcome: ChargeStatus) -> AdminBillingCharge:
    """Records that an owed charge was paid outside the app, or waived."""
    if outcome == ChargeStatus.OWED:
        raise HTTPException(
            status_code=422,
            detail="A charge can only be marked paid or waived",
        )
    client = _client()
    res = (
        client.table("billing_charges")
        .update({"status": outcome.value, "settled_at": "now()"})
        .eq("id", charge_id)
        .eq("status", ChargeStatus.OWED.value)
        .execute()
    )
    if not res.data:
        found = client.table("billing_charges").select("id").eq("id", charge_id).execute()
        if not found.data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Charge not found")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="This charge is already settled"
        )
    log_audit_event(
        actor_id=admin_id,
        action=f"BILLING_CHARGE_{outcome.value.upper()}",
        target_type="billing_charges",
        target_id=charge_id,
    )
    return AdminBillingCharge.model_validate(res.data[0])


def bill_all_subscriptions() -> int:
    """Charges the current month for every approved subscriber. Safe to run again."""
    res = _client().rpc("bill_subscriptions", {}).execute()
    return int(res.data or 0)
