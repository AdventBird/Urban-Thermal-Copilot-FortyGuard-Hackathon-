"""Feature 5 risk-flags tests."""
import json

import pandas as pd
import pytest

from features import feature5_risk_flags as f5
from utc import config


def _grid():
    import geopandas as gpd
    from shapely.geometry import box
    return gpd.GeoDataFrame([
        {"cell_id": "tile_0_0", "temperature_c": 44.0, "exceedance_hours": 1.5,
         "persistence_hours": 0.5, "geometry": box(-112.1, 33.44, -112.09, 33.45)},
        {"cell_id": "tile_2_1", "temperature_c": 45.9, "exceedance_hours": 2.2,
         "persistence_hours": 0.8, "geometry": box(-112.08, 33.44, -112.07, 33.45)},
    ], crs="EPSG:4326")


def test_parse_exceedance_empty_without_props():
    result = {"map_data": {"features": []}}
    assert f5.parse_exceedance(result) == []


def test_summarize_reports_hours_labels():
    df = f5.summarize(_grid(), [], threshold_c=50.0)
    assert "risk_summary" in df.columns
    row = df.loc[df["cell_id"] == "tile_2_1"].iloc[0]
    assert "exceeded 50 C for 2.2 h" in row["risk_summary"]


def test_risk_fixture_is_loadable():
    data = config.read_fixture("sample_risk_flags.json")
    assert "exceedance" in data


def test_render_markdown_both_shapes():
    # Fixture shape: cell_id + *_hours properties.
    fixture = {
        "exceedance": {"map_data": {"features": [
            {"properties": {"cell_id": "tile_0_0", "exceedance_hours": 1.5}},
            {"properties": {"cell_id": "tile_2_1", "exceedance_hours": 2.2}},
        ]}},
        "_meta": {"note": "mock"},
    }
    text = f5.render_markdown(fixture)
    assert "tile_2_1" in text and "1.5" in text
    assert "2 cell(s) above threshold" in text

    # Live shape: tile_id + value + stats_data.
    live = {
        "exceedance": {"map_data": {"features": [
            {"properties": {"tile_id": 0, "value": 3.0}},
            {"properties": {"tile_id": 1, "value": 0.0}},
        ]}, "stats_data": {"n_cells": 2, "min": 0.0, "max": 3.0, "mean": 1.5}},
        "persistence": {"map_data": {"features": []}},
    }
    text = f5.render_markdown(live)
    assert "1 cell(s) above threshold" in text  # only value>0 listed
    assert "mean 1.5 h" in text                 # stats surfaced
    assert "No cells exceeded" not in text.split("Persist")[0]  # no false zero


def test_render_markdown_no_offenders():
    only_zeros = {
        "exceedance": {"map_data": {"features": [
            {"properties": {"tile_id": 0, "value": 0.0}},
        ]}},
    }
    text = f5.render_markdown(only_zeros)
    assert "0 cell(s) above threshold" in text
    assert "No cells exceeded the threshold" in text