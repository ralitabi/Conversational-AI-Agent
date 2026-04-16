"""
Postcode to coordinates lookup and haversine distance calculator.
Uses postcodes.io (free, no API key required).

Postcode resolutions are cached in-process so repeated lookups for the same
postcode (e.g. once per library during distance sorting) cost only one HTTP
call rather than one per item.
"""
from __future__ import annotations

import math
from typing import Dict, List, Optional, Tuple, Any

import requests

_POSTCODES_IO = "https://api.postcodes.io/postcodes/{postcode}"
_TIMEOUT = 5   # tight timeout — fail fast rather than hang

# In-process cache: cleaned postcode → (lat, lon) or None
_cache: Dict[str, Optional[Tuple[float, float]]] = {}


def postcode_to_latlon(postcode: str) -> Optional[Tuple[float, float]]:
    """
    Convert a UK postcode to (latitude, longitude) using postcodes.io.
    Results are cached so the same postcode is only fetched once per process.
    Returns None if the postcode is invalid or the request fails.
    """
    cleaned = postcode.replace(" ", "").upper()
    if cleaned in _cache:
        return _cache[cleaned]

    try:
        resp = requests.get(
            _POSTCODES_IO.format(postcode=cleaned),
            timeout=_TIMEOUT,
        )
        if resp.status_code != 200:
            _cache[cleaned] = None
            return None
        data = resp.json()
        if data.get("status") != 200:
            _cache[cleaned] = None
            return None
        result = data.get("result", {})
        lat = result.get("latitude")
        lon = result.get("longitude")
        if lat is None or lon is None:
            _cache[cleaned] = None
            return None
        coords = (float(lat), float(lon))
        _cache[cleaned] = coords
        return coords
    except Exception as exc:
        print(f"[PostcodeDistance] Failed to resolve {postcode!r}: {exc}")
        _cache[cleaned] = None
        return None


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return the great-circle distance in miles between two lat/lon points."""
    R = 3958.8
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi    = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def add_distances(
    items: List[Dict[str, Any]],
    postcode: str,
    lat_key: str = "lat",
    lon_key: str = "lon",
) -> List[Dict[str, Any]]:
    """
    Resolve *postcode* ONCE, then compute haversine distances for all items.

    This replaces the old pattern of calling distance_from_postcode() once per
    item (which made one HTTP request per item). Now it's one HTTP request total.

    Returns the same list with a 'distance_miles' key added to each item.
    """
    coords = postcode_to_latlon(postcode)
    if coords is None:
        return [{**item, "distance_miles": None} for item in items]

    user_lat, user_lon = coords
    result = []
    for item in items:
        lat = item.get(lat_key)
        lon = item.get(lon_key)
        if lat is not None and lon is not None:
            dist: Optional[float] = round(haversine_miles(user_lat, user_lon, float(lat), float(lon)), 1)
        else:
            dist = None
        result.append({**item, "distance_miles": dist})
    return result


# Legacy single-item helper — kept for backwards compatibility but now uses the cache
def distance_from_postcode(postcode: str, item_lat: float, item_lon: float) -> Optional[float]:
    """
    Return distance in miles from *postcode* to a point at (item_lat, item_lon).
    The postcode is cached so repeated calls for the same postcode are instant.
    """
    coords = postcode_to_latlon(postcode)
    if coords is None:
        return None
    lat, lon = coords
    return round(haversine_miles(lat, lon, item_lat, item_lon), 1)
