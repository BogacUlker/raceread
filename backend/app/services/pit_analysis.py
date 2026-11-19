"""Pit stop time loss analysis.

Computes per-driver pit stop time loss by comparing pit laps against
the driver's median clean pace. Identifies compound changes and
whether the stop occurred under Safety Car or Virtual Safety Car.
"""

from __future__ import annotations

import statistics
from typing import Any

from backend.app.services.preprocessing import _extract_sc_laps, _extract_vsc_laps, _round


def _compute_race_wide_baseline(
    driver_laps_map: dict[str, list[dict]],
    neutralized_laps: set[int],
    all_pit_adjacent: set[int],
) -> float | None:
    """Compute a race-wide median clean pace from all drivers.

    Used as a fallback when a specific driver has too few clean laps
    for a reliable individual baseline.
    """
    all_clean: list[float] = []
    for drv_laps in driver_laps_map.values():
        for lap in drv_laps:
            lap_num = lap.get("lap", 0)
            time_s = lap.get("time_s")
            if lap_num <= 1 or time_s is None:
                continue
            if lap_num in neutralized_laps:
                continue
            if lap_num in all_pit_adjacent:
                continue
            if lap.get("is_accurate") is False:
                continue
            all_clean.append(time_s)
    if all_clean:
        return statistics.median(all_clean)
    return None


# Typical pit lane time loss (seconds) used as a last-resort fallback
# when neither baseline nor lap times are available.  Covers the
# stationary time (~2-3s) plus pit lane speed-limit delta (~20s).
_FALLBACK_PIT_LOSS_S = 22.0

# A lap this many times longer than the driver's clean pace can only be a
# lap that carries a red-flag suspension (Mexico 2026 lap 45: 2278s).
_SUSPENDED_LAP_FACTOR = 3.0


def _extract_red_flag_laps(race_control_data: dict) -> list[int]:
    """Leader lap numbers on which race control showed a red flag."""
    laps: set[int] = set()
    for msg in race_control_data.get("messages", []) or []:
        text = (msg.get("message") or "").upper()
        flag = (msg.get("flag") or "").upper()
        if flag == "RED" or text.startswith("RED FLAG"):
            lap = msg.get("lap")
            if isinstance(lap, int):
                laps.add(lap)
    return sorted(laps)


def _tyres_changed(before: dict | None, after: dict | None) -> bool:
    """True if the compound changes or tyre age resets between two laps."""
    if not before or not after:
        return False
    if before.get("compound") and after.get("compound") and before["compound"] != after["compound"]:
        return True
    age_b, age_a = before.get("tire_age"), after.get("tire_age")
    return age_b is not None and age_a is not None and age_a < age_b


def _is_red_flag_pit(
    pit_lap: int,
    lap_by_number: dict[int, dict],
    red_flag_laps: list[int],
    suspended_laps: set[int],
) -> bool:
    """True if a pit_laps entry is the red-flag pit-lane entry, not a stop.

    During a suspension every car is sent down the pit lane, so the feed
    records a "pit" for the whole field (Monza 2026 lap 3, Mexico 2026
    lap 45). Such an entry is not a pit stop and carries no pit loss.
    A lap "holds the suspension" if its time is >= 3x clean pace
    (Mexico 2026: 2278s) or, next to the red-flag lap, it is untimed
    (FastF1 leaves suspended laps without a time).

    - On the red-flag lap itself: always the pit-lane entry.
    - Out-lap holds the suspension: the car entered the pit lane and the
      race was stopped (lapped cars see this one lap earlier, PER lap 44).
    - In-lap holds the suspension: before the red-flag lap it is still the
      pit-lane entry; after it, it is a real stop at the restart only if
      the tyres changed (Hungary 2021 lap 3, everyone to slicks).
    """
    if not red_flag_laps:
        return False

    def holds_suspension(lap_num: int) -> bool:
        if lap_num in suspended_laps:
            return True
        lap = lap_by_number.get(lap_num)
        near = any(rf - 1 <= lap_num <= rf + 1 for rf in red_flag_laps)
        return near and (lap is None or lap.get("time_s") is None)

    if pit_lap in red_flag_laps:
        return True
    if holds_suspension(pit_lap + 1):
        return True
    if holds_suspension(pit_lap):
        if any(pit_lap <= rf for rf in red_flag_laps if rf - 1 <= pit_lap):
            return True
        return not _tyres_changed(lap_by_number.get(pit_lap), lap_by_number.get(pit_lap + 1))
    return False


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
       - SC/VSC laps and red-flag laps (the red-flag lap and the one after)
       - Pit laps and the lap immediately after each pit (pit_lap + 1)
    4. Median clean pace becomes the baseline.
       Falls back to race-wide median, then a fixed estimate (~22s).
    5. Drop red-flag pit-lane entries (see _is_red_flag_pit): they are
       not stops and their laps hold the suspension time.
    6. Time loss per pit = lap[pit_lap].time_s + lap[pit_lap+1].time_s - 2 * baseline.
       A lap already charged to the previous stop is not charged again
       (back-to-back pit laps), so no lap counts twice.
    7. Track compound changes and SC/VSC status for each stop.

    Returns:
        {"drivers": [DriverPitStats, ...]} sorted by total_time_lost_s descending.
    """
    vsc_laps = set(_extract_vsc_laps(race_control_data))
    sc_laps = set(_extract_sc_laps(race_control_data))
    red_flag_laps = _extract_red_flag_laps(race_control_data)
    red_flag_window = {lap for rf in red_flag_laps for lap in (rf, rf + 1)}
    neutralized_laps = vsc_laps | sc_laps
    # Laps excluded from every pace baseline
    baseline_excluded = neutralized_laps | red_flag_window

    # Build per-driver lap lookup from laps_data.
    # laps_data format: {"drivers": [...], "teams": {...}, "laps": {"VER": [{...}], ...}}
    driver_laps_map: dict[str, list[dict]] = {}
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        for drv, drv_laps in laps_data["laps"].items():
            driver_laps_map[drv] = drv_laps if isinstance(drv_laps, list) else []

    # Collect all pit-adjacent laps across all drivers for race-wide baseline
    all_pit_adjacent: set[int] = set()
    strategy_drivers = strategy_data.get("drivers", [])
    for driver_entry in strategy_drivers:
        for pl in driver_entry.get("pit_laps", []):
            all_pit_adjacent.add(pl)
            all_pit_adjacent.add(pl + 1)

    # Compute race-wide baseline once (used as fallback)
    race_wide_baseline = _compute_race_wide_baseline(
        driver_laps_map, baseline_excluded, all_pit_adjacent
    )

    # Process each driver from strategy data
    results: list[dict[str, Any]] = []

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
            if lap_num in baseline_excluded:
                continue
            if lap_num in pit_adjacent:
                continue
            if lap.get("is_accurate") is False:
                continue

            clean_times.append(time_s)

        # Compute baseline median clean pace with fallback chain:
        # 1. Driver-specific median (needs >= 3 clean laps for reliability)
        # 2. Race-wide median from all drivers
        # 3. None (will use fixed fallback per-stop)
        baseline: float | None = None
        baseline_is_fallback = False
        if len(clean_times) >= 3:
            baseline = statistics.median(clean_times)
        elif race_wide_baseline is not None:
            baseline = race_wide_baseline
            baseline_is_fallback = True
        elif clean_times:
            # Fewer than 3 driver-specific laps but no race-wide data either;
            # use what we have (better than nothing).
            baseline = statistics.median(clean_times)
            baseline_is_fallback = True

        # Laps that hold a red-flag suspension for this driver
        suspended_laps: set[int] = set()
        pace_ref = baseline if baseline is not None else race_wide_baseline
        if red_flag_laps and pace_ref:
            for lap_num, lap in lap_by_number.items():
                near = any(rf - 1 <= lap_num <= rf + 2 for rf in red_flag_laps)
                t = lap.get("time_s")
                if near and t is not None and t >= _SUSPENDED_LAP_FACTOR * pace_ref:
                    suspended_laps.add(lap_num)

        real_pit_laps = [
            pl for pl in pit_laps_list
            if not _is_red_flag_pit(pl, lap_by_number, red_flag_laps, suspended_laps)
        ]

        # Compute time loss per pit stop
        pit_details: list[dict[str, Any]] = []
        total_loss = 0.0
        charged_laps: set[int] = set()

        for pl in real_pit_laps:
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

            # Compute time loss with fallback chain
            time_loss: float
            estimated = False

            pit_time = pit_lap_data.get("time_s") if pit_lap_data else None
            out_time = out_lap_data.get("time_s") if out_lap_data else None
            # Back-to-back pit laps: the in-lap of this stop is the out-lap
            # of the previous one and is already charged there.
            in_lap_charged = pl in charged_laps
            if in_lap_charged:
                pit_time = None
            charged_laps.update((pl, pl + 1))

            if baseline is not None and pit_time is not None and out_time is not None:
                # Normal case: both pit lap and out lap available
                time_loss = _round(pit_time + out_time - 2 * baseline)
            elif baseline is not None and pit_time is not None and out_time is None:
                # Pit on last lap or missing out lap - single lap estimate
                time_loss = _round(pit_time - baseline)
                estimated = True
            elif baseline is not None and pit_time is None and out_time is not None:
                # Missing pit lap time (e.g., lap 1 pit) - single lap estimate
                time_loss = _round(out_time - baseline)
                estimated = True
            elif in_lap_charged:
                # Back-to-back stop whose only new lap is untimed: its loss
                # is already in the previous stop's figure.
                time_loss = 0.0
                estimated = True
            else:
                # No baseline or no lap times at all - use fixed fallback
                time_loss = _FALLBACK_PIT_LOSS_S
                estimated = True

            total_loss += time_loss

            pit_details.append({
                "lap": pl,
                "time_loss_s": time_loss,
                "compound_from": compound_from,
                "compound_to": compound_to,
                "under_sc": under_sc,
                "estimated": estimated or baseline_is_fallback,
            })

        results.append({
            "driver": driver_code,
            "team": team,
            "pits": pit_details,
            "total_time_lost_s": _round(total_loss),
            "num_stops": len(real_pit_laps),
        })

    # Sort by total_time_lost_s descending
    results.sort(key=lambda d: d["total_time_lost_s"] or 0.0, reverse=True)

    return {"drivers": results}
