"""
HTML bubble formatters for library finder results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


_CATALOGUE_URL = "https://bradford.ent.sirsidynix.net.uk/client/en_GB/default"

_SERVICE_LABELS: Dict[str, str] = {
    "computers":           "Computers",
    "wifi":                "Free Wifi",
    "printing":            "Printing",
    "meeting_rooms":       "Meeting Rooms",
    "photocopier":         "Photocopier",
    "audiobooks":          "Audiobooks",
    "disabled_access":     "Disabled Access",
    "children_activities": "Children's Activities",
    "asian_language_books":"Asian Language Books",
    "local_studies":       "Local Studies",
    "archives":            "Archives",
    "home_library_service":"Home Library Service",
}

_DAY_ORDER = [
    "monday", "tuesday", "wednesday", "thursday",
    "friday", "saturday", "sunday",
]
_DAY_LABELS = {
    "monday": "Mon", "tuesday": "Tue", "wednesday": "Wed",
    "thursday": "Thu", "friday": "Fri", "saturday": "Sat", "sunday": "Sun",
}


def _distance_badge(miles: Optional[float]) -> str:
    if miles is None:
        return ""
    return (
        f'<span style="background:#f3f4f6;color:#374151;border-radius:4px;'
        f'padding:1px 6px;font-size:0.78em;">{miles} mi</span>'
    )


def _service_chip(service: str) -> str:
    label = _SERVICE_LABELS.get(service, service.replace("_", " ").title())
    return (
        f'<span style="background:#f3f4f6;color:#374151;border-radius:12px;'
        f'padding:2px 8px;font-size:0.78em;display:inline-block;margin:2px 2px 0 0;">'
        f'{label}</span>'
    )


def _hours_table(hours: Dict[str, Any]) -> str:
    if not hours:
        return ""
    rows = ""
    for day in _DAY_ORDER:
        value = hours.get(day)
        if value is None:
            time_str = "Closed"
            colour = "#9ca3af"
        else:
            time_str = str(value)
            colour = "#374151"
        label = _DAY_LABELS.get(day, day.title())
        rows += (
            f'<tr>'
            f'<td style="padding:2px 8px 2px 0;font-weight:600;color:#6b7280;font-size:0.82em;">{label}</td>'
            f'<td style="padding:2px 0;color:{colour};font-size:0.82em;">{time_str}</td>'
            f'</tr>'
        )
    return f'<table style="border-collapse:collapse;margin:4px 0;">{rows}</table>'


def format_library_search_results(
    libraries: List[Dict[str, Any]],
    query: str,
    postcode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build HTML message bubbles for a list of library search results."""
    if not libraries:
        return [
            {
                "reply": (
                    "No libraries found matching your search. "
                    "Try a different name, area (e.g. Bingley, Shipley), "
                    "or service type (computers / meeting rooms).<br><br>"
                    'You can also view all libraries at: '
                    '<a href="https://www.bradford.gov.uk/libraries/find-your-local-library/" '
                    'target="_blank">Bradford Libraries &#x2197;</a>'
                ),
                "isHtml": True,
            }
        ]

    count    = len(libraries)
    has_dist = any(lib.get("distance_miles") is not None for lib in libraries)
    dist_note = f" sorted by distance from <b>{postcode.upper()}</b>" if (has_dist and postcode) else ""

    intro = f"Found <b>{count} librar{'ies' if count != 1 else 'y'}</b> for <b>{query}</b>{dist_note}:"

    cards = ""
    for i, library in enumerate(libraries, start=1):
        name    = library.get("name", "Unknown Library")
        area    = library.get("area", "")
        address = library.get("address", "")
        phone   = library.get("phone") or ""
        dist    = _distance_badge(library.get("distance_miles"))
        url     = library.get("url", "")

        # Build a short hours summary (today not known, so show Mon-Sat range)
        hours = library.get("hours") or {}
        open_days = [_DAY_LABELS[d] for d in _DAY_ORDER if hours.get(d)]
        hours_summary = ", ".join(open_days) if open_days else "Contact library for hours"

        cards += f"""
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:11px 13px;margin-bottom:9px;background:#fff;">
  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px;">
    <span style="font-weight:700;font-size:0.95em;">{i}. {name}</span>
    {dist}
  </div>
  <div style="color:#6b7280;font-size:0.85em;">{area}</div>
  <div style="color:#6b7280;font-size:0.82em;margin-top:2px;">{address}</div>
  <div style="margin-top:4px;font-size:0.82em;color:#4b5563;">Open: {hours_summary}
    {f'&nbsp;&bull;&nbsp;<a href="{url}" target="_blank" style="color:#2563eb;">Details &#x2197;</a>' if url else ''}
  </div>
</div>"""

    footer = (
        '<p style="font-size:0.83em;color:#6b7280;margin-top:4px;">'
        'Type a <b>number</b> to see full details, or enter a new search.'
        f'&nbsp;<a href="https://www.bradford.gov.uk/libraries/find-your-local-library/" '
        f'target="_blank">View all libraries &#x2197;</a></p>'
    )

    return [{"reply": f"<p>{intro}</p>{cards}{footer}", "isHtml": True}]


def format_library_options(libraries: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Numbered option chips for library selection."""
    options = []
    for i, library in enumerate(libraries, start=1):
        area = library.get("area", "")
        dist = library.get("distance_miles")
        dist_str = f", {dist} mi" if dist is not None else ""
        label = f"{library.get('name', 'Library')} ({area}{dist_str})"
        options.append({"label": label, "value": str(i)})
    return options


def format_library_detail(library: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detailed HTML bubble for a single library."""
    name        = library.get("name", "Unknown Library")
    area        = library.get("area", "")
    address     = library.get("address", "")
    phone       = library.get("phone") or "Not available"
    email       = library.get("email") or ""
    url         = library.get("url", "")
    hours       = library.get("hours") or {}
    services    = library.get("services") or []
    programs    = library.get("programs") or []
    description = library.get("description", "")
    note        = library.get("note", "")
    dist        = library.get("distance_miles")

    dist_html = (
        f'<p style="margin:4px 0;"><b>Distance from your postcode:</b> {dist} miles</p>'
        if dist is not None else ""
    )

    hours_html = _hours_table(hours) if hours else ""

    service_chips = "".join(_service_chip(s) for s in services) if services else ""
    services_html = (
        f'<div style="margin:6px 0 4px;">{service_chips}</div>'
        if service_chips else ""
    )

    programs_html = ""
    if programs:
        items = "".join(f"<li style='margin:2px 0;'>{p}</li>" for p in programs)
        programs_html = f'<ul style="margin:4px 0 4px 16px;padding:0;font-size:0.85em;">{items}</ul>'

    note_html = (
        f'<p style="margin:6px 0;background:#fef3c7;border-left:3px solid #f59e0b;'
        f'padding:6px 8px;border-radius:4px;font-size:0.84em;">{note}</p>'
        if note else ""
    )

    contact_parts = []
    if phone and phone != "Not available":
        contact_parts.append(f'<b>Phone:</b> <a href="tel:{phone}" style="color:#2563eb;">{phone}</a>')
    else:
        contact_parts.append(f'<b>Phone:</b> Not available')
    if email:
        contact_parts.append(f'<b>Email:</b> <a href="mailto:{email}" style="color:#2563eb;">{email}</a>')

    contact_html = "<br>".join(contact_parts)

    detail_html = f"""
<div style="border:1px solid #2563eb;border-radius:10px;padding:16px;background:#eff6ff;">
  <div style="font-size:1.05em;font-weight:700;margin-bottom:4px;">{name}</div>
  <div style="color:#4b5563;font-size:0.88em;margin-bottom:6px;">{area}</div>
  {f'<p style="margin:4px 0;font-size:0.88em;"><b>Address:</b> {address}</p>' if address else ''}
  {dist_html}
  {note_html}
  {f'<p style="margin:8px 0 2px;font-weight:600;font-size:0.88em;">Opening Hours</p>' if hours_html else ''}
  {hours_html}
  {f'<p style="margin:8px 0 2px;font-weight:600;font-size:0.88em;">Facilities</p>' if services_html else ''}
  {services_html}
  {f'<p style="margin:8px 0 2px;font-weight:600;font-size:0.88em;">Events and Activities</p>' if programs_html else ''}
  {programs_html}
  {f'<p style="margin:8px 0;color:#374151;font-size:0.88em;">{description}</p>' if description else ''}
  <div style="margin-top:8px;font-size:0.85em;color:#374151;">{contact_html}</div>
  <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
    {f'<a href="{url}" target="_blank" style="padding:6px 14px;background:#2563eb;color:white;border-radius:6px;font-size:0.85em;text-decoration:none;font-weight:600;">Library Details &#x2197;</a>' if url else ''}
    <a href="{_CATALOGUE_URL}" target="_blank" style="padding:6px 14px;background:#6b7280;color:white;border-radius:6px;font-size:0.85em;text-decoration:none;">Search Catalogue &#x2197;</a>
  </div>
</div>"""

    return [{"reply": detail_html, "isHtml": True}]


def format_library_not_found() -> List[Dict[str, Any]]:
    return [
        {
            "reply": (
                "I could not find that library. Please try again with the library name or area, "
                'or visit <a href="https://www.bradford.gov.uk/libraries/find-your-local-library/" '
                'target="_blank">Bradford Libraries &#x2197;</a> for a full list.'
            ),
            "isHtml": True,
        }
    ]
