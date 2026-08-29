"""feature8_correlation.py -- Feature 8 (stretch): heat vs. heat-death correlation.

Compares our grid's heat/priority scores to Maricopa County public heat-death
reporting for the same Phoenix ZIP codes and reports a Pearson correlation. Uses
the public fallback series unless a real county CSV is provided.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def build_correlation_table(grid, death_df) -> pd.DataFrame:
    """Match grid heat scores to total deaths per ZIP code.

    ZIP is assigned from cell centroid longitude (85007 west of ~-112.06).
    """
    grid = grid.copy().to_crs("EPSG:4326")
    # Compute the longitude split in a projected CRS to avoid geographic-centroid
    # warnings and keep the zip assignment accurate.
    proj = grid.to_crs("EPSG:32612")
    lons = proj.geometry.centroid.x
    # UTM 12N uses meters; the -112.06 lon dividing line sits at x ~= 401,480 m.
    grid["zip_code"] = lons.apply(lambda x: "85007" if x < 401_480 else "85004")
    heat = grid.groupby("zip_code").agg(
        avg_heat_score=("heat_index_c", "mean"),
        avg_priority_score=("priority_score", "mean"),
        cell_count=("cell_id", "count"),
    ).reset_index()
    deaths = death_df.groupby("zip_code").agg(
        total_deaths=("heat_deaths", "sum")).reset_index()
    merged = heat.merge(deaths, on="zip_code", how="left")
    merged["total_deaths"] = merged["total_deaths"].fillna(0)
    return merged


def compute_correlation(corr_df) -> float:
    """Pearson r between avg_heat_score and total_deaths (needs >=2 points)."""
    if len(corr_df) < 2:
        return 0.0
    heat = corr_df["avg_heat_score"].astype(float).values
    deaths = corr_df["total_deaths"].astype(float).values
    return float(round(np.corrcoef(heat, deaths)[0, 1], 4))


def render_correlation(grid, death_df) -> str:
    """Render the heat-vs-death correlation as honest, readable markdown.

    Shows the ZIP-level table (mean heat index, mean priority, reported deaths)
    and the Pearson r + plain-language reading. Guards the case where the active
    grid covers only ONE ZIP code -- with a single data point the correlation is
    undefined, so we say so instead of printing a misleading 0.0.
    """
    import pandas as pd

    try:
        corr_df = build_correlation_table(grid, death_df)
    except Exception:
        corr_df = pd.DataFrame()

    if corr_df.empty or len(corr_df) < 2:
        return (
            "**Heat ↔ reported heat-death correlation**\n\n"
            "This area covers **fewer than two distinct ZIP codes**, so a "
            "reliable correlation can't be computed from a single area's grid. "
            "Run an area spanning multiple ZIPs (e.g. the full city grid) to see "
            "whether hotter zones overlap more reported deaths.\n\n"
            f"*ZIP codes present in this sample: {', '.join(map(str, sorted(set(corr_df['zip_code'])))) if not corr_df.empty else '—'}*"
        )

    r = compute_correlation(corr_df)
    reading = interpret(r)

    def _row(rw):
        return (
            f"| {rw.zip_code} | {rw.avg_heat_score:.1f} °C | "
            f"{rw.avg_priority_score:.2f} | {rw.cell_count} | "
            f"{rw.total_deaths:.0f} |"
        )

    lines = [
        "**Heat ↔ reported heat-death correlation**",
        "",
        f"Pearson r = **{r:+.3f}** — *{reading}*",
        "",
        "| ZIP | Mean heat index | Mean priority | Cells | Reported deaths |",
        "|---|---|---|---|---|",
    ]
    lines += [_row(r) for r in corr_df.sort_values("total_deaths", ascending=False).itertuples(index=False)]
    lines.append("")
    lines.append("*Source: FortyGuard heat grid matched to Maricopa County public "
                 "heat-death reporting by ZIP code.*")
    return "\n".join(lines)

def interpret(r: float) -> str:
    if r > 0.7:
        return "STRONG positive correlation -- hotter cells overlap more reported deaths"
    if r > 0.3:
        return "MODERATE positive correlation"
    if r > -0.3:
        return "WEAK correlation -- more data needed"
    return "NEGATIVE correlation (unexpected -- verify data)"
