"""feature7_trend.py -- Feature 7: multi-year warming trend.

Plots the July mean temperature (``stats_data.Temperature_stats.Mean``) for the
demo box across 2021-2025. In live mode each year is one ``filter_type=5``
(single month) FortyGuard call, cached independently; in mock mode we use the
representative fixture trend.
"""
from __future__ import annotations


def trend_table(pairs) -> list:
    """Convert ``[(year, mean_c), ...]`` into row dicts for display/chart."""
    return [{"year": int(y), "mean_temp_c": float(m)} for y, m in pairs]


def delta_c(pairs) -> float:
    """Total warming across the window (last - first July mean), or 0 if short."""
    if not pairs or len(pairs) < 2:
        return 0.0
    return round(pairs[-1][1] - pairs[0][1], 2)