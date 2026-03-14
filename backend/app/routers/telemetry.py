"""Telemetry router - per-sample speed/throttle/energy data and circuit info."""

from pathlib import Path

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.data_loader import (
    get_race_dir,
    load_circuit,
    load_laps,
    load_race_control,
    load_telemetry,
)
from backend.app.services.preprocessing import compute_traffic_analysis

router = APIRouter(tags=["telemetry"])


@router.get("/races/{race_id}/telemetry")
def get_telemetry(
    race_id: str,
    driver: str = Query(description="Driver abbreviation (e.g. RUS)"),
    lap: int | None = Query(default=None, description="Filter to a single lap number"),
):
    """Return per-sample telemetry for a driver.

    If `lap` is specified, returns only that lap's samples.
    Otherwise returns all laps.
    """
    try:
        data = load_telemetry(race_id, driver)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Telemetry not found for driver '{driver}' in race '{race_id}'",
        )

    if lap is not None:
        filtered_laps = [l for l in data.get("laps", []) if l["lap"] == lap]
        if not filtered_laps:
            raise HTTPException(
                status_code=404,
                detail=f"Lap {lap} not found for driver '{driver}' in race '{race_id}'",
            )
        return {**data, "laps": filtered_laps}

    return data


@router.get("/races/{race_id}/telemetry/compare")
def compare_telemetry(
    race_id: str,
    d1: str = Query(description="First driver abbreviation"),
    d2: str = Query(description="Second driver abbreviation"),
    lap: int = Query(description="Lap number to compare"),
):
    """Return telemetry for two drivers on the same lap, for speed trace overlay."""
    results = {}
    for drv in [d1, d2]:
        try:
            data = load_telemetry(race_id, drv)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Telemetry not found for driver '{drv}' in race '{race_id}'",
            )

        lap_data = [l for l in data.get("laps", []) if l["lap"] == lap]
        if not lap_data:
            raise HTTPException(
                status_code=404,
                detail=f"Lap {lap} not found for driver '{drv}' in race '{race_id}'",
            )

        results[drv.upper()] = {
            "driver": data["driver"],
            "team": data["team"],
            "lap": lap,
            "samples": lap_data[0]["samples"],
        }

    return results


@router.get("/races/{race_id}/circuit")
def get_circuit(race_id: str):
    """Return circuit layout: corners, outline, and track length."""
    try:
        return load_circuit(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Circuit data not found for race '{race_id}'",
        )


@router.get("/races/{race_id}/traffic")
def get_traffic(race_id: str):
    """Return traffic analysis: per-driver time in traffic and pace degradation."""
    # Load all driver telemetry files
    telemetry_dir = get_race_dir(race_id) / "telemetry"
    if not telemetry_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Telemetry data not found for race '{race_id}'",
        )

    all_telemetry = {}
    for f in sorted(telemetry_dir.glob("*.json")):
        driver = f.stem.upper()
        all_telemetry[driver] = load_telemetry(race_id, driver)

    try:
        laps_data = load_laps(race_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Lap data not found for race '{race_id}'")

    try:
        rc_data = load_race_control(race_id)
    except FileNotFoundError:
        rc_data = {"vsc_laps": [], "sc_laps": []}

    return compute_traffic_analysis(all_telemetry, laps_data, rc_data)
