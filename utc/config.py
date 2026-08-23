"""Central configuration: secrets, demo constants, and filesystem anchors.

Both Feature 1 and Feature 2 share these so the team pins ONE set of demo
inputs (the fixed downtown Phoenix bounding box, a real 2025 extreme-heat day,
the asphalt-softening risk threshold) instead of scattering literals across
modules. Change a default here once and every module picks it up.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

# Project root = the parent of this package folder (the repo root).
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Load credentials from a local .env file. That file is gitignored, so real
# API keys are never committed to version control (see .gitignore).
load_dotenv(PROJECT_ROOT / ".env")

# ---------------------------------------------------------------------------
# FortayGuard connection -- always read from the environment, never hardcode.
# ---------------------------------------------------------------------------
FORTYGUARD_BASE_URL = os.getenv("FORTYGUARD_BASE_URL", "https://api.fortyguard.com")
FORTYGUARD_API_KEY = os.getenv("FORTYGUARD_API_KEY", "").strip()


def get_api_key() -> str:
    """Return the configured API key, or raise a clear, actionable error.

    We also reject the placeholder / obvious test values so a teammate does not
    accidentally run a demo call with a fake key and get a confusing 403.
    """
    if not FORTYGUARD_API_KEY or FORTYGUARD_API_KEY.lower().startswith(
        ("your_", "replace", "fake", "changeme")
    ):
        raise RuntimeError(
            "FORTYGUARD_API_KEY is not configured. Copy `.env.example` to `.env` "
            "and paste your real FortyGuard API key there, then re-run."
        )
    return FORTYGUARD_API_KEY


# ---------------------------------------------------------------------------
# Filesystem anchors
# ---------------------------------------------------------------------------
# Local JSON cache fallback (gitignored). The whole demo must run offline from
# these after the first successful API pull.
CACHE_DIR = PROJECT_ROOT / "data" / "cache"
# Committable offline sample data, so Feature 2 can be developed before the
# API credentials / few public endpoints are reachable.
FIXTURE_DIR = PROJECT_ROOT / "fixtures"


def cache_dir() -> Path:
    """Create and return the cache directory (creates it on first use)."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR


def read_fixture(name: str) -> dict | list:
    """Load a committable JSON fixture by filename (e.g. ``sample_env_params.json``)."""
    with open(FIXTURE_DIR / name, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Fixed demo inputs (project brief, Track 4)
# ---------------------------------------------------------------------------
DEMO_ZONES = ("85004", "85007")     # downtown Phoenix ZIP codes (contiguous)

# Demo date: a real extreme-heat day from Phoenix's 2025 season.
#
# NOTE (team): verify the exact calendar day / high temp against the National
# Weather Service + civic reporting before the live demo, and update this in
# ONE place. The default here is the selected mid-July 2025 heat-event day; you
# may override it at runtime with the FORTYGUARD_DEMO_DATE env var.
DEMO_DATE = os.getenv("FORTYGUARD_DEMO_DATE", "2025-07-14")
DEMO_TIME = "15:00"                  # ~3,00 PM local: near the afternoon heat peak
DEMO_GRANULARITY = 100               # meters; 100 is the coarsest/cheapest of {60,80,100}
RISK_THRESHOLD_C = 50.0              # Celsius, ~122 F: the asphalt-softening reference point
RISK_DIRECTION = "above"