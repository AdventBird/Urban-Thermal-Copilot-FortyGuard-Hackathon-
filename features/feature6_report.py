"""feature6_report.py -- Feature 6: AI-generated executive report.

Serializes the computed plan to JSON and requests a narrative executive summary
from the Google Gemini API server-side, framed for OHRM with the honest trade-offs
baked in. If ``GEMINI_API_KEY`` is absent (or the call fails), we fall back to a
deterministic in-app template so the demo still works.
"""
from __future__ import annotations

import json
import logging
import os

log = logging.getLogger(__name__)

# Default Gemini model (fast & capable for a planning narrative). Override with
# the GEMINI_MODEL env var if you prefer a different model.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")


def _mock_prefixes() -> tuple:
    return ("your_", "replace", "changeme", "fake")

def have_gemini_key() -> bool:
    key = (os.getenv("GEMINI_API_KEY") or "").strip()
    return bool(key) and not key.lower().startswith(_mock_prefixes())


def build_plan_context(grid, phases, trend_pairs, mode_label: str,
                       area_name: str = "") -> dict:
    """Assemble a JSON-serializable snapshot of the whole plan for the model."""
    g = grid.sort_values("priority_score", ascending=False).head(8)
    return {
        "mode": mode_label,
        "area_name": area_name or "Downtown Phoenix (ZIP 85004 + 85007)",
        "top_cells": g[["cell_id", "temperature_c", "heat_index_c",
                        "vulnerability_score", "priority_score"]].to_dict("records"),
        "trend_july_mean_c": [{"year": y, "mean_c": m} for y, m in trend_pairs],
        "phases": [
            {
                "phase_number": p["phase_number"],
                "years": p["years"],
                "budget_used": p["phase_budget_used"],
                "recommendations": p["recommendations"],
            }
            for p in phases
        ],
    }


def _system_prompt() -> str:
    return (
        "You are the analyst's assistant at the Phoenix Office of Heat Response "
        "and Mitigation (OHRM). Write a concise executive report for a city "
        "planning audience. ALWAYS state the real cost, the real benefit and the "
        "real trade-off ('con') for each recommendation -- never omit the con. "
        "The budget is a hypothetical capital-improvement slice of OHRM's real "
        "FY2026 $8.9M allocation, not a claim on the full amount. Use plain, "
        "declarative language and short sections. No marketing fluff."
    )


def generate_report(context: dict) -> str:
    """Call the Gemini API for the narrative report, or return template text."""
    if not have_gemini_key():
        return _template_report(context)
    try:
        import google.generativeai as genai
        genai.configure(api_key=os.getenv("GEMINI_API_KEY").strip())
        model = genai.GenerativeModel(GEMINI_MODEL, system_instruction=_system_prompt())
        prompt = (
            "Generate the executive report from this plan JSON:\n"
            f"{json.dumps(context, default=str)}"
        )
        resp = model.generate_content(prompt)
        return resp.text
    except Exception as exc:  # noqa: BLE001
        log.warning("Gemini report failed (%s); returning template.", exc)
        return _template_report(context)


def _template_report(ctx: dict) -> str:
    """Deterministic offline template (used when no Gemini key)."""
    phases = ctx.get("phases", [])
    top_cells = ctx.get("top_cells", [])
    trend = ctx.get("trend_july_mean_c", [])

    lines = [
        "# Executive Summary — Proposed Cooling Investment Plan\n",
        f"Mode: {ctx.get('mode', 'cached/mock')} | "
        f"Area: {ctx.get('area_name', 'Downtown Phoenix (ZIP 85004 + 85007)')}\n",
        "Prepared for the Office of Heat Response and Mitigation (OHRM). The budget "
        "shown is a hypothetical capital-improvement slice of OHRM's real FY2026 "
        "$8.9M allocation.\n",
        "## What the data shows",
    ]
    for tpt in trend:
        lines.append(f"- July {tpt['year']} mean: {tpt.get('mean_c', tpt.get('mean_temp_c')):.1f} C"
                     if isinstance(tpt.get('mean_c', tpt.get('mean_temp_c')), (int, float))
                     else f"- {tpt}")
    lines.append("\n## Highest-priority zones")
    for c in top_cells[:5]:
        lines.append(
            f"- {c['cell_id']}: heat-index {c.get('heat_index_c', 0):.1f} C, "
            f"vulnerability {c.get('vulnerability_score', 0):.2f}, "
            f"priority {c.get('priority_score', 0):.2f}")

    lines.append("\n## Recommended phases and trade-offs")
    for p in phases:
        lines.append(f"\n**Phase {p['phase_number']} ({p['years']})** — "
                     f"${p['budget_used']:,.0f}")
        for r in p["recommendations"]:
            # Tie each funded intervention to its zone so the report reads as a
            # site-by-site plan, not a repeated shopping list.
            cid = r.get("cell_id")
            where = f" for zone `{cid}`" if cid else ""
            lines.append(
                f"- {r['intervention']}{where} ({r['cost_range']}). "
                f"Benefit: {r['benefit']}. Trade-off: {r['con']}.")

    lines.append("\n*Honesty note: every recommendation includes its cost, its "
                 "benefit, and its con. Engineering feasibility and site constraints "
                 "must be confirmed before spending public money.*")
    return "\n".join(lines)