"""Feature 10 satellite segmentation tests (incl. implausible-class exclusion)."""
import logging

import pytest

from features import feature10_satellite as f10


def test_payload_shape_matches_confirmed_contract():
    p = f10.build_payload(33.45, -112.07)
    assert p["latitude"] == 33.45
    assert p["sat"]["latitude"] == 33.45 and p["sat"]["longitude"] == -112.07
    assert p["date_time"]["filter_type"] == 1   # single hour
    assert p["granularity"] == 100


def test_score_plausible_classes_only():
    seg = [
        {"class": "building", "percentage": 30},
        {"class": "road, route", "percentage": 30},
        {"class": "sky", "percentage": 40},
    ]
    score = f10.score_segmentation(seg)
    assert 0.0 <= score <= 1.0
    assert score > 0.5  # mostly built/paved


def test_implausible_ship_class_is_excluded(caplog):
    seg = [
        {"class": "building", "percentage": 30},
        {"class": "ship", "percentage": 70},  # implausible for landlocked Phoenix
    ]
    with caplog.at_level(logging.WARNING):
        score = f10.score_segmentation(seg)
    assert any("implausible class" in rec.message for rec in caplog.records)
    assert score == pytest.approx(1.0)  # ship's 70% ignored, building only


def test_empty_segmentation_neutral():
    assert f10.score_segmentation([]) == pytest.approx(0.5)


def test_fixture_scores_loadable():
    scores = f10.load_fixture_scores()
    assert len(scores) >= 1
    assert all("surface_heat_lens_score" in s for s in scores)