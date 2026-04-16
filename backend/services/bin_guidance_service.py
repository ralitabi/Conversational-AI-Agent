"""
Loads and queries the bin recycling guidance dataset.

Extracted from chat_engine.py so that ChatEngine stays focused on routing.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.chat_helpers import normalize_text
from backend.utils.bin_formatter import format_recycling_guidance_messages
from backend.utils.response_builder import build_messages_reply


class BinGuidanceService:
    """Handles keyword lookup against bin_recycling_guidance.json."""

    DEFAULT_FALLBACK = "I could not find a bin guidance answer for that item."

    # Words that carry no useful item signal
    _STOP_WORDS = {
        "which", "what", "does", "goes", "into", "the", "bin", "put",
        "use", "should", "for", "and", "with", "this", "that", "my", "where",
    }

    def __init__(self, guidance_path: Path) -> None:
        self.guidance_path = Path(guidance_path)
        self.entries: list[dict[str, Any]] = []
        self.fallback: str = self.DEFAULT_FALLBACK
        self._load()

    # ── Public ─────────────────────────────────────────────────────────────────

    def lookup(self, text: str) -> str | None:
        """Return the first matching guidance answer, or None."""
        normalized = normalize_text(text)
        for entry in self.entries:
            keywords = entry.get("keywords", [])
            answer   = str(entry.get("answer", "")).strip()
            if not answer or not isinstance(keywords, list):
                continue
            for kw in keywords:
                if normalize_text(str(kw)) and normalize_text(str(kw)) in normalized:
                    return answer
        return None

    def build_reply(self, text: str, session_id: str, finalise_fn) -> dict[str, Any]:
        """
        Attempt a keyword lookup and build a styled multi-bubble reply.

        Args:
            text:         Raw user message.
            session_id:   Active session ID (passed through to finalise_fn).
            finalise_fn:  ChatEngine._finalise_response — keeps coupling minimal.
        """
        item_name  = self._extract_item_name(text)
        answer     = self.lookup(text) or self.fallback
        bubbles    = format_recycling_guidance_messages(answer, item_name)
        return finalise_fn(build_messages_reply(bubbles), session_id=session_id)

    # ── Private ─────────────────────────────────────────────────────────────────

    def _load(self) -> None:
        if not self.guidance_path.exists():
            print(f"WARNING: bin guidance file not found: {self.guidance_path}")
            return
        try:
            with open(self.guidance_path, encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                self.entries  = data.get("entries", []) if isinstance(data.get("entries"), list) else []
                fallback_raw  = str(data.get("fallback_answer", "")).strip()
                if fallback_raw:
                    self.fallback = fallback_raw
            elif isinstance(data, list):
                self.entries = data
            else:
                print("WARNING: bin guidance data has unexpected format.")
        except Exception as exc:
            print(f"WARNING: failed to load bin guidance data: {exc}")

    def _extract_item_name(self, text: str) -> str:
        """Pick the first content word from the query as the item label."""
        for word in text.lower().split():
            if len(word) > 3 and word not in self._STOP_WORDS:
                return word
        return ""
