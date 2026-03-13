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
    "emilia romagna": "emilia-romagna",
    "saudi arabian": "saudi-arabia",
    "las vegas": "las-vegas",
    "abu dhabi": "abu-dhabi",
    "united states": "usa",
    "great britain": "great-britain",
    "sao paulo": "sao-paulo",
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
        drv_laps = laps.pick_driver(drv)
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

    # Circuit name
    circuit = "Unknown"
    try:
        circuit_info = session.get_circuit_info()
        if hasattr(circuit_info, "name"):
            circuit = circuit_info.name
    except Exception:
        # Fallback: try event location
        if "Location" in event.index and pd.notna(event["Location"]):
            circuit = str(event["Location"])
        elif "OfficialEventName" in event.index:
            circuit = str(event["OfficialEventName"])

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
        drv_laps = laps.pick_driver(drv).sort_values("LapNumber")

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
        drv_laps = laps.pick_driver(drv).sort_values("LapNumber")

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
            if "VIRTUAL" in message_text and "DEPLOYED" in message_text:
                vsc_deploy_lap = lap
            elif "VIRTUAL" in message_text and "ENDING" in message_text:
                if vsc_deploy_lap is not None and lap is not None:
                    for lp in range(vsc_deploy_lap, lap + 1):
                        vsc_laps.add(lp)
                    vsc_deploy_lap = None
            elif "DEPLOYED" in message_text and "VIRTUAL" not in message_text:
                sc_deploy_lap = lap
            elif "ENDING" in message_text and "VIRTUAL" not in message_text:
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
            drv_laps = session.laps.pick_driver(drv)
            telemetry = drv_laps.get_telemetry()

            if telemetry is None or len(telemetry) == 0:
                print(f"    [WARN] No telemetry for {drv}, skipping energy export")
                continue

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
# Main pipeline
# ---------------------------------------------------------------------------

def run_import(year: int, event: str, energy_only: bool = False) -> None:
    """Execute the full import pipeline for a race."""
    print(f"\n{'=' * 60}")
    print(f"RaceRead Import Pipeline")
    print(f"{'=' * 60}")
    print(f"Year: {year}")
    print(f"Event: {event}")
    print(f"Energy only: {energy_only}")
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

    if energy_only:
        # Only re-run energy inference - still need VSC laps
        print("[--energy-only] Loading existing race control for VSC laps...")
        rc_path = output_dir / "race_control.json"
        vsc_laps: list[int] = []
        if rc_path.exists():
            with open(rc_path, "r", encoding="utf-8") as f:
                rc_data = json.load(f)
                vsc_laps = rc_data.get("vsc_laps", [])
        else:
            print("  [WARN] race_control.json not found, running export first")
            safety_car_data = export_race_control(session, output_dir)
            vsc_laps = safety_car_data["vsc_laps"]

        print("[--energy-only] Running energy inference...")
        export_energy(session, drivers_info, vsc_laps, output_dir)
        print("\nEnergy-only import complete.")
        return

    # Full pipeline
    print("[3/8] Exporting race info...")
    race_info = export_race_info(session, session.event, race_id, output_dir)

    print("[4/8] Exporting laps...")
    export_laps(session, drivers_info, output_dir)

    print("[5/8] Exporting strategy...")
    export_strategy(session, drivers_info, output_dir)

    print("[6/8] Exporting race control messages...")
    safety_car_data = export_race_control(session, output_dir)
    vsc_laps = safety_car_data["vsc_laps"]
    sc_laps = safety_car_data["sc_laps"]
    if vsc_laps:
        print(f"  VSC laps detected: {vsc_laps}")
    if sc_laps:
        print(f"  SC laps detected: {sc_laps}")

    print("[7/8] Exporting weather...")
    export_weather(session, output_dir)

    print("[8/8] Exporting energy inference...")
    export_energy(session, drivers_info, vsc_laps, output_dir)

    # Post-pipeline steps
    print("\nPost-pipeline steps:")

    print("  Updating race registry...")
    update_race_registry(race_info, DATA_DIR)

    print("  Writing annotations placeholder...")
    export_annotations_placeholder(output_dir)

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

    args = parser.parse_args()
    run_import(year=args.year, event=args.event, energy_only=args.energy_only)


if __name__ == "__main__":
    main()
