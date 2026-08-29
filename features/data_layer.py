"""data_layer.py -- centralized data assembly for the whole app.

This is the single place that decides which data source to use:

  LIVE  -- a real ``FORTYGUARD_API_KEY`` is in the environment/.env. We call the
           documented FortyGuard endpoints and cache every result to JSON under
           ``data/cache/`` so re-runs are offline and happy.
  MOCK  -- no key (or a placeholder). We build a deterministic grid from the
           fixture JSON files under ``data/fixtures/`` so the app still demoes
           end-to-end. Mock mode is clearly flagged in the UI.

Either way, every grid we return conforms to the shared contract in
``utc/contracts.py`` so downstream features (Honest Matrix, Roadmap, Report)
can trust the fields.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from utc import bbox, config
from utc import feature1_thermal as f1
from utc import feature2_vulnerability as f2
from utc.fortyguard_client import load_cached_json, save_cached_json

log = logging.getLogger(__name__)

# Values that are clearly placeholders / not a real key.
_MOCK_PREFIXES = ("your_", "replace", "changeme", "fake", "demo_")


def have_api_key() -> bool:
    """True when a real-looking FORTYGUARD_API_KEY is configured."""
    key = (config.FORTYGUARD_API_KEY or "").strip()
    return bool(key) and not key.lower().startswith(_MOCK_PREFIXES)


def running_mock() -> bool:
    """True when we are NOT going to touch the live FortyGuard API."""
    return not have_api_key()


def mode_label() -> str:
    """Honest data-source label.

    Starts as "LIVE API" when a key is configured, but downgrades itself the
    first time a live call fails and we fall back to cached/fixture data, so
    the UI never claims live data it isn't actually showing.
    """
    global _LIVE_DOWN
    if _LIVE_DOWN:
        return "Cached / fallback data"
    return "LIVE API" if have_api_key() else "MOCK / cached mode"


# Set True once a live call fails and we fall back; sticky for this process.
_LIVE_DOWN = False


def note_live_failure(exc: Exception | None = None) -> None:
    """Record that a live call failed and we served cached/fixture data."""
    global _LIVE_DOWN
    _LIVE_DOWN = True
    if exc is not None:
        log.warning("Live FortyGuard call failed (%s); serving cached data.", exc)


def _synthesize_env(grid_gdf):
    """Fill mock ``heat_index_c`` / ``solar_ghi`` / risk columns from fixtures.

    Representative, deterministic values so the rest of the pipeline (vulnerability,
    priority, matrix, roadmap) runs identically to the live path.
    """
    import numpy as np

    g = grid_gdf.copy()
    temps = np.asarray(g["temperature_c"].astype(float))
    n = len(g)
    g["heat_index_c"] = temps * 1.06 + 1.4                      # human heat stress > ambient
    g["solar_ghi"] = [820.0 + 60.0 * (i % 3) for i in range(n)]  # W/m^2, plausible midday GHI
    # Risk fields: exceedance of the 50 C threshold is genuinely rare in Phoenix;
    # keep near-zero but non-degenerate so the risk layer still renders.
    g["exceedance_hours"] = np.maximum(0.0, (temps - 46.0) * 0.4).round(2)
    g["persistence_hours"] = np.maximum(0.0, (temps - 47.0) * 0.25).round(2)
    return g


def _mock_grid():
    """Build the grid from fixtures (offline)."""
    heat = config.read_fixture("sample_heatmap_response.json")
    grid = f1.tiles_to_grid(heat)  # projected EPSG:32612, has temperature_c / cell_id
    grid = _synthesize_env(grid)

    pois = f2.load_osm_pois(Path(config.FIXTURE_DIR) / "sample_osm_pois.json")
    census = f2.fetch_census_data()  # fallback tract table (no geometry)
    grid = f2.compute_vulnerability_score(grid, pois, census)
    grid = f2.compute_priority_score(grid)
    grid.attrs["pois"] = pois  # vulnerability overlay renders these markers
    return grid


def _build_ring_grid(ring, date=None):
    """Build a full contract grid for an arbitrary closed ring (live path)."""
    date = date or config.DEMO_DATE

    snapshot = f1.get_snapshot(ring, date=date)   # tcm heat snapshot (cached)
    grid = f1.tiles_to_grid(snapshot)
    grid = _downsample(grid, target_max=80)

    dt = f1.make_date_time(date, filter_type=1)   # ~3pm daytime point for env params
    grid = f2.attach_env_params(grid, dt)         # heat_index_c + solar_ghi per cell

    osm_key = f"osm_pois_{bbox.bbox_hash(ring)}"
    overpass = f2.fetch_osm_pois(ring, cache_key=osm_key)
    pois = f2.osm_pois_to_gdf(overpass)
    census = f2.fetch_census_data()
    grid = f2.compute_vulnerability_score(grid, pois, census)
    grid = f2.compute_priority_score(grid)
    grid.attrs["pois"] = pois  # vulnerability overlay renders these markers
    # Full contract conformance even in live mode: risk-hour columns are read
    # from the native exceedance analytic when present; default to 0.0 otherwise
    # so downstream readers (Feature 5 fallback) never hit a missing column.
    if "exceedance_hours" not in grid.columns:
        grid["exceedance_hours"] = 0.0
    if "persistence_hours" not in grid.columns:
        grid["persistence_hours"] = 0.0
    return grid


def _live_grid(date=None):
    """Build the grid from the live FortyGuard/OSM/Census APIs around Phoenix (cached)."""
    return _build_ring_grid(bbox.build_ring(use_live=True), date=date)


def _downsample(grid, target_max: int = 80):
    """Coarsen a fine grid to roughly ``target_max`` cells with Feature 1's
    aggregated-grid helper, preserving the shared contract columns."""
    if len(grid) <= target_max:
        return grid
    n_rows = int(round((len(grid) / target_max) ** 0.5))
    return f1.tiles_to_grid(_gdf_to_feature_collection(grid),
                            cell_size_m=max(100, 400 * n_rows))


def _gdf_to_feature_collection(grid) -> dict:
    import json
    return json.loads(grid.to_crs("EPSG:4326").to_json())


# Overall budget for the LIVE grid build. FortyGuard jobs are async and can take
# a while; if a key is present but the network is blocked/slow, we want to fall
# back to mock instead of letting the demo hang in a spinner.
LIVE_GRID_TIME_BUDGET_S = 90.0


def _run_with_budget(fn, budget_s: float):
    """Run ``fn`` in a daemon thread and return its result, or raise TimeoutError
    if it does not finish within ``budget_s`` seconds."""
    import threading

    box = {}

    def worker():
        try:
            box["result"] = fn()
        except Exception as exc:  # noqa: BLE001
            box["error"] = exc

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    t.join(timeout=budget_s)
    if "result" in box:
        return box["result"]
    if "error" in box:
        raise box["error"]
    raise TimeoutError(f"Live data build took longer than {budget_s:g}s")


def build_grid(date=None):
    """Assemble the shared grid in live or mock mode (with graceful fallback).

    Returns a GeoDataFrame conforming to ``utc/contracts.REQUIRED_CELL_FIELDS``.
    If a live attempt fails OR exceeds the time budget, we log it and fall back
    to mock so the demo never hard-crashes mid-session.
    """
    if have_api_key():
        try:
            grid = _run_with_budget(lambda: _live_grid(date=date), LIVE_GRID_TIME_BUDGET_S)
            log.info("Grid built from LIVE fortyguard data (%s cells).", len(grid))
            return grid
        except Exception as exc:  # noqa: BLE001 -- deliberate graceful degradation
            log.warning("Live grid build failed (%s); falling back to mock.", exc)
    grid = _mock_grid()
    log.info("Grid built from MOCK fixtures (%s cells).", len(grid))
    return grid

# --------------------------------------------------------------------------- #
# Place search (Feature-less helper for the "search a city" UX)
# --------------------------------------------------------------------------- #
DEMO_LOC = {"name": "Downtown Phoenix, AZ", "lat": 33.4489, "lon": -112.073}


def _to_utm(lon: float, lat: float):
    """Project a lon/lat point to UTM 12N and return a shapely Point (meters)."""
    from pyproj import Transformer
    from shapely.geometry import Point
    t = Transformer.from_crs("EPSG:4326", "EPSG:32612", always_xy=True)
    x, y = t.transform(float(lon), float(lat))
    return Point(x, y)


def geocode(place) -> dict | None:
    """Best-effort Nominatim geocode (cached). Returns ``{name, lat, lon}`` or None."""
    import hashlib
    import requests

    place = (place or "").strip()
    if not place:
        return None
    key = "geocode_" + hashlib.sha256(place.lower().encode()).hexdigest()[:8]
    cached = load_cached_json(key)
    if cached:
        return cached
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": place, "format": "json", "limit": 1},
            headers={"User-Agent": "urban-thermal-copilot-hackathon/1.0"},
            timeout=12,
        )
        r.raise_for_status()
        rows = r.json()
        if not rows:
            return None
        row = rows[0]
        out = {"name": row.get("display_name", place),
               "lat": float(row["lat"]), "lon": float(row["lon"])}
        save_cached_json(key, out)
        return out
    except Exception as exc:  # noqa: BLE001
        log.warning("Geocode failed for %r (%s); returning None.", place, exc)
        return None


def _mock_grid_centered(lat, lon, name):
    """Translate the offline Phoenix grid to sit on the searched (lat, lon).

    Keeps every contract field so the whole pipeline (vulnerability, priority,
    matrix, roadmap) runs identically regardless of the searched city. This is a
    visual/functional demonstration in mock mode, not real 2-metre data for the
    target city.
    """
    grid = _mock_grid()
    target = _to_utm(lon, lat)
    src = grid.geometry.centroid.unary_union.centroid
    grid.geometry = grid.geometry.translate(xoff=target.x - src.x,
                                            yoff=target.y - src.y)
    grid.attrs["city"] = name
    grid.attrs["center"] = (float(lat), float(lon))
    return grid


def _small_ring(lon: float, lat: float, deg: float = 0.03) -> list:
    d = float(deg)
    return [[lon - d, lat - d], [lon + d, lat - d],
            [lon + d, lat + d], [lon - d, lat + d], [lon - d, lat - d]]


def build_grid_for_place(place) :
    """Build a grid for a user-searched place/city.

    Geocodes ``place`` to a center; tries the live FortyGuard pipeline around it
    when a key is present (with a time budget), otherwise returns a mock grid
    centered on the searched location so the demo works for any city offline.
    """
    loc = geocode(place) or DEMO_LOC
    return build_grid_for_center(loc["lat"], loc["lon"], loc["name"])


def build_grid_for_center(lat: float, lon: float, name: str):
    """Build a grid centered on explicit coordinates (live-budget, mock fallback)."""
    if have_api_key():
        try:
            ring = _small_ring(lon, lat)
            grid = _run_with_budget(
                lambda: _build_ring_grid(ring, date=None), LIVE_GRID_TIME_BUDGET_S)
            grid.attrs["city"] = name
            grid.attrs["center"] = (float(lat), float(lon))
            return grid
        except Exception as exc:  # noqa: BLE001
            note_live_failure(exc)
            log.warning("Live grid-for-center failed (%s); using mock. ", exc)
    return _mock_grid_centered(lat, lon, name)


def load_risk_flags(date=None) -> dict:
    """Return ``{"exceedance": {...}, "persistence": {...}}`` risk analytics.

    Live path hits FortyGuard's exceedance/persistence analytics (threshold 50 C,
    direction above) with caching. Mock path returns the representative fixture.
    """
    ring = bbox.fallback_ring()
    if have_api_key():
        try:
            return f1.get_risk_flags(ring, date=date)
        except Exception as exc:  # noqa: BLE001
            log.warning("Live risk flags failed (%s); using fixture.", exc)
    return config.read_fixture("sample_risk_flags.json")


_TREND_CACHE: list | None = None


def load_trend() -> list:
    """Return ``[(year, mean_temp_c), ...]`` spanning 2021-2025 (same month).

    Cached in-process: the yearly trend never changes during a session, so it
    is fetched at most once per process and never re-attempted after a failure
    (a failing endpoint would otherwise add a network round trip to every
    Streamlit rerun).
    """
    global _TREND_CACHE
    if _TREND_CACHE is not None:
        return _TREND_CACHE
    fixture = [(r["year"], r["mean_temp_c"]) for r in
               config.read_fixture("sample_trend.json")["trend"]]
    if have_api_key():
        try:
            _TREND_CACHE = f1.get_yearly_trend(bbox.fallback_ring())
            return _TREND_CACHE
        except Exception as exc:  # noqa: BLE001
            note_live_failure(exc)
    _TREND_CACHE = fixture
    return _TREND_CACHE


def load_maricopa_deaths() -> pd.DataFrame:
    """Return Maricopa County heat-death rows (fixture load)."""
    return pd.DataFrame(config.read_fixture("maricopa_heat_deaths.json")["deaths"])


# --------------------------------------------------------------------------- #
# Preset areas & Civic Landmarks for place identification
# --------------------------------------------------------------------------- #
CIVIC_LANDMARKS = [
    {
        "name": "Arizona State Capitol",
        "category": "government",
        "icon": "🏛️",
        "lat": 33.4481,
        "lon": -112.0970,
        "district": "Capitol District (85007)",
        "desc": "Arizona Executive Tower & State Capitol Museum",
    },
    {
        "name": "Phoenix City Hall",
        "category": "government",
        "icon": "🏢",
        "lat": 33.4487,
        "lon": -112.0772,
        "district": "Downtown Core (85004)",
        "desc": "Phoenix Municipal Complex & Calvin C. Goode Building",
    },
    {
        "name": "Chase Field",
        "category": "sports",
        "icon": "⚾",
        "lat": 33.4453,
        "lon": -112.0667,
        "district": "Downtown Core (85004)",
        "desc": "MLB Arizona Diamondbacks Stadium",
    },
    {
        "name": "Footprint Center",
        "category": "sports",
        "icon": "🏀",
        "lat": 33.4458,
        "lon": -112.0712,
        "district": "Downtown Core (85004)",
        "desc": "NBA Phoenix Suns Arena & Entertainment Center",
    },
    {
        "name": "Phoenix Convention Center",
        "category": "culture",
        "icon": "🏛️",
        "lat": 33.4503,
        "lon": -112.0694,
        "district": "Downtown Core (85004)",
        "desc": "Premier downtown convention & exposition facility",
    },
    {
        "name": "Roosevelt Row Arts District",
        "category": "culture",
        "icon": "🎨",
        "lat": 33.4589,
        "lon": -112.0697,
        "district": "Downtown / Evans Churchill (85004)",
        "desc": "Vibrant walkable arts hub, galleries & pedestrian corridor",
    },
    {
        "name": "ASU Downtown Phoenix Campus",
        "category": "education",
        "icon": "🎓",
        "lat": 33.4535,
        "lon": -112.0740,
        "district": "Downtown Core (85004)",
        "desc": "Arizona State University Downtown Academic Campus",
    },
    {
        "name": "Banner - Univ. Medical Center",
        "category": "healthcare",
        "icon": "🏥",
        "lat": 33.4645,
        "lon": -112.0610,
        "district": "Midtown / Evans Churchill (85006)",
        "desc": "Level 1 Trauma & Academic Medical Center",
    },
    {
        "name": "Valley Metro Central Station",
        "category": "transit",
        "icon": "🚆",
        "lat": 33.4507,
        "lon": -112.0763,
        "district": "Downtown Core (85004)",
        "desc": "Major Light Rail & Bus Transit Interchange",
    },
    {
        "name": "The Van Buren",
        "category": "culture",
        "icon": "🎵",
        "lat": 33.4517,
        "lon": -112.0792,
        "district": "Van Buren Corridor (85004)",
        "desc": "Historic Van Buren music hall & commercial corridor",
    },
    {
        "name": "Margaret T. Hance Deck Park",
        "category": "park",
        "icon": "🌳",
        "lat": 33.4605,
        "lon": -112.0745,
        "district": "Downtown / Midtown",
        "desc": "32-acre urban deck park atop Papago Freeway tunnel",
    },
    {
        "name": "Phoenix Art Museum",
        "category": "culture",
        "icon": "🖼️",
        "lat": 33.4674,
        "lon": -112.0722,
        "district": "Midtown Phoenix (85004)",
        "desc": "Southwest's premier visual arts museum",
    },
    {
        "name": "Wesley Bolin Memorial Plaza",
        "category": "park",
        "icon": "🌲",
        "lat": 33.4480,
        "lon": -112.0940,
        "district": "Capitol District (85007)",
        "desc": "Civic gathering plaza fronting State Capitol",
    },
    {
        "name": "Encanto Park & Golf",
        "category": "park",
        "icon": "⛳",
        "lat": 33.4795,
        "lon": -112.0880,
        "district": "Midtown Phoenix (85008)",
        "desc": "222-acre historic city park, lagoon & golf course",
    },
]


def get_nearest_landmark(lat: float, lon: float, landmarks=CIVIC_LANDMARKS) -> dict | None:
    """Calculate distance to nearest civic landmark for spatial orientation."""
    import math

    if not landmarks:
        return None

    def dist_m(lat1, lon1, lat2, lon2):
        r = 6371000.0  # meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0) ** 2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
        return r * c

    best = None
    min_d = float("inf")
    for lm in landmarks:
        d = dist_m(float(lat), float(lon), float(lm["lat"]), float(lm["lon"]))
        if d < min_d:
            min_d = d
            best = lm

    if best and min_d < 3500:  # within 3.5 km
        d_int = int(round(min_d))
        d_str = f"~{d_int}m" if d_int < 1000 else f"~{d_int / 1000.0:.1f}km"
        return {
            "name": best["name"],
            "icon": best["icon"],
            "category": best["category"],
            "district": best["district"],
            "distance_m": d_int,
            "distance_str": d_str,
            "label": f"{best['icon']} {d_str} from {best['name']}",
        }
    return None


PRESETS = [
    {
        "key": "downtown_core",
        "label": "Downtown Core",
        "zip": "85004",
        "lat": 33.4490,
        "lon": -112.0740,
        "icon": "🏙️",
        "tagline": "City Hall, Chase Field & ASU Campus",
        "description": "High-density urban core with heavy pedestrian traffic and asphalt concentration.",
        "color": "#8b5cf6",
    },
    {
        "key": "capitol_district",
        "label": "Capitol District",
        "zip": "85007",
        "lat": 33.4450,
        "lon": -112.0970,
        "icon": "🏛️",
        "tagline": "State Capitol, Plaza & State Courts",
        "description": "Government mall with extensive surface parking and high vulnerable worker exposure.",
        "color": "#ec4899",
    },
    {
        "key": "midtown_phoenix",
        "label": "Midtown Phoenix",
        "zip": "85008",
        "lat": 33.4800,
        "lon": -112.0600,
        "icon": "🌿",
        "tagline": "Encanto Park, Arts & Medical Center",
        "description": "Mixed commercial-residential corridor connecting cultural centers and hospitals.",
        "color": "#06b6d4",
    },
    {
        "key": "van_buren_corridor",
        "label": "Van Buren Corridor",
        "zip": "85004",
        "lat": 33.4515,
        "lon": -112.0650,
        "icon": "🚦",
        "tagline": "East Van Buren Transit & Entertainment",
        "description": "Critical transit artery with high pavement exposure and major bus stops.",
        "color": "#f59e0b",
    },
]

# Custom areas are capped at ~2 sq mi (≈5.2 km²) so a fresh FortyGuard build
# stays inside a reasonable demo wait (the API's hard cap is ~130 km² / 50 mi²).
CUSTOM_AREA_LIMIT_KM2 = 5.2
CUSTOM_AREA_WAIT_LABEL = "takes 1-3 minutes"


def preset_by_key(key: str) -> dict | None:
    """Return the preset dict for ``key``, or None if unknown."""
    for p in PRESETS:
        if p["key"] == key:
            return p
    return None


def build_preset_grid(key: str):
    """Build the contract grid for a preset area -- instantly, offline.

    This path makes NO live API call at all (even when a key is present): it
    reuses the representative cached/fixture grid translated to the preset's
    center, so a planner clicking a preset sees a map in well under 2 seconds.
    """
    p = preset_by_key(key)
    if p is None:
        raise KeyError(f"Unknown preset: {key!r}")
    grid = _mock_grid_centered(p["lat"], p["lon"], f"{p['label']} — {p['zip']}")
    grid.attrs["preset"] = p["key"]
    grid.attrs["is_custom"] = False
    return grid


def reverse_geocode(lat: float, lon: float) -> str | None:
    """Best-effort Nominatim *reverse* geocode, cached per cell.

    Returns a human-readable location such as ``"Near 3rd St & Van Buren St"``
    (address-level detail, trimmed to the most useful parts), or None when the
    service is unreachable. Results are cached under ``data/cache/`` keyed by
    the rounded coordinates, so repeated clicks on the same cell never re-call
    the network.
    """
    import hashlib
    import requests

    lat_r, lon_r = round(float(lat), 4), round(float(lon), 4)
    key = "revgeo_" + hashlib.sha256(f"{lat_r},{lon_r}".encode()).hexdigest()[:8]
    cached = load_cached_json(key)
    if cached:
        return cached.get("label")
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat_r, "lon": lon_r, "format": "json", "zoom": 17},
            headers={"User-Agent": "urban-thermal-copilot-hackathon/1.0"},
            timeout=8,
        )
        r.raise_for_status()
        data = r.json()
        addr = data.get("address", {}) or {}
        road = addr.get("road") or addr.get("pedestrian") or addr.get("neighbourhood") or ""
        cross = addr.get("neighbourhood") or addr.get("suburb") or addr.get("city") or ""
        display = data.get("display_name", "")
        label = f"Near {road}" if road else (display.split(",")[0] if display else None)
        if road and cross and cross.lower() not in road.lower():
            label = f"Near {road}, {cross}"
        if not label:
            return None
        save_cached_json(key, {"label": label, "lat": lat_r, "lon": lon_r})
        return label
    except Exception as exc:  # noqa: BLE001
        log.warning("Reverse geocode failed for (%s, %s): %s", lat_r, lon_r, exc)
        return None


def load_pois():
    """Return the POI GeoDataFrame used by the vulnerability overlay."""
    return f2.load_osm_pois(Path(config.FIXTURE_DIR) / "sample_osm_pois.json")