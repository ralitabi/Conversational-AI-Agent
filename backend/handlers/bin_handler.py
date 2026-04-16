from __future__ import annotations

from typing import Any, Dict, List

from backend.council_connectors.bin_connector import (
    get_dates_for_address,
    search_addresses_by_postcode,
)
from backend.utils.bin_formatter import (
    format_bin_date_messages,
    format_bin_fallback_messages,
)
from backend.utils.response_builder import build_reply, build_messages_reply


BIN_COLLECTION_LINK = (
    "https://www.bradford.gov.uk/recycling-and-waste/bin-collections/"
    "check-your-bin-collection-dates/"
)


class BinHandler:
    def __init__(self, session_manager) -> None:
        self.session_manager = session_manager

    def start_bin_collection_flow(self, session: dict) -> dict:
        self.session_manager.reset_flow_state(session)
        self.session_manager.reset_bin_flow_state(session)
        self.session_manager.clear_guidance_state(session)

        session["bin_flow_stage"] = "awaiting_postcode"
        session["bin_address_cache"] = {}

        return build_reply(
            reply="Please enter your full postcode to check your bin collection dates.",
            input_type="text",
        )

    def handle_bin_postcode(self, session: dict, postcode: str) -> dict:
        postcode = (postcode or "").strip()

        if not postcode:
            return build_reply(
                reply="Please enter your full postcode.",
                input_type="text",
            )

        address_cache: Dict[str, Any] = {}

        try:
            addresses = search_addresses_by_postcode(postcode, address_cache)
            print(f"[BinHandler] ADDRESSES RETURNED: {len(addresses)}")
        except Exception as exc:
            return build_reply(
                reply=f"I could not look up that postcode right now. Please try again. ({exc})",
                input_type="text",
            )

        if not addresses:
            return build_reply(
                reply=(
                    "I could not find any addresses for that postcode. "
                    "Please check you entered the full postcode correctly and try again."
                ),
                input_type="text",
            )

        session["bin_postcode"] = postcode
        session["bin_addresses"] = addresses
        session["bin_address_cache"] = address_cache
        session["bin_flow_stage"] = "awaiting_address"

        options: List[Dict[str, str]] = []
        allowed_values: List[str] = []

        for index, address in enumerate(addresses, start=1):
            uprn  = str(address.get("uprn", "") or "").strip()
            label = str(address.get("label", "") or "").strip()

            if not label and uprn:
                label = uprn
            if not uprn and label:
                uprn = label
            if not uprn and not label:
                label = f"Address option {index}"
                uprn = label

            options.append({"label": label, "value": uprn})
            allowed_values.append(uprn)

        if not options:
            return build_reply(
                reply=(
                    "I found addresses for that postcode, but I could not display them. "
                    "Please try again."
                ),
                input_type="text",
            )

        return build_reply(
            reply="I found these addresses. Please select your address.",
            input_type="options",
            allowed_values=allowed_values,
            options=options,
        )

    def handle_bin_address_selection(self, session: dict, selected_value: str) -> dict:
        selected_value = str(selected_value or "").strip()
        addresses = session.get("bin_addresses", [])

        matched = self._find_matching_address(addresses, selected_value)

        if matched is None:
            return self._build_invalid_address_response(addresses)

        selected_uprn = (
            str(matched.get("uprn", "") or "").strip()
            or str(matched.get("label", "") or "").strip()
        )
        selected_label = (
            str(matched.get("label", "") or "").strip()
            or selected_uprn
        )

        session["bin_selected_uprn"]    = selected_uprn
        session["bin_selected_address"] = selected_label
        session["rag_bin_uprn"]         = selected_uprn
        session["rag_bin_address"]      = selected_label
        session["bin_flow_stage"]       = "completed"

        session_id = session.get("session_id", "default")
        self.session_manager.update_task(
            session_id,
            service="bins",
            selected_address=selected_label,
            uprn=selected_uprn,
            last_council_link=BIN_COLLECTION_LINK,
        )

        self.session_manager.reset_bin_flow_state(session)
        self.session_manager.clear_guidance_state(session)

        # Try to fetch live collection dates
        address_cache = session.get("bin_address_cache", {})
        date_result = None

        if address_cache:
            try:
                date_result = get_dates_for_address(selected_uprn, address_cache)
            except Exception as exc:
                print(f"[BinHandler] get_dates_for_address failed: {exc}")

        if date_result and date_result.get("success"):
            collections   = date_result.get("collections", [])
            next_coll     = date_result.get("next_collection", "")
            garden_msg    = date_result.get("garden_message", "")
            addr_label    = date_result.get("address_label", "") or selected_label

            bubbles = format_bin_date_messages(
                address_label=addr_label,
                collections=collections,
                next_collection=next_coll,
                garden_message=garden_msg,
            )
        else:
            # Fallback: styled HTML with link
            bubbles = format_bin_fallback_messages(selected_label)

        # Append "anything else?" prompt
        bubbles.append({
            "reply": (
                "Is there anything else I can help you with? "
                "You can ask another question or type <strong>menu</strong>."
            )
        })

        return build_messages_reply(bubbles)

    # -------------------------------------------------------------------------
    def _find_matching_address(self, addresses: list, selected_value: str) -> dict | None:
        for address in addresses:
            uprn  = str(address.get("uprn",  "") or "").strip()
            label = str(address.get("label", "") or "").strip()
            if uprn == selected_value or label == selected_value:
                return address
        return None

    def _build_invalid_address_response(self, addresses: list) -> dict:
        allowed_values: List[str] = []
        options: List[Dict[str, str]] = []

        for address in addresses:
            uprn  = str(address.get("uprn",  "") or "").strip()
            label = str(address.get("label", "") or "").strip()
            value = uprn or label
            display_label = label or uprn or "Address option"

            if value:
                allowed_values.append(value)
                options.append({"label": display_label, "value": value})

        return build_reply(
            reply="Please select one of the addresses shown in the list.",
            input_type="options",
            allowed_values=allowed_values,
            options=options,
        )
