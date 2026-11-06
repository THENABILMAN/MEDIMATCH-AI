"""Doctor billing. Amounts are whole taka. A price of None is unset, and nothing is charged."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import BillingPlan, ChargeKind, ChargeStatus
from app.schemas.common import MAX_CONSULTATION_FEE


class BillingPricing(BaseModel):
    booking_fee_bdt: int | None = None
    subscription_monthly_bdt: int | None = None


class BillingPricingUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    booking_fee_bdt: int | None = Field(gt=0, le=MAX_CONSULTATION_FEE)
    subscription_monthly_bdt: int | None = Field(gt=0, le=MAX_CONSULTATION_FEE)


class BillingPlanChoice(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan: BillingPlan


class BillingCharge(BaseModel):
    id: str
    kind: ChargeKind
    billing_month: date | None = None
    amount_bdt: int
    status: ChargeStatus
    created_at: datetime
    settled_at: datetime | None = None


class MyBilling(BaseModel):
    plan: BillingPlan | None = None
    chosen_at: datetime | None = None
    pricing: BillingPricing
    total_owed_bdt: int
    charges: list[BillingCharge]


class AdminBillingCharge(BillingCharge):
    doctor_id: str
    doctor_name: str | None = None


class AdminBillingChargePage(BaseModel):
    items: list[AdminBillingCharge]
    total: int
    limit: int
    offset: int


class ChargeSettlement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ChargeStatus
