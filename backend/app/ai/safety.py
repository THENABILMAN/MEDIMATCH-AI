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
