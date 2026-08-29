"""Feature data-layer / mock-grid tests + a hand-calculated priority assertion."""
import pytest

from features import data_layer as dl
from features import feature2_vulnerability as f2
from utc import contracts


def _force_mock(monkeypatch):
    monkeypatch.setattr(dl, "have_api_key", lambda: False)
    monkeypatch.setattr(dl, "running_mock", lambda: True)


def test_mock_grid_conforms_to_shared_contract(monkeypatch):
    _force_mock(monkeypatch)
    grid = dl.build_grid()
    # Every contract field must be present.
    for col in contracts.REQUIRED_CELL_FIELDS:
        assert col in grid.columns, f"grid missing contract field {col}"
    assert len(grid) > 0


def test_mock_grid_not_empty_with_scores(monkeypatch):
    _force_mock(monkeypatch)
    grid = dl.build_grid()
    assert grid["heat_index_c"].notna().all()
    assert grid["priority_score"].between(0.0, 1.0 + 1e-9).all()
    assert grid["vulnerability_score"].between(0.0, 1.0 + 1e-9).all()


def test_mode_label_reflects_mock(monkeypatch):
    _force_mock(monkeypatch)
    assert "MOCK" in dl.mode_label()


# Hand-calculated priority assertion (not a black box):
#   heat_index min=30, max=40 -> A norm=1.0, B norm=0.0
#   priority A = 1.0 * 1.0 = 1.0   ; priority B = 0.0 * 0.0 = 0.0
def test_hand_calculated_priority_scores(monkeypatch):
    _force_mock(monkeypatch)
    import pandas as pd
    from utc.feature2_vulnerability import compute_priority_score
    g = pd.DataFrame({
        "cell_id": ["A", "B"],
        "temperature_c": [45.0, 40.0],
        "heat_index_c": [40.0, 30.0],
        "vulnerability_score": [1.0, 0.0],
    })
    out = compute_priority_score(g)
    assert out.loc[0, "cell_id"] == "A"
    assert out.loc[0, "priority_score"] == pytest.approx(1.0)
    assert out.loc[1, "priority_score"] == pytest.approx(0.0)


def test_load_risk_flags_returns_exceedance_key(monkeypatch):
    _force_mock(monkeypatch)
    risk = dl.load_risk_flags()
    assert "exceedance" in risk


def test_load_trend_has_five_scipy_years(monkeypatch):
    _force_mock(monkeypatch)
    pairs = dl.load_trend()
    assert len(pairs) == 5
    assert pairs[0][0] == 2021 and pairs[-1][0] == 2025


def test_load_maricopa_deaths_has_rows(monkeypatch):
    _force_mock(monkeypatch)
    df = dl.load_maricopa_deaths()
    assert len(df) >= 9
    assert {"year", "zip_code", "heat_deaths"} <= set(df.columns)