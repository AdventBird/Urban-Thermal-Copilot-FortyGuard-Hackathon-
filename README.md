# Urban Thermal Copilot — V1 MVP Build (Aug 18–30 Hackathon)

FortyGuard Hackathon '26 — Track 4 (Government & Environment).
Demo city: **downtown Phoenix, AZ** (ZIP codes **85004 + 85007**). Named client:
Phoenix's **Office of Heat Response & Mitigation** (`FY2026 $8.9M` budget anchor).

---

## 🚦 Build Progress (for collaborators)

Last updated: **2026-08-24**. Tests: **29 passed, 1 skipped** (`python -m pytest -q tests/`).

This is a mid-build snapshot of the 9 deliverable workstreams in the V1 MVP
brief. **3 of 9 are functional**, **2 are partially built**, and **4 are not
started yet**. Each row below maps to the code you can find and run today.

| # | V1 Deliverable | Status | What exists / what's next |
|---|---|---|---|
| 1 | **Spatial Thermal Audit (Heat Map)** | ✅ DONE | `feature1_thermal.py` — `get_snapshot`, `tiles_to_grid`, `render_heatmap` (Folium/viridis), 32-tile AOI. Cached to `data/cache/`. |
| 2 | **Vulnerability Overlay** | ✅ DONE | `feature2_vulnerability.py` — OSM POIs, Census fallback, `compute_vulnerability_score`, `compute_priority_score`. |
| 5 | **Threshold Risk Flags** | 🟡 PARTIAL | `get_risk_flags()` (FortyGuard-native exceedance + persistence) exists in Feature 1. Missing: the "12-hour forecast limit" framing + last-summer historical-count wording. |
| 7 | **Multi-Year Trend View** | 🟡 PARTIAL | `get_yearly_trend()` exists in Feature 1 (2021–present). Missing: a rendered line-chart view / printed "X°C hotter across four summers" summary. |
| 3 | **Honest Matrix (Recommendation Engine)** | ⏳ NOT BUILT | Only the `Recommendation` dataclass exists in `contracts.py` (with the required `con` field). Need: curated intervention table + rule-based matcher. Suggested `feature3_recommendations.py`. |
| 4 | **Budget & Timeline Roadmap** | ⏳ NOT BUILT | Only the `Phase` dataclass exists in `contracts.py`. Need: greedy-phase fill, Phase 1/2/3 chart, "how this was prioritized" panel. Suggested `feature4_roadmap.py`. |
| 6 | **AI-Generated Report** | ⏳ NOT BUILT | No Claude/Sonnet integration yet. Need a server-side call + markdown rendering. |
| 8 | **Lightweight Correlation** | ⏳ NOT BUILT | No Maricopa County heat-outcome cross-reference yet. |
| 9 | **One-Slide Business Case** | 🟡 PARTIAL | Buy/budget framing only (this README) — no standalone pitch slide yet. |

> Legend: ✅ DONE · 🟡 PARTIAL (core logic in, demo-worthy UI/piece missing) · ⏳ NOT STARTED.

**Quickest path to a complete MVP** — in priority order a collaborator can grab:
core equity is 3 (Honest Matrix needs one static table + rule matcher) and
4 (Roadmap needs a greedy phase-fill). The others are thin wrappers on existing
Feature 1/2 outputs.

---

## What's currently shippable

| Module | Responsibility | Status |
|---|---|---|
| `utc/config.py` | Secrets + the single set of demo constants (bbox, demo date, risk threshold). | done |
| `utc/bbox.py` | Downtown-Phoenix closed-ring polygon (Nominatim live source, deterministic offline fallback). | done |
| `utc/contracts.py` | The agreed data shapes every feature respects (cell / recommendation / phase). | done |
| `utc/fortyguard_client.py` | One shared `submit_and_poll()` for all `/v1/*` endpoints + local JSON cache. | done |
| `utc/feature1_thermal.py` | Feature 1 — tcm snapshot + native exceedance/persistence flags, `tiles_to_grid`, `render_heatmap`, `get_yearly_trend`. | done |
| `utc/feature2_vulnerability.py` | Feature 2 — env params, OSM POIs, Census fallback, `compute_vulnerability_score`, `compute_priority_score`. | done |

### Setup

```bash
cp .env.example .env          # then paste your real FORTYGUARD_API_KEY in .env
pip install -r requirements.txt
python -m pytest -q tests/    # runs the full suite once deps are installed
```

Secrets live only in `.env` (gitignored — see `.gitignore`). Never hardcode keys.

## Shared data contract (Section 3)

Every grid cell, once Features 1 + 2 have run, carries at least:

```python
{
  "cell_id": str,
  "geometry": <Polygon>,
  "temperature_c": float,        # Feature 1 tcm snapshot
  "heat_index_c": float,         # Feature 2 env_params (used for scoring)
  "exceedance_hours": float,     # Feature 1 native risk flag
  "persistence_hours": float,    # Feature 1 native risk flag
  "solar_ghi": float,            # Feature 2 env_params (solar siting)
  "vulnerability_score": float,  # 0..1
  "priority_score": float        # 0..1 = heat_index_normalized * vulnerability_score
}
```

`utc/contracts.validate_cell()` enforces the required fields; a missing one is a
bug in the producing feature, not a change to make downstream.

## Feature 1 (Spatial Thermal Audit)

```python
from utc import bbox, feature1_thermal as f1
ring   = bbox.build_ring()                      # Phoenix 85004 + 85007

result = f1.get_snapshot(ring, date=config.DEMO_DATE)   # tcm snapshot
risk   = f1.get_risk_flags(ring, threshold=50.0)        # exceedance + persistence
grid   = f1.tiles_to_grid(result["map_data"])           # -> GeoDataFrame (UTM 12N)
my_map = f1.render_heatmap(grid)                        # -> folium.Map (viridis)
trend  = f1.get_yearly_trend(ring, month="07")          # [(year, mean_temp_c), ...]
```

Every result is cached to `data/cache/` (gitignored), so the demo runs offline
after the first successful API pull.

## Feature 2 (Vulnerability Overlay)

```python
from utc import config, feature2_vulnerability as f2
env    = f2.fetch_env_params(lat, lon, temp, date_time, fields=["heat_index_celsius", "solar_irradiance"])
pois   = f2.load_osm_pois(config.FIXTURE_DIR / "sample_osm_pois.json")
census = f2.fetch_census_data()                # hardcoded fallback unless CENSUS_API_KEY set
scored = f2.compute_vulnerability_score(grid, pois, census)
final  = f2.compute_priority_score(scored)     # sorted by priority, descending
```

Scoring formula is documented in each docstring (Honest-Matrix transparency).

## Honest notes for the team

- **Demo date unverified**: `config.DEMO_DATE` defaults to `2025-07-14` (a
  selected mid-July 2025 heat-event day). **Confirm the exact extreme-heat day
  against NWS/civic reporting before the live demo** and update the constant (or
  set `FORTYGUARD_DEMO_DATE`).
- **Fixtures are contract-shaped, not copied**: I could not reach the FortyGuard
  Quickstart repo's bundled cached responses from this sandbox, so `fixtures/*.json`
  are *structurally faithful* to the documented API contract. **Swap in the
  Quickstart's real cached responses** when you clone that repo for the most
  realistic offline demo.
- **Census numbers are placeholders**: the hardcoded ACS figures in
  `feature2_vulnerability.py` must be replaced with real census.gov estimates
  (S0101 / S1901) before judging — clearly commented.
- **Premium endpoints CONFIRMED, not yet wired**: on 2026-08-24 I verified the
  live key has **Premium** satellite access — a minimal `/v1/satellite` job (with
  nested `sat: {latitude, longitude}`) returned `Completed` with a 395×395 px
  segmentation of building/road/sidewalk/skyscraper classes for downtown Phoenix.
  No satellite code has been committed yet; it's a candidate for Feature 5+ if the
  team wants it.

## AI-edit provenance

Files here were authored by an AI assistant (Cline) at the team's request during
the hackathon build. Confirm exact calendar dates and swap in real cached
responses + census figures before presentation.