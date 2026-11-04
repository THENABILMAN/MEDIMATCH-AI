"""Safety Module for MediMatch AI.

Provides:
1. Rule-based emergency detection in English, Bangla, and transliterated Bangla (Banglish)
   using externalized patterns from emergency_patterns.json.
2. Fixed, non-LLM emergency escalation responses, in English and Bangla.
3. Output guard inspecting assistant replies to catch diagnosis, treatment and reassurance.

Crucial Rule: Patient text is NEVER logged here, not even the matched phrase.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import List, NamedTuple, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger("medimatch.ai.safety")

PATTERNS_FILE = Path(__file__).resolve().parent / "data" / "emergency_patterns.json"

_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_WHITESPACE = re.compile(r"\s+")
_CLAUSE_BREAK = re.compile(r"[.,;:!?\n]|\bbut\b|\band\b|\bthough\b|\bকিন্তু\b|\bkintu\b", re.IGNORECASE)


def _normalize(text: str) -> str:
    """Unifies input variants that would otherwise slip past a pattern.

    NFC gives Bengali letters such as U+09DC one encoding whichever keyboard typed them, some
    keyboards add invisible joiners inside words, and phones type a curly apostrophe.
    """
    text = unicodedata.normalize("NFC", text).replace("’", "'")
    return _WHITESPACE.sub(" ", _ZERO_WIDTH.sub("", text)).strip()


class EmergencyRule(NamedTuple):
    category: str
    pattern: re.Pattern
    negatable: bool


class Triage(NamedTuple):
    rules: List[EmergencyRule]
    negated_before: re.Pattern
    negated_after: re.Pattern


def _compile(pattern: str) -> re.Pattern:
    return re.compile(_normalize(pattern), re.IGNORECASE | re.UNICODE)


def _load_patterns(path: Path = PATTERNS_FILE) -> Triage:
    """Compiles emergency patterns, failing loudly so triage can never start switched off."""
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    rules: List[EmergencyRule] = []
    for cat in data.get("categories", []):
        cat_name = cat.get("name", "general_emergency")
        negatable = bool(cat.get("negatable", False))
        for pat in cat.get("patterns", []):
            rules.append(EmergencyRule(cat_name, _compile(pat), negatable))

    if not rules:
        raise RuntimeError(f"No emergency patterns loaded from {path}")

    negation = data.get("negation", {})
    return Triage(rules, _compile(negation.get("before", "(?!)")), _compile(negation.get("after", "(?!)")))


# Load and compile patterns at import time
_TRIAGE = _load_patterns()


def _is_negated(text: str, match: re.Match) -> bool:
    """True for a plain negation in the same clause, such as "no chest pain"."""
    clause = _CLAUSE_BREAK.split(text[: match.start()])[-1]
    return bool(_TRIAGE.negated_before.search(clause) or _TRIAGE.negated_after.match(text[match.end() :]))


def check_emergency(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Inspects patient input against rule-based emergency patterns.

    Every match is checked, so "no chest pain but I can't breathe" still escalates.

    Returns:
        (is_emergency: bool, category: str | None, matched_pattern: str | None)
    """
    if not text:
        return False, None, None

    normalized = _normalize(text)

    for rule in _TRIAGE.rules:
        for match in rule.pattern.finditer(normalized):
            if rule.negatable and _is_negated(normalized, match):
                continue
            logger.warning(f"[SAFETY ESCALATION] Emergency detected in category '{rule.category}'")
            return True, rule.category, match.group(0)

    return False, None, None


def get_emergency_response() -> str:
    """Returns the fixed, non-LLM emergency alert, in English and Bangla."""
    number = settings.EMERGENCY_NUMBER
    return (
        f"🚨 EMERGENCY ALERT: Based on what you described, this may need emergency medical care now.\n\n"
        f"Please call {number} immediately or go to the nearest hospital emergency room. "
        f"Do not wait for an appointment. If you may harm yourself, stay with someone you trust.\n\n"
        f"জরুরি সতর্কতা: আপনি যা লিখেছেন তাতে এখনই জরুরি চিকিৎসা দরকার হতে পারে।\n\n"
        f"অনুগ্রহ করে এখনই {number} নম্বরে কল করুন অথবা নিকটস্থ হাসপাতালের জরুরি বিভাগে যান। "
        f"অ্যাপয়েন্টমেন্টের জন্য অপেক্ষা করবেন না। নিজের ক্ষতি করার আশঙ্কা থাকলে বিশ্বস্ত কারও সঙ্গে থাকুন।"
    )


# ------------------------------------------------------------------------------
# Output Guard (Anti-Diagnosis, Anti-Prescription, Anti-Reassurance)
# ------------------------------------------------------------------------------
# A backstop. The assistant's replies are fixed templates, so LLM text does not reach patients,
# and this catches anything that ever would.

_CONDITIONS = (
    r"pneumonia|stroke|heart\s+attack|cancer|tumou?r|hypertension|migraine|diabetes|asthma|"
    r"appendicitis|flu|influenza|covid(-19)?|dengue|typhoid|chikungunya|malaria|tuberculosis|"
    r"infection|gastritis|ulcer|anemia|anaemia|depression|anxiety|bronchitis|sinusitis|arthritis|"
    r"meningitis|gerd|reflux|viral\s+fever|uti|jaundice|hepatitis|kidney\s+stones?"
)
_DRUGS = (
    r"amoxicillin|paracetamol|acetaminophen|ibuprofen|antibiotics?|ciprofloxacin|azithromycin|"
    r"metronidazole|omeprazole|aspirin|napa|ace|seclo|ceftriaxone|antacids?|painkillers?|"
    r"antihistamines?|insulin|ors|saline"
)
_DOSAGE_FORMS = r"tablets?|pills?|capsules?|syrup|cream|ointment|spray|drops?|injection"
_BN_CONDITIONS = "ডায়াবেটিস|ক্যান্সার|নিউমোনিয়া|ডেঙ্গু|টাইফয়েড|জন্ডিস|হার্ট\\s*অ্যাটাক|স্ট্রোক|মাইগ্রেন|সংক্রমণ|গ্যাস্ট্রিক"
_BN_DRUGS = "নাপা|প্যারাসিটামল|এন্টিবায়োটিক|অ্যান্টিবায়োটিক|সেকলো|ওষুধ|ঔষধ|ট্যাবলেট|ক্যাপসুল|সিরাপ"

DIAGNOSIS_PATTERNS = [
    re.compile(
        r"\b(you|your|it|it's|this|that|these|those|symptoms?)\b.{0,40}"
        r"\b(have|has|had|got|is|are|be|seems?|looks?|sounds?|suggests?|indicates?|"
        r"consistent\s+with|points?\s+to|caused\s+by|due\s+to|means?|suffering\s+from)\b.{0,30}"
        rf"\b({_CONDITIONS})\b",
        re.IGNORECASE,
    ),
    re.compile(rf"\b(looks?|sounds?|seems?)\s+like\b.{{0,30}}\b({_CONDITIONS})\b", re.IGNORECASE),
    re.compile(
        rf"\b(probably|likely|possibly|maybe|perhaps)\b.{{0,25}}\b({_CONDITIONS})\b", re.IGNORECASE
    ),
    re.compile(r"\bi\s+think\s+(it'?s|you|this)\b", re.IGNORECASE),
    re.compile(r"\b(i\s+diagnose\s+you|diagnosis\s*:|this\s+is\s+(definitely\s+)?a\s+case\s+of)\b", re.IGNORECASE),
    re.compile(rf"আপনার.*({_BN_CONDITIONS}).*(আছে|হয়েছে|হতে\s*পারে)"),
    re.compile(r"\bapnar\s+\w+\s+(hoyeche|hoise|ache|hote\s+pare)\b", re.IGNORECASE),
]

REASSURANCE_PATTERNS = [
    re.compile(
        r"\b(you'?ll|you\s+will|you\s+should)\s+be\s+(fine|ok|okay|alright)\b|"
        r"\b(nothing|not\s+anything)\s+(serious|to\s+worry|to\s+be\s+(worried|concerned))|"
        r"\b(do\s+not|don't|no\s+need\s+to)\s+worry\b|"
        r"\b(no|not|don't|do\s+not)\s+(need|have)\s+(to|for)\s+(see|visit|a\s+doctor|go)|"
        r"\b(harmless|not\s+(serious|dangerous))\b|"
        r"\b(go\s+away|clear\s+up|pass|resolve|get\s+better)\s+(on\s+its\s+own|by\s+itself|soon)\b|"
        r"\bshould\s+(go\s+away|clear|pass|resolve)\b",
        re.IGNORECASE,
    ),
    re.compile("চিন্তা[র]?\\s*(?:কিছু\\s*)?(?:নেই|করবেন\\s*না)|ভয়ের\\s*কিছু|এমনিতেই\\s*ঠিক"),
    re.compile(r"\bchinta[r]?\s*(kichu\s*)?(nai|nei|korben\s*na|koren\s*na)\b", re.IGNORECASE),
]

PRESCRIPTION_PATTERNS = [
    re.compile(r"\b\d+\s*(mg|ml|mcg|tablets?|pills?|capsules?)\b", re.IGNORECASE),
    re.compile(r"\b(i\s+prescribe|prescription\s*:|prescribing\s+you)\b", re.IGNORECASE),
    re.compile(
        rf"\b(take|try|use|using|taking|apply|drink|start|have)\b.{{0,30}}\b({_DRUGS}|{_DOSAGE_FORMS})\b",
        re.IGNORECASE,
    ),
    # A capitalized word straight after "Take" or "Try" is how an unlisted brand name appears
    re.compile(r"\b[Tt](ake|ry)\s+[A-Z][a-z]{3,}\b"),
    re.compile(rf"\bcourse\s+of\s+({_DRUGS})\b", re.IGNORECASE),
    re.compile(r"\b(dosage\s*:|every\s+\d+\s+hours|twice\s+(a\s+)?(day|daily)|\d+\s+times\s+a\s+day)\b", re.IGNORECASE),
    re.compile(rf"({_BN_DRUGS})\s*(টি\s*)?(খান|খাবেন|নিন|সেবন)"),
    re.compile(r"\d+\s*(মিগ্রা|ট্যাবলেট|ক্যাপসুল)"),
    re.compile(rf"\b({_DRUGS}|oshudh?|tablet|capsule)\s+(khan|khaben|nin)\b", re.IGNORECASE),
]

SAFE_FALLBACK_DISCLAIMER = (
    "As an AI assistant, I cannot diagnose medical conditions or prescribe medications. "
    "Please consult a qualified doctor for professional diagnosis and clinical treatment."
)


def output_guard(text: str) -> str:
    """Replaces any reply that diagnoses, prescribes or reassures with safe advisory text."""
    if not text:
        return text

    normalized = _normalize(text)

    for pat in DIAGNOSIS_PATTERNS:
        if pat.search(normalized):
            logger.warning("[OUTPUT GUARD] Blocked diagnostic language")
            return (
                f"I cannot provide a medical diagnosis for your symptoms. "
                f"{SAFE_FALLBACK_DISCLAIMER} I can, however, help you find a suitable doctor."
            )

    for pat in REASSURANCE_PATTERNS:
        if pat.search(normalized):
            logger.warning("[OUTPUT GUARD] Blocked reassurance")
            return (
                f"I cannot tell you whether your symptoms are serious. "
                f"{SAFE_FALLBACK_DISCLAIMER} I can, however, help you find a suitable doctor."
            )

    for pat in PRESCRIPTION_PATTERNS:
        if pat.search(normalized):
            logger.warning("[OUTPUT GUARD] Blocked prescription language")
            return (
                f"I cannot prescribe medications or dosage instructions. "
                f"{SAFE_FALLBACK_DISCLAIMER} Would you like help finding a licensed physician?"
            )

    return text
