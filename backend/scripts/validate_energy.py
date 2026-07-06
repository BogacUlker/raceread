"""Energy inference validation suite.

Two independent checks on the inferred energy states, neither requiring
ground truth (which public telemetry does not provide):

A. INVARIANTS - rules that must hold if the classification is sane:
   1. VSC/SC laps should show less deployment than green laps
   2. Per-lap deploy/harvest energy must fit physical budgets
      (350 kW MGU-K; see constants below)
   3. Sample-level contradictions (deploy while braking, harvest at
      full throttle, clip below the 95% throttle definition)
   4. Teammates share a car -> their clip profiles should correlate

B. PHYSICS PROXY - power-balance cross-check:
   P_wheel = m*a*v + 0.5*rho*CdA*v^3 + Crr*m*g*v
   Samples where P_wheel exceeds what the ICE alone can deliver are
   "physics-certain" deployment. Precision/recall of the classifier is
   reported against this partial label set. CdA is calibrated per team
   from top-speed samples. All constants are assumptions (documented
   below), so treat the output as a proxy metric, not absolute truth.

Usage:
    python3 backend/scripts/validate_energy.py 2026-austria [more ids]
    python3 backend/scripts/validate_energy.py --all

Writes data/<race>/validation.json and prints a summary table.
Exit code 1 if any race scores below CONFIDENCE_FAIL.
"""

import json
import statistics
import sys
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# --- Physical assumptions (2026 power unit regulations, approximate) ---
MASS_KG = 850.0          # car + driver + mid-race fuel
P_ICE_W = 400e3          # ICE peak power
P_K_W = 350e3            # MGU-K peak power
DRIVELINE_EFF = 0.95
RHO = 1.225              # air density kg/m^3
CRR = 0.012              # rolling resistance coefficient
G = 9.81
CDA_CLAMP = (0.9, 1.8)   # plausible F1 CdA range m^2
DEPLOY_BUDGET_MJ = 4.0   # max plausible deploy energy per lap (at full 350 kW)
HARVEST_BUDGET_MJ = 8.5  # max plausible recovered energy per lap
P_HARVEST_AVG_W = 150e3  # realistic average recovery power under braking
PHYS_CERTAIN_MARGIN = 1.10  # P_wheel must exceed ICE-only by 10%
CONFIDENCE_FAIL = 50

# Era overrides: 2021-22 hybrid PU (MGU-H era, 120 kW MGU-K, 2 MJ/lap K-recovery)
ERAS = {
    "2021": dict(P_ICE_W=540e3, P_K_W=120e3, DEPLOY_BUDGET_MJ=4.2,
                 HARVEST_BUDGET_MJ=2.4, P_HARVEST_AVG_W=70e3),
}
_DEFAULTS = dict(P_ICE_W=P_ICE_W, P_K_W=P_K_W, DEPLOY_BUDGET_MJ=DEPLOY_BUDGET_MJ,
                 HARVEST_BUDGET_MJ=HARVEST_BUDGET_MJ, P_HARVEST_AVG_W=P_HARVEST_AVG_W)


def load(path):
    with open(path) as f:
        return json.load(f)


def pearson(xs, ys):
    n = len(xs)
    if n < 5:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    cov = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    vx = sum((a - mx) ** 2 for a in xs)
    vy = sum((b - my) ** 2 for b in ys)
    if vx == 0 or vy == 0:
        return None
    return cov / (vx * vy) ** 0.5


def check_invariants(race_dir, laps_data):
    energy_dir = race_dir / "energy"
    lap_times = {}   # driver -> {lap: time_s}
    for drv, laps in laps_data["laps"].items():
        lap_times[drv] = {l["lap"]: l["time_s"] for l in laps if l.get("time_s")}

    per_driver = {}
    deploy_budget_violations = 0
    harvest_budget_violations = 0
    budget_total = 0
    vsc_violators = []
    vsc_checked = []
    clip_series = {}  # driver -> {lap: clip_pct}

    for f in sorted(energy_dir.glob("*.json")):
        drv = f.stem.upper()
        e = load(f)
        laps = e.get("laps", [])
        if not laps:
            continue
        green = [l["deploy_pct"] for l in laps if not l.get("is_vsc")]
        vsc = [l["deploy_pct"] for l in laps if l.get("is_vsc")]
        clip_series[drv] = {l["lap"]: l["clip_pct"] for l in laps}

        if vsc and green:
            g_mean = statistics.mean(green)
            v_mean = statistics.mean(vsc)
            vsc_checked.append(drv)
            if g_mean > 0 and v_mean >= g_mean:
                vsc_violators.append(drv)

        # energy budget per lap: deploy assumed at full MGU-K power (bursts),
        # harvest at a realistic average recovery power
        for l in laps:
            t = lap_times.get(drv, {}).get(l["lap"])
            if not t:
                continue
            budget_total += 1
            deploy_mj = l["deploy_pct"] / 100 * t * P_K_W / 1e6
            harvest_mj = l["harvest_pct"] / 100 * t * P_HARVEST_AVG_W / 1e6
            if deploy_mj > DEPLOY_BUDGET_MJ:
                deploy_budget_violations += 1
            if harvest_mj > HARVEST_BUDGET_MJ:
                harvest_budget_violations += 1

        per_driver[drv] = {"team": e.get("team")}

    # teammate clip correlation
    teams = {}
    for drv, meta in per_driver.items():
        teams.setdefault(meta["team"], []).append(drv)
    team_corrs = {}
    for team, drvs in teams.items():
        if len(drvs) != 2:
            continue
        a, b = clip_series.get(drvs[0], {}), clip_series.get(drvs[1], {})
        common = sorted(set(a) & set(b))
        r = pearson([a[l] for l in common], [b[l] for l in common])
        if r is not None:
            team_corrs[team] = round(r, 3)

    return {
        "vsc_drivers_checked": len(vsc_checked),
        "vsc_violators": vsc_violators,
        "deploy_budget_violation_laps": deploy_budget_violations,
        "harvest_budget_violation_laps": harvest_budget_violations,
        "budget_total_laps": budget_total,
        "teammate_clip_corr": team_corrs,
    }


def check_samples_and_physics(race_dir, laps_data):
    tel_dir = race_dir / "telemetry"
    teams = laps_data.get("teams", {})

    # ---- pass 1: per-team terminal speed for CdA calibration ----
    team_top = {}
    tel_cache = {}
    for f in sorted(tel_dir.glob("*.json")):
        drv = f.stem.upper()
        t = load(f)
        tel_cache[drv] = t
        speeds = [
            s["speed"] for lap in t.get("laps", []) for s in lap.get("samples", [])
            if s.get("throttle", 0) >= 99 and not s.get("brake")
        ]
        if speeds:
            speeds.sort()
            vt = speeds[int(len(speeds) * 0.995)] / 3.6
            team = teams.get(drv, "?")
            team_top[team] = max(team_top.get(team, 0), vt)

    p_avail = (P_ICE_W + P_K_W) * DRIVELINE_EFF
    team_cda = {}
    for team, vt in team_top.items():
        if vt < 60:
            continue
        cda = (p_avail - CRR * MASS_KG * G * vt) / (0.5 * RHO * vt ** 3)
        team_cda[team] = max(CDA_CLAMP[0], min(CDA_CLAMP[1], cda))

    # ---- pass 2: contradictions + physics labels ----
    p_ice_eff = P_ICE_W * DRIVELINE_EFF
    contra_rates = []
    precisions, recalls = [], []
    per_driver = {}

    for drv, t in tel_cache.items():
        cda = team_cda.get(teams.get(drv, "?"), 1.3)
        contra = active = 0
        d_total = d_phys_ok = 0          # precision proxy
        cert_total = cert_deploy = 0      # recall proxy
        for lap in t.get("laps", []):
            ss = lap.get("samples", [])
            for i in range(1, len(ss) - 1):
                s = ss[i]
                st = s.get("energy", "N")
                thr = s.get("throttle", 0)
                brk = s.get("brake", False)
                if st != "N":
                    active += 1
                    if st == "D" and (brk or thr < 80):
                        contra += 1
                    elif st == "C" and thr < 95:
                        contra += 1
                    elif st == "H" and thr >= 95 and not brk:
                        contra += 1
                # physics: accel from time_s when present, else kinematic
                # fallback from dist (a = (v1^2 - v0^2) / 2*ds)
                v0, v1 = ss[i - 1].get("speed"), ss[i + 1].get("speed")
                if None in (v0, v1, s.get("speed")):
                    continue
                v = s["speed"] / 3.6
                if v < 20 or brk or thr < 80:
                    continue
                t0, t1 = ss[i - 1].get("time_s"), ss[i + 1].get("time_s")
                if t0 is not None and t1 is not None and 0.1 < t1 - t0 < 2.5:
                    a = (v1 - v0) / 3.6 / (t1 - t0)
                else:
                    s0, s1 = ss[i - 1].get("dist"), ss[i + 1].get("dist")
                    if s0 is None or s1 is None or not (1 < s1 - s0 < 250):
                        continue
                    a = ((v1 / 3.6) ** 2 - (v0 / 3.6) ** 2) / (2 * (s1 - s0))
                p_wheel = MASS_KG * a * v + 0.5 * RHO * cda * v ** 3 + CRR * MASS_KG * G * v
                certain = p_wheel > p_ice_eff * PHYS_CERTAIN_MARGIN
                if st == "D":
                    d_total += 1
                    if p_wheel > p_ice_eff:
                        d_phys_ok += 1
                if certain:
                    cert_total += 1
                    if st == "D":
                        cert_deploy += 1
        rate = contra / active if active else 0.0
        contra_rates.append(rate)
        prec = d_phys_ok / d_total if d_total else None
        rec = cert_deploy / cert_total if cert_total else None
        if prec is not None:
            precisions.append(prec)
        if rec is not None:
            recalls.append(rec)
        per_driver[drv] = {
            "contradiction_rate": round(rate, 4),
            "deploy_physics_precision": round(prec, 3) if prec is not None else None,
            "deploy_physics_recall": round(rec, 3) if rec is not None else None,
        }

    return {
        "team_cda": {k: round(v, 3) for k, v in sorted(team_cda.items())},
        "median_contradiction_rate": round(statistics.median(contra_rates), 4) if contra_rates else None,
        "median_deploy_precision": round(statistics.median(precisions), 3) if precisions else None,
        "median_deploy_recall": round(statistics.median(recalls), 3) if recalls else None,
        "per_driver": per_driver,
    }


def confidence(inv, phys):
    score = 100.0
    c = phys.get("median_contradiction_rate") or 0
    score -= min(40, 400 * c)
    if inv["vsc_drivers_checked"]:
        score -= 30 * len(inv["vsc_violators"]) / inv["vsc_drivers_checked"]
    if inv["budget_total_laps"]:
        viol = inv["deploy_budget_violation_laps"] + inv["harvest_budget_violation_laps"]
        score -= min(20, 200 * viol / inv["budget_total_laps"])
    corrs = list(inv["teammate_clip_corr"].values())
    if corrs:
        med = statistics.median(corrs)
        score -= 10 * max(0.0, (0.5 - med) / 0.5)
    return round(score, 1)


def validate_race(race_id):
    # apply era-specific power-unit constants (single-threaded script)
    globals().update(_DEFAULTS)
    globals().update(ERAS.get(race_id[:4], {}))
    race_dir = DATA_DIR / race_id
    laps_data = load(race_dir / "laps.json")
    inv = check_invariants(race_dir, laps_data)
    phys = check_samples_and_physics(race_dir, laps_data)
    score = confidence(inv, phys)
    result = {"race": race_id, "confidence": score, "invariants": inv, "physics": phys}
    (race_dir / "validation.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__)
        sys.exit(2)
    if args == ["--all"]:
        race_ids = sorted(d.name for d in DATA_DIR.iterdir() if d.is_dir() and (d / "laps.json").exists())
    else:
        race_ids = args

    failed = False
    print(f"{'race':<18} {'conf':>5} {'contra%':>8} {'prec':>6} {'rec':>6} {'vsc-viol':>9} {'budget':>7} {'clip-corr':>9}")
    for rid in race_ids:
        r = validate_race(rid)
        inv, phys = r["invariants"], r["physics"]
        corrs = list(inv["teammate_clip_corr"].values())
        med_corr = f"{statistics.median(corrs):.2f}" if corrs else "-"
        c = phys["median_contradiction_rate"]
        viol = inv["deploy_budget_violation_laps"] + inv["harvest_budget_violation_laps"]
        print(f"{rid:<18} {r['confidence']:>5} {100*c if c is not None else -1:>7.2f}% "
              f"{phys['median_deploy_precision'] or '-':>6} {phys['median_deploy_recall'] or '-':>6} "
              f"{len(inv['vsc_violators']):>2}/{inv['vsc_drivers_checked']:<2}    "
              f"{viol:>3}/{inv['budget_total_laps']:<5} {med_corr:>7}")
        if r["confidence"] < CONFIDENCE_FAIL:
            failed = True
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
