# CLAUDE.md — RaceRead Project Guide

## Project Overview

RaceRead (raceread.app) is an F1 post-race telemetry analysis platform. Interactive charts show what happened. Descriptor annotations (AI pre-generated) explain why. Energy inference reveals the invisible battery strategy that decides races in 2026.

**Status**: MVP-0 complete (data validated), building MVP-1.

---

## Core Architecture

```
Frontend (SvelteKit) → Backend (FastAPI) → Data (JSON → PostgreSQL later)
                                         → Energy Inference (Python)
                                         → Descriptor (Claude API batch)
```

- **Frontend**: SvelteKit + D3.js/LayerCake + Paraglide.js (i18n)
- **Backend**: FastAPI (Python), port 8000
- **Data source**: FastF1 3.8.1 (validated with 2026 Australian GP)
- **Energy inference**: Physics-based, acceleration residual model
- **Descriptor**: Pre-generated AI annotations via Claude API (batch, NOT real-time chat)
- **Hosting**: Hetzner VPS CX33 (46.225.19.63), Docker
- **Domain**: raceread.app via Cloudflare
- **Database**: JSON files for MVP-1, PostgreSQL (Supabase or raw) later

---

## Critical Rules — NEVER Violate These

1. **NEVER use Vercel** — not for hosting, not for deployment, not for anything
2. **NEVER use DRS data** — channel exists in FastF1 but is always 0 in 2026. DRS was removed from F1. Ignore this channel everywhere.
3. **NEVER use Capology** as a data source (unreliable)
4. **NEVER use Turkish news sites** as sources unless absolutely no alternative
5. **Energy states are INFERRED, not measured** — always display "inferred" badge/label on energy charts. Never claim energy data is direct measurement.
6. **No em dashes (—)** in user-facing written content. Use regular dashes or rewrite.
7. **Bilingual from day one** — all user-facing text must have TR and EN versions
8. **No live AI chat** — RaceRead uses descriptor (pre-generated annotations), not a chatbot

---

## 2026 F1 Regulations Context

This is essential knowledge for all code and content:

- **DRS is DEAD** — replaced by Active Aero (movable front+rear wings)
- **Active Aero**: X Mode (straight, wings open, low drag) / Z Mode (corner, wings closed, high downforce). All drivers can use it everywhere, no 1-second rule.
- **Boost Mode**: Driver presses button to deploy max power from battery+ICE. Can be used anytime. Drains battery.
- **Overtake Mode**: Extra energy for car within 1 second of car ahead. Replaces DRS as overtaking aid.
- **Super Clipping**: At full throttle, up to 250kW stolen from ICE to charge battery. Car runs at ~150kW. This is why cars are slow at full throttle sometimes.
- **MGU-K**: 350kW (was 120kW in 2025). MGU-H removed entirely.
- **Battery**: 8.5MJ per lap available, but only 4MJ capacity. Must recharge constantly.
- **Power split**: ~50% ICE, ~50% electrical

---

## Energy Inference Engine

### How It Works

1. Calculate acceleration from speed telemetry (diff + Gaussian smoothing)
2. Build ICE baseline: expected acceleration at each speed when only engine is working (Throttle >= 95%, Brake == False, binned by 10 km/h)
3. Classify each telemetry sample:
   - **DEPLOYING**: Throttle >= 80%, acceleration > baseline + 1.5*std
   - **CLIPPING**: Throttle >= 95%, acceleration < baseline - 2.0*std
   - **HARVESTING**: Brake == True or Throttle < 20%, acceleration < -0.3 m/s²
   - **NEUTRAL**: everything else

### Key Decisions

- **Normalized active states**: Dashboard shows deploy/harvest/clip WITHOUT neutral (neutral is ~73% and drowns the signal). Normalized: deploy ~11%, harvest ~85%, clip ~4%.
- **Deploy/Clip Ratio**: New metric we invented. Higher = more efficient. RUS 2.95 (best), HAM 1.26 (worst). This is a key differentiator chart.
- **VSC validation**: During VSC laps, all drivers show harvesting +5-8pts, deploy -1-2pts, clip ~0. Model found this independently — strong validation.

### Current Thresholds (may need calibration)

```python
deploy_threshold = baseline_median + 1.5 * std  # may lower to 1.0
clip_threshold = baseline_median - 2.0 * std     # may lower to 1.5
harvest_decel = -0.3  # m/s²
clip_throttle_min = 95  # %
deploy_throttle_min = 80  # %
```

---

## Descriptor System

NOT a chatbot. Pre-generated annotations computed once per race.

### Detection Rules (what triggers an annotation)

- Pace anomaly: lap time delta > 0.5s from rolling 3-lap average
- Energy state shift: deploy or clip % changes > 2x between consecutive laps
- SC/VSC event: race control message with SafetyCar category
- Pit stop: PitInTime is not null
- Position change: Position delta > 2 between consecutive laps
- Fastest lap: IsPersonalBest == True and best of all

### Annotation Generation

Each detected event → Claude API call with telemetry context → 2-3 sentence explanation in both TR and EN → stored as JSON → served as hover tooltip on charts.

---

## Data Available from FastF1 (2026 Confirmed)

### Lap Data (session.laps) — 31 columns
`LapTime, Sector1Time, Sector2Time, Sector3Time, Driver, Team, LapNumber, Stint, Compound, TyreLife, FreshTyre, PitInTime, PitOutTime, TrackStatus, Position, IsPersonalBest, SpeedI1, SpeedI2, SpeedFL, SpeedST, IsAccurate`

### Telemetry (lap.get_telemetry()) — per sample
`Speed (km/h), RPM, nGear, Throttle (0-100%), Brake (bool), DRS (IGNORE - always 0), X, Y, Z, Distance, RelativeDistance, DriverAhead, DistanceToDriverAhead, Time, SessionTime, Status, Source`

### Weather (session.weather_data)
`AirTemp, TrackTemp, Humidity, Pressure, Rainfall, WindDirection, WindSpeed`

### Race Control Messages
`Time, Category, Message, Status, Flag, Scope, Sector, RacingNumber, Lap`
Categories include: SafetyCar, Flag, Other

### Circuit Info
14 corners with: `X, Y, Number, Letter, Angle, Distance`

### What's NOT Available
- Battery level / State of Charge (must be inferred)
- ERS deployment data (must be inferred)
- Brake pressure (only boolean)
- Active Aero state (must be inferred from speed patterns)
- Boost/Overtake mode activation (must be inferred)

---

## Chart Roadmap (30 total, 4 tiers)

### MVP-1 (launch — 7 charts)
1. Race pace (interactive line chart, SC/VSC overlay, driver filter)
2. Summarized race pace (bar+dot distribution)
3. Pace delta matrix (driver x driver heatmap)
4. Strategy timeline (horizontal bars, compound colors, SC/VSC markers)
5. Energy profile bars (deploy/harvest/clip normalized, per driver)
6. Energy state timeline (lap-by-lap stacked bar, per driver)
7. Descriptor annotations (hover tooltips on chart anomalies)

### MVP-2 (post-launch — 7 charts)
8. Speed trace overlay (2 drivers)
9. Speed trace + energy overlay
10. Track map telemetry (X/Y + speed or energy color)
11. Pilot comparison page
12. Laps in traffic
13. Qualifying pace
14. Broadcaster mode

### Later tiers
15-30: See PRD v2 and chart feasibility matrix for full list.

---

## File Structure

```
~/raceread/
├── CLAUDE.md                      ← you are here
├── backend/
│   ├── app/
│   │   ├── main.py                (FastAPI, CORS, port 8000)
│   │   ├── routers/
│   │   │   ├── races.py
│   │   │   ├── laps.py
│   │   │   ├── energy.py
│   │   │   └── annotations.py     (descriptor tooltips)
│   │   └── services/
│   │       ├── data_loader.py     (JSON → API)
│   │       ├── energy_inference.py
│   │       ├── descriptor.py      (annotation generation)
│   │       └── preprocessing.py   (SC/VSC filter, stint detection)
│   ├── scripts/
│   │   ├── import_race.py         (FastF1 → JSON pipeline)
│   │   └── generate_annotations.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/
│   │   │   ├── [[lang]]/          (i18n: /tr/... and /en/...)
│   │   │   │   ├── +page.svelte   (race selection)
│   │   │   │   └── race/[id]/
│   │   │   │       └── +page.svelte (dashboard)
│   │   │   └── broadcast/         (broadcaster mode)
│   │   ├── lib/
│   │   │   ├── components/
│   │   │   │   ├── PaceChart.svelte
│   │   │   │   ├── EnergyBars.svelte
│   │   │   │   ├── EnergyTimeline.svelte
│   │   │   │   ├── StrategyTimeline.svelte
│   │   │   │   ├── DeltaMatrix.svelte
│   │   │   │   ├── SpeedTrace.svelte
│   │   │   │   ├── TrackMap.svelte
│   │   │   │   └── AnnotationTooltip.svelte
│   │   │   ├── stores/
│   │   │   └── i18n/
│   │   │       ├── tr.json
│   │   │       └── en.json
│   │   └── app.html
│   └── package.json
├── data/
│   ├── 2026-australia/
│   │   ├── rus_energy_laps.json   ← EXISTS
│   │   ├── ant_energy_laps.json   ← EXISTS
│   │   ├── ver_energy_laps.json   ← EXISTS
│   │   ├── lec_energy_laps.json   ← EXISTS
│   │   ├── nor_energy_laps.json   ← EXISTS
│   │   └── ham_energy_laps.json   ← EXISTS
│   └── 2026-china/               (after Chinese GP)
├── docker-compose.yml
└── README.md
```

---

## API Endpoints (MVP-1)

```
GET /api/races
  → [{id, name, date, circuit, winner, total_laps}]

GET /api/races/{id}/laps?driver=RUS
  → [{lap, time_s, s1, s2, s3, compound, tire_age, position, track_status}]

GET /api/races/{id}/energy?driver=RUS
  → [{lap, deploy_pct, harvest_pct, clip_pct, neutral_pct, normalized: {deploy, harvest, clip}}]

GET /api/races/{id}/energy/comparison
  → [{driver, team, deploy_pct, harvest_pct, clip_pct, dc_ratio, rank}]

GET /api/races/{id}/energy/vsc
  → [{driver, vsc: {deploy, harvest, clip}, normal: {deploy, harvest, clip}}]

GET /api/races/{id}/strategy
  → [{driver, stints: [{compound, start_lap, end_lap, laps}], pit_laps: []}]

GET /api/races/{id}/annotations
  → [{driver, lap, chart_type, text_tr, text_en, category, severity}]

GET /api/races/{id}/delta
  → {drivers: [], matrix: [[delta_values]]}
```

---

## Design System

- **Fonts**: JetBrains Mono (data, labels, monospace) + DM Sans (body, UI)
- **Colors**: Team colors from FastF1 `get_team_color()`. Energy states: deploy=#22C55E, harvest=#3B82F6, clip=#F59E0B, neutral=#6B7280
- **Theme**: Dark theme default (broadcaster-friendly), light theme available
- **Accent**: #E24B4A (red, used sparingly)
- **Charts**: All interactive — hover, click, filter. No static PNGs.
- **Annotations**: Appear as tooltip on hover. Left border colored by category. JetBrains Mono, 10-11px.
- **"Inferred" badge**: Small green badge (font-size: 9px, bg: #22C55E) next to any energy chart title

---

## Development Workflow

- **Claude Code**: Primary coder + tester. Runs on VPS or local.
- **Opus (claude.ai)**: Strategy, PRD, design decisions, prompt engineering, copy writing.
- **Boğaç**: Product owner, designer, motion design, broadcaster relationships, final decisions.

### Git Workflow
- Main branch: `main` (deployable)
- Feature branches: `feat/pace-chart`, `feat/energy-bars`, etc.
- Commit messages: conventional commits (`feat:`, `fix:`, `docs:`)

### Testing
- Backend: `curl` endpoint tests, pytest later
- Frontend: manual browser testing, Playwright later
- Energy inference: cross-validate with each new race

---

## Current Status & Next Steps

### DONE (MVP-0)
- [x] FastF1 2026 data validation (Australian GP)
- [x] Energy inference prototype (6 drivers, 58 laps each)
- [x] Cross-validation (D/C Ratio, VSC validation, teammate comparison)
- [x] JSON data files on VPS

### NOW (MVP-1 Week 1)
- [ ] FastAPI backend with all endpoints above
- [ ] Chinese GP data import + energy inference
- [ ] Descriptor detection rules implementation

### NEXT (MVP-1 Week 2-4)
- [ ] SvelteKit frontend scaffold
- [ ] 7 MVP-1 charts with real data
- [ ] i18n (TR/EN)
- [ ] Descriptor annotation generation
- [ ] Deploy to raceread.app

---

## Competitor Reference

- **F1Pace**: Stopped updating after 2025 Abu Dhabi. 9 recurring chart types, all static PNG. No energy analysis, no annotations. CC BY-NC-ND 4.0 license — do not copy.
- **GP Tempo**: Interactive telemetry, no AI, no energy inference. Melbourne-based solo dev. Closest UX competitor.
- **Formula Live Pulse**: Mobile app, basic AI, live timing focus (not post-race).
- **OpenF1**: API only, not a product. Potential alternative data source if FastF1 fails.

---

## Calendar Context

2026 season: Bahrain and Saudi Arabia GPs likely cancelled (Middle East conflict). Gap from Japan (Mar 29) to Miami (May 3). This is our build window. Launch target: Miami GP.

Available race data for calibration before launch:
1. Australian GP (Mar 8) ← DONE
2. Chinese GP (Mar 15) ← this weekend
3. Japanese GP (Mar 29)
