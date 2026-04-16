from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


START_URL = (
    "https://onlineforms.bradford.gov.uk/ufs/collectiondates.eb"
    "?ebd=0&ebp=20&ebz=1_1775594560015"
)


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


def looks_like_address(text: str) -> bool:
    text = clean_text(text)
    if not text:
        return False

    lower = text.lower()

    blocked = {
        "select",
        "please select",
        "select address",
        "find address",
        "search",
        "submit",
        "continue",
    }
    if lower in blocked:
        return False

    has_digit = any(ch.isdigit() for ch in text)
    has_address_word = any(
        word in lower
        for word in [
            "road",
            "street",
            "avenue",
            "drive",
            "lane",
            "close",
            "place",
            "court",
            "crescent",
            "way",
            "terrace",
            "grove",
            "rise",
            "hill",
        ]
    )

    return has_digit and ("," in text or has_address_word)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-GB,en;q=0.9",
        }
    )
    return session


def get_page(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def post_form(session: requests.Session, url: str, payload: Dict[str, str]) -> str:
    response = session.post(url, data=payload, timeout=30)
    response.raise_for_status()
    return response.text


def find_main_form(soup: BeautifulSoup):
    forms = soup.find_all("form")
    if not forms:
        return None

    for form in forms:
        if form.find(["input", "select", "button", "textarea"]) is not None:
            return form

    return forms[0]


def form_action_url(form, base_url: str) -> str:
    action = form.get("action") or ""
    return urljoin(base_url, action) if action else base_url


def extract_base_payload(form) -> Dict[str, str]:
    payload: Dict[str, str] = {}

    for field in form.find_all(["input", "textarea", "select"]):
        name = field.get("name")
        if not name:
            continue

        tag_name = field.name.lower()

        if tag_name == "input":
            input_type = (field.get("type") or "text").lower()
            if input_type in {"hidden", "text", "search", "email", "tel"}:
                payload[name] = field.get("value", "")
            elif input_type in {"radio", "checkbox"} and field.has_attr("checked"):
                payload[name] = field.get("value", "on")

        elif tag_name == "textarea":
            payload[name] = field.text or ""

        elif tag_name == "select":
            options = field.find_all("option")
            selected_value = ""
            for option in options:
                if option.has_attr("selected"):
                    selected_value = option.get("value", "")
                    break
            if not selected_value and options:
                selected_value = options[0].get("value", "")
            payload[name] = selected_value

    return payload


def find_submit_control(form) -> Dict[str, str]:
    submit_input = form.find(
        "input",
        attrs={"type": lambda v: isinstance(v, str) and v.lower() in {"submit", "image"}},
    )
    if submit_input and submit_input.get("name"):
        return {submit_input.get("name"): submit_input.get("value", "Submit")}

    button = form.find("button")
    if button and button.get("name"):
        return {
            button.get("name"): button.get("value", button.get_text(" ", strip=True) or "Submit")
        }

    return {}


def find_postcode_field_name(form) -> Optional[str]:
    candidates: List[str] = []

    for field in form.find_all(["input", "textarea"]):
        tag_name = field.name.lower()
        input_type = (field.get("type") or "text").lower()

        if tag_name == "input" and input_type not in {"text", "search"}:
            continue

        name = field.get("name", "")
        field_id = field.get("id", "")
        placeholder = field.get("placeholder", "")
        label_text = ""

        if field_id:
            label = form.find("label", attrs={"for": field_id})
            if label:
                label_text = label.get_text(" ", strip=True)

        haystack = " ".join([name, field_id, placeholder, label_text]).lower()

        if "postcode" in haystack or "street" in haystack or "property" in haystack:
            return name

        if name:
            candidates.append(name)

    return candidates[0] if candidates else None


def dedupe_results(items: List[Dict[str, str]]) -> List[Dict[str, str]]:
    seen = set()
    output: List[Dict[str, str]] = []

    for item in items:
        key = (
            str(item.get("id", "")).strip().lower(),
            str(item.get("label", "")).strip().lower(),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(item)

    return output


def parse_addresses(html: str, base_url: str) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    results: List[Dict[str, str]] = []

    form = find_main_form(soup)

    if form:
        for select in form.find_all("select"):
            for option in select.find_all("option"):
                value = clean_text(option.get("value"))
                label = clean_text(option.get_text(" ", strip=True))

                if not value or not label:
                    continue
                if looks_like_address(label):
                    results.append(
                        {
                            "uprn": value,
                            "id": value,
                            "label": label,
                        }
                    )

        for radio in form.find_all(
            "input",
            attrs={"type": lambda v: isinstance(v, str) and v.lower() == "radio"},
        ):
            value = clean_text(radio.get("value"))
            if not value:
                continue

            label = ""
            radio_id = radio.get("id")

            if radio_id:
                label_tag = form.find("label", attrs={"for": radio_id})
                if label_tag:
                    label = clean_text(label_tag.get_text(" ", strip=True))

            if not label and radio.parent:
                label = clean_text(radio.parent.get_text(" ", strip=True))

            if looks_like_address(label):
                results.append(
                    {
                        "uprn": value,
                        "id": value,
                        "label": label,
                    }
                )

    for link in soup.find_all("a", href=True):
        href = clean_text(link.get("href"))
        label = clean_text(link.get_text(" ", strip=True))

        if href and looks_like_address(label):
            results.append(
                {
                    "uprn": href,
                    "id": href,
                    "label": label,
                }
            )

    return dedupe_results(results)


class LocalBinData:
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
            print(f"[BinLookup] Local lookup file not found: {self.lookup_file}")
            return []

        try:
            with self.lookup_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as exc:
            print(f"[BinLookup] Failed to load local lookup data: {exc}")
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
                    results.append(
                        {
                            "uprn": address_id,
                            "id": address_id,
                            "label": label,
                        }
                    )

            return dedupe_results(results)

        return []


class BinLookup:
    def __init__(self) -> None:
        self.session = build_session()
        self.local = LocalBinData(__file__)

    def search_addresses(self, postcode: str) -> List[Dict[str, str]]:
        postcode = normalize_postcode(postcode)

        if not postcode:
            return []

        # local first = more reliable for your project/demo
        local_results = self.local.lookup(postcode)
        print(f"[BinLookup] LOCAL RESULTS: {local_results}")
        if local_results:
            return local_results

        # live fallback
        try:
            html = get_page(self.session, START_URL)

            soup = BeautifulSoup(html, "html.parser")
            form = find_main_form(soup)
            if form is None:
                raise RuntimeError("Could not find postcode form.")

            action_url = form_action_url(form, START_URL)
            payload = extract_base_payload(form)

            field_name = find_postcode_field_name(form)
            if not field_name:
                raise RuntimeError("Could not find postcode field.")

            payload[field_name] = postcode
            payload.update(find_submit_control(form))

            result_html = post_form(self.session, action_url, payload)
            print("[BinLookup] LIVE HTML PREVIEW:")
            print(result_html[:2000])

            addresses = parse_addresses(result_html, action_url)
            print(f"[BinLookup] LIVE PARSED ADDRESSES: {addresses}")

            return addresses

        except Exception as exc:
            print(f"[BinLookup] Live lookup failed: {exc}")
            return []


_default_connector = BinLookup()


def search_addresses_by_postcode(postcode: str) -> List[Dict[str, str]]:
    return _default_connector.search_addresses(postcode)