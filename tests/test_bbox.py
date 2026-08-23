"""Tests for utc.bbox: closed-ring polygon, feature-collection shape, AOI cap."""
import json

from utc import bbox


def test_default_ring_is_closed():
    ring = bbox.fallback_ring()
    assert ring[0] == ring[-1], "ring must close (first == last coordinate pair)"


def test_close_ring_idempotent():
    opened = [[-112.145, 33.435], [-112.06, 33.435], [-112.06, 33.48], [-112.145, 33.48]]
    closed = bbox.close_ring(opened)
    assert closed[0] == closed[-1]
    assert bbox.close_ring(closed) == closed


def test_coordinate_order_is_lon_lat():
    ring = bbox.fallback_ring()
    for lon, lat in ring:
        assert -180 <= lon <= 180    # first is longitude
        assert -90 <= lat <= 90      # second is latitude


def test_feature_collection_matches_api_contract():
    fc = bbox.build_feature_collection(bbox.fallback_ring())
    assert fc["type"] == "FeatureCollection"
    (feature,) = fc["features"]
    assert feature["type"] == "Feature"
    assert feature["properties"] == {}
    assert feature["geometry"]["type"] == "Polygon"
    coords = feature["geometry"]["coordinates"][0]
    assert coords[0] == coords[-1], "polygon ring must close"


def test_area_under_aoi_cap():
    ring = bbox.fallback_ring()
    area = bbox.area_km2(ring)
    assert 0 < area < 130, f"expected well under the ~130 km2 cap, got {area}"


def test_bbox_hash_stable_and_sensitive():
    ring = bbox.fallback_ring()
    assert bbox.bbox_hash(ring) == bbox.bbox_hash(bbox.close_ring(ring))
    other = list(ring)
    other[0] = [-112.15, 33.43]  # nudge a corner
    assert bbox.bbox_hash(other) != bbox.bbox_hash(ring)


def test_to_ring_normalizes_unclosed():
    opened = [[-112.1, 33.43], [-112.06, 33.43], [-112.06, 33.48], [-112.1, 33.48]]
    assert bbox.to_ring(opened)[0] == bbox.to_ring(opened)[-1]


def test_feature_collection_json_encodes_cleanly():
    fc = bbox.build_feature_collection(bbox.fallback_ring())
    # If this round-trips, the structure is plain JSON (cache-safe).
    json.loads(json.dumps(fc))