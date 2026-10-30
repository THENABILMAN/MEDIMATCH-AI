"""Recommendation Quality Evaluation Benchmark for MediMatch AI.

Evaluates hybrid recommendation accuracy across at least 20 diverse clinical queries
in English and Banglish across Neurology, Cardiology, and General Medicine in Bangladesh.

Metrics:
- Precision@3: Fraction of test queries where at least one of the top 3 recommended
  doctors belongs to the expected medical specialty.
- Failure Analysis: Logs any queries that did not retrieve an expected specialist in the top 3.

Usage:
    python backend/scripts/eval_recommendations.py
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.search.recommend import recommend_doctors

# 20+ Diverse Clinical Queries with Expected Target Specialties
BENCHMARK_CASES = [
    # Neurology (6 cases)
    {
        "query": "Severe throbbing unilateral headache with light sensitivity and visual aura",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },
    {
        "query": "Chronic tension headaches and neck stiffness for three weeks",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },
    {
        "query": "Numbness and tingling in feet and hands with peripheral neuropathy",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },
    {
        "query": "Occasional spinning sensation vertigo and loss of balance",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },
    {
        "query": "Post-stroke rehabilitation and motor recovery consultation",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },
    {
        "query": "khub matha betha ar chokh jhapsha lagche",
        "candidate_specialties": ["Neurology"],
        "city": "Dhaka",
        "expected_specialty": "Neurology",
    },

    # Cardiology (7 cases)
    {
        "query": "Heart racing palpitations and irregular pulse after light exercise",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "High blood pressure hypertension routine checkup and echocardiography review",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "Shortness of breath on exertion and mild ankle swelling",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "Cardiovascular risk screening and cholesterol lipid profile review",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "Heart specialist consultation in Sylhet for coronary artery disease checkup",
        "candidate_specialties": ["Cardiology"],
        "city": "Sylhet",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "buke dhorfor kora ar high blood pressure checkup",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },
    {
        "query": "Cardiologist in Panthapath for heart murmur and ECG test review",
        "candidate_specialties": ["Cardiology"],
        "city": "Dhaka",
        "expected_specialty": "Cardiology",
    },

    # General Medicine (7 cases)
    {
        "query": "High fever, chills, body ache, and persistent fatigue for four days",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "Chronic dry cough, mild sore throat, and low-grade temperature",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "Abdominal discomfort, bloating, and indigestion after meals",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "General physician in Chittagong for seasonal viral fever treatment",
        "candidate_specialties": ["General Medicine"],
        "city": "Chittagong",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "Routine annual health wellness review and complete blood count interpretation",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "Unexplained weight loss and constant low energy weakness",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
    {
        "query": "daktar dekhaite chai jor ar sharir betha 3 din dhore",
        "candidate_specialties": ["General Medicine"],
        "city": "Dhaka",
        "expected_specialty": "General Medicine",
    },
]


def run_evaluation():
    print("=" * 70)
    print(" 📊 MediMatch AI — Recommendation Quality Benchmark (Precision@3)")
    print("=" * 70)
    print(f"Total Benchmark Queries: {len(BENCHMARK_CASES)}\n")

    passed_count = 0
    failures: List[Dict[str, Any]] = []

    for idx, case in enumerate(BENCHMARK_CASES, 1):
        query = case["query"]
        expected = case["expected_specialty"]
        city = case["city"]
        cands = case["candidate_specialties"]

        search_criteria = {
            "keywords": [query],
            "candidate_specialties": cands,
            "city": city,
        }

        try:
            res = recommend_doctors(search_criteria, top_k=3)
            recs = res.recommendations

            # Check if expected specialty is present in any of top 3 recommendations
            top_specialties = []
            for doc in recs:
                for s in doc.specialties:
                    name = s.get("name") if isinstance(s, dict) else str(s)
                    if name:
                        top_specialties.append(name)

            is_match = expected in top_specialties
            status_tag = "PASS" if is_match else "FAIL"

            if is_match:
                passed_count += 1
            else:
                failures.append({
                    "case_num": idx,
                    "query": query,
                    "expected": expected,
                    "city": city,
                    "top_docs": [f"{d.full_name} ({[s['name'] for s in d.specialties]})" for d in recs],
                    "retrieval_mode": res.retrieval_mode,
                })

            top_doc_names = ", ".join([d.full_name.split()[0] + " " + d.full_name.split()[-1] for d in recs]) if recs else "None"
            print(f"[{status_tag}] #{idx:02d}: {expected.ljust(16)} | Found: {top_doc_names[:35]}")

        except Exception as e:
            print(f"[ERROR] #{idx:02d} Failed executing query: {e}")
            failures.append({
                "case_num": idx,
                "query": query,
                "expected": expected,
                "error": str(e),
            })

    total_queries = len(BENCHMARK_CASES)
    precision_at_3 = (passed_count / total_queries) * 100.0

    print("\n" + "=" * 70)
    print(" 📈 Evaluation Results Summary")
    print("=" * 70)
    print(f"  • Total Evaluated Queries : {total_queries}")
    print(f"  • Successful Matches      : {passed_count}")
    print(f"  • Failed Matches          : {len(failures)}")
    print(f"  • Precision@3 Score       : {precision_at_3:.1f}%")

    if failures:
        print("\n⚠️ Failure Breakdown:")
        for f in failures:
            print(f"  - Case #{f.get('case_num')}: Expected '{f.get('expected')}' in {f.get('city')}")
            print(f"    Query: \"{f.get('query')}\"")
            if "top_docs" in f:
                print(f"    Returned: {f.get('top_docs')}")
            if "error" in f:
                print(f"    Error: {f.get('error')}")

    print("=" * 70)

    # Threshold requirement: At least 85% precision@3
    if precision_at_3 >= 85.0:
        print("[SUCCESS] Benchmark PASSED with high recommendation accuracy!")
        return True
    else:
        print(f"[FAIL] Benchmark score ({precision_at_3:.1f}%) below target threshold (85%).")
        return False


if __name__ == "__main__":
    success = run_evaluation()
    sys.exit(0 if success else 1)

