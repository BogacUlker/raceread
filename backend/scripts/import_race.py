"""
RaceRead data import pipeline.

Downloads F1 race data via FastF1 and exports structured JSON files
for the RaceRead backend API. Includes energy inference per driver.

Usage:
    From project root (as module):
        python -m backend.scripts.import_race --year 2026 --event "Australian Grand Prix"

    Direct execution:
        python backend/scripts/import_race.py --year 2026 --event "Australian Grand Prix"

    Energy-only re-run:
        python -m backend.scripts.import_race --year 2026 --event "Australian Grand Prix" --energy-only
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import fastf1
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Path setup - ensure project root is on sys.path for both execution modes
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.config import DATA_DIR, FASTF1_CACHE_DIR, MIN_LAPS_THRESHOLD

# Energy inference imports (needed for telemetry export)
try:
    from backend.app.services.energy_inference import (
        EnergyState,
        EnergyThresholds,
        build_ice_baseline,
        classify_samples,
        _prepare_telemetry,
    )
    _HAS_ENERGY = True
except ImportError:
    _HAS_ENERGY = False


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------

def _clean_value(val: Any) -> Any:
    """Convert pandas/numpy types to JSON-safe Python types.

    - NaN, NaT, None -> None
    - Timedelta -> float seconds
    - numpy int/float -> Python int/float
    - numpy bool -> Python bool
    """
    if val is None:
        return None
    if isinstance(val, pd.Timedelta):
        if pd.isna(val):
            return None
        return round(val.total_seconds(), 3)
    if isinstance(val, pd.Timestamp):
        if pd.isna(val):
            return None
        return val.isoformat()
    if isinstance(val, (np.floating, float)):
        if math.isnan(val) or math.isinf(val):
            return None
        return round(float(val), 3)
    if isinstance(val, np.integer):
        return int(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, np.ndarray):
        return [_clean_value(v) for v in val.tolist()]
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _write_json(path: Path, data: Any) -> None:
    """Write data to a JSON file with consistent formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    print(f"  -> wrote {path}")


# ---------------------------------------------------------------------------
# Event slug derivation
# ---------------------------------------------------------------------------

# Common GP name patterns: "Australian Grand Prix" -> "australia"
# "Chinese Grand Prix" -> "china", "Japanese Grand Prix" -> "japan"
# Also handle special cases like "Emilia Romagna Grand Prix" -> "emilia-romagna"
_COUNTRY_OVERRIDES = {
    "australian": "australia",
    "chinese": "china",
    "japanese": "japan",
    "british": "great-britain",
    "spanish": "spain",
    "belgian": "belgium",
    "italian": "italy",
    "hungarian": "hungary",
    "dutch": "netherlands",
    "mexican": "mexico",
    "brazilian": "brazil",
    "canadian": "canada",
    "bahrain": "bahrain",
    "saudi arabian": "saudi-arabia",
    "emilia romagna": "emilia-romagna",
    "las vegas": "las-vegas",
    "abu dhabi": "abu-dhabi",
    "united states": "usa",
    "great britain": "great-britain",
    "sao paulo": "sao-paulo",
    "monaco": "monaco",
    "singapore": "singapore",
    "qatar": "qatar",
    "austrian": "austria",
    "azerbaijan": "azerbaijan",
    "miami": "miami",
}


def _derive_event_slug(event_name: str) -> str:
    """Derive a filesystem-safe slug from the Grand Prix name.

    Takes the country/location portion of the event name (everything before
    'Grand Prix') and converts it to a lowercase slug.
    """
    name = event_name.strip()

    # Remove "Grand Prix" suffix (case insensitive)
    cleaned = re.sub(r"\s*grand\s*prix\s*$", "", name, flags=re.IGNORECASE).strip()

    # Check overrides first
    lower_cleaned = cleaned.lower()
    for pattern, slug in _COUNTRY_OVERRIDES.items():
        if lower_cleaned == pattern:
            return slug

    # Default: take the full cleaned name, lowercase, replace spaces with hyphens
    slug = re.sub(r"\s+", "-", lower_cleaned)
    # Remove non-alphanumeric except hyphens
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    return slug


# ---------------------------------------------------------------------------
# Driver info collection
# ---------------------------------------------------------------------------

def _collect_driver_info(session: fastf1.core.Session) -> dict:
    """Gather driver metadata and classify as valid or DNS.

    Returns a dict with:
        drivers_valid: list of driver abbreviations with >= MIN_LAPS_THRESHOLD laps
        drivers_dns: list of driver abbreviations with < MIN_LAPS_THRESHOLD laps
        drivers_all: list of all driver abbreviations
        teams: dict mapping driver abbreviation to team name
        inaccurate_drivers: list of drivers where all laps have IsAccurate == False
    """
    laps = session.laps
    all_drivers = sorted(laps["Driver"].unique().tolist())

    drivers_valid = []
    drivers_dns = []
    inaccurate_drivers = []
    teams: dict[str, str] = {}

    for drv in all_drivers:
        drv_laps = laps.pick_drivers(drv)
        lap_count = len(drv_laps)

        # Get team name
        team_series = drv_laps["Team"].dropna()
        team_name = team_series.iloc[0] if len(team_series) > 0 else "Unknown"
        teams[drv] = team_name

        if lap_count < MIN_LAPS_THRESHOLD:
            drivers_dns.append(drv)
            print(f"  [SKIP] {drv} ({team_name}): {lap_count} laps (DNS/DNF early)")
            continue

        # Check if all laps are inaccurate
        accurate_col = drv_laps["IsAccurate"]
        if accurate_col.notna().any() and not accurate_col.any():
            inaccurate_drivers.append(drv)
            print(f"  [WARN] {drv} ({team_name}): all {lap_count} laps marked IsAccurate=False")

        drivers_valid.append(drv)

    return {
        "drivers_valid": drivers_valid,
        "drivers_dns": drivers_dns,
        "drivers_all": all_drivers,
        "teams": teams,
        "inaccurate_drivers": inaccurate_drivers,
    }


# ---------------------------------------------------------------------------
# 1. Race info export
# ---------------------------------------------------------------------------

def export_race_info(
    session: fastf1.core.Session,
    event: fastf1.events.Event,
    race_id: str,
    output_dir: Path,
) -> dict:
    """Export race_info.json and return the race info dict."""
    laps = session.laps

    # Find winner: driver with Position == 1 on the last recorded lap
    last_lap_num = laps["LapNumber"].max()
    last_lap_data = laps[laps["LapNumber"] == last_lap_num]

    winner = "N/A"
    pos1 = last_lap_data[last_lap_data["Position"] == 1.0]
    if len(pos1) > 0:
        winner = pos1.iloc[0]["Driver"]

    # Race date
    race_date = None
    if hasattr(event, "EventDate"):
        race_date = str(event["EventDate"].date()) if pd.notna(event["EventDate"]) else None
    if race_date is None and hasattr(session, "date"):
        race_date = str(session.date.date()) if session.date else None

    # Event name
    event_name = str(event["EventName"]) if "EventName" in event.index else str(event)

    # Circuit name: prefer Location from event, fallback to Country
    circuit = "Unknown"
    if "Location" in event.index and pd.notna(event["Location"]):
        circuit = str(event["Location"])
    elif "Country" in event.index and pd.notna(event["Country"]):
        circuit = str(event["Country"])

    race_info = {
        "id": race_id,
        "name": event_name,
        "date": race_date,
        "circuit": circuit,
        "winner": winner,
        "total_laps": int(last_lap_num),
    }

    _write_json(output_dir / "race_info.json", race_info)
    return race_info


# ---------------------------------------------------------------------------
# 2. Laps export
# ---------------------------------------------------------------------------

def export_laps(
    session: fastf1.core.Session,
    drivers_info: dict,
    output_dir: Path,
) -> None:
    """Export laps.json with all drivers keyed by abbreviation."""
    laps = session.laps
    all_drivers = drivers_info["drivers_all"]
    teams = drivers_info["teams"]

    laps_by_driver: dict[str, list[dict]] = {}

    for drv in all_drivers:
        drv_laps = laps.pick_drivers(drv).sort_values("LapNumber")

        if drv in drivers_info["drivers_dns"]:
            laps_by_driver[drv] = []
            continue

        lap_records = []
        for _, row in drv_laps.iterrows():
            record = {
                "lap": int(row["LapNumber"]),
                "time_s": _clean_value(row.get("LapTime")),
                "s1": _clean_value(row.get("Sector1Time")),
                "s2": _clean_value(row.get("Sector2Time")),
                "s3": _clean_value(row.get("Sector3Time")),
                "compound": _clean_value(row.get("Compound")),
                "tire_age": _clean_value(row.get("TyreLife")),
                "position": _clean_value(row.get("Position")),
                "track_status": _clean_value(row.get("TrackStatus")),
                "is_personal_best": _clean_value(row.get("IsPersonalBest")),
                "speed_i1": _clean_value(row.get("SpeedI1")),
                "speed_i2": _clean_value(row.get("SpeedI2")),
                "speed_fl": _clean_value(row.get("SpeedFL")),
                "speed_st": _clean_value(row.get("SpeedST")),
                "is_accurate": _clean_value(row.get("IsAccurate")),
            }
            # Convert position to int if present
            if record["position"] is not None:
                record["position"] = int(record["position"])
            if record["tire_age"] is not None:
                record["tire_age"] = int(record["tire_age"])

            lap_records.append(record)

        laps_by_driver[drv] = lap_records

    output = {
        "drivers": all_drivers,
        "teams": teams,
        "laps": laps_by_driver,
    }

    _write_json(output_dir / "laps.json", output)


# ---------------------------------------------------------------------------
# 3. Strategy export
# ---------------------------------------------------------------------------

def export_strategy(
    session: fastf1.core.Session,
    drivers_info: dict,
    output_dir: Path,
) -> None:
    """Export strategy.json with stint and pit stop data per driver."""
    laps = session.laps
    valid_drivers = drivers_info["drivers_valid"]
    teams = drivers_info["teams"]

    strategy_entries = []

    for drv in sorted(valid_drivers):
        drv_laps = laps.pick_drivers(drv).sort_values("LapNumber")

        # Detect pit laps: laps where PitInTime is not null
        pit_laps = []
        for _, row in drv_laps.iterrows():
            pit_in = row.get("PitInTime")
            if pit_in is not None and pd.notna(pit_in):
                pit_laps.append(int(row["LapNumber"]))

        # Build stints from Compound and Stint columns
        stints = []
        current_stint_num = None
        current_compound = None
        stint_start = None

        for _, row in drv_laps.iterrows():
            lap_num = int(row["LapNumber"])
            compound = _clean_value(row.get("Compound"))
            stint_col = row.get("Stint")
            stint_num = int(stint_col) if pd.notna(stint_col) else None

            # Detect stint change via the Stint column or compound change
            is_new_stint = False
            if stint_num is not None and stint_num != current_stint_num:
                is_new_stint = True
            elif stint_num is None and compound != current_compound and compound is not None:
                is_new_stint = True

            if is_new_stint:
                # Close previous stint
                if current_compound is not None and stint_start is not None:
                    prev_lap = lap_num - 1
                    stints.append({
                        "compound": current_compound,
                        "start_lap": stint_start,
                        "end_lap": prev_lap,
                        "laps": prev_lap - stint_start + 1,
                    })

                current_stint_num = stint_num
                current_compound = compound
                stint_start = lap_num

        # Close the final stint
        if current_compound is not None and stint_start is not None:
            last_lap = int(drv_laps["LapNumber"].max())
            stints.append({
                "compound": current_compound,
                "start_lap": stint_start,
                "end_lap": last_lap,
                "laps": last_lap - stint_start + 1,
            })

        strategy_entries.append({
            "driver": drv,
            "team": teams.get(drv, "Unknown"),
            "stints": stints,
            "pit_laps": pit_laps,
        })

    output = {"drivers": strategy_entries}
    _write_json(output_dir / "strategy.json", output)


# ---------------------------------------------------------------------------
# 4. Race control export
# ---------------------------------------------------------------------------

def export_race_control(
    session: fastf1.core.Session,
    output_dir: Path,
) -> dict[str, list[int]]:
    """Export race_control.json and return VSC/SC lap ranges.

    Returns dict with 'vsc_laps' and 'sc_laps' lists.
    """
    rc_messages_raw = session.race_control_messages

    messages = []
    for _, row in rc_messages_raw.iterrows():
        msg = {
            "time": _clean_value(row.get("Time")),
            "category": _clean_value(row.get("Category")),
            "message": _clean_value(row.get("Message")),
            "status": _clean_value(row.get("Status")),
            "flag": _clean_value(row.get("Flag")),
            "scope": _clean_value(row.get("Scope")),
            "sector": _clean_value(row.get("Sector")),
            "racing_number": _clean_value(row.get("RacingNumber")),
            "lap": _clean_value(row.get("Lap")),
        }
        if msg["lap"] is not None:
            msg["lap"] = int(msg["lap"])
        messages.append(msg)

    # Detect VSC and SC lap ranges from race control messages
    # VSC: SafetyCar category with VIRTUAL SAFETY CAR DEPLOYED / ENDING
    # SC: SafetyCar category with SAFETY CAR DEPLOYED / ENDING (not virtual)
    # Also use TrackStatus from lap data: "4" = SC, "6" = VSC (can be composite like "46")

    vsc_laps: set[int] = set()
    sc_laps: set[int] = set()

    # Method 1: Parse race control messages for SC/VSC deploy/ending pairs
    sc_deploy_lap = None
    vsc_deploy_lap = None

    for msg in messages:
        category = str(msg.get("category") or "").lower()
        message_text = str(msg.get("message") or "").upper()
        lap = msg.get("lap")

        if "safetycar" in category.replace(" ", ""):
            is_virtual = "VIRTUAL" in message_text or "VSC" in message_text
            if is_virtual and "DEPLOYED" in message_text:
                vsc_deploy_lap = lap
            elif is_virtual and "ENDING" in message_text:
                if vsc_deploy_lap is not None and lap is not None:
                    for lp in range(vsc_deploy_lap, lap + 1):
                        vsc_laps.add(lp)
                    vsc_deploy_lap = None
            elif "DEPLOYED" in message_text and not is_virtual:
                sc_deploy_lap = lap
            elif "ENDING" in message_text and not is_virtual:
                if sc_deploy_lap is not None and lap is not None:
                    for lp in range(sc_deploy_lap, lap + 1):
                        sc_laps.add(lp)
                    sc_deploy_lap = None

    # Method 2: Cross-validate with TrackStatus from lap data
    # TrackStatus can be composite strings; "4" means SC, "6" means VSC
    laps_df = session.laps
    for _, row in laps_df.iterrows():
        track_status = str(row.get("TrackStatus") or "")
        lap_num = row.get("LapNumber")
        if pd.isna(lap_num):
            continue
        lap_num = int(lap_num)

        if "6" in track_status:
            vsc_laps.add(lap_num)
        if "4" in track_status:
            sc_laps.add(lap_num)

    vsc_laps_sorted = sorted(vsc_laps)
    sc_laps_sorted = sorted(sc_laps)

    output = {
        "messages": messages,
        "vsc_laps": vsc_laps_sorted,
        "sc_laps": sc_laps_sorted,
    }

    _write_json(output_dir / "race_control.json", output)

    return {"vsc_laps": vsc_laps_sorted, "sc_laps": sc_laps_sorted}


# ---------------------------------------------------------------------------
# 5. Weather export
# ---------------------------------------------------------------------------

def export_weather(
    session: fastf1.core.Session,
    output_dir: Path,
) -> None:
    """Export weather.json with time-series weather samples."""
    weather = session.weather_data

    if weather is None or len(weather) == 0:
        _write_json(output_dir / "weather.json", {"samples": []})
        return

    samples = []
    for _, row in weather.iterrows():
        # Time field - convert to seconds from session start
        time_val = row.get("Time")
        time_s = _clean_value(time_val)
        if isinstance(time_s, str):
            # If it came out as ISO string, try to parse back
            time_s = None

        sample = {
            "time_s": time_s,
            "air_temp": _clean_value(row.get("AirTemp")),
            "track_temp": _clean_value(row.get("TrackTemp")),
            "humidity": _clean_value(row.get("Humidity")),
            "pressure": _clean_value(row.get("Pressure")),
            "rainfall": bool(row.get("Rainfall")) if pd.notna(row.get("Rainfall")) else None,
            "wind_direction": _clean_value(row.get("WindDirection")),
            "wind_speed": _clean_value(row.get("WindSpeed")),
        }
        samples.append(sample)

    _write_json(output_dir / "weather.json", {"samples": samples})


# ---------------------------------------------------------------------------
# 6a. Telemetry export (per-sample data for speed traces / track maps)
# ---------------------------------------------------------------------------

# Energy state short codes for compact JSON
_ENERGY_SHORT = {
    "DEPLOYING": "D",
    "HARVESTING": "H",
    "CLIPPING": "C",
    "NEUTRAL": "N",
}


def export_telemetry(
    session: fastf1.core.Session,
    drivers_info: dict,
    vsc_laps: list[int],
    output_dir: Path,
    target_samples: int = 150,
) -> None:
    """Export downsampled per-lap telemetry with energy states for each driver.

    Each driver gets a JSON file at data/{race}/telemetry/{driver}.json with
    ~target_samples samples per lap including speed, throttle, brake, gear,
    RPM, X/Y coordinates, gap to driver ahead, and inferred energy state.
    """
    telemetry_dir = output_dir / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    valid_drivers = drivers_info["drivers_valid"]
    teams = drivers_info["teams"]

    for drv in valid_drivers:
        print(f"  Exporting telemetry for {drv}...")
        try:
            drv_laps = session.laps.pick_drivers(drv).sort_values("LapNumber")
            team = teams.get(drv, "Unknown")

            # Collect full telemetry per lap for energy baseline
            all_tel_frames = []
            lap_tel_map: dict[int, pd.DataFrame] = {}

            for _, lap_row in drv_laps.iterrows():
                lap_num = int(lap_row["LapNumber"])
                try:
                    lap_tel = lap_row.get_telemetry()
                    if lap_tel is not None and len(lap_tel) > 0:
                        lap_tel = lap_tel.copy()
                        lap_tel["LapNumber"] = lap_num
                        all_tel_frames.append(lap_tel)
                        lap_tel_map[lap_num] = lap_tel
                except Exception:
                    continue

            if not all_tel_frames:
                print(f"    [WARN] No telemetry for {drv}, skipping")
                continue

            # Build energy baseline from all laps combined
            energy_states_per_lap: dict[int, np.ndarray] = {}
            if _HAS_ENERGY:
                try:
                    combined_tel = pd.concat(all_tel_frames, ignore_index=True)
                    thresholds = EnergyThresholds()
                    prepared = _prepare_telemetry(combined_tel, thresholds)
                    baseline = build_ice_baseline(prepared, thresholds)

                    if baseline:
                        # Classify per lap using the prepared telemetry
                        for lap_num, lap_tel in lap_tel_map.items():
                            lap_prep = _prepare_telemetry(lap_tel, thresholds)
                            states = classify_samples(lap_prep, baseline, thresholds)
                            energy_states_per_lap[lap_num] = states
                except Exception as exc:
                    print(f"    [WARN] Energy classification failed for {drv}: {exc}")

            # Build output per lap with downsampling
            laps_out = []
            total_samples = 0

            for lap_num in sorted(lap_tel_map.keys()):
                lap_tel = lap_tel_map[lap_num]
                n = len(lap_tel)

                if n < 10:
                    continue

                # Downsample via linspace index selection
                if n > target_samples:
                    indices = np.linspace(0, n - 1, target_samples, dtype=int)
                else:
                    indices = np.arange(n)

                samples = []
                energy_states = energy_states_per_lap.get(lap_num)

                for idx in indices:
                    row = lap_tel.iloc[idx]

                    # Distance - prefer Distance column, fall back to 0
                    dist = _clean_value(row.get("Distance"))
                    if dist is not None:
                        dist = round(float(dist), 1)
                    else:
                        dist = 0.0

                    speed = _clean_value(row.get("Speed"))
                    if speed is not None:
                        speed = round(float(speed), 1)

                    throttle = _clean_value(row.get("Throttle"))
                    if throttle is not None:
                        throttle = round(float(throttle), 0)

                    brake = bool(row.get("Brake")) if pd.notna(row.get("Brake")) else False

                    gear = _clean_value(row.get("nGear"))
                    if gear is not None:
                        gear = int(gear)

                    rpm = _clean_value(row.get("RPM"))
                    if rpm is not None:
                        rpm = int(rpm)

                    x = _clean_value(row.get("X"))
                    if x is not None:
                        x = round(float(x), 1)

                    y = _clean_value(row.get("Y"))
                    if y is not None:
                        y = round(float(y), 1)

                    driver_ahead = _clean_value(row.get("DriverAhead"))
                    if driver_ahead is not None:
                        driver_ahead = str(driver_ahead)

                    gap_ahead = _clean_value(row.get("DistanceToDriverAhead"))
                    if gap_ahead is not None:
                        gap_ahead = round(float(gap_ahead), 2)

                    # Energy state short code
                    energy = "N"
                    if energy_states is not None and idx < len(energy_states):
                        energy = _ENERGY_SHORT.get(str(energy_states[idx]), "N")

                    sample = {
                        "dist": dist,
                        "speed": speed,
                        "throttle": throttle,
                        "brake": brake,
                        "gear": gear,
                        "rpm": rpm,
                        "x": x,
                        "y": y,
                        "driver_ahead": driver_ahead,
                        "gap_ahead": gap_ahead,
                        "energy": energy,
                    }
                    samples.append(sample)

                laps_out.append({
                    "lap": lap_num,
                    "samples": samples,
                })
                total_samples += len(samples)

            output = {
                "driver": drv,
                "team": team,
                "laps": laps_out,
            }

            _write_json(telemetry_dir / f"{drv.lower()}.json", output)
            print(f"    {len(laps_out)} laps, {total_samples} total samples")

        except Exception as exc:
            print(f"    [ERROR] Telemetry export failed for {drv}: {exc}")
            import traceback
            traceback.print_exc()
            continue


def export_circuit(
    session: fastf1.core.Session,
    output_dir: Path,
) -> None:
    """Export circuit.json with corner positions and track outline.

    Uses session.get_circuit_info() for corner data and the fastest
    clean lap's telemetry X/Y for the track outline.
    """
    print("  Exporting circuit info...")

    corners_out = []
    outline_out = []
    track_length = 0

    try:
        circuit_info = session.get_circuit_info()

        if circuit_info is not None:
            # Corners
            if hasattr(circuit_info, "corners") and circuit_info.corners is not None:
                for _, corner in circuit_info.corners.iterrows():
                    corners_out.append({
                        "number": int(corner.get("Number", 0)),
                        "x": round(float(corner.get("X", 0)), 1),
                        "y": round(float(corner.get("Y", 0)), 1),
                        "angle": round(float(corner.get("Angle", 0)), 1),
                        "distance": round(float(corner.get("Distance", 0)), 1),
                        "letter": str(corner.get("Letter", "")),
                    })

            # Track length from circuit info or approximate from telemetry
            if hasattr(circuit_info, "circuit_length"):
                track_length = round(float(circuit_info.circuit_length), 0)

    except Exception as exc:
        print(f"    [WARN] Circuit info not available: {exc}")

    # Track outline from fastest lap's X/Y
    try:
        laps = session.laps
        fastest = laps.pick_fastest()
        if fastest is not None:
            tel = fastest.get_telemetry()
            if tel is not None and len(tel) > 0:
                # Downsample outline to ~200 points
                n = len(tel)
                step = max(1, n // 200)
                for i in range(0, n, step):
                    row = tel.iloc[i]
                    x_val = row.get("X")
                    y_val = row.get("Y")
                    if pd.notna(x_val) and pd.notna(y_val):
                        outline_out.append({
                            "x": round(float(x_val), 1),
                            "y": round(float(y_val), 1),
                        })

                # Estimate track length from Distance if not available
                if track_length == 0 and "Distance" in tel.columns:
                    max_dist = tel["Distance"].max()
                    if pd.notna(max_dist):
                        track_length = round(float(max_dist), 0)
    except Exception as exc:
        print(f"    [WARN] Could not extract track outline: {exc}")

    output = {
        "corners": corners_out,
        "outline": outline_out,
        "track_length": int(track_length),
    }

    _write_json(output_dir / "circuit.json", output)
    print(f"    {len(corners_out)} corners, {len(outline_out)} outline points")


# ---------------------------------------------------------------------------
# 6. Energy inference export
# ---------------------------------------------------------------------------

def export_energy(
    session: fastf1.core.Session,
    drivers_info: dict,
    vsc_laps: list[int],
    output_dir: Path,
) -> None:
    """Export energy/{driver}.json for each valid driver.

    Imports and calls the energy inference engine. If the engine module
    is not yet available, prints a warning and skips.
    """
    try:
        from backend.app.services.energy_inference import infer_energy_states
    except ImportError as exc:
        print(f"  [WARN] Cannot import energy inference engine: {exc}")
        print("  [WARN] Skipping energy export. Implement backend.app.services.energy_inference first.")
        return

    energy_dir = output_dir / "energy"
    energy_dir.mkdir(parents=True, exist_ok=True)

    valid_drivers = drivers_info["drivers_valid"]
    teams = drivers_info["teams"]

    for drv in valid_drivers:
        print(f"  Processing energy for {drv}...")
        try:
            drv_laps = session.laps.pick_drivers(drv)

            # Build combined telemetry with LapNumber column
            # get_telemetry() on multi-lap doesn't include LapNumber,
            # so we iterate per lap and concatenate
            telemetry_frames = []
            for _, lap_row in drv_laps.iterrows():
                lap_num = int(lap_row["LapNumber"])
                try:
                    lap_tel = lap_row.get_telemetry()
                    if lap_tel is not None and len(lap_tel) > 0:
                        lap_tel = lap_tel.copy()
                        lap_tel["LapNumber"] = lap_num
                        telemetry_frames.append(lap_tel)
                except Exception:
                    continue

            if not telemetry_frames:
                print(f"    [WARN] No telemetry for {drv}, skipping energy export")
                continue

            telemetry = pd.concat(telemetry_frames, ignore_index=True)
            print(f"    {len(telemetry)} telemetry samples, {len(telemetry_frames)} laps")

            team = teams.get(drv, "Unknown")
            energy_result = infer_energy_states(
                telemetry_df=telemetry,
                driver=drv,
                team=team,
                vsc_laps=vsc_laps,
            )

            _write_json(energy_dir / f"{drv.lower()}.json", energy_result)

        except Exception as exc:
            print(f"    [ERROR] Energy inference failed for {drv}: {exc}")
            import traceback
            traceback.print_exc()
            continue


# ---------------------------------------------------------------------------
# 7. Race registry update
# ---------------------------------------------------------------------------

def update_race_registry(race_info: dict, data_dir: Path) -> None:
    """Append race to data/races.json if not already present."""
    registry_path = data_dir / "races.json"

    races: list[dict] = []
    if registry_path.exists():
        with open(registry_path, "r", encoding="utf-8") as f:
            try:
                races = json.load(f)
            except json.JSONDecodeError:
                print("  [WARN] races.json is corrupted, creating fresh registry")
                races = []

    # Check if race already registered
    existing_ids = {r.get("id") for r in races}
    if race_info["id"] in existing_ids:
        print(f"  Race {race_info['id']} already in registry, updating entry")
        races = [r for r in races if r.get("id") != race_info["id"]]

    races.append({
        "id": race_info["id"],
        "name": race_info["name"],
        "date": race_info["date"],
        "circuit": race_info["circuit"],
        "winner": race_info["winner"],
        "total_laps": race_info["total_laps"],
    })

    # Sort by date
    races.sort(key=lambda r: r.get("date") or "")

    _write_json(registry_path, races)


# ---------------------------------------------------------------------------
# 8. Annotations placeholder
# ---------------------------------------------------------------------------

def export_annotations_placeholder(output_dir: Path) -> None:
    """Write an empty annotations.json placeholder for later generation."""
    _write_json(output_dir / "annotations.json", {"annotations": []})


# ---------------------------------------------------------------------------
# Qualifying export
# ---------------------------------------------------------------------------

def _format_timedelta_str(td: pd.Timedelta | None) -> str | None:
    """Format a Timedelta as 'm:ss.SSS' string. Returns None for NaT/None."""
    if td is None or pd.isna(td):
        return None
    total = td.total_seconds()
    mins = int(total // 60)
    secs = total % 60
    return f"{mins}:{secs:06.3f}"


def _find_sectors_for_time(
    drv_laps: pd.DataFrame,
    target_td: pd.Timedelta,
    tolerance_ms: int = 50,
) -> dict[str, float | None]:
    """Find sector times for a lap matching a target time within tolerance."""
    sectors: dict[str, float | None] = {"s1": None, "s2": None, "s3": None}
    if target_td is None or pd.isna(target_td) or len(drv_laps) == 0:
        return sectors
    tolerance = pd.Timedelta(milliseconds=tolerance_ms)
    for _, lap_row in drv_laps.iterrows():
        lt = lap_row.get("LapTime")
        if lt is not None and pd.notna(lt):
            if abs(lt - target_td) <= tolerance:
                sectors["s1"] = _clean_value(lap_row.get("Sector1Time"))
                sectors["s2"] = _clean_value(lap_row.get("Sector2Time"))
                sectors["s3"] = _clean_value(lap_row.get("Sector3Time"))
                break
    return sectors


def _classify_sessions_for_driver(
    drv_laps: "pd.DataFrame",
    q1_s: float | None,
    q2_s: float | None,
    q3_s: float | None,
    eliminated_in: str | None,
) -> dict[int, str]:
    """Classify each lap into Q1/Q2/Q3 using official best times as anchors.

    Finds laps matching the driver's official Q1/Q2/Q3 best times,
    then uses per-driver gaps in LapStartTime to determine session boundaries.
    """
    sorted_laps = drv_laps.sort_values("LapStartTime").reset_index(drop=True)
    n = len(sorted_laps)

    if n == 0:
        return {}

    if eliminated_in == "Q1":
        return {i: "Q1" for i in range(n)}

    # Find anchor indices: laps whose LapTime matches official best
    def find_anchor(target_s):
        if target_s is None:
            return None
        best_idx, best_diff = None, 0.1  # 100ms tolerance
        for i in range(n):
            lt = sorted_laps.iloc[i].get("LapTime")
            if lt is not None and not pd.isna(lt):
                diff = abs(lt.total_seconds() - target_s)
                if diff < best_diff:
                    best_diff = diff
                    best_idx = i
        return best_idx

    q1_anchor = find_anchor(q1_s)
    q2_anchor = find_anchor(q2_s)
    q3_anchor = find_anchor(q3_s)

    # Compute gaps between consecutive laps
    gaps = []
    for i in range(n - 1):
        a = sorted_laps.iloc[i]["LapStartTime"]
        b = sorted_laps.iloc[i + 1]["LapStartTime"]
        if pd.notna(a) and pd.notna(b):
            gaps.append((i, (b - a).total_seconds()))

    # Q1->Q2 boundary: largest gap (>240s) before Q2 anchor
    q1_boundary = None
    ref = q2_anchor if q2_anchor is not None else (q1_anchor if q1_anchor is not None else n)
    cands = [(i, g) for i, g in gaps if i < ref and g > 240]
    if not cands and ref is not None:
        cands = [(i, g) for i, g in gaps if i < ref]
    if cands:
        q1_boundary = max(cands, key=lambda x: x[1])[0]

    # Q2->Q3 boundary: largest gap (>240s) between Q2 and Q3 anchors
    q2_boundary = None
    if q2_anchor is not None and q3_anchor is not None:
        cands = [(i, g) for i, g in gaps if i >= q2_anchor and i < q3_anchor and g > 240]
        if not cands:
            cands = [(i, g) for i, g in gaps if i >= q2_anchor and i < q3_anchor]
        if cands:
            q2_boundary = max(cands, key=lambda x: x[1])[0]

    # Classify
    result = {}
    for i in range(n):
        if q1_boundary is not None and i <= q1_boundary:
            result[i] = "Q1"
        elif q2_boundary is not None and i <= q2_boundary:
            result[i] = "Q2"
        elif q2_boundary is not None:
            result[i] = "Q3"
        elif q1_boundary is not None:
            result[i] = "Q2"
        else:
            result[i] = "Q1"

    # Safety: eliminated drivers cannot have higher sessions
    if eliminated_in == "Q2":
        for i in result:
            if result[i] == "Q3":
                result[i] = "Q2"

    return result



def export_qualifying(
    year: int,
    event: str,
    race_id: str,
    output_dir: Path,
) -> None:
    """Export qualifying.json with Q1/Q2/Q3 times, positions, sector data, and per-attempt details.

    Loads the qualifying session separately from the race session.
    Uses session.results for authoritative Q times and session.laps for sectors + attempts.
    """
    print("  Loading qualifying session...")
    quali_session = fastf1.get_session(year, event, "Q")
    quali_session.load()

    results = quali_session.results
    if results is None or len(results) == 0:
        print("  [WARN] No qualifying results available, skipping")
        return

    quali_laps = quali_session.laps

    # Session classification is done per-driver using _classify_sessions_for_driver

    drivers_out = []
    for _, row in results.iterrows():
        driver = str(row.get("Abbreviation", ""))
        if not driver:
            continue

        team = str(row.get("TeamName", "Unknown"))
        position = _clean_value(row.get("Position"))
        if position is not None:
            position = int(position)
        grid_position = _clean_value(row.get("GridPosition"))
        if grid_position is not None:
            grid_position = int(grid_position)

        q1_td = row.get("Q1")
        q2_td = row.get("Q2")
        q3_td = row.get("Q3")

        q1_str = _format_timedelta_str(q1_td)
        q2_str = _format_timedelta_str(q2_td)
        q3_str = _format_timedelta_str(q3_td)

        q1_s = _clean_value(q1_td)
        q2_s = _clean_value(q2_td)
        q3_s = _clean_value(q3_td)

        # Determine elimination round
        eliminated_in = None
        if q2_s is None and q1_s is not None:
            eliminated_in = "Q1"
        elif q3_s is None and q2_s is not None:
            eliminated_in = "Q2"

        drv_laps = quali_laps[quali_laps["Driver"] == driver] if len(quali_laps) > 0 else pd.DataFrame()

        # Best overall sectors (from best lap)
        best_q_td = q3_td if pd.notna(q3_td) else (q2_td if pd.notna(q2_td) else q1_td)
        sectors = _find_sectors_for_time(drv_laps, best_q_td)

        # Per-session sectors
        sectors_q1 = _find_sectors_for_time(drv_laps, q1_td)
        sectors_q2 = _find_sectors_for_time(drv_laps, q2_td)
        sectors_q3 = _find_sectors_for_time(drv_laps, q3_td)

        # Per-attempt data
        attempts: list[dict] = []
        if len(drv_laps) > 0:
            # Sort by SessionTime to get chronological order
            sorted_laps = drv_laps.sort_values("LapStartTime") if "LapStartTime" in drv_laps.columns else drv_laps

            # Track attempt numbers per session
            # Classify sessions using anchor-based per-driver detection
            session_map = _classify_sessions_for_driver(
                drv_laps, q1_s, q2_s, q3_s, eliminated_in,
            )
            # Build index mapping: sorted_laps index -> session label
            sorted_idx_to_session = {}
            sorted_laps_reset = drv_laps.sort_values("LapStartTime").reset_index(drop=True)
            for si in range(len(sorted_laps_reset)):
                sorted_idx_to_session[si] = session_map.get(si, "Q1")

            session_counts: dict[str, int] = {"Q1": 0, "Q2": 0, "Q3": 0}
            sorted_counter = 0

            for _, lap_row in sorted_laps.iterrows():
                lt = lap_row.get("LapTime")
                if lt is None or pd.isna(lt):
                    sorted_counter += 1
                    continue

                session_label = sorted_idx_to_session.get(sorted_counter, "Q1")
                sorted_counter += 1

                session_counts[session_label] = session_counts.get(session_label, 0) + 1

                lt_s = _clean_value(lt)
                is_deleted = bool(lap_row.get("Deleted", False)) if pd.notna(lap_row.get("Deleted", False)) else False
                is_pb = bool(lap_row.get("IsPersonalBest", False)) if pd.notna(lap_row.get("IsPersonalBest", False)) else False
                compound = str(lap_row.get("Compound", "")) if pd.notna(lap_row.get("Compound", "")) else None

                attempts.append({
                    "attempt_number": session_counts[session_label],
                    "session": session_label,
                    "time_s": lt_s,
                    "time_str": _format_timedelta_str(lt),
                    "s1": _clean_value(lap_row.get("Sector1Time")),
                    "s2": _clean_value(lap_row.get("Sector2Time")),
                    "s3": _clean_value(lap_row.get("Sector3Time")),
                    "compound": compound,
                    "is_deleted": is_deleted,
                    "is_personal_best": is_pb,
                })

        drivers_out.append({
            "driver": driver,
            "team": team,
            "position": position,
            "grid_position": grid_position,
            "q1": q1_str,
            "q1_s": q1_s,
            "q2": q2_str,
            "q2_s": q2_s,
            "q3": q3_str,
            "q3_s": q3_s,
            "eliminated_in": eliminated_in,
            "sectors": sectors,
            "sectors_q1": sectors_q1,
            "sectors_q2": sectors_q2,
            "sectors_q3": sectors_q3,
            "attempts": attempts,
        })

    # Sort by position
    drivers_out.sort(key=lambda d: d["position"] if d["position"] is not None else 99)

    # Compute gap to pole (P1's best time)
    pole_time = None
    if drivers_out and drivers_out[0].get("q3_s") is not None:
        pole_time = drivers_out[0]["q3_s"]
    elif drivers_out and drivers_out[0].get("q2_s") is not None:
        pole_time = drivers_out[0]["q2_s"]
    elif drivers_out and drivers_out[0].get("q1_s") is not None:
        pole_time = drivers_out[0]["q1_s"]

    for d in drivers_out:
        best_time = d["q3_s"] or d["q2_s"] or d["q1_s"]
        if best_time is not None and pole_time is not None:
            d["gap_to_pole"] = round(best_time - pole_time, 3)
        else:
            d["gap_to_pole"] = None

    total_attempts = sum(len(d["attempts"]) for d in drivers_out)
    print(f"  {len(drivers_out)} drivers, {total_attempts} total qualifying attempts exported")

    output = {
        "race_id": race_id,
        "drivers": drivers_out,
    }

    _write_json(output_dir / "qualifying.json", output)


def export_qualifying_telemetry(
    year: int,
    event: str,
    race_id: str,
    output_dir: Path,
    max_samples: int = 200,
) -> None:
    """Export per-driver qualifying telemetry for animated comparison.

    For each driver, gets telemetry from their best qualifying lap (Q3 > Q2 > Q1)
    and downsamples to ~max_samples points.
    """
    print("  Loading qualifying session for telemetry...")
    quali_session = fastf1.get_session(year, event, "Q")
    quali_session.load()

    results = quali_session.results
    if results is None or len(results) == 0:
        print("  [WARN] No qualifying results available, skipping telemetry")
        return

    quali_laps = quali_session.laps
    if quali_laps is None or len(quali_laps) == 0:
        print("  [WARN] No qualifying laps available, skipping telemetry")
        return

    tel_dir = output_dir / "qualifying_telemetry"
    tel_dir.mkdir(parents=True, exist_ok=True)

    exported = 0
    for _, row in results.iterrows():
        driver = str(row.get("Abbreviation", ""))
        if not driver:
            continue

        team = str(row.get("TeamName", "Unknown"))

        # Find best Q time and corresponding session
        q3_td = row.get("Q3")
        q2_td = row.get("Q2")
        q1_td = row.get("Q1")

        best_td = None
        session_label = "Q1"
        if q3_td is not None and pd.notna(q3_td):
            best_td = q3_td
            session_label = "Q3"
        elif q2_td is not None and pd.notna(q2_td):
            best_td = q2_td
            session_label = "Q2"
        elif q1_td is not None and pd.notna(q1_td):
            best_td = q1_td
            session_label = "Q1"

        if best_td is None:
            continue

        # Find the matching lap in session.laps
        drv_laps = quali_laps[quali_laps["Driver"] == driver]
        best_lap = None
        tolerance = pd.Timedelta(milliseconds=50)
        for _, lap_row in drv_laps.iterrows():
            lt = lap_row.get("LapTime")
            if lt is not None and pd.notna(lt) and abs(lt - best_td) <= tolerance:
                best_lap = lap_row
                break

        if best_lap is None:
            print(f"    [WARN] No matching lap found for {driver} ({session_label}), skipping")
            continue

        # Get telemetry for this lap
        try:
            tel = best_lap.get_telemetry()
        except Exception as exc:
            print(f"    [WARN] Telemetry failed for {driver}: {exc}")
            continue

        if tel is None or len(tel) == 0:
            continue

        # Extract columns
        raw_samples = []
        for _, s in tel.iterrows():
            time_val = s.get("Time")
            time_s = time_val.total_seconds() if time_val is not None and pd.notna(time_val) else 0
            raw_samples.append({
                "time_s": round(time_s, 4),
                "dist": round(float(s.get("Distance", 0)), 1),
                "speed": round(float(s.get("Speed", 0)), 1),
                "x": round(float(s.get("X", 0)), 1),
                "y": round(float(s.get("Y", 0)), 1),
                "throttle": round(float(s.get("Throttle", 0)), 1) if pd.notna(s.get("Throttle")) else None,
                "brake": bool(s.get("Brake", False)),
                "gear": int(s.get("nGear", 0)) if pd.notna(s.get("nGear")) else None,
            })

        # Downsample if needed
        if len(raw_samples) > max_samples:
            step = len(raw_samples) / max_samples
            samples = [raw_samples[int(i * step)] for i in range(max_samples)]
            # Always include last sample
            if samples[-1] != raw_samples[-1]:
                samples[-1] = raw_samples[-1]
        else:
            samples = raw_samples

        lap_time_s = _clean_value(best_td) or 0

        driver_tel = {
            "driver": driver,
            "team": team,
            "session": session_label,
            "lap_time_s": lap_time_s,
            "samples": samples,
        }

        _write_json(tel_dir / f"{driver.lower()}.json", driver_tel)
        exported += 1

    print(f"  {exported} drivers' qualifying telemetry exported")


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def run_import(year: int, event: str, energy_only: bool = False, telemetry_only: bool = False) -> None:
    """Execute the full import pipeline for a race."""
    print(f"\n{'=' * 60}")
    print(f"RaceRead Import Pipeline")
    print(f"{'=' * 60}")
    print(f"Year: {year}")
    print(f"Event: {event}")
    print(f"Energy only: {energy_only}")
    print(f"Telemetry only: {telemetry_only}")
    print(f"Data dir: {DATA_DIR}")
    print(f"Cache dir: {FASTF1_CACHE_DIR}")
    print()

    # Enable FastF1 cache
    FASTF1_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(FASTF1_CACHE_DIR))

    # Load session
    print("[1/8] Loading session from FastF1...")
    session = fastf1.get_session(year, event, "R")
    session.load()
    print(f"  Session loaded: {session.event['EventName']}")

    # Derive event slug and race ID
    event_name = str(session.event["EventName"])
    event_slug = _derive_event_slug(event_name)
    race_id = f"{year}-{event_slug}"
    output_dir = DATA_DIR / race_id

    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"  Race ID: {race_id}")
    print(f"  Output dir: {output_dir}")
    print()

    # Collect driver info
    print("[2/8] Detecting drivers...")
    drivers_info = _collect_driver_info(session)
    print(f"  Valid drivers ({len(drivers_info['drivers_valid'])}): {', '.join(drivers_info['drivers_valid'])}")
    if drivers_info["drivers_dns"]:
        print(f"  DNS/early DNF ({len(drivers_info['drivers_dns'])}): {', '.join(drivers_info['drivers_dns'])}")
    if drivers_info["inaccurate_drivers"]:
        print(f"  All-inaccurate drivers: {', '.join(drivers_info['inaccurate_drivers'])}")
    print()

    # Helper to load VSC laps from existing race control data
    def _load_vsc_laps() -> list[int]:
        rc_path = output_dir / "race_control.json"
        if rc_path.exists():
            with open(rc_path, "r", encoding="utf-8") as f:
                rc_data = json.load(f)
                return rc_data.get("vsc_laps", [])
        print("  [WARN] race_control.json not found, running export first")
        safety_car_data = export_race_control(session, output_dir)
        return safety_car_data["vsc_laps"]

    if energy_only:
        # Only re-run energy inference - still need VSC laps
        print("[--energy-only] Loading existing race control for VSC laps...")
        vsc_laps: list[int] = _load_vsc_laps()

        print("[--energy-only] Running energy inference...")
        export_energy(session, drivers_info, vsc_laps, output_dir)
        print("\nEnergy-only import complete.")
        return

    if telemetry_only:
        # Only export telemetry + circuit data
        print("[--telemetry-only] Loading existing race control for VSC laps...")
        vsc_laps = _load_vsc_laps()

        print("[--telemetry-only] Exporting telemetry...")
        export_telemetry(session, drivers_info, vsc_laps, output_dir)
        export_circuit(session, output_dir)
        print("\nTelemetry-only import complete.")
        return

    # Full pipeline
    print("[3/10] Exporting race info...")
    race_info = export_race_info(session, session.event, race_id, output_dir)

    print("[4/10] Exporting laps...")
    export_laps(session, drivers_info, output_dir)

    print("[5/10] Exporting strategy...")
    export_strategy(session, drivers_info, output_dir)

    print("[6/10] Exporting race control messages...")
    safety_car_data = export_race_control(session, output_dir)
    vsc_laps = safety_car_data["vsc_laps"]
    sc_laps = safety_car_data["sc_laps"]
    if vsc_laps:
        print(f"  VSC laps detected: {vsc_laps}")
    if sc_laps:
        print(f"  SC laps detected: {sc_laps}")

    print("[7/10] Exporting weather...")
    export_weather(session, output_dir)

    print("[8/10] Exporting energy inference...")
    export_energy(session, drivers_info, vsc_laps, output_dir)

    print("[9/10] Exporting telemetry...")
    export_telemetry(session, drivers_info, vsc_laps, output_dir)

    print("[10/10] Exporting circuit info...")
    export_circuit(session, output_dir)

    # Post-pipeline steps
    print("\nPost-pipeline steps:")

    print("  Updating race registry...")
    update_race_registry(race_info, DATA_DIR)

    print("  Writing annotations placeholder...")
    export_annotations_placeholder(output_dir)

    print("  Exporting qualifying data...")
    try:
        export_qualifying(year, event, race_id, output_dir)
    except Exception as exc:
        print(f"  [WARN] Qualifying export failed (non-fatal): {exc}")

    print("  Exporting qualifying telemetry...")
    try:
        export_qualifying_telemetry(year, event, race_id, output_dir)
    except Exception as exc:
        print(f"  [WARN] Qualifying telemetry export failed (non-fatal): {exc}")

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Import complete: {race_id}")
    print(f"{'=' * 60}")
    print(f"  Race: {race_info['name']}")
    print(f"  Date: {race_info['date']}")
    print(f"  Circuit: {race_info['circuit']}")
    print(f"  Winner: {race_info['winner']}")
    print(f"  Total laps: {race_info['total_laps']}")
    print(f"  Drivers exported: {len(drivers_info['drivers_valid'])}")
    print(f"  Output: {output_dir}")
    print()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RaceRead: Import F1 race data from FastF1 to JSON",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            '  python -m backend.scripts.import_race --year 2026 --event "Australian Grand Prix"\n'
            '  python -m backend.scripts.import_race --year 2026 --event Australia\n'
            '  python -m backend.scripts.import_race --year 2026 --event "Chinese Grand Prix" --energy-only\n'
        ),
    )
    parser.add_argument(
        "--year",
        type=int,
        required=True,
        help="Season year (e.g. 2026)",
    )
    parser.add_argument(
        "--event",
        type=str,
        required=True,
        help='Grand Prix name - FastF1 supports fuzzy matching (e.g. "Australian Grand Prix" or "Australia")',
    )
    parser.add_argument(
        "--energy-only",
        action="store_true",
        default=False,
        help="Only re-run energy inference (skip other exports)",
    )
    parser.add_argument(
        "--telemetry-only",
        action="store_true",
        default=False,
        help="Only export telemetry and circuit data (skip other exports)",
    )

    args = parser.parse_args()
    run_import(
        year=args.year,
        event=args.event,
        energy_only=args.energy_only,
        telemetry_only=args.telemetry_only,
    )


if __name__ == "__main__":
    main()
