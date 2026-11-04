"""Recommendation Quality Evaluation for MediMatch AI.

Each case is symptom text and the specialty a clinician would expect. Retrieval gets the symptoms
only, with every specialty allowed, so the answer has to come from the vector ranking. An earlier
version passed the expected specialty in as the query and could not fail.

Metrics:
- Precision@3: share of the top 3 doctors in the expected specialty, averaged over cases.
- Hit@3: share of cases with at least one such doctor in the top 3.

This measures the retrieval step alone, using the real embedding model and index. Set DATABASE and
Supabase variables to the project being measured. It never writes.

Usage:
    python backend/scripts/eval_recommendations.py
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.search.recommend import recommend_doctors

ALL_SPECIALTIES = ["Neurology", "Cardiology", "General Medicine"]

CASES: list[tuple[str, str]] = [
    ("throbbing headache on one side with light sensitivity", "Neurology"),
    ("tension headaches and tight neck for three weeks", "Neurology"),
    ("numbness and tingling in my feet and hands", "Neurology"),
    ("spinning sensation and loss of balance when i turn my head", "Neurology"),
    ("tremor in my right hand that gets worse", "Neurology"),
    ("memory problems and trouble finding words", "Neurology"),
    ("muscle weakness in my legs over several months", "Neurology"),
    ("recovering after a stroke, need follow up", "Neurology"),
    ("nerve pain shooting down my leg", "Neurology"),
    ("matha betha ar matha ghurano", "Neurology"),
    ("high blood pressure readings at home", "Cardiology"),
    ("heart flutters and palpitations after coffee", "Cardiology"),
    ("high cholesterol and family history of heart disease", "Cardiology"),
    ("ankles swelling and tired when walking uphill", "Cardiology"),
    ("irregular heartbeat found on a routine ecg", "Cardiology"),
    ("follow up after angioplasty", "Cardiology"),
    ("need a heart checkup before surgery", "Cardiology"),
    ("buk dhorphor kore majhe majhe", "Cardiology"),
    ("fever and body aches for three days", "General Medicine"),
    ("dry cough and sore throat", "General Medicine"),
    ("loose motions and stomach cramps", "General Medicine"),
    ("feeling tired all the time and low appetite", "General Medicine"),
    ("seasonal cold and runny nose", "General Medicine"),
    ("urine burning for two days", "General Medicine"),
    ("general health checkup", "General Medicine"),
    ("skin rash that itches", "General Medicine"),
    ("jor ar kashi tin din dhore", "General Medicine"),
    ("pet betha ar gas", "General Medicine"),
]


def run_evaluation() -> None:
    print("MediMatch recommendation evaluation")
    print(f"Cases: {len(CASES)}, symptoms only, all specialties allowed\n")

    precision_total = 0.0
    hits = 0
    modes = {"hybrid": 0, "sql_fallback": 0}
    failures: list[str] = []

    for symptoms, expected in CASES:
        res = recommend_doctors(
            {
                "candidate_specialties": ALL_SPECIALTIES,
                "city": "Bangladesh",
                "keywords": [symptoms],
            },
            top_k=3,
        )
        modes[res.retrieval_mode] = modes.get(res.retrieval_mode, 0) + 1
        top = [[s["name"] for s in rec.specialties] for rec in res.recommendations]
        relevant = sum(1 for names in top if expected in names)

        precision_total += relevant / 3
        if relevant:
            hits += 1
        else:
            failures.append(f"  {symptoms!r} expected {expected}, got {top}")

    print(f"Precision@3: {100 * precision_total / len(CASES):.1f}%")
    print(f"Hit@3:       {100 * hits / len(CASES):.1f}% ({hits} of {len(CASES)})")
    print(f"Retrieval:   {modes}")
    print(f"\nFailures ({len(failures)}):")
    print("\n".join(failures) or "  none")


if __name__ == "__main__":
    run_evaluation()
