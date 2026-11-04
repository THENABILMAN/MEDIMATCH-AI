import logging
from math import ceil
from typing import Any, Dict, List, Optional
from fastapi import HTTPException, status
from app.core.supabase import get_supabase_admin_client, get_supabase_client
from app.models.enums import UserRole, VerificationStatus
from app.schemas.doctor import (
    DoctorCredentialRead,
    DoctorProfileCreateOrUpdate,
    DoctorSearchResult,
    PublicDoctorRead,
)
from app.schemas.profile import DoctorProfileRead, SpecialtyRead
from app.services.audit_service import log_audit_event
from app.services.doctor_events import on_doctor_updated

logger = logging.getLogger(__name__)

CREDENTIAL_BUCKET = "doctor-credentials"
CREDENTIAL_URL_SECONDS = 300
VERIFICATION_ACTIONS = [
    "CREATE_DOCTOR_PROFILE",
    "DOCTOR_MATERIAL_PROFILE_UPDATE",
    "APPROVE_DOCTOR",
    "REJECT_DOCTOR",
    "SUSPEND_DOCTOR",
]


def get_doctor_profile_by_user_id(user_id: str) -> DoctorProfileRead:
    """Fetch complete doctor profile for the authenticated doctor."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    resp = (
        client.table("doctor_profiles")
        .select("*, doctor_specialties(specialties(*))")
        .eq("user_id", user_id)
        .execute()
    )

    if not resp.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found for this user",
        )

    raw_doc = resp.data[0]
    specialties = []
    for ds in raw_doc.get("doctor_specialties", []):
        spec = ds.get("specialties")
        if spec:
            specialties.append(spec)

    return DoctorProfileRead(
        id=str(raw_doc["id"]),
        user_id=str(raw_doc["user_id"]),
        bio=raw_doc.get("bio"),
        qualifications=raw_doc.get("qualifications") or [],
        years_experience=raw_doc.get("years_experience", 0),
        consultation_fee=float(raw_doc.get("consultation_fee", 0.0)),
        clinic_name=raw_doc.get("clinic_name"),
        city=raw_doc.get("city", "Dhaka"),
        verification_status=raw_doc.get("verification_status", "pending"),
        specialties=specialties,
        created_at=raw_doc.get("created_at"),
        updated_at=raw_doc.get("updated_at"),
    )


def upsert_doctor_profile(user_id: str, payload: DoctorProfileCreateOrUpdate) -> DoctorProfileRead:
    """Create or update a doctor profile.
    
    A new or edited profile transitions to 'pending'; saving without changes keeps its status.
    A suspended doctor cannot edit, since that would clear the suspension.
    Material edits to an approved profile are tracked in audit_logs and trigger on_doctor_updated.
    """
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    # Check if doctor profile already exists
    existing = client.table("doctor_profiles").select("*").eq("user_id", user_id).execute()
    doc_data = {
        "user_id": user_id,
        "bio": payload.bio,
        "qualifications": payload.qualifications,
        "years_experience": payload.years_experience,
        "consultation_fee": payload.consultation_fee,
        "clinic_name": payload.clinic_name,
        "city": payload.city,
        "verification_status": VerificationStatus.PENDING.value,  # Reset to pending on any update
    }

    if existing.data:
        old_doc = existing.data[0]
        doctor_id = str(old_doc["id"])
        if old_doc.get("verification_status") == VerificationStatus.SUSPENDED.value:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This profile is suspended. Please contact support.",
            )

        was_approved = old_doc.get("verification_status") == VerificationStatus.APPROVED.value

        # Identify changed fields
        changed_fields = [
            k for k in ["bio", "qualifications", "years_experience", "consultation_fee", "clinic_name", "city"]
            if old_doc.get(k) != doc_data[k]
        ]

        # Only a request that sends specialty_ids may change them
        specialties_sent = "specialty_ids" in payload.model_fields_set
        old_specialties = (
            client.table("doctor_specialties").select("specialty_id").eq("doctor_id", doctor_id).execute()
        )
        old_specialty_ids = {str(row["specialty_id"]) for row in old_specialties.data or []}
        if specialties_sent and set(payload.specialty_ids) != old_specialty_ids:
            changed_fields.append("specialties")

        if not changed_fields:
            return get_doctor_profile_by_user_id(user_id)

        # Update doctor profile table
        client.table("doctor_profiles").update(doc_data).eq("id", doctor_id).execute()

        if "specialties" in changed_fields:
            client.table("doctor_specialties").delete().eq("doctor_id", doctor_id).execute()
            if payload.specialty_ids:
                entries = [{"doctor_id": doctor_id, "specialty_id": sid} for sid in payload.specialty_ids]
                client.table("doctor_specialties").insert(entries).execute()

        # Material edit audit log
        if was_approved:
            log_audit_event(
                actor_id=user_id,
                action="DOCTOR_MATERIAL_PROFILE_UPDATE",
                target_type="doctor_profiles",
                target_id=doctor_id,
                metadata={
                    "previous_status": VerificationStatus.APPROVED.value,
                    "new_status": VerificationStatus.PENDING.value,
                    "changed_fields": changed_fields,
                },
            )
            on_doctor_updated(doctor_id=doctor_id, updated_fields=changed_fields)
    else:
        # Create new doctor profile
        res = client.table("doctor_profiles").insert(doc_data).execute()
        doctor_id = str(res.data[0]["id"])
        if payload.specialty_ids:
            entries = [{"doctor_id": doctor_id, "specialty_id": sid} for sid in payload.specialty_ids]
            client.table("doctor_specialties").insert(entries).execute()

        log_audit_event(
            actor_id=user_id,
            action="CREATE_DOCTOR_PROFILE",
            target_type="doctor_profiles",
            target_id=doctor_id,
            metadata={"city": payload.city, "status": VerificationStatus.PENDING.value},
        )

    return get_doctor_profile_by_user_id(user_id)


def add_doctor_credential(user_id: str, file_path: str, document_type: str) -> DoctorCredentialRead:
    """Store record of uploaded credential document in doctor_credentials table."""
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    # Get doctor ID
    doc_res = client.table("doctor_profiles").select("id").eq("user_id", user_id).execute()
    if not doc_res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor profile not found. Please create doctor profile first.",
        )
    doctor_id = str(doc_res.data[0]["id"])

    data = {
        "doctor_id": doctor_id,
        "file_path": file_path,
        "document_type": document_type,
    }
    res = client.table("doctor_credentials").insert(data).execute()
    created = res.data[0]

    log_audit_event(
        actor_id=user_id,
        action="UPLOAD_CREDENTIAL",
        target_type="doctor_credentials",
        target_id=str(created["id"]),
        metadata={"document_type": document_type, "file_path": file_path},
    )

    return DoctorCredentialRead(
        id=str(created["id"]),
        doctor_id=str(created["doctor_id"]),
        file_path=created["file_path"],
        document_type=created["document_type"],
        uploaded_at=created["uploaded_at"],
    )


def list_my_credentials(user_id: str) -> List[DoctorCredentialRead]:
    """Lists the doctor's own uploaded credential records, newest first."""
    doctor = get_doctor_profile_by_user_id(user_id)
    client = get_supabase_admin_client() or get_supabase_client()
    res = (
        client.table("doctor_credentials")
        .select("*")
        .eq("doctor_id", doctor.id)
        .order("uploaded_at", desc=True)
        .execute()
    )
    return [DoctorCredentialRead.model_validate(row) for row in res.data or []]


def get_credential_url(credential_id: str, user_id: str, is_admin: bool) -> Dict[str, str]:
    """Creates a short-lived link to a credential file for its owner or an admin."""
    client = get_supabase_admin_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Credential storage is unavailable",
        )

    res = (
        client.table("doctor_credentials")
        .select("file_path, doctor_profiles(user_id)")
        .eq("id", credential_id)
        .execute()
    )
    if not res.data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Credential not found")

    credential = res.data[0]
    owner_id = (credential.get("doctor_profiles") or {}).get("user_id")
    if not is_admin and str(owner_id) != str(user_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this document",
        )

    try:
        signed = client.storage.from_(CREDENTIAL_BUCKET).create_signed_url(
            credential["file_path"], CREDENTIAL_URL_SECONDS
        )
        url = signed.get("signedURL") or signed.get("signedUrl")
    except Exception as e:
        logger.error(f"Could not sign credential {credential_id}: {e}")
        url = None

    if not url:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="This document could not be opened. Please try again.",
        )
    return {"url": url}


def get_verification_history(user_id: str) -> List[Dict[str, Any]]:
    """Returns status events for the doctor's timeline, without exposing which admin acted."""
    doctor = get_doctor_profile_by_user_id(user_id)
    client = get_supabase_admin_client() or get_supabase_client()
    res = (
        client.table("audit_logs")
        .select("action, created_at, metadata")
        .eq("target_type", "doctor_profiles")
        .eq("target_id", doctor.id)
        .in_("action", VERIFICATION_ACTIONS)
        .order("created_at", desc=False)
        .execute()
    )
    return [
        {
            "action": row["action"],
            "created_at": row["created_at"],
            "reason": (row.get("metadata") or {}).get("reason"),
        }
        for row in res.data or []
    ]


def _doctor_ids_with_specialty(client: Any, specialty: str) -> List[str]:
    """Resolves a specialty name fragment or id to the doctors who practise it."""
    s_filter = specialty.lower().strip()
    specialties = client.table("specialties").select("id, name").execute().data or []
    specialty_ids = [
        str(s["id"]) for s in specialties if s_filter in s["name"].lower() or s_filter == str(s["id"])
    ]
    if not specialty_ids:
        return []

    rows = client.table("doctor_specialties").select("doctor_id").in_("specialty_id", specialty_ids).execute()
    return sorted({str(row["doctor_id"]) for row in rows.data or []})


def search_public_doctors(
    specialty: Optional[str] = None,
    city: Optional[str] = None,
    max_fee: Optional[float] = None,
    min_experience: Optional[int] = None,
    sort_by: Optional[str] = None,
    page: int = 1,
    page_size: int = 10,
) -> DoctorSearchResult:
    """Search doctors available to the public.
    
    CRITICAL NON-NEGOTIABLE RULE:
    Strictly returns ONLY doctors where verification_status = 'approved'.
    Never returns credential files, private phone numbers, or unapproved records.
    """
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    # Filter by specialty inside the query, so pages and totals stay correct
    doctor_ids: Optional[List[str]] = None
    if specialty:
        doctor_ids = _doctor_ids_with_specialty(client, specialty)
        if not doctor_ids:
            return DoctorSearchResult(items=[], total=0, page=page, page_size=page_size, total_pages=1)

    # Always enforce verification_status = 'approved'
    query = (
        client.table("doctor_profiles")
        .select("*, profiles!inner(full_name), doctor_specialties(specialties(*))", count="exact")
        .eq("verification_status", VerificationStatus.APPROVED.value)
    )

    if doctor_ids is not None:
        query = query.in_("id", doctor_ids)
    if city:
        query = query.ilike("city", f"%{city.strip()}%")
    if max_fee is not None:
        query = query.lte("consultation_fee", max_fee)
    if min_experience is not None:
        query = query.gte("years_experience", min_experience)

    # Sorting
    if sort_by == "fee_asc":
        query = query.order("consultation_fee", desc=False)
    elif sort_by == "fee_desc":
        query = query.order("consultation_fee", desc=True)
    elif sort_by == "experience_desc":
        query = query.order("years_experience", desc=True)
    else:
        query = query.order("created_at", desc=True)

    # Pagination range (0-based in Supabase)
    offset = (page - 1) * page_size
    query = query.range(offset, offset + page_size - 1)

    result = query.execute()
    total = result.count or 0
    raw_doctors = result.data or []

    # Map to PublicDoctorRead
    items: List[PublicDoctorRead] = []
    for doc in raw_doctors:
        specs: List[SpecialtyRead] = []
        for ds in doc.get("doctor_specialties", []):
            s = ds.get("specialties")
            if s:
                specs.append(SpecialtyRead(id=str(s["id"]), name=s["name"], description=s.get("description")))

        profile_info = doc.get("profiles") or {}
        full_name = profile_info.get("full_name") or "Dr. Anonymous"

        items.append(
            PublicDoctorRead(
                id=str(doc["id"]),
                full_name=full_name,
                bio=doc.get("bio"),
                qualifications=doc.get("qualifications") or [],
                years_experience=doc.get("years_experience", 0),
                consultation_fee=float(doc.get("consultation_fee", 0.0)),
                clinic_name=doc.get("clinic_name"),
                city=doc.get("city", "Dhaka"),
                verification_status=VerificationStatus.APPROVED,
                specialties=specs,
            )
        )

    total_pages = max(1, ceil(total / page_size)) if page_size else 1
    return DoctorSearchResult(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_public_doctor_by_id(doctor_id: str) -> PublicDoctorRead:
    """Fetch public profile for a single doctor.
    
    Returns 404 if doctor is not found OR verification_status != 'approved'.
    """
    client = get_supabase_admin_client() or get_supabase_client()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database service unavailable",
        )

    res = (
        client.table("doctor_profiles")
        .select("*, profiles!inner(full_name), doctor_specialties(specialties(*))")
        .eq("id", doctor_id)
        .eq("verification_status", VerificationStatus.APPROVED.value)
        .execute()
    )

    if not res.data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found or not currently approved for public search",
        )

    raw_doc = res.data[0]
    specs: List[SpecialtyRead] = []
    for ds in raw_doc.get("doctor_specialties", []):
        s = ds.get("specialties")
        if s:
            specs.append(SpecialtyRead(id=str(s["id"]), name=s["name"], description=s.get("description")))

    profile_info = raw_doc.get("profiles") or {}
    full_name = profile_info.get("full_name") or "Dr. Anonymous"

    return PublicDoctorRead(
        id=str(raw_doc["id"]),
        full_name=full_name,
        bio=raw_doc.get("bio"),
        qualifications=raw_doc.get("qualifications") or [],
        years_experience=raw_doc.get("years_experience", 0),
        consultation_fee=float(raw_doc.get("consultation_fee", 0.0)),
        clinic_name=raw_doc.get("clinic_name"),
        city=raw_doc.get("city", "Dhaka"),
        verification_status=VerificationStatus.APPROVED,
        specialties=specs,
    )

