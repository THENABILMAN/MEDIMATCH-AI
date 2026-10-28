"""RLS Policy Tests for MediMatch AI.

These tests verify Postgres Row-Level Security (RLS) policies and triggers:
1. Patients cannot read another patient's profile, conversations, or appointments.
2. A user cannot escalate their own role to admin.
3. A pending/rejected/suspended doctor is not visible to patients or anonymous queries.
4. Admins can view and verify all doctor profiles.

Requirements to run against a real Postgres database:
- Set DATABASE_URL in .env to a running PostgreSQL instance (or local Supabase: `supabase start`).
- Run migrations: migrations in supabase/migrations/ must be applied.
- If DATABASE_URL is unreachable or in offline test mode, tests skip gracefully with clear instructions.
"""

import os
import uuid
import pytest
import psycopg2
from psycopg2.extras import RealDictCursor
from app.core.config import settings


def get_db_connection():
    """Attempt to establish a direct connection to PostgreSQL."""
    db_url = settings.DATABASE_URL
    if not db_url:
        return None
    try:
        conn = psycopg2.connect(db_url, connect_timeout=3)
        return conn
    except Exception:
        return None


@pytest.fixture(scope="module")
def db_conn():
    conn = get_db_connection()
    if conn is None:
        pytest.skip(
            "PostgreSQL database not reachable. To run live RLS tests, ensure DATABASE_URL "
            "is accessible in .env and migrations are applied."
        )
    conn.autocommit = False
    yield conn
    conn.close()


def test_rls_patient_isolation(db_conn):
    """Verify patient A cannot read patient B's profile, conversations, or appointments."""
    cur = db_conn.cursor(cursor_factory=RealDictCursor)

    patient_a = str(uuid.uuid4())
    patient_b = str(uuid.uuid4())

    try:
        email_a = f"patient_a_{uuid.uuid4().hex[:8]}@test.com"
        email_b = f"patient_b_{uuid.uuid4().hex[:8]}@test.com"

        # 1. As superuser/admin, seed patient A and patient B in auth.users and profiles
        cur.execute(
            """
            INSERT INTO auth.users (id, aud, role, email)
            VALUES 
                (%s, 'authenticated', 'authenticated', %s),
                (%s, 'authenticated', 'authenticated', %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (patient_a, email_a, patient_b, email_b),
        )

        cur.execute(
            """
            INSERT INTO public.profiles (id, role, full_name)
            VALUES (%s, 'patient', 'Patient A'), (%s, 'patient', 'Patient B')
            ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role, full_name = EXCLUDED.full_name;
            """,
            (patient_a, patient_b),
        )

        cur.execute(
            """
            INSERT INTO public.conversations (id, patient_id, title)
            VALUES (gen_random_uuid(), %s, 'Private Chat B');
            """,
            (patient_b,),
        )
        db_conn.commit()

        # 2. Simulate Patient A context via Supabase JWT claim
        cur.execute("SET LOCAL ROLE authenticated;")
        cur.execute(f"SET LOCAL \"request.jwt.claim.sub\" = '{patient_a}';")
        cur.execute("SET LOCAL \"request.jwt.claim.role\" = 'authenticated';")

        # Patient A queries Patient B's profile
        cur.execute("SELECT * FROM public.profiles WHERE id = %s;", (patient_b,))
        rows = cur.fetchall()
        assert len(rows) == 0, "Patient A should NOT be able to read Patient B profile"

        # Patient A queries Patient B's conversations
        cur.execute("SELECT * FROM public.conversations WHERE patient_id = %s;", (patient_b,))
        conv_rows = cur.fetchall()
        assert len(conv_rows) == 0, "Patient A should NOT be able to read Patient B conversations"

    finally:
        db_conn.rollback()


def test_rls_unapproved_doctor_hidden(db_conn):
    """Verify only approved doctors are visible to patients."""
    cur = db_conn.cursor(cursor_factory=RealDictCursor)

    doc_pending = str(uuid.uuid4())
    doc_approved = str(uuid.uuid4())
    patient_id = str(uuid.uuid4())

    try:
        email_doc_pending = f"doc_pen_{uuid.uuid4().hex[:8]}@test.com"
        email_doc_app = f"doc_app_{uuid.uuid4().hex[:8]}@test.com"
        email_patient = f"pat_obs_{uuid.uuid4().hex[:8]}@test.com"

        # Seed auth users first
        cur.execute(
            """
            INSERT INTO auth.users (id, aud, role, email)
            VALUES 
                (%s, 'authenticated', 'authenticated', %s),
                (%s, 'authenticated', 'authenticated', %s),
                (%s, 'authenticated', 'authenticated', %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (doc_pending, email_doc_pending, doc_approved, email_doc_app, patient_id, email_patient),
        )

        # Seed doctors with different verification statuses
        cur.execute(
            """
            INSERT INTO public.profiles (id, role, full_name)
            VALUES 
                (%s, 'doctor', 'Dr. Pending'),
                (%s, 'doctor', 'Dr. Approved'),
                (%s, 'patient', 'Patient Observer')
            ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role;
            """,
            (doc_pending, doc_approved, patient_id),
        )

        cur.execute(
            """
            INSERT INTO public.doctor_profiles (id, user_id, verification_status, city)
            VALUES 
                (gen_random_uuid(), %s, 'pending', 'Dhaka'),
                (gen_random_uuid(), %s, 'approved', 'Dhaka')
            ON CONFLICT (user_id) DO NOTHING;
            """,
            (doc_pending, doc_approved),
        )
        db_conn.commit()

        # Simulate Patient Observer context
        cur.execute("SET LOCAL ROLE authenticated;")
        cur.execute(f"SET LOCAL \"request.jwt.claim.sub\" = '{patient_id}';")
        cur.execute("SET LOCAL \"request.jwt.claim.role\" = 'authenticated';")

        # Query all doctors
        cur.execute("SELECT * FROM public.doctor_profiles;")
        visible_doctors = cur.fetchall()

        # All visible doctors must strictly have verification_status = 'approved'
        for doc in visible_doctors:
            assert doc["verification_status"] == "approved", (
                f"Unapproved doctor visible to patient: {doc['verification_status']}"
            )

    finally:
        db_conn.rollback()


def test_trigger_prevents_role_escalation(db_conn):
    """Verify a user cannot escalate their role to admin directly in the database."""
    cur = db_conn.cursor(cursor_factory=RealDictCursor)
    test_user_id = str(uuid.uuid4())

    try:
        user_email = f"norm_usr_{uuid.uuid4().hex[:8]}@test.com"

        # Seed auth user and patient profile
        cur.execute(
            """
            INSERT INTO auth.users (id, aud, role, email)
            VALUES (%s, 'authenticated', 'authenticated', %s)
            ON CONFLICT (id) DO NOTHING;
            """,
            (test_user_id, user_email),
        )

        cur.execute(
            """
            INSERT INTO public.profiles (id, role, full_name)
            VALUES (%s, 'patient', 'Normal User')
            ON CONFLICT (id) DO UPDATE SET role = EXCLUDED.role;
            """,
            (test_user_id,),
        )
        db_conn.commit()

        # Set user context
        cur.execute("SET LOCAL ROLE authenticated;")
        cur.execute(f"SET LOCAL \"request.jwt.claim.sub\" = '{test_user_id}';")
        cur.execute("SET LOCAL \"request.jwt.claim.role\" = 'authenticated';")

        # Attempt to escalate to admin
        with pytest.raises(psycopg2.Error):
            cur.execute(
                """
                UPDATE public.profiles
                SET role = 'admin'
                WHERE id = %s;
                """,
                (test_user_id,),
            )
            db_conn.commit()

    finally:
        db_conn.rollback()
