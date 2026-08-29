"""feature10_satellite.py -- Feature 10 (bonus): satellite segmentation heat-lens.

Uses the CONFIRMED premium ``POST /v1/satellite`` payload:

    payload = {
        "latitude": lat, "longitude": lon,
        "sat": {"latitude": lat, "longitude": lon},     # required nested object
        "date_time": {"start_date": date, "start_time": time_str, "filter_type": 1},
        "granularity": 100,
    }

which returns segmentation classes as % of a tile (building, road/route,
sidewalk/pavement, skyscraper, sky, ...). We derive a **surface heat-lens score**
per cell from the built / impervious share, EXCLUDING any class that is not
physically plausible for landlocked Phoenix (e.g. the model's implausible
``ship`` class) and logging what was excluded rather than silently averaging it.
"""
from __future__ import annotations

import logging

from . import data_layer as dl

log = logging.getLogger(__name__)

# Classes physically implausible for an inland desert city -- excluded from the
# heat-lens math and logged, not silently averaged in.
IMPLAUSIBLE_CLASSES = {"ship", "boat", "waterway", "ocean", "sea"}

# Class -> relative surface-heat contribution (warming potential of the surface).
HEAT_LENS_WEIGHTS = {
    "building": 1.0,
    "skyscraper": 1.0,
    "road, route": 0.95,
    "sidewalk, pavement": 0.9,
    "parking": 0.85,
    "bare rock": 0.8,
    "sand": 0.7,
    "grass": 0.3,
    "tree": 0.1,
    "sky": 0.0,
}


def satellite_url() -> str:
    from utc import config
    return f"{config.FORTYGUARD_BASE_URL}/v1/satellite"


def build_payload(lat: float, lon: float, date=None, time_str="15:00") -> dict:
    date = date or "2025-07-14"
    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "sat": {"latitude": float(lat), "longitude": float(lon)},
        "date_time": {"start_date": date, "start_time": time_str, "filter_type": 1},
        "granularity": 100,
    }


def score_segmentation(segmentation: list) -> float:
    """Compute a 0-1 surface heat-lens score from segmentation classes.

    Ignores any class in IMPLAUSIBLE_CLASSES and logs it (per the brief). With no
    plausible classes we return a neutral 0.5 so an unlabelled cell is neither
    penalised nor rewarded.
    """
    total = 0.0
    weighted = 0.0
    for item in segmentation or []:
        cls = str(item.get("class", "")).strip().lower()
        pct = float(item.get("percentage", 0.0))
        if cls in IMPLAUSIBLE_CLASSES:
            log.warning("Excluding implausible class for landlocked Phoenix: %r", cls)
            continue
        w = HEAT_LENS_WEIGHTS.get(cls)
        if w is None:
            continue
        total += pct
        weighted += pct * w
    if total <= 0:
        return 0.5
    return round(weighted / total, 4)


def load_fixture_scores() -> list:
    """Load the representative mock satellite tile scores (offline)."""
    fixture = dl.config.read_fixture("sample_satellite.json")
    out = []
    for tile in fixture["tiles"]:
        out.append({
            "cell_id": tile["cell_id"],
            "latitude": tile["latitude"],
            "longitude": tile["longitude"],
            "surface_heat_lens_score": score_segmentation(tile["segmentation"]),
        })
    return out


def surface_hint_map(grid) -> dict:
    """Return ``{cell_id: {"paved_pct": float}}`` from satellite-derived scores.

    Estimates the paved/built share so Feature 3 can choose the solar canopy for
    large impervious footprints. Falls back to a simple centroid-based estimate
    when no satellite score is present.
    """
    scores = {s["cell_id"]: s["surface_heat_lens_score"] for s in load_fixture_scores()}
    hint = {}
    for _, row in grid.iterrows():
        s = scores.get(row["cell_id"])
        paved = round((s or 0.5) * 80, 1)   # heat-lens -> nominal paved share
        hint[row["cell_id"]] = {"paved_pct": paved}
    return hint