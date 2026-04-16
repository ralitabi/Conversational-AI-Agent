"""
Bradford library finder connector.

Searches the curated libraries_list.json dataset by name, area, or service.
Supports optional postcode-based distance sorting via postcodes.io.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.utils.postcode_distance import add_distances


_LIBRARIES_FILE = (
    Path(__file__).resolve().parent.parent.parent
    / "datasets" / "libraries" / "libraries_list.json"
)


def _load_libraries() -> List[Dict[str, Any]]:
    try:
        with open(_LIBRARIES_FILE, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"[LibraryConnector] Failed to load libraries list: {exc}")
        return []


def _normalize(text: str) -> str:
    text = (text or "").lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _score_library(library: Dict[str, Any], tokens: List[str]) -> int:
    name_norm    = _normalize(library.get("name", ""))
    area_norm    = _normalize(library.get("area", ""))
    address_norm = _normalize(library.get("address", ""))
    services     = " ".join(library.get("services", []))
    services_norm = _normalize(services)

    score = 0
    for token in tokens:
        if token in name_norm:
            score += 5
        if token in area_norm:
            score += 4
        if token in address_norm:
            score += 2
        if token in services_norm:
            score += 3

    # Bonus for full phrase in name
    if " ".join(tokens) in name_norm:
        score += 10

    return score


class LibraryConnector:
    """Search Bradford libraries and optionally sort by distance from a postcode."""

    def __init__(self) -> None:
        self._libraries: List[Dict[str, Any]] = _load_libraries()

    def search(
        self,
        query: str,
        service_filter: Optional[str] = None,
        postcode: Optional[str] = None,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """
        Search libraries by name / area / service type.

        If *postcode* is provided, each result includes a 'distance_miles' field
        and results are sorted nearest-first (with score as tiebreaker).
        """
        tokens = _normalize(query).split()

        candidates = list(self._libraries)

        if service_filter:
            filtered = [
                lib for lib in candidates
                if service_filter.lower() in [s.lower() for s in lib.get("services", [])]
            ]
            if filtered:
                candidates = filtered

        # Score
        scored = [
            (library, _score_library(library, tokens))
            for library in candidates
        ]
        scored = [(lib, sc) for lib, sc in scored if sc > 0]
        scored.sort(key=lambda x: x[1], reverse=True)

        results = [lib for lib, _ in scored[:max_results]] if scored else candidates[:max_results]

        # Add distance if postcode given
        if postcode:
            results = self._add_distances(results, postcode)
            results.sort(key=lambda lib: (lib.get("distance_miles") or 9999))

        return results

    def get_by_id(self, lib_id: str) -> Optional[Dict[str, Any]]:
        for library in self._libraries:
            if library.get("id") == lib_id:
                return library
        return None

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self._libraries)

    def nearest_to_postcode(
        self,
        postcode: str,
        max_results: int = 6,
    ) -> List[Dict[str, Any]]:
        """Return libraries sorted by distance from *postcode*."""
        candidates = self.get_all()
        candidates = self._add_distances(candidates, postcode)
        candidates = [lib for lib in candidates if lib.get("distance_miles") is not None]
        candidates.sort(key=lambda lib: lib.get("distance_miles") or 9999)
        return candidates[:max_results]

    # ─── internal ────────────────────────────────────────────────────────────

    def _add_distances(
        self,
        libraries: List[Dict[str, Any]],
        postcode: str,
    ) -> List[Dict[str, Any]]:
        # One HTTP call for the postcode, then pure maths for each item
        return add_distances(libraries, postcode)


# Singleton
_connector = LibraryConnector()


def search_libraries(
    query: str,
    service_filter: Optional[str] = None,
    postcode: Optional[str] = None,
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    return _connector.search(query, service_filter=service_filter, postcode=postcode, max_results=max_results)


def get_library_by_id(lib_id: str) -> Optional[Dict[str, Any]]:
    return _connector.get_by_id(lib_id)


def nearest_libraries(
    postcode: str,
    max_results: int = 6,
) -> List[Dict[str, Any]]:
    return _connector.nearest_to_postcode(postcode, max_results=max_results)
