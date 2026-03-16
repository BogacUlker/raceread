"""Pit stop time loss analysis.

Computes per-driver pit stop time loss by comparing pit laps against
the driver's median clean pace. Identifies compound changes and
whether the stop occurred under Safety Car or Virtual Safety Car.
"""

from __future__ import annotations

import statistics
from typing import Any

from backend.app.services.preprocessing import _extract_sc_laps, _extract_vsc_laps, _round


def compute_pit_stats(
    laps_data: dict,
    strategy_data: dict,
    race_control_data: dict,
) -> dict[str, Any]:
    """Compute pit stop time loss statistics for all drivers.

    Algorithm:
    1. Extract SC/VSC laps from race control data.
    2. For each driver in strategy_data, look up their pit_laps.
    3. Build a set of "clean" lap times by excluding:
       - Lap 1 (standing start distortion)
       - SC/VSC laps
       - Pit laps and the lap immediately after each pit (pit_lap + 1)
    4. Median clean pace becomes the baseline.
    5. Time loss per pit = lap[pit_lap].time_s + lap[pit_lap+1].time_s - 2 * baseline.
    6. Track compound changes and SC/VSC status for each stop.

    Returns:
        {"drivers": [DriverPitStats, ...]} sorted by total_time_lost_s descending.
    """
    vsc_laps = set(_extract_vsc_laps(race_control_data))
    sc_laps = set(_extract_sc_laps(race_control_data))
    neutralized_laps = vsc_laps | sc_laps

    # Build per-driver lap lookup from laps_data.
    # laps_data format: {"drivers": [...], "teams": {...}, "laps": {"VER": [{...}], ...}}
    driver_laps_map: dict[str, list[dict]] = {}
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        for drv, drv_laps in laps_data["laps"].items():
            driver_laps_map[drv] = drv_laps if isinstance(drv_laps, list) else []

    # Process each driver from strategy data
    results: list[dict[str, Any]] = []

    strategy_drivers = strategy_data.get("drivers", [])
    for driver_entry in strategy_drivers:
        driver_code = driver_entry.get("driver", "")
        team = driver_entry.get("team", "Unknown")
        pit_laps_list: list[int] = driver_entry.get("pit_laps", [])

        drv_laps = driver_laps_map.get(driver_code, [])
        if not drv_laps:
            # No lap data for this driver - include with empty pits
            results.append({
                "driver": driver_code,
                "team": team,
                "pits": [],
                "total_time_lost_s": 0.0,
                "num_stops": 0,
            })
            continue

        # Build a lap_number -> lap_dict index for fast lookups
        lap_by_number: dict[int, dict] = {}
        for lap in drv_laps:
            lap_num = lap.get("lap")
            if lap_num is not None:
                lap_by_number[lap_num] = lap

        # Build set of all laps adjacent to pit stops (pit_lap and pit_lap+1)
        pit_adjacent: set[int] = set()
        for pl in pit_laps_list:
            pit_adjacent.add(pl)
            pit_adjacent.add(pl + 1)

        # Collect clean lap times for baseline computation
        clean_times: list[float] = []
        for lap in drv_laps:
            lap_num = lap.get("lap", 0)
            time_s = lap.get("time_s")

            if lap_num <= 1:
                continue
            if time_s is None:
                continue
            if lap_num in neutralized_laps:
                continue
            if lap_num in pit_adjacent:
                continue
            if lap.get("is_accurate") is False:
                continue

            clean_times.append(time_s)

        # Compute baseline median clean pace
        baseline: float | None = None
        if clean_times:
            baseline = statistics.median(clean_times)

        # Compute time loss per pit stop
        pit_details: list[dict[str, Any]] = []
        total_loss = 0.0

        for pl in pit_laps_list:
            pit_lap_data = lap_by_number.get(pl)
            out_lap_data = lap_by_number.get(pl + 1)

            # Determine compound change
            compound_from: str | None = None
            compound_to: str | None = None
            if pit_lap_data and pit_lap_data.get("compound"):
                compound_from = pit_lap_data["compound"][0]  # First letter: H, M, S
            if out_lap_data and out_lap_data.get("compound"):
                compound_to = out_lap_data["compound"][0]

            # Check if pit stop happened under SC/VSC
            under_sc = pl in neutralized_laps

            # Compute time loss
            time_loss: float | None = None
            if baseline is not None:
                pit_time = pit_lap_data.get("time_s") if pit_lap_data else None
                out_time = out_lap_data.get("time_s") if out_lap_data else None

                if pit_time is not None and out_time is not None:
                    time_loss = _round(pit_time + out_time - 2 * baseline)
                    total_loss += time_loss
                elif pit_time is not None and out_time is None:
                    # Pit on last lap or missing out lap - estimate from single lap
                    time_loss = _round(pit_time - baseline)
                    total_loss += time_loss

            pit_details.append({
                "lap": pl,
                "time_loss_s": time_loss,
                "compound_from": compound_from,
                "compound_to": compound_to,
                "under_sc": under_sc,
            })

        results.append({
            "driver": driver_code,
            "team": team,
            "pits": pit_details,
            "total_time_lost_s": _round(total_loss),
            "num_stops": len(pit_laps_list),
        })

    # Sort by total_time_lost_s descending
    results.sort(key=lambda d: d["total_time_lost_s"] or 0.0, reverse=True)

    return {"drivers": results}
