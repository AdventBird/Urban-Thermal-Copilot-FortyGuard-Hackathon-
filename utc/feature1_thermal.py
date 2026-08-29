"""feature1_thermal.py -- Spatial Thermal Audit (heat snapshot + native risk flags).

Goal: for the fixed downtown Phoenix box, fetch
  * a plain ``tcm`` heat snapshot (deg C), and
  * FortyGuard's native ``exceedance`` / ``persistence`` risk analytics
with local-online caching, and render the snapshot as a color-coded map layer.

The function signatures are the stable handoff to later modules (Honest Matrix,
Roadmap). Keep names/arg order stable. Heavy deps (geopandas, shapely, folium)
are imported lazily inside the functions that need them so this module can be
imported and its pure parts tested in a bare environment.
"""
from __future__ import annotations

import logging

from . import bbox, config
from .fortyguard_client import (
    HEATMAP_URL,
    create_activity,
    load_cached_json,
    save_cached_json,
    submit_and_poll,
)

log = logging.getLogger(__name__)

# Candidate tile-property names that might hold the temperature value (the API
# bundles several projections; we detect the real one at runtime).
TEMP_COLUMN_CANDIDATES = ("temperature_c", "temp_c", "temperature", "mean", "value")


def make_date_time(
    date,
    filter_type: int = 3,
    start_time=None,
    end_time=None,
    end_date=None,
) -> dict:
    """Build a ``date_time`` block for a Create Heatmap call.

    filter_type semantics (per the confirmed contract):
        1 = single hour          (needs start_date + start_time)
        2 = hour range, same day (<= 23h; adds end_time)
        3 = single day           (start_date only)
        4 = day range (<= 1 mon) (adds end_date)
        5 = single month         (start_date = YYYY-MM-01)
    """
    date = str(date)
    block = {"filter_type": int(filter_type)}
    if filter_type == 5:
        yyyy, mm = date[:4], date.split("-")[1:2][0].zfill(2)
        block["start_date"] = f"{yyyy}-{mm}-01"
    else:
        block["start_date"] = date
    if filter_type in (1, 2):
        block["start_time"] = start_time or config.DEMO_TIME
        if filter_type == 2:
            block["end_time"] = end_time or config.DEMO_TIME
            block["end_date"] = end_date or date
    if filter_type == 4:
        block["end_date"] = end_date or date
    return block


def build_heatmap_payload(
    bbox_coords,
    date_time,
    granularity: int = config.DEMO_GRANULARITY,
    analytic_type: str = "tcm",
    threshold: float = 30.0,
    direction: str = "above",
) -> dict:
    """Assemble the exact JSON body Create Heatmap expects (closed-ring polygon)."""
    ring = bbox.to_ring(bbox_coords)
    return {
        "polygon_aoi": bbox.build_feature_collection(ring),
        "date_time": date_time,
        "granularity": int(granularity),
        "analytic_type": analytic_type,
        "threshold": float(threshold),
        "direction": direction,
    }


def submit_heatmap(
    bbox_coords,
    date_time,
    granularity: int = config.DEMO_GRANULARITY,
    analytic_type: str = "tcm",
    threshold: float = 30.0,
    direction: str = "above",
) -> str:
    """Submit a heatmap job; return the ``activity_id`` (no polling yet)."""
    payload = build_heatmap_payload(bbox_coords, date_time, granularity, analytic_type, threshold, direction)
    return create_activity(HEATMAP_URL, payload)


def fetch_heatmap(
    bbox_coords,
    date_time,
    granularity: int = config.DEMO_GRANULARITY,
    analytic_type: str = "tcm",
    threshold: float = 30.0,
    direction: str = "above",
    cache_key: str | None = None,
    timeout_s: float = 60.0,
) -> dict:
    """Submit+poll a heatmap, honoring the local cache.

    Returns the completed ``result`` dict (with ``map_data`` / ``stats_data``).
    If ``cache_key`` is given and already cached, we return the cache file
    without calling the API (offline-safe demo).
    """
    if cache_key:
        cached = load_cached_json(cache_key)
        if cached is not None:
            log.info("Using cached heatmap result for %s", cache_key)
            return cached
    payload = build_heatmap_payload(bbox_coords, date_time, granularity, analytic_type, threshold, direction)
    result = submit_and_poll(HEATMAP_URL, payload, timeout_s=timeout_s)
    if cache_key:
        save_cached_json(cache_key, result)
    return result


def _snapshot_date_time(date) -> dict:
    return make_date_time(date, filter_type=3)


def get_snapshot(
    bbox_coords,
    date=None,
    granularity: int = config.DEMO_GRANULARITY,
    timeout_s: float = 60.0,
) -> dict:
    """Return the plain ``tcm`` heat snapshot (cached)."""
    ring = bbox.to_ring(bbox_coords)
    date = date or config.DEMO_DATE
    key = f"heatmap_{bbox.bbox_hash(ring)}_{date}_tcm"
    return fetch_heatmap(ring, _snapshot_date_time(date), granularity=granularity, analytic_type="tcm", cache_key=key, timeout_s=timeout_s)


def get_risk_flags(
    bbox_coords,
    date=None,
    threshold: float = config.RISK_THRESHOLD_C,
    direction: str = "above",
    include_persistence: bool = True,
    timeout_s: float = 60.0,
) -> dict:
    """Fetch FortyGuard's own exceedance (+ optionally persistence) analytics.

    This REPLACES any homegrown threshold logic -- the values come from the API.
    Returns ``{"exceedance": result_dict, "persistence": result_dict|None}``.
    """
    ring = bbox.to_ring(bbox_coords)
    date = date or config.DEMO_DATE
    dt = _snapshot_date_time(date)
    out: dict = {}
    exc_key = f"heatmap_{bbox.bbox_hash(ring)}_{date}_exceedance"
    out["exceedance"] = fetch_heatmap(
        ring, dt, analytic_type="exceedance", threshold=threshold, direction=direction, cache_key=exc_key, timeout_s=timeout_s
    )
    if include_persistence:
        per_key = f"heatmap_{bbox.bbox_hash(ring)}_{date}_persistence"
        out["persistence"] = fetch_heatmap(
            ring, dt, analytic_type="persistence", threshold=threshold, direction=direction, cache_key=per_key, timeout_s=timeout_s
        )
    else:
        out["persistence"] = None
    return out
def _detect_temperature_column(columns) -> str | None:
    """Pick the tile property that most likely holds the Celsius value."""
    lowered = {str(c).lower(): c for c in columns}
    for candidate in TEMP_COLUMN_CANDIDATES:
        for low, original in lowered.items():
            if candidate in low:
                return original
    return None


def _aggregate_to_grid(g, cell_size_m: int):
    """Coarsen tiles by binning projected centroids onto a grid and averaging temps.

    Only used when the API tile count is impractically fine for downstream logic.
    This is an OPTIONAL step -- check tile count against a real response first.
    """
    import geopandas as gpd
    from shapely.geometry import box

    target_crs = g.crs  # already projected by caller
    gp = g.copy().to_crs(target_crs)
    c = gp.geometry.centroid
    size = int(cell_size_m)
    rows = []
    for (_, r), cx, cy in zip(gp.iterrows(), c.x, c.y):
        bx = int(cx // size)
        by = int(cy // size)
        cell = box(bx * size, by * size, bx * size + size, by * size + size)
        rows.append((bx, by, cell, float(r.get("temperature_c", 0.0))))
    import pandas as pd

    df = pd.DataFrame(rows, columns=["bx", "by", "geometry", "temperature_c"])
    grouped = df.groupby(["bx", "by"], as_index=False).agg(
        temperature_c=("temperature_c", "mean"), geometry=("geometry", "first")
    )
    gdf = gpd.GeoDataFrame(grouped, geometry="geometry", crs=g.crs)
    gdf["cell_id"] = [f"coarse_{int(bx)}_{int(by)}" for bx, by in zip(gdf.bx, gdf.by)]
    return gdf


def tiles_to_grid(map_data, temperature_col=None, cell_size_m=None, target_crs="EPSG:32612"):
    """Convert the API's ``map_data`` GeoJSON tiles into a projected GeoDataFrame.

    The API already tiles the AOI at the requested granularity, so this is a
    GeoJSON load + reproject (NOT a from-scratch downsampling algorithm). If the
    tile count is impractically fine, pass ``cell_size_m`` to average adjacent
    tiles into coarser cells (optional).

    Returns a GeoDataFrame in ``target_crs`` (default UTM 12N, meters) with at
    least: ``geometry``, ``temperature_c``, ``cell_id``.
    """
    import geopandas as gpd
    from shapely.geometry import shape

    fc = map_data.get("map_data") if isinstance(map_data, dict) and "map_data" in map_data else map_data
    feats = fc.get("features", [])
    rows = []
    for i, f in enumerate(feats):
        props = dict(f.get("properties") or {})
        props["geometry"] = shape(f["geometry"])
        props["__idx"] = i
        rows.append(props)
    g = gpd.GeoDataFrame(rows, crs="EPSG:4326") if rows else gpd.GeoDataFrame(columns=["geometry"])

    temp_col = temperature_col or _detect_temperature_column(g.columns)
    if temp_col is None:
        raise ValueError("Could not detect a temperature column in the tile properties.")

    if cell_size_m:
        g_proj = g.to_crs(target_crs)
        g_agg = _aggregate_to_grid(g_proj, cell_size_m)
        return g_agg
    g = g.to_crs(target_crs)
    g["temperature_c"] = g[temp_col].astype(float)
    if "cell_id" not in g.columns:
        g["cell_id"] = [f"tile_{i}" for i in range(len(g))]
    g["area_m2"] = g.geometry.area
    return g


def _viridis_hex() -> list[str]:
    """A small viridis-like colorblind-safe ramp (no red/green)."""
    return [
        "#440154", "#482878", "#3f4889", "#33698f", "#2f8a8a",
        "#28a87e", "#3fc26d", "#8cd05a", "#d4e046", "#fde725",
    ]


def render_heatmap(grid_gdf, temperature_col="temperature_c", zoom_start=13):
    """Render a color-coded, legend-carrying Folium map from a grid GeoDataFrame."""
    import folium
    import branca
    from pyproj import Transformer

    # Center computed in a projected CRS (avoid the geographic-centroid warning),
    # then converted back to WGS84 lon/lat for Folium.
    proj = grid_gdf.to_crs("EPSG:32612")
    mx = float(proj.geometry.centroid.x.mean())
    my = float(proj.geometry.centroid.y.mean())
    t = Transformer.from_crs("EPSG:32612", "EPSG:4326", always_xy=True)
    clon, clat = t.transform(mx, my)

    m = folium.Map(location=[float(clat), float(clon)], zoom_start=zoom_start, tiles="OpenStreetMap", control_scale=True)
    g = grid_gdf.to_crs("EPSG:4326")
    vals = list(g[temperature_col].dropna().astype(float))
    if not vals:
        return m
    vmin, vmax = min(vals), max(vals)

    cmap = branca.colormap.LinearColormap(
        colors=_viridis_hex(), vmin=vmin, vmax=vmax,
        caption="FortyGuard tcm ambient temp (deg C)",
    )

    def style(feature):
        v = float(feature["properties"][temperature_col])
        return {"fillColor": cmap(v), "color": "#444444", "weight": 0.5, "fillOpacity": 0.7}

    folium.GeoJson(g, name="Heat map", style_function=style).add_to(m)
    cmap.add_to(m)
    folium.LayerControl().add_to(m)
    return m


def _extract_mean_temp(result: dict) -> float:
    """Tolerantly read ``stats_data.Temperature_stats.Mean`` from a result."""
    stats = result.get("stats_data") or {}
    tstats = stats.get("Temperature_stats") or stats.get("temperature_stats") or {}
    mean = tstats.get("Mean")
    if mean is None:  # some responses keep Mean at stats level
        mean = stats.get("Mean")
    if mean is None:
        raise KeyError("No temperature mean found in result.")
    return float(mean)


def get_yearly_trend(bbox_coords, month="07", years=(2021, 2022, 2023, 2024, 2025), granularity=config.DEMO_GRANULARITY) -> list:
    """Return ``[(year, mean_temp_c), ...]`` via one filter_type=4 (month range) call per year.

    2021 is the earliest valid year in the confirmed data range -- do not
    request earlier. Each year's call is cached independently.

    Note: the API's ``filter_type`` accepts only 1..4 (a previous draft used a
    now-invalid ``5`` for "single month", which the live API rejects with a 422 --
    we substitute a month-long day range, ``filter_type=4``, instead).
    """
    import calendar

    ring = bbox.to_ring(bbox_coords)
    pairs = []
    for year in (int(y) for y in years):
        if year < 2021:
            raise ValueError(f"Data range starts at 2021; requested {year}.")
        ym = f"{year}-{str(month).zfill(2)}"
        last = calendar.monthrange(year, int(month))[1]
        dt = make_date_time(f"{ym}-01", filter_type=4, end_date=f"{ym}-{last}")
        key = f"heatmap_{bbox.bbox_hash(ring)}_{ym}_tcm"
        result = fetch_heatmap(ring, dt, granularity=granularity, analytic_type="tcm", cache_key=key)
        pairs.append((year, _extract_mean_temp(result)))
    return pairs