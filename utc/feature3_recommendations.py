"""Feature 3 - Honest Matrix recommendation engine."""

from .contracts import Recommendation


# Evidence-backed intervention options for urban heat mitigation.
INTERVENTIONS = [
    {
        "intervention": "Trees / shade",
        "cost_range": "Phoenix Cool Corridors had a $1.4M allocation supporting up to 1,800 trees",
        "benefit": "Adds shade and can reduce heat exposure",
        "con": "Requires water, maintenance, and time for trees to mature",
        "cited_program": "Phoenix Cool Corridors",
    },
    {
        "intervention": "Cool pavement",
        "cost_range": "About $5 per square yard in Phoenix pilot/program reporting",
        "benefit": "Can reduce pavement surface temperatures by up to about 12 F in Phoenix reporting",
        "con": "The effect on surrounding air temperature is relatively small",
        "cited_program": "Phoenix Cool Pavement Program",
    },
    {
        "intervention": "Cool roof",
        "cost_range": "$0.85-$1.25 per square foot for the cited Arizona cool-roof coating specification",
        "benefit": "Reflects solar energy and can reduce cooling demand, with actual savings depending on the building",
        "con": "Effectiveness depends on the building and may require maintenance/recoating",
        "cited_program": "Arizona State Facilities Board / U.S. DOE",
    },
]

_INTERVENTIONS_BY_NAME = {
    intervention["intervention"]: intervention
    for intervention in INTERVENTIONS
}


def _median(values):
    """Return the median for available numeric values, or None."""
    values = sorted(float(value) for value in values if value is not None)
    if not values:
        return None

    middle = len(values) // 2
    if len(values) % 2 == 1:
        return values[middle]

    return (values[middle - 1] + values[middle]) / 2


def get_recommendations(cells, priority_threshold=0.7):
    """Generate 2-3 recommendations for high-priority cells.

    Recommendations are selected using simple, explainable MVP rules based on
    the data already produced by Feature 2.
    """

    recommendations = []

    # Convert cells to a list so we can compare each cell with the others.
    cells = list(cells)

    # Use the median as a simple "high compared with this batch" reference.
    solar_median = _median(cell.get("solar_ghi") for cell in cells)
    heat_index_median = _median(cell.get("heat_index_c") for cell in cells)
    vulnerability_median = _median(
        cell.get("vulnerability_score") for cell in cells
    )

    for cell in cells:
        cell_id = cell["cell_id"]
        priority_score = float(cell["priority_score"])

        # Ignore cells that are not high priority.
        if priority_score < priority_threshold:
            continue

        scores = {
            "Trees / shade": 1,
            "Cool pavement": 1,
            "Cool roof": 1,
        }

        # High solar exposure -> make cool roof more relevant.
        solar = cell.get("solar_ghi")
        if (
            solar is not None
            and solar_median is not None
            and float(solar) > solar_median
        ):
            scores["Cool roof"] += 2

        # High heat index -> make cool pavement more relevant.
        heat_index = cell.get("heat_index_c")
        if (
            heat_index is not None
            and heat_index_median is not None
            and float(heat_index) > heat_index_median
        ):
            scores["Cool pavement"] += 2

        # High vulnerability -> prioritize shade/tree intervention.
        vulnerability = cell.get("vulnerability_score")
        if (
            vulnerability is not None
            and vulnerability_median is not None
            and float(vulnerability) > vulnerability_median
        ):
            scores["Trees / shade"] += 2

        selected_names = sorted(
            scores,
            key=scores.get,
            reverse=True,
        )[:3]

        for name in selected_names:
            intervention = _INTERVENTIONS_BY_NAME[name]
            recommendations.append(
                Recommendation(
                    cell_id=cell_id,
                    intervention=intervention["intervention"],
                    cost_range=intervention["cost_range"],
                    benefit=intervention["benefit"],
                    con=intervention["con"],
                    cited_program=intervention["cited_program"],
                )
            )

    return recommendations
