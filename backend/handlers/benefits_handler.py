from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.council_connectors.benefits_connector import BenefitsConnector


class BenefitsHandler:
    """
    Multi-step flow handler for the Turn2Us benefits calculator integration.

    Flow:
      start_flow()           -> sets pending_action = "awaiting_benefits_age_group"
      handle_age_group()     -> sets pending_action = "awaiting_benefits_housing_type"
      handle_housing_type()  -> clears pending_action, returns 3-bubble result
    """

    AGE_GROUP_MAP: Dict[str, str] = {
        "working": "working",
        "working age": "working",
        "working-age": "working",
        "work": "working",
        "under 66": "working",
        "employed": "working",
        "pension": "pension",
        "pension age": "pension",
        "pension-age": "pension",
        "pensioner": "pension",
        "retired": "pension",
        "retirement": "pension",
        "state pension": "pension",
        "66": "pension",
        "over 66": "pension",
    }

    HOUSING_MAP: Dict[str, str] = {
        "private": "private",
        "private landlord": "private",
        "private renting": "private",
        "private rent": "private",
        "renting privately": "private",
        "privately": "private",
        "council": "council",
        "council house": "council",
        "housing association": "council",
        "social housing": "council",
        "social": "council",
        "renting": "council",
        "rent": "council",
        "ha tenant": "council",
        "own": "own",
        "owned": "own",
        "owner": "own",
        "mortgage": "own",
        "homeowner": "own",
        "home owner": "own",
        "own home": "own",
        "owning": "own",
        "i own": "own",
    }

    def __init__(self, connector: BenefitsConnector) -> None:
        self.connector = connector

    # -------------------------------------------------------------------------
    # Flow entry points
    # -------------------------------------------------------------------------

    def start_flow(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Start the benefits calculator qualifying flow."""
        session["pending_action"] = "awaiting_benefits_age_group"
        session["benefits_age_group"] = None
        session["benefits_housing_type"] = None

        intro = (
            "I can help you find out what benefits support you may be entitled to "
            "and link you to the <strong>Turn2Us Benefits Calculator</strong> for a full, "
            "personalised calculation."
        )

        question = (
            "To get started, are you <strong>working-age</strong> (under 66) "
            "or <strong>pension-age</strong> (66 or over)?<br>"
            "Please reply <strong>working</strong> or <strong>pension</strong>."
        )

        return {
            "reply": "I can help you find out what benefits you may be entitled to.",
            "messages": [
                {"reply": intro},
                {"reply": question},
            ],
        }

    def handle_age_group(self, user_input: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the age group response (working / pension)."""
        lowered = user_input.strip().lower()
        age_group = self._match_key(lowered, self.AGE_GROUP_MAP)

        if not age_group:
            return {
                "reply": "Please reply working or pension.",
                "messages": [
                    {
                        "reply": (
                            "I did not quite catch that. "
                            "Are you <strong>working-age</strong> (under 66) "
                            "or <strong>pension-age</strong> (66 or over)?<br>"
                            "Please reply <strong>working</strong> or <strong>pension</strong>."
                        )
                    }
                ],
            }

        session["benefits_age_group"] = age_group
        session["pending_action"] = "awaiting_benefits_housing_type"

        question = (
            "Thank you. What is your current housing situation?<br><br>"
            "&#x2022; <strong>private</strong> &mdash; renting from a private landlord<br>"
            "&#x2022; <strong>council</strong> &mdash; renting from the council or housing association<br>"
            "&#x2022; <strong>own</strong> &mdash; owner-occupier or mortgage<br><br>"
            "Please reply <strong>private</strong>, <strong>council</strong>, or <strong>own</strong>."
        )

        return {
            "reply": "Thank you. What is your housing situation?",
            "messages": [{"reply": question}],
        }

    def handle_housing_type(self, user_input: str, session: Dict[str, Any]) -> Dict[str, Any]:
        """Handle the housing type response and produce the final guidance."""
        lowered = user_input.strip().lower()
        housing_type = self._match_key(lowered, self.HOUSING_MAP)

        if not housing_type:
            return {
                "reply": "Please reply private, council, or own.",
                "messages": [
                    {
                        "reply": (
                            "I did not quite catch that. Please reply:<br>"
                            "&#x2022; <strong>private</strong> &mdash; renting from a private landlord<br>"
                            "&#x2022; <strong>council</strong> &mdash; council or housing association tenant<br>"
                            "&#x2022; <strong>own</strong> &mdash; homeowner or mortgage"
                        )
                    }
                ],
            }

        session["benefits_housing_type"] = housing_type
        session["pending_action"] = None

        age_group = session.get("benefits_age_group", "working")
        overview = self.connector.get_eligibility_overview(age_group, housing_type)
        return self._build_result_messages(overview)

    # -------------------------------------------------------------------------
    # Response builder
    # -------------------------------------------------------------------------

    def _build_result_messages(self, overview: Dict[str, Any]) -> Dict[str, Any]:
        age_label = "pension-age" if overview["is_pension"] else "working-age"
        housing_label_map = {
            "private": "private renter",
            "council": "council / HA tenant",
            "own": "owner-occupier",
        }
        housing_label = housing_label_map.get(overview["housing_type"], overview["housing_type"])

        # ---- Bubble 1: Housing Benefit eligibility ----
        hb_icon = "&#x1F3E0;"
        bubble_1 = (
            f'<div style="background:#1a4a7a;color:#fff;padding:14px 18px;'
            f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
            f'<span style="font-size:1.25em;">{hb_icon}</span>'
            f'<strong style="margin-left:8px;">Housing Benefit Eligibility</strong>'
            f'</div>'
            f'<div style="background:#f0f7ff;border:1px solid #b8d4f5;'
            f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
            f'<p style="margin:0 0 10px 0;color:#555;font-size:0.9em;">'
            f'Based on: <strong>{age_label}</strong> &middot; <strong>{housing_label}</strong>'
            f'</p>'
            f'<p style="margin:0 0 10px 0;">{overview["housing_benefit_text"]}</p>'
        )

        if overview["extra_tip"]:
            bubble_1 += (
                f'<p style="margin:0;padding:10px;background:#ddeeff;'
                f'border-left:4px solid #1a4a7a;border-radius:4px;'
                f'color:#1a4a7a;font-size:0.92em;">'
                f'<strong>Tip:</strong> {overview["extra_tip"]}'
                f'</p>'
            )

        bubble_1 += (
            f'<p style="margin:10px 0 0 0;">'
            f'<a href="{self.connector.BRADFORD_HOUSING_BENEFIT_URL}" '
            f'target="_blank" rel="noopener noreferrer" style="color:#1a4a7a;">'
            f'Apply for Housing Benefit &rarr;</a>'
            f'</p>'
            f'</div>'
        )

        # ---- Bubble 2: Council Tax Reduction ----
        ctr_icon = "&#x1F4CB;"
        bubble_2 = (
            f'<div style="background:#1a4a7a;color:#fff;padding:14px 18px;'
            f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
            f'<span style="font-size:1.25em;">{ctr_icon}</span>'
            f'<strong style="margin-left:8px;">Council Tax Reduction (CTR)</strong>'
            f'</div>'
            f'<div style="background:#f0f7ff;border:1px solid #b8d4f5;'
            f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
            f'<p style="margin:0 0 12px 0;">{overview["ctr_text"]}</p>'
            f'<p style="margin:0 0 6px 0;font-weight:600;">To apply for CTR in Bradford:</p>'
            f'<p style="margin:0;">'
            f'<a href="{self.connector.BRADFORD_CTR_URL}" '
            f'target="_blank" rel="noopener noreferrer" style="color:#1a4a7a;">'
            f'{self.connector.BRADFORD_CTR_URL}</a>'
            f'</p>'
            f'</div>'
        )

        # ---- Bubble 3: Turn2Us full calculator + Bradford contact ----
        calc_url = self.connector.TURN2US_URL
        bubble_3 = (
            f'<div style="background:#006b3c;color:#fff;padding:14px 18px;'
            f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
            f'<span style="font-size:1.25em;">&#x1F4CA;</span>'
            f'<strong style="margin-left:8px;">Full Benefits Calculator &mdash; Turn2Us</strong>'
            f'</div>'
            f'<div style="background:#f0fff7;border:1px solid #9de0bc;'
            f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
            f'<p style="margin:0 0 10px 0;">'
            f'For a <strong>full, personalised calculation</strong> of all benefits '
            f'you may be entitled to &mdash; including Universal Credit, PIP, '
            f'Carer\'s Allowance, and more &mdash; use the '
            f'<strong>Turn2Us Benefits Calculator</strong>:'
            f'</p>'
            f'<p style="margin:0 0 16px 0;">'
            f'<a href="{calc_url}" target="_blank" rel="noopener noreferrer" '
            f'style="color:#006b3c;font-weight:700;word-break:break-all;">'
            f'Open Turn2Us Benefits Calculator &rarr;</a>'
            f'</p>'
            f'<hr style="border:none;border-top:1px solid #9de0bc;margin:10px 0;">'
            f'<p style="margin:0 0 6px 0;font-weight:600;">Bradford Council Benefits Team:</p>'
            f'<p style="margin:0 0 4px 0;">&#x260E;&nbsp;<strong>01274 432772</strong></p>'
            f'<p style="margin:0 0 4px 0;">&#x1F4E7;&nbsp;'
            f'<a href="mailto:benefits@bradford.gov.uk" style="color:#006b3c;">'
            f'benefits@bradford.gov.uk</a></p>'
            f'<p style="margin:6px 0 0 0;">'
            f'<a href="{self.connector.BRADFORD_BENEFITS_URL}" '
            f'target="_blank" rel="noopener noreferrer" style="color:#006b3c;">'
            f'Bradford Council Benefits page &rarr;</a>'
            f'</p>'
            f'</div>'
        )

        messages: List[Dict[str, Any]] = [
            {"reply": bubble_1, "isHtml": True},
            {"reply": bubble_2, "isHtml": True},
            {"reply": bubble_3, "isHtml": True},
        ]

        return {
            "reply": "Here is your benefits eligibility overview.",
            "messages": messages,
        }

    # -------------------------------------------------------------------------
    # Utility
    # -------------------------------------------------------------------------

    def _match_key(self, text: str, mapping: Dict[str, str]) -> Optional[str]:
        """Match text against a mapping dict; exact first, then substring."""
        if text in mapping:
            return mapping[text]
        for key, value in mapping.items():
            if key in text:
                return value
        return None
