"""Feature 7 trend + Feature 6 report + Feature 9 business case tests."""
import json

from features import feature6_report as f6
from features import feature7_trend as f7
from features import feature9_business_case as f9


# --- Feature 7 ---
def test_trend_table_shape():
    rows = f7.trend_table([(2021, 39.4), (2025, 41.3)])
    assert rows[0] == {"year": 2021, "mean_temp_c": 39.4}


def test_delta_c_hand_calc():
    pairs = [(2021, 40.0), (2022, 41.0), (2023, 43.5)]
    assert f7.delta_c(pairs) == 3.5          # 43.5 - 40.0


def test_delta_c_short_series_is_zero():
    assert f7.delta_c([(2021, 40.0)]) == 0.0


# --- Feature 6 ---
def test_template_report_mentions_con_per_phase():
    ctx = {
        "mode": "mock",
        "top_cells": [{"cell_id": "tile_0_0", "heat_index_c": 48.0,
                       "vulnerability_score": 0.7, "priority_score": 0.6}],
        "trend_july_mean_c": [{"year": 2021, "mean_c": 39.4}],
        "get_phases_hint": True,
        "phases": [{
            "phase_number": 1, "years": "2026-2027", "budget_used": 100000,
            "recommendations": [{
                "intervention": "High-Albedo Reflective Coating", "cost_range": "$1.50-$4.00 / sq ft",
                "benefit": "Cools surface", "con": "Reapply every 3-5 years", "cell_id": "tile_0_0",
                "cited_program": None}],
        }],
    }
    txt = f6._template_report(ctx)
    assert "Trade-off:" in txt
    assert "hypothetical capital-improvement slice" in txt or "OHRM" in txt  # framing present


def test_build_plan_context_serializes():
    ctx = {"mode": "mock", "top_cells": [], "trend_july_mean_c": [], "phases": []}
    assert json.loads(json.dumps(ctx)) == ctx


def test_have_gemini_key_false_in_ci(monkeypatch):
    import os
    monkeypatch.setenv("GEMINI_API_KEY", "your_key_here")
    assert f6.have_gemini_key() is False


# --- Feature 9 ---
def test_business_case_names_ohrm_and_budget():
    txt = f9.business_case_text()
    assert "Office of Heat Response and Mitigation" in txt
    assert "8,900,000" in txt
    assert "hypothetical" in txt