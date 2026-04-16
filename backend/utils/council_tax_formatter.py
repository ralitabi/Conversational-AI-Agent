"""
Formats council tax responses into styled HTML multi-bubble responses,
matching the visual style of benefits_formatter.py and bin_formatter.py.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


COUNCIL_TAX_URL   = "https://www.bradford.gov.uk/council-tax/council-tax/"
BAND_URL          = (
    "https://www.bradford.gov.uk/council-tax/council-tax-bands-and-appeals/"
    "council-tax-bands/"
)
PAYMENT_URL       = (
    "https://www.bradford.gov.uk/council-tax/paying-council-tax/"
    "ways-to-pay-council-tax/"
)
DISCOUNTS_URL     = (
    "https://www.bradford.gov.uk/council-tax/council-tax-discounts-and-exemptions/"
    "council-tax-discounts/"
)
ARREARS_URL       = (
    "https://www.bradford.gov.uk/council-tax/having-problems-paying/"
    "having-problems-paying-your-council-tax/"
)
APPEAL_URL        = (
    "https://www.bradford.gov.uk/council-tax/council-tax-bands-and-appeals/"
    "appeal-against-your-council-tax-band/"
)

_CT_COLOR   = "#1a4a7a"
_CT_LIGHT   = "#eef4ff"
_CT_BORDER  = "#b8d4f5"

_ICONS: Dict[str, str] = {
    "find_council_tax_band":           "",
    "check_council_tax_balance":       "",
    "check_council_tax_amount":        "",
    "council_tax_payment":             "",
    "council_tax_payment_methods":     "",
    "council_tax_payment_problem":     "",
    "apply_council_tax_discount":      "",
    "council_tax_general_discounts":   "",
    "report_move_council_tax":         "",
    "council_tax_change_details":      "",
    "council_tax_appeal":              "",
    "council_tax_arrears_help":        "",
    "council_tax_general_info":        "",
    "set_up_direct_debit":             "",
    "change_payment_date_or_instalments": "",
    "apply_student_discount":          "",
    "council_tax_reduction_support":   "",
    "empty_property_council_tax":      "",
    "contact_council_tax_team":        "",
}

_TITLES: Dict[str, str] = {
    "find_council_tax_band":           "Your Council Tax Band",
    "check_council_tax_balance":       "Council Tax Balance",
    "check_council_tax_amount":        "Council Tax Amounts by Band",
    "council_tax_payment":             "Paying Your Council Tax",
    "council_tax_payment_methods":     "Ways to Pay Council Tax",
    "council_tax_payment_problem":     "Problems Paying Council Tax",
    "apply_council_tax_discount":      "Single Person Discount",
    "council_tax_general_discounts":   "Council Tax Discounts &amp; Exemptions",
    "report_move_council_tax":         "Moving House &mdash; Council Tax",
    "council_tax_change_details":      "Update Your Council Tax Details",
    "council_tax_appeal":              "Appeal Your Council Tax Band",
    "council_tax_arrears_help":        "Help with Council Tax Arrears",
    "council_tax_general_info":        "About Council Tax",
    "set_up_direct_debit":             "Set Up a Direct Debit",
    "change_payment_date_or_instalments": "Payment Dates &amp; Instalments",
    "apply_student_discount":          "Student Council Tax Exemption",
    "council_tax_reduction_support":   "Council Tax Reduction (CTR)",
    "empty_property_council_tax":      "Empty Property Council Tax",
    "contact_council_tax_team":        "Contact the Council Tax Team",
}

_URLS: Dict[str, str] = {
    "find_council_tax_band":           BAND_URL,
    "check_council_tax_balance":       COUNCIL_TAX_URL,
    "check_council_tax_amount":        BAND_URL,
    "council_tax_payment":             PAYMENT_URL,
    "council_tax_payment_methods":     PAYMENT_URL,
    "council_tax_payment_problem":     ARREARS_URL,
    "apply_council_tax_discount":      DISCOUNTS_URL,
    "council_tax_general_discounts":   DISCOUNTS_URL,
    "report_move_council_tax":         COUNCIL_TAX_URL,
    "council_tax_change_details":      COUNCIL_TAX_URL,
    "council_tax_appeal":              APPEAL_URL,
    "council_tax_arrears_help":        ARREARS_URL,
    "council_tax_general_info":        COUNCIL_TAX_URL,
    "set_up_direct_debit":             PAYMENT_URL,
    "change_payment_date_or_instalments": PAYMENT_URL,
    "apply_student_discount":          DISCOUNTS_URL,
    "council_tax_reduction_support":   COUNCIL_TAX_URL,
    "empty_property_council_tax":      COUNCIL_TAX_URL,
    "contact_council_tax_team":        COUNCIL_TAX_URL,
}

_RAW_URL = re.compile(r"(https?://[^\s<>\"']+)")
_BULLET  = re.compile(r"^[\u2022\-\*\d+\.]")


def _linkify(text: str) -> str:
    return _RAW_URL.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer" '
        r'style="color:#0f4ca3;font-weight:600;text-decoration:underline">\1</a>',
        text,
    )


def _lines_to_html(lines: List[str]) -> str:
    bullet_count = sum(1 for ln in lines if _BULLET.match(ln))
    if bullet_count >= 2:
        items = "".join(
            f'<li style="margin-bottom:5px;line-height:1.6">{_linkify(ln.lstrip(chr(8226) + "-* "))}</li>'
            for ln in lines if ln.strip()
        )
        return (
            f'<ul style="margin:8px 0 0 0;padding-left:20px;color:#334155">{items}</ul>'
        )
    return "".join(
        f'<p style="margin:5px 0;line-height:1.6;color:#334155">{_linkify(ln)}</p>'
        for ln in lines if ln.strip()
    )


def _split_answer(text: str) -> List[str]:
    raw = re.split(r"\n{2,}", text.strip())
    parts = [p.strip() for p in raw if p.strip()]
    if len(parts) == 1:
        lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
        if len(lines) > 5:
            mid = len(lines) // 2
            parts = ["\n".join(lines[:mid]), "\n".join(lines[mid:])]
    return parts[:3]


def format_council_tax_messages(
    answer: str,
    intent: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a plain-text council tax FAQ answer into 2-4 styled HTML message bubbles.
    """
    if not answer or not answer.strip():
        return [{"reply": (
            "I could not find a specific answer for that. "
            "Please visit <a href='" + COUNCIL_TAX_URL + "' target='_blank' "
            "style='color:#0f4ca3;font-weight:600;text-decoration:underline'>"
            "Bradford Council Tax</a> or call "
            "<strong>01274 432345</strong>."
        )}]

    title = _TITLES.get(intent or "", "Council Tax Information")
    url   = source_url or _URLS.get(intent or "", COUNCIL_TAX_URL)

    parts = _split_answer(answer)
    messages: List[Dict[str, Any]] = []

    # ── Bubble 1: header card + first content block ───────────────────────────
    first_html = _lines_to_html([ln.strip() for ln in parts[0].splitlines() if ln.strip()])
    messages.append({"reply": (
        '<div style="font-family:inherit">'
        f'<div style="background:{_CT_LIGHT};border-left:4px solid {_CT_COLOR};'
        f'border-radius:8px;padding:10px 14px;margin-bottom:12px;">'
        f'<strong style="color:#123b7a;font-size:0.97em">{title}</strong>'
        f'</div>'
        f'<div style="font-size:0.95em">{first_html}</div>'
        f'</div>'
    )})

    # ── Bubble 2+ : remaining content parts ───────────────────────────────────
    for part in parts[1:]:
        part_html = _lines_to_html([ln.strip() for ln in part.splitlines() if ln.strip()])
        messages.append({"reply": (
            f'<div style="font-family:inherit;font-size:0.95em">{part_html}</div>'
        )})

    # ── Final bubble: action links ─────────────────────────────────────────────
    messages.append({"reply": (
        '<div style="font-family:inherit">'
        f'<div style="background:{_CT_LIGHT};border:1px solid {_CT_BORDER};'
        f'border-radius:8px;padding:10px 14px;margin-bottom:10px;display:inline-block">'
        f'<span style="font-size:0.9em;color:{_CT_COLOR}">'
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
        f'style="color:{_CT_COLOR};font-weight:600;text-decoration:underline">'
        f'View on Bradford Council website</a>'
        f'</span>'
        f'</div>'
        f'<p style="margin:8px 0 0;font-size:0.85em;color:#64748b;line-height:1.6">'
        f'Need help? Call '
        f'<strong style="color:#1e293b">01274 432345</strong>'
        f'</p>'
        f'</div>'
    )})

    return messages
