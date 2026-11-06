"""Charges this month's subscription to every approved doctor on that plan. Run daily.

Each month is charged once, so daily runs also pick up doctors approved during the month.

Usage:
    python backend/scripts/bill_subscriptions.py
"""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.services.billing_service import bill_all_subscriptions

if __name__ == "__main__":
    print(f"[INFO] Added {bill_all_subscriptions()} subscription charge(s).")
