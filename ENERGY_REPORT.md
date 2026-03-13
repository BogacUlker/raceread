# Energy Inference Prototype — RUS 2026 Australian GP

**Date**: 2026-03-13
**Driver**: George Russell (RUS)
**Session**: 2026 Australian Grand Prix — Race
**Method**: Acceleration-based energy state inference from public telemetry

---

## Methodology

1. **Acceleration**: `speed_ms = Speed / 3.6`, then `diff(speed_ms) / diff(time)`, Gaussian smoothed (sigma=1.5)
2. **ICE Baseline**: Samples where Throttle >= 95% and Brake == False, binned by 10 km/h speed ranges. Median acceleration per bin = "expected ICE-only performance"
3. **Classification**:
   - **DEPLOYING**: Throttle >= 80%, acceleration > baseline_median + 1.5*std (extra push beyond ICE alone)
   - **CLIPPING**: Throttle >= 95%, acceleration < baseline_median - 2.0*std (power limited despite full throttle)
   - **HARVESTING**: Brake == True or Throttle < 20%, acceleration < -0.3 m/s² (energy recovery under decel)
   - **NEUTRAL**: Everything else

---

## Dataset

| Metric | Value |
|--------|-------|
| Laps | 58 |
| Total telemetry samples | 37,548 |
| ICE baseline samples | 19,025 |
| Speed bins with data | 22 (130–340 km/h) |

### Overall Distribution

| State | Samples | Percentage |
|-------|---------|------------|
| NEUTRAL | 27,396 | 73.0% |
| HARVESTING | 8,663 | 23.1% |
| DEPLOYING | 1,110 | 3.0% |
| CLIPPING | 379 | 1.0% |

---

## First 5 Laps (Race Start / Tyre Warm-up)

| Lap | Deploy % | Harvest % | Clip % | Neutral % | Samples |
|-----|----------|-----------|--------|-----------|---------|
| 1 | 4.06 | 26.05 | 0.70 | 69.19 | 714 |
| 2 | 2.00 | 23.69 | 1.08 | 73.23 | 650 |
| 3 | 0.62 | 25.66 | 0.46 | 73.26 | 647 |
| 4 | 2.66 | 27.70 | 0.78 | 68.86 | 639 |
| 5 | 2.06 | 24.68 | 0.47 | 72.78 | 632 |

**Observations**:
- Lap 1 has the highest deploy (4.06%) — expected for race start with aggressive ERS usage
- Lap 1 also has higher sample count (714) — slower lap, more telemetry points
- Harvesting is elevated across early laps (24-28%) — heavy braking in traffic, tyre management

---

## Last 5 Laps (Race End / Final Push)

| Lap | Deploy % | Harvest % | Clip % | Neutral % | Samples |
|-----|----------|-----------|--------|-----------|---------|
| 54 | 3.39 | 20.32 | 0.97 | 75.32 | 620 |
| 55 | 1.58 | 21.04 | 0.47 | 76.90 | 632 |
| 56 | 4.37 | 20.06 | 1.13 | 74.43 | 618 |
| 57 | 4.03 | 22.48 | 1.86 | 71.63 | 645 |
| 58 | 3.41 | 20.81 | 0.98 | 74.80 | 615 |

**Observations**:
- Deploy spikes on laps 56-58 (3.4-4.4%) — final stint push
- Clipping peaks on lap 57 (1.86%) — battery potentially depleting in closing stages
- Harvesting drops to 20-22% vs 24-28% in early laps — less braking (cleaner air / less traffic)

---

## Top 3 Clipping Laps (Power-Limited)

| Lap | Clip % | Deploy % | Harvest % | Notes |
|-----|--------|----------|-----------|-------|
| **31** | **2.85** | 4.91 | 20.76 | Highest clipping — battery-limited mid-race |
| **34** | **2.64** | 2.91 | 21.78 | 721 samples = slower lap, possible traffic/VSC |
| **15** | **2.35** | 2.19 | 23.47 | Early stint clipping — conservative deployment? |

**Analysis**: Lap 31 is the most interesting — both high clipping (2.85%) AND high deploying (4.91%). This suggests the battery was being used aggressively but hitting limits. Lap 34 has 721 samples (slowest lap with clipping), possibly a VSC period where the system was in a constrained mode. The VSC deployments in race control data (see REPORT.md) align with mid-race timing.

---

## Top 3 Deploying Laps (Maximum ERS Usage)

| Lap | Deploy % | Clip % | Harvest % | Notes |
|-----|----------|--------|-----------|-------|
| **6** | **7.06** | 0.46 | 25.46 | Highest deployment — early stint fresh tyres |
| **28** | **5.75** | 1.92 | 23.80 | Post-pit fresh tyres, aggressive push |
| **52** | **5.12** | 1.12 | 23.36 | Late race push — fighting for position? |

**Analysis**: Lap 6 stands out with 7.06% deploy and near-zero clipping (0.46%). This is the "ideal" energy lap — full battery, fresh tyres, deploying everything without hitting limits. Lap 28 shows higher clipping alongside deploy (1.92%), suggesting the battery was more stressed. Lap 52 in the late race shows the team turning up deployment for the final push.

---

## ICE Baseline Summary (Key Speed Bins)

| Speed Bin | Median Acc (m/s²) | Std | Samples |
|-----------|-------------------|-----|---------|
| 150-160 | 10.76 | 2.94 | 120 |
| 200-210 | 4.97 | 3.93 | 1,180 |
| 250-260 | 3.72 | 3.58 | 1,347 |
| 290-300 | 1.17 | 2.06 | 1,865 |
| 310-320 | 0.00 | 1.61 | 1,863 |
| 330-340 | -0.22 | 1.49 | 37 |

The baseline shows the expected aerodynamic drag curve — high acceleration at low speeds, tapering to near-zero at top speed (~310-320 km/h). Above 330 km/h the median goes negative (drag > thrust), which is physically correct.

---

## Validation Assessment

### Does the inference make sense?

**YES — the results are physically plausible:**

1. **Distribution is reasonable**: 73% neutral is expected — most of a lap is steady-state. 23% harvesting aligns with braking zones at Albert Park (14 corners). 3% deploying and 1% clipping are small but meaningful signals.

2. **Temporal patterns are correct**:
   - Early laps: Higher harvesting (traffic braking) + higher deploy (full battery)
   - Mid-race: Clipping peaks (battery stress after sustained deployment)
   - Late race: Deploy increases again (final push), clipping rises slightly (battery fatigue)

3. **ICE baseline is physically valid**: Acceleration decreases with speed as expected from aero drag. Top speed bin shows ~0 acceleration = terminal velocity.

4. **Lap 6 vs Lap 31 contrast is telling**: Fresh-tyre aggressive lap (high deploy, low clip) vs mid-race stressed lap (both high deploy AND high clip) — this is exactly what battery degradation would look like.

### Limitations

- **No ground truth**: We're inferring energy states, not measuring them directly
- **Brake is boolean**: No brake pressure data means we can't distinguish light harvesting from full braking
- **Baseline assumes ICE-only**: In reality, some baseline samples may still have ERS contribution
- **Wind/gradient effects**: Not accounted for — could cause false positives
- **Threshold sensitivity**: The 1.5*std / 2.0*std multipliers are tunable and affect distribution significantly

### Next Steps

- Cross-validate with other drivers (VER, NOR, LEC) to see if patterns hold
- Compare deploy/clip patterns between teammates (RUS vs HAM)
- Correlate energy states with lap time delta to quantify ERS impact
- Add stint/compound awareness (fresh vs worn tyres affect acceleration)
- Overlay with race control messages (VSC periods should show distinct energy patterns)
