# Urban Thermal Copilot 🌡️

Turn FortyGuard's hyperlocal (2‑metre) temperature data into a **budget‑constrained,
multi‑year cooling investment plan** for a city planning office.

Built for the **FortyGuard Hackathon '26 — Track 4 (Government & Environment)**.
Demo city: **downtown Phoenix, AZ** (ZIP codes 85004 + 85007). Named client: the
Phoenix **Office of Heat Response and Mitigation (OHRM)**.

> **The one idea that matters:** every recommendation shows a real **cost**, a real
> **benefit**, and a real **trade‑off ("con")** — the con is never omitted. This
> honesty is what a public agency can defend to a council.

---

## ✨ What it does

A Streamlit web app with one tab per feature. Open the repo, run one command, and
get a full cooling‑investment plan for Phoenix:

| Tab | What you get |
|-----|--------------|
| **Overview** | Business‑case framing, headline heat/vulnerability metrics, and a live map. |
| **1 · Heat Map** | A color‑blind‑safe (viridis) Folium map of the 2‑metre thermal snapshot, plus the hottest cells. |
| **2 · Vulnerability** | Who is at risk: schools/transit/hospitals + Census demographics blended into a documented 0–1 vulnerability and priority score per cell. |
| **3 · Honest Matrix** | Top‑priority zones matched to curated interventions, each with cost, benefit **and** a real con. |
| **4 · Budget Roadmap** | Enter a budget + multi‑year horizon (pre‑filled from OHRM's real FY2026 $8.9M as a hypothetical slice) → a transparent greedy Phase 1/2/3 spend plan. |
| **5 · Risk Flags** | FortyGuard‑native `exceedance` / `persistence` analytics (threshold 50 °C, direction above). |
| **6 · AI Report** | A narrative executive summary generated server‑side by the **Gemini API**, framed for OHRM with the trade‑offs included. |
| **7 · Multi‑year Trend** | July mean temperature 2021–2025 (one FortyGuard "single month" call per year). |
| **8 · Heat vs Death** | Compares grid heat to Maricopa County public heat‑death reporting for the same ZIPs (Pearson r). |
| **9 · Business Case** | The buyer (OHRM) and the real $8.9M budget line. |
| **10 · Satellite Heat‑lens (bonus)** | Per‑tile surface heat‑lens score from satellite segmentation (the premium endpoint), feeding the Honest Matrix. |

### The honest‑matrix rule (no exceptions)
Every recommendation produced anywhere in the app — matrix, roadmap, or report —
always includes a **`con`**. There is a test (`assert_every_con_present`) that
fails the build if any recommendation is shipped without its trade‑off.

---

## 🚀 Quick start (2 minutes)

**1. Clone / open the repo.**
```bash
git clone <this-repo-url>
cd Urban-Thermal-Copilot-FortyGuard-Hackathon-
```

**2. Create a virtual environment and install dependencies (Python 3.11+).**
```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

**3. (Optional) Add your API keys.**
```bash
cp .env.example .env
```
Then open `.env` and paste your keys:
- `FORTYGUARD_API_KEY` — live 2‑metre heat data.
- `GEMINI_API_KEY` — live AI report (Feature 6) via the Gemini API.

> **No keys? The app still runs fully.** Without keys it runs in **mock/cached
> mode** using representative fixtures in `data/fixtures/`, so you can demo the
> whole product end‑to‑end offline. The sidebar shows a banner telling you which
> mode you're in.

**4. Launch the app.**
```bash
streamlit run app/main.py
```
Your browser opens at `http://localhost:8501`.

**5. What to click first.**
- On the landing page, click a **preset area card** (e.g. *Downtown Core — 85004*) —
  it loads instantly from pre-computed data.
- Or draw a box under **Custom area** — this analyzes fresh and takes 1–3 minutes.
- On the map, toggle **Show Vulnerability** to reveal POIs and priority zones, then
  click any zone for its **Honest Matrix** (cost / benefit / **con**).
- Open **Budget roadmap** and set your budget — it re-prioritizes instantly;
  see the "Why this order?" expander for the actual scores.
- Land on the **AI report** tab and press **Generate report**.

**6. Run the test suite.**
```bash
python -m pytest -q
```

---

## 🧠 How the scoring works (transparent, not a black box)

Per grid cell (after Features 1 + 2):

```
vulnerability_score = 0.5 × POI exposure + 0.5 × demographic sensitivity
     POI exposure        = min-max over { 0.5×proximity + 0.5×density }
                           to schools / transit / hospitals / elder care
     demographic sensitivity = min-max over { 0.5×% elderly + 0.5×% low income }

priority_score     = heat_index_normalized × vulnerability_score
```

The roadmap spends the budget on the highest `priority_score` cells first, at
`$50,000 / cell`, batching them into Phase 1 / 2 / 3. This is a **heuristic** for
planning, not an engineering guarantee — the UI says so.

---

## 📁 Project layout

```
app/               main.py            → Streamlit entrypoint (all tabs)
features/          feature1..feature10 → one module per feature + data_layer.py
utc/               shared business logic (bbox, contracts, fortyguard_client,
                   feature1_thermal, feature2_vulnerability, feature4_roadmap, ...)
data/cache/        runtime JSON cache (gitignored, created on demand)
data/fixtures/     offline sample data (heat map, OSM POIs, Census, trend,
                   satellite, risk flags, Maricopa deaths)
tests/             one test file per feature (incl. hand-calculated score asserts)
requirements.txt, .env.example, README.md
```

### How the app handles "live vs offline"
- With a real `FORTYGUARD_API_KEY`: the app calls the documented async endpoints
  (submit → poll `/v1/status/{id}` with 3s→6s→12s backoff, credits only on
  `Completed`) and caches every result to `data/cache/` as local JSON.
- Without a key: it loads the fixture JSON instead, clearly flagged in the UI.
- Every external call (FortyGuard, OSM, Census, satellite) has a JSON cache
  fallback, so a rerun — or an offline demo during judging — still works.

---

## ✅ Security & honesty notes

- Keys are read from the environment / `.env` only — never committed (see
  `.gitignore`). `.env` is gitignored.
- Census figures, Maricopa death counts, intervention costs and the satellite
  classes are **representative/illustrative** and clearly labeled where they are
  not freshly sourced public data — swap in the latest census/municipal numbers
  before a public demo.
- The satellite model can return an **implausible `ship` class** for landlocked
  Phoenix; the app **excludes and logs** such classes rather than averaging them in.

---

## 🧭 Need to know
- Data range is 2021‑01‑01 → present (+12 h forecast for heat maps only).
- The demo area is ~< 130 km² (under FortyGuard's AOI cap).
- Wants tests, contributions, or to wire a new city? Add a new ring in `utc/bbox.py`
  and the grid assembly in `features/data_layer.py`; the rest follows the contract.