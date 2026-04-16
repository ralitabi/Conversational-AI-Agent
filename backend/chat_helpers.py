from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from backend.chat_config import (
    FLOW_INTENTS,
    INTENT_ALIASES,
    INTENT_GROUPS,
    INTENT_LABELS,
    SERVICE_OPTIONS,
)
LIVE_BIN_INTENT = "check_bin_collection_dates"
LIVE_COUNCIL_TAX_INTENTS = {
    "find_council_tax_band",
    "check_council_tax_balance",
    "council_tax_payment",
}


def get_time_greeting() -> str:
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning"
    if hour < 18:
        return "Good afternoon"
    return "Good evening"


def normalize_text(value: str) -> str:
    return " ".join(value.strip().lower().split())


def build_main_menu_text() -> str:
    return (
        "Please choose a service area by typing its name: "
        "Bin collection, Blue Badge, Contact services, Council tax, "
        "Library services, Planning applications, School admissions, "
        "Benefits support, Something else."
    )


def resolve_service_choice(user_input: str) -> tuple[str, str] | None:
    return SERVICE_OPTIONS.get(normalize_text(user_input))


def normalize_intent(intent_name: str | None) -> str | None:
    if not intent_name:
        return None
    return INTENT_ALIASES.get(intent_name, intent_name)


def get_intent_label(intent_name: str | None) -> str:
    if not intent_name:
        return "this request"
    return INTENT_LABELS.get(intent_name, intent_name.replace("_", " "))


def is_intent_allowed_for_service(predicted_intent: str | None, service_key: str) -> bool:
    if not predicted_intent:
        return False

    allowed = INTENT_GROUPS.get(service_key, [])
    if not allowed:
        return True

    return predicted_intent in allowed


def _contains_any_phrase(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


# -------------------------------------------------------------------------
# Bin collection helpers
# -------------------------------------------------------------------------

def _is_strong_live_bin_lookup_query(text: str) -> bool:
    """
    Only strong collection-date style phrases should trigger the live bin flow.
    Informational bin/recycling questions must not trigger postcode lookup.
    """
    strong_live_phrases = [
        "next bin",
        "next collection",
        "collection date",
        "collection dates",
        "bin collection date",
        "bin collection dates",
        "next bin collection",
        "next bin collection date",
        "when is my bin",
        "when is my next bin",
        "when is the next collection",
        "when is the next bin collection",
        "check my bin collection",
        "find my collection date",
        "find my next collection",
        "pickup date",
        "next pickup",
    ]

    info_blockers = [
        "what can i put",
        "what goes in",
        "what goes into",
        "which bin",
        "what bin",
        "can i recycle",
        "recycling rules",
        "bin guidance",
        "where do i put",
        "what can go in",
        "what belongs in",
    ]

    missed_bin_blockers = [
        "missed bin",
        "missed collection",
        "bin not collected",
        "bins not collected",
        "not collected",
        "not emptied",
        "my bin was missed",
        "my bin was not collected",
    ]

    assisted_blockers = [
        "assisted collection",
        "assisted bin collection",
        "help moving bin",
        "cannot move my bin",
        "can't move my bin",
        "need help with bin",
        "medical condition",
        "mobility issue",
        "disability",
    ]

    if _contains_any_phrase(text, info_blockers):
        return False

    if _contains_any_phrase(text, missed_bin_blockers):
        return False

    if _contains_any_phrase(text, assisted_blockers):
        return False

    return _contains_any_phrase(text, strong_live_phrases)


# -------------------------------------------------------------------------
# Council tax helpers
# -------------------------------------------------------------------------

def _is_strong_live_council_tax_lookup_query(text: str) -> bool:
    """
    Only strong property/account-specific council tax queries should trigger
    live lookup style handling. General guidance should remain in dialogue/RAG.
    """
    strong_live_phrases = [
        "find my council tax band",
        "check my council tax band",
        "what is my council tax band",
        "what band is my house",
        "what band is my property",
        "council tax band",
        "check my council tax balance",
        "my council tax balance",
        "how much do i owe",
        "outstanding council tax",
        "amount due",
        "balance due",
        "check my bill",
        "pay my council tax",
        "pay council tax",
        "make a council tax payment",
        "pay my bill",
        "council tax payment",
        "pay now",
    ]

    info_blockers = [
        "how can i pay",
        "payment methods",
        "ways to pay",
        "what is council tax",
        "how council tax works",
        "discounts",
        "exemptions",
        "council tax reduction",
        "single person discount",
        "live alone discount",
        "appeal council tax",
        "challenge my band",
        "wrong band",
        "arrears help",
        "struggling to pay",
        "missed payment",
        "moving house",
        "moved house",
        "report a move",
        "change my details",
        "change name on council tax",
    ]

    if _contains_any_phrase(text, info_blockers):
        return False

    return _contains_any_phrase(text, strong_live_phrases)


def is_live_lookup_intent(intent_name: str | None) -> bool:
    intent_name = normalize_intent(intent_name)

    if not intent_name:
        return False

    if intent_name == LIVE_BIN_INTENT:
        return True

    if intent_name in LIVE_COUNCIL_TAX_INTENTS:
        return True

    return False


def extract_step_id(payload: dict[str, Any]) -> str | None:
    return (
        payload.get("current_step_id")
        or payload.get("step_id")
        or payload.get("next_step_id")
        or payload.get("current_step")
    )


def should_use_dialogue_flow(
    intent_name: Optional[str],
    service_key: str | None = None,
) -> bool:
    intent_name = normalize_intent(intent_name)

    if not intent_name:
        return False

    if is_live_lookup_intent(intent_name):
        return False

    if intent_name in FLOW_INTENTS:
        return True

    return False