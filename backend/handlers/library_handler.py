"""
Bradford library finder handler.

Flow:
  1. start_library_finder_flow  — ask what to search for
  2. handle_library_query       — search; if results found, ask for postcode to sort by distance
  3. handle_postcode_for_distance — re-sort results by distance, show options
  4. handle_library_selection   — show full library detail
"""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from backend.council_connectors.library_connector import (
    search_libraries,
    get_library_by_id,
    nearest_libraries,
)
from backend.utils.library_formatter import (
    format_library_options,
    format_library_search_results,
    format_library_detail,
    format_library_not_found,
)
from backend.utils.response_builder import build_reply, build_messages_reply

_UK_POSTCODE_RE = re.compile(
    r"^[A-Z]{1,2}\d{1,2}[A-Z]?\s*\d[A-Z]{2}$", re.IGNORECASE
)


def _looks_like_postcode(text: str) -> bool:
    return bool(_UK_POSTCODE_RE.match(text.strip()))


class LibraryHandler:
    """Manages the library finder conversation flow."""

    def __init__(self, session_manager) -> None:
        self.session_manager = session_manager

    # -------------------------------------------------------------------------
    # Step 1: Start flow
    # -------------------------------------------------------------------------

    def start_library_finder_flow(self, session: Dict[str, Any]) -> Dict[str, Any]:
        self._reset_library_flow(session)
        session["library_flow_stage"] = "awaiting_library_query"
        return {
            "reply": (
                "I can help you find a Bradford library. "
                "Please type a library name, area (for example Bingley or Shipley), "
                "or a service you need (such as computers or meeting rooms). "
                "You can also enter your postcode to find the nearest libraries."
            ),
            "messages": [
                {
                    "reply": (
                        "I can help you find a Bradford library.<br><br>"
                        "Type a <b>library name</b>, <b>area</b> (e.g. Bingley, Shipley, Keighley) "
                        "or <b>service type</b> (e.g. computers, meeting rooms, children's activities).<br><br>"
                        "You can also enter your <b>postcode</b> to find the nearest libraries to you."
                    ),
                    "isHtml": True,
                }
            ],
            "input_type": "text",
        }

    # -------------------------------------------------------------------------
    # Step 2: Handle search query or postcode
    # -------------------------------------------------------------------------

    def handle_library_query(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        """Entry point when library_flow_stage == 'awaiting_library_query'."""
        text = (text or "").strip()
        if not text:
            return build_reply(
                "Please type a library name, area, or postcode to search.",
                input_type="text",
            )

        # If user entered a postcode directly → show nearest libraries
        if _looks_like_postcode(text):
            return self._handle_nearest_by_postcode(session, text)

        # Otherwise search by name/area/service
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
            results = session.get("library_results", [])
            query   = session.get("library_query", "")
            session["library_flow_stage"] = "awaiting_library_selection"
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

        query = session.get("library_query", "")
        results = search_libraries(query, postcode=text)

        if not results:
            results = session.get("library_results", [])

        session["library_results"]  = results
        session["library_postcode"] = text
        session["library_flow_stage"] = "awaiting_library_selection"

        return self._build_results_reply(session, results, query, postcode=text)

    # -------------------------------------------------------------------------
    # Step 4: Library selection
    # -------------------------------------------------------------------------

    def handle_library_selection(
        self,
        session: Dict[str, Any],
        text: str,
    ) -> Dict[str, Any]:
        results: List[Dict[str, Any]] = session.get("library_results", [])
        text = (text or "").strip()

        # Check if user entered a postcode at this stage → re-sort
        if _looks_like_postcode(text):
            return self.handle_postcode_for_distance(session, text)

        library = self._resolve_selection(text, results)

        if library is None:
            # Try a fresh search
            new_results = search_libraries(
                text, postcode=session.get("library_postcode")
            )
            if new_results:
                session["library_results"] = new_results
                session["library_query"]   = text
                session["library_flow_stage"] = "awaiting_library_selection"
                return self._build_results_reply(session, new_results, text)

            session["library_flow_stage"] = "awaiting_library_query"
            return {
                **build_messages_reply(format_library_not_found()),
                "input_type": "text",
            }

        # Clear results but keep the user in library context so follow-up
        # queries ("search again", another name/postcode) route correctly.
        session.pop("library_results", None)
        session.pop("library_query", None)
        session.pop("library_postcode", None)
        session["library_flow_stage"] = "awaiting_library_query"

        detail = format_library_detail(library)
        follow_up = {
            "reply": (
                "Would you like to search for another library? "
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
        results = nearest_libraries(postcode)
        if not results:
            return {
                "reply": (
                    "I could not find libraries for that postcode. "
                    "Please check the postcode and try again, or type a library name or area."
                ),
                "input_type": "text",
            }
        session["library_results"]  = results
        session["library_query"]    = "nearest libraries"
        session["library_postcode"] = postcode
        session["library_flow_stage"] = "awaiting_library_selection"
        return self._build_results_reply(session, results, "nearest libraries", postcode=postcode)

    def _handle_search(
        self,
        session: Dict[str, Any],
        query: str,
    ) -> Dict[str, Any]:
        results = search_libraries(query)
        if not results:
            session["library_flow_stage"] = "awaiting_library_query"
            return {
                **build_messages_reply(format_library_not_found()),
                "input_type": "text",
            }

        session["library_results"] = results
        session["library_query"]   = query
        session["library_flow_stage"] = "awaiting_postcode_for_library_distance"

        # Ask for postcode to sort by distance
        intro_messages = format_library_search_results(results, query)
        postcode_prompt = {
            "reply": (
                "To sort these results by distance from your home, "
                "please enter your postcode (e.g. BD1 1HY). "
                "Type 'skip' to see the results without distance."
            ),
            "isHtml": False,
        }
        return {
            "reply": f"Found {len(results)} librar{'ies' if len(results) != 1 else 'y'}. Enter your postcode for nearest-first order, or 'skip'.",
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
        options  = format_library_options(results)
        allowed  = [str(i) for i in range(1, len(results) + 1)]
        messages = format_library_search_results(results, query, postcode=postcode)
        return {
            "reply": f"Found {len(results)} librar{'ies' if len(results) != 1 else 'y'}. Select a number for details:",
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
        for library in results:
            if text_lower in library.get("name", "").lower():
                return library
        for library in results:
            if library.get("id") == text:
                return library
        return None

    def _reset_library_flow(self, session: Dict[str, Any]) -> None:
        for key in (
            "library_flow_stage",
            "library_results",
            "library_query",
            "library_postcode",
        ):
            session.pop(key, None)
