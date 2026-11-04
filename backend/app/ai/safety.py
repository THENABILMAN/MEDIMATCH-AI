"""Safety Module for MediMatch AI.

Provides:
1. Rule-based emergency detection in English, Bangla, and transliterated Bangla (Banglish)
   using externalized patterns from emergency_patterns.json.
2. Fixed, non-LLM emergency escalation responses (defaulting to 999 for Bangladesh).
3. Output guard inspecting LLM replies to intercept and sanitize diagnostic or prescriptive language.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("medimatch.ai.safety")

PATTERNS_FILE = Path(__file__).resolve().parent / "data" / "emergency_patterns.json"

_DEFAULT_EMERGENCY_NUMBER = "999"


def _normalize(text: str) -> str:
    """Unifies input variants that would otherwise slip past a pattern.

    NFC gives Bengali letters such as U+09DC one encoding whichever keyboard typed them,
    and phone keyboards type a curly apostrophe in words like "can't".
    """
    return unicodedata.normalize("NFC", text).replace("\u2019", "'").strip()


def _load_patterns(path: Path = PATTERNS_FILE) -> Tuple[List[Tuple[str, re.Pattern]], str]:
    """Compiles emergency patterns, failing loudly so triage can never start switched off."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    compiled: List[Tuple[str, re.Pattern]] = []
    for cat in data.get("categories", []):
        cat_name = cat.get("name", "general_emergency")
        for pat in cat.get("patterns", []):
            compiled.append((cat_name, re.compile(_normalize(pat), re.IGNORECASE | re.UNICODE)))

    if not compiled:
        raise RuntimeError(f"No emergency patterns loaded from {path}")
    return compiled, data.get("emergency_number", _DEFAULT_EMERGENCY_NUMBER)


# Load and compile patterns at import time
_COMPILED_PATTERNS, _DEFAULT_EMERGENCY_NUMBER = _load_patterns()


def check_emergency(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Inspects patient input against rule-based emergency patterns.
    
    Returns:
        (is_emergency: bool, category: str | None, matched_pattern: str | None)
    """
    if not text:
        return False, None, None

    normalized = _normalize(text)

    for cat_name, compiled_pat in _COMPILED_PATTERNS:
        match = compiled_pat.search(normalized)
        if match:
            matched_str = match.group(0)
            logger.warning(
                f"[SAFETY ESCALATION] Emergency detected in category '{cat_name}': matched '{matched_str}'"
            )
            return True, cat_name, matched_str

    return False, None, None


def get_emergency_response(emergency_number: str = "999") -> str:
    """Returns a deterministic, non-LLM emergency alert directing the patient to emergency care."""
    return (
        f"🚨 EMERGENCY ALERT: Based on your symptoms, this may require immediate emergency medical care.\n\n"
        f"Please call {emergency_number} immediately or proceed directly to the nearest hospital emergency room.\n"
        f"Do not wait for an online doctor appointment. Emergency medical personnel should evaluate you without delay."
    )


# ------------------------------------------------------------------------------
# Output Guard (Anti-Diagnosis & Anti-Prescription)
# ------------------------------------------------------------------------------

_CONDITIONS = (
    r"pneumonia|stroke|heart\s+attack|cancer|tumou?r|hypertension|migraine|diabetes|asthma|"
    r"appendicitis|flu|influenza|covid(-19)?|dengue|typhoid|chikungunya|malaria|tuberculosis|"
    r"infection|gastritis|ulcer|anemia|anaemia|depression|anxiety|bronchitis|sinusitis|arthritis"
)
_DRUGS = (
    r"amoxicillin|paracetamol|acetaminophen|ibuprofen|antibiotics?|ciprofloxacin|azithromycin|"
    r"metronidazole|omeprazole|aspirin|napa|ace|antacids?|painkillers?|antihistamines?|insulin"
)
_BN_CONDITIONS = "ডায়াবেটিস|ক্যান্সার|নিউমোনিয়া|ডেঙ্গু|টাইফয়েড|জন্ডিস|হার্ট\\s*অ্যাটাক|স্ট্রোক|মাইগ্রেন|সংক্রমণ"

DIAGNOSIS_PATTERNS = [
    re.compile(
        r"\byou(\s+\w+){0,2}\s+(have|are\s+suffering\s+from|got)\s+((a|an|the)\s+)?(\w+\s+)?"
        rf"({_CONDITIONS})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(this|it|that)(\s+\w+){0,2}\s+(is|be|sounds\s+like|looks\s+like|seems\s+like)\s+"
        rf"((just|probably|likely|definitely)\s+)?((a|an|the)\s+)?(\w+\s+)?({_CONDITIONS})\b",
        re.IGNORECASE,
    ),
    re.compile(r"\b(i\s+diagnose\s+you|diagnosis\s*:|this\s+is\s+(definitely\s+)?a\s+case\s+of)\b", re.IGNORECASE),
    re.compile(
        r"\b(your\s+condition\s+is\s+harmless|nothing\s+to\s+worry\s+about|nothing\s+serious|"
        r"(do\s+not|don't|no\s+need\s+to)\s+worry|(is|it's|that's)\s+(probably\s+|likely\s+)?"
        r"(harmless|not\s+serious))\b",
        re.IGNORECASE,
    ),
    re.compile(rf"আপনার.*({_BN_CONDITIONS}).*(আছে|হয়েছে|হতে\s*পারে)"),
]

PRESCRIPTION_PATTERNS = [
    re.compile(r"\b\d+\s*(mg|ml|tablets?|pills?|capsules?)\b", re.IGNORECASE),
    re.compile(r"\b(i\s+prescribe|prescription\s*:|prescribing\s+you)\b", re.IGNORECASE),
    re.compile(rf"\b(take|try|use|using|taking)\s+(\w+\s+){{0,2}}({_DRUGS})\b", re.IGNORECASE),
    re.compile(r"\b(start\s+taking\s+[a-z]+|dosage\s*:|every\s+\d+\s+hours)\b", re.IGNORECASE),
    re.compile(r"(ওষুধ|ট্যাবলেট|ক্যাপসুল|সিরাপ)\s*(টি\s*)?(খান|খাবেন|নিন|সেবন)"),
    re.compile(r"\d+\s*(মিগ্রা|ট্যাবলেট|ক্যাপসুল)"),
    re.compile(r"\b(oshudh?|tablet|capsule)\s+(khan|khaben|nin)\b", re.IGNORECASE),
]

SAFE_FALLBACK_DISCLAIMER = (
    "As an AI assistant, I cannot diagnose medical conditions or prescribe medications. "
    "Please consult a qualified doctor for professional diagnosis and clinical treatment."
)


def output_guard(text: str) -> str:
    """Inspects assistant output and blocks unauthorized diagnosis or medication language.
    
    If diagnostic or prescriptive phrasing is found, neutralizes and replaces it with safe advisory text.
    """
    if not text:
        return text

    normalized = _normalize(text)

    # Check for diagnosis claims
    for pat in DIAGNOSIS_PATTERNS:
        if pat.search(normalized):
            logger.warning("[OUTPUT GUARD] Blocked diagnostic language from LLM response")
            return (
                f"I cannot provide a medical diagnosis for your symptoms. "
                f"{SAFE_FALLBACK_DISCLAIMER} I can, however, help you find a suitable doctor."
            )

    # Check for prescription language
    for pat in PRESCRIPTION_PATTERNS:
        if pat.search(normalized):
            logger.warning("[OUTPUT GUARD] Blocked prescription/medication language from LLM response")
            return (
                f"I cannot prescribe medications or dosage instructions. "
                f"{SAFE_FALLBACK_DISCLAIMER} Would you like help finding a licensed physician?"
            )

    return text

