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
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("medimatch.ai.safety")

PATTERNS_FILE = Path(__file__).resolve().parent / "data" / "emergency_patterns.json"

# Load and compile patterns at import time
_COMPILED_PATTERNS: List[Tuple[str, re.Pattern]] = []
_DEFAULT_EMERGENCY_NUMBER = "999"

try:
    if PATTERNS_FILE.exists():
        with open(PATTERNS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            _DEFAULT_EMERGENCY_NUMBER = data.get("emergency_number", "999")
            for cat in data.get("categories", []):
                cat_name = cat.get("name", "general_emergency")
                for pat in cat.get("patterns", []):
                    try:
                        compiled = re.compile(pat, re.IGNORECASE | re.UNICODE)
                        _COMPILED_PATTERNS.append((cat_name, compiled))
                    except re.error as err:
                        logger.error(f"Invalid regex pattern '{pat}' in {PATTERNS_FILE}: {err}")
except Exception as e:
    logger.error(f"Failed to load emergency patterns from {PATTERNS_FILE}: {e}")


def check_emergency(text: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """Inspects patient input against rule-based emergency patterns.
    
    Returns:
        (is_emergency: bool, category: str | None, matched_pattern: str | None)
    """
    if not text:
        return False, None, None

    normalized = text.strip()

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

DIAGNOSIS_PATTERNS = [
    re.compile(r"\b(you\s+(have|are\s+suffering\s+from|might\s+have)\s+(pneumonia|stroke|heart\s+attack|cancer|hypertension|migraine|diabetes|asthma|appendicitis))\b", re.IGNORECASE),
    re.compile(r"\b(i\s+diagnose\s+you|diagnosis\s*:|this\s+is\s+(definitely\s+)?a\s+case\s+of)\b", re.IGNORECASE),
    re.compile(r"\b(your\s+condition\s+is\s+harmless|nothing\s+to\s+worry\s+about)\b", re.IGNORECASE),
]

PRESCRIPTION_PATTERNS = [
    re.compile(r"\b(take\s+\d+\s*(mg|ml|tablets?|pills?))\b", re.IGNORECASE),
    re.compile(r"\b(i\s+prescribe|prescription\s*:|prescribing\s+you)\b", re.IGNORECASE),
    re.compile(r"\b(take\s+(amoxicillin|paracetamol|ibuprofen|antibiotics?|ciprofloxacin|azithromycin|metronidazole|omeprazole|aspirin|napa|ace))\b", re.IGNORECASE),
    re.compile(r"\b(start\s+taking\s+[a-z]+|dosage\s*:)\b", re.IGNORECASE),
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

    # Check for diagnosis claims
    for pat in DIAGNOSIS_PATTERNS:
        if pat.search(text):
            logger.warning("[OUTPUT GUARD] Blocked diagnostic language from LLM response")
            return (
                f"I cannot provide a medical diagnosis for your symptoms. "
                f"{SAFE_FALLBACK_DISCLAIMER} I can, however, help you find a suitable doctor."
            )

    # Check for prescription language
    for pat in PRESCRIPTION_PATTERNS:
        if pat.search(text):
            logger.warning("[OUTPUT GUARD] Blocked prescription/medication language from LLM response")
            return (
                f"I cannot prescribe medications or dosage instructions. "
                f"{SAFE_FALLBACK_DISCLAIMER} Would you like help finding a licensed physician?"
            )

    return text
