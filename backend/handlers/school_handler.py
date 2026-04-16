"""
Bradford school finder handler.

Flow:
  1. start_school_finder_flow  — ask what to search for
  2. handle_school_search      — search; if results found, ask for postcode to sort by distance
  3. handle_postcode_for_distance — re-sort results by distance, show options
  4. handle_school_selection   — show full school detail
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.council_connectors.school_connector import (
    search_schools,
    get_school_by_id,
    nearest_schools,
)
from backend.utils.school_formatter import (
    format_school_options,
    format_school_search_results,
    format_school_detail,
    format_school_not_found,
)
from backend.utils.response_builder import build_reply, build_messages_reply

_UK_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$", re.IGNORECASE
)


def _looks_like_postcode(text: str) -> bool:
    return bool(_UK_POSTCODE_RE.match(text.strip()))


class SchoolHandler:
    """Manages the school finder conversation flow."""

    def __init__(self, session_manager) -> None:
        self.session_manager = session_manager

    # -------------------------------------------------------------------------
    # Step 1: Start flow
    # -------------------------------------------------------------------------

    def start_school_finder_flow(self, session: Dict[str, Any]) -> Dict[str, Any]:
        self._reset_school_flow(session)
        session["school_flow_stage"] = "awaiting_school_query"
        return {
            "reply": (
                "I can help you find a Bradford school. "
                "Please type a school name, area (for example Bingley or Shipley), "
                "or school type (primary or secondary) to search. "
                "You can also enter your postcode to find the nearest schools."
            ),
            "messages": [
                {
                    "reply": (
                        "I can help you find a Bradford school.<br><br>"
                        "Type a <b>school name</b>, <b>area</b> (e.g. Bingley, Shipley, Keighley) "
                        "or <b>school type</b> (primary / secondary).<br><br>"
                        "You can also enter your <b>postcode</b> to find the nearest schools to you."
                    ),
                    "isHtml": True,
                }
            ],
            "input_type": "text",
        }


    # -------------------------------------------------------------------------
    # Step 2: Handle search query or postcode
    # -------------------------------------------------------------------------

    def handle_school_query(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """Entry point when school_flow_stage == 'awaiting_school_query'."""
        text = (text or "").strip()
        if not text:
            return build_reply(
                "Please type a school name, area, or postcode to search.",
                input_type="text",
            )

        # If user entered a postcode directly → show nearest schools
        if _looks_like_postcode(text):
            return self._handle_nearest_by_postcode(session, text)

        # Otherwise search by name/area/type
        return self._handle_search(session, text)

    # -------------------------------------------------------------------------
    # Step 3: Postcode for distance after seeing results
    # -------------------------------------------------------------------------

    def handle_postcode_for_distance(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """User entered their postcode after seeing initial results."""
        text = (text or "").strip()

        if text.lower() in {"skip", "no", "no thanks", "n"}:
            # Show results without distance
            results = session.get("school_results", [])
            query   = session.get("school_query", "")
            session["school_flow_stage"] = "awaiting_school_selection"
            return self._build_results_reply(session, results, query)

        if not _looks_like_postcode(text):
            return {
                "reply": (
                    "That doesn't look like a valid UK postcode. "
                    "Please enter your full postcode (for example BD1 1HY) or type 'skip' to continue."
                ),
                "messages": [
                    {
                        "reply": (
                            "That doesn't look like a valid UK postcode. "
                            "Please enter your full postcode (e.g. <b>BD1 1HY</b>) "
                            "or type <b>skip</b> to continue without distance."
                        ),
                        "isHtml": True,
                    }
                ],
                "input_type": "text",
            }

        query = session.get("school_query", "")
        results = search_schools(query, postcode=text)

        if not results:
            results = session.get("school_results", [])

        session["school_results"] = results
        session["school_postcode"] = text
        session["school_flow_stage"] = "awaiting_school_selection"

        return self._build_results_reply(session, results, query, postcode=text)

    # -------------------------------------------------------------------------
    # Step 4: School selection
    # -------------------------------------------------------------------------

    def handle_school_selection(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = session.get("school_results", [])
        text = (text or "").strip()

        # Check if user entered a postcode at this stage → re-sort
        if _looks_like_postcode(text):
            return self.handle_postcode_for_distance(session, text)

        school = self._resolve_selection(text, results)

        if school is None:
            # Try a fresh search
            new_results = search_schools(
                text, postcode=session.get("school_postcode")
            )
            if new_results:
                session["school_results"] = new_results
                session["school_query"]   = text
                session["school_flow_stage"] = "awaiting_school_selection"
                return self._build_results_reply(session, new_results, text)

            session["school_flow_stage"] = "awaiting_school_query"
            return {
                **build_messages_reply(format_school_not_found()),
                "input_type": "text",
            }

        self._reset_school_flow(session)
        detail = format_school_detail(school)
        follow_up = {
            "reply": (
                "Would you like to search for another school? "
                "Type a name, area, or postcode, or type <b>menu</b> to return to the main menu."
            ),
            "isHtml": True,
        }
        return {
            **build_messages_reply(detail + [follow_up]),
            "input_type": "text",
        }

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _handle_nearest_by_postcode(
        self,
        session: Dict[str, Any],
        postcode: str,
    ) -> Dict[str, Any]:
        results = nearest_schools(postcode)
        if not results:
            return {
                "reply": (
                    "I could not find schools for that postcode. "
                    "Please check the postcode and try again, or type a school name or area."
                ),
                "input_type": "text",
            }
        session["school_results"]  = results
        session["school_query"]    = "nearest schools"
        session["school_postcode"] = postcode
        session["school_flow_stage"] = "awaiting_school_selection"
        return self._build_results_reply(session, results, "nearest schools", postcode=postcode)

    def _handle_search(
        self,
        session: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        results = search_schools(query)
        if not results:
            session["school_flow_stage"] = "awaiting_school_query"
            return {
                **build_messages_reply(format_school_not_found()),
                "input_type": "text",
            }

        session["school_results"] = results
        session["school_query"]   = query
        session["school_flow_stage"] = "awaiting_postcode_for_distance"

        # Ask for postcode to sort by distance
        intro_messages = format_school_search_results(results, query)
        postcode_prompt = {
            "reply": (
                "To sort these results by distance from your home, "
                "please enter your postcode (e.g. BD1 1HY). "
                "Type 'skip' to see the results without distance."
            ),
            "isHtml": False,
        }
        return {
            "reply": f"Found {len(results)} school(s). Enter your postcode for nearest-first order, or 'skip'.",
            "messages": intro_messages + [postcode_prompt],
            "input_type": "text",
        }

    def _build_results_reply(
        self,
        session: Dict[str, Any],
        results: List[Dict[str, Any]],
        query: str,
        postcode: Optional[str] = None,
    ) -> Dict[str, Any]:
        options  = format_school_options(results)
        allowed  = [str(i) for i in range(1, len(results) + 1)]
        messages = format_school_search_results(results, query, postcode=postcode)
        return {
            "reply": f"Found {len(results)} school(s). Select a number for details:",
            "messages": messages,
            "input_type": "options",
            "options": options,
            "allowed_values": allowed,
        }

    def _resolve_selection(
        self,
        text: str,
        results: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        if not results:
            return None
        if text.isdigit():
            idx = int(text) - 1
            if 0 <= idx < len(results):
                return results[idx]
            return None
        text_lower = text.lower()
        for school in results:
            if text_lower in school.get("name", "").lower():
                return school
        for school in results:
            if school.get("id") == text:
                return school
        return None

    def _reset_school_flow(self, session: Dict[str, Any]) -> None:
        for key in ("school_flow_stage", "school_results", "school_query", "school_postcode"):
            session.pop(key, None)
