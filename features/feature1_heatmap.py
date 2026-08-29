"""feature1_heatmap.py -- Feature 1: hyperlocal heat map.

Renders the shared, contract-conforming grid as a color-blind-safe Folium map
with a legend, plus a sortable table of the hottest cells. The palette is a
viridis ramp (no red/green) so it stays legible for color-blind viewers.
"""
from __future__ import annotations


def render_map(grid, temperature_col="temperature_c"):
    """Return a Folium map of the grid colored by ``temperature_col``.

    ``grid`` is the shared GeoDataFrame from ``data_layer.build_grid``. The
    optional ``temperature_col`` lets us swap in heat-index or priority for
    different tabs.
    """
    import folium
    from pyproj import Transformer

    geod = grid.to_crs("EPSG:4326")
    proj = grid.to_crs("EPSG:32612")
    mx, my = float(proj.geometry.centroid.x.mean()), float(proj.geometry.centroid.y.mean())
    t = Transformer.from_crs("EPSG:32612", "EPSG:4326", always_xy=True)
    clon, clat = t.transform(mx, my)

    m = folium.Map(location=[float(clat), float(clon)], zoom_start=13, tiles="OpenStreetMap", control_scale=True)

    vals = [float(v) for v in geod[temperature_col].dropna()]
    if not vals:
        return m
    vmin, vmax = min(vals), max(vals)

    import branca
    cmap = branca.colormap.LinearColormap(
        colors=[  # viridis-like, colorblind-safe
            "#440154", "#482878", "#3f4889", "#33698f", "#2f8a8a",
            "#28a87e", "#3fc26d", "#8cd05a", "#d4e046", "#fde725",
        ],
        vmin=vmin, vmax=vmax, caption=f"FortyGuard {temperature_col}",
    )

    def _style(feature):
        v = float(feature["properties"][temperature_col])
        return {"fillColor": cmap(v), "color": "#444444", "weight": 0.5, "fillOpacity": 0.7}

    folium.GeoJson(geod, name="Grid", style_function=_style).add_to(m)
    cmap.add_to(m)
    folium.LayerControl().add_to(m)
    return m


def top_cells(grid, n=8):
    """Return the hottest cells as a plain list of dicts for tabular display."""
    g = grid.sort_values("temperature_c", ascending=False).head(n)
    return g[["cell_id", "temperature_c", "heat_index_c", "vulnerability_score", "priority_score"]].to_dict("records")


def summary_stats(grid):
    """Return simple summary metrics dict for headline cards."""
    import statistics
    temps = [float(t) for t in grid["temperature_c"].dropna()]
    return {
        "cells": int(len(grid)),
        "mean_c": round(statistics.mean(temps), 2) if temps else 0.0,
        "max_c": round(max(temps), 2) if temps else 0.0,
        "min_c": round(min(temps), 2) if temps else 0.0,
    }


# --------------------------------------------------------------------------- #
# Risk-condition classification (used by the explorer map + inspector)
# --------------------------------------------------------------------------- #
SEVERITY_LEVELS = [
    ("terrible", 0.60, "#b5179e"),
    ("bad", 0.40, "#e85d04"),
    ("fair", 0.20, "#f2b705"),
    ("good", -float("inf"), "#2a9d8f"),
]


def classify_priority(priority: float):
    """Map a 0..1 priority score to a (level, hexcolor) bucket.

    terrible >= 0.60 · bad >= 0.40 · fair >= 0.20 · good otherwise.
    Colors are chosen to stay distinct under common color-vision deficiencies
    and are always accompanied by a text label (never color-only).
    """
    p = float(priority)
    for level, thr, color in SEVERITY_LEVELS:
        if p >= thr:
            return level, color
    return SEVERITY_LEVELS[-1][0], SEVERITY_LEVELS[-1][2]


def severity_color(level: str) -> str:
    for name, _, color in SEVERITY_LEVELS:
        if name == level:
            return color
    return "#2a9d8f"


def priority_label(priority: float) -> str:
    """Plain-language takeaway from a 0-1 priority_score: High/Medium/Low.

    terrible -> High · bad -> Medium · fair/good -> Low. Shown next to the raw
    number so a non-technical user never has to interpret the float.
    """
    level, _ = classify_priority(float(priority))
    return {"terrible": "High", "bad": "Medium"}.get(level, "Low")


_VIRIDIS = ["#440154", "#482878", "#3f4889", "#33698f", "#2f8a8a",
            "#28a87e", "#3fc26d", "#8cd05a", "#d4e046", "#fde725"]


def render_explorer_map(grid, center=None, show_vulnerability=False, pois=None,
                        show_landmarks=True, center_name=None):
    """Interactive, full-bleed map with temperature, place markers & vulnerability.

    Layers:
      * Base Tiles: Crisp, unwatermarked OpenStreetMap (Streets) and Esri Satellite.
      * "Heat · temperature"  — viridis ambient-temperature base (colorblind-safe).
      * "🏛️ Landmarks & Districts" — Place markers and civic landmarks to identify
        where you are.
      * "Vulnerability · priority" (when toggled on) — bold borders on bad/terrible cells.
      * "🎓 Facilities & Transit (POIs)" (when toggled on) — schools, hospitals, transit.
      * Locate Me control — Click to instantly view your GPS location on the map.
      * Geocoder search — Search any address or landmark inside the map.
    """
    import folium
    from folium import plugins as fplugins
    import branca
    from pyproj import Transformer
    from features import data_layer as dl

    geod = grid.to_crs("EPSG:4326")
    if center is None:
        proj = grid.to_crs("EPSG:32612")
        mx, my = float(proj.geometry.centroid.x.mean()), float(proj.geometry.centroid.y.mean())
        t = Transformer.from_crs("EPSG:32612", "EPSG:4326", always_xy=True)
        clon, clat = t.transform(mx, my)
    else:
        clat, clon = float(center[0]), float(center[1])

    # Initialize map without default tiles to add clean custom basemaps with nice names
    m = folium.Map(location=[clat, clon], zoom_start=14, control_scale=True, tiles=None)

    # 1. Clean, high-performance base map layers (no watermarks)
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        name="🗺️ OpenStreetMap (Detailed Streets)",
        attr="&copy; OpenStreetMap contributors",
        max_zoom=19,
        control=True,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="🛰️ Esri Satellite (Ground Imagery)",
        attr="&copy; Esri, Maxar, Earthstar Geographics",
        max_zoom=19,
        control=True,
    ).add_to(m)

    # 2. Interactive Navigation Plugins (Locate Me & In-Map Geocoder)
    fplugins.LocateControl(
        auto_start=False,
        flyTo=True,
        keepCurrentZoomLevel=False,
        drawCircle=True,
        position="topleft",
        strings={"title": "🎯 Locate My GPS Position"},
    ).add_to(m)

    fplugins.Fullscreen(position="topleft").add_to(m)
    fplugins.Geocoder(collapsed=True, position="topright", placeholder="🔍 Search address or place...").add_to(m)

    # 3. Ambient temperature layer (FortyGuard 2-metre)
    vals = [float(v) for v in geod["temperature_c"].dropna()]
    if vals:
        vmin, vmax = min(vals), max(vals)
        cmap = branca.colormap.LinearColormap(
            colors=_VIRIDIS, vmin=vmin, vmax=vmax, caption="FortyGuard Ambient Temp (°C)"
        )

        def _temp_style(f):
            return {
                "fillColor": cmap(float(f["properties"]["temperature_c"])),
                "color": "#475569",
                "weight": 1.2,
                "fillOpacity": 0.74,
            }

        folium.GeoJson(
            geod,
            name="🔥 Heat · Ambient Temperature",
            style_function=_temp_style,
            highlight_function=lambda f: {"fillOpacity": 0.96, "weight": 3.5, "color": "#0ea5e9"},
            tooltip=folium.GeoJsonTooltip(
                fields=["cell_id", "temperature_c", "heat_index_c", "priority_score"],
                aliases=["Zone ID", "Temp °C", "Heat Index °C", "Priority Score"],
                localize=True,
                style="background:rgba(15,23,42,0.92); color:#fff; font-family:'Plus Jakarta Sans',sans-serif; border:1px solid #6366f1; border-radius:8px; padding:8px 12px;",
            ),
        ).add_to(m)
        cmap.add_to(m)

    # 4. Civic Landmarks & Place Identifiers Layer (Helps the user know what place is what)
    if show_landmarks and hasattr(dl, "CIVIC_LANDMARKS"):
        landmark_group = folium.FeatureGroup(name="🏛️ Civic Landmarks & Districts", show=True)
        for lm in dl.CIVIC_LANDMARKS:
            lat, lon = float(lm["lat"]), float(lm["lon"])
            # Sleek emoji marker pin
            pin_html = f"""
            <div style="display:flex; align-items:center; justify-content:center;
                        width:32px; height:32px; border-radius:50%;
                        background:#0f172a; border:2px solid #8b5cf6;
                        box-shadow:0 2px 10px rgba(139,92,246,0.6);
                        font-size:16px; cursor:pointer;"
                 title="{lm['name']} · {lm['district']}">
                {lm['icon']}
            </div>
            """
            popup_html = f"""
            <div style="font-family:'Plus Jakarta Sans',sans-serif; min-width:200px; padding:6px;">
                <div style="font-weight:800; font-size:14px; color:#1e1b4b; display:flex; align-items:center; gap:6px;">
                    <span>{lm['icon']}</span><span>{lm['name']}</span>
                </div>
                <div style="font-size:11px; color:#7c3aed; font-weight:700; text-transform:uppercase; margin-top:2px;">
                    {lm['district']}
                </div>
                <div style="font-size:12px; color:#334155; margin-top:6px; line-height:1.4;">
                    {lm['desc']}
                </div>
                <div style="font-size:11px; color:#64748b; margin-top:6px;">
                    📍 {lat:.4f}°N, {abs(lon):.4f}°W
                </div>
            </div>
            """
            folium.Marker(
                [lat, lon],
                icon=folium.DivIcon(html=pin_html, icon_size=(32, 32), icon_anchor=(16, 16)),
                popup=folium.Popup(popup_html, max_width=280),
                tooltip=f"<b>{lm['icon']} {lm['name']}</b><br/><span style='color:#7c3aed;'>{lm['district']}</span>",
            ).add_to(landmark_group)
        landmark_group.add_to(m)

    # 5. Active Analysis Center Focus Pin
    if center_name or center:
        c_label = center_name or "Active Focus Area"
        focus_html = f"""
        <div style="background:linear-gradient(135deg, #7c3aed, #db2777); color:#fff;
                    font-weight:700; font-size:11px; padding:3px 9px; border-radius:999px;
                    box-shadow:0 2px 12px rgba(124,58,237,0.6); border:2px solid #fff;
                    display:inline-flex; align-items:center; gap:5px; white-space:nowrap;">
            <span style="font-size:13px;">📍</span><span>{c_label}</span>
        </div>
        """
        folium.Marker(
            [clat, clon],
            icon=folium.DivIcon(html=focus_html, icon_size=(160, 26), icon_anchor=(80, 13)),
            tooltip=f"Current Focus Area: {c_label}",
        ).add_to(m)

    # 6. Vulnerability & Priority Overlay (when toggled on)
    if show_vulnerability:
        def _sev_style(f):
            level, color = classify_priority(float(f["properties"]["priority_score"]))
            strong = level in ("terrible", "bad")
            return {
                "fillColor": color,
                "color": "#0f172a" if strong else color,
                "weight": 3.8 if strong else 1.6,
                "fillOpacity": 0.84 if strong else 0.18,
            }

        folium.GeoJson(
            geod,
            name="⚠️ Vulnerability · High-Risk Overlay",
            style_function=_sev_style,
            highlight_function=lambda f: {"fillOpacity": 0.96, "weight": 4.5, "color": "#ffffff"},
            tooltip=folium.GeoJsonTooltip(
                fields=["cell_id", "priority_score"],
                aliases=["Zone ID", "Priority Score"],
                localize=True,
                style="background:rgba(15,23,42,0.92); color:#fff; font-family:'Plus Jakarta Sans',sans-serif; border:1px solid #e11d48; border-radius:8px; padding:8px 12px;",
            ),
        ).add_to(m)

        # OSM POI markers (schools / transit / hospitals / elder care)
        if pois is not None and len(pois):
            poi4426 = pois.to_crs("EPSG:4326")
            icons = {
                "school": "🎓",
                "hospital": "🏥",
                "transit": "🚌",
                "bus_stop": "🚌",
                "elder_care": "🏠",
                "social_facility": "🏠",
            }
            poi_group = folium.FeatureGroup(name="🎓 Facilities & Transit (POIs)", show=True)
            for _, p in poi4426.iterrows():
                cat = str(p.get("category") or p.get("element_type") or "poi")
                icon = icons.get(cat, "📍")
                name = p.get("name") or cat.replace("_", " ").title()
                folium.Marker(
                    [float(p.geometry.y), float(p.geometry.x)],
                    icon=folium.DivIcon(
                        html=(
                            f"<div style='font-size:18px;line-height:18px;filter:drop-shadow(0 2px 4px rgba(0,0,0,0.5));' "
                            f"title='{name} ({cat})'>{icon}</div>"
                        )
                    ),
                    tooltip=f"<b>{icon} {name}</b><br/>Category: {cat.title()}",
                ).add_to(poi_group)
            poi_group.add_to(m)

    folium.LayerControl(collapsed=False, position="topright").add_to(m)
    return m