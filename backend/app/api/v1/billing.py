from fastapi import APIRouter, Depends
from postgrest import SyncPostgrestClient

from app.api.deps import get_user_db, require_doctor
from app.schemas.billing import BillingPlanChoice, BillingPricing, MyBilling
from app.schemas.profile import UserMeResponse
from app.services.billing_service import choose_plan, get_my_billing, get_pricing

router = APIRouter(prefix="/billing", tags=["Billing"])


@router.get("/pricing", response_model=BillingPricing, summary="Current prices for doctors")
def read_pricing() -> BillingPricing:
    return get_pricing()


@router.get("/me", response_model=MyBilling, summary="Own billing plan and charges")
def read_my_billing(
    current_doctor: UserMeResponse = Depends(require_doctor),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> MyBilling:
    return get_my_billing(str(current_doctor.id), db)


@router.put("/me/plan", response_model=MyBilling, summary="Choose a billing plan")
def update_my_plan(
    choice: BillingPlanChoice,
    current_doctor: UserMeResponse = Depends(require_doctor),
    db: SyncPostgrestClient = Depends(get_user_db),
) -> MyBilling:
    return choose_plan(str(current_doctor.id), choice.plan, db)
