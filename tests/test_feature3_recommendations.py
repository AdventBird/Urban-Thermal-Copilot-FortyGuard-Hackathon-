"""Tests for Feature 3 - Honest Matrix."""

from utc.contracts import REQUIRED_RECOMMENDATION_FIELDS
from utc.feature3_recommendations import get_recommendations


def test_high_priority_cell_gets_three_recommendations():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
        }
    ]

    recommendations = get_recommendations(cells)

    assert len(recommendations) == 3
    assert all(r.cell_id == "A" for r in recommendations)


def test_low_priority_cell_gets_no_recommendations():
    cells = [
        {
            "cell_id": "B",
            "priority_score": 0.4,
        }
    ]

    recommendations = get_recommendations(cells)

    assert recommendations == []


def test_high_solar_cell_prioritizes_cool_roof():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
            "solar_ghi": 1000,
            "heat_index_c": 35,
            "vulnerability_score": 0.2,
        },
        {
            "cell_id": "B",
            "priority_score": 0.5,
            "solar_ghi": 500,
            "heat_index_c": 35,
            "vulnerability_score": 0.8,
        },
    ]

    recommendations = get_recommendations(cells)

    assert recommendations[0].intervention == "Cool roof"


def test_high_heat_index_cell_prioritizes_cool_pavement():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
            "solar_ghi": 500,
            "heat_index_c": 45,
            "vulnerability_score": 0.2,
        },
        {
            "cell_id": "B",
            "priority_score": 0.5,
            "solar_ghi": 500,
            "heat_index_c": 35,
            "vulnerability_score": 0.8,
        },
    ]

    recommendations = get_recommendations(cells)

    assert recommendations[0].intervention == "Cool pavement"


def test_high_vulnerability_cell_prioritizes_trees():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
            "solar_ghi": 500,
            "heat_index_c": 35,
            "vulnerability_score": 0.9,
        },
        {
            "cell_id": "B",
            "priority_score": 0.5,
            "solar_ghi": 500,
            "heat_index_c": 35,
            "vulnerability_score": 0.2,
        },
    ]

    recommendations = get_recommendations(cells)

    assert recommendations[0].intervention == "Trees / shade"


def test_recommendations_have_required_fields():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
        }
    ]

    recommendations = get_recommendations(cells)

    for recommendation in recommendations:
        data = recommendation.as_dict()
        for field in REQUIRED_RECOMMENDATION_FIELDS:
            assert data[field]


def test_every_recommendation_has_a_con():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
        }
    ]

    recommendations = get_recommendations(cells)

    assert all(r.con.strip() for r in recommendations)


def test_missing_optional_scoring_fields_do_not_crash():
    cells = [
        {
            "cell_id": "A",
            "priority_score": 0.9,
        },
        {
            "cell_id": "B",
            "priority_score": 0.8,
            "solar_ghi": None,
            "heat_index_c": None,
            "vulnerability_score": None,
        },
    ]

    recommendations = get_recommendations(cells)

    assert len(recommendations) == 6
    assert {r.cell_id for r in recommendations} == {"A", "B"}
