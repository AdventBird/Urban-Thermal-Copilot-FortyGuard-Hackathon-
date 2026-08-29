"""feature4_roadmap.py -- Feature 4: budget-constrarmed, multi-year roadmap.

A transparent GREEDY heuristic spends the user's budget (defaulted to OHRM's real
FY2026 $8.9M, labeled as a hypothetical capital-improvement slice) on the highest
``priority_score`` grid cells first, batching them into Year 1 / Year 2 / Year 3
phases. Output conforms to ``utc/contracts.py`` Phase shape.
"""
from __future__ import annotations

from . import feature3_honest_matrix as f3

# Default seat from OHRM FY2026; labeled in the UI as a hypothetical capital slice.
DEFAULT_BUDGET_USD = 8_900_000.0
DEFAULT_YEARS = 3
DEFAULT_COST_PER_CELL_USD = 50_000.0


def _phase_years_label(phase_number: int, start_year: int, years: int) -> str:
    y = start_year + phase_number - 1
    n = years - phase_number + 1
    if n <= 1:
        return str(y)
    return f"{y}-{y + n - 1}"


def build_phases(grid, budget=None, years=DEFAULT_YEARS, cost_per_cell=DEFAULT_COST_PER_CELL_USD,
                 start_year=2026, top_n=None):
    """Greedy phase-fill by priority_score (contract-conforming Phase dicts).

    Rule (transparent): sort cells by ``priority_score`` descending and spend on
    the most urgent cells first. Each phase has a budget slice of
    ``budget / years``; we keep treating cells until the slice (or total budget or
    the priority-ranked list) is exhausted. Every treated cell carries a
    recommendation from the Honest Matrix (so each has a real con).

    Returns ``(phases, cells_used, cells_skipped)``.
    """
    budget = float(budget) if budget is not None else DEFAULT_BUDGET_USD
    years = max(1, int(years))
    phase_slice = budget / years
    g = grid.sort_values("priority_score", ascending=False).reset_index(drop=True)
    if top_n:
        g = g.head(top_n)
    cells = g.to_dict("records")

    # One recommendation per treated cell (honest matrix, includes the con).
    recs = f3.match_interventions(grid, top_n=len(g))

    phases = []
    cum = 0.0
    used_i = 0
    for phase_number in range(1, years + 1):
        phase_recs = []
        phase_spent = 0.0
        while (used_i < len(cells)
               and phase_spent + cost_per_cell <= phase_slice + 1e-9):
            rec = recs[used_i]
            phase_recs.append(rec)
            phase_spent += cost_per_cell
            used_i += 1
        if not phase_recs:
            break  # nothing left to fund
        cum += phase_spent
        phases.append({
            "phase_number": phase_number,
            "years": _phase_years_label(phase_number, start_year, years),
            "recommendations": phase_recs,
            "phase_budget_used": round(phase_spent, 2),
            "cumulative_budget_used": round(cum, 2),
        })
        if used_i >= len(cells):
            break
    cells_skipped = len(cells) - used_i
    return phases, used_i, cells_skipped


def plan_to_dataframe(phases) -> list:
    """Flatten phases into a per-recommendation row list for table display."""
    rows = []
    for p in phases:
        for r in p["recommendations"]:
            row = dict(r)
            row["phase"] = p["phase_number"]
            row["phased_years"] = p["years"]
            rows.append(row)
    return rows


def how_prioritized_text(phases=None, grid=None) -> str:
    """The expandable 'how this was prioritized' panel copy.

    When ``phases`` and ``grid`` are given, it also lists the REAL funded zones
    with their actual priority scores (e.g. "Zone X funded first: priority 0.91
    — highest in this area"), not just the generic method.
    """
    lines = [
        "**How this plan was prioritized (transparent, no black box):**\n",
        "1. Every grid cell gets a `priority_score` from Feature 2 "
        "(`heat_index_normalized × vulnerability_score`).\n"
        "2. Cells are sorted by `priority_score` **descending** — hottest AND most "
        "vulnerable first.\n"
        "3. The greedy loop spends the year's budget slice on the highest-priority "
        "cells first, at `$50,000 / cell`, until the money (or the list) runs out.\n"
        "4. Each funded cell receives one Honest-Matrix intervention — cost, benefit, "
        "**and a con** — so decision-makers see the trade-off, not just the upside.\n",
    ]

    if phases and grid is not None and len(grid):
        scores = dict(zip(grid["cell_id"], grid["priority_score"].astype(float)))
        lines.append("**Actual funding order (this plan):**\n")
        order = 0
        for p in phases:
            for rec in p["recommendations"]:
                order += 1
                cid = rec.get("cell_id")
                sc = scores.get(cid)
                sc_txt = f"{sc:.2f}" if sc is not None else "n/a"
                rank = (" — **highest in this area**" if order == 1 else "")
                lines.append(
                    f"{order}. Zone `{cid}` funded in Phase {p['phase_number']}: "
                    f"priority score {sc_txt}{rank}.\n")

    lines.append(
        "This is a **heuristic**, not a guarantee: real engineering feasibility, "
        "procurement timelines and site constraints must be confirmed before "
        "spending public money.")
    return "\n".join(lines)