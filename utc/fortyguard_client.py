"""fortyguard_client.py -- shared async client for all ``/v1/*`` endpoints.

Important: every FortyGuard endpoint (``/v1/heatmap``, ``/v1/env_params``)
uses the same submit-then-poll pattern, so we reuse ONE helper here:

  1. POST a payload -> the API answers ``{data: {activity_id}}``.
  2. Poll ``GET /v1/status/{activity_id}`` until ``data.status`` is
     ``"Completed"`` (or ``"Failed"``, which is terminal -- we raise and never
     retry the same activity).

Quriks we handle in plain sight (teammates are first-timers):
  * status strings are capitalized (``"Completed"`` / ``"Failed"``) -- we
    compare with ``.lower()`` defensively.
  * credits are only deducted on ``Completed``; a ``Failed`` (or timed-out)
    job costs nothing.
  * the API key header is ``api-key`` (not an Authorization Bearer).

We also own the local JSON cache: every successful result is written to
``data/cache/<key>.json`` and re-used on re-run so the demo keeps working
even if the live API is unreachable during judging.
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Dict, Optional

import requests

from . import config

log = logging.getLogger(__name__)

HEATMAP_URL = f"{config.FORTYGUARD_BASE_URL}/v1/heatmap"
ENV_PARAMS_URL = f"{config.FORTYGUARD_BASE_URL}/v1/env_params"
STATUS_URL_TPL = f"{config.FORTYGUARD_BASE_URL}/v1/status/{{activity_id}}"

# Prescribed ascending backoff (seconds) per the handbook: 3s -> 6s -> 12s.
# We hold at 12s (the largest) for any further polls until the timeout.
BACKOFF_SECONDS = (3, 6, 12)

_READ_TIMEOUT = 30.0


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
def get_headers() -> dict:
    """Headers every FortyGuard call needs. Key is read live from the env."""
    return {"api-key": config.get_api_key(), "Content-Type": "application/json"}


# ---------------------------------------------------------------------------
# Local JSON cache (Feature 1/2 offline fallback)
# ---------------------------------------------------------------------------
def cache_path(cache_key: str) -> Path:
    """Full path to a cache file for a key (no I/O)."""
    return config.cache_dir() / f"{cache_key}.json"


def load_cached_json(cache_key: str) -> Optional[dict]:
    """Return cached file contents, or ``None`` if the key is not cached."""
    p = cache_path(cache_key)
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_cached_json(cache_key: str, data) -> Path:
    """Persist a JSON-serializable object under a cache key; returns the path."""
    p = cache_path(cache_key)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, default=str)
    return p


# ---------------------------------------------------------------------------
# Low-level submit / poll
# ---------------------------------------------------------------------------
def create_activity(url: str, payload: dict) -> str:
    """POST a job; return the ``activity_id`` (no polling yet)."""
    resp = requests.post(url, json=payload, headers=get_headers(), timeout=_READ_TIMEOUT)
    resp.raise_for_status()
    body = resp.json()
    if body.get("error"):
        raise RuntimeError(f"FortyGuard submission error: {body.get('message')}")
    return body["data"]["activity_id"]


def poll_status(activity_id, timeout_s: float = 60.0) -> dict:
    """Poll a job to completion using increasing backoff (3s->6s->12s).

    Returns the ``data.result`` payload on success. Raises:
      * RuntimeError on a terminal ``Failed`` status (never retried);
      * TimeoutError if still ``Processing`` when ``timeout_s`` elapses.
    """
    url = STATUS_URL_TPL.format(activity_id=activity_id)
    start = time.time()
    time.sleep(1.0)  # give the job a beat before the first poll
    attempt = 0
    while True:
        if time.time() - start >= timeout_s:
            raise TimeoutError(
                f"Timeout after {timeout_s:.0f}s waiting for activity {activity_id} "
                "(still Processing). A timed-out job is NOT charged credits."
            )
        resp = requests.get(url, headers=get_headers(), timeout=_READ_TIMEOUT)
        resp.raise_for_status()
        body = resp.json()
        if body.get("error"):
            raise RuntimeError(f"FortyGuard status error: {body.get('message')}")
        info = body.get("data") or {}
        # Compare defensively on the lowercased status (API reports "Completed").
        status = str(info.get("status", "")).lower()
        if status == "completed":
            return info.get("result", {})
        if status == "failed":
            log.error("Activity %s FAILED (terminal; not retried).", activity_id)
            raise RuntimeError(f"FortyGuard activity {activity_id} failed (terminal). {body.get('message','')}")
        # still Processing -> sleep the increasing backoff, repeating the last
        step = BACKOFF_SECONDS[min(attempt, len(BACKOFF_SECONDS) - 1)]
        time.sleep(step)
        attempt += 1


def submit_and_poll(url: str, payload: dict, timeout_s: float = 60.0) -> dict:
    """One shared helper: submit then poll an async FortyGuard job.

    Feature 1 (heatmap) and Feature 2 (env_params) both call this -- never
    duplicate the poll loop. Returns the endpoint's ``result`` payload.
    """
    activity_id = create_activity(url, payload)
    return poll_status(activity_id, timeout_s=timeout_s)