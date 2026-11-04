"""Privacy and PII Redaction Module.

Strips personally identifiable information (phone numbers, email addresses, ID numbers, street
addresses and personal names) from patient text before sending to external LLM or embedding
providers. Names cannot be found perfectly by rules, so this reduces exposure rather than ending it,
and clinical detail is kept where the two conflict.
"""

import re

# Email regex
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    re.IGNORECASE,
)

# Phone regex (Bangladeshi and international formats). \d also matches Bangla digits.
# Examples: +8801712345678, 01712345678, 017 1234 5678, +1-555-123-4567, 01812-345678
PHONE_REGEX = re.compile(
    r"(?<!\d)(?:\+?880[\s-]?)?0?1[3-9]\d{2}[\s-]?\d{6}(?!\d)|"
    r"(?<!\d)0?1[3-9][\s-]?\d{4}[\s-]?\d{4}(?!\d)|"
    r"(?<!\d)(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}(?!\d)",
)

# National ID and similar long numbers
ID_NUMBER_REGEX = re.compile(r"(?<!\d)\d{10,17}(?!\d)")

# Street-level address fragments. The area or city stays, since it decides which doctor is near.
ADDRESS_REGEX = re.compile(
    r"\b(?:house|flat|road|holding|sector|block|apartment|apt)\s*(?:no\.?|number|#)?\s*\d+[a-z]?\b"
    r"(?:\s*[,/]\s*(?:house|flat|road|holding|sector|block)\s*(?:no\.?|number|#)?\s*\d+[a-z]?\b)*",
    re.IGNORECASE,
)

# Words that follow "I'm" without being a name
NOT_A_NAME = (
    "sick|ill|tired|fine|okay|ok|dizzy|unwell|better|worse|pregnant|diabetic|weak|sad|scared|"
    "worried|alone|here|feeling|having|not|very|so|in|at|from|looking|trying|a|an|the|old|young"
)

# Self-identifying introduction name patterns (English, Bangla, Banglish).
# The word after "I am" must be capitalized: without that, "I am feeling dizzy" reads as a
# name and the symptom is lost. "My name is" is explicit, so any casing counts as a name.
NAME_INTRO_PATTERNS = [
    re.compile(r"\b((?i:my\s+name\s+is))\s+([A-Za-z]+(?:\s+[A-Z][a-z]+)?)"),
    re.compile(r"\b((?i:i\s+am|i['’]m|this\s+is|call\s+me))\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)"),
    # Lower case is only a name when it stands alone, as in "i'm rahim, fever for 2 days"
    re.compile(rf"\b((?i:i\s+am|i['’]m))\s+(?!(?i:{NOT_A_NAME})\b)([a-z]+)(?=\s*[,.]|\s*$)"),
    re.compile(
        r"\b((?i:my\s+(?:wife|husband|son|daughter|mother|father|mum|mom|dad|brother|sister|"
        r"friend|baby|child)))\s+([A-Z][a-z]+)"
    ),
    re.compile(r"\b(amar\s+naam|amar\s+nam)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", re.IGNORECASE),
    re.compile(r"(আমার\s*নাম)\s+([ঀ-৿]+(?:\s+[ঀ-৿]+)?)"),
    re.compile(r"(আমি)\s+([ঀ-৿]+)(?=\s*[,।])"),
]

# "Rahim here." opening a message
SIGN_ON_NAME = re.compile(r"^\s*[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s+(?=here\b)")


def redact_pii(text: str) -> str:
    """Redacts emails, phones, ID numbers, street addresses and self-identifying names."""
    if not text:
        return ""

    redacted = EMAIL_REGEX.sub("[EMAIL REDACTED]", text)
    redacted = PHONE_REGEX.sub("[PHONE REDACTED]", redacted)
    redacted = ID_NUMBER_REGEX.sub("[ID REDACTED]", redacted)
    redacted = ADDRESS_REGEX.sub("[ADDRESS REDACTED]", redacted)

    for pattern in NAME_INTRO_PATTERNS:
        redacted = pattern.sub(lambda m: f"{m.group(1)} [NAME REDACTED]", redacted)
    redacted = SIGN_ON_NAME.sub("[NAME REDACTED] ", redacted)

    return redacted
