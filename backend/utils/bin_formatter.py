"""
Formats bin collection dates and guidance into styled HTML multi-bubble responses.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


WASTE_PAGE_URL   = "https://www.bradford.gov.uk/recycling-and-waste/recycling-and-waste/"
BIN_DATES_URL    = (
    "https://www.bradford.gov.uk/recycling-and-waste/bin-collections/"
    "check-your-bin-collection-dates/"
)
RECYCLING_URL    = "https://www.bradford.gov.uk/recycling-and-waste/recycling-and-waste/"
CONTACT_URL      = "https://www.bradford.gov.uk/contact/"

# Bin type colour + emoji config
_BIN_CONFIG: Dict[str, Dict[str, str]] = {
    "general waste":  {"emoji": "&#x1F5D1;", "color": "#1a1a1a", "bg": "#f5f5f5", "border": "#888"},
    "recycling waste":{"emoji": "&#x267B;",  "color": "#1a5c2e", "bg": "#f0fff4", "border": "#6fcf97"},
    "garden waste":   {"emoji": "&#x1F33F;", "color": "#4a3200", "bg": "#fffbeb", "border": "#f59e0b"},
    "next collection":{"emoji": "&#x1F4C5;", "color": "#1a3a7a", "bg": "#eef4ff", "border": "#3b82f6"},
}

_DEFAULT_CONFIG = {"emoji": "&#x1F5D1;", "color": "#333", "bg": "#f9f9f9", "border": "#ccc"}


def _bin_config(bin_type: str) -> Dict[str, str]:
    return _BIN_CONFIG.get(bin_type.lower().strip(), _DEFAULT_CONFIG)


def format_bin_date_messages(
    address_label: str,
    collections: List[Dict[str, str]],
    next_collection: str = "",
    garden_message: str = "",
) -> List[Dict[str, Any]]:
    """
    Format live bin collection dates into styled HTML bubbles.

    Returns a list of {"reply": "<html>", "isHtml": True} dicts.
    """
    messages: List[Dict[str, Any]] = []

    # ── Bubble 1: Address confirmation header ─────────────────────────────────
    addr_display = address_label.strip() if address_label else "your address"
    bubble_1 = (
        f'<div style="background:#1a3a7a;color:#fff;padding:14px 18px;'
        f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
        f'<strong>Bin Collection Dates</strong>'
        f'</div>'
        f'<div style="background:#eef4ff;border:1px solid #b8d4f5;'
        f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
        f'<p style="margin:0 0 10px 0;font-size:0.9em;color:#444;">'
        f'Address: <strong>{addr_display}</strong>'
        f'</p>'
    )

    # Group collections by type
    general_dates: List[str] = []
    recycling_dates: List[str] = []
    garden_dates: List[str] = []

    for item in collections:
        bin_type = item.get("bin_type", "").lower().strip()
        date = item.get("date", "").strip()
        if not date or bin_type == "next collection":
            continue
        if "general" in bin_type:
            general_dates.append(date)
        elif "recycling" in bin_type:
            recycling_dates.append(date)
        elif "garden" in bin_type:
            garden_dates.append(date)

    # Build collection rows in bubble 1
    rows = []
    if general_dates:
        dates_str = " &amp; ".join(general_dates[:3])
        cfg = _bin_config("general waste")
        rows.append(
            f'<div style="display:flex;align-items:flex-start;gap:10px;'
            f'margin-bottom:10px;padding:10px;background:{cfg["bg"]};'
            f'border-left:4px solid {cfg["border"]};border-radius:6px;">'
            f'<span style="font-size:1.4em;">{cfg["emoji"]}</span>'
            f'<div><strong style="color:{cfg["color"]};">General Waste (Black Bin)</strong>'
            f'<br><span style="color:#333;">{dates_str}</span></div>'
            f'</div>'
        )
    if recycling_dates:
        dates_str = " &amp; ".join(recycling_dates[:3])
        cfg = _bin_config("recycling waste")
        rows.append(
            f'<div style="display:flex;align-items:flex-start;gap:10px;'
            f'margin-bottom:10px;padding:10px;background:{cfg["bg"]};'
            f'border-left:4px solid {cfg["border"]};border-radius:6px;">'
            f'<span style="font-size:1.4em;">{cfg["emoji"]}</span>'
            f'<div><strong style="color:{cfg["color"]};">Recycling (Blue/Green Bin)</strong>'
            f'<br><span style="color:#333;">{dates_str}</span></div>'
            f'</div>'
        )
    if garden_dates:
        dates_str = " &amp; ".join(garden_dates[:3])
        cfg = _bin_config("garden waste")
        rows.append(
            f'<div style="display:flex;align-items:flex-start;gap:10px;'
            f'margin-bottom:10px;padding:10px;background:{cfg["bg"]};'
            f'border-left:4px solid {cfg["border"]};border-radius:6px;">'
            f'<span style="font-size:1.4em;">{cfg["emoji"]}</span>'
            f'<div><strong style="color:{cfg["color"]};">Garden Waste (Brown Bin)</strong>'
            f'<br><span style="color:#333;">{dates_str}</span></div>'
            f'</div>'
        )

    if rows:
        bubble_1 += "".join(rows)
    elif next_collection:
        bubble_1 += (
            f'<p style="margin:0;color:#333;">'
            f'&#x1F4C5; <strong>Next collection:</strong> {next_collection}</p>'
        )
    else:
        bubble_1 += '<p style="margin:0;color:#555;">No upcoming dates found.</p>'

    bubble_1 += '</div>'
    messages.append({"reply": bubble_1, "isHtml": True})

    # ── Bubble 2: Garden waste note (if any) + key reminders ──────────────────
    reminder_parts = []
    if garden_message:
        reminder_parts.append(
            f'<p style="margin:0 0 10px;padding:10px;background:#fffbeb;'
            f'border-left:4px solid #f59e0b;border-radius:6px;color:#92400e;">'
            f'&#x1F33F; {garden_message}</p>'
        )

    reminder_parts.append(
        '<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:12px 14px;">'
        '<p style="margin:0 0 8px;font-weight:700;color:#1e293b;">&#x1F4CB; Key reminders:</p>'
        '<ul style="margin:0;padding-left:18px;color:#334155;line-height:1.7;">'
        '<li>Bins are collected every <strong>other week</strong></li>'
        '<li>Put your bin out by <strong>6:30am</strong> on collection day</li>'
        '<li>Collections run <strong>Tuesday to Friday</strong>, 6:30am&ndash;5:15pm</li>'
        '<li>If your bin is missed, wait <strong>2 working days</strong> before reporting</li>'
        '</ul>'
        '</div>'
    )

    bubble_2 = (
        f'<div style="font-family:inherit;">'
        + "".join(reminder_parts)
        + '</div>'
    )
    messages.append({"reply": bubble_2, "isHtml": True})

    # ── Bubble 3: Links ───────────────────────────────────────────────────────
    bubble_3 = (
        f'<div style="background:#006b3c;color:#fff;padding:14px 18px;'
        f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
        f'<strong>Useful Links</strong>'
        f'</div>'
        f'<div style="background:#f0fff7;border:1px solid #9de0bc;'
        f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
        f'<p style="margin:0 0 8px 0;">'
        f'&#x267B;&nbsp;<a href="{WASTE_PAGE_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="color:#006b3c;font-weight:600;">Recycling &amp; Waste Services &rarr;</a>'
        f'</p>'
        f'<p style="margin:0 0 8px 0;">'
        f'&#x1F4C5;&nbsp;<a href="{BIN_DATES_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="color:#006b3c;font-weight:600;">Check your bin dates online &rarr;</a>'
        f'</p>'
        f'<p style="margin:10px 0 0;font-size:0.87em;color:#555;">'
        f'&#x260E;&nbsp;Report missed bins: <strong>01274 431000</strong>'
        f'</p>'
        f'</div>'
    )
    messages.append({"reply": bubble_3, "isHtml": True})

    return messages


def format_bin_fallback_messages(address_label: str = "") -> List[Dict[str, Any]]:
    """
    Styled fallback when live dates can't be fetched.
    Still shows useful info and a direct link.
    """
    addr_line = (
        f'<p style="margin:0 0 10px;font-size:0.9em;color:#444;">'
        f'Address: <strong>{address_label}</strong></p>'
        if address_label else ""
    )

    bubble_1 = (
        f'<div style="background:#1a3a7a;color:#fff;padding:14px 18px;'
        f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
        f'<strong>Bin Collection Dates</strong>'
        f'</div>'
        f'<div style="background:#eef4ff;border:1px solid #b8d4f5;'
        f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
        f'{addr_line}'
        f'<p style="margin:0 0 10px;">I was unable to fetch your live bin dates right now, '
        f'but you can check them directly on the Bradford Council website:</p>'
        f'<p style="margin:0 0 10px;font-weight:700;">'
        f'<a href="{BIN_DATES_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="color:#1a3a7a;">Check your bin collection dates &rarr;</a>'
        f'</p>'
        f'</div>'
    )

    bubble_2 = (
        f'<div style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:12px;padding:14px 18px;">'
        f'<p style="margin:0 0 8px;font-weight:700;color:#1e293b;">&#x1F4CB; General information:</p>'
        f'<ul style="margin:0;padding-left:18px;color:#334155;line-height:1.7;">'
        f'<li>Bins are collected every <strong>other week</strong></li>'
        f'<li>Put your bin out by <strong>6:30am</strong> on collection day</li>'
        f'<li>Collections run <strong>Tuesday to Friday</strong></li>'
        f'<li>&#x267B; Recycling and general waste alternate weeks</li>'
        f'<li>&#x1F33F; Garden waste requires a <strong>subscription</strong></li>'
        f'</ul>'
        f'<p style="margin:12px 0 0;font-size:0.87em;color:#555;">'
        f'&#x260E;&nbsp;Report missed bins: <strong>01274 431000</strong>'
        f'</p>'
        f'</div>'
    )

    return [
        {"reply": bubble_1, "isHtml": True},
        {"reply": bubble_2, "isHtml": True},
    ]


def format_recycling_guidance_messages(answer: str, item_name: str = "") -> List[Dict[str, Any]]:
    """Format recycling guidance as styled HTML bubbles."""
    title = f"Recycling Guidance{f' — {item_name.title()}' if item_name else ''}"

    bubble_1 = (
        f'<div style="background:#1a5c2e;color:#fff;padding:14px 18px;'
        f'border-radius:12px 12px 4px 4px;margin-bottom:4px;">'
        f'<strong>{title}</strong>'
        f'</div>'
        f'<div style="background:#f0fff4;border:1px solid #9de0bc;'
        f'border-radius:4px 4px 12px 12px;padding:14px 18px;">'
        f'<p style="margin:0;line-height:1.7;color:#1a1a1a;">{answer}</p>'
        f'</div>'
    )

    bubble_2 = (
        f'<div style="background:#f0fff7;border:1px solid #9de0bc;border-radius:12px;padding:14px 18px;">'
        f'<p style="margin:0 0 8px;font-weight:700;color:#1a5c2e;">&#x1F517; More information:</p>'
        f'<p style="margin:0 0 6px;">'
        f'<a href="{RECYCLING_URL}" target="_blank" rel="noopener noreferrer" '
        f'style="color:#1a5c2e;font-weight:600;">'
        f'Bradford Recycling &amp; Waste guide &rarr;</a>'
        f'</p>'
        f'<p style="margin:6px 0 0;font-size:0.87em;color:#555;">'
        f'&#x260E;&nbsp;Recycling enquiries: <strong>01274 431000</strong>'
        f'</p>'
        f'</div>'
    )

    return [
        {"reply": bubble_1, "isHtml": True},
        {"reply": bubble_2, "isHtml": True},
    ]
