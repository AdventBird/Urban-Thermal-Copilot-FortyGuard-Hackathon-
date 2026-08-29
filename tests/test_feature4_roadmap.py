"""Feature 4 Roadmap tests: greedy priority phases, contract shape, hand-calc."""
import pytest

from features import feature4_roadmap as f4
from utc import contracts


def _sample_grid(n=5):
    import geopandas as gpd
    from shapely.geometry import box
    rows = []
    for i in range(n):
        rows.append({
            "cell_id": f"cell_{i}",
            "priority_score": round(1.0 - i * 0.2, 2),
            "vulnerability_score": 0.5,
            "temperature_c": 45.0,
            "heat_index_c": 47.0,
            "geometry": box(-112.1 + i * 0.01, 33.44, -112.09 + i * 0.01, 33.45),
        })
    return gpd.GeoDataFrame(rows, crs="EPSG:4326")


def test_phases_match_contract_shape():
    grid = _sample_grid()
    phases, used, skipped = f4.build_phases(grid, budget=300_000, years=1)
    assert used == 5 and skipped == 0, "300k / 50k covers all 5 cells"
    for p in phases:
        for field in contracts.REQUIRED_PHASE_FIELDS:
            assert field in p
        for r in p["recommendations"]:
            for field in contracts.REQUIRED_RECOMMENDATION_FIELDS:
                assert field in r


def test_greedy_orders_by_priority_hand_calc():
    """Hand calculation: 2 cells, $100k budget (one year, $50k/cell).
    Cell A (priority 0.8) funded in Phase 1; Cell B (priority 0.6) in Phase 2."""
    import geopandas as gpd
    from shapely.geometry import box
    grid = gpd.GeoDataFrame([
        {"cell_id": "A", "priority_score": 0.8, "vulnerability_score": 0.9,
         "temperature_c": 45.0, "heat_index_c": 48.0},
        {"cell_id": "B", "priority_score": 0.6, "vulnerability_score": 0.7,
         "temperature_c": 44.0, "heat_index_c": 46.0},
    ], geometry=[box(0, 0, 1, 1), box(1, 0, 2, 1)], crs="EPSG:4326")
    phases, used, skipped = f4.build_phases(grid, budget=100_000, years=1,
                                            cost_per_cell=50_000)
    assert used == 2 and skipped == 0
    # Phase 1 has room for only 2 cells ($100k), greedy fills A then B.
    p1_cells = [r["cell_id"] for r in phases[0]["recommendations"]]
    assert p1_cells == ["A", "B"], "greedy fills highest priority first"


def test_budget_cap_skips_cells():
    grid = _sample_grid(n=5)
    phases, used, skipped = f4.build_phases(grid, budget=100_000, years=1,
                                            cost_per_cell=50_000)
    assert used == 2 and skipped == 3
    assert phases[0]["phase_budget_used"] == pytest.approx(100_000)


def test_plan_to_dataframe_flattens():
    grid = _sample_grid()
    phases, _, _ = f4.build_phases(grid, budget=150_000, years=1)
    rows = f4.plan_to_dataframe(phases)
    assert len(rows) == 3
    assert {"phase", "phased_years"} <= set(rows[0])