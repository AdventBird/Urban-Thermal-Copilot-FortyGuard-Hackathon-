"""feature9_business_case.py -- Feature 9: business case / buyer framing.

A short in-app section naming OHRM as the buyer and the real $8.9M budget line,
so reviewers can immediately see who this is for and where the money comes from.
"""
from __future__ import annotations

OHEM_NAME = "Phoenix Office of Heat Response and Mitigation (OHRM)"
FY2026_BUDGET_USD = 8_900_000.0
BUDGET_LABEL = "hypothetical capital-improvement slice (not a claim on the full amount)"


def business_case_text() -> str:
    return (
        f"**Buyer:** {OHEM_NAME}\n\n"
        f"**Budget roadmap seeded from:** OHRM's real FY2026 **${FY2026_BUDGET_USD:,.0f}** "
        f"allocation — used here as a {BUDGET_LABEL}.\n\n"
        "**Why this product gets adopted:** every recommendation is honest. It shows "
        "a real cost, a real benefit, and a real trade-off. City planners can defend "
        "the spend to a council because nothing is oversold.\n\n"
        "**Data trust:** heat analytics are FortyGuard-native (2-metre resolution), "
        "vulnerability is computed with a documented, inspectable formula, and all "
        "external figures are clearly labeled as representative/illustrative where "
        "public source data is not yet wired in."
    )