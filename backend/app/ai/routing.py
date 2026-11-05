"""Decides what the assistant does next. The model reads the conversation, and Python decides.

Pure functions, so every stopping rule can be tested without a model. Nothing here writes text for
the patient.
"""

import re
from pathlib import Path
from typing import Any, NamedTuple

import yaml

from app.core.config import settings

MAP_FILE = Path(__file__).resolve().parent / "data" / "specialty_map.yaml"

# Meaning "any city" to the recommender
ANY_CITY = "Bangladesh"

CLARIFY = "clarify_meaning"
LOCATION = "location"
GENERAL_MEDICINE = "General Medicine"
PSYCHIATRY = "Psychiatry"
# A patient may need to be asked twice, but a third time would be pressure
MAX_ASKS = 2
LOWEST_SEARCH_CONFIDENCE = 0.3
MOST_SPECIALTIES_SEARCHED = 3

# Asked in this order when the model has no better suggestion
DEFAULT_GOALS = ("symptoms", "duration", "severity", "location")
EMOTIONAL_GOALS = ("symptoms", "duration", "daily_impact", "care_preference", "location")


class AmbiguousPhrase(NamedTuple):
    id: str
    meaning: str
    chest: bool
    pattern: re.Pattern


class TurnPlan(NamedTuple):
    action: str  # "ask" | "search" | "talk" | "support"
    goal: str | None = None
    reason: str | None = None
    any_city: bool = False


def _load_map(path: Path = MAP_FILE) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


_MAP = _load_map()
_PHRASES = [
    AmbiguousPhrase(
        p["id"], p["meaning"], bool(p.get("chest")), re.compile(p["pattern"], re.IGNORECASE)
    )
    for p in _MAP["ambiguous_phrases"]
]
EMOTIONAL_SPECIALTIES = {
    name for name, entry in _MAP["specialties"].items() if entry.get("emotional")
}
CHEST_PHRASE_IDS = {phrase.id for phrase in _PHRASES if phrase.chest}


def find_ambiguous_phrases(text: str) -> list[str]:
    """A backstop, so the phrases we know about are caught even if the model misses them."""
    return [phrase.id for phrase in _PHRASES if phrase.pattern.search(text)]


def phrases_prompt() -> str:
    return "\n".join(f"- {phrase.id}: {phrase.meaning}" for phrase in _PHRASES)


def specialty_guide(verified: list[str]) -> str:
    """The guide for specialties that exist in the database. Others can never be searched."""
    lines = []
    for name in verified:
        entry = _MAP["specialties"].get(name)
        if entry:
            lines.append(f"- {name}: {entry['when']}. For: {'; '.join(entry['groups'])}")
        else:
            lines.append(f"- {name}")
    return "\n".join(lines)


def ranked_specialties(confidence: dict[str, float]) -> list[tuple[str, float]]:
    return sorted(confidence.items(), key=lambda item: item[1], reverse=True)


def is_confident(confidence: dict[str, float]) -> bool:
    """True once one specialty is clearly ahead."""
    ranked = ranked_specialties(confidence)
    if not ranked:
        return False
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    return (
        ranked[0][1] >= settings.ROUTING_MIN_CONFIDENCE
        and ranked[0][1] - runner_up >= settings.ROUTING_MIN_MARGIN
    )


def is_emotional(confidence: dict[str, float]) -> bool:
    ranked = ranked_specialties(confidence)
    return bool(ranked) and ranked[0][0] in EMOTIONAL_SPECIALTIES


def specialties_to_search(
    confidence: dict[str, float],
    physical_symptoms_too: bool,
    care_preference: str | None = None,
) -> list[str]:
    """The best-scoring specialties, honouring the kind of help the patient chose.

    A general doctor joins emotional care only for physical symptoms.
    """
    ranked = ranked_specialties(confidence)
    if not ranked:
        return []
    names = [
        name
        for name, score in ranked[:MOST_SPECIALTIES_SEARCHED]
        if score >= LOWEST_SEARCH_CONFIDENCE or name == ranked[0][0]
    ]
    if ranked[0][0] not in EMOTIONAL_SPECIALTIES:
        return names
    if not physical_symptoms_too:
        names = [name for name in names if name != GENERAL_MEDICINE]
    if care_preference == "talking":
        return [name for name in names if name != PSYCHIATRY] or names
    if care_preference == "medical" and PSYCHIATRY in confidence:
        return [PSYCHIATRY] + [name for name in names if name not in EMOTIONAL_SPECIALTIES]
    return names


def open_flags(flags: dict[str, str]) -> list[str]:
    return [phrase for phrase, status in flags.items() if status == "open"]


def chest_is_possible(flags: dict[str, str]) -> bool:
    return any(phrase in CHEST_PHRASE_IDS for phrase in open_flags(flags))


def _next_goal(
    suggested: str | None, emotional: bool, asked: list[str], known: set[str]
) -> str | None:
    order = EMOTIONAL_GOALS if emotional else DEFAULT_GOALS
    for goal in ([suggested] if suggested else []) + list(order):
        # For emotional pain, how it affects daily life is the kinder form of "how severe"
        if emotional and goal == "severity":
            continue
        if goal != CLARIFY and goal not in known and goal not in asked:
            return goal
    return None


def plan_turn(
    *,
    symptoms: list[str],
    location: str | None,
    confidence: dict[str, float],
    urgency_known: bool,
    flags: dict[str, str],
    asked: list[str],
    known: set[str],
    question_count: int,
    wants_now: bool,
    suggested: str | None,
    crisis_active: bool,
) -> TurnPlan:
    """Chooses this turn's action. Each rule below is a limit the brief or the owner set."""
    unresolved = open_flags(flags)

    if crisis_active and not wants_now:
        return TurnPlan("support")

    # The patient can always leave, but only after the meaning and the city have been asked once
    if wants_now:
        if unresolved and CLARIFY not in asked:
            return TurnPlan("ask", CLARIFY)
        if not location and LOCATION not in asked:
            return TurnPlan("ask", LOCATION)
        return TurnPlan("search", reason="patient_asked", any_city=not location)

    if question_count >= settings.CONVERSATION_SOFT_QUESTION_LIMIT:
        return TurnPlan("search", reason="soft_limit", any_city=not location)

    if not symptoms:
        return TurnPlan("ask", "symptoms") if suggested == "symptoms" else TurnPlan("talk")

    if unresolved and asked.count(CLARIFY) < MAX_ASKS:
        return TurnPlan("ask", CLARIFY)

    emotional = is_emotional(confidence)
    if is_confident(confidence):
        impact_goal = "daily_impact" if emotional else "severity"
        if not urgency_known and impact_goal not in asked and impact_goal not in known:
            return TurnPlan("ask", impact_goal)
        if emotional and "care_preference" not in known and "care_preference" not in asked:
            return TurnPlan("ask", "care_preference")
        if location:
            return TurnPlan("search", reason="confident")
        suggested = LOCATION

    goal = _next_goal(suggested, emotional, asked, known)
    if goal:
        return TurnPlan("ask", goal)
    if location:
        return TurnPlan("search", reason="out_of_questions")
    if asked.count(LOCATION) < MAX_ASKS:
        return TurnPlan("ask", LOCATION)
    return TurnPlan("search", reason="out_of_questions", any_city=True)


def routing_record(
    *,
    specialties: list[str],
    confidence: dict[str, float],
    reason: str | None,
    answer_basis: list[str],
    flags: dict[str, str],
) -> dict[str, Any]:
    """Why a route was chosen, for auditing. It holds labels and numbers, never patient text."""
    ranked = ranked_specialties(confidence)
    runner_up = ranked[1][1] if len(ranked) > 1 else 0.0
    top = ranked[0][1] if ranked else 0.0
    return {
        "specialties": specialties,
        "confidence": round(top, 2),
        "margin": round(top - runner_up, 2),
        "reason": reason,
        "driven_by": sorted(set(answer_basis)),
        "explained_as": sorted(set(flags.values())),
    }
