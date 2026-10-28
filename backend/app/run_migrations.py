"""Migration Runner Utility for MediMatch AI.

Applies SQL migrations from supabase/migrations/ in sequential order
against the configured DATABASE_URL.
"""

import os
import sys
from pathlib import Path

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import psycopg2
from app.core.config import settings


def apply_migrations():
    db_url = settings.DATABASE_URL
    if not db_url:
        print("[ERROR] DATABASE_URL is not set in environment or .env file.")
        sys.exit(1)

    migrations_dir = Path(__file__).resolve().parent.parent.parent / "supabase" / "migrations"
    if not migrations_dir.exists():
        print(f"[ERROR] Migrations directory not found at {migrations_dir}")
        sys.exit(1)

    sql_files = sorted(migrations_dir.glob("*.sql"))
    if not sql_files:
        print("[INFO] No SQL migration files found.")
        return

    print(f"[INFO] Connecting to database...")
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Failed to connect to database: {e}")
        sys.exit(1)

    print(f"[INFO] Connected successfully. Found {len(sql_files)} migration(s).")

    for sql_file in sql_files:
        print(f"[INFO] Applying {sql_file.name}...")
        try:
            sql_content = sql_file.read_text(encoding="utf-8")
            cur.execute(sql_content)
            print(f"[SUCCESS] Applied {sql_file.name}")
        except Exception as e:
            print(f"[ERROR] Failed applying {sql_file.name}: {e}")
            cur.close()
            conn.close()
            sys.exit(1)

    cur.close()
    conn.close()
    print("[SUCCESS] All migrations applied successfully!")


if __name__ == "__main__":
    apply_migrations()
