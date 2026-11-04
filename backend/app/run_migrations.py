"""Migration Runner Utility for MediMatch AI.

Applies each SQL file in supabase/migrations/ once, in order, and records it in
public.schema_migrations. Every file runs in its own transaction, so a failure leaves that file
with no effect and stops the run.

A database created before tracking existed needs a baseline, to say which files it already has:

    python backend/app/run_migrations.py --baseline 00007
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import psycopg2

from app.core.config import settings

MIGRATIONS_DIR = backend_dir.parent / "supabase" / "migrations"

CREATE_TRACKING_TABLE = """
CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE public.schema_migrations ENABLE ROW LEVEL SECURITY;
"""


def apply_migrations(
    db_url: str,
    migrations_dir: Path = MIGRATIONS_DIR,
    baseline: Optional[str] = None,
) -> List[str]:
    """Applies pending files and returns their names. Raises if any of them fails."""
    conn = psycopg2.connect(db_url)
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT to_regclass('public.schema_migrations')")
            first_run = cur.fetchone()[0] is None
            cur.execute("SELECT to_regclass('public.profiles')")
            existing_schema = cur.fetchone()[0] is not None
            if first_run and existing_schema and baseline is None:
                raise RuntimeError(
                    "This database has tables but no migration history. "
                    "Pass --baseline with the last migration it already has."
                )
            cur.execute(CREATE_TRACKING_TABLE)
            cur.execute("SELECT version FROM public.schema_migrations")
            applied = {row[0] for row in cur.fetchall()}

        pending: List[Path] = []
        for sql_file in sorted(migrations_dir.glob("*.sql")):
            if sql_file.name in applied:
                continue
            if baseline is not None and sql_file.name[: len(baseline)] <= baseline:
                with conn, conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                        (sql_file.name,),
                    )
                continue
            pending.append(sql_file)

        done: List[str] = []
        for sql_file in pending:
            with conn, conn.cursor() as cur:
                cur.execute(sql_file.read_text(encoding="utf-8"))
                cur.execute(
                    "INSERT INTO public.schema_migrations (version) VALUES (%s)",
                    (sql_file.name,),
                )
            done.append(sql_file.name)
        return done
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply pending database migrations")
    parser.add_argument("--baseline", help="Mark migrations up to this prefix as already applied")
    args = parser.parse_args()

    if not settings.DATABASE_URL:
        print("[ERROR] DATABASE_URL is not set in environment or .env file.")
        sys.exit(1)

    try:
        applied = apply_migrations(settings.DATABASE_URL, baseline=args.baseline)
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        sys.exit(1)

    for name in applied:
        print(f"[SUCCESS] Applied {name}")
    print(f"[SUCCESS] {len(applied)} migration(s) applied.")


if __name__ == "__main__":
    main()
