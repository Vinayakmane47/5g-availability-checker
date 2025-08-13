from __future__ import annotations
import csv
import os
import threading
import numpy as np
from typing import List, Dict, Any
from models import MapPoint, EligibilityRow
from utils import to_xy_km, haversine_km


class ResultsIndex:
    """Vectorized spatial index over results.csv with thread-safety."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ready = False
        self.addr: List[str] = []
        self.lat = np.array([])
        self.lon = np.array([])
        self.x = np.array([])
        self.y = np.array([])
        self.elig = np.array([], dtype=bool)
        self.status: List[str] = []
        self.latency: List[str] = []
        self.checked_at: List[str] = []

    @staticmethod
    def _parse_bool(v: str) -> bool:
        if v is None:
            return False
        vv = str(v).strip().lower()
        return vv in ("true", "1", "yes", "y", "t")

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            with self._lock:
                self.__init__()
            return

        addrs, lats, lons = [], [], []
        elig, status, latency, checked_at = [], [], [], []

        with open(path, "r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                a = (row.get("address") or "").strip()
                if not a:
                    continue
                try:
                    la = float(row.get("lat"))
                    lo = float(row.get("lon"))
                except Exception:
                    continue
                addrs.append(a)
                lats.append(la)
                lons.append(lo)
                elig.append(self._parse_bool(row.get("eligible")))
                status.append((row.get("status_text") or "").strip())
                latency.append((row.get("latency_sec") or "").strip())
                checked_at.append((row.get("checked_at") or "").strip())

        with self._lock:
            if not addrs:
                self.ready = False
                return
            self.addr = addrs
            self.lat = np.asarray(lats, dtype=np.float64)
            self.lon = np.asarray(lons, dtype=np.float64)
            self.x, self.y = to_xy_km(self.lat, self.lon)
            self.elig = np.asarray(elig, dtype=bool)
            self.status = status
            self.latency = latency
            self.checked_at = checked_at
            self.ready = True

    def nearest_eligible(self, lat: float, lon: float, k: int) -> List[Dict[str, Any]]:
        with self._lock:
            if not self.ready or len(self.addr) == 0:
                return []
            tx, ty = to_xy_km(np.array([lat]), np.array([lon]))
            d2 = (self.x - tx[0]) ** 2 + (self.y - ty[0]) ** 2
            idx = np.where(self.elig)[0]
            if idx.size == 0:
                return []
            k = min(k, idx.size)
            sub = d2[idx]
            part = np.argpartition(sub, k - 1)[:k]
            choose = idx[part[np.argsort(sub[part])]]

            out = []
            for i in choose:
                out.append(
                    {
                        "addr": self.addr[i],
                        "lat": float(self.lat[i]),
                        "lon": float(self.lon[i]),
                        "eligible": True,
                        "status_text": self.status[i],
                        "latency_sec": self.latency[i],
                        "checked_at": self.checked_at[i],
                        "distance_km": haversine_km(lat, lon, float(self.lat[i]), float(self.lon[i])),
                    }
                )
            return out


class InputIndex:
    """Spatial index over input.csv used by the live map path."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.ready = False
        self.addr: List[str] = []
        self.lat = np.array([])
        self.lon = np.array([])
        self.x = np.array([])
        self.y = np.array([])

    def load(self, path: str) -> None:
        if not os.path.exists(path):
            with self._lock:
                self.__init__()
            return
        addrs, lats, lons = [], [], []
        with open(path, "r", newline="", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                a = (row.get("address") or "").strip()
                if not a:
                    continue
                try:
                    la = float(row.get("lat"))
                    lo = float(row.get("lon"))
                except Exception:
                    continue
                addrs.append(a)
                lats.append(la)
                lons.append(lo)
        if not addrs:
            with self._lock:
                self.__init__()
            return
        with self._lock:
            self.addr = addrs
            self.lat = np.asarray(lats, dtype=np.float64)
            self.lon = np.asarray(lons, dtype=np.float64)
            self.x, self.y = to_xy_km(self.lat, self.lon)
            self.ready = True

    def nearest(self, lat: float, lon: float, k: int) -> List[MapPoint]:
        with self._lock:
            if not self.ready or not self.addr:
                return []
            tx, ty = to_xy_km(np.array([lat]), np.array([lon]))
            d2 = (self.x - tx[0]) ** 2 + (self.y - ty[0]) ** 2
            k = min(k, d2.shape[0])
            if k <= 0:
                return []
            idx_k = np.argpartition(d2, k - 1)[:k]
            idx_k = idx_k[np.argsort(d2[idx_k])]
            return [MapPoint(self.addr[i], float(self.lat[i]), float(self.lon[i])) for i in idx_k]
