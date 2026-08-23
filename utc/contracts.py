"""contracts.py -- stable data shapes shared across all feature modules.

The team agreed on these shapes up front (Section 3 of the brief). Downstream
modules (Honest Matrix, Roadmap) import these exact field names, so if Feature 1
or Feature 2 produce different fields, that is a bug in the producing function,
not a change to make downstream. We expose small helpers so a cell dataframe can
be validated before it is handed to a scoring / ranking function.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# Every grid cell, once Features 1 + 2 have run, must carry at least:
REQUIRED_CELL_FIELDS = [
    "cell_id",
    "geometry",
    "temperature_c",
    "heat_index_c",
    "exceedance_hours",
    "persistence_hours",
    "solar_ghi",
    "vulnerability_score",
    "priority_score",
]

# A "recommendation" object (Feature 3) - ``con`` is REQUIRED, never omitted.
REQUIRED_RECOMMENDATION_FIELDS = ["cell_id", "intervention", "cost_range", "benefit", "con"]

# A "phase" object (Feature 4).
REQUIRED_PHASE_FIELDS = ["phase_number", "years", "recommendations", "phase_budget_used", "cumulative_budget_used"]


@dataclass
class GridCell:
    """Typed helper for the shared grid-cell contract.

    This is a convenience for tests / small fixtures; in production the real
    grid usually lives as a GeoDataFrame. The dataclass keeps the field list
    discoverable and provably one place.
    """

    cell_id: str
    geometry: Any                          # shapely Polygon
    temperature_c: float = 0.0
    heat_index_c: float = 0.0
    exceedance_hours: float = 0.0
    persistence_hours: float = 0.0
    solar_ghi: float = 0.0
    vulnerability_score: float = 0.0
    priority_score: float = 0.0

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Recommendation:
    """A single recommendation. ``con`` is REQUIRED -- the product's differentiator."""

    cell_id: str
    intervention: str
    cost_range: str
    benefit: str
    con: str
    cited_program: Optional[str] = None

    def as_dict(self) -> dict:
        return self.__dict__.copy()


@dataclass
class Phase:
    """A budget roadmap phase."""

    phase_number: int
    years: str
    recommendations: List[Recommendation] = field(default_factory=list)
    phase_budget_used: float = 0.0
    cumulative_budget_used: float = 0.0

    def as_dict(self) -> dict:
        return {
            "phase_number": self.phase_number,
            "years": self.years,
            "recommendations": [r.as_dict() for r in self.recommendations],
            "phase_budget_used": self.phase_budget_used,
            "cumulative_budget_used": self.cumulative_budget_used,
        }


def missing_fields(obj: dict, required: List[str]) -> List[str]:
    """Return required field names that are missing from ``obj``."""
    return [f for f in required if f not in obj]


def validate_cell(obj: dict, raise_error: bool = True) -> List[str]:
    """Check a dict-shaped cell against the shared grid contract.

    Returns the list of missing required fields; if ``raise_error`` and any are
    missing, raises ValueError naming them. Assorted downstream modules call this
    before trusting a cell dict.
    """
    missing = missing_fields(obj, REQUIRED_CELL_FIELDS)
    if missing and raise_error:
        raise ValueError(f"Cell missing required contract fields: {missing}")
    return missing