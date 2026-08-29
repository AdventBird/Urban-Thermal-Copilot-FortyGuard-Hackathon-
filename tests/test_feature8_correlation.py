"""Feature 8 correlation tests (hand-calculated Pearson)."""
import numpy as np
import pandas as pd
import pytest

from features import feature8_correlation as f8


def _grid():
    import geopandas as gpd
    from shapely.geometry import box
    # Two cells: one west (85007), one east (85004) -> two ZIP groups.
    return gpd.GeoDataFrame([
        {"cell_id": "w", "heat_index_c": 48.0, "priority_score": 0.8,
         "geometry": box(-112.10, 33.44, -112.09, 33.45)},
        {"cell_id": "e", "heat_index_c": 44.0, "priority_score": 0.4,
         "geometry": box(-112.04, 33.44, -112.03, 33.45)},
    ], crs="EPSG:4326")


def _deaths():
    return pd.DataFrame([
        {"zip_code": "85007", "heat_deaths": 13},
        {"zip_code": "85004", "heat_deaths": 7},
    ])


def test_correlation_hand_calc_heat_up_deaths_up():
    """Hand calculation: heat=48 -> more deaths; heat=44 -> fewer. Pearson r=1.0."""
    corr = f8.build_correlation_table(_grid(), _deaths())
    r = f8.compute_correlation(corr)
    assert r == pytest.approx(1.0)
    assert f8.interpret(r).startswith("STRONG")


def test_correlation_table_has_expected_columns():
    corr = f8.build_correlation_table(_grid(), _deaths())
    assert {"zip_code", "avg_heat_score", "total_deaths"} <= set(corr.columns)


def test_interpret_thresholds():
    assert "STRONG" in f8.interpret(0.9)
    assert "MODERATE" in f8.interpret(0.5)
    assert "WEAK" in f8.interpret(0.1)

def test_render_correlation_guard_single_zip():
    """A one-ZIP grid must return the guard note, not a misleading 0.0."""
    import geopandas as gpd
    from shapely.geometry import box
    single_zip = gpd.GeoDataFrame([
        {"cell_id": "w1", "heat_index_c": 47.0, "priority_score": 0.5,
         "geometry": box(-112.10, 33.44, -112.09, 33.45)},
        {"cell_id": "w2", "heat_index_c": 46.0, "priority_score": 0.4,
         "geometry": box(-112.09, 33.44, -112.08, 33.45)},
    ], crs="EPSG:4326")
    out = f8.render_correlation(single_zip, _deaths())
    assert "fewer than two distinct ZIP" in out
    assert "85007" in out


def test_render_correlation_table_and_reading():
    """Two-ZIP grid renders the row table plus a Pearson-correlation reading."""
    out = f8.render_correlation(_grid(), _deaths())
    assert "Pearson r" in out
    assert "85007" in out and "85004" in out
    assert "| ZIP |" in out
