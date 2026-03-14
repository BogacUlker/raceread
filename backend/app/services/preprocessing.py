"""Computed analytics: delta matrix, energy comparison, VSC comparison.

All heavy computation lives here so routers stay thin.
"""

from __future__ import annotations

import statistics
from typing import Any

from backend.app.config import MIN_LAPS_THRESHOLD


def _round(value: float | None, decimals: int = 2) -> float | None:
    """Round a float to the specified decimal places, or return None."""
    if value is None:
        return None
    return round(value, decimals)


def _extract_vsc_laps(race_control_data: dict) -> list[int]:
    """Extract VSC lap numbers from race control data."""
    vsc_laps: list[int] = []
    if "vsc_laps" in race_control_data:
        vsc_laps.extend(race_control_data["vsc_laps"])
    return vsc_laps


def _extract_sc_laps(race_control_data: dict) -> list[int]:
    """Extract SC lap numbers from race control data."""
    sc_laps: list[int] = []
    if "sc_laps" in race_control_data:
        sc_laps.extend(race_control_data["sc_laps"])
    return sc_laps


def _is_pit_lap(lap: dict) -> bool:
    """Check if a lap involves a pit stop (in or out)."""
    pit_in = lap.get("pit_in_time") or lap.get("PitInTime")
    pit_out = lap.get("pit_out_time") or lap.get("PitOutTime")
    return pit_in is not None or pit_out is not None


def compute_delta_matrix(
    laps_data: dict,
    race_control_data: dict,
) -> dict[str, Any]:
    """Compute NxN median lap time delta matrix across all drivers.

    Filters out:
    - Lap 1 (formation / standing start distortion)
    - Pit in/out laps
    - SC/VSC laps
    - Laps marked as inaccurate

    Only includes drivers with at least MIN_LAPS_THRESHOLD valid laps.

    Returns:
        {
            "drivers": ["VER", "NOR", ...],
            "matrix": [[0.0, 0.45, ...], [-0.45, 0.0, ...], ...]
        }

    matrix[i][j] = median(driver_i) - median(driver_j)
    Positive means driver i is slower than driver j.
    """
    vsc_laps = set(_extract_vsc_laps(race_control_data))
    sc_laps = set(_extract_sc_laps(race_control_data))
    neutralized_laps = vsc_laps | sc_laps

    # Build per-driver valid lap times
    driver_times: dict[str, list[float]] = {}

    # Our laps.json format:
    # {"drivers": ["RUS", ...], "teams": {...}, "laps": {"RUS": [...], ...}}
    drivers_list: list[dict] = []
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        for drv, drv_laps in laps_data["laps"].items():
            drivers_list.append({"driver": drv, "laps": drv_laps if isinstance(drv_laps, list) else []})
    elif isinstance(laps_data, list):
        drivers_list = laps_data
    elif isinstance(laps_data, dict) and "drivers" in laps_data and isinstance(laps_data["drivers"], list):
        if laps_data["drivers"] and isinstance(laps_data["drivers"][0], dict):
            drivers_list = laps_data["drivers"]

    for driver_entry in drivers_list:
        driver_code = driver_entry.get("driver", "UNK")
        laps = driver_entry.get("laps", [])
        valid_times: list[float] = []

        for lap in laps:
            lap_num = lap.get("lap", 0)
            time_s = lap.get("time_s")
            is_accurate = lap.get("is_accurate", True)

            # Filter conditions
            if lap_num <= 1:
                continue
            if lap_num in neutralized_laps:
                continue
            if _is_pit_lap(lap):
                continue
            if is_accurate is False:
                continue
            if time_s is None:
                continue

            valid_times.append(time_s)

        if len(valid_times) >= MIN_LAPS_THRESHOLD:
            driver_times[driver_code] = valid_times

    # Sort drivers alphabetically for consistent ordering
    sorted_drivers = sorted(driver_times.keys())
    n = len(sorted_drivers)

    # Compute medians
    medians: dict[str, float] = {}
    for drv in sorted_drivers:
        medians[drv] = statistics.median(driver_times[drv])

    # Build NxN matrix
    matrix: list[list[float | None]] = []
    for i in range(n):
        row: list[float | None] = []
        for j in range(n):
            if i == j:
                row.append(0.0)
            else:
                delta = medians[sorted_drivers[i]] - medians[sorted_drivers[j]]
                row.append(_round(delta))
        matrix.append(row)

    return {
        "drivers": sorted_drivers,
        "matrix": matrix,
    }


def compute_energy_comparison(
    all_energy: dict[str, dict],
) -> list[dict[str, Any]]:
    """Compute energy deployment comparison across all drivers.

    For each driver, extracts average deploy/harvest/clip percentages
    and the deploy-to-clip ratio. Results are sorted by dc_ratio descending
    and ranked.

    Returns a list of dicts matching EnergyComparisonEntry schema.
    """
    entries: list[dict[str, Any]] = []

    for driver, energy_data in all_energy.items():
        team = energy_data.get("team", "Unknown")
        laps = energy_data.get("laps", [])

        if not laps:
            continue

        deploy_vals: list[float] = []
        harvest_vals: list[float] = []
        clip_vals: list[float] = []

        for lap in laps:
            # Use normalized values (without neutral) for comparison
            deploy_vals.append(lap.get("normalized_deploy", 0.0))
            harvest_vals.append(lap.get("normalized_harvest", 0.0))
            clip_vals.append(lap.get("normalized_clip", 0.0))

        avg_deploy = statistics.mean(deploy_vals) if deploy_vals else 0.0
        avg_harvest = statistics.mean(harvest_vals) if harvest_vals else 0.0
        avg_clip = statistics.mean(clip_vals) if clip_vals else 0.0

        # Deploy/Clip ratio: higher = more efficient energy usage
        dc_ratio = avg_deploy / avg_clip if avg_clip > 0 else 0.0

        entries.append({
            "driver": driver,
            "team": team,
            "deploy_pct": _round(avg_deploy),
            "harvest_pct": _round(avg_harvest),
            "clip_pct": _round(avg_clip),
            "dc_ratio": _round(dc_ratio),
            "rank": 0,  # assigned below
        })

    # Sort by dc_ratio descending, assign ranks
    entries.sort(key=lambda e: e["dc_ratio"], reverse=True)
    for idx, entry in enumerate(entries, start=1):
        entry["rank"] = idx

    return entries


def compute_vsc_comparison(
    all_energy: dict[str, dict],
    vsc_laps: list[int],
) -> list[dict[str, Any]]:
    """Compare energy profiles during VSC vs normal racing.

    Separates each driver's laps into VSC and normal groups,
    then computes average deploy/harvest/clip for each.

    Returns a list of dicts matching VSCComparisonEntry schema.
    """
    vsc_set = set(vsc_laps)
    entries: list[dict[str, Any]] = []

    for driver, energy_data in all_energy.items():
        team = energy_data.get("team", "Unknown")
        laps = energy_data.get("laps", [])

        vsc_deploy: list[float] = []
        vsc_harvest: list[float] = []
        vsc_clip: list[float] = []
        normal_deploy: list[float] = []
        normal_harvest: list[float] = []
        normal_clip: list[float] = []

        for lap in laps:
            lap_num = lap.get("lap", 0)
            is_vsc = lap.get("is_vsc", False) or lap_num in vsc_set

            d = lap.get("normalized_deploy", 0.0)
            h = lap.get("normalized_harvest", 0.0)
            c = lap.get("normalized_clip", 0.0)

            if is_vsc:
                vsc_deploy.append(d)
                vsc_harvest.append(h)
                vsc_clip.append(c)
            else:
                normal_deploy.append(d)
                normal_harvest.append(h)
                normal_clip.append(c)

        # Only include drivers that have both VSC and normal laps
        if not vsc_deploy or not normal_deploy:
            continue

        entries.append({
            "driver": driver,
            "team": team,
            "vsc": {
                "deploy": _round(statistics.mean(vsc_deploy)),
                "harvest": _round(statistics.mean(vsc_harvest)),
                "clip": _round(statistics.mean(vsc_clip)),
            },
            "normal": {
                "deploy": _round(statistics.mean(normal_deploy)),
                "harvest": _round(statistics.mean(normal_harvest)),
                "clip": _round(statistics.mean(normal_clip)),
            },
        })

    # Sort by driver code for consistent ordering
    entries.sort(key=lambda e: e["driver"])
    return entries


def compute_traffic_analysis(
    all_telemetry: dict[str, dict],
    laps_data: dict,
    race_control_data: dict,
) -> dict[str, Any]:
    """Compute traffic analysis from telemetry gap_ahead data.

    A lap is "in traffic" if the median gap to the car ahead is < 1.5s
    for > 50% of valid samples on that lap.

    Returns per-driver summary and per-lap details.
    """
    traffic_threshold = 1.5  # seconds gap
    sample_threshold = 0.5  # proportion of lap in traffic

    vsc_laps = set(_extract_vsc_laps(race_control_data))
    sc_laps = set(_extract_sc_laps(race_control_data))
    neutralized = vsc_laps | sc_laps

    # Build a map of lap times for pace degradation
    lap_times: dict[str, dict[int, float]] = {}
    drivers_list = []
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        for drv, drv_laps in laps_data["laps"].items():
            drivers_list.append({"driver": drv, "laps": drv_laps if isinstance(drv_laps, list) else []})
    elif isinstance(laps_data, list):
        drivers_list = laps_data

    for d in drivers_list:
        drv = d.get("driver", "")
        lap_times[drv] = {}
        for lap in d.get("laps", []):
            if lap.get("time_s") is not None and lap.get("is_accurate") is not False:
                lap_times[drv][lap["lap"]] = lap["time_s"]

    driver_results = []

    for driver, tel_data in sorted(all_telemetry.items()):
        team = tel_data.get("team", "Unknown")
        tel_laps = tel_data.get("laps", [])

        total_laps = 0
        traffic_laps = 0
        clean_times = []
        traffic_times = []
        lap_details = []

        for lap_entry in tel_laps:
            lap_num = lap_entry.get("lap", 0)

            # Skip lap 1, SC/VSC laps
            if lap_num <= 1 or lap_num in neutralized:
                continue

            samples = lap_entry.get("samples", [])
            if not samples:
                continue

            total_laps += 1

            # Compute proportion of samples with gap < threshold
            # gap_ahead is in meters (DistanceToDriverAhead from FastF1)
            # Convert to seconds: gap_s = gap_m / (speed_kmh / 3.6)
            valid_gaps_s = []
            for s in samples:
                gap_m = s.get("gap_ahead")
                speed = s.get("speed", 0)
                if gap_m is not None and gap_m > 0 and speed and speed > 30:
                    gap_s = gap_m / (speed / 3.6)
                    valid_gaps_s.append(gap_s)

            if not valid_gaps_s:
                # Race leader or no gap data - treat as clean air
                in_traffic = False
                median_gap = None
            else:
                median_gap = sorted(valid_gaps_s)[len(valid_gaps_s) // 2]
                close_count = sum(1 for g in valid_gaps_s if g < traffic_threshold)
                in_traffic = (close_count / len(valid_gaps_s)) > sample_threshold

            if in_traffic:
                traffic_laps += 1

            # Track pace for degradation calc
            t = lap_times.get(driver, {}).get(lap_num)
            if t is not None:
                if in_traffic:
                    traffic_times.append(t)
                else:
                    clean_times.append(t)

            lap_details.append({
                "lap": lap_num,
                "in_traffic": in_traffic,
                "median_gap": _round(median_gap),
            })

        traffic_pct = round((traffic_laps / total_laps) * 100, 1) if total_laps > 0 else 0.0

        # Pace degradation: median lap time in traffic - median in clean air
        pace_degradation = None
        if clean_times and traffic_times:
            clean_median = statistics.median(clean_times)
            traffic_median = statistics.median(traffic_times)
            pace_degradation = _round(traffic_median - clean_median)

        driver_results.append({
            "driver": driver,
            "team": team,
            "total_laps": total_laps,
            "traffic_laps": traffic_laps,
            "traffic_pct": traffic_pct,
            "pace_degradation": pace_degradation,
            "lap_details": lap_details,
        })

    # Sort by traffic_pct descending
    driver_results.sort(key=lambda d: d["traffic_pct"], reverse=True)

    return {
        "drivers": driver_results,
    }
