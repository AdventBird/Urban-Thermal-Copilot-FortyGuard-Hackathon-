"""Feature 1 tests: payload shape, date_time blocks, yearly trend caching, tiles_to_grid."""
import json

import pytest

from utc import bbox, feature1_thermal as f1
from utc import config


# ---------------------------------------------------------------------------
# Pure-Python (no geopandas needed) -- these always run.
# ---------------------------------------------------------------------------
def test_make_date_time_single_day():
    dt = f1.make_date_time("2025-07-14", filter_type=3)
    assert dt == {"filter_type": 3, "start_date": "2025-07-14"}


def test_make_date_time_single_hour():
    dt = f1.make_date_time("2025-07-14", filter_type=1)
    assert dt["filter_type"] == 1
    assert dt["start_time"] == config.DEMO_TIME


def test_make_date_time_single_month_uses_day_01():
    dt = f1.make_date_time("2026-07-14", filter_type=5)
    assert dt["start_date"] == "2026-07-01"


def test_build_heatmap_payload_matches_contract():
    ring = bbox.fallback_ring()
    payload = f1.build_heatmap_payload(ring, f1.make_date_time("2025-07-14", 3))
    assert payload["polygon_aoi"]["type"] == "FeatureCollection"
    geom = payload["polygon_aoi"]["features"][0]["geometry"]
    assert geom["type"] == "Polygon"
    assert geom["coordinates"][0][0] == geom["coordinates"][0][-1]  # closed ring
    assert payload["analytic_type"] == "tcm"
    assert payload["granularity"] == 100
    assert payload["date_time"]["filter_type"] == 3


def test_yearly_trend_caches_per_year_and_extracts_mean(monkeypatch):
    # Force the network path and record cache keys instead of touching disk.
    calls = []
    monkeypatch.setattr(f1, "load_cached_json", lambda key: None)
    monkeypatch.setattr(f1, "save_cached_json", lambda key, data: calls.append(key))

    def fake_submit_and_poll(url, payload, timeout_s=60):
        month = payload["date_time"]["start_date"]
        mean = {"2021-07-01": 40.1, "2022-07-01": 40.8, "2023-07-01": 41.2}.get(month, 42.0)
        return {"stats_data": {"Temperature_stats": {"Mean": mean}}}

    monkeypatch.setattr(f1, "submit_and_poll", fake_submit_and_poll)

    pairs = f1.get_yearly_trend(bbox.fallback_ring(), month="07", years=[2021, 2022, 2023])
    assert pairs == [(2021, 40.1), (2022, 40.8), (2023, 41.2)]
    assert len(calls) == 3, "each year's call should be cached independently"
    assert any("2021-07" in k for k in calls)


def test_get_yearly_trend_rejects_pre_2021(monkeypatch):
    with pytest.raises(ValueError):
        f1.get_yearly_trend(bbox.fallback_ring(), month="07", years=[2020])


# ---------------------------------------------------------------------------
# Geo-dependent (skipped unless geopandas/pandas installed).
# ---------------------------------------------------------------------------
def test_tiles_to_grid_columns_and_count():
    gpd = pytest.importorskip("geopandas")
    pd = pytest.importorskip("pandas")
    sample = json.load(open(config.FIXTURE_DIR / "sample_heatmap_response.json"))
    grid = f1.tiles_to_grid(sample)
    assert len(grid) == 12, "expected one row per tile in the fixture"
    for col in ("geometry", "temperature_c", "cell_id", "area_m2"):
        assert col in grid.columns, f"missing expected column {col}"
    # tile temperatures were 40.9..45.9 in fixture
    assert grid["temperature_c"].min() == pytest.approx(40.9)
    assert grid["temperature_c"].max() == pytest.approx(45.9)
    assert grid.crs.to_string().startswith("EPSG:32612")


def test_render_heatmap_returns_folium_map():
    pytest.importorskip("geopandas")
    folium = pytest.importorskip("folium")
    sample = json.load(open(config.FIXTURE_DIR / "sample_heatmap_response.json"))
    grid = f1.tiles_to_grid(sample)
    m = f1.render_heatmap(grid)
    assert isinstance(m, folium.Map)