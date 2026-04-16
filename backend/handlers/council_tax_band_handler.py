from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def is_valid_uk_postcode(text: str) -> bool:
    postcode = text.strip().upper()
    pattern = r"^[A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2}$"
    return bool(re.match(pattern, postcode))


class CouncilTaxBandHandler:
    BILL_INFO_URL = (
        "https://www.bradford.gov.uk/council-tax/"
        "council-tax-bills/council-tax-bills/"
    )

    BAND_CHARGES_2026_27 = {
        "A": "£1,514.75",
        "B": "£1,767.21",
        "C": "£2,019.67",
        "D": "£2,272.12",
        "E": "£2,777.04",
        "F": "£3,281.95",
        "G": "£3,786.87",
        "H": "£4,544.24",
    }

    YES_VALUES = {"yes", "y", "yeah", "yep", "ok", "okay", "correct"}
    NO_VALUES = {"no", "n", "nope", "not really"}

    def __init__(self, connector) -> None:
        self.connector = connector

    # -------------------------------------------------------------------------
    # Public entry points for Council Tax payment flow
    # -------------------------------------------------------------------------
    def start_payment_flow(self, session: Dict[str, Any]) -> Dict[str, Any]:
        session["pending_action"] = "awaiting_council_tax_amount_confirmation"

        return {
            "reply": "Do you know your Council Tax amount? Please reply yes or no.",
            "messages": [
                {
                    "reply": "Do you know your Council Tax amount? Please reply yes or no."
                }
            ],
        }

    def handle_amount_confirmation(
        self,
        user_input: str,
        session: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = self._normalize_choice(user_input)

        if normalized in self.YES_VALUES:
            session["pending_action"] = None
            return self._build_payment_guidance_messages()

        if normalized in self.NO_VALUES:
            session["pending_action"] = "awaiting_council_tax_band_confirmation"
            return {
                "reply": "Do you know your house band? Please reply yes or no.",
                "messages": [
                    {
                        "reply": "Do you know your house band? Please reply yes or no."
                    }
                ],
            }

        return {
            "reply": "Please reply yes or no. Do you know your Council Tax amount?",
            "messages": [
                {
                    "reply": "Please reply yes or no. Do you know your Council Tax amount?"
                }
            ],
        }

    def handle_band_confirmation(
        self,
        user_input: str,
        session: Dict[str, Any],
    ) -> Dict[str, Any]:
        normalized = self._normalize_choice(user_input)

        if normalized in self.YES_VALUES:
            session["pending_action"] = "awaiting_council_tax_band_input"
            return {
                "reply": "Please enter your Council Tax band letter, from A to H.",
                "messages": [
                    {
                        "reply": "Please enter your Council Tax band letter, from A to H."
                    }
                ],
            }

        if normalized in self.NO_VALUES:
            session["pending_action"] = "awaiting_council_tax_postcode"
            return {
                "reply": "No problem. I can help you check your Council Tax band. Please enter your postcode.",
                "messages": [
                    {
                        "reply": "No problem. I can help you check your Council Tax band. Please enter your postcode."
                    }
                ],
            }

        return {
            "reply": "Please reply yes or no. Do you know your house band?",
            "messages": [
                {
                    "reply": "Please reply yes or no. Do you know your house band?"
                }
            ],
        }

    def handle_band_input(
        self,
        user_input: str,
        session: Dict[str, Any],
    ) -> Dict[str, Any]:
        band = user_input.strip().upper()

        if band not in self.BAND_CHARGES_2026_27:
            return {
                "reply": "Please enter a valid Council Tax band letter from A to H.",
                "messages": [
                    {
                        "reply": "Please enter a valid Council Tax band letter from A to H."
                    }
                ],
            }

        session["pending_action"] = None
        return self._build_manual_band_messages(band)

    # -------------------------------------------------------------------------
    # Postcode step
    # -------------------------------------------------------------------------
    def handle_postcode(self, user_input: str, session: Dict[str, Any]) -> Dict[str, Any]:
        postcode = user_input.strip().upper()

        if not is_valid_uk_postcode(postcode):
            return {
                "reply": "Please enter a valid UK postcode, for example BD7 3AB."
            }

        try:
            addresses = self.connector.lookup_addresses(postcode)
        except Exception as e:
            return {
                "reply": f"I could not look up that postcode right now. Error: {str(e)}"
            }

        if not addresses:
            return {
                "reply": f"I could not find any properties for postcode {postcode}. Please check it and try again."
            }

        session["pending_action"] = "awaiting_council_tax_address_selection"
        session["council_tax_addresses"] = addresses
        session["council_tax_postcode"] = postcode

        return {
            "reply": "I found these properties. Please choose your address.",
            "response_type": "address_list",
            "addresses": addresses,
            "messages": [
                {
                    "reply": "I found these properties. Please choose your address."
                }
            ],
        }

    # -------------------------------------------------------------------------
    # Address selection step
    # -------------------------------------------------------------------------
    def handle_address_selection(self, user_input: str, session: Dict[str, Any]) -> Dict[str, Any]:
        addresses = session.get("council_tax_addresses", [])

        if not addresses:
            session["pending_action"] = None
            return {
                "reply": "I could not find the saved address list. Please enter your postcode again."
            }

        selected = self._match_selected_address(user_input, addresses)

        if not selected:
            return {
                "reply": "I could not match that address. Please choose one of the listed addresses.",
                "response_type": "address_list",
                "addresses": addresses,
                "messages": [
                    {
                        "reply": "I could not match that address. Please choose one of the listed addresses."
                    }
                ],
            }

        try:
            result = self.connector.get_band_for_address(selected)
        except Exception as e:
            return {
                "reply": f"I could not get the Council Tax band right now. Error: {str(e)}"
            }

        session["pending_action"] = None
        session["council_tax_addresses"] = []
        session["council_tax_postcode"] = None

        return self._build_council_tax_messages(result, selected)

    # -------------------------------------------------------------------------
    # Response builders
    # -------------------------------------------------------------------------
    def _build_payment_guidance_messages(self) -> Dict[str, Any]:
        message_1 = (
            "You can pay your Council Tax bill using Direct Debit or other available methods."
        )

        message_2 = (
            "If you are struggling to pay, support may be available from the council."
        )

        message_3 = (
            "You can also:<br>"
            "• Request a copy of your bill<br>"
            "• Sign up for paperless billing<br>"
            "• Appeal your Council Tax band<br><br>"
            "👉 For full details, visit:<br>"
            f'<a href="{self.BILL_INFO_URL}" target="_blank" rel="noopener noreferrer">{self.BILL_INFO_URL}</a>'
        )

        return {
            "reply": message_1,
            "messages": [
                {"reply": message_1},
                {"reply": message_2},
                {"reply": message_3},
            ],
        }

    def _build_manual_band_messages(self, band: str) -> Dict[str, Any]:
        charge = self.BAND_CHARGES_2026_27.get(band)

        message_1 = (
            f'Your property is in <strong>Band {band}</strong>.'
        )

        if charge:
            message_2 = (
                f'For <strong>2026–2027</strong>, the annual Council Tax charge for '
                f'<strong>Band {band}</strong> in Bradford is approximately '
                f'<strong>{charge}</strong> (excluding parish precepts).'
            )
        else:
            message_2 = (
                f'I could not find the annual charge for <strong>Band {band}</strong> right now.'
            )

        message_3 = (
            "You can pay your bill using <strong>Direct Debit</strong> or other available methods.<br>"
            "If you are struggling to pay, support may be available from the council.<br>"
            "You can also:<br>"
            "• Request a copy of your bill<br>"
            "• Sign up for paperless billing<br>"
            "• Appeal your Council Tax band<br><br>"
            "👉 For full details, visit:<br>"
            f'<a href="{self.BILL_INFO_URL}" target="_blank" rel="noopener noreferrer">{self.BILL_INFO_URL}</a>'
        )

        return {
            "reply": self._strip_html(message_1),
            "messages": [
                {"reply": message_1},
                {"reply": message_2},
                {"reply": message_3},
            ],
            "result": {
                "band": band,
                "annual_charge": charge,
            },
        }

    def _build_council_tax_messages(
        self,
        result: Dict[str, Any],
        selected: Dict[str, Any],
    ) -> Dict[str, Any]:
        address = str(
            result.get("address") or selected.get("label", "that property")
        ).strip()

        band = str(result.get("band", "")).strip().upper()
        local_authority = str(result.get("local_authority", "")).strip()

        if not band:
            return {
                "reply": f"I found the property {address}, but I could not confirm the Council Tax band.",
                "messages": [
                    {
                        "reply": f"I found the property <strong>{address}</strong>, but I could not confirm the Council Tax band."
                    }
                ],
                "result": result,
            }

        charge = self.BAND_CHARGES_2026_27.get(band)

        message_1 = (
            f'The Council Tax band for <strong>{address}</strong> '
            f'is <strong>Band {band}</strong>.'
        )

        if charge:
            message_2 = (
                f'For <strong>2026–2027</strong>, a property in '
                f'<strong>Band {band}</strong> in Bradford has an annual '
                f'Council Tax charge of approximately <strong>{charge}</strong> '
                f'(excluding parish precepts).'
            )
        else:
            message_2 = (
                f'The amount you pay depends on your property band. '
                f'Your selected property is in <strong>Band {band}</strong>.'
            )

        extra_lines = []

        if local_authority:
            extra_lines.append(
                f'• Local authority: <strong>{local_authority}</strong>'
            )

        extra_lines.extend(
            [
                '• You can pay your bill using <strong>Direct Debit</strong> or other available methods',
                '• If you are struggling to pay, support may be available from the council',
                '• You can request a copy of your bill',
                '• You can sign up for paperless billing',
                '• You can appeal your Council Tax band if needed',
            ]
        )

        message_3 = (
            "<br>".join(extra_lines)
            + "<br><br>👉 For full details, visit:<br>"
            + (
                f'<a href="{self.BILL_INFO_URL}" target="_blank" '
                f'rel="noopener noreferrer">{self.BILL_INFO_URL}</a>'
            )
        )

        messages = [
            {"reply": message_1},
            {"reply": message_2},
            {"reply": message_3},
        ]

        return {
            "reply": self._strip_html(message_1),
            "messages": messages,
            "result": result,
        }

    # -------------------------------------------------------------------------
    # Address matching
    # -------------------------------------------------------------------------
    def _match_selected_address(
        self,
        user_input: str,
        addresses: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        raw = user_input.strip()
        lowered = raw.lower()

        if raw.isdigit():
            index = int(raw) - 1
            if 0 <= index < len(addresses):
                return addresses[index]

        for address in addresses:
            label = str(address.get("label", "")).strip()
            if label.lower() == lowered:
                return address

        for address in addresses:
            address_id = str(address.get("id", "")).strip().lower()
            if address_id and address_id == lowered:
                return address

        for address in addresses:
            label = str(address.get("label", "")).strip().lower()
            if lowered and lowered in label:
                return address

        return None

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------
    def _normalize_choice(self, value: str) -> str:
        return " ".join((value or "").strip().lower().split())

    def _strip_html(self, value: str) -> str:
        return re.sub(r"<[^>]+>", "", value or "").strip()