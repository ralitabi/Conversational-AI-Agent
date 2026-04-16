"""
Full Bradford Council bin collection connector.

Flow:
  1. search_addresses(postcode) -> list of addresses + stores form state in address_cache
  2. get_collection_dates(address_id, address_cache) -> actual dates parsed from the results page
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup

from .bin_http import START_URL, build_session, get_page, post_form, post_form_with_url
from .bin_local import LocalBinData, normalize_postcode
from .bin_parsers import (
    extract_show_dates_action,
    find_main_form,
    form_action_url,
    extract_base_payload,
    find_submit_control,
    find_postcode_field_name,
    page_contains_final_results,
    parse_address_options_and_cache,
    parse_collection_results,
)


class BinConnector:
    """
    Handles the two-step bin date lookup:
      Step 1 — postcode → address list (with cached form state)
      Step 2 — address selection → actual collection dates
    """

    def __init__(self) -> None:
        self.http = build_session()
        self.local = LocalBinData(__file__)

    # -------------------------------------------------------------------------
    # Step 1: Postcode → address list
    # -------------------------------------------------------------------------

    def search_addresses(
        self,
        postcode: str,
        address_state_cache: Dict[str, Dict[str, Any]],
    ) -> List[Dict[str, str]]:
        """
        Return a list of addresses for the given postcode.
        Populates address_state_cache so Step 2 can fetch dates without
        re-entering the postcode.

        Returns: list of {"uprn": ..., "id": ..., "label": ...}
        """
        postcode = normalize_postcode(postcode)
        if not postcode:
            return []

        # Local JSON fallback first (no form state cached in this path)
        local_results = self.local.lookup(postcode)
        if local_results:
            print(f"[BinConnector] LOCAL results for {postcode}: {len(local_results)}")
            return local_results

        # Live scraping
        try:
            html = get_page(self.http, START_URL)
            soup = BeautifulSoup(html, "html.parser")
            form = find_main_form(soup)
            if form is None:
                raise RuntimeError("Postcode form not found on start page.")

            action_url = form_action_url(form, START_URL)
            payload = extract_base_payload(form)

            field_name = find_postcode_field_name(form)
            if not field_name:
                raise RuntimeError("Postcode input field not found.")

            payload[field_name] = postcode
            payload.update(find_submit_control(form))

            result_html = post_form(self.http, action_url, payload)
            print("[BinConnector] Postcode submitted — parsing address options")

            addresses = parse_address_options_and_cache(
                result_html, action_url, address_state_cache
            )
            print(f"[BinConnector] LIVE addresses: {len(addresses)}")
            return addresses

        except Exception as exc:
            print(f"[BinConnector] search_addresses failed: {exc}")
            return []

    # -------------------------------------------------------------------------
    # Step 2: Address selection → collection dates
    # -------------------------------------------------------------------------

    def get_collection_dates(
        self,
        address_id: str,
        address_state_cache: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Use cached form state to fetch and parse bin collection dates.

        Returns a dict from parse_collection_results or None on failure.
        """
        state = address_state_cache.get(address_id)
        if state is None:
            print(f"[BinConnector] No cached state for address_id={address_id!r}")
            return None

        try:
            mode = state.get("mode", "")
            current_url = state.get("action_url", "")

            if mode == "form_choice":
                # Submit the address selection form
                payload: Dict[str, str] = dict(state.get("form_payload", {}))
                field_name   = state.get("address_field_name", "")
                choice_value = state.get("choice_value", "")
                submit_ctrl  = state.get("submit_control", {})

                if field_name:
                    payload[field_name] = choice_value
                payload.update(submit_ctrl)

                result_html, current_url = post_form_with_url(self.http, current_url, payload)
                print(f"[BinConnector] After address select → URL: {current_url}")

            elif mode == "shared_link_then_show":
                result_html = get_page(self.http, current_url)

            else:
                print(f"[BinConnector] Unknown mode: {mode!r}")
                return None

            # ── Step 3: click "Show collection dates" if we are on the confirmation page ──
            soup = BeautifulSoup(result_html, "html.parser")

            if page_contains_final_results(soup):
                print("[BinConnector] Dates already on page — skipping Show button click")
            else:
                page_snippet = soup.get_text(" ", strip=True)[:300].lower()
                print(f"[BinConnector] Confirmation page snippet: {page_snippet[:200]!r}")

                show_action = extract_show_dates_action(result_html, current_url)

                if show_action:
                    method, show_url, show_payload = show_action
                    print(f"[BinConnector] Clicking Show dates — method={method} url={show_url}")
                    if method == "post":
                        result_html, current_url = post_form_with_url(
                            self.http, show_url, show_payload
                        )
                    else:
                        result_html = get_page(self.http, show_url)
                        current_url = show_url
                else:
                    print("[BinConnector] WARNING: could not find 'Show collection dates' control")

            return parse_collection_results(result_html)

        except Exception as exc:
            print(f"[BinConnector] get_collection_dates failed: {exc}")
            return None


# Singleton
_connector = BinConnector()


def search_addresses_by_postcode(
    postcode: str,
    address_state_cache: Dict[str, Dict[str, Any]],
) -> List[Dict[str, str]]:
    return _connector.search_addresses(postcode, address_state_cache)


def get_dates_for_address(
    address_id: str,
    address_state_cache: Dict[str, Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    return _connector.get_collection_dates(address_id, address_state_cache)
