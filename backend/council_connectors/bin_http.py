"""
HTTP session helpers for Bradford Council bin date scraping.
"""
from __future__ import annotations

import random
import time
from typing import Dict

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


START_URL = (
    "https://onlineforms.bradford.gov.uk/ufs/collectiondates.eb"
    "?ebd=0&ebp=20&ebz=1_1775594560015"
)


def build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-GB,en;q=0.9",
        }
    )
    return session


def sleep_briefly() -> None:
    time.sleep(random.uniform(0.3, 0.8))


def get_page(session: requests.Session, url: str) -> str:
    response = session.get(url, timeout=30)
    response.raise_for_status()
    return response.text


def post_form(session: requests.Session, url: str, payload: Dict[str, str]) -> str:
    sleep_briefly()
    response = session.post(url, data=payload, timeout=30)
    response.raise_for_status()
    return response.text


def post_form_with_url(
    session: requests.Session,
    url: str,
    payload: Dict[str, str],
) -> tuple[str, str]:
    """
    Same as post_form but also returns the final URL after any redirects.
    Returns (html, final_url).
    """
    sleep_briefly()
    response = session.post(url, data=payload, timeout=30)
    response.raise_for_status()
    return response.text, response.url
