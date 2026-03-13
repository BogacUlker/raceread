"""Descriptor detection rules for annotation generation.

Detects noteworthy events in race data that warrant annotations.
This module handles DETECTION only - Claude API generation comes later.

6 detection rules:
1. Pace anomaly: lap delta > 0.5s from rolling 3-lap average
2. Energy shift: deploy/clip > 2x change between laps AND absolute > 1.5%
3. SC/VSC event: race control SafetyCar category
4. Pit stop: PitInTime not null
5. Position change: delta > 2 between consecutive laps
6. Fastest lap: best of all drivers
"""

from __future__ import annotations

from typing import Any

from backend.app.config import (
    ENERGY_SHIFT_ABSOLUTE,
    ENERGY_SHIFT_RATIO,
    PACE_ANOMALY_DELTA,
    POSITION_CHANGE_THRESHOLD,
)


def detect_pace_anomalies(
    driver: str,
    laps: list[dict],
) -> list[dict]:
    """Detect laps where pace deviates significantly from rolling average.

    Rule: lap time delta > 0.5s from rolling 3-lap average.
    """
    events: list[dict] = []
    valid_times: list[tuple[int, float]] = []

    for lap in laps:
        time_s = lap.get("time_s")
        lap_num = lap.get("lap", 0)
        if time_s is None or lap_num <= 1:
            continue
        valid_times.append((lap_num, time_s))

    for i, (lap_num, time_s) in enumerate(valid_times):
        if i < 3:
            continue

        # Rolling 3-lap average from previous 3 laps
        window = [t for _, t in valid_times[i - 3 : i]]
        avg = sum(window) / len(window)
        delta = time_s - avg

        if abs(delta) > PACE_ANOMALY_DELTA:
            direction = "slower" if delta > 0 else "faster"
            events.append({
                "driver": driver,
                "lap": lap_num,
                "chart_type": "pace",
                "category": "pace_anomaly",
                "severity": "high" if abs(delta) > 1.0 else "medium",
                "detail": {
                    "delta": round(delta, 3),
                    "lap_time": round(time_s, 3),
                    "rolling_avg": round(avg, 3),
                    "direction": direction,
                },
            })

    return events


def detect_energy_shifts(
    driver: str,
    energy_laps: list[dict],
) -> list[dict]:
    """Detect significant energy state shifts between consecutive laps.

    Rule: deploy or clip % changes > 2x between laps AND absolute change > 1.5%.
    Both ratio AND absolute thresholds must be met to avoid false positives
    from low baselines (e.g. 0.5% -> 1.2% = 2.4x but meaningless).
    """
    events: list[dict] = []

    for i in range(1, len(energy_laps)):
        prev = energy_laps[i - 1]
        curr = energy_laps[i]
        lap_num = curr.get("lap", 0)

        for field, label in [("deploy_pct", "deploy"), ("clip_pct", "clip")]:
            prev_val = prev.get(field, 0.0)
            curr_val = curr.get(field, 0.0)
            abs_change = abs(curr_val - prev_val)

            # Check absolute threshold first
            if abs_change < ENERGY_SHIFT_ABSOLUTE:
                continue

            # Check ratio threshold (avoid division by zero)
            if prev_val > 0.01:
                ratio = curr_val / prev_val
            elif curr_val > 0.01:
                ratio = ENERGY_SHIFT_RATIO + 1  # treat zero->nonzero as significant
            else:
                continue

            if ratio >= ENERGY_SHIFT_RATIO or (prev_val > 0.01 and ratio <= 1.0 / ENERGY_SHIFT_RATIO):
                direction = "increase" if curr_val > prev_val else "decrease"
                events.append({
                    "driver": driver,
                    "lap": lap_num,
                    "chart_type": "energy",
                    "category": "energy_shift",
                    "severity": "high" if abs_change > 3.0 else "medium",
                    "detail": {
                        "field": label,
                        "prev_value": round(prev_val, 2),
                        "curr_value": round(curr_val, 2),
                        "abs_change": round(abs_change, 2),
                        "ratio": round(ratio, 2) if ratio < 100 else "inf",
                        "direction": direction,
                    },
                })

    return events


def detect_safety_car_events(
    race_control: dict,
) -> list[dict]:
    """Detect SC/VSC events from race control messages.

    Rule: race control message with SafetyCar category.
    """
    events: list[dict] = []

    for msg in race_control.get("messages", []):
        category = str(msg.get("category") or "").lower().replace(" ", "")
        if "safetycar" not in category:
            continue

        message_text = str(msg.get("message") or "")
        lap = msg.get("lap")
        if lap is None:
            continue

        is_vsc = "VIRTUAL" in message_text.upper()
        sc_type = "VSC" if is_vsc else "SC"

        events.append({
            "driver": "ALL",
            "lap": int(lap),
            "chart_type": "pace",
            "category": "safety_car",
            "severity": "high",
            "detail": {
                "type": sc_type,
                "message": message_text,
            },
        })

    return events


def detect_pit_stops(
    driver: str,
    laps: list[dict],
) -> list[dict]:
    """Detect pit stop laps.

    Rule: PitInTime is not null.
    """
    events: list[dict] = []

    for lap in laps:
        pit_in = lap.get("pit_in_time") or lap.get("PitInTime")
        if pit_in is None:
            continue

        lap_num = lap.get("lap", 0)
        compound = lap.get("compound")

        events.append({
            "driver": driver,
            "lap": lap_num,
            "chart_type": "strategy",
            "category": "pit_stop",
            "severity": "low",
            "detail": {
                "compound_before": compound,
            },
        })

    return events


def detect_position_changes(
    driver: str,
    laps: list[dict],
) -> list[dict]:
    """Detect significant position changes between consecutive laps.

    Rule: position delta > 2 between laps.
    """
    events: list[dict] = []

    prev_position = None
    for lap in laps:
        lap_num = lap.get("lap", 0)
        position = lap.get("position")

        if position is None:
            prev_position = position
            continue

        if prev_position is not None:
            delta = prev_position - position  # positive = gained positions
            if abs(delta) > POSITION_CHANGE_THRESHOLD:
                direction = "gained" if delta > 0 else "lost"
                events.append({
                    "driver": driver,
                    "lap": lap_num,
                    "chart_type": "pace",
                    "category": "position_change",
                    "severity": "high" if abs(delta) > 4 else "medium",
                    "detail": {
                        "positions": abs(int(delta)),
                        "direction": direction,
                        "from_position": int(prev_position),
                        "to_position": int(position),
                    },
                })

        prev_position = position

    return events


def detect_fastest_lap(
    laps_data: dict,
) -> list[dict]:
    """Detect the overall fastest lap of the race.

    Rule: best lap time across all drivers.
    """
    best_time = float("inf")
    best_driver = None
    best_lap_num = 0

    # Handle our laps.json format: {"drivers": [...], "teams": {...}, "laps": {"RUS": [...], ...}}
    laps_dict: dict[str, list[dict]] = {}
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        laps_dict = laps_data["laps"]
    elif isinstance(laps_data, dict):
        laps_dict = {k: v for k, v in laps_data.items() if isinstance(v, list)}

    for driver, driver_laps in laps_dict.items():
        for lap in driver_laps:
            time_s = lap.get("time_s")
            lap_num = lap.get("lap", 0)
            is_accurate = lap.get("is_accurate", True)

            if time_s is None or lap_num <= 1 or is_accurate is False:
                continue

            if time_s < best_time:
                best_time = time_s
                best_driver = driver
                best_lap_num = lap_num

    if best_driver is None:
        return []

    return [{
        "driver": best_driver,
        "lap": best_lap_num,
        "chart_type": "pace",
        "category": "fastest_lap",
        "severity": "low",
        "detail": {
            "time_s": round(best_time, 3),
        },
    }]


def detect_all_events(
    laps_data: dict,
    energy_data: dict[str, dict],
    race_control: dict,
) -> list[dict[str, Any]]:
    """Run all detection rules and return combined events.

    Args:
        laps_data: Full laps.json content
        energy_data: Dict of driver -> energy data (from load_all_energy)
        race_control: race_control.json content

    Returns:
        List of detected events sorted by (lap, driver).
    """
    all_events: list[dict] = []

    # Safety car events (applies to all drivers)
    all_events.extend(detect_safety_car_events(race_control))

    # Fastest lap (cross-driver)
    all_events.extend(detect_fastest_lap(laps_data))

    # Per-driver laps from laps_data
    laps_dict: dict[str, list[dict]] = {}
    if isinstance(laps_data, dict) and "laps" in laps_data and isinstance(laps_data["laps"], dict):
        laps_dict = laps_data["laps"]

    for driver, driver_laps in laps_dict.items():
        if not driver_laps:
            continue

        all_events.extend(detect_pace_anomalies(driver, driver_laps))
        all_events.extend(detect_pit_stops(driver, driver_laps))
        all_events.extend(detect_position_changes(driver, driver_laps))

    # Per-driver energy data
    for driver, energy in energy_data.items():
        energy_laps = energy.get("laps", [])
        if energy_laps:
            all_events.extend(detect_energy_shifts(driver, energy_laps))

    # Sort by lap number, then driver
    all_events.sort(key=lambda e: (e.get("lap", 0), e.get("driver", "")))

    return all_events
