# Urban Thermal Copilot 🌡️

**Urban Thermal Copilot** turns FortyGuard's hyperlocal (2-metre) temperature data
into a **budget-constrained cooling investment plan** that a city planning office
can actually defend. It is an interactive Streamlit web app — pick a district,
click a hot square, and get that zone's heat data plus a concrete cooling
recommendation with a real cost, a real benefit, and an honest trade-off.

Built for the **FortyGuard Hackathon '26**. Demo city: **downtown Phoenix, AZ**
(ZIP codes 85004 + 85007). The named "client" is the Phoenix **Office of Heat
Response and Mitigation (OHRM)** — the agency that actually buys this kind of
work, with a real FY2026 heat budget of $8.9M.

---

## 🤔 Why it was made

Extreme heat is the deadliest weather hazard in the US, and Maricopa County
(includes Phoenix) reports hundreds of heat-associated deaths per year. Cities
have money and interventions — cool pavement, shade, trees — but no clear,
defensible answer to *"which block, which intervention, at what cost, and what
trade-off are we accepting?"*

Urban Thermal Copilot answers that question in three clicks, built on two
principles:

1. **Every recommendation shows a real cost, a real benefit, and a mandatory
   trade-off ("con")** — the con is never omitted. That honesty is what a public
   agency can defend to a council. It is enforced by a test
   (`assert_every_con_present`) that fails the build if any recommendation ships
   without its trade-off.
2. **Nothing is a black box** — the scoring formulas are documented in the app
   and in this README, and every data source (live API vs. offline sample) is
   clearly labeled in the UI.

---

## ✨ What you get

### Landing page
- **Preset district cards** (Downtown Core, Capitol District, Midtown Phoenix,
  Van Buren Corridor) — load instantly, no API call needed.
- **Search any location**, or **draw a custom box** on the landmark map
  (capped at ~2 sq mi / 5.2 km² — a fresh analysis *usually takes under a
  minute*).

### The dashboard
- **Interactive heat map** — color-blind-safe (viridis) 2-metre thermal grid,
  auto-framed to the selected area, with OpenStreetMap and Esri Satellite base
  layers, GPS locate, and an in-map geocoder.
- **Zone Inspector** — click any colored square to see that zone's ambient temp,
  heat index, >50 °C exceedance hours, vulnerability index, nearest landmark,
  and its **Honest Matrix** recommendation (cost / benefit / con).
- **Severity chips** — click 🔴 Terrible / 🟠 Bad / 🟡 Fair / 🟢 Good to highlight
  only those zones on the map; click again to clear.
- **Overlay toggles** — vulnerability layer (schools, transit, hospitals,
  elderly care with priority borders) and civic landmark pins.

### City Heat Analytics & Planning Toolkit (below the map)
| Tab | What you get |
|-----|--------------|
| **📈 Multi-Year Trend (2021–2025)** | July mean temperature per year for the selected area — is it getting hotter? |
| **💰 Budget Roadmap & Allocation** | Enter a budget + horizon (pre-filled as a slice of OHRM's real $8.9M) → a transparent Phase 1/2/3 spend plan with a "Why this order?" explainer showing the actual scores. |
| **📑 Executive Memo** | A narrative briefing for OHRM (AI-generated when a `GEMINI_API_KEY` is present; a solid template otherwise). |
| **🛡️ Risk Flags & Mortality** | FortyGuard-native exceedance/persistence analytics (50 °C threshold) next to Maricopa County's public heat-death reporting. |

---

## 🚀 How to run it (2 minutes)

**1. Clone and enter the repo.**
```bash
git clone git@github.com:AdventBird/Urban-Thermal-Copilot-FortyGuard-Hackathon-.git
cd Urban-Thermal-Copilot-FortyGuard-Hackathon-
```

**2. Create a virtual environment and install dependencies (Python 3.11+).**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. (Optional) Add API keys.**
```bash
cp .env.example .env
```
Then paste your keys into `.env`:
- `FORTYGUARD_API_KEY` — live 2-metre heat data.
- `GEMINI_API_KEY` — AI-generated executive memo (optional; a template memo is
  used otherwise). The memo uses **Gemini 3.5 Flash Lite** by default; override
  with `GEMINI_MODEL=<model-name>` (see `.env.example`).

> **No keys? The app still runs fully.** Without a FortyGuard key it runs in
> **offline/demo mode** on representative fixtures in `data/fixtures/` — the
> whole product works end-to-end, and the UI clearly labels which mode is
> active (it downgrades itself to "cached" the first time a live call fails).

**4. Launch.**
```bash
streamlit run app/main.py
```
Then open `http://localhost:8501`.

---

## 🖱️ How to use it (first 60 seconds)

1. Click a **preset district card** — the heat map loads instantly.
2. **Click any colored square** — the Zone Inspector on the right fills with
   that zone's metrics and its cooling recommendation.
3. Click a **severity chip** above the map (e.g. 🟠 Bad) to highlight only the
   worst zones; click it again to clear.
4. Flip the **Vulnerability overlay** toggle to see schools, transit and
   hospitals against high-priority cells.
5. Scroll to the **🧰 Analytics Toolkit**: set a budget in the **Budget Roadmap**,
   read the **Executive Memo**, and check **Risk Flags & Mortality**.
6. Feeling adventurous? Back on the landing page, **draw a custom box** around
   your own neighborhood — a live FortyGuard analysis takes *usually under a
   minute*.

---

## 🧠 How the scoring works (transparent, not a black box)

Per grid cell:

```
vulnerability_score = 0.5 × POI exposure + 0.5 × demographic sensitivity
     POI exposure            = min-max over { 0.5×proximity + 0.5×density }
                               to schools / transit / hospitals / elder care
     demographic sensitivity = min-max over { 0.5×% elderly + 0.5×% low income }

priority_score     = heat_index_normalized × vulnerability_score
```

The Budget Roadmap spends the budget on the highest `priority_score` cells
first, at `$50,000 / cell`, batching them into Phase 1 / 2 / 3. This is a
**planning heuristic**, not an engineering guarantee — and the UI says so.

Severity classes come from `priority_score`: Terrible / Bad / Fair / Good.

---

## 📁 Project layout

```
app/main.py          Streamlit entrypoint — landing page, dashboard, toolkit
features/            one module per feature + data_layer.py (live/mock assembly)
utc/                 shared business logic: FortyGuard client, thermal + scoring
                     modules, bbox helpers, config
data/fixtures/       offline sample data (heat map, OSM POIs, Census, trend,
                     risk flags, Maricopa heat deaths)
data/cache/          runtime JSON cache (gitignored, created on demand)
tests/               focused pytest suite (75 passing, 1 skipped)
requirements.txt, .env.example, README.md
```

### Live vs offline data handling
- **With a real `FORTYGUARD_API_KEY`:** the app calls the documented async
  endpoints (submit → poll `/v1/status/{id}` with 3s→6s→12s backoff; credits
  are charged only on completion) and caches every result to `data/cache/` as
  local JSON, so re-runs work offline.
- **Without a key:** fixture JSON is used instead, clearly flagged in the UI.
- Every external call (FortyGuard, OSM, Census) has a cache/fallback, so an
  offline demo never breaks.
- The monthly trend uses the API's month-range query (`filter_type=4`,
  2021+); per-area live grids are downsampled to ~80 cells for the UI.

---

## ✅ Running the tests

```bash
python -m pytest -q
```
Covers the data layer, thermal scoring, risk flags, correlation, roadmap,
report, and the UI regression fixes (grid extent, map fit-bounds, click-to-zone
resolution, severity filter).

---

## 🔐 Security & honesty notes

- API keys are read from the environment / `.env` only — never committed
  (`.env` is gitignored; `.env.example` documents the shape).
- Census figures, Maricopa death counts, and intervention costs are
  **representative/illustrative** where they are not freshly sourced public
  data — swap in current municipal numbers before a public demo.
- Preset districts are square analysis areas around real Phoenix centers (not
  exact ZIP boundaries); custom areas are capped at ~5.2 km² to keep live
  builds fast (the API's own AOI cap is ~130 km²).
- Heat data range is 2021-01-01 → present.

---

## 🧭 Credits

Built with [FortyGuard](https://fortyguard.com)'s 2-metre urban temperature API
for the FortyGuard Hackathon '26. Data also from OpenStreetMap and the US
Census. Made for the Phoenix Office of Heat Response and Mitigation.
