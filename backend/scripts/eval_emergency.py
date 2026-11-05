"""Measures the classifier's emergency net against the real LLM. Opt-in: it calls Groq.

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

from app.ai.graph import _get_verified_specialty_names, build_system_prompt
from app.ai.llm import LLMUnavailableError, get_llm_client
from app.ai.state import AssistantTurn
from app.core.config import settings


def classify(text: str) -> bool | None:
    """True or False from the model, or None if the call failed."""
    state = {"messages": [{"role": "user", "content": text}]}
    try:
        result = get_llm_client().generate_structured(
            messages=state["messages"],
            response_model=AssistantTurn,
            system_prompt=build_system_prompt(state, _get_verified_specialty_names()),
        )
    except (LLMUnavailableError, ValueError):
        return None
    return result.possible_emergency


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--emergencies", type=int, default=30)
    parser.add_argument("--ordinary", type=int, default=15)
    parser.add_argument("--pause", type=float, default=4.0, help="Seconds between calls")
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    if not settings.GROQ_API_KEY:
        sys.exit("GROQ_API_KEY is not set.")

    logging.disable(logging.WARNING)
    rng = random.Random(args.seed)
    emergencies = rng.sample(HELD_OUT_EMERGENCIES, min(args.emergencies, len(HELD_OUT_EMERGENCIES)))
    ordinary = rng.sample(HELD_OUT_ORDINARY, min(args.ordinary, len(HELD_OUT_ORDINARY)))
    print(f"Model: {settings.GROQ_MODEL}")

    missed, false_alarms, failed = [], [], []
    for label, phrases, wrong, expected in (
        ("emergency", emergencies, missed, True),
        ("ordinary", ordinary, false_alarms, False),
    ):
        for text in phrases:
            result = classify(text)
            shown = "CALL FAILED" if result is None else ("flagged" if result else "not flagged")
            print(f"  {label:9} {shown:11} {text}")
            if result is None:
                failed.append(text)
            elif result != expected:
                wrong.append(text)
            time.sleep(args.pause)

    answered = len(emergencies) + len(ordinary) - len(failed)
    print(f"\nCalls answered: {answered}, failed: {len(failed)}")
    print(f"Emergencies missed: {len(missed)}")
    print(f"Ordinary messages wrongly flagged: {len(false_alarms)}")


if __name__ == "__main__":
    main()
