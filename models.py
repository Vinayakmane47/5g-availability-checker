from __future__ import annotations
from dataclasses import dataclass
from typing import Optional


@dataclass
class MapPoint:
    addr: str
    lat: float
    lon: float


@dataclass
class EligibilityRow:
    addr: str
    lat: float
    lon: float
    eligible: bool
    status_text: str
    latency_sec: str
    checked_at: str