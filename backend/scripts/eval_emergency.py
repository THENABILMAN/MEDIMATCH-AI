"""Measures the classifier's emergency net against the real LLM. Opt-in: it calls OpenRouter.

Uses only the written test phrases, never patient data. Reports the classifier alone, because the
rules were tuned on these phrases and their score here says nothing about unseen wording.

Usage:
    python backend/scripts/eval_emergency.py --emergencies 30 --ordinary 15 --pause 4
"""

import argparse
import logging
import random
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = Path(__file__).resolve().parent.parent
for path in (backend_dir, backend_dir / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from test_safety_tables import HELD_OUT_EMERGENCIES, HELD_OUT_ORDINARY

from app.ai.graph import classify_intent_node
from app.core.config import settings


def flagged(text: str) -> bool:
    state = {"messages": [{"role": "user", "content": text}]}
    return classify_intent_node(state).get("safety_status") == "emergency"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emergencies", type=int, default=30)
    parser.add_argument("--ordinary", type=int, default=15)
    parser.add_argument("--pause", type=float, default=4.0, help="Seconds between calls")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if not settings.OPENROUTER_API_KEY:
        sys.exit("OPENROUTER_API_KEY is not set.")

    logging.disable(logging.WARNING)
    rng = random.Random(args.seed)
    emergencies = rng.sample(HELD_OUT_EMERGENCIES, min(args.emergencies, len(HELD_OUT_EMERGENCIES)))
    ordinary = rng.sample(HELD_OUT_ORDINARY, min(args.ordinary, len(HELD_OUT_ORDINARY)))
    print(f"Model: {settings.OPENROUTER_MODEL}")

    missed, false_alarms = [], []
    for label, phrases, wrong, expected in (
        ("emergency", emergencies, missed, True),
        ("ordinary", ordinary, false_alarms, False),
    ):
        for text in phrases:
            result = flagged(text)
            print(f"  {label:9} {'flagged' if result else 'not flagged':11} {text}")
            if result != expected:
                wrong.append(text)
            time.sleep(args.pause)

    print(f"\nEmergencies flagged: {len(emergencies) - len(missed)} of {len(emergencies)}")
    print(f"Ordinary messages wrongly flagged: {len(false_alarms)} of {len(ordinary)}")
    print("A failed call counts as not flagged, so an outage appears here as a missed emergency.")


if __name__ == "__main__":
    main()
