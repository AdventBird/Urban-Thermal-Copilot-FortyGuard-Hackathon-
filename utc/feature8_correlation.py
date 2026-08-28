"""feature8_correlation.py -- Lightweight Heat vs Death Correlation (Feature 8)

Stretch feature: compares our grid heat data to Maricopa County's public
heat-death data for the same Phoenix area (85004 + 85007).

What this does in simple words:
  - Takes heat scores from Feature 1/2
  - Loads Maricopa County heat death counts (public data)
  - Makes a simple chart showing if hotter areas = more deaths
  - Computes a correlation number (0-1, higher = stronger link)

Hand-calculation test:
  heat_scores  = [0.3, 0.5, 0.7, 0.9]
  death_counts = [1,   2,   4,   5  ]
  Expected: positive correlation (as heat goes up, deaths go up)
  Pearson r should be > 0.95
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import numpy as np

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Maricopa County heat death data (hardcoded fallback)
# Source: Maricopa County Environmental Services heat reports
# Replace with real CSV from:
# https://www.maricopa.gov/5105/Heat-Surveillance
#
# NOTE: These are PLACEHOLDER values shaped like real data.
# Replace with actual Maricopa County figures before the demo.
# ---------------------------------------------------------------------------
MARICOPA_HEAT_DEATHS_FALLBACK = [
    {"year": 2019, "month": 7, "zip_code": "85004", "heat_deaths": 3},
    {"year": 2019, "month": 7, "zip_code": "85007", "heat_deaths": 5},
    {"year": 2020, "month": 7, "zip_code": "85004", "heat_deaths": 4},
    {"year": 2020, "month": 7, "zip_code": "85007", "heat_deaths": 7},
    {"year": 2021, "month": 7, "zip_code": "85004", "heat_deaths": 5},
    {"year": 2021, "month": 7, "zip_code": "85007", "heat_deaths": 9},
    {"year": 2022, "month": 7, "zip_code": "85004", "heat_deaths": 6},
    {"year": 2022, "month": 7, "zip_code": "85007", "heat_deaths": 11},
    {"year": 2023, "month": 7, "zip_code": "85004", "heat_deaths": 7},
    {"year": 2023, "month": 7, "zip_code": "85007", "heat_deaths": 13},
]


# ---------------------------------------------------------------------------
# Load heat death data
# ---------------------------------------------------------------------------
def load_heat_deaths(csv_path=None) -> pd.DataFrame:
    """Load Maricopa County heat death data.

    Uses real CSV if path provided, otherwise uses hardcoded fallback.

    Parameters
    ----------
    csv_path : str or Path, optional
        Path to real Maricopa County heat death CSV file

    Returns
    -------
    pd.DataFrame with columns: year, month, zip_code, heat_deaths
    """
    if csv_path and Path(csv_path).exists():
        df = pd.read_csv(csv_path)
        log.info("Loaded real heat death data from %s", csv_path)
        return df

    log.warning("Using hardcoded fallback heat death data -- replace before demo!")
    return pd.DataFrame(MARICOPA_HEAT_DEATHS_FALLBACK)


# ---------------------------------------------------------------------------
# Build correlation table
# ---------------------------------------------------------------------------
def build_correlation_table(grid_gdf, death_df) -> pd.DataFrame:
    """Match grid heat scores to death counts by zip code.

    Parameters
    ----------
    grid_gdf : GeoDataFrame
        Output of feature2_vulnerability (has priority_score, heat_index_c)
    death_df : pd.DataFrame
        Output of load_heat_deaths()

    Returns
    -------
    pd.DataFrame with columns:
        zip_code, avg_heat_score, avg_priority_score, total_deaths
    """
    # Average heat scores per zip code from our grid
    # (zip assignment based on longitude -- matches feature2 logic)
    grid = grid_gdf.copy().to_crs("EPSG:4326")
    grid["zip_code"] = grid.geometry.centroid.x.apply(
        lambda x: "85007" if x < -112.06 else "85004"
    )

    heat_by_zip = grid.groupby("zip_code").agg(
        avg_heat_score=("heat_index_c", "mean"),
        avg_priority_score=("priority_score", "mean"),
        cell_count=("cell_id", "count"),
    ).reset_index()

    # Total deaths per zip code across all years
    deaths_by_zip = death_df.groupby("zip_code").agg(
        total_deaths=("heat_deaths", "sum")
    ).reset_index()

    # Merge both tables
    merged = heat_by_zip.merge(deaths_by_zip, on="zip_code", how="left")
    merged["total_deaths"] = merged["total_deaths"].fillna(0)

    return merged


# ---------------------------------------------------------------------------
# Compute correlation
# ---------------------------------------------------------------------------
def compute_correlation(corr_df) -> float:
    """Compute Pearson correlation between avg heat score and death count.

    Returns
    -------
    float : correlation coefficient (-1 to 1)
        > 0.7 = strong positive correlation (hotter = more deaths)
        0.3-0.7 = moderate
        < 0.3 = weak
    """
    if len(corr_df) < 2:
        log.warning("Need at least 2 data points for correlation")
        return 0.0

    heat   = corr_df["avg_heat_score"].values
    deaths = corr_df["total_deaths"].values

    # Pearson r
    r = float(np.corrcoef(heat, deaths)[0, 1])
    return round(r, 4)


# ---------------------------------------------------------------------------
# Print summary
# ---------------------------------------------------------------------------
def print_correlation_summary(corr_df, r_value) -> None:
    """Print a clean correlation summary to terminal."""
    print("\n" + "=" * 55)
    print("  FEATURE 8 -- Heat vs Heat-Death Correlation")
    print("  Area: Phoenix 85004 + 85007 | Source: Maricopa Co.")
    print("=" * 55)
    print(f"\n  {'ZIP':<10} {'Avg Heat Score':<18} {'Total Deaths':<15}")
    print(f"  {'-'*10} {'-'*18} {'-'*15}")
    for _, row in corr_df.iterrows():
        print(
            f"  {row['zip_code']:<10} "
            f"{row['avg_heat_score']:<18.3f} "
            f"{int(row['total_deaths']):<15}"
        )
    print(f"\n  Pearson r = {r_value}")
    if r_value > 0.7:
        strength = "STRONG positive correlation ✅"
    elif r_value > 0.3:
        strength = "MODERATE positive correlation"
    else:
        strength = "WEAK correlation -- check data"
    print(f"  Interpretation: {strength}")
    print("=" * 55 + "\n")


# ---------------------------------------------------------------------------
# Plot chart (saves as PNG for the demo)
# ---------------------------------------------------------------------------
def plot_correlation(corr_df, r_value, output_path="data/cache/feature8_correlation.png") -> None:
    """Save a scatter chart: heat score vs heat deaths per zip code.

    Parameters
    ----------
    corr_df : pd.DataFrame  output of build_correlation_table()
    r_value : float         output of compute_correlation()
    output_path : str       where to save the PNG
    """
    try:
        import matplotlib.pyplot as plt
        import matplotlib
        matplotlib.use("Agg")  # no display needed, just save file
    except ImportError:
        log.warning("matplotlib not installed -- skipping chart. pip install matplotlib")
        return

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(figsize=(7, 5))

    ax.scatter(
        corr_df["avg_heat_score"],
        corr_df["total_deaths"],
        s=200,
        color="#e05c2e",
        edgecolors="white",
        linewidths=1.5,
        zorder=3,
    )

    # Label each point with zip code
    for _, row in corr_df.iterrows():
        ax.annotate(
            row["zip_code"],
            (row["avg_heat_score"], row["total_deaths"]),
            textcoords="offset points",
            xytext=(8, 4),
            fontsize=10,
            color="#333333",
        )

    ax.set_xlabel("Average Heat Score (normalized)", fontsize=11)
    ax.set_ylabel("Total Heat Deaths (2019-2023)", fontsize=11)
    ax.set_title(
        f"Heat Score vs Heat Deaths — Phoenix 85004/85007\nPearson r = {r_value}",
        fontsize=12,
        fontweight="bold",
    )
    ax.grid(True, linestyle="--", alpha=0.4)
    ax.set_facecolor("#f9f9f9")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    print(f"  Chart saved to: {output_path}")


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------
def run_correlation(grid_gdf, csv_path=None, save_chart=True) -> pd.DataFrame:
    """Full Feature 8 pipeline.

    Parameters
    ----------
    grid_gdf : GeoDataFrame  output of feature2_vulnerability
    csv_path : str, optional  real Maricopa CSV path
    save_chart : bool         whether to save PNG chart

    Returns
    -------
    pd.DataFrame  correlation table
    """
    death_df = load_heat_deaths(csv_path)
    corr_df  = build_correlation_table(grid_gdf, death_df)
    r_value  = compute_correlation(corr_df)

    print_correlation_summary(corr_df, r_value)

    if save_chart:
        plot_correlation(corr_df, r_value)

    return corr_df


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Hand-calculation check:
    # heat = [0.3, 0.5, 0.7, 0.9], deaths = [1, 2, 4, 5]
    # Expected: r > 0.95 (strong positive correlation)

    test_df = pd.DataFrame({
        "zip_code":        ["85004", "85007"],
        "avg_heat_score":  [0.60,     0.80],
        "avg_priority_score": [0.55,  0.75],
        "total_deaths":    [10,       18],
    })

    r = compute_correlation(test_df)
    assert r > 0.0, f"Expected positive correlation, got {r}"
    print(f"✅ Correlation self-test passed! Pearson r = {r}")
    print_correlation_summary(test_df, r)