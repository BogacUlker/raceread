# RaceRead

F1 post-race telemetry analysis platform. Interactive charts show what happened. AI annotations explain why. Energy inference reveals the invisible battery strategy that decides races in 2026.

**Live**: [raceread.app](https://raceread.app)

## What is this?

2026 F1 regulations introduced the biggest technical change in the sport's history. ~50% of car power now comes from the battery. Energy management decides races more than tire strategy. But this data isn't broadcast - teams guard it closely.

RaceRead infers energy states from publicly available telemetry (via FastF1) and visualizes what no other tool shows:

- **Deploy/Clip Ratio** - energy efficiency metric we created. Higher = smarter energy use
- **Energy state timeline** - lap-by-lap deploy/harvest/clip breakdown per driver
- **Track map with energy overlay** - see where on track drivers deploy and harvest, with corner zoom
- **Speed trace with energy coloring** - two-driver comparison with energy context
- **AI-generated annotations** - bilingual (TR/EN) race insights generated via Claude API
- **Traffic analysis** - time spent in dirty air and pace degradation
- **Qualifying animation** - two drivers' qualifying laps animated on track with live speed panels
- **Pit stop time loss** - computed from lap deltas, SC pit detection

Plus standard race analysis: pace charts, strategy timeline, delta matrix, qualifying breakdown, per-driver qualifying detail with phase progression and sector mapping.

## Design

RaceRead uses a custom design system inspired by the Bloomberg Terminal aesthetic:

- **Space Grotesk** headlines, **JetBrains Mono** data, **DM Sans** body text
- 0px border-radius throughout - sharp corners signal "professional tool"
- Tonal layering instead of borders - surfaces distinguished by background shade
- Chart cards with hover glow effect and left accent border
- Dark theme optimized for broadcaster and analyst use
- Collapsible sidebar with hover-to-expand for race navigation
- Dynamic hero with animated drivers racing on the most recent circuit

## Pages

| Page | Description |
|------|-------------|
| **Homepage** | Hero section, 2026 season timeline, race cards with hover stats, animated circuit |
| **Race Dashboard** | Overview cards (SC/VSC, margin, overtakes, D/C ratio), all charts with driver filtering |
| **Compare** | Side-by-side driver analysis with custom SpeedTrace, TrackMap, and EnergyTimeline components |
| **Qualifying Detail** | Per-driver attempts, Q1/Q2/Q3 phase progression, sector track map, improvement chart |
| **Qualifying Animation** | 3-column layout: live speed panels, track animation, mini gap chart |
| **Broadcast Mode** | Full-screen charts with manual selection via bottom pill bar |
| **How It Works** | Bilingual explainer: data source, energy inference, AI annotations |
| **About** | Creator info, tech stack, contact |

## Charts

20+ interactive charts and features across race and qualifying sessions:

| Chart | What it shows |
|-------|--------------|
| Race Pace | Lap-by-lap gap-to-leader with SC/VSC overlay, pin up to 5 drivers |
| Summarized Pace | Median pace distribution per driver |
| Delta Matrix | Driver-to-driver median gap heatmap |
| Strategy Timeline | Tyre compounds, pit stops, SC/VSC periods |
| Pit Stop Stats | Per-driver pit stop time loss, SC pit detection |
| Energy Profile | Normalized deploy/harvest/clip per driver, click to sync Energy Timeline |
| Energy Timeline | Lap-by-lap energy state changes |
| Speed Trace | Two-driver speed comparison by track distance |
| Track Map | Telemetry on circuit layout with corner zoom and animation |
| Traffic Analysis | Time in dirty air per driver |
| Compare SpeedTrace | Purpose-built two-driver overlay with shared lap selector |
| Compare TrackMap | Delta heatmap on single track with animation |
| Compare EnergyTimeline | Side-by-side stacked bars for two drivers |
| Qualifying Results | Q1/Q2/Q3 times with elimination rounds |
| Sector Comparison | Sector times across drivers |
| Gap to Pole | Qualifying delta visualization |
| Ideal Laps | Theoretical best lap from best sectors across sessions |
| Phase Progression | Q1/Q2/Q3 visual timeline with attempt dots |
| Sector Track Map | Circuit colored by sector with best times |
| Qualifying Animation | Time-synced lap animation with live speed and gap panels |

All charts are interactive: hover tooltips, driver filtering, corner zoom on track map, cross-chart sync.

## Energy Inference

Energy states are **inferred, not measured**. The model:

1. Calculates acceleration from speed telemetry (Gaussian smoothed)
2. Builds per-driver ICE baseline (expected acceleration at each speed)
3. Classifies each telemetry sample:
   - **Deploying**: acceleration significantly above baseline at high throttle
   - **Harvesting**: braking or low throttle with deceleration
   - **Clipping**: full throttle but acceleration below baseline (ICE power stolen for battery)
   - **Neutral**: steady-state driving

Validated against VSC laps (all drivers show +harvesting during VSC - model found this independently).

Always displayed with an "inferred" badge. This is inference, not measurement.

## AI Annotations

Race annotations are generated via Claude API (Sonnet 4.6), not live chat. After each race:

1. `export_for_annotations.py` aggregates all race data into structured markdown
2. `generate_annotations.py` sends data + system prompt to Claude API
3. Claude returns 25-35 bilingual (TR/EN) annotations as JSON
4. Annotations appear as insight cards and chart tooltips

Detection categories: pace anomaly, energy shift, safety car, pit stop, position change, fastest lap, traffic insight, qualifying insight.

Cost: ~$0.50-0.75 per race with Sonnet.

## Tech Stack

- **Frontend**: SvelteKit 2 + Svelte 5 + D3.js
- **Backend**: FastAPI (Python)
- **Data**: FastF1 3.8.1 (MIT licensed)
- **Energy Inference**: Python + NumPy + SciPy (physics-based, acceleration residual model)
- **AI Annotations**: Claude API (Sonnet 4.6)
- **i18n**: Turkish + English (bilingual from day one)
- **Design**: Space Grotesk + JetBrains Mono + DM Sans
- **Hosting**: Hetzner VPS, Docker
- **Domain**: raceread.app via Cloudflare

## Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn backend.app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

## Data Import

```bash
# Import a race (requires FastF1)
python -m backend.scripts.import_race --year 2026 --round 1

# Generate annotations (requires ANTHROPIC_API_KEY)
ANTHROPIC_API_KEY=sk-ant-xxx python -m backend.scripts.generate_annotations --race 2026-australia
```

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

## License

[Business Source License 1.1](LICENSE)

- Read, learn, fork for personal/educational use: **allowed**
- Contribute: **welcome**
- Host a competing commercial service: **not allowed**
- After 2030: automatically becomes Apache 2.0

## Acknowledgments

- [FastF1](https://github.com/theOehrly/Fast-F1) - F1 telemetry data (MIT)
- [LayerCake](https://layercake.graphics/) - Svelte chart framework
- Built with [Claude Code](https://claude.ai/claude-code)
