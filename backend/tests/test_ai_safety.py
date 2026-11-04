"""Table-Driven Safety & Redaction Tests for MediMatch AI.

Verifies:
1. At least 30 emergency phrases (English, Bengali script, Banglish) trigger escalation.
2. At least 20 non-emergency phrases do not trigger escalation.
3. Output guard sanitizes diagnosis and prescription language.
4. Privacy module redacts emails, phone numbers, and names.
"""

import pytest

from app.ai.privacy import redact_pii
from app.ai.safety import _load_patterns, check_emergency, output_guard

# ------------------------------------------------------------------------------
# 1. Emergency Phrases Test Table (32 distinct test cases)
# ------------------------------------------------------------------------------

EMERGENCY_PHRASES = [
    # English Cardiovascular & Respiratory
    "I have severe chest pain and cannot breathe",
    "Crushing chest pressure radiating to my left arm",
    "Shortness of breath and gasping for air",
    "Tightness in chest and dizziness",
    "Suffocating and can't breathe at all",
    # English Neurological / Stroke
    "My mother's face is drooping and speech is slurred",
    "Sudden weakness on my left side, cannot move my arm",
    "He passed out and is unconscious",
    "Patient is having a violent seizure right now",
    "Loss of consciousness after head hit",
    # English Hemorrhage & Trauma
    "He is bleeding profusely from a deep cut",
    "Vomiting blood since morning",
    "Severe bleeding that won't stop",
    "Coughing up blood continuously",
    "Victim has a stab wound",
    # English Psychiatric & Toxic
    "I want to kill myself, I have suicidal thoughts",
    "Thinking of ending my life tonight",
    "I took an overdose of sleeping pills",
    "Child drank poison from a bottle",
    "Throat closing and swollen lips after eating nuts",
    # Bengali Script (বাংলা)
    "আমার বুকে প্রচণ্ড ব্যথা করছে",
    "বুক ব্যথা সাথে শ্বাস নিতে কষ্ট হচ্ছে",
    "হঠাৎ মুখ বেঁকে গেছে এবং কথা জড়িয়ে যাচ্ছে",
    "রোগী অজ্ঞান হয়ে পড়েছে",
    "বাচ্চার খিঁচুনি উঠেছে",
    "প্রচণ্ড রক্তপাত হচ্ছে থামছে না",
    "রক্ত বমি হচ্ছে",
    "আমি আত্মহত্যা করতে চাই",
    "বিষ খেয়েছে অবিলম্বে সাহায্য চাই",
    "গর্ভবতী এবং প্রচুর রক্তপাত হচ্ছে",
    # Transliterated Bangla (Banglish)
    "buke prochur betha ar shash nite parsi na",
    "ogyan hoye porese kotha bolte parse na",
]


@pytest.mark.parametrize("phrase", EMERGENCY_PHRASES)
def test_emergency_phrases_trigger_escalation(phrase: str):
    """Every phrase in EMERGENCY_PHRASES must be recognized as an emergency."""
    is_emergency, category, matched = check_emergency(phrase)
    assert is_emergency is True, f"Failed to detect emergency for: '{phrase}'"
    assert category is not None
    assert matched is not None


# ------------------------------------------------------------------------------
# 2. Non-Emergency Phrases Test Table (21 distinct test cases)
# ------------------------------------------------------------------------------

NON_EMERGENCY_PHRASES = [
    "I have had a mild headache since yesterday",
    "Slight runny nose and sneezing for two days",
    "Mild lower back pain from sitting at my desk",
    "Looking for a dermatologist for acne treatment",
    "Need a routine annual health checkup in Dhaka",
    "Sore throat and mild fever of 99 degrees",
    "Dry skin on my elbows during winter",
    "Feeling a little bloated after dinner",
    "Minor sprained ankle while jogging in the park",
    "Consultation fee inquiry for an eye doctor",
    "Mild dandruff and itchy scalp",
    "Looking for a cardiologist for a routine cholesterol review",
    "Cough for 3 days without fever",
    "Slight toothache when drinking cold water",
    "Need vitamin supplements recommendation",
    "I feel tired after a long work week",
    "Want to consult a neurologist about occasional tension headaches",
    "মাথা ব্যথা করছে কাল থেকে",
    "হালকা সর্দি এবং কাশি",
    "ekhon matha betha korche",
    "daktar dekhaite chai pete gas ache",
]


@pytest.mark.parametrize("phrase", NON_EMERGENCY_PHRASES)
def test_non_emergency_phrases_do_not_trigger_escalation(phrase: str):
    """Non-emergency phrases must pass through safely without triggering emergency escalation."""
    is_emergency, category, _ = check_emergency(phrase)
    assert is_emergency is False, (
        f"False positive emergency triggered on: '{phrase}' (category: {category})"
    )


# ------------------------------------------------------------------------------
# 3. Output Guard Tests (Diagnosis & Prescription Blocking)
# ------------------------------------------------------------------------------


def test_output_guard_blocks_diagnosis_claims():
    """Output guard must intercept and sanitize diagnostic claims."""
    diagnosis_output = "Based on your symptoms, you have hypertension and migraine."
    safe_output = output_guard(diagnosis_output)
    assert "cannot provide a medical diagnosis" in safe_output
    assert "hypertension" not in safe_output


def test_output_guard_blocks_prescription_claims():
    """Output guard must intercept and sanitize drug prescriptions."""
    prescription_output = "You should take 500mg amoxicillin twice daily with water."
    safe_output = output_guard(prescription_output)
    assert "cannot prescribe medications" in safe_output
    assert "amoxicillin" not in safe_output


def test_output_guard_allows_safe_advisory_text():
    """Safe, non-diagnostic text passes through unaltered."""
    safe_text = "I recommend consulting a specialist in Cardiology located in Dhaka."
    assert output_guard(safe_text) == safe_text


# ------------------------------------------------------------------------------
# 4. Privacy & PII Redaction Tests
# ------------------------------------------------------------------------------


def test_privacy_redacts_bangladeshi_and_international_phones():
    """Redaction must mask phone numbers."""
    text1 = "My phone number is 01712345678, call me."
    assert "01712345678" not in redact_pii(text1)
    assert "[PHONE REDACTED]" in redact_pii(text1)

    text2 = "Contact +8801812345678 or +1 (555) 234-5678 immediately."
    redacted2 = redact_pii(text2)
    assert "+8801812345678" not in redacted2
    assert "555" not in redacted2
    assert "[PHONE REDACTED]" in redacted2


def test_privacy_redacts_emails():
    """Redaction must mask email addresses."""
    text = "Send my medical report to john.doe@example.com or rahim@test.org."
    redacted = redact_pii(text)
    assert "john.doe@example.com" not in redacted
    assert "rahim@test.org" not in redacted
    assert "[EMAIL REDACTED]" in redacted


def test_privacy_redacts_self_identifying_names():
    """Redaction masks introductory self-identifying names."""
    text1 = "Hello, my name is John Smith and I have a headache."
    redacted1 = redact_pii(text1)
    assert "John Smith" not in redacted1
    assert "[NAME REDACTED]" in redacted1

    text2 = "আমার নাম রহিম আহমেদ, পেটে ব্যথা।"
    redacted2 = redact_pii(text2)
    assert "রহিম আহমেদ" not in redacted2
    assert "[NAME REDACTED]" in redacted2


# ------------------------------------------------------------------------------
# Regression cases
# ------------------------------------------------------------------------------

MISSED_EMERGENCIES = [
    "baby is not breathing",
    "I don't want to live anymore",
    "I don\u2019t want to live anymore",
    "pressure in my chest and left arm numb",
    "my lips are turning blue",
    "worst headache of my life",
    "sudden severe headache",
    "shash nite parchi na",
    "I can\u2019t breathe",
    "my father collapsed in the bathroom",
    "snake bite on her leg",
    "আমি আর বাঁচতে চাই না",
    "ami ar banchte chai na",
    # Same word, two Bengali encodings of the letter RA with dot below
    "কথা জড়িয়ে যাচ্ছে",
    "কথা জ\u09a1\u09bcিয়ে যাচ্ছে",
]


@pytest.mark.parametrize("phrase", MISSED_EMERGENCIES)
def test_previously_missed_emergencies_escalate(phrase: str):
    assert check_emergency(phrase)[0] is True


def test_triage_refuses_to_start_without_patterns(tmp_path):
    empty = tmp_path / "patterns.json"
    empty.write_text('{"categories": []}', encoding="utf-8")

    with pytest.raises(RuntimeError):
        _load_patterns(empty)


@pytest.mark.parametrize("path_name", ["missing.json"])
def test_triage_refuses_to_start_with_missing_file(tmp_path, path_name: str):
    with pytest.raises(FileNotFoundError):
        _load_patterns(tmp_path / path_name)


@pytest.mark.parametrize(
    "unsafe",
    [
        "You may have diabetes.",
        "You probably have a migraine",
        "It sounds like you have the flu",
        "This could be a stomach infection",
        "Try 2 Napa tablets",
        "Take 2 tablets every 6 hours",
        "You should be taking antibiotics",
        "Don't worry, it's nothing serious",
        "আপনার ডায়াবেটিস আছে",
        "দিনে দুইবার ওষুধ খান",
        "500 মিগ্রা ট্যাবলেট",
    ],
)
def test_output_guard_blocks_unsafe_replies(unsafe: str):
    assert output_guard(unsafe) != unsafe


@pytest.mark.parametrize(
    "safe",
    [
        "Hello! I can help you find a suitable doctor.",
        "Do you have a fever?",
        "How long have you had these symptoms?",
        "A neurologist can evaluate your headaches.",
        "What can MediMatch do? It helps you book verified doctors.",
    ],
)
def test_output_guard_allows_safe_replies(safe: str):
    assert output_guard(safe) == safe


@pytest.mark.parametrize(
    "text, kept",
    [
        ("I am having chest tightness for 3 days", "having chest tightness"),
        ("I am feeling dizzy and nauseous", "feeling dizzy"),
        ("this is very painful", "very painful"),
        ("I'm diabetic and pregnant", "diabetic and pregnant"),
    ],
)
def test_redaction_keeps_clinical_detail(text: str, kept: str):
    assert kept in redact_pii(text)


@pytest.mark.parametrize(
    "text, name",
    [
        ("My name is Rahim Uddin", "Rahim"),
        ("my name is rahim", "rahim"),
        ("I am Fatema Begum from Dhaka", "Fatema"),
        ("I\u2019m Karim", "Karim"),
        ("amar naam Rahim", "Rahim"),
    ],
)
def test_redaction_still_removes_names(text: str, name: str):
    redacted = redact_pii(text)
    assert name not in redacted
    assert "[NAME REDACTED]" in redacted
