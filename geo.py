from __future__ import annotations
from typing import List, Dict, Any, Tuple
import requests
import overpy
from config import USER_AGENT


# geo.py
from typing import Tuple
import time
import requests
from config import USER_AGENT

_GEOCODE_ENDPOINT = "https://nominatim.openstreetmap.org/search"

def _try_query(params) -> list:
    resp = requests.get(_GEOCODE_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    # Graceful handling of 429 / 5xx
    if resp.status_code in (429, 502, 503, 504):
        time.sleep(1.2)  # Nominatim etiquette: ≤1 req/sec
        resp = requests.get(_GEOCODE_ENDPOINT, params=params, headers={"User-Agent": USER_AGENT}, timeout=20)
    resp.raise_for_status()
    return resp.json()

def geocode_address(address: str) -> Tuple[float, float]:
    """
    Robust geocoder with AU bias + fallbacks.
    Raises ValueError if nothing could be geocoded.
    """
    q = (address or "").strip()
    if not q:
        raise ValueError("Empty address")

    # Normalize simple cases (add region/country if user omitted them)
    fallbacks = [
        q,
        f"{q}, VIC",
        f"{q}, Melbourne, VIC",
        f"{q}, Victoria, Australia",
        f"{q}, Australia",
    ]

    # Base params: AU bias, JSON v2
    base = {
        "format": "jsonv2",
        "limit": 3,
        "addressdetails": 0,
        "countrycodes": "au",
    }

    last_err = None
    for candidate in fallbacks:
        try:
            data = _try_query({**base, "q": candidate})
            if data:
                return float(data[0]["lat"]), float(data[0]["lon"])
        except Exception as e:
            last_err = e
            continue

    # Final attempt without country bias (in case it really isn't AU)
    try:
        data = _try_query({**base, "q": q, "countrycodes": None})
        if data:
            return float(data[0]["lat"]), float(data[0]["lon"])
    except Exception as e:
        last_err = e

    raise ValueError("Address could not be geocoded")


def _format_addr(tags: dict) -> str:
    hn = (tags.get("addr:housenumber") or "").strip()
    st = (tags.get("addr:street") or "").strip()
    suburb = (
        tags.get("addr:suburb")
        or tags.get("addr:city")
        or tags.get("addr:town")
        or tags.get("addr:locality")
        or ""
    ).strip()
    pc = (tags.get("addr:postcode") or "").strip()

    parts = []
    if hn and st:
        parts.append(f"{hn} {st}")
    elif st:
        parts.append(st)
    if suburb:
        parts.append(suburb)
    parts.append("VIC")
    if pc:
        parts.append(pc)
    return " ".join(parts).strip()


def fetch_nearby_addresses(lat: float, lon: float, radius: int = 1000) -> List[str]:
    api = overpy.Overpass()
    query = f"""
    [out:json][timeout:60];
    (
      node["addr:housenumber"]["addr:street"](around:{radius},{lat},{lon});
      way["addr:housenumber"]["addr:street"](around:{radius},{lat},{lon});
    );
    out center tags;
    """
    result = api.query(query)
    addrs: List[str] = []

    for n in result.nodes:
        a = _format_addr(n.tags)
        if a:
            addrs.append(a)

    for w in result.ways:
        a = _format_addr(w.tags)
        if a:
            addrs.append(a)

    seen, out = set(), []
    for a in addrs:
        k = a.lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(a)
    return out


def fetch_addresses_in_bbox(bbox: Tuple[float, float, float, float], limit: int = 500) -> List[Dict[str, Any]]:
    south, west, north, east = bbox
    api = overpy.Overpass()
    query = f"""
    [out:json][timeout:120];
    (
      node["addr:housenumber"]["addr:street"]({south},{west},{north},{east});
      way["addr:housenumber"]["addr:street"]({south},{west},{north},{east});
    );
    out center tags;
    """
    result = api.query(query)
    rows: List[Dict[str, Any]] = []

    for n in result.nodes:
        a = _format_addr(n.tags)
        if a:
            rows.append({"addr": a, "lat": float(n.lat), "lon": float(n.lon)})

    for w in result.ways:
        a = _format_addr(w.tags)
        if a and hasattr(w, "center_lat") and hasattr(w, "center_lon"):
            rows.append({"addr": a, "lat": float(w.center_lat), "lon": float(w.center_lon)})

    seen, out = set(), []
    for r in rows:
        k = r["addr"].lower()
        if k in seen:
            continue
        seen.add(k)
        out.append(r)
        if len(out) >= limit:
            break
    return out
