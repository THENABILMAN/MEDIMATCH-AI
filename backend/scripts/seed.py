"""Database Seeding Script for MediMatch AI.

Seeds:
- 3 Specialties: Neurology, Cardiology, General Medicine
- 10 Fake clearly-labelled demo doctors in Bangladesh (mix of approved, pending, suspended)
- 3 Core test accounts:
    - Admin:   admin@medimatch.test   / AdminPass123!
    - Doctor:  doctor@medimatch.test  / DoctorPass123!
    - Patient: patient@medimatch.test / PatientPass123!

Usage:
    python backend/scripts/seed.py
"""

import os
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings
from app.models.enums import UserRole, VerificationStatus


SPECIALTIES = [
    {
        "id": "11111111-0000-0000-0000-000000000001",
        "name": "Neurology",
        "description": "Diagnosis and management of disorders of the brain, spinal cord, nerves, and neurological conditions.",
    },
    {
        "id": "11111111-0000-0000-0000-000000000002",
        "name": "Cardiology",
        "description": "Diagnosis and treatment of heart conditions, cardiovascular disease, arrhythmias, and hypertension.",
    },
    {
        "id": "11111111-0000-0000-0000-000000000003",
        "name": "General Medicine",
        "description": "Primary healthcare, internal medicine, comprehensive diagnosis, fever management, and chronic disease control.",
    },
]

DEMO_USERS = [
    {
        "id": "a0000000-0000-0000-0000-000000000001",
        "email": "admin@medimatch.test",
        "role": UserRole.ADMIN.value,
        "full_name": "MediMatch Platform Admin",
        "phone": "+8801710000001",
    },
    {
        "id": "a0000000-0000-0000-0000-000000000002",
        "email": "patient@medimatch.test",
        "role": UserRole.PATIENT.value,
        "full_name": "Demo Patient Karim",
        "phone": "+8801710000002",
    },
    {
        "id": "a0000000-0000-0000-0000-000000000003",
        "email": "doctor@medimatch.test",
        "role": UserRole.DOCTOR.value,
        "full_name": "Dr. Tanvir Hasan (Demo Doctor)",
        "phone": "+8801710000003",
        "doctor_profile": {
            "id": "d0000000-0000-0000-0000-000000000000",
            "bio": "Consultant Cardiologist with extensive clinical experience in cardiac diagnostics and coronary intervention.",
            "qualifications": ["MBBS (DMC)", "MD (Cardiology)", "MRCP (UK)"],
            "years_experience": 14,
            "consultation_fee": 1500.0,
            "clinic_name": "Square Hospital, Panthapath",
            "city": "Dhaka",
            "verification_status": VerificationStatus.APPROVED.value,
            "specialty_id": "11111111-0000-0000-0000-000000000002",
        },
    },
]

DEMO_DOCTORS = [
    {
        "user_id": "d1000000-0000-0000-0000-000000000001",
        "doc_id": "d2000000-0000-0000-0000-000000000001",
        "email": "dr.ahmed.neuro@medimatch.test",
        "full_name": "[Demo] Dr. Kazi Ahmed (Neurologist)",
        "bio": "Specialized in stroke rehabilitation, epilepsy management, migraine syndromes, and clinical neurophysiology.",
        "qualifications": ["MBBS", "FCPS (Neurology)", "Fellow Neurovascular (Singapore)"],
        "years_experience": 16,
        "consultation_fee": 2000.0,
        "clinic_name": "United Hospital, Gulshan",
        "city": "Dhaka",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000001",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000002",
        "doc_id": "d2000000-0000-0000-0000-000000000002",
        "email": "dr.samira.cardio@medimatch.test",
        "full_name": "[Demo] Dr. Samira Rahman (Cardiologist)",
        "bio": "Experienced cardiologist focused on echocardiography, preventive heart health, and heart failure management.",
        "qualifications": ["MBBS", "FCPS (Cardiology)"],
        "years_experience": 11,
        "consultation_fee": 1200.0,
        "clinic_name": "National Heart Foundation, Mirpur",
        "city": "Dhaka",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000002",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000003",
        "doc_id": "d2000000-0000-0000-0000-000000000003",
        "email": "dr.mahmud.gen@medimatch.test",
        "full_name": "[Demo] Dr. Mahmudul Hasan (General Physician)",
        "bio": "Senior general medicine consultant handling acute fever, metabolic diseases, diabetes, and infections.",
        "qualifications": ["MBBS", "MCPS", "FCPS (Medicine)"],
        "years_experience": 20,
        "consultation_fee": 1000.0,
        "clinic_name": "Evercare Hospital, Bashundhara",
        "city": "Dhaka",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000003",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000004",
        "doc_id": "d2000000-0000-0000-0000-000000000004",
        "email": "dr.farhana.ctg@medimatch.test",
        "full_name": "[Demo] Dr. Farhana Haque (Chittagong)",
        "bio": "Consultant physician practicing in Chittagong, providing accessible diagnosis and general health management.",
        "qualifications": ["MBBS (CMC)", "BCS (Health)", "MD (Medicine)"],
        "years_experience": 9,
        "consultation_fee": 800.0,
        "clinic_name": "Chevron Clinical Laboratory, Panchlaish",
        "city": "Chittagong",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000003",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000005",
        "doc_id": "d2000000-0000-0000-0000-000000000005",
        "email": "dr.imran.sylhet@medimatch.test",
        "full_name": "[Demo] Dr. Imran Chowdhury (Sylhet)",
        "bio": "Experienced cardiologist serving the Sylhet division with cardiovascular risk screening and therapy.",
        "qualifications": ["MBBS (SOMC)", "Diploma in Cardiology (NICVD)"],
        "years_experience": 13,
        "consultation_fee": 1100.0,
        "clinic_name": "Popular Diagnostic Centre, Subhanighat",
        "city": "Sylhet",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000002",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000006",
        "doc_id": "d2000000-0000-0000-0000-000000000006",
        "email": "dr.rubina.neuro@medimatch.test",
        "full_name": "[Demo] Dr. Rubina Akhter (Approved Neuro)",
        "bio": "Pediatric and adult neurology specialist focusing on chronic headache, neuropathy, and movement disorders.",
        "qualifications": ["MBBS", "MD (Neurology - BSMMU)"],
        "years_experience": 8,
        "consultation_fee": 1400.0,
        "clinic_name": "Ibn Sina Medical College Hospital, Kallyanpur",
        "city": "Dhaka",
        "verification_status": VerificationStatus.APPROVED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000001",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000007",
        "doc_id": "d2000000-0000-0000-0000-000000000007",
        "email": "dr.jamil.pending@medimatch.test",
        "full_name": "[Demo] Dr. Jamil Siddiqui",
        "bio": "Recently registered general physician awaiting admin certificate verification.",
        "qualifications": ["MBBS", "D-Card (in progress)"],
        "years_experience": 4,
        "consultation_fee": 900.0,
        "clinic_name": "Labaid Diagnostic, Dhanmondi",
        "city": "Dhaka",
        "verification_status": VerificationStatus.PENDING.value,
        "specialty_id": "11111111-0000-0000-0000-000000000003",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000008",
        "doc_id": "d2000000-0000-0000-0000-000000000008",
        "email": "dr.zubaida.pending@medimatch.test",
        "full_name": "[Demo] Dr. Zubaida Khan",
        "bio": "Neurology trainee pending credential inspection by admin.",
        "qualifications": ["MBBS", "FCPS (Part 2)"],
        "years_experience": 5,
        "consultation_fee": 1000.0,
        "clinic_name": "Anwer Khan Modern Hospital",
        "city": "Dhaka",
        "verification_status": VerificationStatus.PENDING.value,
        "specialty_id": "11111111-0000-0000-0000-000000000001",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000009",
        "doc_id": "d2000000-0000-0000-0000-000000000009",
        "email": "dr.rafiqul.suspended@medimatch.test",
        "full_name": "[Demo] Dr. Rafiqul Islam",
        "bio": "Profile suspended due to outdated institutional credentials.",
        "qualifications": ["MBBS"],
        "years_experience": 7,
        "consultation_fee": 800.0,
        "clinic_name": "City Care Clinic",
        "city": "Chittagong",
        "verification_status": VerificationStatus.SUSPENDED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000003",
    },
    {
        "user_id": "d1000000-0000-0000-0000-000000000010",
        "doc_id": "d2000000-0000-0000-0000-000000000010",
        "email": "dr.nabil.rejected@medimatch.test",
        "full_name": "[Demo] Dr. Tariq Nabil",
        "bio": "Application rejected due to incomplete credential submissions.",
        "qualifications": ["MBBS"],
        "years_experience": 2,
        "consultation_fee": 600.0,
        "clinic_name": "Independent Medical Care",
        "city": "Dhaka",
        "verification_status": VerificationStatus.REJECTED.value,
        "specialty_id": "11111111-0000-0000-0000-000000000003",
    },
]


def run_seed():
    db_url = settings.DATABASE_URL
    if not db_url:
        print("[ERROR] DATABASE_URL is not set.")
        sys.exit(1)

    print("[INFO] Connecting to PostgreSQL database for seeding...")
    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=RealDictCursor)

    try:
        # 1. Seed Specialties
        print("[INFO] Seeding specialties...")
        for spec in SPECIALTIES:
            cur.execute(
                """
                INSERT INTO public.specialties (id, name, description)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    name = EXCLUDED.name,
                    description = EXCLUDED.description;
                """,
                (spec["id"], spec["name"], spec["description"]),
            )
        print(f"[SUCCESS] {len(SPECIALTIES)} specialties seeded.")

        # 2. Seed Core Test Accounts
        print("[INFO] Seeding 3 core test accounts (Admin, Patient, Doctor)...")
        for u in DEMO_USERS:
            cur.execute(
                """
                INSERT INTO auth.users (id, aud, role, email)
                VALUES (%s, 'authenticated', 'authenticated', %s)
                ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
                """,
                (u["id"], u["email"]),
            )

            cur.execute(
                """
                INSERT INTO public.profiles (id, role, full_name, phone)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET 
                    role = EXCLUDED.role,
                    full_name = EXCLUDED.full_name,
                    phone = EXCLUDED.phone;
                """,
                (u["id"], u["role"], u["full_name"], u["phone"]),
            )

            # If user has a doctor_profile
            dp = u.get("doctor_profile")
            if dp:
                cur.execute(
                    """
                    INSERT INTO public.doctor_profiles 
                        (id, user_id, bio, qualifications, years_experience, consultation_fee, clinic_name, city, verification_status)
                    VALUES 
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        bio = EXCLUDED.bio,
                        qualifications = EXCLUDED.qualifications,
                        years_experience = EXCLUDED.years_experience,
                        consultation_fee = EXCLUDED.consultation_fee,
                        clinic_name = EXCLUDED.clinic_name,
                        city = EXCLUDED.city,
                        verification_status = EXCLUDED.verification_status;
                    """,
                    (
                        dp["id"],
                        u["id"],
                        dp["bio"],
                        dp["qualifications"],
                        dp["years_experience"],
                        dp["consultation_fee"],
                        dp["clinic_name"],
                        dp["city"],
                        dp["verification_status"],
                    ),
                )
                if dp.get("specialty_id"):
                    cur.execute(
                        """
                        INSERT INTO public.doctor_specialties (doctor_id, specialty_id)
                        VALUES (%s, %s)
                        ON CONFLICT (doctor_id, specialty_id) DO NOTHING;
                        """,
                        (dp["id"], dp["specialty_id"]),
                    )

        print("[SUCCESS] Core test accounts seeded.")

        # 3. Seed 10 Bangladesh Demo Doctors
        print("[INFO] Seeding 10 demo doctors...")
        for doc in DEMO_DOCTORS:
            # Create auth user
            cur.execute(
                """
                INSERT INTO auth.users (id, aud, role, email)
                VALUES (%s, 'authenticated', 'authenticated', %s)
                ON CONFLICT (id) DO UPDATE SET email = EXCLUDED.email;
                """,
                (doc["user_id"], doc["email"]),
            )

            # Create profile
            cur.execute(
                """
                INSERT INTO public.profiles (id, role, full_name)
                VALUES (%s, 'doctor', %s)
                ON CONFLICT (id) DO UPDATE SET 
                    role = 'doctor',
                    full_name = EXCLUDED.full_name;
                """,
                (doc["user_id"], doc["full_name"]),
            )

            # Create doctor profile
            cur.execute(
                """
                INSERT INTO public.doctor_profiles 
                    (id, user_id, bio, qualifications, years_experience, consultation_fee, clinic_name, city, verification_status)
                VALUES 
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    bio = EXCLUDED.bio,
                    qualifications = EXCLUDED.qualifications,
                    years_experience = EXCLUDED.years_experience,
                    consultation_fee = EXCLUDED.consultation_fee,
                    clinic_name = EXCLUDED.clinic_name,
                    city = EXCLUDED.city,
                    verification_status = EXCLUDED.verification_status;
                """,
                (
                    doc["doc_id"],
                    doc["user_id"],
                    doc["bio"],
                    doc["qualifications"],
                    doc["years_experience"],
                    doc["consultation_fee"],
                    doc["clinic_name"],
                    doc["city"],
                    doc["verification_status"],
                ),
            )

            # Link specialty
            cur.execute(
                """
                INSERT INTO public.doctor_specialties (doctor_id, specialty_id)
                VALUES (%s, %s)
                ON CONFLICT (doctor_id, specialty_id) DO NOTHING;
                """,
                (doc["doc_id"], doc["specialty_id"]),
            )

        # 4. Seed Upcoming Availability Slots for Approved Doctors
        print("[INFO] Seeding upcoming availability slots for approved doctors...")
        approved_doc_ids = ["d0000000-0000-0000-0000-000000000000"] + [
            d["doc_id"] for d in DEMO_DOCTORS if d["verification_status"] == VerificationStatus.APPROVED.value
        ]

        from datetime import datetime, timedelta, timezone
        now_dt = datetime.now(timezone.utc)

        total_slots_seeded = 0
        for doc_id in approved_doc_ids:
            # Clear old unbooked slots for clean idempotency
            cur.execute("DELETE FROM public.availability_slots WHERE doctor_id = %s AND is_booked = false;", (doc_id,))

            # Generate slots across the next 10 days
            for day_offset in range(1, 11):
                day_base = now_dt + timedelta(days=day_offset)
                # Morning slot: 10:00 - 10:30 AM UTC
                m_start = day_base.replace(hour=10, minute=0, second=0, microsecond=0)
                m_end = day_base.replace(hour=10, minute=30, second=0, microsecond=0)
                # Afternoon slot: 15:00 - 15:30 PM UTC
                a_start = day_base.replace(hour=15, minute=0, second=0, microsecond=0)
                a_end = day_base.replace(hour=15, minute=30, second=0, microsecond=0)

                for s_start, s_end in [(m_start, m_end), (a_start, a_end)]:
                    cur.execute(
                        """
                        INSERT INTO public.availability_slots (id, doctor_id, start_time, end_time, is_booked)
                        VALUES (%s, %s, %s, %s, false);
                        """,
                        (str(uuid.uuid4()), doc_id, s_start, s_end),
                    )
                    total_slots_seeded += 1

        print(f"[SUCCESS] Seeded {total_slots_seeded} future availability slots for {len(approved_doc_ids)} approved doctors.")

        conn.commit()
        print("[SUCCESS] All demo doctors and schedules seeded successfully!")
        print("  - 6 Approved (searchable by patients)")
        print("  - 2 Pending (awaiting verification)")
        print("  - 1 Suspended (hidden from search)")
        print("  - 1 Rejected (hidden from search)")

    except Exception as e:
        conn.rollback()
        print(f"[ERROR] Seeding failed: {e}")
        cur.close()
        conn.close()
        sys.exit(1)

    cur.close()
    conn.close()


if __name__ == "__main__":
    run_seed()
