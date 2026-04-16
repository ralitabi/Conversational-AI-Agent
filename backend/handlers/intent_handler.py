from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.chat_config import (
    INTENT_GROUPS,
    INTENT_LABELS,
    LOW_CONFIDENCE_THRESHOLD,
    MID_CONFIDENCE_THRESHOLD,
)
from backend.chat_helpers import normalize_text
from backend.handlers.intent_keyword_matcher import keyword_intent_override
from backend.utils.response_builder import build_response


class IntentHandler:
    def __init__(self, classifier) -> None:
        self.classifier = classifier

    # -------------------------------------------------------------------------
    # Labels and options
    # -------------------------------------------------------------------------

    def get_intent_label(self, intent_name: Optional[str]) -> str:
        if not intent_name:
            return "this request"
        return INTENT_LABELS.get(intent_name, intent_name.replace("_", " "))

    def is_intent_allowed_for_service(
        self,
        intent_name: Optional[str],
        service_key: Optional[str],
    ) -> bool:
        if not intent_name or not service_key:
            return False
        return intent_name in INTENT_GROUPS.get(service_key, [])

    def show_intent_options_for_service(
        self,
        service_key: str,
        excluded_intent: Optional[str] = None,
    ) -> str:
        intents = INTENT_GROUPS.get(service_key, [])
        choices = [intent for intent in intents if intent != excluded_intent]

        if not choices:
            return "Please rephrase your query."

        excluded_label = self.get_intent_label(excluded_intent)
        option_labels = ", ".join(
            self.get_intent_label(intent_name) for intent_name in choices
        )

        return (
            f"If your query is not about {excluded_label}, is it about one of these? "
            f"{option_labels}. Please type the option name that matches your query."
        )

    def resolve_intent_label_choice(
        self,
        user_input: str,
        service_key: str,
        excluded_intent: Optional[str] = None,
    ) -> Optional[str]:
        normalized_input = normalize_text(user_input)

        for intent_name in INTENT_GROUPS.get(service_key, []):
            if intent_name == excluded_intent:
                continue

            normalized_label = normalize_text(self.get_intent_label(intent_name))
            normalized_name = normalize_text(intent_name)

            if normalized_input == normalized_label or normalized_input == normalized_name:
                return intent_name

        return None

    # -------------------------------------------------------------------------
    # Phrase helpers
    # -------------------------------------------------------------------------

    def _contains_any_phrase(self, text: str, phrases: List[str]) -> bool:
        return any(phrase in text for phrase in phrases)

    def _is_yes(self, text: str) -> bool:
        return normalize_text(text) in {"yes", "y", "yeah", "yep", "correct", "ok", "okay"}

    def _is_no(self, text: str) -> bool:
        return normalize_text(text) in {"no", "n", "nope", "not really"}

    def _is_short_followup(self, text: str) -> bool:
        normalized = normalize_text(text)
        return normalized in {
            "yes",
            "y",
            "yeah",
            "yep",
            "correct",
            "ok",
            "okay",
            "no",
            "n",
            "nope",
            "not really",
        }

    def _has_active_flow(self, session: Dict[str, Any]) -> bool:
        pending_action = session.get("pending_action")
        pending_intent = session.get("pending_intent")
        awaiting_confirmation = session.get("awaiting_intent_confirmation")
        return bool(pending_action or pending_intent or awaiting_confirmation)

    # -------------------------------------------------------------------------
    # Bin-specific routing safeguards
    # -------------------------------------------------------------------------

    def _is_live_bin_lookup_query(self, text: str) -> bool:
        normalized = normalize_text(text)

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
            "not collected",
            "not emptied",
            "my bin was missed",
            "my bin was not collected",
        ]

        if self._contains_any_phrase(normalized, info_blockers):
            return False

        if self._contains_any_phrase(normalized, missed_bin_blockers):
            return False

        return self._contains_any_phrase(normalized, strong_live_phrases)

    # -------------------------------------------------------------------------
    # Council tax routing safeguards
    # -------------------------------------------------------------------------

    def _is_live_council_tax_lookup_query(self, text: str) -> bool:
        normalized = normalize_text(text)

        live_lookup_phrases = [
            "find my council tax band",
            "check my council tax band",
            "what is my council tax band",
            "what band is my house",
            "what band is my property",
            "check my council tax balance",
            "my council tax balance",
            "how much do i owe",
            "outstanding council tax",
            "amount due",
            "balance due",
            "pay my council tax",
            "pay council tax",
            "make a council tax payment",
            "pay my bill",
        ]

        info_blockers = [
            "how can i pay",
            "payment methods",
            "ways to pay",
            "what is council tax",
            "how council tax works",
            "discounts",
            "exemptions",
            "reduction",
            "single person discount",
            "appeal",
            "challenge my band",
            "wrong band",
            "arrears help",
            "struggling to pay",
            "missed payment",
        ]

        if self._contains_any_phrase(normalized, info_blockers):
            return False

        return self._contains_any_phrase(normalized, live_lookup_phrases)

    # -------------------------------------------------------------------------
    # Keyword overrides
    # -------------------------------------------------------------------------

    def _keyword_intent_override(
        self,
        service_key: str,
        text: str,
    ) -> Optional[str]:
        return keyword_intent_override(service_key, text)

    # -------------------------------------------------------------------------
    # Classifier helpers
    # -------------------------------------------------------------------------

    def _safe_classify(
        self,
        text: str,
        selected_service: Optional[str],
    ) -> Dict[str, Any]:
        try:
            result = self.classifier.classify(text, selected_service=selected_service)
            if isinstance(result, dict):
                return result
        except Exception:
            pass

        return {
            "intent": None,
            "confidence": 0.0,
            "candidates": [],
            "needs_live_lookup": False,
            "service": selected_service,
        }

    def _filter_candidates_for_service(
        self,
        candidates: List[Dict[str, Any]],
        service_key: Optional[str],
    ) -> List[Dict[str, Any]]:
        if not service_key:
            return candidates

        filtered: List[Dict[str, Any]] = []
        for candidate in candidates:
            intent_name = candidate.get("intent")
            if self.is_intent_allowed_for_service(intent_name, service_key):
                filtered.append(candidate)

        return filtered

    def _intent_needs_live_lookup(
        self,
        service_key: Optional[str],
        intent_name: Optional[str],
        classifier_flag: bool = False,
    ) -> bool:
        if classifier_flag:
            return True

        if service_key == "bin_collection":
            return intent_name == "check_bin_collection_dates"

        if service_key == "council_tax":
            return intent_name in {
                "find_council_tax_band",
                "check_council_tax_balance",
                "council_tax_payment",
            }

        return False

    # -------------------------------------------------------------------------
    # Flow-aware shortcuts
    # -------------------------------------------------------------------------

    def _handle_active_flow_short_reply(
        self,
        service_key: str,
        text: str,
        session: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Prevent yes/no from being reclassified while a step-based flow is active.
        The chat engine / main router should handle the actual next step.
        """
        normalized = normalize_text(text)

        if not self._has_active_flow(session):
            return None

        pending_intent = session.get("pending_intent")
        awaiting_confirmation = session.get("awaiting_intent_confirmation")

        if self._is_short_followup(normalized):
            return {
                "type": "flow_reply",
                "intent": pending_intent,
                "reply_text": normalized,
                "message": build_response(
                    session=session,
                    reply=normalized,
                    response_type="flow_reply",
                    data={
                        "service_key": service_key,
                        "pending_action": session.get("pending_action"),
                        "pending_intent": pending_intent,
                        "awaiting_intent_confirmation": awaiting_confirmation,
                    },
                ),
                "candidates": [],
                "needs_live_lookup": False,
            }

        return None

    # -------------------------------------------------------------------------
    # Public intent detection API
    # -------------------------------------------------------------------------

    def detect_intent(
        self,
        service_key: str,
        text: str,
        session: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Return structure:
        - type: direct | confirm | clarify | flow_reply
        - intent
        - message
        - candidates
        - needs_live_lookup
        """
        session = session or {}

        session_id = session.get("session_id")
        if session_id and hasattr(self.classifier, "session_manager"):
            try:
                self.classifier.session_manager.update_task(session_id, service=service_key)
            except Exception:
                pass

        # -------------------------------------------------------------
        # If a step-based flow is already active, do not reclassify
        # very short replies like yes/no.
        # -------------------------------------------------------------
        flow_result = self._handle_active_flow_short_reply(
            service_key=service_key,
            text=text,
            session=session,
        )
        if flow_result:
            return flow_result

        override_intent = self._keyword_intent_override(service_key, text)
        if override_intent:
            return {
                "type": "direct",
                "intent": override_intent,
                "candidates": [],
                "needs_live_lookup": self._intent_needs_live_lookup(
                    service_key,
                    override_intent,
                    classifier_flag=False,
                ),
            }

        result = self._safe_classify(text, selected_service=service_key)

        predicted_intent = result.get("intent")
        confidence = float(result.get("confidence", 0.0))
        candidates = result.get("candidates", []) or []

        allowed_candidates = self._filter_candidates_for_service(candidates, service_key)
        wrong_domain = not self.is_intent_allowed_for_service(predicted_intent, service_key)

        if allowed_candidates and predicted_intent is None:
            predicted_intent = allowed_candidates[0].get("intent")
            confidence = float(allowed_candidates[0].get("confidence", 0.0))
            wrong_domain = not self.is_intent_allowed_for_service(predicted_intent, service_key)

        if predicted_intent is None:
            message = build_response(
                session=session,
                reply="I’m not sure what you need help with. Please rephrase your question.",
                response_type="intent_unclear",
            )
            return {
                "type": "clarify",
                "intent": None,
                "message": message,
                "candidates": allowed_candidates[:3],
                "needs_live_lookup": False,
            }

        if wrong_domain:
            option_text = self.show_intent_options_for_service(
                service_key,
                excluded_intent=predicted_intent,
            )
            message = build_response(
                session=session,
                reply=option_text,
                response_type="intent_clarification",
                data={
                    "predicted_intent": predicted_intent,
                    "candidates": allowed_candidates[:3],
                },
            )
            return {
                "type": "clarify",
                "intent": predicted_intent,
                "message": message,
                "candidates": allowed_candidates[:3],
                "needs_live_lookup": False,
            }

        if confidence < LOW_CONFIDENCE_THRESHOLD:
            label = self.get_intent_label(predicted_intent)
            message = build_response(
                session=session,
                reply=f"Is your query about {label}? Please reply yes or no.",
                response_type="intent_confirmation",
                data={
                    "predicted_intent": predicted_intent,
                    "confidence": confidence,
                    "candidates": allowed_candidates[:3],
                },
            )
            return {
                "type": "confirm",
                "intent": predicted_intent,
                "message": message,
                "candidates": allowed_candidates[:3],
                "needs_live_lookup": self._intent_needs_live_lookup(
                    service_key,
                    predicted_intent,
                    classifier_flag=bool(result.get("needs_live_lookup", False)),
                ),
            }

        if LOW_CONFIDENCE_THRESHOLD <= confidence < MID_CONFIDENCE_THRESHOLD:
            label = self.get_intent_label(predicted_intent)
            message = build_response(
                session=session,
                reply=f"I think your query is about {label}. Shall I continue? Please reply yes or no.",
                response_type="intent_confirmation",
                data={
                    "predicted_intent": predicted_intent,
                    "confidence": confidence,
                    "candidates": allowed_candidates[:3],
                },
            )
            return {
                "type": "confirm",
                "intent": predicted_intent,
                "message": message,
                "candidates": allowed_candidates[:3],
                "needs_live_lookup": self._intent_needs_live_lookup(
                    service_key,
                    predicted_intent,
                    classifier_flag=bool(result.get("needs_live_lookup", False)),
                ),
            }

        return {
            "type": "direct",
            "intent": predicted_intent,
            "candidates": allowed_candidates[:3],
            "needs_live_lookup": self._intent_needs_live_lookup(
                service_key,
                predicted_intent,
                classifier_flag=bool(result.get("needs_live_lookup", False)),
            ),
        }