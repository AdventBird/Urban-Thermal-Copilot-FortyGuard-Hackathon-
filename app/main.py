"""Urban Thermal Copilot — Hyperlocal cooling plan for city planning & heat mitigation.

Built for the FortyGuard Hackathon '26 (Track 4: Government & Environment).
City of Phoenix Office of Heat Response and Mitigation (OHRM).
"""
import sys
from pathlib import Path

import streamlit as st

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from features import (  # noqa: E402
    data_layer as dl,
    feature1_heatmap as f1,
    feature3_honest_matrix as f3,
    feature4_roadmap as f4,
    feature5_risk_flags as f5,
    feature6_report as f6,
    feature7_trend as f7,
    feature8_correlation as f8,
)

st.set_page_config(
    page_title="Urban Thermal Copilot | Phoenix OHRM",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


# --------------------------------------------------------------------------- #
# Premium Design System & Typography
# --------------------------------------------------------------------------- #
def inject_css():
    st.markdown(
        """
<style>
  @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@500;700&display=swap');

  :root {
    --bg-primary: #0b0f19;
    --bg-surface: #111827;
    --bg-card: rgba(17, 24, 39, 0.75);
    --border-color: rgba(255, 255, 255, 0.1);
    --accent-purple: #8b5cf6;
    --accent-cyan: #06b6d4;
    --accent-pink: #ec4899;
    --accent-amber: #f59e0b;
    --accent-rose: #f43f5e;
    --accent-emerald: #10b981;
    --text-main: #f8fafc;
    --text-muted: #94a3b8;
  }

  html, body, [class*="css"], .stMarkdown, p, div, span, label {
    font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif !important;
  }

  code, pre, .font-mono {
    font-family: 'JetBrains Mono', monospace !important;
  }

  .block-container {
    max-width: 100% !important;
    padding: 0.5rem 1.25rem 2rem !important;
  }

  [data-testid="stHeader"] {
    background: transparent !important;
  }

  section.main > div {
    padding-top: 0 !important;
  }

  [data-testid="stVerticalBlock"] {
    gap: 0.6rem !important;
  }

  /* Header banner */
  .utc-header {
    background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 27, 75, 0.92) 50%, rgba(76, 29, 149, 0.88) 100%);
    color: #ffffff;
    border-radius: 16px;
    padding: 18px 24px;
    border: 1px solid rgba(139, 92, 246, 0.3);
    box-shadow: 0 8px 32px rgba(15, 23, 42, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.15);
    backdrop-filter: blur(16px);
    margin-bottom: 12px;
  }

  .utc-header .row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 12px;
  }

  .utc-header-title {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .utc-header h1 {
    margin: 0;
    font-size: 24px;
    font-weight: 800;
    letter-spacing: -0.5px;
    background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 50%, #c084fc 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .utc-header .tagline {
    margin: 3px 0 0;
    color: #cbd5e1;
    font-size: 13px;
    font-weight: 500;
  }

  .utc-badge-live {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
    box-shadow: 0 0 12px rgba(16, 185, 129, 0.25);
  }

  .utc-badge-mock {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 5px 14px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    background: rgba(245, 158, 11, 0.15);
    border: 1px solid rgba(245, 158, 11, 0.4);
    color: #fbbf24;
  }

  /* Hero Section */
  .utc-hero-title {
    text-align: center;
    font-size: 28px;
    font-weight: 800;
    margin: 8px 0 4px;
    background: linear-gradient(135deg, #ffffff 20%, #c084fc 60%, #38bdf8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }

  .utc-hero-desc {
    text-align: center;
    color: #94a3b8;
    font-size: 14.5px;
    max-width: 780px;
    margin: 0 auto 16px;
    line-height: 1.5;
  }

  /* Preset district cards */
  .utc-preset-card {
    background: linear-gradient(145deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.85) 100%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 16px;
    height: 100%;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }

  .utc-preset-card:hover {
    border-color: rgba(139, 92, 246, 0.6);
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(139, 92, 246, 0.25);
  }

  .utc-preset-top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 8px;
  }

  .utc-preset-title {
    font-size: 16px;
    font-weight: 800;
    color: #f8fafc;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .utc-preset-zip {
    font-size: 11px;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 6px;
    background: rgba(139, 92, 246, 0.2);
    border: 1px solid rgba(139, 92, 246, 0.35);
    color: #c084fc;
  }

  .utc-preset-tagline {
    font-size: 12.5px;
    color: #cbd5e1;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .utc-preset-desc {
    font-size: 11.5px;
    color: #94a3b8;
    line-height: 1.4;
    margin-bottom: 12px;
  }

  .utc-preset-badges {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 10px;
  }

  .utc-heat-chip {
    font-size: 12px;
    font-weight: 800;
    font-family: 'JetBrains Mono', monospace;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  .utc-preset-badge {
    font-size: 11px;
    font-weight: 700;
    color: #10b981;
    display: flex;
    align-items: center;
    gap: 4px;
  }

  /* Custom Area & Search Containers */
  .utc-custom-box {
    background: linear-gradient(145deg, rgba(15, 23, 42, 0.8) 0%, rgba(30, 41, 59, 0.5) 100%);
    border: 1.5px dashed rgba(139, 92, 246, 0.4);
    border-radius: 16px;
    padding: 18px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.25);
    margin-top: 14px;
  }

  .utc-note-box {
    background: rgba(15, 23, 42, 0.6);
    border-left: 3px solid #8b5cf6;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 12px;
    color: #cbd5e1;
    margin-top: 8px;
  }

  /* Inspector & Metric Cards */
  .utc-glass-card {
    background: linear-gradient(145deg, rgba(17, 24, 39, 0.85) 0%, rgba(15, 23, 42, 0.95) 100%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 16px;
    padding: 20px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    backdrop-filter: blur(12px);
  }

  .utc-sev-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    font-size: 12px;
    padding: 6px 14px;
    border-radius: 999px;
    margin-bottom: 10px;
  }

  .utc-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
    margin: 12px 0;
  }

  .utc-kpi-tile {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 12px;
    padding: 10px 12px;
  }

  .utc-kpi-tile .label {
    font-size: 11px;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 700;
    letter-spacing: 0.4px;
  }

  .utc-kpi-tile .value {
    font-size: 20px;
    font-weight: 800;
    color: #f8fafc;
    margin-top: 2px;
  }

  /* Honest Matrix Card */
  .utc-matrix-box {
    border-radius: 12px;
    background: rgba(15, 23, 42, 0.8);
    border: 1px solid rgba(139, 92, 246, 0.3);
    padding: 14px;
    margin-top: 14px;
  }

  .utc-matrix-box h4 {
    margin: 0 0 8px;
    font-size: 14px;
    font-weight: 800;
    color: #c084fc;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .utc-matrix-interv {
    font-size: 15px;
    font-weight: 800;
    color: #f8fafc;
    margin-bottom: 10px;
  }

  .utc-fact-row {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 8px 10px;
    border-radius: 8px;
    margin-top: 6px;
    font-size: 12.5px;
  }

  .utc-fact-cost {
    background: rgba(59, 130, 246, 0.12);
    border: 1px solid rgba(59, 130, 246, 0.3);
    color: #93c5fd;
  }

  .utc-fact-benefit {
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(16, 185, 129, 0.3);
    color: #6ee7b7;
  }

  .utc-fact-con {
    background: rgba(244, 63, 94, 0.12);
    border: 1px solid rgba(244, 63, 94, 0.35);
    color: #fda4af;
  }

  .utc-fact-tag {
    font-weight: 800;
    font-size: 10.5px;
    letter-spacing: 0.5px;
  }

  /* Location identifier tag */
  .utc-location-bar {
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(139, 92, 246, 0.25);
    border-radius: 10px;
    padding: 8px 12px;
    margin: 8px 0 12px;
    font-size: 13px;
    color: #e2e8f0;
  }

  /* Landmark Chip */
  .utc-landmark-chip {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(139, 92, 246, 0.18);
    border: 1px solid rgba(139, 92, 246, 0.3);
    color: #d8b4fe;
    font-size: 12px;
    font-weight: 600;
    margin-top: 4px;
  }

  /* Breadcrumbs bar */
  .utc-bread-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    flex-wrap: wrap;
    gap: 10px;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 12px;
    padding: 10px 16px;
    margin-bottom: 8px;
  }

  .utc-bread-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 15px;
    font-weight: 700;
    color: #f8fafc;
  }

  /* Severity legend chips */
  .utc-legend-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 700;
    margin-right: 8px;
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }

  /* Streamlit Button Overrides */
  .stButton > button {
    border-radius: 10px !important;
    font-weight: 700 !important;
    transition: all 0.15s ease !important;
  }

  .stButton > button:hover {
    box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3) !important;
  }
</style>
""",
        unsafe_allow_html=True,
    )


def mode_badge() -> str:
    mode = dl.mode_label()
    down = getattr(dl, "_LIVE_DOWN", False)
    is_live = not dl.running_mock() and not down
    if is_live:
        return (
            "<span class='utc-badge-live'>"
            "<span style='width:7px;height:7px;border-radius:50%;background:#10b981;'></span>"
            f"{mode}</span>"
        )
    return (
        "<span class='utc-badge-mock'>"
        "<span style='width:7px;height:7px;border-radius:50%;background:#f59e0b;'></span>"
        f"{mode}</span>"
    )


def render_header():
    st.markdown(
        f"""
        <div class='utc-header'>
          <div class='row'>
            <div>
              <div class='utc-header-title'>
                <span style='font-size:26px;'>🌡️</span>
                <h1>Urban Thermal Copilot</h1>
              </div>
              <p class='tagline'>Hyperlocal 2‑metre heat mitigation & investment planner for Phoenix OHRM</p>
            </div>
            <div style='margin-left:auto;'>{mode_badge()}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def search_form():
    """Global search bar with quick shortcut buttons."""
    with st.container():
        with st.form("place_search", clear_on_submit=False):
            c1, c2 = st.columns([5.5, 1.5], gap="small")
            place = c1.text_input(
                "Search any place or neighborhood",
                placeholder="e.g., Downtown Phoenix, Capitol Mall, Tempe, Scottsdale, Mesa...",
                label_visibility="collapsed",
            )
            go_btn = c2.form_submit_button("🔍 Analyze Place", width="stretch")
        return place, go_btn


@st.cache_data
def _preset_heat(key: str) -> float:
    """Mean ambient temperature (°C) for a preset district, cached per key."""
    grid = dl.build_preset_grid(key)
    return float(grid["temperature_c"].mean())


def _heat_color(t, tmin, tmax):
    """Smooth blue→red hex for a temperature between tmin and tmax."""
    b = (0x38, 0xB8, 0xF8)
    r = (0xF4, 0x3F, 0x5E)
    f = 0.0 if tmax <= tmin else (t - tmin) / (tmax - tmin)
    f = max(0.0, min(1.0, f))
    return "#{:02x}{:02x}{:02x}".format(
        *(round(b[0] + (r[0] - b[0]) * f),
           round(b[1] + (r[1] - b[1]) * f),
           round(b[2] + (r[2] - b[2]) * f)))


def preset_cards():
    """Clickable pre-cached district cards, each led by its real mean heat.

    The warm/cool accent on every card's top edge is drawn from the district's
    actual mean July temperature (computed once, cached), so ``which district is
    hottest`` is readable before you click -- grounding the cards in the data
    rather than decoration.
    """
    temps = {p["key"]: _preset_heat(p["key"]) for p in dl.PRESETS}
    tmin, tmax = min(temps.values()), max(temps.values())

    cols = st.columns(len(dl.PRESETS), gap="small")
    chosen = None
    for col, p in zip(cols, dl.PRESETS):
        with col:
            mean_c = temps[p["key"]]
            edge = _heat_color(mean_c, tmin, tmax)
            icon = p.get("icon", "📍")
            tagline = p.get("tagline", "High-priority urban sector")
            desc = p.get("description", "Pre-computed 2-metre thermal snapshot.")
            st.markdown(
                f"""
                <div class='utc-preset-card' style='border-top:4px solid {edge};'>
                  <div>
                    <div class='utc-preset-top'>
                      <div class='utc-preset-title'><span>{icon}</span> {p['label']}</div>
                      <div class='utc-preset-zip'>ZIP {p['zip']}</div>
                    </div>
                    <div class='utc-preset-tagline'>{tagline}</div>
                    <div class='utc-preset-desc'>{desc}</div>
                  </div>
                  <div class='utc-preset-badges'>
                    <span class='utc-heat-chip' style='color:{edge};'>Ø {mean_c:.1f}°C</span>
                    <span class='utc-preset-badge'>⚡ Instant</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Explore {p['label']} ➔", key=f"preset_{p['key']}", width="stretch"):
                chosen = p["key"]
    return chosen


def _overview_hero_map():
    """Interactive overview map showing Phoenix presets, civic landmarks, and custom draw rectangle."""
    import folium
    from folium import plugins as fplugins
    from streamlit_folium import st_folium

    m = folium.Map(location=[33.4560, -112.0780], zoom_start=13, control_scale=True, tiles=None)

    # Clean OpenStreetMap base
    folium.TileLayer(
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        name="🗺️ OpenStreetMap (Detailed Streets)",
        attr="&copy; OpenStreetMap contributors",
        max_zoom=19,
    ).add_to(m)

    folium.TileLayer(
        tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
        name="🛰️ Esri Satellite (Ground Imagery)",
        attr="&copy; Esri, Maxar",
        max_zoom=19,
    ).add_to(m)

    fplugins.LocateControl(
        auto_start=False,
        flyTo=True,
        keepCurrentZoomLevel=False,
        drawCircle=True,
        position="topleft",
        strings={"title": "🎯 Locate My GPS Position"},
    ).add_to(m)

    fplugins.Fullscreen(position="topleft").add_to(m)

    # Preset District Polygons & Markers
    preset_colors = {
        "downtown_core": "#8b5cf6",
        "capitol_district": "#ec4899",
        "midtown_phoenix": "#06b6d4",
        "van_buren_corridor": "#f59e0b",
    }

    # Add preset district highlight areas
    for p in dl.PRESETS:
        lat, lon = float(p["lat"]), float(p["lon"])
        color = preset_colors.get(p["key"], "#8b5cf6")
        icon = p.get("icon", "📍")

        # Bounding box approximate area for the preset
        delta_lat, delta_lon = 0.009, 0.012
        bounds = [[lat - delta_lat, lon - delta_lon], [lat + delta_lat, lon + delta_lon]]
        folium.Rectangle(
            bounds=bounds,
            color=color,
            weight=2,
            fill=True,
            fill_color=color,
            fill_opacity=0.18,
            popup=f"<b>{p['label']}</b> (ZIP {p['zip']})<br/>{p.get('tagline', '')}",
            tooltip=f"{icon} {p['label']} (ZIP {p['zip']})",
        ).add_to(m)

        badge_html = f"""
        <div style="background:{color}; color:#fff; font-weight:800; font-size:11px;
                    padding:3px 8px; border-radius:999px; box-shadow:0 2px 8px rgba(0,0,0,0.4);
                    border:1.5px solid #fff; white-space:nowrap; cursor:pointer;">
            {icon} {p['label']}
        </div>
        """
        folium.Marker(
            [lat, lon],
            icon=folium.DivIcon(html=badge_html, icon_size=(130, 24), icon_anchor=(65, 12)),
            tooltip=f"Preset Zone: {p['label']} (ZIP {p['zip']})",
        ).add_to(m)

    # Add Civic Landmarks
    if hasattr(dl, "CIVIC_LANDMARKS"):
        for lm in dl.CIVIC_LANDMARKS:
            pin_html = f"""
            <div style="display:flex; align-items:center; justify-content:center;
                        width:28px; height:28px; border-radius:50%;
                        background:#0f172a; border:1.5px solid #8b5cf6;
                        box-shadow:0 2px 6px rgba(0,0,0,0.5); font-size:14px;"
                 title="{lm['name']}">
                {lm['icon']}
            </div>
            """
            folium.Marker(
                [float(lm["lat"]), float(lm["lon"])],
                icon=folium.DivIcon(html=pin_html, icon_size=(28, 28), icon_anchor=(14, 14)),
                tooltip=f"<b>{lm['icon']} {lm['name']}</b><br/><span style='color:#7c3aed;'>{lm['district']}</span>",
            ).add_to(m)

    # Rectangle draw plugin for custom area
    fplugins.Draw(
        export=False,
        position="topleft",
        draw_options={
            "rectangle": True,
            "polyline": False,
            "polygon": False,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": False, "remove": False},
    ).add_to(m)

    folium.LayerControl(collapsed=True, position="topright").add_to(m)

    out = st_folium(m, key="hero_overview_map", height=480, width="100%")
    drawing = (out or {}).get("last_active_drawing") or {}
    coords = (((drawing.get("geometry") or {}).get("coordinates") or [[]])[0])
    if len(coords) >= 3:
        lons = [c[0] for c in coords]
        lats = [c[1] for c in coords]
        return min(lats), min(lons), max(lats), max(lons)
    return None


def custom_area_box():
    """Interactive custom draw area box with landmark map preview."""
    st.markdown("<div class='utc-custom-box'>", unsafe_allow_html=True)
    st.markdown(
        f"**✏️ Interactive Map & Custom Area** — Draw a rectangle below to analyze any custom boundary "
        f"({dl.CUSTOM_AREA_WAIT_LABEL}), or locate landmarks and preset zones on the map."
    )
    st.markdown(
        "<div class='utc-note-box'>💡 <b>Spatial Orientation:</b> The map markers highlight key Phoenix civic landmarks "
        "(State Capitol, City Hall, Stadiums, Hospitals). You can also click the <b>Locate Me 🎯</b> button to pinpoint your location.</div>",
        unsafe_allow_html=True,
    )
    bounds = _overview_hero_map()
    st.markdown("</div>", unsafe_allow_html=True)
    if bounds and st.button("🚀 Analyze Selected Custom Area", type="primary"):
        return bounds
    return None


def build_grid_for(place: str):
    """Geocode + build the contract grid for a searched place."""
    with st.status(f"Generating 2-metre heat map for '{place}'…", expanded=True) as s:
        st.write("Fetching FortyGuard thermal model snapshot…")
        grid = dl.build_grid_for_place(place)
        st.write("Computing vulnerability & spatial priority scores…")
        s.update(label=f"Done! Loaded heat map for {place}", state="complete")
    _prime_session(grid)


def build_grid_for_bounds(bounds):
    """Build the grid for a drawn custom box."""
    south, west, north, east = bounds
    area_km2 = (north - south) * 111.0 * (east - west) * 111.0 * 0.85
    if area_km2 > dl.CUSTOM_AREA_LIMIT_KM2:
        st.warning(
            f"That box is ~{area_km2:.1f} km². Please keep it under ~2 sq mi ({dl.CUSTOM_AREA_LIMIT_KM2:.0f} km²) for a fast demo."
        )
        return
    with st.status("Analyzing your custom bounding area…", expanded=True) as s:
        st.write("Fetching 2-metre thermal snapshot…")
        lat_c, lon_c = (south + north) / 2, (west + east) / 2
        grid = dl.build_grid_for_center(lat_c, lon_c, "Custom Boundary")
        st.write("Computing vulnerability index and recommendations…")
        s.update(label="Analysis complete!", state="complete")
    _prime_session(grid)
    grid.attrs["is_custom"] = True


def _prime_session(grid):
    """Store grid + precomputed recommendations so clicks resolve instantly."""
    st.session_state["grid"] = grid
    st.session_state["recs"] = f3.recommendation_map(grid, surface_hint=None)
    st.session_state["place"] = grid.attrs.get("city") or "Selected area"
    st.session_state["selected"] = None


def hero():
    render_header()
    st.markdown("<div class='utc-hero-title'>Find the zones that need cooling first</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='utc-hero-desc'>Select a pre-computed district to inspect its 2-metre heat map instantly, "
        "or search any location. Every cooling recommendation includes real cost, real benefit, and its <b>mandatory trade-off (con)</b>.</div>",
        unsafe_allow_html=True,
    )

    chosen = preset_cards()
    if chosen:
        with st.spinner("Loading pre-computed district…"):
            grid = dl.build_preset_grid(chosen)
        _prime_session(grid)
        st.rerun()

    st.markdown("<h4 style='color:#f8fafc; margin-top:20px; margin-bottom:8px;'>📍 Search Any Location or Draw Custom Box</h4>", unsafe_allow_html=True)
    place, go = search_form()
    if go and place:
        build_grid_for(place)
        st.rerun()

    bounds = custom_area_box()
    if bounds:
        build_grid_for_bounds(bounds)
        st.rerun()


def severity_counts(grid):
    import collections

    counts = collections.Counter(f1.classify_priority(float(p))[0] for p in grid["priority_score"])
    return {k: counts.get(k, 0) for k in ("terrible", "bad", "fair", "good")}


def render_inspector(grid, recs, cell_id):
    st.markdown("<div class='utc-glass-card'>", unsafe_allow_html=True)
    st.markdown("<h3 style='margin:0 0 10px; font-size:18px; color:#f8fafc;'>🔎 Zone Inspector & Honest Matrix</h3>", unsafe_allow_html=True)

    if not cell_id:
        st.markdown(
            "<div style='color:#94a3b8; font-size:13.5px; padding:20px 0; text-align:center;'>"
            "👆 <b>Click any 2-metre grid cell</b> on the map to inspect its microclimate metrics, "
            "nearby landmarks, and tailored cooling plan."
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    row = grid[grid["cell_id"] == cell_id]
    if row.empty:
        st.markdown("</div>", unsafe_allow_html=True)
        return
    r = row.iloc[0]

    # Human-readable location & landmark calculation
    centroid = r.geometry.centroid
    import geopandas as _gpd

    pt = _gpd.GeoSeries([centroid], crs=grid.crs).to_crs("EPSG:4326").iloc[0]
    lat_val, lon_val = float(pt.y), float(pt.x)
    loc_label = dl.reverse_geocode(lat_val, lon_val) or f"Zone `{cell_id}`"
    nearby_lm = dl.get_nearest_landmark(lat_val, lon_val)

    level, color = f1.classify_priority(float(r["priority_score"]))
    prio_txt = f1.priority_label(float(r["priority_score"]))

    st.markdown(
        f"<span class='utc-sev-pill' style='background:{color}25; color:{color}; border:1px solid {color}55;'>"
        f"<span style='width:8px;height:8px;border-radius:50%;background:{color};'></span>"
        f"{level.upper()} RISK · Priority: {prio_txt}</span>",
        unsafe_allow_html=True,
    )

    # Location Information Card
    lm_html = (
        f"<div class='utc-landmark-chip'>{nearby_lm['label']}</div>"
        if nearby_lm
        else ""
    )
    st.markdown(
        f"""
        <div class='utc-location-bar'>
          <div style='font-weight:700; color:#f8fafc;'>📍 {loc_label}</div>
          <div style='font-size:11.5px; color:#94a3b8; margin-top:2px;'>
            {st.session_state.get('place', '')} · <span class='font-mono'>{lat_val:.4f}°N, {abs(lon_val):.4f}°W</span>
          </div>
          {lm_html}
        </div>
        """,
        unsafe_allow_html=True,
    )

    # KPIs
    st.markdown(
        f"""
        <div class='utc-kpi-grid'>
          <div class='utc-kpi-tile'>
            <div class='label'>Ambient Temp</div>
            <div class='value'>{float(r['temperature_c']):.1f} °C</div>
          </div>
          <div class='utc-kpi-tile'>
            <div class='label'>Heat Index</div>
            <div class='value'>{float(r['heat_index_c']):.1f} °C</div>
          </div>
          <div class='utc-kpi-tile'>
            <div class='label'>Exceedance (>50°C)</div>
            <div class='value'>{float(r.get('exceedance_hours', 0) or 0):.1f} h</div>
          </div>
          <div class='utc-kpi-tile'>
            <div class='label'>Persistence (>47°C)</div>
            <div class='value'>{float(r.get('persistence_hours', 0) or 0):.1f} h</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    vuln = float(r["vulnerability_score"])
    prio = float(r["priority_score"])
    st.caption(f"Vulnerability Index: **{vuln:.2f}** · Composite Priority Score: **{prio:.2f}**")

    # Honest-Matrix recommendation
    rec = (recs or {}).get(cell_id)
    if rec:
        st.markdown(
            f"""
            <div class='utc-matrix-box'>
              <h4>✅ Recommended Action — Honest Matrix</h4>
              <div class='utc-matrix-interv'>{rec['intervention']}</div>
              <div class='utc-fact-row utc-fact-cost'>
                <span class='utc-fact-tag'>💰 ESTIMATED COST</span>
                <span>{rec['cost_range']}</span>
              </div>
              <div class='utc-fact-row utc-fact-benefit'>
                <span class='utc-fact-tag'>✨ COOLING BENEFIT</span>
                <span>{rec['benefit']}</span>
              </div>
              <div class='utc-fact-row utc-fact-con'>
                <span class='utc-fact-tag'>⚠️ MANDATORY CON (TRADE-OFF)</span>
                <span>{rec['con']}</span>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("No recommendation mapped for this zone.")

    st.markdown("</div>", unsafe_allow_html=True)


def st_folium_map(grid, show_vulnerability=False, show_landmarks=True):
    from streamlit_folium import st_folium

    center = grid.attrs.get("center")
    pois = grid.attrs.get("pois") if show_vulnerability else None
    center_name = st.session_state.get("place")
    return st_folium(
        f1.render_explorer_map(
            grid,
            center=center,
            show_vulnerability=show_vulnerability,
            pois=pois,
            show_landmarks=show_landmarks,
            center_name=center_name,
        ),
        key="explorer_map",
        height=780,
        width="100%",
    )


def render_dashboard(grid):
    render_header()

    # Breadcrumbs and Quick District Switcher Bar
    st.markdown(
        f"""
        <div class='utc-bread-bar'>
          <div class='utc-bread-title'>
            <span>📍 Active Area:</span>
            <span style='color:#c084fc;'>{st.session_state.get('place', 'Phoenix, AZ')}</span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    top_c1, top_c2, top_c3, top_c4, top_c5 = st.columns([1.5, 1.5, 1.5, 1.5, 1.5], gap="small")
    for col, p in zip((top_c1, top_c2, top_c3, top_c4), dl.PRESETS):
        with col:
            if st.button(f"{p.get('icon', '📍')} {p['label']}", key=f"dash_preset_{p['key']}", width="stretch"):
                with st.spinner(f"Loading {p['label']}…"):
                    new_grid = dl.build_preset_grid(p["key"])
                _prime_session(new_grid)
                st.rerun()

    with top_c5:
        if st.button("🔄 Reset / Home", width="stretch", type="secondary"):
            st.session_state["grid"] = None
            st.session_state["selected"] = None
            st.rerun()

    place, go = search_form()
    if go and place:
        build_grid_for(place)
        st.rerun()

    counts = severity_counts(grid)

    # Controls Row
    ctrl1, ctrl2, ctrl3 = st.columns([2.5, 2.5, 5], gap="small")
    with ctrl1:
        show_vuln = st.checkbox(
            "⚠️ Show Vulnerability (POIs & Priority)",
            value=False,
            help="Displays schools, transit, and hospitals with bold high-priority cell borders.",
        )
    with ctrl2:
        show_lm = st.checkbox(
            "🏛️ Show Civic Landmarks & Districts",
            value=True,
            help="Pins major civic landmarks (City Hall, State Capitol, Stadiums, Parks) to orient where you are.",
        )
    with ctrl3:
        legend_html = "<div style='display:flex; align-items:center; justify-content:flex-end; flex-wrap:wrap; gap:4px; padding-top:4px;'>" + "".join(
            f"<span class='utc-legend-chip'>"
            f"<span style='width:10px;height:10px;border-radius:3px;background:{color}'></span>"
            f"{level.capitalize()} ({counts.get(level,0)})</span>"
            for level, color in (("terrible", "#b5179e"), ("bad", "#e85d04"), ("fair", "#f2b705"), ("good", "#2a9d8f"))
        ) + "</div>"
        st.markdown(legend_html, unsafe_allow_html=True)

    # Main Grid Layout: Map (Left) + Inspector (Right)
    col_map, col_insp = st.columns([0.64, 0.36], gap="medium")
    with col_map:
        map_data = st_folium_map(grid, show_vulnerability=show_vuln, show_landmarks=show_lm)
        st.caption("🗺️ **Tip:** Click any square cell to inspect it. Use the layer switcher (top right) to toggle Satellite Imagery or POIs. Click 🎯 (top left) to locate your GPS.")

        clicked = map_data.get("last_object_clicked") or {}
        cell_id = clicked.get("cell_id")
        if cell_id:
            st.session_state["selected"] = cell_id

    with col_insp:
        render_inspector(grid, st.session_state.get("recs"), st.session_state.get("selected"))

    render_insights(grid, counts)


def render_insights(grid, counts):
    st.markdown("---")
    st.markdown("<h3 style='color:#f8fafc; margin-top:10px;'>📊 City Heat Analytics & Planning Toolkit</h3>", unsafe_allow_html=True)
    t1, t2, t3, t4 = st.tabs(["📈 Multi‑Year Trend (2021–2025)", "💰 Budget Roadmap & Allocation", "📑 Executive Memo", "🛡️ Risk Flags & Mortality"])

    with t1:
        pairs = dl.load_trend()
        idx = [y for y, _ in pairs]
        vals = [m for _, m in pairs]
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=idx,
                y=vals,
                mode="lines+markers",
                line=dict(width=3.5, color="#8b5cf6"),
                marker=dict(size=8, color="#c084fc", line=dict(width=2, color="#ffffff")),
                name="July Mean °C",
                fill="tozeroy",
                fillcolor="rgba(139, 92, 246, 0.15)",
            )
        )

        if len(vals) >= 2:
            delta = f7.delta_c(pairs)
            import numpy as _np

            slope = float(_np.polyfit(idx, vals, 1)[0])
            xs = [idx[0], idx[-1]]
            ys = [vals[0], vals[-1]]
            fig.add_trace(
                go.Scatter(
                    x=xs,
                    y=ys,
                    mode="lines",
                    line=dict(width=2, dash="dash", color="#f43f5e"),
                    name=f"Trend {slope:+.2f} °C/yr",
                    opacity=0.85,
                )
            )
            fig.add_annotation(
                x=idx[-1],
                y=vals[-1],
                text=f"<b>{delta:+.2f} °C warming ({slope:+.2f} °C/yr)</b>",
                showarrow=True,
                arrowhead=2,
                bgcolor="#1e1b4b",
                bordercolor="#8b5cf6",
                font=dict(color="#ffffff", size=12),
            )

        fig.update_layout(
            title="Phoenix July Mean Ambient Temperature (°C) 2021–2025",
            template="plotly_dark",
            paper_bgcolor="rgba(15,23,42,0.6)",
            plot_bgcolor="rgba(15,23,42,0.4)",
            xaxis_title="Year",
            yaxis_title="Ambient Temperature (°C)",
            height=360,
            margin=dict(l=10, r=10, t=50, b=10),
            font=dict(family="Plus Jakarta Sans", color="#cbd5e1"),
        )
        st.plotly_chart(fig, width="stretch")
        st.metric("Total Warming Across Window (2021–2025)", f"{f7.delta_c(pairs):+.2f} °C")

    with t2:
        c1, c2 = st.columns(2, gap="small")
        budget = c1.number_input(
            "Budget Allocation (USD)",
            min_value=50_000,
            max_value=500_000_000,
            value=int(f4.DEFAULT_BUDGET_USD),
            step=100_000,
            help="Pre-filled with Phoenix OHRM's real FY2026 $8.9M allocation as an illustrative cooling capital slice.",
        )
        years = c2.number_input(
            "Investment Horizon (Years)", min_value=1, max_value=10, value=f4.DEFAULT_YEARS, step=1
        )
        phases, used, skipped = f4.build_phases(grid, budget=float(budget), years=int(years))

        st.markdown(
            f"**Priority‑ordered spend strategy**: **{used} zones funded** · **{skipped} waiting for future capital**."
        )

        if phases:
            import plotly.graph_objects as go

            chart = [{"Phase": p["phase_number"], "Years": p["years"], "Spend": p["phase_budget_used"]} for p in phases]
            fig = go.Figure(
                go.Bar(
                    x=[f"Phase {c['Phase']} ({c['Years']})" for c in chart],
                    y=[c["Spend"] for c in chart],
                    marker=dict(
                        color=["#8b5cf6", "#a78bfa", "#c4b5fd"][: len(chart)],
                        line=dict(color="#ffffff", width=1),
                    ),
                )
            )
            fig.update_layout(
                title="Capital Expenditure by Phase ($ USD)",
                template="plotly_dark",
                paper_bgcolor="rgba(15,23,42,0.6)",
                plot_bgcolor="rgba(15,23,42,0.4)",
                xaxis_title="Phase & Timeline",
                yaxis_title="Phase Spend ($)",
                height=320,
                margin=dict(l=10, r=10, t=50, b=10),
                font=dict(family="Plus Jakarta Sans", color="#cbd5e1"),
            )
            st.plotly_chart(fig, width="stretch")
            with st.expander("🔍 Why this allocation order? (Transparent scoring breakdown)"):
                st.markdown(f4.how_prioritized_text(phases, grid))

    with t3:
        phases, _, _ = f4.build_phases(grid)
        trend_pairs = dl.load_trend()
        ctx = f6.build_plan_context(
            grid, phases, trend_pairs, dl.mode_label(), area_name=st.session_state.get("place", "")
        )
        st.markdown(
            "<div style='font-size:13px; color:#94a3b8; margin-bottom:12px;'>"
            "Prepares a municipal briefing memo for city leadership, synthesizing "
            "this area's thermal data, vulnerability scores, and Honest Matrix "
            "trade-offs into a single short read. This is the one live external "
            "step in the app; without a key it uses the same numbers in a "
            "deterministic template.</div>",
            unsafe_allow_html=True,
        )
        if st.button("📝 Generate memo", type="primary"):
            with st.spinner("Synthesizing executive briefing…"):
                st.session_state["report"] = f6.generate_report(ctx)

        report_text = st.session_state.get("report") or f6._template_report(ctx)
        st.markdown(
            f"<div style='background:rgba(15,23,42,0.7); border:1px solid rgba(139,92,246,0.3); border-radius:12px; padding:20px;'>{report_text}</div>",
            unsafe_allow_html=True,
        )
        st.download_button(
            "⬇️ Download Executive Briefing Memo (.md)",
            report_text,
            file_name="phoenix-urban-thermal-briefing.md",
            mime="text/markdown",
        )

    with t4:
        st.markdown("#### 🛡️ FortyGuard Native Risk Analytics & Public Heat-Death Correlation")
        rc1, rc2 = st.columns(2, gap="medium")
        with rc1:
            flags = dl.load_risk_flags()
            st.markdown(f5.render_markdown(flags))
        with rc2:
            deaths_df = dl.load_maricopa_deaths()
            st.markdown(f8.render_correlation(grid, deaths_df))


def main():
    inject_css()
    grid = st.session_state.get("grid")
    if grid is None:
        hero()
    else:
        render_dashboard(grid)


if __name__ == "__main__":
    main()