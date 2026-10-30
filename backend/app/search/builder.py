"""Doctor Document Builder for Vector Embeddings.

Constructs clinical semantic document text for vector indexing from descriptive fields ONLY.
Strict Rule: Must NEVER include doctor full names, phone numbers, email addresses,
or consultation fees to preserve privacy and prevent fee bias in vector similarity.
"""

from typing import Any, Dict, List, Optional


def build_doctor_embedding_text(doctor: Dict[str, Any]) -> str:
    """Builds a rich, clinical semantic text representation of a doctor profile

    for vector indexing.

    Included fields:
    - Specialties: names and descriptions
    - Bio: clinical background, focus areas, syndromes managed
    - Qualifications: medical degrees and board certifications
    - Clinic / Institution: hospital or medical center
    - Practice City: geographical location

    Excluded fields:
    - full_name, phone, email, consultation_fee, user_id
    """
    parts: List[str] = []

    # 1. Specialties & Clinical Descriptions
    specialties = doctor.get("specialties") or []
    if specialties:
        spec_entries = []
        for s in specialties:
            if isinstance(s, dict):
                name = s.get("name", "").strip()
                desc = s.get("description", "").strip()
                if name and desc:
                    spec_entries.append(f"{name} ({desc})")
                elif name:
                    spec_entries.append(name)
            elif isinstance(s, str):
                spec_entries.append(s.strip())
        if spec_entries:
            parts.append(f"Medical Specialties: {', '.join(spec_entries)}.")

    # 2. Clinical Bio & Practice Focus
    bio = doctor.get("bio")
    if bio and bio.strip():
        parts.append(f"Clinical Bio and Expertise: {bio.strip()}")

    # 3. Medical Qualifications & Degrees
    qualifications = doctor.get("qualifications") or []
    if isinstance(qualifications, list) and qualifications:
        valid_quals = [q.strip() for q in qualifications if isinstance(q, str) and q.strip()]
        if valid_quals:
            parts.append(f"Medical Qualifications: {', '.join(valid_quals)}.")
    elif isinstance(qualifications, str) and qualifications.strip():
        parts.append(f"Medical Qualifications: {qualifications.strip()}.")

    # 4. Clinical Experience Years (as general clinical depth)
    years = doctor.get("years_experience")
    if years and isinstance(years, int) and years > 0:
        parts.append(f"Clinical Experience: {years} years of medical practice.")

    # 5. Clinic / Hospital Practice
    clinic_name = doctor.get("clinic_name")
    if clinic_name and clinic_name.strip():
        parts.append(f"Clinical Practice Hospital: {clinic_name.strip()}.")

    # 6. Practice City / Region
    city = doctor.get("city")
    if city and city.strip():
        parts.append(f"Location: {city.strip()}, Bangladesh.")

    return "\n".join(parts)

