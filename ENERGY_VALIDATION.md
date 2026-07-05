# Energy Inference Validation — Quantitative Assessment

**Date**: 2026-07-05
**Scope**: All 8 races of the 2026 dataset
**Tool**: `backend/scripts/validate_energy.py` (stdlib-only, run with `--all`)

Public telemetry contains no ERS/battery ground truth, so absolute accuracy
cannot be measured. This suite instead combines **invariant checks** (rules
that must hold if the classification is sane) with a **physics proxy**
(power-balance cross-check) to produce quantitative, repeatable metrics.

---

## Method

### A. Invariants
1. **VSC discipline** — drivers should deploy less on VSC laps than green laps
2. **Energy budget** — per lap: deploy time x 350 kW must stay under ~4 MJ;
   harvest time x ~150 kW (realistic average recovery power) under ~8.5 MJ
3. **Sample contradictions** — deploy while braking / below 80% throttle,
   clip below 95% throttle, harvest at full throttle
4. **Teammate clip correlation** — same car should produce similar clip profiles

### B. Physics proxy
`P_wheel = m*a*v + 0.5*rho*CdA*v^3 + Crr*m*g*v` per sample (a from time_s,
or the kinematic fallback (v1²-v0²)/2Δs for pre-Miami imports that lack
time_s). CdA calibrated per team from 99.5th-percentile top speed assuming
full ICE+MGU-K power at terminal velocity, clamped to [0.9, 1.8] m².
Samples where P_wheel exceeds ICE-only capability (380 kW effective) by >10%
are **physics-certain deployment**. Assumptions: m=850 kg, ICE 400 kW,
MGU-K 350 kW, driveline eff. 0.95 — documented in the script header.

### Confidence score (0–100)
`100 - 40*contradiction - 30*vsc_violation_share - 20*budget_violation_share - 10*low_teammate_corr`

---

## Results (2026 season, 8 races)

| Race | Confidence | Contradiction % | Physics Precision | Physics Recall | VSC violators | Budget viol. laps | Teammate clip corr (med) |
|------|-----------|-----------------|-------------------|----------------|---------------|-------------------|--------------------------|
| Australia | 89.5 | 0.07% | 0.985 | 0.051 | 1/20 | 1/1000 | 0.08 |
| China | 89.5 | 0.54% | 0.991 | 0.081 | — | 0/904 | 0.08 |
| Japan | 89.9 | 1.09% | 0.979 | 0.079 | — | 11/1064 | 0.31 |
| Miami | 88.3 | 0.51% | 0.995 | 0.133 | — | 17/996 | 0.19 |
| Canada | 89.1 | 0.00% | 1.000 | 0.085 | 1/19 | 0/1206 | 0.03 |
| Monaco | 83.1 | 2.11% | 1.000 | 0.013 | — | 14/1415 | 0.18 |
| Barcelona | 80.4 | 1.34% | 0.995 | 0.052 | 4/19 | 0/1228 | 0.10 |
| Austria | 82.0 | 1.31% | 0.996 | 0.048 | 4/20 | 0/1332 | 0.16 |

---

## Key findings

### 1. Precision is excellent; the "deploy" label is trustworthy
When the classifier marks a sample as DEPLOY, the physics model agrees in
**98–100%** of cases across all 8 races. False positives are rare.

### 2. Recall is low by construction — and that is the honest headline
Only **1–13%** of physics-certain deployment samples are labeled DEPLOY.
This quantifies the limitation already noted in ENERGY_REPORT.md: the ICE
baseline is built from full-throttle samples that *already contain routine
ERS deployment*, so the sigma-threshold only fires on deployment *beyond the
typical level*. The current model is therefore an **anomalous-deployment
detector, not a total-deployment measure**. Consequences for the product:
- Deploy % values are *relative* signals (who pushed harder than usual),
  not absolute energy usage. UI copy and annotations should not imply
  absolute measurement.
- D/C ratios remain meaningful for driver-to-driver comparison because the
  same bias applies to everyone.

### 3. Monaco is the weakest race for the method (expected)
Highest contradiction rate (2.1%), lowest recall (1.3%) — a low-speed,
wall-lined lap with no long straights gives the accel-based baseline the
least signal. Treat Monaco energy insights with extra caution.

### 4. Teammate clip correlation is weak (0.03–0.31)
Per-lap clip profiles of teammates barely correlate. Either clipping is
driven more by individual deployment strategy than by the car, or per-lap
clip percentages are noise-dominated at this sampling rate (2.5 Hz).
Either way, annotations should avoid claims like "team X has a clipping
problem" based on a single race.

### 5. VSC discipline mostly holds
Austria and Barcelona each show 4/20 drivers with VSC-lap deploy above
their green-lap mean; worth a spot-check (restart laps counted as VSC laps
are the likely cause).

---

## Recommended next steps

1. **Wire into the import pipeline**: run `validate_energy.py <race>` after
   each import; fail loudly if confidence < 50, store `validation.json`.
2. **V2 classifier**: use the power-balance model directly (physics-certain
   deploy as a positive class) instead of the sigma-over-baseline heuristic —
   the recall gap above is the roadmap.
3. **Manual spot-check set**: hand-label 2–3 laps from F1 TV onboard ERS
   graphics (~500 samples) to get one genuinely external accuracy estimate.
4. **Surface confidence in the UI**: the per-race score could back the
   existing "INFERRED" badge (e.g. tooltip "validation confidence 82/100").
