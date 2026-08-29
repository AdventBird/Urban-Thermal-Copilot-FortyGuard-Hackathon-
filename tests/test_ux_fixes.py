"""Regression tests for the live-bug + UX fixes (tiny grid, dead inspector, copy)."""

import importlib.util
import warnings

import pytest

warnings.filterwarnings("ignore")

from features import data_layer as dl  # noqa: E402
from features import feature1_heatmap as fh  # noqa: E402
from features import feature5_risk_flags as f5  # noqa: E402


def _app_main():
    """Import app/main.py (module name clashes with its main() function)."""
    spec = importlib.util.spec_from_file_location("app_main_mod", "app/main.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def capitol():
    return dl.build_preset_grid("capitol_district")


def test_preset_grid_spans_district(capitol):
    """Bug 2: preset grids must cover a real district area, not a 400 m blob."""
    proj = capitol.to_crs("EPSG:32612")
    area_km2 = float(proj.geometry.area.sum()) / 1e6
    assert len(capitol) >= 100
    assert area_km2 >= 1.0
    wgs = capitol.to_crs("EPSG:4326")
    minx, miny, maxx, maxy = wgs.total_bounds
    assert abs((minx + maxx) / 2 - (-112.0970)) < 0.01   # preset center
    assert abs((miny + maxy) / 2 - 33.4450) < 0.01


def test_preset_grid_is_deterministic():
    a = dl.build_preset_grid("capitol_district")
    b = dl.build_preset_grid("capitol_district")
    assert list(a["temperature_c"].round(3)) == list(b["temperature_c"].round(3))


def test_preset_grid_contract_columns(capitol):
    for col in ("temperature_c", "cell_id", "heat_index_c",
                "vulnerability_score", "priority_score",
                "exceedance_hours", "persistence_hours"):
        assert col in capitol.columns, col


def test_map_fit_bounds_present(capitol):
    """Bug 2: the map must frame the full grid extent."""
    m = fh.render_explorer_map(capitol, center=capitol.attrs["center"])
    assert "fitBounds" in m.get_root().render()


def test_map_accepts_severity_highlight(capitol):
    m = fh.render_explorer_map(capitol, center=capitol.attrs["center"],
                               highlight_severity="terrible")
    assert "fitBounds" in m.get_root().render()


def test_nearest_cell_hit_and_reject(capitol):
    """Bug 3: clicks resolve via coordinates (st_folium never returns cell_id)."""
    app_main = _app_main()
    wgs = capitol.to_crs("EPSG:4326")
    cent = wgs.geometry.centroid.iloc[7]
    got = app_main._nearest_cell(capitol, float(cent.y), float(cent.x))
    assert got == str(capitol["cell_id"].iloc[7])
    # A click far outside the analysis area resolves to nothing.
    assert app_main._nearest_cell(capitol, 40.0, -100.0) is None


def test_inspector_row_lookup_matches(capitol):
    app_main = _app_main()
    wgs = capitol.to_crs("EPSG:4326")
    cent = wgs.geometry.centroid.iloc[100]
    cell_id = app_main._nearest_cell(capitol, float(cent.y), float(cent.x))
    assert not capitol[capitol["cell_id"] == cell_id].empty


def test_risk_flags_render_markdown_nonempty():
    flags = dl.load_risk_flags()
    md = f5.render_markdown(flags)
    assert isinstance(md, str) and len(md) > 40


def test_custom_area_wait_copy():
    assert dl.CUSTOM_AREA_WAIT_LABEL == "usually under a minute"