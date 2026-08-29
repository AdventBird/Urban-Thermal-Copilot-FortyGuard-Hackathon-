"""demo.py -- quick end-to-end smoke test / usage example for the V1 build.

Runs Features 1 + 2 end-to-end against the live FortyGuard API (caching every
result to data/cache/ so a re-run works even offline), then writes:
    * heatmap_downtown_phoenix.html  -- color-coded Folium heat map you can open
                                        in any browser
    * prints a short summary of the grid + vulnerability/priority scoring.

Usage:
    python demo.py

If you just want the offline path (no live API), the API data is cached on the
first successful run, so simply running it a second time uses cached JSON.
Set FORTYGUARD_DEMO_DATE to override the demo date if you wish.
"""
from __future__ import annotations

from utc import bbox, config
from utc import feature1_thermal as f1
from utc import feature2_vulnerability as f2


def main() -> None:
    print("Building demo bounding box for downtown Phoenix (85004 + 85007)...")
    ring = bbox.build_ring()

    # --- Feature 1: heat snapshot + native risk flags + map ------------------
    print(f"Fetching tcm snapshot for {config.DEMO_DATE} (cached once live) ...")
    # First live run of the full demo box can take SEVERAL MINUTES to process.
    # Bump the poll timeout well past the 60s default so it can finish + cache.
    snap = f1.get_snapshot(ring, date=config.DEMO_DATE, timeout_s=600.0)

    print("Fetching exceedance + persistence risk flags ...")
    risk = f1.get_risk_flags(ring, threshold=config.RISK_THRESHOLD_C, timeout_s=600.0)

    grid = f1.tiles_to_grid(snap["map_data"] if isinstance(snap, dict) and "map_data" in snap else snap)
    print(f"Grid cells from tcm tiles: {len(grid)}; temperature range "
          f"{float(grid['temperature_c'].min()):.1f}-{float(grid['temperature_c'].max()):.1f} deg C")

    my_map = f1.render_heatmap(grid)
    out_map = "heatmap_downtown_phoenix.html"
    my_map.save(out_map)
    print(f"Wrote heat map -> {out_map}  (open in a browser)")

    # --- Feature 2: vulnerability + priority scoring -------------------------
    print("Computing vulnerability + priority scores (using sample POIs + census fallback)...")
    pois = f2.load_osm_pois(config.FIXTURE_DIR / "sample_osm_pois.json")
    census = f2.fetch_census_data()
    scored = f2.compute_vulnerability_score(grid, pois, census)
    final = f2.compute_priority_score(scored)
    print("\nTop 3 priority cells:")
    for row in final.head(3).itertuples():
        print(f"  {row.cell_id}: heat_index={float(row.heat_index_c):.1f}C  "
              f"vuln={float(row.vulnerability_score):.2f}  priority={float(row.priority_score):.2f}")

    print("\nDemo pipeline OK. Tests: run `python -m pytest -q tests/`.")


if __name__ == "__main__":
    main()