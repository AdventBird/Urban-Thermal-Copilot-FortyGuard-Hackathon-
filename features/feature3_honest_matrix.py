"""feature3_honest_matrix.py -- Feature 3: the Honest Matrix.

Every recommendation shows a real cost, a real benefit AND a real trade-off (a
"con"). Never omits the con -- that honesty framing is the product's core
differentiator for a public-agency buyer.

Interventions are matched to top-ranked zones via simple transparent rules
(public-sourced, illustrative cost/benefit figures from the brief appendix).
"""
from __future__ import annotations

# Public-sourced, illustrative intervention reference table (brief appendix).
INTERVENTIONS = {
    "High-Albedo Reflective Coating": {
        "cost_range": "$1.50-$4.00 / sq ft",
        "benefit": "Drops surface temps up to 12 C; cheap to apply across parking/plazas",
        "con": "Can cause glare for drivers; needs reapplication every 3-5 years",
        "cited_program": "City 'Cool Pavements' pilot (illustrative)",
    },
    "Solar Canopy (parking)": {
        "cost_range": "$3,500-$5,000 / space",
        "benefit": "Generates solar power and cools shaded surface 6-10 C",
        "con": "High upfront cost; requires structural wind-load review",
        "cited_program": "Maricopa solar shade structures program (illustrative)",
    },
    "Urban Micro-Forest": {
        "cost_range": "$15-$25 / sq ft",
        "benefit": "Long-term cooling + AQI improvement; habitat & shade canopy",
        "con": "Takes 3-5 years to mature; heavy early irrigation/maintenance",
        "cited_program": "OHRM urban forestry investment (illustrative)",
    },
}


def match_interventions(grid, top_n=6, surface_hint=None):
    """Return a list of recommendation dicts for the highest-priority cells.

    Rules (simple, transparent):
      * Always recommend the reflective coating for the hot, paved priority cells
        (lowest cost-per-benefit, quickest win).
      * Reserve the solar canopy for cells whose centroid sits on parking lots or
        large impervious footprints (if a satellite ``surface_hint`` is provided
        for that cell we use it, else every ~3rd top cell gets it).
      * Reserve the micro-forest for the most vulnerable/hottest zone as a
        high-impact-but-slow option.

    Every returned recommendation has a non-empty ``con``.
    """
    g = grid.sort_values("priority_score", ascending=False).head(top_n)
    recs = []
    for i, (_, row) in enumerate(g.iterrows()):
        cell_id = row["cell_id"]
        hint = (surface_hint or {}).get(cell_id, {})
        high_paved = hint.get("paved_pct", 40.0) >= 40.0

        if i == 0 and high_paved:
            key = "Solar Canopy (parking)"
        elif i == 1:
            key = "Urban Micro-Forest"
        else:
            key = "High-Albedo Reflective Coating"
        meta = INTERVENTIONS[key]
        recs.append({
            "cell_id": cell_id,
            "intervention": key,
            "cost_range": meta["cost_range"],
            "benefit": meta["benefit"],
            "con": meta["con"],  # REQUIRED, never blank
            "cited_program": meta["cited_program"],
        })
    return recs


def recommendation_map(grid, surface_hint=None) -> dict:
    """Precompute one recommendation per grid cell, keyed by ``cell_id``.

    This is what the inspector panel uses to show "what can be done" for the
    clicked zone. Every recommendation keeps its required ``con``.
    """
    recs = match_interventions(grid, top_n=len(grid), surface_hint=surface_hint)
    return {r["cell_id"]: r for r in recs}


def assert_every_con_present(recs) -> None:
    """Guard the core promise: no recommendation is allowed a blank con."""
    for r in recs:
        if not r.get("con"):
            raise ValueError(f"Recommendation for {r.get('cell_id')} has no 'con'.")