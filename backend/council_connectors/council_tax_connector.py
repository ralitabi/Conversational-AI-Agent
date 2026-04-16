from __future__ import annotations

import re
import threading
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

# In-process cache: cleaned postcode → address list
# Populated on first lookup; subsequent requests return instantly.
_address_cache: Dict[str, List[Dict[str, str]]] = {}
_cache_lock = threading.Lock()

# Cache for band results: property URL → band result dict
_band_cache: Dict[str, Dict[str, str]] = {}


class CouncilTaxConnector:
    BASE_URL   = "https://www.tax.service.gov.uk"
    SEARCH_URL = "https://www.tax.service.gov.uk/check-council-tax-band/search"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; Bradford Council Assistant/1.0)",
            "Accept-Language": "en-GB,en;q=0.9",
            "Connection": "keep-alive",
        })

    def _clean_postcode(self, postcode: str) -> str:
        return re.sub(r"\s+", "", postcode.strip().upper())

    def lookup_addresses(self, postcode: str) -> List[Dict[str, str]]:
        postcode = self._clean_postcode(postcode)

        # Return cached result immediately if available
        with _cache_lock:
            if postcode in _address_cache:
                return list(_address_cache[postcode])

        # First GET the search page
        page = self.session.get(self.SEARCH_URL, timeout=8)
        page.raise_for_status()

        soup = BeautifulSoup(page.text, "html.parser")

        # GOV.UK forms use hidden CSRF tokens
        payload: Dict[str, Any] = {}
        for inp in soup.select("input[type='hidden']"):
            name  = inp.get("name")
            value = inp.get("value", "")
            if name:
                payload[name] = value

        postcode_field = self._find_postcode_field_name(soup) or "postcode"
        payload[postcode_field] = postcode

        form       = soup.find("form")
        action     = form.get("action") if form else self.SEARCH_URL
        submit_url = urljoin(self.BASE_URL, action)

        result = self.session.post(submit_url, data=payload, timeout=8)
        result.raise_for_status()

        addresses = self._parse_search_results(result.text)

        # Store in cache
        with _cache_lock:
            _address_cache[postcode] = list(addresses)

        return addresses

    def _find_postcode_field_name(self, soup: BeautifulSoup) -> Optional[str]:
        for inp in soup.select("input"):
            name       = (inp.get("name") or "").strip()
            input_type = (inp.get("type") or "").strip().lower()
            if input_type in {"text", "search"} and "postcode" in name.lower():
                return name
        return None

    def _parse_search_results(self, html: str) -> List[Dict[str, str]]:
        soup      = BeautifulSoup(html, "html.parser")
        addresses: List[Dict[str, str]] = []

        rows = soup.select("table tbody tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            if len(cols) < 2:
                continue
            link         = row.find("a", href=True)
            address_text = cols[0].get_text(" ", strip=True)
            band_text    = cols[1].get_text(" ", strip=True)
            if not address_text:
                continue
            addresses.append({
                "id":    link["href"] if link else address_text,
                "label": address_text,
                "band":  band_text,
                "url":   urljoin(self.BASE_URL, link["href"]) if link else "",
            })

        if not addresses:
            for link in soup.find_all("a", href=True):
                text = link.get_text(" ", strip=True)
                href = link["href"]
                if text and self._looks_like_address(text):
                    addresses.append({
                        "id":    href,
                        "label": text,
                        "band":  "",
                        "url":   urljoin(self.BASE_URL, href),
                    })

        return addresses

    def _looks_like_address(self, text: str) -> bool:
        text = text.upper()
        return any(c.isdigit() for c in text) and "," in text

    def get_band_for_address(self, selected: Dict[str, str]) -> Dict[str, str]:
        # Band already in the results table — return immediately, no extra HTTP call
        if selected.get("band") and selected["band"].lower() not in {"", "deleted"}:
            return {
                "address":         selected.get("label", ""),
                "band":            selected["band"],
                "local_authority": "",
                "source_url":      selected.get("url", ""),
            }

        url = selected.get("url")
        if not url:
            raise ValueError("No property URL found for selected address.")

        # Check band cache
        with _cache_lock:
            if url in _band_cache:
                return dict(_band_cache[url])

        res = self.session.get(url, timeout=8)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text("\n", strip=True)

        band_match      = re.search(r"Council Tax band\s*([A-H])", text, re.IGNORECASE)
        authority_match = re.search(r"Local authority\s*([A-Za-z .&'-]+)", text, re.IGNORECASE)

        result = {
            "address":         selected.get("label", ""),
            "band":            band_match.group(1).upper() if band_match else "",
            "local_authority": authority_match.group(1).strip() if authority_match else "",
            "source_url":      url,
        }

        with _cache_lock:
            _band_cache[url] = dict(result)

        return result
