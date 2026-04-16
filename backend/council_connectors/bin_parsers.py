from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from bs4 import BeautifulSoup, NavigableString, Tag

from .bin_local import clean_text


def looks_like_postcode(text: str) -> bool:
    return bool(re.search(r"\b[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}\b", text or "", re.I))


def looks_like_day_date(text: str) -> bool:
    if not text:
        return False

    value = clean_text(text)
    return bool(
        re.search(r"^(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b", value, re.I)
        or re.search(
            r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            value,
            re.I,
        )
        or re.search(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", value)
        or re.search(r"\b\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}\b", value)
        or re.search(r"\b[A-Z][a-z]{2}\s+[A-Z][a-z]{2}\s+\d{1,2}\s+\d{4}\b", value)
    )


def looks_like_address(text: str) -> bool:
    if not text:
        return False

    t = clean_text(text)
    if len(t) < 8:
        return False

    lower = t.lower()
    blocked = {
        "select this address",
        "select address",
        "find address",
        "find addresses",
        "please select the adddress for the property",
        "please select the address for the property",
        "please choose one",
        "contact us online",
        "find a property",
        "privacy notice",
        "close",
        "opens in a new window",
        "bradford household bin collection dates",
        "show collection dates",
        "search again",
        "search for another address",
        "save",
        "save address",
        "print/save collection dates",
        "print/save with images",
        "print/save without images",
        "find out more",
        "bradford council",
        "bmdc",
        "cookies",
        "accessibility",
        "a to z",
        "how we use your information",
    }
    if lower in blocked:
        return False

    if lower.startswith("http://") or lower.startswith("https://"):
        return False

    has_digit = any(ch.isdigit() for ch in t)
    has_postcode = looks_like_postcode(t)
    has_street_word = bool(
        re.search(
            r"\b(street|road|avenue|drive|lane|close|place|court|crescent|way|terrace|grove)\b",
            t,
            re.I,
        )
    )
    has_comma = "," in t

    return has_digit and (has_postcode or has_street_word or has_comma)


def find_all_forms(soup: BeautifulSoup) -> List[Tag]:
    return soup.find_all("form")


def find_main_form(soup: BeautifulSoup) -> Optional[Tag]:
    forms = find_all_forms(soup)
    if not forms:
        return None

    for form in forms:
        if form.find(["input", "select", "button", "a", "textarea"]) is not None:
            return form
    return forms[0]


def form_action_url(form: Tag, base_url: str) -> str:
    action = form.get("action") or ""
    return urljoin(base_url, action) if action else base_url


def extract_base_payload(form: Tag) -> Dict[str, str]:
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
            selected_value = ""
            options = field.find_all("option")
            for option in options:
                if option.has_attr("selected"):
                    selected_value = option.get("value", "")
                    break
            if not selected_value and options:
                selected_value = options[0].get("value", "")
            payload[name] = selected_value

    return payload


def find_submit_control(form: Tag) -> Dict[str, str]:
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


def find_postcode_field_name(form: Tag) -> Optional[str]:
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
    seen: set[str] = set()
    deduped: List[Dict[str, str]] = []

    for item in items:
        key = f"{item.get('id', '')}|{item.get('label', '')}".strip().lower()
        if key and key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def extract_line_like_text(text: str) -> List[str]:
    cleaned = clean_text(text)
    if not cleaned:
        return []
    parts = [p.strip(" ,:-|") for p in re.split(r"\s{2,}|\n|\r", cleaned)]
    parts = [p for p in parts if p]
    return parts or [cleaned]


def extract_address_label_from_link_context(link: Tag) -> str:
    link_text = clean_text(link.get_text(" ", strip=True))
    candidates: List[str] = []

    for sibling in link.previous_siblings:
        if isinstance(sibling, NavigableString):
            text = clean_text(str(sibling))
            if text:
                candidates.extend(extract_line_like_text(text))
        elif isinstance(sibling, Tag):
            text = clean_text(sibling.get_text(" ", strip=True))
            if text:
                candidates.extend(extract_line_like_text(text))

    for container in [link.parent, link.find_parent(["li", "tr", "td", "p", "div"])]:
        if not container:
            continue

        container_text = clean_text(container.get_text(" ", strip=True))
        if container_text:
            stripped = container_text.replace(link_text, "").strip(" ,:-|")
            if stripped:
                candidates.extend(extract_line_like_text(stripped))

        for child in container.find_all(["span", "div", "p", "td", "label", "strong"]):
            child_text = clean_text(child.get_text(" ", strip=True))
            if child_text and child_text.lower() != link_text.lower():
                candidates.extend(extract_line_like_text(child_text))

    prev_tag = link.find_previous(["span", "strong", "label", "td", "div", "p"])
    if prev_tag:
        prev_text = clean_text(prev_tag.get_text(" ", strip=True))
        if prev_text:
            candidates.extend(extract_line_like_text(prev_text))

    unique_candidates: List[str] = []
    seen = set()
    for item in candidates:
        value = clean_text(item)
        if value and value.lower() not in seen:
            seen.add(value.lower())
            unique_candidates.append(value)

    for candidate in unique_candidates:
        if looks_like_address(candidate) and looks_like_postcode(candidate):
            return candidate
    for candidate in unique_candidates:
        if looks_like_address(candidate):
            return candidate
    return ""


def parse_address_options_and_cache(
    html: str,
    base_url: str,
    address_state_cache: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    form = find_main_form(soup)
    if form is None:
        return []

    action_url = form_action_url(form, base_url=base_url)
    base_payload = extract_base_payload(form)
    submit_control = find_submit_control(form)

    address_state_cache.clear()

    for select in form.find_all("select"):
        name = select.get("name")
        if not name:
            continue

        results: List[Dict[str, str]] = []
        for option in select.find_all("option"):
            value = clean_text(option.get("value"))
            label = clean_text(option.get_text(" ", strip=True))

            if not value or not label:
                continue

            lowered = label.lower()
            if lowered in {"select", "please select"}:
                continue
            if lowered.startswith("select ") and not looks_like_address(label):
                continue
            if not looks_like_address(label):
                continue

            address_state_cache[value] = {
                "mode": "form_choice",
                "action_url": action_url,
                "form_payload": dict(base_payload),
                "address_field_name": name,
                "choice_value": value,
                "label": label,
                "submit_control": dict(submit_control),
            }
            results.append({"uprn": value, "id": value, "label": label})

        if results:
            return dedupe_results(results)

    radios = form.find_all(
        "input",
        attrs={"type": lambda v: isinstance(v, str) and v.lower() == "radio"},
    )
    if radios:
        results = []
        for radio in radios:
            name = radio.get("name")
            value = clean_text(radio.get("value"))
            if not name or not value:
                continue

            label = ""
            radio_id = radio.get("id")
            if radio_id:
                label_tag = form.find("label", attrs={"for": radio_id})
                if label_tag:
                    label = clean_text(label_tag.get_text(" ", strip=True))

            if not label and radio.parent:
                label = clean_text(radio.parent.get_text(" ", strip=True))

            if not looks_like_address(label):
                continue

            address_state_cache[value] = {
                "mode": "form_choice",
                "action_url": action_url,
                "form_payload": dict(base_payload),
                "address_field_name": name,
                "choice_value": value,
                "label": label,
                "submit_control": dict(submit_control),
            }
            results.append({"uprn": value, "id": value, "label": label})

        return dedupe_results(results)

    results = []
    seen_labels: set[str] = set()
    synthetic_index = 0

    for link in form.find_all("a", href=True):
        href = clean_text(link.get("href"))
        if not href or href.lower().startswith("javascript:"):
            continue

        link_text = clean_text(link.get_text(" ", strip=True)).lower()
        if any(
            phrase in link_text
            for phrase in [
                "show collection dates",
                "search again",
                "find out more",
                "privacy notice",
                "close",
            ]
        ):
            continue

        label = extract_address_label_from_link_context(link)
        if not label or not looks_like_address(label):
            continue

        label_key = label.lower()
        if label_key in seen_labels:
            continue
        seen_labels.add(label_key)

        synthetic_id = f"address::{synthetic_index}"
        synthetic_index += 1

        full_url = urljoin(action_url, href)
        address_state_cache[synthetic_id] = {
            "mode": "shared_link_then_show",
            "action_url": full_url,
            "label": label,
        }
        results.append({"uprn": synthetic_id, "id": synthetic_id, "label": label})

    return dedupe_results(results)


def page_is_address_selection_page(html: str, address_state_cache: Dict[str, Dict[str, Any]]) -> bool:
    soup = BeautifulSoup(html, "html.parser")
    text = clean_text(soup.get_text(" ", strip=True)).lower()

    signals = [
        "please select the adddress for the property",
        "please select the address for the property",
        "find a property",
        "please enter the property postcode",
    ]
    if any(signal in text for signal in signals):
        return True

    labels = [
        clean_text(state.get("label", "")).lower()
        for state in address_state_cache.values()
        if isinstance(state, dict) and state.get("label")
    ]
    if labels:
        hits = sum(1 for label in labels if label and label in text)
        if hits >= 3:
            return True

    return False


def page_contains_final_results(soup: BeautifulSoup) -> bool:
    """
    True only when the page clearly shows actual collection dates.
    Uses strong multi-word phrases to avoid false positives on
    navigation links or newsletter text that mention 'waste'.
    """
    text = clean_text(soup.get_text(" ", strip=True)).lower()

    # Very specific phrases that only appear on the results page
    strong_phrases = [
        "your next general/recycling collections are",
        "print/save collection dates",
        "collectors are in a",   # Bradford-specific table header
        "collectors are on a",
    ]
    if any(p in text for p in strong_phrases):
        return True

    # Weaker phrases — require TWO of them to reduce false positives
    weak_phrases = ["general waste", "recycling waste", "garden waste"]
    hits = sum(1 for p in weak_phrases if p in text)
    return hits >= 2


def extract_show_dates_action(html: str, current_url: str) -> Optional[Tuple[str, str, Dict[str, str]]]:
    """
    Scan *html* for a 'Show collection dates' control and return
    (method, url, payload) needed to submit it, or None if not found.

    Checks in order:
      1. <a> links whose text contains the phrase
      2. <button> / <input type=submit> inside any <form>
      3. Any submit control inside a form that looks like an address-confirmation page
         (fallback for when the button label differs slightly)
    """
    soup = BeautifulSoup(html, "html.parser")

    # ── 1. Link-style button ────────────────────────────────────────────────
    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" ", strip=True)).lower()
        href = clean_text(link.get("href"))
        if "show collection dates" in text and href and not href.lower().startswith("javascript:"):
            return ("get", urljoin(current_url, href), {})

    # ── 2. Form-based submit controls ───────────────────────────────────────
    for form in find_all_forms(soup):
        action_url = form_action_url(form, base_url=current_url)
        payload    = extract_base_payload(form)

        # <button> elements
        for button in form.find_all("button"):
            btn_text  = clean_text(button.get_text(" ", strip=True)).lower()
            btn_value = clean_text(button.get("value", "")).lower()
            name      = button.get("name")

            if "show collection dates" in btn_text or "show collection dates" in btn_value:
                post_payload = dict(payload)
                if name:
                    post_payload[name] = button.get("value") or button.get_text(" ", strip=True) or "Submit"
                return ("post", action_url, post_payload)

        # <input type="submit|button|image">
        for inp in form.find_all("input"):
            inp_type = (inp.get("type") or "text").lower()
            if inp_type not in {"submit", "button", "image"}:
                continue

            inp_value = clean_text(inp.get("value", "")).lower()
            name      = inp.get("name")

            if "show collection dates" in inp_value:
                post_payload = dict(payload)
                if name:
                    post_payload[name] = inp.get("value", "Submit")
                return ("post", action_url, post_payload)

    # ── 3. Fallback: address-confirmation page with any forward submit ───────
    # Bradford's eBridge form shows "You have selected the following address"
    # then a submit button. If we reach here the button label didn't match,
    # so we pick the first submit that is NOT "Search again".
    page_text = soup.get_text(" ", strip=True).lower()
    is_confirmation = (
        "you have selected the following address" in page_text
        or "property address" in page_text
    ) and "show collection dates" not in page_text  # avoid looping

    if is_confirmation:
        for form in find_all_forms(soup):
            action_url = form_action_url(form, base_url=current_url)
            payload    = extract_base_payload(form)

            for inp in form.find_all("input"):
                inp_type  = (inp.get("type") or "text").lower()
                inp_value = clean_text(inp.get("value", "")).lower()
                name      = inp.get("name")

                if inp_type not in {"submit", "button", "image"}:
                    continue
                if "search again" in inp_value or "back" in inp_value:
                    continue

                post_payload = dict(payload)
                if name:
                    post_payload[name] = inp.get("value", "Submit")
                print(f"[BinParsers] Fallback: clicking submit '{inp.get('value')}' on confirmation page")
                return ("post", action_url, post_payload)

            for button in form.find_all("button"):
                btn_text = clean_text(button.get_text(" ", strip=True)).lower()
                name     = button.get("name")

                if "search again" in btn_text or "back" in btn_text:
                    continue

                post_payload = dict(payload)
                if name:
                    post_payload[name] = button.get("value") or button.get_text(" ", strip=True)
                print(f"[BinParsers] Fallback: clicking button '{btn_text}' on confirmation page")
                return ("post", action_url, post_payload)

    return None


def extract_address_label_from_result_page(lines: List[str]) -> str:
    for line in lines:
        if looks_like_address(line):
            return line
    return ""


def extract_next_collection(lines: List[str]) -> str:
    for i, line in enumerate(lines):
        if "your next general/recycling collections are" in line.lower():
            for j in range(i + 1, min(i + 8, len(lines))):
                candidate = lines[j]
                lower = candidate.lower()
                if "please ensure that your bin is out" in lower:
                    break
                if "waste" in lower and (" on " in lower or looks_like_day_date(candidate)):
                    return candidate
    return ""


def extract_garden_message(lines: List[str]) -> str:
    for line in lines:
        lower = line.lower()
        if "not currently subscribed" in lower:
            return line
        if "garden waste collections" in lower and "subscribe" in lower:
            return line
    return ""


def extract_section_dates(lines: List[str], section_title: str) -> List[str]:
    dates: List[str] = []
    start_index = -1

    for i, line in enumerate(lines):
        if line.strip().lower() == section_title.strip().lower():
            start_index = i
            break

    if start_index == -1:
        return dates

    stop_titles = {
        "general waste",
        "recycling waste",
        "garden waste (subscription only)",
        "print/save collection dates",
        "additional bin collection information (all links open in a new window)",
    }

    for j in range(start_index + 1, len(lines)):
        line = lines[j]
        lower = line.lower()

        if j > start_index + 1 and (lower in stop_titles or lower.startswith("print/save")):
            break

        if looks_like_day_date(line):
            dates.append(line)

    deduped: List[str] = []
    seen = set()
    for item in dates:
        key = item.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    return deduped


def parse_collection_results(html: str) -> Dict[str, Any]:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text("\n", strip=True)
    lines = [clean_text(line) for line in text.splitlines() if clean_text(line)]

    address_label = extract_address_label_from_result_page(lines)
    next_collection = extract_next_collection(lines)
    garden_message = extract_garden_message(lines)

    general_dates = extract_section_dates(lines, "General waste")
    recycling_dates = extract_section_dates(lines, "Recycling waste")
    garden_dates = extract_section_dates(lines, "Garden waste (subscription only)")

    collections: List[Dict[str, str]] = []
    if next_collection:
        collections.append({"bin_type": "Next collection", "date": next_collection})
    for date in general_dates:
        collections.append({"bin_type": "General waste", "date": date})
    for date in recycling_dates:
        collections.append({"bin_type": "Recycling waste", "date": date})
    for date in garden_dates:
        collections.append({"bin_type": "Garden waste", "date": date})

    deduped: List[Dict[str, str]] = []
    seen = set()
    for item in collections:
        key = (
            item.get("bin_type", "").strip().lower(),
            item.get("date", "").strip().lower(),
        )
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    if not deduped:
        print("[BinLookupConnector] RESULT PAGE PREVIEW:")
        for line in lines[:120]:
            print(line)

        return {
            "success": False,
            "message": "I reached the council website, but I could not read the collection dates from the results page.",
            "collections": [],
            "next_collection": "",
            "garden_message": "",
            "raw_text": "\n".join(lines[:200]),
        }

    return {
        "success": True,
        "address": address_label,
        "address_label": address_label,
        "collections": deduped,
        "next_collection": next_collection,
        "garden_message": garden_message,
        "raw_text": "\n".join(lines[:200]),
    }