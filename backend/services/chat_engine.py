from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from backend.chat_helpers import (
    build_main_menu_text,
    get_time_greeting,
    is_greeting,
    normalize_text,
    resolve_service_choice,
    SERVICE_OPTION_CHIPS,
)
from backend.intent_classifier import IntentClassifier
from backend.core.session_manager import SessionManager
from backend.handlers.bin_handler import BinHandler
from backend.handlers.dialogue_handler import DialogueHandler
from backend.handlers.intent_handler import IntentHandler
from backend.handlers.school_handler import SchoolHandler
from backend.handlers.library_handler import LibraryHandler
from backend.handlers.blue_badge_handler import BlueBadgeHandler
from backend.rag_service import RAGService
from backend.utils.response_builder import build_reply, build_messages_reply
from backend.utils.council_tax_formatter import format_council_tax_messages
from backend.services.bin_guidance_service import BinGuidanceService


BIN_LIVE_INTENT = "check_bin_collection_dates"
SCHOOL_FINDER_INTENT = "school_finder"

_UK_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$", re.IGNORECASE
)


def _is_uk_postcode(text: str) -> bool:
    return bool(_UK_POSTCODE_RE.match(text.strip()))
LIBRARY_FINDER_INTENT = "library_finder"
COUNCIL_TAX_LIVE_INTENTS = {
    "find_council_tax_band",
    "council_tax_payment",
}


class ChatEngine:
    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.datasets_path = self.project_root.parent / "datasets"
        self.model_path = self.project_root / "models" / "intent_classifier.joblib"
        self.bin_guidance_path = self.datasets_path / "bin_collection" / "bin_recycling_guidance.json"

        print("DEBUG ChatEngine project_root:", self.project_root)
        print("DEBUG ChatEngine datasets_path:", self.datasets_path)

        self.classifier = IntentClassifier(self.datasets_path)
        self.classifier.load(self.model_path)

        self.session_manager  = SessionManager()
        self.bin_handler      = BinHandler(self.session_manager)
        self.dialogue_handler = DialogueHandler(self.datasets_path, self.session_manager)
        self.intent_handler   = IntentHandler(self.classifier)
        self.school_handler      = SchoolHandler(self.session_manager)
        self.library_handler     = LibraryHandler(self.session_manager)
        self.blue_badge_handler  = BlueBadgeHandler(self.session_manager)
        self.rag_service         = RAGService(self.datasets_path)
        self.bin_guidance     = BinGuidanceService(
            self.bin_guidance_path
        )

    # =========================================================
    # PUBLIC
    # =========================================================
    def get_welcome_message(self) -> str:
        return (
            f"{get_time_greeting()}, please let me know how I can help you.\n\n"
            f"{build_main_menu_text()}"
        )

    def process_message(self, user_input: str, session_id: str = "default") -> dict[str, Any]:
        session = self.session_manager.get_session(session_id)
        memory = self.session_manager.get_memory(session_id)

        try:
            text = (user_input or "").strip()
            if not text:
                return self._finalise_response(
                    build_reply("Please enter something."),
                    session_id=session_id,
                    store_user_message=False,
                    store_assistant_message=False,
                )

            self.session_manager.add_message(session_id, "user", text)
            lowered = normalize_text(text)

            feedback_value = self._extract_feedback_value(text)
            if session.get("awaiting_feedback") and feedback_value:
                session["awaiting_feedback"] = False
                session["bin_task_completed"] = False

                self._reset_pending_intent_state(session)
                self.session_manager.reset_flow_state(session)
                self.session_manager.reset_bin_flow_state(session)
                self.session_manager.clear_guidance_state(session)
                self.session_manager.reset_service_context(session)
                self._reset_council_tax_state(session)

                self.session_manager.update_task(
                    session_id,
                    feedback_requested=False,
                )

                star_messages = {
                    "1": "Thank you for your feedback. We're sorry your experience wasn't great — we'll use this to improve. &#x1F64F;",
                    "2": "Thank you for your feedback. We'll work on doing better. &#x1F44D;",
                    "3": "Thank you for your feedback! We're always looking to improve. &#x1F44D;",
                    "4": "Thank you — great to hear you had a good experience! &#x2B50;",
                    "5": "Thank you so much! &#x1F31F; We're delighted you had an excellent experience.",
                }
                thank_you = star_messages.get(feedback_value, "Thank you for your feedback.")
                return self._finalise_response(
                    build_reply(thank_you),
                    session_id=session_id,
                )

            if lowered == "exit":
                reply = build_reply("Goodbye.")
                self.session_manager.reset_session(session_id)
                return self._finalise_response(
                    reply,
                    session_id=session_id,
                    store_assistant_message=False,
                )

            if lowered == "menu":
                self.session_manager.reset_session(session_id)
                reply = build_reply(build_main_menu_text())
                return self._finalise_response(
                    reply,
                    session_id=session_id,
                    store_assistant_message=False,
                )

            if lowered == "back":
                return self._handle_back(session, session_id)

            if self._is_polite_closing_message(text):
                session["awaiting_feedback"] = True
                session["bin_task_completed"] = False
                self._reset_pending_intent_state(session)

                self.session_manager.update_task(
                    session_id,
                    feedback_requested=True,
                )

                return self._finalise_response(
                    self._build_feedback_prompt(),
                    session_id=session_id,
                )

            if session.get("selected_service") is None:
                if is_greeting(text):
                    return self._finalise_response(
                        build_reply(
                            f"{get_time_greeting()}! How can I help you today? "
                            "Please choose a service below or type your question.",
                            input_type="options",
                            options=SERVICE_OPTION_CHIPS,
                        ),
                        session_id=session_id,
                    )
                return self._handle_service_selection(text, session, session_id)

            # Direct postcode entry in bin service → skip confirmation, start lookup
            if (
                session.get("selected_service") == "bin_collection"
                and session.get("bin_flow_stage") is None
                and _is_uk_postcode(text)
            ):
                self._clear_post_completion_state(session)
                session["bin_flow_stage"] = "awaiting_postcode"
                response = self.bin_handler.handle_bin_postcode(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("bin_flow_stage") == "awaiting_postcode":
                self._clear_post_completion_state(session)
                response = self.bin_handler.handle_bin_postcode(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("bin_flow_stage") == "awaiting_address":
                self._clear_post_completion_state(session)
                response = self.bin_handler.handle_bin_address_selection(session, text)
                payload = self._normalise_response(response)

                self._sync_bin_memory_from_session(session_id, session)

                if (
                    session.get("bin_flow_stage") is None
                    and payload.get("input_type") != "options"
                ):
                    self._mark_bin_task_completed(session)

                return self._finalise_response(payload, session_id=session_id)

            if session.get("school_flow_stage") == "awaiting_school_query":
                self._clear_post_completion_state(session)
                response = self.school_handler.handle_school_query(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("school_flow_stage") == "awaiting_postcode_for_distance":
                self._clear_post_completion_state(session)
                response = self.school_handler.handle_postcode_for_distance(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("school_flow_stage") == "awaiting_school_selection":
                self._clear_post_completion_state(session)
                response = self.school_handler.handle_school_selection(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("library_flow_stage") == "awaiting_library_query":
                self._clear_post_completion_state(session)
                response = self.library_handler.handle_library_query(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("library_flow_stage") in {
                "awaiting_postcode_for_distance",
                "awaiting_postcode_for_library_distance",
            }:
                self._clear_post_completion_state(session)
                response = self.library_handler.handle_postcode_for_distance(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("library_flow_stage") == "awaiting_library_selection":
                self._clear_post_completion_state(session)
                response = self.library_handler.handle_library_selection(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("blue_badge_flow_stage") == "awaiting_renewal_date":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.handle_renewal_date(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("blue_badge_flow_stage") == "eligibility_wizard":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.handle_eligibility_step(session, text)
                return self._finalise_response(response, session_id=session_id)

            pending_result = self._dispatch_pending_action(session, text, session_id)
            if pending_result is not None:
                return pending_result

            if (
                session.get("active_intent") is not None
                and session.get("current_step_id") is not None
            ):
                self._clear_post_completion_state(session)
                response = self.dialogue_handler.continue_flow(session, text)
                return self._finalise_response(response, session_id=session_id)

            if session.get("awaiting_confirmation_type") is not None:
                return self._handle_intent_confirmation(
                    text=text,
                    lowered=lowered,
                    session=session,
                    session_id=session_id,
                    memory=memory,
                )

            if session.get("awaiting_intent_choice"):
                return self._handle_intent_choice(
                    text=text,
                    session=session,
                    session_id=session_id,
                    memory=memory,
                )

            if session.get("selected_service") == "something_else":
                return self._finalise_response(
                    build_reply("Please type 'menu' and choose the closest service area."),
                    session_id=session_id,
                )

            session["last_question_text"] = text
            intent_result = self.intent_handler.detect_intent(
                session["selected_service"],
                text,
                session=session,
            )

            if intent_result["type"] == "confirm":
                session["awaiting_confirmation_type"] = "intent_check"
                session["pending_predicted_intent"] = intent_result["intent"]
                return self._finalise_response(
                    intent_result["message"],
                    session_id=session_id,
                )

            if intent_result["type"] == "clarify":
                session["awaiting_intent_choice"] = True
                session["excluded_intent_choice"] = intent_result.get("intent")
                session["pending_predicted_intent"] = None
                return self._finalise_response(
                    intent_result["message"],
                    session_id=session_id,
                )

            if intent_result["type"] == "flow_reply":
                pending_result = self._dispatch_pending_action(session, text, session_id)
                if pending_result is not None:
                    return pending_result

            detected_intent = intent_result.get("intent")

            if not detected_intent:
                return self._finalise_response(
                    build_reply("I’m not sure what you need help with. Please rephrase your question."),
                    session_id=session_id,
                )

            return self._route_detected_intent(
                detected_intent=detected_intent,
                text=text,
                session=session,
                session_id=session_id,
                memory=memory,
            )

        except Exception as exc:
            return self._finalise_response(
                build_reply(f"Something went wrong: {exc}"),
                session_id=session_id,
                store_user_message=False,
            )

    # =========================================================
    # MAIN ROUTING
    # =========================================================
    def _route_detected_intent(
        self,
        detected_intent: str,
        text: str,
        session: dict[str, Any],
        session_id: str,
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        if detected_intent == BIN_LIVE_INTENT:
            self._clear_post_completion_state(session)

            self.session_manager.update_task(
                session_id,
                service=session.get("selected_service") or "bin_collection",
            )

            self._hydrate_bin_session_from_memory(session, memory)

            response = self.bin_handler.start_bin_collection_flow(session)
            final_payload = self._finalise_response(response, session_id=session_id)

            self._sync_bin_memory_from_session(session_id, session)
            return final_payload

        if detected_intent == SCHOOL_FINDER_INTENT:
            self._clear_post_completion_state(session)
            self.session_manager.update_task(session_id, service="school_admissions")
            response = self.school_handler.start_school_finder_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if detected_intent == LIBRARY_FINDER_INTENT:
            self._clear_post_completion_state(session)
            self.session_manager.update_task(session_id, service="libraries")
            response = self.library_handler.start_library_finder_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if detected_intent == "bin_recycling_guidance":
            return self._answer_bin_guidance(
                text=text,
                session=session,
                session_id=session_id,
                detected_intent=detected_intent,
            )

        if detected_intent in COUNCIL_TAX_LIVE_INTENTS:
            return self._handle_council_tax_live_intent(
                intent_name=detected_intent,
                session=session,
                session_id=session_id,
            )

        if session.get("selected_service") == "council_tax":
            rag_response = self._try_rag(
                text=text,
                detected_intent=detected_intent,
                session=session,
                session_id=session_id,
            )
            if rag_response is not None:
                return rag_response

        if session.get("selected_service") == "school_admissions":
            rag_response = self._try_rag(
                text=text,
                detected_intent=detected_intent,
                session=session,
                session_id=session_id,
            )
            if rag_response is not None:
                return rag_response

        if session.get("selected_service") == "blue_badge":
            # Renewal reminder — guided multi-step flow
            if detected_intent == "blue_badge_renewal":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.start_renewal_reminder_flow(session)
                return self._finalise_response(response, session_id=session_id)

            # Eligibility wizard — step-by-step questions
            if detected_intent == "blue_badge_eligibility":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.start_eligibility_wizard(session)
                return self._finalise_response(response, session_id=session_id)

            # Parking rules — RAG answer + map card
            if detected_intent == "blue_badge_parking_rules":
                return self._answer_blue_badge_parking(
                    text=text,
                    session=session,
                    session_id=session_id,
                    detected_intent=detected_intent,
                )

            rag_response = self._try_rag(
                text=text,
                detected_intent=detected_intent,
                session=session,
                session_id=session_id,
            )
            if rag_response is not None:
                return rag_response

        if session.get("selected_service") == "libraries":
            rag_response = self._try_rag(
                text=text,
                detected_intent=detected_intent,
                session=session,
                session_id=session_id,
            )
            if rag_response is not None:
                return rag_response

        self._clear_post_completion_state(session)
        response = self.dialogue_handler.handle_direct_intent(
            session=session,
            intent_name=detected_intent,
            service_key=session["selected_service"],
            original_text=text,
            live_bin_intent=BIN_LIVE_INTENT,
            bin_handler=self.bin_handler,
        )
        return self._finalise_response(response, session_id=session_id)

    def _handle_council_tax_live_intent(
        self,
        intent_name: str,
        session: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        self._clear_post_completion_state(session)

        self.session_manager.update_task(
            session_id,
            service="council_tax",
        )

        if intent_name == "find_council_tax_band":
            self.session_manager.reset_flow_state(session)
            self.session_manager.clear_guidance_state(session)

            session["active_intent"] = intent_name
            session["pending_action"] = "awaiting_council_tax_postcode"
            session["council_tax_addresses"] = []
            session["council_tax_postcode"] = None

            return self._finalise_response(
                build_reply("Please enter your postcode to find your Council Tax band."),
                session_id=session_id,
            )

        if intent_name == "council_tax_payment":
            session["active_intent"] = intent_name
            response = self.dialogue_handler.council_tax_handler.start_payment_flow(session)
            return self._finalise_response(
                response,
                session_id=session_id,
            )

        return self._finalise_response(
            build_reply("Please tell me more about your Council Tax request."),
            session_id=session_id,
        )

    def _try_rag(
        self,
        text: str,
        detected_intent: str,
        session: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any] | None:
        try:
            rag_result = self.rag_service.answer_query(
                query=text,
                service_name=session.get("selected_service"),
                intent=detected_intent,
                context={
                    "band": session.get("band"),
                    "balance": session.get("balance"),
                    "selected_address": session.get("selected_address"),
                    "postcode": session.get("postcode"),
                },
            )
        except TypeError:
            rag_result = self.rag_service.answer_query(
                query=text,
                service_name=session.get("selected_service"),
                k=1,
            )
        except Exception:
            return None

        if not isinstance(rag_result, dict):
            return None

        if not rag_result.get("matched"):
            return None

        answer = str(rag_result.get("answer", "")).strip()
        if not answer:
            return None

        # Council tax gets styled HTML bubbles
        if session.get("selected_service") == "council_tax":
            bubbles = format_council_tax_messages(
                answer,
                intent=detected_intent,
                source_url=rag_result.get("source_url"),
            )
            return self._finalise_response(
                build_messages_reply(bubbles),
                session_id=session_id,
            )

        return self._finalise_response(
            build_reply(answer),
            session_id=session_id,
        )

    # =========================================================
    # BIN GUIDANCE
    # =========================================================
    def _answer_bin_guidance(
        self,
        text: str,
        session: dict[str, Any],
        session_id: str,
        detected_intent: str,
    ) -> dict[str, Any]:
        # Try keyword dataset first
        if self.bin_guidance.lookup(text):
            return self.bin_guidance.build_reply(text, session_id, self._finalise_response)

        # Fall back to RAG
        rag_response = self._try_rag(
            text=text,
            detected_intent=detected_intent,
            session=session,
            session_id=session_id,
        )
        if rag_response is not None:
            return rag_response

        # Final fallback: generic guidance bubble
        return self.bin_guidance.build_reply(text, session_id, self._finalise_response)

    # =========================================================
    # BLUE BADGE PARKING MAP
    # =========================================================
    def _answer_blue_badge_parking(
        self,
        text: str,
        session: dict[str, Any],
        session_id: str,
        detected_intent: str,
    ) -> dict[str, Any]:
        """Return RAG parking-rules answer + a helpful map card."""
        rag_response = self._try_rag(
            text=text,
            detected_intent=detected_intent,
            session=session,
            session_id=session_id,
        )

        # Build a compact map card as an extra bubble
        map_card = (
            '<div style="border:1px solid #e0e0e0;border-radius:8px;padding:12px 14px;'
            'background:#f8faff;margin-top:4px;">'
            '<div style="font-weight:600;margin-bottom:6px;">&#x1F5FA; Find Disabled Parking in Bradford</div>'
            '<div style="margin-bottom:4px;">'
            '- <a href="https://www.bradford.gov.uk/transport-and-travel/parking/blue-badge-parking/" '
            'target="_blank" rel="noopener noreferrer">Bradford Blue Badge Parking Guide</a>'
            " — full rules and concessions"
            "</div>"
            '<div style="margin-bottom:4px;">'
            '- <a href="https://www.google.com/maps/search/disabled+parking+bradford+city+centre/" '
            'target="_blank" rel="noopener noreferrer">Disabled Parking Bays Map (Google Maps)</a>'
            " — find bays near you"
            "</div>"
            '<div>'
            '- <a href="https://www.gov.uk/government/publications/blue-badge-can-i-use-it-here" '
            'target="_blank" rel="noopener noreferrer">GOV.UK — Can I use it here?</a>'
            " — full national rules"
            "</div>"
            "</div>"
        )

        if rag_response is not None:
            # Append the map card as an extra message bubble
            messages = list(rag_response.get("messages") or [])
            if messages:
                messages.append({"reply": map_card, "isHtml": True})
            else:
                text_reply = rag_response.get("reply", "")
                messages = [
                    {"reply": text_reply},
                    {"reply": map_card, "isHtml": True},
                ]
            rag_response["messages"] = messages
            return rag_response

        # No RAG match — return just the map card with a brief intro
        from backend.utils.response_builder import build_messages_reply
        return self._finalise_response(
            build_messages_reply([
                {
                    "reply": (
                        "With a valid Blue Badge you can park in disabled bays, "
                        "on single or double yellow lines for up to 3 hours (with your parking clock), "
                        "and free of charge in council Pay and Display bays. "
                        "The badge holder must always be present in the vehicle. "
                        "See the full rules at "
                        "https://www.bradford.gov.uk/transport-and-travel/parking/blue-badge-parking/"
                    ),
                },
                {"reply": map_card, "isHtml": True},
            ]),
            session_id=session_id,
        )

    # =========================================================
    # FLOW HELPERS
    # =========================================================
    def _handle_service_selection(
        self,
        text: str,
        session: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        resolved = resolve_service_choice(text)
        if resolved is None:
            return self._finalise_response(
                build_reply(
                    "Please type one of the service names shown in the menu.\n\n"
                    + build_main_menu_text()
                ),
                session_id=session_id,
            )

        selected_service, selected_label = resolved
        session["selected_service"] = selected_service

        self.session_manager.update_task(
            session_id,
            service=selected_service,
        )

        self.session_manager.reset_flow_state(session)
        self.session_manager.reset_bin_flow_state(session)
        self.session_manager.clear_guidance_state(session)
        self._clear_post_completion_state(session)
        self._reset_pending_intent_state(session)
        self._reset_council_tax_state(session)
        self.school_handler._reset_school_flow(session)
        self.library_handler._reset_library_flow(session)
        self.blue_badge_handler.reset_blue_badge_flow(session)

        return self._finalise_response(
            build_reply(f"You selected {selected_label}. Please type your question."),
            session_id=session_id,
        )

    def _handle_back(
        self,
        session: dict[str, Any],
        session_id: str,
    ) -> dict[str, Any]:
        self._clear_post_completion_state(session)
        self._reset_pending_intent_state(session)

        if session.get("bin_flow_stage") is not None:
            self.session_manager.reset_bin_flow_state(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the current bin request. Please ask another question or type 'menu'."
                ),
                session_id=session_id,
            )

        if session.get("school_flow_stage") is not None:
            self.school_handler._reset_school_flow(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the school search. Please ask another question or type 'menu'."
                ),
                session_id=session_id,
            )

        if session.get("library_flow_stage") is not None:
            self.library_handler._reset_library_flow(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the library search. Please ask another question or type 'menu'."
                ),
                session_id=session_id,
            )

        if session.get("blue_badge_flow_stage") is not None:
            self.blue_badge_handler.reset_blue_badge_flow(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the Blue Badge request. Please ask another question or type 'menu'."
                ),
                session_id=session_id,
            )

        if session.get("pending_action") in {
            "awaiting_council_tax_amount_confirmation",
            "awaiting_council_tax_band_confirmation",
            "awaiting_council_tax_band_input",
            "awaiting_council_tax_postcode",
            "awaiting_council_tax_address_selection",
        }:
            self._reset_council_tax_state(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the current Council Tax request. Please ask another question in this service area, or type 'menu'."
                ),
                session_id=session_id,
            )

        if session.get("active_intent") is not None:
            self.session_manager.reset_flow_state(session)
            self.session_manager.clear_guidance_state(session)
            return self._finalise_response(
                build_reply(
                    "Leaving the current request flow. Please ask another question in this service area, or type 'menu'."
                ),
                session_id=session_id,
            )

        self.session_manager.reset_service_context(session)
        return self._finalise_response(
            build_reply(
                "Returning to the main service menu.\n\n" + build_main_menu_text()
            ),
            session_id=session_id,
        )

    def _handle_intent_confirmation(
        self,
        text: str,
        lowered: str,
        session: dict[str, Any],
        session_id: str,
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        predicted_intent = session.get("pending_predicted_intent")
        selected_service = session.get("selected_service")
        original_question = session.get("last_question_text") or text

        if lowered in {"yes", "y"} and predicted_intent:
            if predicted_intent == BIN_LIVE_INTENT:
                self._clear_post_completion_state(session)
                self._hydrate_bin_session_from_memory(session, memory)
                response = self.bin_handler.start_bin_collection_flow(session)
                return self._finalise_response(response, session_id=session_id)

            if predicted_intent == SCHOOL_FINDER_INTENT:
                self._clear_post_completion_state(session)
                response = self.school_handler.start_school_finder_flow(session)
                return self._finalise_response(response, session_id=session_id)

            if predicted_intent == LIBRARY_FINDER_INTENT:
                self._clear_post_completion_state(session)
                response = self.library_handler.start_library_finder_flow(session)
                return self._finalise_response(response, session_id=session_id)

            if predicted_intent == "bin_recycling_guidance":
                return self._answer_bin_guidance(
                    text=original_question,
                    session=session,
                    session_id=session_id,
                    detected_intent=predicted_intent,
                )

            if predicted_intent == "blue_badge_renewal":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.start_renewal_reminder_flow(session)
                return self._finalise_response(response, session_id=session_id)

            if predicted_intent == "blue_badge_eligibility":
                self._clear_post_completion_state(session)
                response = self.blue_badge_handler.start_eligibility_wizard(session)
                return self._finalise_response(response, session_id=session_id)

            if predicted_intent == "blue_badge_parking_rules":
                return self._answer_blue_badge_parking(
                    text=original_question,
                    session=session,
                    session_id=session_id,
                    detected_intent=predicted_intent,
                )

            if predicted_intent in COUNCIL_TAX_LIVE_INTENTS:
                return self._handle_council_tax_live_intent(
                    intent_name=predicted_intent,
                    session=session,
                    session_id=session_id,
                )

            self._clear_post_completion_state(session)
            response = self.dialogue_handler.handle_direct_intent(
                session=session,
                intent_name=predicted_intent,
                service_key=selected_service,
                original_text=original_question,
                live_bin_intent=BIN_LIVE_INTENT,
                bin_handler=self.bin_handler,
            )
            return self._finalise_response(response, session_id=session_id)

        session["awaiting_confirmation_type"] = None
        session["awaiting_intent_choice"] = True
        session["excluded_intent_choice"] = predicted_intent
        session["skip_fallback_once"] = True
        session["pending_predicted_intent"] = None

        return self._finalise_response(
            build_reply(
                self.intent_handler.show_intent_options_for_service(
                    selected_service,
                    predicted_intent,
                )
            ),
            session_id=session_id,
        )

    def _handle_intent_choice(
        self,
        text: str,
        session: dict[str, Any],
        session_id: str,
        memory: dict[str, Any],
    ) -> dict[str, Any]:
        chosen_intent = self.intent_handler.resolve_intent_label_choice(
            text,
            session["selected_service"],
            session.get("excluded_intent_choice"),
        )

        if chosen_intent is None:
            return self._finalise_response(
                build_reply(
                    "Please type one of the intent option names exactly as shown.\n\n"
                    + self.intent_handler.show_intent_options_for_service(
                        session["selected_service"],
                        session.get("excluded_intent_choice"),
                    )
                ),
                session_id=session_id,
            )

        session["awaiting_intent_choice"] = False
        session["excluded_intent_choice"] = None

        if chosen_intent == BIN_LIVE_INTENT:
            self._clear_post_completion_state(session)
            self._hydrate_bin_session_from_memory(session, memory)
            response = self.bin_handler.start_bin_collection_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if chosen_intent == SCHOOL_FINDER_INTENT:
            self._clear_post_completion_state(session)
            response = self.school_handler.start_school_finder_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if chosen_intent == LIBRARY_FINDER_INTENT:
            self._clear_post_completion_state(session)
            response = self.library_handler.start_library_finder_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if chosen_intent == "bin_recycling_guidance":
            return self._answer_bin_guidance(
                text=text,
                session=session,
                session_id=session_id,
                detected_intent=chosen_intent,
            )

        if chosen_intent == "blue_badge_renewal":
            self._clear_post_completion_state(session)
            response = self.blue_badge_handler.start_renewal_reminder_flow(session)
            return self._finalise_response(response, session_id=session_id)

        if chosen_intent == "blue_badge_eligibility":
            self._clear_post_completion_state(session)
            response = self.blue_badge_handler.start_eligibility_wizard(session)
            return self._finalise_response(response, session_id=session_id)

        if chosen_intent == "blue_badge_parking_rules":
            return self._answer_blue_badge_parking(
                text=text,
                session=session,
                session_id=session_id,
                detected_intent=chosen_intent,
            )

        if chosen_intent in COUNCIL_TAX_LIVE_INTENTS:
            return self._handle_council_tax_live_intent(
                intent_name=chosen_intent,
                session=session,
                session_id=session_id,
            )

        self._clear_post_completion_state(session)
        response = self.dialogue_handler.handle_direct_intent(
            session=session,
            intent_name=chosen_intent,
            service_key=session["selected_service"],
            original_text=text,
            live_bin_intent=BIN_LIVE_INTENT,
            bin_handler=self.bin_handler,
        )
        return self._finalise_response(response, session_id=session_id)

    # =========================================================
    # RESPONSE HELPERS
    # =========================================================
    def _normalise_response(self, response: Any) -> dict[str, Any]:
        if isinstance(response, dict):
            if isinstance(response.get("messages"), list):
                if not response.get("reply") and response["messages"]:
                    first_reply = str(response["messages"][0].get("reply", "")).strip()
                    if first_reply:
                        response["reply"] = first_reply
                return response

            if "reply" in response:
                reply_text = str(response.get("reply", "")).strip()
                return {
                    **response,
                    "reply": reply_text,
                    "messages": [{"reply": reply_text}],
                }

            if "message" in response:
                message_text = str(response.get("message", "")).strip()
                return {
                    **response,
                    "reply": message_text,
                    "messages": [{"reply": message_text}],
                }

            return response

        text = str(response).strip()
        return build_reply(text)

    def _finalise_response(
        self,
        response: Any,
        session_id: str,
        store_user_message: bool = False,
        store_assistant_message: bool = True,
    ) -> dict[str, Any]:
        payload = self._normalise_response(response)

        reply_text = str(payload.get("reply", "")).strip()
        if store_assistant_message and reply_text:
            self.session_manager.add_message(session_id, "assistant", reply_text)

            extracted_link = self._extract_first_link(reply_text)
            if extracted_link:
                self.session_manager.update_task(
                    session_id,
                    last_council_link=extracted_link,
                )

        return payload

    # =========================================================
    # PENDING-ACTION DISPATCH  (single source of truth)
    # =========================================================
    def _dispatch_pending_action(
        self,
        session: dict[str, Any],
        text: str,
        session_id: str,
    ) -> dict[str, Any] | None:
        """
        Route a pending_action to its handler.
        Returns a finalised response dict, or None if no pending action is set.
        Called from two places: the direct flow checks and the flow_reply branch.
        """
        pending_action = session.get("pending_action")
        if not pending_action:
            return None

        ct  = self.dialogue_handler.council_tax_handler
        ben = self.dialogue_handler.benefits_handler

        handlers = {
            "awaiting_council_tax_amount_confirmation":  lambda: ct.handle_amount_confirmation(text, session),
            "awaiting_council_tax_band_confirmation":    lambda: ct.handle_band_confirmation(text, session),
            "awaiting_council_tax_band_input":           lambda: ct.handle_band_input(text, session),
            "awaiting_council_tax_postcode":             lambda: ct.handle_postcode(text, session),
            "awaiting_council_tax_address_selection":    lambda: ct.handle_address_selection(text, session),
            "awaiting_benefits_age_group":               lambda: ben.handle_age_group(text, session),
            "awaiting_benefits_housing_type":            lambda: ben.handle_housing_type(text, session),
        }

        fn = handlers.get(pending_action)
        if fn is None:
            return None

        self._clear_post_completion_state(session)
        return self._finalise_response(fn(), session_id=session_id)

    # =========================================================
    # STATE HELPERS
    # =========================================================
    def _clear_post_completion_state(self, session: dict[str, Any]) -> None:
        session["awaiting_feedback"] = False
        session["bin_task_completed"] = False

    def _mark_bin_task_completed(self, session: dict[str, Any]) -> None:
        session["bin_task_completed"] = True
        session["awaiting_feedback"] = False

    def _reset_pending_intent_state(self, session: dict[str, Any]) -> None:
        session["awaiting_confirmation_type"] = None
        session["awaiting_intent_choice"] = False
        session["pending_predicted_intent"] = None
        session["excluded_intent_choice"] = None
        session["skip_fallback_once"] = False

    def _reset_council_tax_state(self, session: dict[str, Any]) -> None:
        session["pending_action"] = None
        session["council_tax_addresses"] = []
        session["council_tax_postcode"] = None
        if session.get("active_intent") in {
            "find_council_tax_band",
            "council_tax_payment",
        }:
            session["active_intent"] = None

    # =========================================================
    # MEMORY HELPERS
    # =========================================================
    def _sync_bin_memory_from_session(self, session_id: str, session: dict[str, Any]) -> None:
        selected_uprn = session.get("bin_selected_uprn")
        if selected_uprn:
            self.session_manager.update_task(session_id, uprn=selected_uprn)

        addresses = session.get("bin_addresses") or []
        if selected_uprn and addresses:
            selected_address = next(
                (item for item in addresses if item.get("uprn") == selected_uprn),
                None,
            )
            if selected_address:
                self.session_manager.update_task(
                    session_id,
                    selected_address=selected_address.get("label"),
                )

    def _hydrate_bin_session_from_memory(
        self,
        session: dict[str, Any],
        memory: dict[str, Any],
    ) -> None:
        task = memory.get("current_task", {})
        remembered_uprn = task.get("uprn")

        if remembered_uprn and not session.get("bin_selected_uprn"):
            session["bin_selected_uprn"] = remembered_uprn

    # =========================================================
    # TEXT HELPERS
    # =========================================================
    def _is_polite_closing_message(self, text: str) -> bool:
        cleaned = normalize_text(text)
        cleaned = re.sub(r"[^\w\s]", "", cleaned)

        closing_phrases = {
            "ok",
            "okay",
            "ok thanks",
            "okay thanks",
            "thanks",
            "thank you",
            "thanks okay",
            "thanks ok",
            "ok thank you",
            "okay thank you",
            "no thanks",
            "no thank you",
            "thats all",
            "that's all",
            "all good",
            "im done",
            "i am done",
            "done thanks",
            "nothing else",
            "no thats all",
            "no that's all",
            "thats it",
            "that's it",
            "cheers",
            "cheers thanks",
        }
        return cleaned in closing_phrases

    def _build_feedback_prompt(self) -> dict[str, Any]:
        reply = "How would you rate your experience today? &#x2B50;"
        return {
            "reply": reply,
            "messages": [{"reply": reply, "isHtml": True}],
            "input_type": "feedback",
            "isHtml": True,
        }

    def _extract_feedback_value(self, text: str) -> str | None:
        cleaned = normalize_text(str(text or "").strip())
        # Accept numeric 1-5
        if cleaned in {"1", "2", "3", "4", "5"}:
            return cleaned
        # Accept star words
        word_map = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "terrible": "1", "poor": "2", "okay": "3", "good": "4", "great": "5",
            "excellent": "5", "awful": "1", "bad": "2", "average": "3",
        }
        return word_map.get(cleaned)

    def _extract_first_link(self, text: str) -> str | None:
        match = re.search(r"https?://\S+", text or "")
        return match.group(0) if match else None