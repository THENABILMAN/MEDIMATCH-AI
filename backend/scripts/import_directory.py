"""Imports the owner's doctor directory into the database named by DATABASE_URL.

Directory doctors are marked listing_source = 'directory': patients are told MediMatch has not
verified them, and that they cannot be booked online. Fields the listing does not give, such as the
fee, stay empty. Running it again updates each doctor in place, matched by their profile URL.

The source file is private and kept out of git. Never commit it.

Usage:
    python backend/scripts/import_directory.py --dry-run
    python backend/scripts/import_directory.py
    python backend/scripts/import_directory.py --skip-vectors
"""

import argparse
import collections
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = Path(__file__).resolve().parent.parent
for folder in (backend_dir, backend_dir / "scripts"):
    if str(folder) not in sys.path:
        sys.path.insert(0, str(folder))

import psycopg2  # noqa: E402
from directory_rules import (  # noqa: E402
    classify_specialties,
    detect_city,
    parse_bmdc,
    parse_years,
    split_qualifications,
    strip_contacts,
)
from psycopg2.extras import RealDictCursor, execute_values  # noqa: E402

from app.core.config import settings  # noqa: E402

DEFAULT_FILE = backend_dir.parent / "doctor db" / "doctorbangladesh_doctors.xlsx"
COLUMNS = [
    "Doctor Name",
    "BMDC Reg. No",
    "Degree",
    "Training",
    "Experience",
    "Specialty",
    "Specialist",
    "Designation",
    "Workplace",
    "Profile URL",
]
INSERT_BATCH = 500


def _clean(value: Any) -> str | None:
    text = " ".join(str(value).split()) if value is not None else ""
    return text or None


def read_listings(path: Path) -> list[dict[str, str | None]]:
    """Rows of the spreadsheet as dictionaries. Stops if the columns are not the expected ones."""
    from openpyxl import load_workbook

    sheet = load_workbook(path, read_only=True).worksheets[0]
    rows = list(sheet.iter_rows(values_only=True))
    header = [_clean(cell) for cell in rows[0]]
    missing = [c for c in COLUMNS if c not in header]
    if missing:
        raise SystemExit(f"[ERROR] The file is missing columns: {missing}")
    position = {name: header.index(name) for name in COLUMNS}
    return [{name: _clean(row[i]) for name, i in position.items()} for row in rows[1:] if any(row)]


def to_doctor(listing: dict[str, str | None]) -> dict[str, Any] | None:
    """A database row for one listing, or None if it has no name or profile URL."""
    name, url = listing["Doctor Name"], listing["Profile URL"]
    if not name or not url:
        return None
    workplace = strip_contacts(listing["Workplace"])
    focus = strip_contacts(listing["Specialist"])
    training = strip_contacts(listing["Training"])
    bio_parts = [part for part in (focus, f"Training: {training}" if training else None) if part]
    return {
        "listed_name": name,
        "source_url": url,
        "bmdc_number": parse_bmdc(listing["BMDC Reg. No"]),
        "qualifications": split_qualifications(listing["Degree"]),
        "years_experience": parse_years(listing["Experience"]),
        "specialty_text": listing["Specialty"],
        "designation": listing["Designation"],
        "clinic_name": workplace,
        "city": detect_city(listing["Workplace"], listing["Designation"]),
        "bio": "\n".join(bio_parts) or None,
        "specialties": classify_specialties(listing["Specialty"], listing["Specialist"]),
    }


def _upsert(cur: Any, doctors: list[dict[str, Any]]) -> dict[str, str]:
    """Inserts or updates the listings, and returns each one's id by profile URL."""
    ids: dict[str, str] = {}
    for start in range(0, len(doctors), INSERT_BATCH):
        chunk = doctors[start : start + INSERT_BATCH]
        rows = execute_values(
            cur,
            """
            INSERT INTO public.doctor_profiles (
                listing_source, verification_status, sync_status, listed_name, source_url,
                bmdc_number, qualifications, years_experience, specialty_text, designation,
                clinic_name, city, bio, consultation_fee
            ) VALUES %s
            ON CONFLICT (source_url) WHERE source_url IS NOT NULL DO UPDATE SET
                listed_name = EXCLUDED.listed_name,
                bmdc_number = EXCLUDED.bmdc_number,
                qualifications = EXCLUDED.qualifications,
                years_experience = EXCLUDED.years_experience,
                specialty_text = EXCLUDED.specialty_text,
                designation = EXCLUDED.designation,
                clinic_name = EXCLUDED.clinic_name,
                city = EXCLUDED.city,
                bio = EXCLUDED.bio,
                sync_status = 'pending',
                updated_at = now()
            WHERE public.doctor_profiles.listing_source = 'directory'
            RETURNING id, source_url
            """,
            [
                (
                    "directory",
                    "approved",
                    "pending",
                    d["listed_name"],
                    d["source_url"],
                    d["bmdc_number"],
                    d["qualifications"],
                    d["years_experience"],
                    d["specialty_text"],
                    d["designation"],
                    d["clinic_name"],
                    d["city"],
                    d["bio"],
                    None,
                )
                for d in chunk
            ],
            fetch=True,
        )
        ids.update({url: str(doctor_id) for doctor_id, url in rows})
    return ids


def _link_specialties(cur: Any, doctors: list[dict[str, Any]], ids: dict[str, str]) -> None:
    cur.execute("SELECT id, name FROM public.specialties")
    specialty_ids = {name: str(sid) for sid, name in cur.fetchall()}
    unknown = {n for d in doctors for n in d["specialties"] if n not in specialty_ids}
    if unknown:
        raise SystemExit(f"[ERROR] Specialties missing from the database: {sorted(unknown)}")

    doctor_ids = list(ids.values())
    cur.execute(
        "DELETE FROM public.doctor_specialties WHERE doctor_id = ANY(%s::uuid[])", (doctor_ids,)
    )
    links = [
        (ids[d["source_url"]], specialty_ids[name])
        for d in doctors
        if d["source_url"] in ids
        for name in d["specialties"]
    ]
    execute_values(
        cur, "INSERT INTO public.doctor_specialties (doctor_id, specialty_id) VALUES %s", links
    )


def _index(ids: list[str]) -> int:
    """Embeds the imported doctors into MongoDB. Supabase stays the source of truth."""
    from app.search.sync import index_doctors

    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT d.*, COALESCE(json_agg(json_build_object(
                    'id', s.id, 'name', s.name, 'description', s.description
                )) FILTER (WHERE s.id IS NOT NULL), '[]') AS specialties
                FROM public.doctor_profiles d
                LEFT JOIN public.doctor_specialties ds ON ds.doctor_id = d.id
                LEFT JOIN public.specialties s ON s.id = ds.specialty_id
                WHERE d.id = ANY(%s::uuid[])
                GROUP BY d.id
                """,
                (ids,),
            )
            doctors = [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()
    for doc in doctors:
        doc["id"] = str(doc["id"])
        doc["specialties"] = [{**s, "id": str(s["id"])} for s in doc["specialties"]]
    return index_doctors(
        doctors, progress=lambda done, total: print(f"  • Indexed {done}/{total}", flush=True)
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Import the doctor directory")
    parser.add_argument("--file", type=Path, default=DEFAULT_FILE)
    parser.add_argument("--dry-run", action="store_true", help="Report only, write nothing")
    parser.add_argument("--skip-vectors", action="store_true", help="Leave MongoDB for later")
    args = parser.parse_args()

    listings = read_listings(args.file)
    doctors = [d for d in (to_doctor(listing) for listing in listings) if d]
    by_url = {d["source_url"]: d for d in doctors}
    doctors = list(by_url.values())

    cities = collections.Counter(d["city"] or "unknown" for d in doctors)
    specialties = collections.Counter(n for d in doctors for n in d["specialties"])
    print(f"[INFO] {len(listings)} listings, {len(doctors)} doctors to import")
    print(
        f"[INFO] With no specialty, so never suggested: {sum(not d['specialties'] for d in doctors)}"
    )
    print(f"[INFO] With no city, so only in all-Bangladesh searches: {cities['unknown']}")
    print(f"[INFO] Cities: {cities.most_common(8)}")
    print(f"[INFO] Specialties: {specialties.most_common()}")
    if args.dry_run:
        print("[INFO] Dry run: nothing written.")
        return

    conn = psycopg2.connect(settings.DATABASE_URL)
    try:
        with conn, conn.cursor() as cur:
            ids = _upsert(cur, doctors)
            _link_specialties(cur, doctors, ids)
        print(f"[SUCCESS] Saved {len(ids)} directory doctors.")
    finally:
        conn.close()

    if args.skip_vectors:
        print("[INFO] Skipped MongoDB. Run scripts/reindex_all.py --unsynced later.")
        return
    print(f"[SUCCESS] Indexed {_index(list(ids.values()))} doctors in MongoDB.")


if __name__ == "__main__":
    main()
