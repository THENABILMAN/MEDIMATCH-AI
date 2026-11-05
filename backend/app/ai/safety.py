"""Safety Module for MediMatch AI.

Provides:
1. Rule-based emergency detection in English, Bangla, and transliterated Bangla (Banglish)
   using externalized patterns from emergency_patterns.json.
2. Fixed, non-LLM responses to physical emergencies and to self-harm risk. No model writes these.
3. Output guard inspecting assistant replies to catch diagnosis, treatment, reassurance and any
   claim to be human or to have feelings.

Crucial Rule: Patient text is NEVER logged here, not even the matched phrase.
"""

import json
import logging
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal, NamedTuple

import yaml

from app.core.config import settings

logger = logging.getLogger("medimatch.ai.safety")

PATTERNS_FILE = Path(__file__).resolve().parent / "data" / "emergency_patterns.json"
MESSAGES_FILE = Path(__file__).resolve().parent / "prompts" / "safety_messages.yaml"

EmergencyKind = Literal["physical", "self_harm"]
SELF_HARM_CATEGORY = "psychiatric_self_harm"

_ZERO_WIDTH = re.compile("[​‌‍⁠﻿]")
_WHITESPACE = re.compile(r"\s+")
_CLAUSE_BREAK = re.compile(
    r"[.,;:!?\n]|\bbut\b|\band\b|\bthough\b|\bকিন্তু\b|\bkintu\b", re.IGNORECASE
)


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


class CombinationRule(NamedTuple):
    """Every group must match somewhere in the message, in any order."""

    category: str
    groups: list[re.Pattern]
    negatable: bool


class Triage(NamedTuple):
    rules: list[EmergencyRule]
    combinations: list[CombinationRule]
    negated_before: re.Pattern
    negated_after: re.Pattern


def _compile(pattern: str) -> re.Pattern:
    return re.compile(_normalize(pattern), re.IGNORECASE | re.UNICODE)


def _load_patterns(path: Path = PATTERNS_FILE) -> Triage:
    """Compiles emergency patterns, failing loudly so triage can never start switched off."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    rules: list[EmergencyRule] = []
    combinations: list[CombinationRule] = []
    for cat in data.get("categories", []):
        cat_name = cat.get("name", "general_emergency")
        negatable = bool(cat.get("negatable", False))
        for pat in cat.get("patterns", []):
            rules.append(EmergencyRule(cat_name, _compile(pat), negatable))
        for groups in cat.get("combinations", []):
            combinations.append(CombinationRule(cat_name, [_compile(g) for g in groups], negatable))

    if not rules:
        raise RuntimeError(f"No emergency patterns loaded from {path}")

    negation = data.get("negation", {})
    return Triage(
        rules,
        combinations,
        _compile(negation.get("before", "(?!)")),
        _compile(negation.get("after", "(?!)")),
    )


# Load and compile patterns at import time
_TRIAGE = _load_patterns()


def _is_negated(text: str, match: re.Match) -> bool:
    """True for a plain negation in the same clause, such as "no chest pain"."""
    clause = _CLAUSE_BREAK.split(text[: match.start()])[-1]
    return bool(
        _TRIAGE.negated_before.search(clause) or _TRIAGE.negated_after.match(text[match.end() :])
    )


def _combination_matches(rule: CombinationRule, text: str) -> str | None:
    """Returns the first group's matched text if every group has a match that is not negated."""
    found: str | None = None
    for group in rule.groups:
        matches = [m for m in group.finditer(text) if not (rule.negatable and _is_negated(text, m))]
        if not matches:
            return None
        found = found or matches[0].group(0)
    return found


def check_emergency(text: str) -> tuple[bool, str | None, str | None]:
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

    for combination in _TRIAGE.combinations:
        found = _combination_matches(combination, normalized)
        if found:
            logger.warning(
                f"[SAFETY ESCALATION] Emergency detected in category '{combination.category}'"
            )
            return True, combination.category, found

    return False, None, None


def _load_messages(path: Path = MESSAGES_FILE) -> dict[str, Any]:
    """Loads the fixed messages, failing loudly so an alert can never be missing at runtime."""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


_MESSAGES = _load_messages()


def emergency_kind(category: str | None) -> EmergencyKind:
    """Which fixed response a rule category gets. Anything not self-harm is physical."""
    return "self_harm" if category == SELF_HARM_CATEGORY else "physical"


def has_bangla_script(text: str) -> bool:
    return any("\u0980" <= ch <= "\u09ff" for ch in text)


def get_emergency_response() -> str:
    """Returns the fixed, non-LLM alert for a physical emergency, in English and Bangla."""
    return _MESSAGES["physical"].replace("{number}", settings.EMERGENCY_NUMBER)


def _helpline_lines() -> str:
    return "\n".join(
        f"{line.name}: {line.number}" + (f" ({line.hours})" if line.hours else "")
        for line in settings.CRISIS_HELPLINES
    )


def _fill_crisis(template: str) -> str:
    helplines = _helpline_lines()
    filled = template.replace("{number}", settings.EMERGENCY_NUMBER)
    if not helplines:
        return filled.replace("\n{helplines}", "")
    return filled.replace("{helplines}", helplines)


def get_crisis_response(patient_text: str, repeat: bool = False) -> str:
    """Returns the fixed, non-LLM message for self-harm risk.

    Bangla script gets Bangla. Everything else gets English then Bangla, because Latin letters
    cannot reliably separate English from Banglish and this message must always be understood.
    """
    messages = _MESSAGES["crisis_repeat" if repeat else "crisis"]
    if has_bangla_script(patient_text):
        return _fill_crisis(messages["bn"])
    return f"{_fill_crisis(messages['en'])}\n\n{_fill_crisis(messages['bn'])}"


# ------------------------------------------------------------------------------
# Output Guard (Anti-Diagnosis, Anti-Prescription, Anti-Reassurance)
# ------------------------------------------------------------------------------
# The last check on model text. It is known to be incomplete, so the persona prompt carries the same
# rules. A reply that fails gets one rewrite, then a short fixed reply in the patient's language.

_CONDITIONS = (
    r"pneumonia|stroke|heart\s+attack|cancer|tumou?r|hypertension|migraine|diabetes|asthma|"
    r"appendicitis|flu|influenza|covid(-19)?|dengue|typhoid|chikungunya|malaria|tuberculosis|"
    r"infection|gastritis|ulcer|anemia|anaemia|depression|anxiety|bronchitis|sinusitis|arthritis|"
    r"meningitis|gerd|reflux|viral\s+fever|uti|jaundice|hepatitis|kidney\s+stones?|"
    r"panic\s+(attacks?|disorder)|bipolar|schizophrenia|ptsd|insomnia|ocd"
)
_DRUGS = (
    r"amoxicillin|paracetamol|acetaminophen|ibuprofen|antibiotics?|ciprofloxacin|azithromycin|"
    r"metronidazole|omeprazole|aspirin|napa|ace|seclo|ceftriaxone|antacids?|painkillers?|"
    r"antihistamines?|insulin|ors|saline"
)
# Unmistakable medicine names. Ambiguous short names such as "ace" only count after "take"
_DRUG_NAMES = (
    r"amoxicillin|paracetamol|acetaminophen|ibuprofen|antibiotics?|ciprofloxacin|azithromycin|"
    r"metronidazole|omeprazole|aspirin|seclo|ceftriaxone|antacids?|painkillers?|antihistamines?|"
    r"antidepressants?|sertraline|escitalopram|fluoxetine|diazepam|alprazolam|clonazepam|"
    r"lorazepam|sleeping\s+pills?"
)
_DOSAGE_FORMS = r"tablets?|pills?|capsules?|syrup|cream|ointment|spray|drops?|injection"
_BN_CONDITIONS = "ডায়াবেটিস|ক্যান্সার|নিউমোনিয়া|ডেঙ্গু|টাইফয়েড|জন্ডিস|হার্ট\\s*অ্যাটাক|স্ট্রোক|মাইগ্রেন|সংক্রমণ|গ্যাস্ট্রিক|ডিপ্রেশন|বিষণ্ণতা|বিষণ্নতা|প্যানিক\\s*অ্যাটাক"
_BN_DRUG_NAMES = "নাপা|প্যারাসিটামল|এন্টিবায়োটিক|অ্যান্টিবায়োটিক|সেকলো"
_BN_DRUGS = "নাপা|প্যারাসিটামল|এন্টিবায়োটিক|অ্যান্টিবায়োটিক|সেকলো|ওষুধ|ঔষধ|ট্যাবলেট|ক্যাপসুল|সিরাপ"

DIAGNOSIS_PATTERNS = [
    # A reply names no condition at all, in any sentence
    re.compile(rf"\b({_CONDITIONS})\b", re.IGNORECASE),
    re.compile(_BN_CONDITIONS),
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
    re.compile(
        r"\b(i\s+diagnose\s+you|diagnosis\s*:|this\s+is\s+(definitely\s+)?a\s+case\s+of)\b",
        re.IGNORECASE,
    ),
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
        r"\bshould\s+(go\s+away|clear|pass|resolve)\b|"
        r"\b(it'?ll|it\s+will|everything\s+will|everything'?ll)\s+be\s+(fine|ok|okay|alright)\b",
        re.IGNORECASE,
    ),
    re.compile("কিছু\\s*হবে\\s*না|ভালো\\s*হয়ে\\s*যাবেন|ঠিক\\s*হয়ে\\s*যাবে"),
    re.compile(r"\b(thik|valo|bhalo)\s+hoye\s+(jabe|jaben)\b", re.IGNORECASE),
    re.compile("চিন্তা[র]?\\s*(?:কিছু\\s*)?(?:নেই|করবেন\\s*না)|ভয়ের\\s*কিছু|এমনিতেই\\s*ঠিক"),
    re.compile(r"\bchinta[r]?\s*(kichu\s*)?(nai|nei|korben\s*na|koren\s*na)\b", re.IGNORECASE),
]

PRESCRIPTION_PATTERNS = [
    re.compile(rf"\b({_DRUG_NAMES})\b", re.IGNORECASE),
    re.compile(_BN_DRUG_NAMES),
    re.compile(r"\b\d+\s*(mg|ml|mcg|tablets?|pills?|capsules?)\b", re.IGNORECASE),
    re.compile(r"\b(i\s+prescribe|prescription\s*:|prescribing\s+you)\b", re.IGNORECASE),
    re.compile(
        rf"\b(take|try|use|using|taking|apply|drink|start|have)\b.{{0,30}}\b({_DRUGS}|{_DOSAGE_FORMS})\b",
        re.IGNORECASE,
    ),
    # A capitalized word straight after "Take" or "Try" is how an unlisted brand name appears
    re.compile(r"\b[Tt](ake|ry)\s+[A-Z][a-z]{3,}\b"),
    re.compile(rf"\bcourse\s+of\s+({_DRUGS})\b", re.IGNORECASE),
    re.compile(
        r"\b(dosage\s*:|every\s+\d+\s+hours|twice\s+(a\s+)?(day|daily)|\d+\s+times\s+a\s+day)\b",
        re.IGNORECASE,
    ),
    re.compile(rf"({_BN_DRUGS})\s*(টি\s*)?(খান|খাবেন|নিন|সেবন)"),
    re.compile(r"\d+\s*(মিগ্রা|ট্যাবলেট|ক্যাপসুল)"),
    re.compile(rf"\b({_DRUGS}|oshudh?|tablet|capsule)\s+(khan|khaben|nin)\b", re.IGNORECASE),
]

# Warmth comes from attention, so "I'm sorry" and "that sounds painful" pass. The assistant saying it
# has a body, a life or feelings of its own does not. "I'm not a doctor" passes too.
HUMAN_CLAIM_PATTERNS = [
    re.compile(
        r"\bi\s+(\w+\s+)?(feel|felt)\b|"
        r"\bi\s+(\w+\s+)?(know|understand)\s+(\w+\s+)?how\s+you\s+(feel|are\s+feeling)\b|"
        r"\bi('?ve|\s+have)\s+(\w+\s+)?been\s+(there|through)\b|"
        r"\bi\s+(went|go)\s+through\b|\bhappened\s+to\s+me\b|"
        r"\bas\s+a\s+(human|person|woman|man|mother|father|parent|friend|doctor|therapist)\b|"
        r"\bi(?:'?m|\s+am)\s+(a\s+|your\s+)?(real\s+)?(human|person|friend|doctor|therapist)\b|"
        r"\bi(?:'?m|\s+am)\s+(so\s+|very\s+|really\s+|deeply\s+)?"
        r"(sad|heartbroken|worried|concerned|hurt|happy|glad|moved|touched)\b|"
        r"\bmy\s+(heart|body|family|wife|husband|mother|father|own\s+experience)\b|"
        r"\bi\s+love\s+you\b|\bas\s+an\s+ai\s+language\s+model\b",
        re.IGNORECASE,
    ),
    re.compile(
        "আমি\\s*(?:\\S+\\s+){0,2}অনুভব\\s*করছি|আপনার\\s*কষ্ট\\s*আমি\\s*(?:অনুভব|টের)|আমারও\\s*(?:কষ্ট|খারাপ|এমন)|"
        "আমি\\s*(?:একজন\\s*)?মানুষ|আমি\\s*(?:একজন\\s*)?(?:ডাক্তার|থেরাপিস্ট)|আমার\\s*(?:হৃদয়|বুক|শরীর|পরিবার)|"
        "আমিও\\s*(?:একই|এমন|এই)"
    ),
    re.compile(
        r"\bami\s+(\w+\s+){0,2}onubhob\s+kor|\bamaro\s+(kosto|koshto|kharap|emon)\b|"
        r"\bami\s+(ekjon\s+)?(manush|doctor|daktar|therapist)\b|\bamio\s+(eki|emon)\b",
        re.IGNORECASE,
    ),
]

_RULES = (
    ("diagnosis", DIAGNOSIS_PATTERNS),
    ("reassurance", REASSURANCE_PATTERNS),
    ("prescription", PRESCRIPTION_PATTERNS),
    ("human_claim", HUMAN_CLAIM_PATTERNS),
)


def reply_violation(text: str) -> str | None:
    """Names the first rule a reply breaks, or None. Only the rule name is ever logged."""
    if not text:
        return None
    normalized = _normalize(text)
    for name, patterns in _RULES:
        if any(pattern.search(normalized) for pattern in patterns):
            return name
    return None


def guard_fallback(language: str = "en") -> str:
    """The fixed reply for a model reply that could not be made safe."""
    messages = _MESSAGES["guard_fallback"]
    return messages.get(language, messages["en"])


def output_guard(text: str, language: str = "en") -> str:
    """Replaces any reply that breaks a rule with the fixed safe reply."""
    violation = reply_violation(text)
    if violation is None:
        return text
    logger.warning(f"[OUTPUT GUARD] Blocked {violation}")
    return guard_fallback(language)
