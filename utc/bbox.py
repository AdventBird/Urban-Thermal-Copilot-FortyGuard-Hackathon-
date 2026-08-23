"""bbox.py -- downtown Phoenix polygon for ZIP codes 85004 + 85007.

The Create Heatmap API expects a GeoJSON ``FeatureCollection`` wrapping one
``Feature`` whose geometry is a closed-ring ``Polygon``:

  * coordinates are always ``[longitude, latitude]`` (not lat/lon);
  * the ring MUST close -- first and last coordinate pair identical -- or
    FortyGuard rejects the payload.

When possible we fetch the real ZIP boundary from Nominatim (OpenStreetMap).
If the network is unreachable (common during judging) we fall back to a
deterministic, documented rectangle covering both ZIPs, comfortably under
FortyGuard's ~130 km^2 / 50 mp2 AOI cap.
"""
from __future__ import annotations

import hashlib
import json
import math
import warnings
from typing import Optional


# ---------------------------------------------------------------------------
# Fallback rectangle (offline): spans 85004 (downtown core) west to 85007
# (state-capitol district). Project Web-Mercator lon/lat order, ring closed.
# ---------------------------------------------------------------------------
_FALLBACK_RING: list[list[float]] = [
    [-112.1450, 33.4350],
    [-112.0600, 33.4350],
    [-112.0600, 33.4800],
    [-112.1450, 33.4800],
    [-112.1450, 33.4350],  # closes the ring (first == last)
]

# Approximate center of the two-ZIP area (map-centering help).
PHOENIX_CENTER_LAT, PHOENIX_CENTER_LON = 33.4575, -112.1025


def close_ring(ring) -> list[list[float]]:
    """Return a ring whose first/last lon/lat pair are identical (idempotent)."""
    out = [list(p) for p in ring]
    if out and out[0] != out[-1]:
        out.append(list(out[0]))
    return out


def to_ring(value) -> list[list[float]]:
    """Normalize several accepted shapes into a *closed* lon/lat ring.

    Accepted:
      * a sequence of ``[lon, lat]`` pairs (closed or unclosed),
      * a GeoPandas GeoSeries/GeoDataFrame whose first row is a ring polygon.
    """
    if hasattr(value, "geometry"):  # GeoDataFrame / GeoSeries -> exterior ring
        geom = value.geometry.iloc[0]
        if geom.geom_type != "Polygon":
            geom = geom.buffer(0)
        return close_ring([list(c) for c in geom.exterior.coords])
    ring = [[float(x), float(y)] for (x, y) in value]
    if len(ring) < 4:
        raise ValueError("A ring needs at least 4 coordinate pairs.")
    return close_ring(ring)


def fallback_ring() -> list[list[float]]:
    """Return a fresh copy of the documented offline rectangle for 85004+85007."""
    return [list(p) for p in _FALLBACK_RING]


def try_nominatim_ring(zips=("85004", "85007"), timeout=1.0) -> list | None:
    """Fetch a real ZIP-boundary poly from Nominatim; return a closed ring or None.

    Iterates each ZIP code, keeps the largest usable polygon (still under the
    AOI cap), and returns nothing on any error so the caller can fall back.
    """
    try:
        import requests
    except ImportError:
        return None
    best_ring, best_area = None, 0.0
    for zip_code in zips:
        try:
            resp = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "postalcode": zip_code,
                    "country": "United States",
                    "format": "json",
                    "polygon_geojson": "1",
                    "limit": "5",
                },
                headers={"User-Agent": "urban-thermal-copilot-hackathon/1.0"},
                timeout=timeout,
            )
            resp.raise_for_status()
            for row in resp.json():
                gj = row.get("geojson") or {}
                if gj.get("type") != "Polygon":
                    continue
                ring = close_ring(gj["coordinates"][0])
                area = area_km2(ring)
                if 0.0 < area < 10.0 and area > best_area:  # keep the largest real ZIP
                    best_area, best_ring = area, ring
        except Exception as exc:
            warnings.warn(f"Nominatim lookup failed for {zip_code}: {exc!r}")
    return best_ring


def build_ring(use_live=False) -> list[list[float]]:
    """Return the demo ring -- real ZIP boundary if requested/available, else the rectangle."""
    if use_live:
        live = try_nominatim_ring()
        if live:
            return live
        warnings.warn("Nominatim unavailable; using the documented offline rectangle.")
    return fallback_ring()


def area_km2(ring) -> float:
    """Approximate planar area (km^2) of a lon/lat ring, enough to check the AOI cap."""
    r = to_ring(ring)
    xs = [p[0] for p in r]
    ys = [p[1] for p in r]
    m_per_deg_lon = 111_320.0 * math.cos(math.radians(sum(ys) / len(ys)))
    m_per_deg_lat = 111_320.0
    return ((max(xs) - min(xs)) * m_per_deg_lon) * ((max(ys) - min(ys)) * m_per_deg_lat) / 1e6
def build_feature_collection(ring) -> dict:
    """Wrap a closed ring into the exact FeatureCollection shape Create Heatmap expects.

    Printed JSON matches the confirmed API contract::

        polygon_aoi -> FeatureCollection -> Feature -> Polygon -> closed ring
    """
    ring = to_ring(ring)
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {"type": "Polygon", "coordinates": [ring]},
            }
        ],
    }


def bbox_hash(ring) -> str:
    """Stable, short cache key for a ring (first 8 hex digits of a SHA-256)."""
    r = to_ring(ring)
    encoded = json.dumps(r, separators=(",", ":"), sort_keys=True).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:8]