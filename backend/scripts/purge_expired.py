"""Erases chats and symptom sessions older than CHAT_RETENTION_DAYS. Run daily.

Usage:
    python backend/scripts/purge_expired.py
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.account_service import purge_expired_chats

if __name__ == "__main__":
    print(f"[INFO] Erased {purge_expired_chats()} expired conversation(s).")
