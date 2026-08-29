"""feature5_risk_flags.py -- Feature 5: FortyGuard-native risk flags.

Shows where/how long the 50 C (direction=above) threshold was exceeded and the
longest streak past it. These come straight from FortyGuard's ``exceedance`` and
``persistence`` analytics (threshold + direction) -- NOT a homegrown prediction.
"""
from __future__ import annotations


def _parse_properties(result, key: str) -> list:
    """Extract ``(cell_id, value)`` pairs for one analytic key.

    Handles both data shapes:
      * fixture -- ``properties['cell_id']`` + ``properties['{key}_hours']`` (or
        ``value``)
      * live    -- ``properties['tile_id']`` + ``properties['value']``
    Falls back to the tile index when no cell id is present so the table is
    never silently empty.
    """
    block = (result or {}).get(key)
    fc = block.get("map_data") if isinstance(block, dict) else block
    feats = (fc or {}).get("features", []) if isinstance(fc, dict) else []
    rows = []
    for i, f in enumerate(feats):
        props = f.get("properties") or {}
        cid = props.get("cell_id") or props.get("tile_id")
        if cid is None:
            cid = f.get("id") or f"cell_{i}"
        val = props.get(f"{key}_hours") or props.get("value") or 0.0
        try:
            rows.append((str(cid), float(val)))
        except (TypeError, ValueError):
            continue
    return rows


def parse_exceedance(result: dict) -> list:
    """Extract ``(cell_id, exceedance_hours)`` from an exceedance result.

    If the API returns per-tile properties we read them directly; otherwise we
    fall back to the grid's ``exceedance_hours`` column (already populated by the
    data layer), keeping the label "FortyGuard exceedance analytic".
    """
    rows = []
    fc = result.get("map_data") if isinstance(result, dict) else result
    feats = (fc or {}).get("features", []) if isinstance(fc, dict) else []
    for f in feats:
        props = f.get("properties") or {}
        if "exceedance_hours" in props:
            rows.append((props.get("cell_id"), float(props["exceedance_hours"])))
    return rows


def summarize(grid, exceedance_rows, threshold_c=50.0):
    """Build a human-readable per-cell risk summary dataframe.

    Preferred source is the API's exceedance rows; when that is empty (e.g. mock
    fixtures with no per-tile property) we fall back to the grid's own
    ``exceedance_hours`` / ``persistence_hours`` columns.
    """
    import pandas as pd

    if exceedance_rows:
        df = pd.DataFrame(exceedance_rows, columns=["cell_id", "exceedance_hours"])
        df = df.merge(grid[["cell_id", "temperature_c"]], on="cell_id", how="left")
    else:
        df = grid[["cell_id", "temperature_c", "exceedance_hours", "persistence_hours"]].copy()
    df["exceedance_hours"] = df["exceedance_hours"].fillna(0.0)
    if "persistence_hours" not in df.columns:
        df["persistence_hours"] = 0.0
    df = df.sort_values("exceedance_hours", ascending=False).reset_index(drop=True)
    df.insert(0, "risk_summary", df["exceedance_hours"].apply(
        lambda h: f"exceeded {threshold_c:.0f} C for {h:.1f} h" if h > 0 else "below threshold"))
    return df


def render_markdown(flags: dict) -> str:
    """Render the risk-flag analytics as readable markdown for ``st.markdown``.

    Handles both the fixture shape (``exceedance`` + ``_meta``) and the live
    shape (``exceedance`` + ``persistence``). Only cells actually above the
    threshold are listed; a live analytic that returned no exceedances reports
    that honestly instead of implying measurements that aren't there.
    """
    exc = _parse_properties(flags, "exceedance")
    per = _parse_properties(flags, "persistence")

    def _section(title, threshold, rows):
        offenders = [r for r in rows if r[1] > 0]
        offenders.sort(key=lambda r: r[1], reverse=True)
        lines = [f"**{title}** ({threshold}): {len(offenders)} cell(s) above threshold."]
        if not offenders:
            lines.append("*No cells exceeded the threshold in this snapshot.*")
            return "\n".join(lines)
        table = ["| Zone | Hours |", "|---|---|"] + [
            f"| `{cid}` | {val:.1f} |" for cid, val in offenders[:8]
        ]
        return "\n".join(lines + table)

    # Optional live stats block (min/max/mean) for extra precision when present.
    stats = ""
    block = (flags or {}).get("exceedance") or {}
    sd = block.get("stats_data") if isinstance(block, dict) else None
    if isinstance(sd, dict) and sd.get("mean") is not None:
        stats = (f"\n\n*Live analytic: {sd.get('n_cells', '—')} cells · "
                 f"min {sd.get('min', 0):.1f} h · max {sd.get('max', 0):.1f} h · "
                 f"mean {sd.get('mean', 0):.1f} h*")

    return "\n".join([
        "**Risk exposure flags — where/when heat crossed the threshold**",
        "",
        _section("Exceedance", "peak > 50°C", exc),
        "",
        _section("Persistence", "sustained > 47°C", per),
        stats,
        "",
        "*Source: FortyGuard exceedance / persistence analytics on this snapshot.*",
    ])