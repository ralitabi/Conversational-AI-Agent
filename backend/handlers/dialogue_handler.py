from pathlib import Path
from typing import Optional

from backend.chat_helpers import extract_step_id, should_use_dialogue_flow
from backend.dialogue_manager import DialogueManager
from backend.rag_service import RAGService
from backend.utils.response_builder import build_reply, build_messages_reply
from backend.utils.benefits_formatter import format_benefits_messages
from backend.utils.council_tax_formatter import format_council_tax_messages

from backend.handlers.council_tax_band_handler import CouncilTaxBandHandler
from backend.council_connectors.council_tax_connector import CouncilTaxConnector
from backend.handlers.benefits_handler import BenefitsHandler
from backend.council_connectors.benefits_connector import BenefitsConnector


class DialogueHandler:
    def __init__(self, datasets_path: Path, session_manager) -> None:
        self.datasets_path = Path(datasets_path)
        self.dialogue_manager = DialogueManager(self.datasets_path)
        self.rag_service: Optional[RAGService] = None
        self.session_manager = session_manager

        # Special handler for Council Tax band lookup
        self.council_tax_handler = CouncilTaxBandHandler(CouncilTaxConnector())

        # Special handler for benefits calculator (Turn2Us integration)
        self.benefits_handler = BenefitsHandler(BenefitsConnector())

    def get_rag_service(self) -> RAGService:
        if self.rag_service is None:
            self.rag_service = RAGService(self.datasets_path)
        return self.rag_service

    # -------------------------------------------------------------------------
    # Special flows
    # -------------------------------------------------------------------------

    def start_council_tax_band_flow(self, session: dict) -> dict:
        """
        Starts the special Council Tax band flow.
        """
        self.session_manager.reset_flow_state(session)
        self.session_manager.clear_guidance_state(session)

        session["active_intent"] = "find_council_tax_band"
        session["pending_action"] = "awaiting_council_tax_postcode"
        session["council_tax_addresses"] = []
        session["council_tax_postcode"] = None

        session_id = session.get("session_id", "default")
        self.session_manager.update_task(session_id, service="council_tax")

        return build_reply(
            reply="Please enter your postcode to find your Council Tax band."
        )

    # -------------------------------------------------------------------------
    # Structured dialogue flows
    # -------------------------------------------------------------------------

    def start_flow(
        self,
        session: dict,
        intent_name: str,
        live_bin_intent: str,
        bin_handler,
    ) -> dict:
        """
        Starts a structured dialogue flow for an intent.
        """
        if intent_name == live_bin_intent:
            return bin_handler.start_bin_collection_flow(session)

        first_response = self.dialogue_manager.get_first_response(intent_name)

        if not isinstance(first_response, dict):
            self.session_manager.reset_flow_state(session)
            return build_reply("Dialogue manager returned an invalid response.")

        if first_response.get("status") != "ok":
            self.session_manager.reset_flow_state(session)
            return build_reply(
                first_response.get("message", "Could not start that flow.")
            )

        message = first_response.get("message", "I can help with that.")
        session["active_intent"] = intent_name
        session["current_step_id"] = extract_step_id(first_response)
        session["collected_slots"] = first_response.get("slots", {})

        self.session_manager.clear_guidance_state(session)

        session_id = session.get("session_id", "default")
        self.session_manager.update_task(
            session_id,
            service=session.get("selected_service"),
        )

        if session["current_step_id"] is None and first_response.get("flow_complete") is True:
            self.session_manager.reset_flow_state(session)

        return build_reply(
            reply=message,
            input_type=first_response.get("input_type"),
            allowed_values=first_response.get("allowed_values"),
        )

    def continue_flow(self, session: dict, text: str) -> dict:
        """
        Continues an active structured dialogue flow.
        """
        result = self.dialogue_manager.continue_flow(
            intent_name=session["active_intent"],
            current_step_id=session["current_step_id"],
            user_input=text,
            slots=session["collected_slots"],
        )

        if not isinstance(result, dict):
            self.session_manager.reset_flow_state(session)
            return build_reply("Dialogue manager returned an invalid continuation response.")

        if result.get("status") != "ok":
            self.session_manager.reset_flow_state(session)
            return build_reply(
                result.get("message", "Could not continue that flow.")
            )

        session["collected_slots"] = result.get("slots", {})
        session["current_step_id"] = extract_step_id(result)

        message = result.get("message", "Okay.")

        if result.get("flow_complete") or session["current_step_id"] is None:
            self.session_manager.reset_flow_state(session)
            self.session_manager.clear_guidance_state(session)

            completion_mode = result.get("completion_mode", "rag")
            service_key = session.get("selected_service")

            if completion_mode == "rag" and service_key:
                original_query = session.get("last_question_text", "")
                active_intent = session.get("active_intent")
                rag_result = self.get_rag_service().answer_query(
                    query=original_query,
                    service_name=service_key,
                    intent=active_intent,
                    context={
                        "band": session.get("band"),
                        "balance": session.get("balance"),
                        "selected_address": session.get("selected_address"),
                        "postcode": session.get("postcode"),
                    },
                )
                if rag_result.get("matched"):
                    answer = str(rag_result.get("answer", "")).strip()
                    if answer:
                        if service_key == "benefits_support":
                            bubbles = format_benefits_messages(
                                answer,
                                intent=active_intent,
                                source_url=rag_result.get("source_url"),
                            )
                            bubbles.append(
                                {"reply": "Is there anything else I can help you with? You can ask another question or type <strong>menu</strong>."}
                            )
                            return build_messages_reply(bubbles)
                        if service_key == "council_tax":
                            bubbles = format_council_tax_messages(
                                answer,
                                intent=active_intent,
                                source_url=rag_result.get("source_url"),
                            )
                            bubbles.append(
                                {"reply": "Is there anything else I can help you with? You can ask another question or type <strong>menu</strong>."}
                            )
                            return build_messages_reply(bubbles)
                        return build_reply(
                            reply=(
                                f"{answer}\n\n"
                                "Is there anything else I can help you with? You can ask another question or type 'menu'."
                            )
                        )

            return build_reply(
                reply="This request is now complete. You can ask another question or type 'menu'."
            )

        return build_reply(
            reply=message,
            input_type=result.get("input_type"),
            allowed_values=result.get("allowed_values"),
        )

    # -------------------------------------------------------------------------
    # RAG
    # -------------------------------------------------------------------------

    def answer_with_rag(self, session: dict, query: str, service_key: str | None) -> dict:
        """
        Uses RAG for direct question answering.
        """
        result = self.get_rag_service().answer_query(
            query=query,
            k=10,
            service_name=service_key,
        )

        answer = result.get("answer", "I could not find an answer.")

        session_id = session.get("session_id", "default")
        memory = self.session_manager.get_memory(session_id)
        last_link = memory.get("current_task", {}).get("last_council_link")

        if last_link and last_link in answer:
            answer = answer.replace(last_link, "").strip()

        if service_key == "benefits_support" and result.get("matched"):
            bubbles = format_benefits_messages(
                answer,
                intent=result.get("intent"),
                source_url=result.get("source_url"),
            )
            return build_messages_reply(bubbles)

        if service_key == "council_tax" and result.get("matched"):
            bubbles = format_council_tax_messages(
                answer,
                intent=result.get("intent"),
                source_url=result.get("source_url"),
            )
            return build_messages_reply(bubbles)

        return build_reply(reply=answer)

    # -------------------------------------------------------------------------
    # Intent handling
    # -------------------------------------------------------------------------

    def start_benefits_calculator_flow(self, session: dict) -> dict:
        """Starts the Turn2Us benefits calculator qualifying flow."""
        return self.benefits_handler.start_flow(session)

    def handle_direct_intent(
        self,
        session: dict,
        intent_name: str,
        service_key: str | None,
        original_text: str,
        live_bin_intent: str,
        bin_handler,
        council_tax_band_intent: str = "find_council_tax_band",
    ) -> dict:
        """
        Handles a directly detected intent.
        """
        self.session_manager.clear_guidance_state(session)

        session_id = session.get("session_id", "default")
        if service_key:
            self.session_manager.update_task(session_id, service=service_key)

        # Benefits calculator
        if intent_name == "benefits_calculator":
            return self.start_benefits_calculator_flow(session)

        # Keep existing live bin flow
        if intent_name == live_bin_intent:
            return bin_handler.start_bin_collection_flow(session)

        # New Council Tax band flow
        if intent_name == council_tax_band_intent:
            return self.start_council_tax_band_flow(session)

        if should_use_dialogue_flow(intent_name, service_key):
            return self.start_flow(session, intent_name, live_bin_intent, bin_handler)

        return self.answer_with_rag(session, original_text, service_key)

    def handle_confirmed_intent(
        self,
        session: dict,
        predicted_intent: str | None,
        selected_service: str | None,
        original_question: str,
        live_bin_intent: str,
        bin_handler,
        council_tax_band_intent: str = "find_council_tax_band",
    ) -> dict:
        """
        Handles an intent after the user confirms it.
        """
        self.session_manager.clear_guidance_state(session)

        session_id = session.get("session_id", "default")
        if selected_service:
            self.session_manager.update_task(session_id, service=selected_service)

        # Benefits calculator
        if predicted_intent == "benefits_calculator":
            return self.start_benefits_calculator_flow(session)

        # Keep existing live bin flow
        if predicted_intent == live_bin_intent:
            return bin_handler.start_bin_collection_flow(session)

        # New Council Tax band flow
        if predicted_intent == council_tax_band_intent:
            return self.start_council_tax_band_flow(session)

        if predicted_intent and should_use_dialogue_flow(predicted_intent, selected_service):
            return self.start_flow(session, predicted_intent, live_bin_intent, bin_handler)

        return self.answer_with_rag(session, original_question, selected_service)