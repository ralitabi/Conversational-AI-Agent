"""
Local (JSON) bin data lookup — shared helpers used by bin_parsers.py and bin_lookup.py.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


def normalize_postcode(value: Optional[str]) -> str:
    if not value:
        return ""
    text = str(value).strip().upper()
    text = re.sub(r"\s+", "", text)
    if len(text) > 3:
        text = f"{text[:-3]} {text[-3:]}"
    return text


def clean_text(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


class LocalBinData:
    """Loads address lists from the local datasets/bin_collection/bin_lookup.json."""

    def __init__(self, current_file: str) -> None:
        self.lookup_file = (
            Path(current_file).resolve().parent.parent.parent
            / "datasets"
            / "bin_collection"
            / "bin_lookup.json"
        )
        self.lookup_data = self._load_lookup_data()

    def _load_lookup_data(self) -> List[Dict]:
        if not self.lookup_file.exists():
            print(f"[BinLocal] Local lookup file not found: {self.lookup_file}")
            return []
        try:
            with self.lookup_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            print(f"[BinLocal] Failed to load local data: {exc}")
            return []

    def lookup(self, postcode: str) -> List[Dict[str, str]]:
        target = normalize_postcode(postcode)
        for entry in self.lookup_data:
            if normalize_postcode(entry.get("postcode")) != target:
                continue
            results: List[Dict[str, str]] = []
            for address in entry.get("addresses", []):
                if not isinstance(address, dict):
                    continue
                address_id = str(address.get("id", "")).strip()
                label = str(address.get("label", "")).strip()
                if address_id and label:
                    results.append({"uprn": address_id, "id": address_id, "label": label})
            return results
        return []
