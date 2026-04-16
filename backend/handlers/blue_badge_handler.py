"""
Bradford Blue Badge conversational flows.

Renewal Reminder Flow:
  1. start_renewal_reminder_flow  — ask when badge expires
  2. handle_renewal_date          — parse date, check 3-month window, guide to renewal

Eligibility Wizard Flow:
  1. start_eligibility_wizard     — ask first eligibility question
  2. handle_eligibility_step      — process yes/no answer, ask next question or give result
"""
from __future__ import annotations

import calendar
import re
from datetime import date
from typing import Any, Dict, Optional, Tuple

from backend.utils.response_builder import build_reply

RENEWAL_LINK   = "https://www.gov.uk/apply-blue-badge"
BRADFORD_PHONE = "01274 438723"
BRADFORD_EMAIL = "transport.concessions@bradford.gov.uk"
BRADFORD_HOURS = "Mon–Thu 8:30am–5pm, Fri 8:30am–4:30pm"

# Month name → number
_MONTH_MAP: Dict[str, int] = {
    "january": 1,   "jan": 1,
    "february": 2,  "feb": 2,
    "march": 3,     "mar": 3,
    "april": 4,     "apr": 4,
    "may": 5,
    "june": 6,      "jun": 6,
    "july": 7,      "jul": 7,
    "august": 8,    "aug": 8,
    "september": 9, "sep": 9, "sept": 9,
    "october": 10,  "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}

_ELIGIBILITY_STEP_KEYS = [
    "receives_pip_dla",
    "walking_difficulty",
    "hidden_disability",
    "is_child",
]

_ELIGIBILITY_QUESTIONS = [
    (
        "Let me help you check whether you may qualify for a Blue Badge. "
        "I will ask a few quick questions.\n\n"
        "Do you currently receive PIP (Personal Independence Payment) or "
        "DLA (Disability Living Allowance)? (Please reply yes or no)"
    ),
    (
        "Do you have a significant difficulty walking — for example due to a "
        "physical disability, pain, or breathlessness? (Please reply yes or no)"
    ),
    (
        "Do you have a hidden or non-visible disability — such as autism, ADHD, "
        "anxiety, epilepsy, Crohn's disease, or a condition that affects your "
        "ability to be in a vehicle safely? (Please reply yes or no)"
    ),
    (
        "Is this badge for a child under 16? (Please reply yes or no)"
    ),
]


def _parse_expiry_date(text: str) -> Optional[Tuple[int, int]]:
    """
    Parse (month, year) from free text.
    Accepts: 'March 2025', '03/2025', '3/25', '2025-03', 'March 25', etc.
    Returns None when no date can be extracted.
    """
    lowered = text.strip().lower()

    # MM/YYYY or MM/YY  (e.g. 03/2025 or 3/25)
    m = re.search(r"\b(\d{1,2})[/\-](\d{2,4})\b", lowered)
    if m:
        mo, yr = int(m.group(1)), int(m.group(2))
        if yr < 100:
            yr += 2000
        if 1 <= mo <= 12:
            return (mo, yr)

    # YYYY-MM or YYYY/MM  (e.g. 2025-03)
    m = re.search(r"\b(20\d{2})[/\-](\d{1,2})\b", lowered)
    if m:
        yr, mo = int(m.group(1)), int(m.group(2))
        if 1 <= mo <= 12:
            return (mo, yr)

    # Month name + year  (e.g. 'March 2025' or '2025 March')
    for name, num in _MONTH_MAP.items():
        pat1 = rf"\b{re.escape(name)}\s+(\d{{2,4}})\b"
        m1 = re.search(pat1, lowered)
        if m1:
            yr = int(m1.group(1))
            if yr < 100:
                yr += 2000
            return (num, yr)
        pat2 = rf"\b(\d{{2,4}})\s+{re.escape(name)}\b"
        m2 = re.search(pat2, lowered)
        if m2:
            yr = int(m2.group(1))
            if yr < 100:
                yr += 2000
            return (num, yr)

    # Bare year (e.g. '2025') — treat as middle of that year (June)
    m = re.search(r"\b(20\d{2})\b", lowered)
    if m:
        return (6, int(m.group(1)))

    return None


def _is_yes(text: str) -> bool:
    t = text.strip().lower()
    return t in {
        "yes", "y", "yeah", "yep", "yup", "correct", "true",
        "i do", "i have", "definitely", "absolutely", "sure",
    } or t.startswith("yes ")


def _is_no(text: str) -> bool:
    t = text.strip().lower()
    return t in {
        "no", "n", "nope", "nah", "not really", "i don't", "i do not",
        "no i don't", "no i do not", "false", "negative",
    } or t.startswith("no ")


class BlueBadgeHandler:
    """Manages the Blue Badge renewal reminder and eligibility wizard flows."""

    def __init__(self, session_manager) -> None:
        self.session_manager = session_manager

    # =========================================================================
    # PUBLIC — Reset
    # =========================================================================

    def reset_blue_badge_flow(self, session: Dict[str, Any]) -> None:
        for key in ("blue_badge_flow_stage", "eligibility_step", "eligibility_answers"):
            session.pop(key, None)

    # =========================================================================
    # RENEWAL REMINDER FLOW
    # =========================================================================

    def start_renewal_reminder_flow(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1 — ask for expiry date."""
        self.reset_blue_badge_flow(session)
        session["blue_badge_flow_stage"] = "awaiting_renewal_date"
        return build_reply(
            "To help you with your Blue Badge renewal, please tell me when your "
            "current badge expires — for example: 'March 2025' or '06/2025'."
        )

    def handle_renewal_date(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """Step 2 — parse date, calculate urgency, respond."""
        text = (text or "").strip()
        parsed = _parse_expiry_date(text)

        if not parsed:
            return build_reply(
                "I did not quite catch that date. Please enter your badge's expiry month and year "
                "— for example 'March 2025' or '06/2025'."
            )

        expiry_month, expiry_year = parsed
        today = date.today()

        try:
            last_day   = calendar.monthrange(expiry_year, expiry_month)[1]
            expiry_date = date(expiry_year, expiry_month, last_day)
        except ValueError:
            return build_reply(
                "That date does not look valid. Please re-enter your badge's expiry month and year."
            )

        self.reset_blue_badge_flow(session)

        # ── Expired ──────────────────────────────────────────────────────────
        if expiry_date < today:
            months_ago = (today.year - expiry_year) * 12 + (today.month - expiry_month)
            return build_reply(
                f"Your Blue Badge expired in {expiry_date.strftime('%B %Y')}, "
                f"approximately {months_ago} month{'s' if months_ago != 1 else ''} ago. "
                "You cannot legally use an expired badge — doing so is a criminal offence. "
                f"Please apply for a new badge as soon as possible at {RENEWAL_LINK}. "
                f"For help, contact Bradford Council on {BRADFORD_PHONE} ({BRADFORD_HOURS}) "
                f"or email {BRADFORD_EMAIL}."
            )

        months_until = (expiry_year - today.year) * 12 + (expiry_month - today.month)

        # ── Expiring within 3 months ──────────────────────────────────────────
        if months_until <= 3:
            return build_reply(
                f"Your Blue Badge expires in {expiry_date.strftime('%B %Y')}, "
                f"which is only {months_until} month{'s' if months_until != 1 else ''} away. "
                "You should apply for renewal now — Bradford Council recommends renewing at least "
                "12 weeks before your badge expires as processing can take time. "
                f"Apply for renewal at {RENEWAL_LINK}. "
                "Your eligibility will be reassessed during renewal, so make sure your application "
                "reflects your current circumstances. "
                "The renewal fee is £10, payable on approval. "
                f"For help, call Bradford Council on {BRADFORD_PHONE} ({BRADFORD_HOURS}) "
                f"or email {BRADFORD_EMAIL}."
            )

        # ── Expiring in 4–6 months ────────────────────────────────────────────
        if months_until <= 6:
            return build_reply(
                f"Your Blue Badge expires in {expiry_date.strftime('%B %Y')}, "
                f"which is about {months_until} months away. "
                "You do not need to renew just yet, but it is worth planning ahead. "
                "Bradford Council recommends applying at least 12 weeks before expiry, "
                "as processing takes time. "
                f"When you are ready, renew at {RENEWAL_LINK}. "
                f"For questions, call {BRADFORD_PHONE} or email {BRADFORD_EMAIL}."
            )

        # ── More than 6 months ────────────────────────────────────────────────
        return build_reply(
            f"Your Blue Badge expires in {expiry_date.strftime('%B %Y')}, "
            f"which is {months_until} months away — there is no need to renew yet. "
            "Bradford Council recommends applying around 12 weeks before your badge expires. "
            f"When the time comes, renew at {RENEWAL_LINK}. "
            f"For any queries, contact Bradford on {BRADFORD_PHONE} or email {BRADFORD_EMAIL}."
        )

    # =========================================================================
    # ELIGIBILITY WIZARD FLOW
    # =========================================================================

    def start_eligibility_wizard(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Step 1 — start wizard, ask first question."""
        self.reset_blue_badge_flow(session)
        session["blue_badge_flow_stage"] = "eligibility_wizard"
        session["eligibility_step"]      = 0
        session["eligibility_answers"]   = {}
        return build_reply(_ELIGIBILITY_QUESTIONS[0])

    def handle_eligibility_step(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """Process a yes/no answer and advance the wizard or return a result."""
        text = (text or "").strip()
        step = session.get("eligibility_step", 0)

        is_yes = _is_yes(text)
        is_no  = _is_no(text)

        if not is_yes and not is_no:
            question = (
                _ELIGIBILITY_QUESTIONS[step]
                if step < len(_ELIGIBILITY_QUESTIONS)
                else "Please reply yes or no."
            )
            return build_reply(
                "Please reply with 'yes' or 'no' to continue.\n\n" + question
            )

        # Save answer
        answers = session.get("eligibility_answers", {})
        if step < len(_ELIGIBILITY_STEP_KEYS):
            answers[_ELIGIBILITY_STEP_KEYS[step]] = is_yes
            session["eligibility_answers"] = answers

        # ── Step 0: receives PIP / DLA ────────────────────────────────────────
        if step == 0 and is_yes:
            self.reset_blue_badge_flow(session)
            return build_reply(
                "Based on your answer, you may be automatically eligible for a Blue Badge. "
                "You qualify automatically if you receive the Higher Rate Mobility component "
                "of DLA, or 8 or more points under the PIP 'moving around' activity, or "
                "10 points under PIP descriptor E due to overwhelming psychological distress. "
                f"Apply directly at {RENEWAL_LINK} — your benefit entitlement will be verified "
                "as part of the application. The badge costs £10 if approved. "
                f"For help, call Bradford Council on {BRADFORD_PHONE} ({BRADFORD_HOURS}) "
                f"or email {BRADFORD_EMAIL}."
            )

        # ── Step 1: significant walking difficulty ────────────────────────────
        if step == 1 and is_yes:
            self.reset_blue_badge_flow(session)
            return build_reply(
                "If you have a severe or substantial difficulty walking, you may qualify "
                "for a Blue Badge through a discretionary assessment. Bradford Council will "
                "consider how far you can walk, whether you experience significant pain or "
                "breathlessness, and the time it takes you. "
                f"Apply at {RENEWAL_LINK} and include supporting evidence such as a letter "
                "from your GP, consultant, or physiotherapist. The badge costs £10 if approved. "
                f"For help, call {BRADFORD_PHONE} ({BRADFORD_HOURS}) or email {BRADFORD_EMAIL}."
            )

        # ── Step 2: hidden / non-visible disability ───────────────────────────
        if step == 2 and is_yes:
            self.reset_blue_badge_flow(session)
            return build_reply(
                "Bradford Council recognises hidden and non-visible disabilities. You may qualify "
                "through a discretionary assessment if your condition significantly affects your "
                "ability to walk, or means you cannot be safely left alone in a vehicle. "
                "Conditions considered include autism, ADHD, anxiety, epilepsy, Crohn's disease, "
                "ME, lupus, rheumatoid arthritis, and others. You will need supporting evidence "
                "from a GP, consultant, or specialist. "
                f"Apply at {RENEWAL_LINK}. "
                f"For guidance, call {BRADFORD_PHONE} or email {BRADFORD_EMAIL}."
            )

        # ── Step 3: is a child ────────────────────────────────────────────────
        if step == 3 and is_yes:
            self.reset_blue_badge_flow(session)
            return build_reply(
                "Children can qualify for a Blue Badge. Children under 3 may be eligible if "
                "they have a medical condition requiring them to remain near a vehicle at all "
                "times, or if they need bulky medical equipment that cannot easily be carried. "
                "Children aged 3 and over with a severe permanent walking disability may also "
                "qualify automatically or through a discretionary assessment. "
                "A parent or carer applies on their behalf. "
                f"Apply at {RENEWAL_LINK}. "
                f"For help, call Bradford Council on {BRADFORD_PHONE} or email {BRADFORD_EMAIL}."
            )

        # ── All steps exhausted with 'no' answers ────────────────────────────
        if step >= len(_ELIGIBILITY_QUESTIONS) - 1:
            self.reset_blue_badge_flow(session)
            return build_reply(
                "Based on your answers, you may not meet the standard automatic criteria, "
                "but Bradford Council also considers applications on a discretionary basis. "
                "If your condition affects your ability to walk or your safety near traffic, "
                "it is still worth applying with supporting evidence from your GP or specialist. "
                f"Apply at {RENEWAL_LINK} or call Bradford Council on {BRADFORD_PHONE} "
                "for personal advice before you apply."
            )

        # ── Advance to next step ──────────────────────────────────────────────
        next_step = step + 1
        session["eligibility_step"] = next_step
        return build_reply(_ELIGIBILITY_QUESTIONS[next_step])
