"""
Bradford school finder connector.

Searches the curated schools_list.json dataset by name, area, or type.
Supports optional postcode-based distance sorting via postcodes.io.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.postcode_distance import add_distances


_SCHOOLS_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "datasets" / "school_admissions" / "schools_list.json"
)


def _load_schools() -> List[Dict[str, Any]]:
    try:
        with open(_SCHOOLS_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"[SchoolConnector] Failed to load schools list: {exc}")
        return []


def _normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _score_school(school: Dict[str, Any], tokens: List[str]) -> int:
    name_norm  = _normalize(school.get("name", ""))
    area_norm  = _normalize(school.get("area", ""))
    phase_norm = _normalize(school.get("phase", ""))
    type_norm  = _normalize(school.get("type", ""))

    score = 0
    for token in tokens:
        if token in name_norm:
            score += 5
        if token in area_norm:
            score += 4
        if token in phase_norm:
            score += 3
        if token in type_norm:
            score += 2

    # Bonus for full phrase in name
    if " ".join(tokens) in name_norm:
        score += 10

    return score


class SchoolConnector:
    """Search Bradford schools and optionally sort by distance from a postcode."""

    def __init__(self) -> None:
        self._schools: List[Dict[str, Any]] = _load_schools()

    def search(
        self,
        query: str,
        phase_filter: Optional[str] = None,
        postcode: Optional[str] = None,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Search schools by name / area / type.

        If *postcode* is provided, each result includes a 'distance_miles' field
        and results are sorted nearest-first (with score as tiebreaker).
        """
        tokens = _normalize(query).split()

        # Detect phase keywords in query
        phase_override: Optional[str] = None
        cleaned_tokens: List[str] = []
        for tok in tokens:
            if tok in {"primary", "junior", "infant"}:
                phase_override = "Primary"
            elif tok in {"secondary", "high", "grammar", "college"}:
                phase_override = "Secondary"
            else:
                cleaned_tokens.append(tok)

        effective_phase = phase_filter or phase_override
        candidates = list(self._schools)

        if effective_phase:
            filtered = [
                s for s in candidates
                if s.get("phase", "").lower() == effective_phase.lower()
            ]
            if filtered:
                candidates = filtered

        # Score
        search_tokens = cleaned_tokens if cleaned_tokens else tokens
        scored = [
            (school, _score_school(school, search_tokens))
            for school in candidates
        ]
        scored = [(s, sc) for s, sc in scored if sc > 0]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [s for s, _ in scored[:max_results]] if scored else candidates[:max_results]

        # Add distance if postcode given
        if postcode:
            results = self._add_distances(results, postcode)
            results.sort(key=lambda s: (s.get("distance_miles") or 9999))

        return results

    def get_by_id(self, school_id: str) -> Optional[Dict[str, Any]]:
        for school in self._schools:
            if school.get("id") == school_id:
                return school
        return None

    def get_all(self, phase_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        if phase_filter:
            return [s for s in self._schools if s.get("phase", "").lower() == phase_filter.lower()]
        return list(self._schools)

    def nearest_to_postcode(
        self,
        postcode: str,
        phase_filter: Optional[str] = None,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """Return schools sorted by distance from *postcode*."""
        candidates = self.get_all(phase_filter)
        candidates = self._add_distances(candidates, postcode)
        candidates = [s for s in candidates if s.get("distance_miles") is not None]
        candidates.sort(key=lambda s: s.get("distance_miles") or 9999)
        return candidates[:max_results]

    # ─── internal ────────────────────────────────────────────────────────────

    def _add_distances(
        self,
        schools: List[Dict[str, Any]],
        postcode: str,
    ) -> List[Dict[str, Any]]:
        # One HTTP call for the postcode, then pure maths for each item
        return add_distances(schools, postcode)


# Singleton
_connector = SchoolConnector()


def search_schools(
    query: str,
    phase_filter: Optional[str] = None,
    postcode: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return _connector.search(query, phase_filter=phase_filter, postcode=postcode)


def get_school_by_id(school_id: str) -> Optional[Dict[str, Any]]:
    return _connector.get_by_id(school_id)


def nearest_schools(
    postcode: str,
    phase_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    return _connector.nearest_to_postcode(postcode, phase_filter=phase_filter)
