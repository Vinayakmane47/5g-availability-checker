from __future__ import annotations
import math
import numpy as np
from typing import Tuple
from config import LAT0, LON0

_COS_LAT0 = math.cos(math.radians(LAT0))
_KM_PER_DEG_LAT = 110.574
_KM_PER_DEG_LON = 111.320 * _COS_LAT0


def to_xy_km(lat: np.ndarray, lon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    x = (lon - LON0) * _KM_PER_DEG_LON
    y = (lat - LAT0) * _KM_PER_DEG_LAT
    return x, y


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0088
    p = math.pi / 180
    dlat = (lat2 - lat1) * p
    dlon = (lon2 - lon1) * p
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin(dlon / 2) ** 2)
    return 2 * R * math.asin(math.sqrt(a))
