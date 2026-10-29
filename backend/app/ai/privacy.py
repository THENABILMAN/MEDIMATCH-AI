"""Privacy and PII Redaction Module.

Strips personally identifiable information (phone numbers, email addresses, and personal names)
from patient text before sending to external LLM or embedding providers.
"""

import re

# Email regex
EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
    re.IGNORECASE,
)

# Phone regex (Bangladeshi and international formats)
# Examples: +8801712345678, 01712345678, +1-555-123-4567, 01812-345678
PHONE_REGEX = re.compile(
    r"(?:\+?880[\s-]?)?01[3-9]\d{2}[\s-]?\d{6}\b|"
    r"(?:\+?\d{1,3}[\s-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}\b|"
    r"\b01[3-9]\d{8}\b",
    re.IGNORECASE,
)

# Self-identifying introduction name patterns (English, Bangla, Banglish)
NAME_INTRO_PATTERNS = [
    re.compile(r"\b(my\s+name\s+is|i\s+am|i'm|this\s+is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", re.IGNORECASE),
    re.compile(r"\b(amar\s+naam|amar\s+nam)\s+([A-Za-z]+(?:\s+[A-Za-z]+)?)", re.IGNORECASE),
    re.compile(r"(আমার\s*নাম)\s+([\u0980-\u09FF]+(?:\s+[\u0980-\u09FF]+)?)"),
]


def redact_pii(text: str) -> str:
    """Redacts emails, phone numbers, and explicit self-identifying names from text."""
    if not text:
        return ""

    # 1. Redact Emails
    redacted = EMAIL_REGEX.sub("[EMAIL REDACTED]", text)

    # 2. Redact Phone Numbers
    redacted = PHONE_REGEX.sub("[PHONE REDACTED]", redacted)

    # 3. Redact Self-Identifying Names
    for pattern in NAME_INTRO_PATTERNS:
        def replace_name(m):
            prefix = m.group(1)
            return f"{prefix} [NAME REDACTED]"
        redacted = pattern.sub(replace_name, redacted)

    return redacted
