"""Feature 3 Honest Matrix tests: every recommendation carries a real con."""
import pytest

from features import feature3_honest_matrix as f3


def _sample_grid(n=6):
    import geopandas as gpd
    from shapely.geometry import box
    rows = []
    for i in range(n):
        rows.append({
            "cell_id": f"cell_{i}",
            "priority_score": round(1.0 - i * 0.1, 2),
            "vulnerability_score": 0.5,
            "temperature_c": 45.0 - i,
            "heat_index_c": 47.0 - i,
            "geometry": box(-112.1 + i * 0.01, 33.44, -112.09 + i * 0.01, 33.45),
        })
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def test_every_recommendation_has_a_real_con():
    grid = _sample_grid()
    recs = f3.match_interventions(grid, top_n=6)
    f3.assert_every_con_present(recs)      # raises if any con is blank
    for r in recs:
        assert r["con"] and r["con"].strip(), "con must never be blank"


def test_recommendation_contract_fields_present():
    grid = _sample_grid()
    for r in f3.match_interventions(grid, top_n=3):
        for field in ("cell_id", "intervention", "cost_range", "benefit", "con"):
            assert field in r


def test_interventions_are_curated():
    grid = _sample_grid()
    kinds = {r["intervention"] for r in f3.match_interventions(grid, top_n=8)}
    assert kinds <= set(f3.INTERVENTIONS)


def test_top_cell_gets_solar_canopy_when_paved():
    grid = _sample_grid()
    hint = {grid.iloc[0]["cell_id"]: {"paved_pct": 75.0}}
    recs = f3.match_interventions(grid, top_n=8, surface_hint=hint)
    assert recs[0]["intervention"] == "Solar Canopy (parking)"