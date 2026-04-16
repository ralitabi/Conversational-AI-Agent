"""
Formats benefits FAQ answers into visually appealing HTML multi-bubble responses.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# Bradford Council benefits URLs
_URLS: Dict[str, str] = {
    "housing_benefit_eligibility": "https://www.bradford.gov.uk/benefits/applying-for-benefits/housing-benefit-and-council-tax-reduction/",
    "apply_housing_benefit_ctr": "https://www.bradford.gov.uk/benefits/applying-for-benefits/housing-benefit-and-council-tax-reduction/",
    "discretionary_housing_payment": "https://www.bradford.gov.uk/benefits/housing-benefit-and-council-tax-reduction/discretionary-housing-payments/",
    "benefits_myinfo_access": "https://www.bradford.gov.uk/benefits/housing-benefit-and-council-tax-reduction/manage-your-housing-benefit-and-council-tax-reduction-claim-online/",
    "submit_benefit_evidence": "https://www.bradford.gov.uk/benefits/housing-benefit-and-council-tax-reduction/upload-supporting-evidence-for-a-housing-benefit-or-council-tax-reduction-claim/",
    "report_change_of_circumstances": "https://www.bradford.gov.uk/benefits/housing-benefit-and-council-tax-reduction/changes-in-your-circumstances/",
    "benefit_appeal_or_reconsideration": "https://www.bradford.gov.uk/benefits/housing-benefit-and-council-tax-reduction/appeals-and-reconsiderations/",
    "benefits_support_contact": "https://www.bradford.gov.uk/benefits/benefits/",
}

_DEFAULT_URL = "https://www.bradford.gov.uk/benefits/benefits/"

_ICONS: Dict[str, str] = {
    "housing_benefit_eligibility": "&#9989;",
    "apply_housing_benefit_ctr": "&#128203;",
    "discretionary_housing_payment": "&#128176;",
    "benefits_myinfo_access": "&#128272;",
    "submit_benefit_evidence": "&#128206;",
    "report_change_of_circumstances": "&#128260;",
    "benefit_appeal_or_reconsideration": "&#9878;",
    "benefits_support_contact": "&#128222;",
}

_TITLES: Dict[str, str] = {
    "housing_benefit_eligibility": "Housing Benefit &amp; Council Tax Reduction &mdash; Eligibility",
    "apply_housing_benefit_ctr": "How to Apply for Housing Benefit / CTR",
    "discretionary_housing_payment": "Discretionary Housing Payment (DHP)",
    "benefits_myinfo_access": "Managing Your Claim Online",
    "submit_benefit_evidence": "Submitting Evidence for Your Claim",
    "report_change_of_circumstances": "Reporting a Change of Circumstances",
    "benefit_appeal_or_reconsideration": "Appealing or Challenging a Benefits Decision",
    "benefits_support_contact": "Contact the Benefits Team",
}

_BULLET = re.compile(r"^[\u2022\-\*\d+\.]")
_RAW_URL = re.compile(r"(https?://[^\s<>\"']+)")


def _linkify(text: str) -> str:
    """Convert bare URLs into clickable anchor tags."""
    return _RAW_URL.sub(
        r'<a href="\1" target="_blank" rel="noopener noreferrer" '
        r'style="color:#0f4ca3;font-weight:600;text-decoration:underline">\1</a>',
        text,
    )


def _lines_to_html(lines: List[str]) -> str:
    """Convert lines into either a <ul> list or <p> paragraphs."""
    bullet_count = sum(1 for l in lines if _BULLET.match(l))
    if bullet_count >= 2:
        items = "".join(
            f'<li style="margin-bottom:5px;line-height:1.6">{_linkify(l.lstrip(chr(8226) + "-* "))}</li>'
            for l in lines
            if l.strip()
        )
        return (
            '<ul style="margin:8px 0 0 0;padding-left:20px;color:#334155">'
            + items
            + "</ul>"
        )

    return "".join(
        f'<p style="margin:5px 0;line-height:1.6;color:#334155">{_linkify(l)}</p>'
        for l in lines
        if l.strip()
    )


def _split_answer(text: str) -> List[str]:
    """
    Split answer text into 2-3 logical parts.
    Prefer splitting on double newlines; fall back to line-count halving.
    """
    raw = re.split(r"\n{2,}", text.strip())
    parts = [p.strip() for p in raw if p.strip()]

    if len(parts) == 1:
        lines = [l.strip() for l in text.strip().splitlines() if l.strip()]
        if len(lines) > 5:
            mid = len(lines) // 2
            parts = ["\n".join(lines[:mid]), "\n".join(lines[mid:])]

    return parts[:3]


def format_benefits_messages(
    answer: str,
    intent: Optional[str] = None,
    source_url: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Convert a plain-text benefits FAQ answer into 2-4 HTML message bubbles.

    Returns a list of ``{"reply": "<html>"}`` dicts ready to be placed in the
    ``messages`` array of an API response.
    """
    if not answer or not answer.strip():
        return [
            {
                "reply": (
                    "I could not find a specific answer for that. "
                    "Please contact the benefits team on "
                    '<strong>01274 432772</strong> or email '
                    '<a href="mailto:benefits@bradford.gov.uk" '
                    'style="color:#0f4ca3;text-decoration:underline">'
                    "benefits@bradford.gov.uk</a>."
                )
            }
        ]

    icon = _ICONS.get(intent or "", "&#8505;")
    title = _TITLES.get(intent or "", "Benefits Information")
    url = source_url or _URLS.get(intent or "", _DEFAULT_URL)

    parts = _split_answer(answer)
    messages: List[Dict[str, Any]] = []

    # ── Bubble 1: header card + first content block ────────────────────────
    first_html = _lines_to_html([l.strip() for l in parts[0].splitlines() if l.strip()])
    messages.append(
        {
            "reply": (
                '<div style="font-family:inherit">'
                '<div style="background:#eef4ff;border-left:4px solid #0f4ca3;'
                "border-radius:8px;padding:10px 14px;margin-bottom:12px;"
                'display:flex;align-items:center;gap:8px">'
                f'<span style="font-size:1.15em">{icon}</span>'
                f'<strong style="color:#123b7a;font-size:0.97em">{title}</strong>'
                "</div>"
                f'<div style="font-size:0.95em">{first_html}</div>'
                "</div>"
            )
        }
    )

    # ── Bubble 2+ : remaining content parts ───────────────────────────────
    for part in parts[1:]:
        part_html = _lines_to_html([l.strip() for l in part.splitlines() if l.strip()])
        messages.append(
            {
                "reply": (
                    f'<div style="font-family:inherit;font-size:0.95em">{part_html}</div>'
                )
            }
        )

    # ── Final bubble: action links ─────────────────────────────────────────
    messages.append(
        {
            "reply": (
                '<div style="font-family:inherit">'
                '<div style="background:#f0fdf4;border:1px solid #bbf7d0;'
                "border-radius:8px;padding:10px 14px;margin-bottom:10px;"
                'display:inline-block">'
                '<span style="font-size:0.9em;color:#166534">'
                "&#128279;&nbsp;"
                f'<a href="{url}" target="_blank" rel="noopener noreferrer" '
                'style="color:#166534;font-weight:600;text-decoration:underline">'
                "View on Bradford Council website</a>"
                "</span>"
                "</div>"
                '<p style="margin:8px 0 0;font-size:0.85em;color:#64748b;line-height:1.6">'
                "&#128222;&nbsp;Need help? Call "
                '<strong style="color:#1e293b">01274 432772</strong>'
                " or email&nbsp;"
                '<a href="mailto:benefits@bradford.gov.uk" '
                'style="color:#0f4ca3;font-weight:600;text-decoration:underline">'
                "benefits@bradford.gov.uk</a>"
                "</p>"
                "</div>"
            )
        }
    )

    return messages
