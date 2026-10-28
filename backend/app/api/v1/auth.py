from fastapi import APIRouter, status
from app.schemas.auth import LoginRequest, RegisterDoctorRequest, RegisterPatientRequest, TokenResponse
from app.services.auth_service import login_service, register_doctor_service, register_patient_service

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register-patient",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new patient account",
)
def register_patient(payload: RegisterPatientRequest):
    return register_patient_service(payload)


@router.post(
    "/register-doctor",
    status_code=status.HTTP_201_CREATED,
    summary="Register a new doctor account with pending verification",
)
def register_doctor(payload: RegisterDoctorRequest):
    return register_doctor_service(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive JWT access token",
)
def login(payload: LoginRequest):
    return login_service(payload)
