"""Verify secrets handling: key must come from the env, never hardcoded."""

import pytest

from utc import config


def test_placeholder_key_is_rejected():
    """Until a real key is in .env, get_api_key() must raise (guards a fake-403 demo)."""
    placeholder = config.FORTYGUARD_API_KEY
    if placeholder and not placeholder.lower().startswith(("your_", "replace", "fake", "changeme")):
        pytest.skip("a real-looking key is already configured in this environment")
    with pytest.raises(RuntimeError):
        config.get_api_key()


def test_base_url_default():
    assert config.FORTYGUARD_BASE_URL.startswith("https://")


def test_fixture_dir_is_readable():
    from utc import config as c
    sample = c.read_fixture("sample_env_params.json")
    assert "locations" in sample