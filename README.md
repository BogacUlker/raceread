# RaceRead

F1 post-race telemetry analysis platform. Interactive charts show what happened. Energy inference reveals the invisible battery strategy that decides races in 2026.

**Live**: [raceread.app](https://raceread.app)

## What is this?

2026 F1 regulations introduced the biggest technical change in the sport's history. ~50% of car power now comes from the battery. Energy management decides races more than tire strategy. But this data isn't broadcast - teams guard it closely.

RaceRead infers energy states from publicly available telemetry (via FastF1) and visualizes what no other tool shows:

- **Deploy/Clip Ratio** - energy efficiency metric we created. Higher = smarter energy use
- **Energy state timeline** - lap-by-lap deploy/harvest/clip breakdown per driver
- **Track map with energy overlay** - see where on track drivers deploy and harvest, with corner zoom
- **Speed trace with energy coloring** - two-driver comparison with energy context
- **Traffic analysis** - time spent in dirty air and pace degradation
- **Pit stop time loss** - computed from lap deltas, SC pit detection
- **Qualifying animation** - two drivers' qualifying laps animated on track with real-time gap chart
- **Ideal lap analysis** - theoretical best from best sectors across Q1/Q2/Q3

Plus standard race analysis: pace charts, strategy timeline, delta matrix, qualifying breakdown, per-driver qualifying detail pages.

## Charts

18 interactive charts and features across race and qualifying sessions:

| Chart | What it shows |
|-------|--------------|
| Race Pace | Lap-by-lap gap-to-leader with SC/VSC overlay |
| Summarized Pace | Median pace distribution per driver |
| Delta Matrix | Driver-to-driver median gap heatmap |
| Strategy Timeline | Tyre compounds, pit stops, SC/VSC periods |
| Pit Stop Stats | Per-driver pit stop time loss, SC pit detection |
| Energy Profile | Normalized deploy/harvest/clip per driver |
| Energy Timeline | Lap-by-lap energy state changes |
| Speed Trace | Two-driver speed comparison by track distance |
| Track Map | Telemetry on circuit layout with corner zoom |
| Traffic Analysis | Time in dirty air per driver |
| Pilot Comparison | Side-by-side analysis of any two drivers |
| Qualifying Results | Q1/Q2/Q3 times with elimination rounds |
| Sector Comparison | Sector times across drivers |
| Gap to Pole | Qualifying delta visualization |
| Ideal Laps | Theoretical best lap from best sectors across sessions |
| Driver Qualifying Detail | Per-driver attempt history, time progression, best sectors |
| Qualifying Animation | Time-synced lap animation of two drivers on track with live gap chart |
| Broadcaster Mode | Full-screen, auto-cycling charts for live streams |

All charts are interactive: hover tooltips, driver filtering, corner zoom on track map, cross-chart sync on hover.

## Energy Inference

Energy states are **inferred, not measured**. The model:

1. Calculates acceleration from speed telemetry
2. Builds per-driver ICE baseline (expected acceleration at each speed)
3. Classifies each telemetry sample:
   - **Deploying**: acceleration significantly above baseline at high throttle
   - **Harvesting**: braking or low throttle with deceleration
   - **Clipping**: full throttle but acceleration below baseline (battery limiting power)
   - **Neutral**: steady-state driving

Validated against VSC laps (all drivers show +harvesting during VSC - model found this independently).

Always displayed with an "inferred" badge. This is inference, not measurement.

## Tech Stack

- **Frontend**: SvelteKit + D3.js/LayerCake
- **Backend**: FastAPI (Python)
- **Data**: FastF1 3.8.1 (MIT licensed)
- **Energy Inference**: Python + NumPy (physics-based, acceleration residual model)
- **i18n**: Turkish + English (bilingual)
- **Hosting**: Hetzner VPS, Docker

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
cd backend
python -m scripts.import_race --year 2026 --round 1

# Re-run energy inference only
python -m scripts.import_race --year 2026 --round 1 --telemetry-only
```

## Contributing

Contributions are welcome. Please open an issue first to discuss what you'd like to change.

The codebase was built with Claude Code (LLM-assisted development). If you're reading the code to learn, welcome.

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
