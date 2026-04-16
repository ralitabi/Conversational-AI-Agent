"""
HTML bubble formatters for school finder results.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


_OFSTED_BADGE = {
    "outstanding":           '<span style="background:#16a34a;color:white;border-radius:4px;padding:1px 6px;font-size:0.78em;">Outstanding</span>',
    "good":                  '<span style="background:#2563eb;color:white;border-radius:4px;padding:1px 6px;font-size:0.78em;">Good</span>',
    "requires improvement":  '<span style="background:#d97706;color:white;border-radius:4px;padding:1px 6px;font-size:0.78em;">Requires Improvement</span>',
    "inadequate":            '<span style="background:#dc2626;color:white;border-radius:4px;padding:1px 6px;font-size:0.78em;">Inadequate</span>',
}

_PHASE_ICON = {
    "primary":    "",
    "secondary":  "",
    "post-16":    "",
    "all-through":"",
}


def _ofsted_badge(rating: Optional[str]) -> str:
    if not rating:
        return ""
    return _OFSTED_BADGE.get(rating.lower(), "")


def _phase_icon(phase: Optional[str]) -> str:
    return _PHASE_ICON.get((phase or "").lower(), "&#x1F3EB;")


def _distance_badge(miles: Optional[float]) -> str:
    if miles is None:
        return ""
    return (
        f'<span style="background:#f3f4f6;color:#374151;border-radius:4px;'
        f'padding:1px 6px;font-size:0.78em;">{miles} mi</span>'
    )


def format_school_search_results(
    schools: List[Dict[str, Any]],
    query: str,
    postcode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Build HTML message bubbles for a list of school search results."""
    if not schools:
        return [
            {
                "reply": (
                    "No schools found matching your search. "
                    "Try a different name, area (e.g. Bingley, Shipley), "
                    "or school type (primary / secondary).<br><br>"
                    'You can also view all schools at: '
                    '<a href="https://www.bradford.gov.uk/education-and-skills/find-a-school/schools-finder/" '
                    'target="_blank">Bradford Schools Finder &#x2197;</a>'
                ),
                "isHtml": True,
            }
        ]

    count   = len(schools)
    has_dist = any(s.get("distance_miles") is not None for s in schools)
    dist_note = f" sorted by distance from <b>{postcode.upper()}</b>" if (has_dist and postcode) else ""

    intro = f"Found <b>{count} school{'s' if count != 1 else ''}</b> for <b>{query}</b>{dist_note}:"

    cards = ""
    for i, school in enumerate(schools, start=1):
        name    = school.get("name", "Unknown School")
        phase   = school.get("phase", "")
        stype   = school.get("type", "")
        area    = school.get("area", "")
        ages    = school.get("age_range", "")
        ofsted  = _ofsted_badge(school.get("ofsted"))
        dist    = _distance_badge(school.get("distance_miles"))
        url     = school.get("url", "")
        app     = school.get("application_type", "ICAF")
        app_note = "ICAF form" if app == "ICAF" else "Apply direct to school"

        cards += f"""
<div style="border:1px solid #e5e7eb;border-radius:8px;padding:11px 13px;margin-bottom:9px;background:#fff;">
  <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap;margin-bottom:3px;">
    <span style="font-weight:700;font-size:0.95em;">{i}. {name}</span>
    {ofsted}
    {dist}
  </div>
  <div style="color:#6b7280;font-size:0.85em;">{stype} &bull; {phase} &bull; Ages {ages} &bull; {area}</div>
  <div style="margin-top:5px;font-size:0.82em;color:#4b5563;">{app_note}
    {f'&nbsp;&bull;&nbsp;<a href="{url}" target="_blank" style="color:#2563eb;">Website &#x2197;</a>' if url else ''}
  </div>
</div>"""

    footer = (
        '<p style="font-size:0.83em;color:#6b7280;margin-top:4px;">'
        'Type a <b>number</b> to see full details, or enter a new search.'
        f'&nbsp;<a href="https://www.bradford.gov.uk/education-and-skills/find-a-school/schools-finder/" '
        f'target="_blank">View all schools &#x2197;</a></p>'
    )

    return [{"reply": f"<p>{intro}</p>{cards}{footer}", "isHtml": True}]


def format_school_options(schools: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Numbered option chips for school selection."""
    options = []
    for i, school in enumerate(schools, start=1):
        phase = school.get("phase", "")
        area  = school.get("area", "")
        dist  = school.get("distance_miles")
        dist_str = f", {dist} mi" if dist is not None else ""
        label = f"{school.get('name', 'School')} ({phase}, {area}{dist_str})"
        options.append({"label": label, "value": str(i)})
    return options


def format_school_detail(school: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Detailed HTML bubble for a single school."""
    name        = school.get("name", "Unknown School")
    phase       = school.get("phase", "")
    stype       = school.get("type", "")
    area        = school.get("area", "")
    ages        = school.get("age_range", "")
    address     = school.get("address", "")
    ofsted      = _ofsted_badge(school.get("ofsted"))
    dist        = school.get("distance_miles")
    url         = school.get("url", "")
    council_url = school.get(
        "council_page",
        "https://www.bradford.gov.uk/education-and-skills/find-a-school/schools-finder/",
    )
    app         = school.get("application_type", "ICAF")
    description = school.get("description", "")

    dist_html = (
        f'<p style="margin:4px 0;"><b>Distance from your postcode:</b> {dist} miles</p>'
        if dist is not None else ""
    )

    if app == "ICAF":
        app_html = (
            '<p style="margin:6px 0 2px;">Application: <b>How to apply:</b> '
            'Use the Bradford In Common Application Form (ICAF) &mdash; '
            '<a href="https://www.bradford.gov.uk/education-and-skills/school-admissions/" '
            'target="_blank">Apply here &#x2197;</a></p>'
        )
    else:
        app_html = (
            '<p style="margin:6px 0 2px;">Application: <b>How to apply:</b> '
            'Apply <b>directly to the school</b>. Contact the school for their application form '
            'and any supplementary information required.</p>'
        )

    detail_html = f"""
<div style="border:1px solid #2563eb;border-radius:10px;padding:16px;background:#eff6ff;">
  <div style="font-size:1.05em;font-weight:700;margin-bottom:6px;display:flex;align-items:center;gap:8px;flex-wrap:wrap;">
    {name} {ofsted}
  </div>
  <div style="color:#4b5563;font-size:0.88em;margin-bottom:8px;">{stype} &bull; {phase} &bull; Ages {ages}</div>
  {f'<p style="margin:4px 0;">Address: <b>{address}</b></p>' if address else ''}
  {f'<p style="margin:4px 0;">Area: <b>{area}</b></p>' if area else ''}
  {dist_html}
  {f'<p style="margin:8px 0;color:#374151;font-size:0.92em;">{description}</p>' if description else ''}
  {app_html}
  <div style="margin-top:12px;display:flex;gap:8px;flex-wrap:wrap;">
    {f'<a href="{url}" target="_blank" style="padding:6px 14px;background:#2563eb;color:white;border-radius:6px;font-size:0.85em;text-decoration:none;font-weight:600;">Visit School Website &#x2197;</a>' if url else ''}
    <a href="{council_url}" target="_blank" style="padding:6px 14px;background:#6b7280;color:white;border-radius:6px;font-size:0.85em;text-decoration:none;">Bradford Schools Finder &#x2197;</a>
  </div>
</div>"""

    return [{"reply": detail_html, "isHtml": True}]


def format_school_not_found() -> List[Dict[str, Any]]:
    return [
        {
            "reply": (
                "I could not find that school. Please try again with the school name or area, "
                'or visit the <a href="https://www.bradford.gov.uk/education-and-skills/find-a-school/schools-finder/" '
                'target="_blank">Bradford Schools Finder &#x2197;</a> for a full list.'
            ),
            "isHtml": True,
        }
    ]
