"""feature4_roadmap.py -- Budget & Timeline Roadmap (Feature 4)

Takes the priority-ranked grid cells produced by Feature 2 and phases them
into a greedy budget/timeline plan:
  - Highest priority_score cells get funded first (greedy rule)
  - Cells are grouped into phases by available phase budget
  - Output is a DataFrame + printed summary ready for the demo

Hand-calculation test (written before coding -- used as assert below):
  Cell A: priority_score = 0.80
  Cell B: priority_score = 0.60
  Cell C: priority_score = 0.40
  PHASE_BUDGET = $100,000, COST_PER_CELL = $50,000
  → Phase 1: Cell A + Cell B  (2 cells × $50k = $100k)
  → Phase 2: Cell C           (1 cell  × $50k = $50k)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

import pandas as pd
import geopandas as gpd

# ---------------------------------------------------------------------------
# Budget constants -- adjust to match the real Phoenix FY2026 envelope
# ---------------------------------------------------------------------------
COST_PER_CELL_USD   = 50_000    # cost to treat one grid cell
PHASE_BUDGET_USD    = 250_000   # max spend per phase
TOTAL_BUDGET_USD    = 1_000_000 # total available budget
PHASE_DURATION_MONTHS = 3       # months per phase


# ---------------------------------------------------------------------------
# Data shape for one phase (matches contracts.py Phase dataclass)
# ---------------------------------------------------------------------------
@dataclass
class Phase:
    phase_number: int
    cells: List[dict] = field(default_factory=list)

    @property
    def total_cost(self) -> float:
        return len(self.cells) * COST_PER_CELL_USD

    @property
    def start_month(self) -> int:
        return (self.phase_number - 1) * PHASE_DURATION_MONTHS + 1

    @property
    def end_month(self) -> int:
        return self.phase_number * PHASE_DURATION_MONTHS

    @property
    def avg_priority(self) -> float:
        if not self.cells:
            return 0.0
        return round(
            sum(c["priority_score"] for c in self.cells) / len(self.cells), 4
        )

    @property
    def avg_vulnerability(self) -> float:
        if not self.cells:
            return 0.0
        return round(
            sum(c["vulnerability_score"] for c in self.cells) / len(self.cells), 4
        )


# ---------------------------------------------------------------------------
# Core greedy phase-fill
# ---------------------------------------------------------------------------
def build_phases(
    gdf: gpd.GeoDataFrame,
    cost_per_cell: float = COST_PER_CELL_USD,
    phase_budget: float = PHASE_BUDGET_USD,
    total_budget: float = TOTAL_BUDGET_USD,
) -> List[Phase]:
    """Greedy phase-fill algorithm.

    1. Sort cells by priority_score descending (highest urgency first)
    2. Fill Phase 1 until phase budget exhausted
    3. Overflow into Phase 2, repeat until total budget exhausted

    Parameters
    ----------
    gdf : GeoDataFrame
        Output of feature2_vulnerability.compute_priority_score()
        Must have: cell_id, priority_score, vulnerability_score,
        heat_index_c (or temperature_c), geometry

    Returns
    -------
    List[Phase] ordered by phase number
    """
    required = {"cell_id", "priority_score", "vulnerability_score"}
    missing = required - set(gdf.columns)
    if missing:
        raise KeyError(f"Grid is missing required columns: {missing}")

    # Sort highest priority first
    ranked = gdf.sort_values("priority_score", ascending=False).reset_index(drop=True)

    phases: List[Phase] = []
    current_phase = Phase(phase_number=1)
    total_spent = 0.0

    for _, row in ranked.iterrows():
        # Stop if total budget exhausted
        if total_spent + cost_per_cell > total_budget:
            break

        # Start a new phase if current phase budget is full
        if current_phase.total_cost + cost_per_cell > phase_budget:
            phases.append(current_phase)
            current_phase = Phase(phase_number=len(phases) + 1)

        # Add cell to current phase
        current_phase.cells.append({
            "cell_id":             row["cell_id"],
            "priority_score":      round(float(row["priority_score"]), 4),
            "vulnerability_score": round(float(row["vulnerability_score"]), 4),
            "heat_index_c":        round(float(row.get("heat_index_c") or row.get("temperature_c", 0.0)), 2),
        })
        total_spent += cost_per_cell

    # Append the last phase if it has cells
    if current_phase.cells:
        phases.append(current_phase)

    return phases


# ---------------------------------------------------------------------------
# Convert phases → flat DataFrame for CSV / downstream use
# ---------------------------------------------------------------------------
def phases_to_dataframe(phases: List[Phase]) -> pd.DataFrame:
    """Flatten all phases into one tidy DataFrame.

    Columns: phase, start_month, end_month, cell_id,
             priority_score, vulnerability_score, heat_index_c, cost_usd
    """
    rows = []
    for phase in phases:
        for cell in phase.cells:
            rows.append({
                "phase":               phase.phase_number,
                "start_month":         phase.start_month,
                "end_month":           phase.end_month,
                "cell_id":             cell["cell_id"],
                "priority_score":      cell["priority_score"],
                "vulnerability_score": cell["vulnerability_score"],
                "heat_index_c":        cell["heat_index_c"],
                "cost_usd":            COST_PER_CELL_USD,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pretty summary for the demo terminal / daily check-in
# ---------------------------------------------------------------------------
def print_roadmap_summary(phases: List[Phase]) -> None:
    """Print a clean readable roadmap to the terminal."""
    print("\n" + "=" * 60)
    print("  BUDGET & TIMELINE ROADMAP — Phoenix Heat Response FY2026")
    print("=" * 60)

    for phase in phases:
        print(
            f"\n  Phase {phase.phase_number}"
            f"  │  Month {phase.start_month}–{phase.end_month}"
            f"  │  ${phase.total_cost:>10,.0f}"
            f"  │  Avg priority: {phase.avg_priority:.3f}"
            f"  │  Avg vulnerability: {phase.avg_vulnerability:.3f}"
        )
        top = [c["cell_id"] for c in phase.cells[:5]]
        suffix = "..." if len(phase.cells) > 5 else ""
        print(f"         Top cells: {top}{suffix}  ({len(phase.cells)} total)")

    total_cells = sum(len(p.cells) for p in phases)
    total_cost  = sum(p.total_cost for p in phases)
    print("\n" + "-" * 60)
    print(f"  Total cells treated : {total_cells}")
    print(f"  Total budget used   : ${total_cost:,.0f} of ${TOTAL_BUDGET_USD:,.0f}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main entry point (called by app / notebook)
# ---------------------------------------------------------------------------
def run_roadmap(gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """Full pipeline: priority-ranked grid → phased budget roadmap.

    Parameters
    ----------
    gdf : GeoDataFrame
        Output of feature2_vulnerability.compute_priority_score()

    Returns
    -------
    pd.DataFrame  one row per cell with phase assignment
    """
    phases     = build_phases(gdf)
    print_roadmap_summary(phases)
    roadmap_df = phases_to_dataframe(phases)
    return roadmap_df


# ---------------------------------------------------------------------------
# Self-test -- matches the hand-calculation written at the top of this file
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    from shapely.geometry import Polygon

    # Use small budgets so hand-calc is easy to verify
    _TEST_PHASE_BUDGET = 100_000
    _TEST_TOTAL_BUDGET = 200_000

    fake_grid = gpd.GeoDataFrame(
        [
            {"cell_id": "cell_A", "priority_score": 0.80,
             "vulnerability_score": 0.90, "heat_index_c": 42.0, "temperature_c": 42.0},
            {"cell_id": "cell_B", "priority_score": 0.60,
             "vulnerability_score": 0.70, "heat_index_c": 38.0, "temperature_c": 38.0},
            {"cell_id": "cell_C", "priority_score": 0.40,
             "vulnerability_score": 0.50, "heat_index_c": 35.0, "temperature_c": 35.0},
        ],
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])] * 3,
        crs="EPSG:4326",
    )

    phases = build_phases(
        fake_grid,
        cost_per_cell=50_000,
        phase_budget=_TEST_PHASE_BUDGET,
        total_budget=_TEST_TOTAL_BUDGET,
    )

    # Hand-calculation assertions
    assert len(phases) == 2,                          "Expected 2 phases"
    assert len(phases[0].cells) == 2,                 "Phase 1 should have 2 cells"
    assert phases[0].cells[0]["cell_id"] == "cell_A", "Cell A should be first"
    assert phases[0].cells[1]["cell_id"] == "cell_B", "Cell B should be second"
    assert len(phases[1].cells) == 1,                 "Phase 2 should have 1 cell"
    assert phases[1].cells[0]["cell_id"] == "cell_C", "Cell C should be in Phase 2"

    print("✅ All hand-calculation tests passed!")
    print_roadmap_summary(phases)