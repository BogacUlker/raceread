"""Telemetry router - per-sample speed/throttle/energy data and circuit info."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.services.data_loader import (
    get_computed_cache,
    get_race_dir,
    load_all_telemetry,
    load_circuit,
    load_laps,
    load_race_control,
    load_telemetry,
    load_telemetry_lap,
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
        if lap is not None:
            result = load_telemetry_lap(race_id, driver, lap)
            if result is None:
                raise HTTPException(
                    status_code=404,
                    detail=f"Lap {lap} not found for driver '{driver}' in race '{race_id}'",
                )
            return result
        return load_telemetry(race_id, driver)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Telemetry not found for driver '{driver}' in race '{race_id}'",
        )


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
            result = load_telemetry_lap(race_id, drv, lap)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Telemetry not found for driver '{drv}' in race '{race_id}'",
            )

        if result is None:
            raise HTTPException(
                status_code=404,
                detail=f"Lap {lap} not found for driver '{drv}' in race '{race_id}'",
            )

        results[drv.upper()] = {
            "driver": result["driver"],
            "team": result["team"],
            "lap": lap,
            "samples": result["laps"][0]["samples"],
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
    """Return traffic analysis: per-driver time in traffic and pace degradation.

    Results are cached in memory after first computation.
    """
    cache = get_computed_cache()
    cache_key = f"traffic:{race_id}"

    if cache_key in cache:
        return cache[cache_key]

    telemetry_dir = get_race_dir(race_id) / "telemetry"
    if not telemetry_dir.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Telemetry data not found for race '{race_id}'",
        )

    all_telemetry = load_all_telemetry(race_id)

    try:
        laps_data = load_laps(race_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Lap data not found for race '{race_id}'")

    try:
        rc_data = load_race_control(race_id)
    except FileNotFoundError:
        rc_data = {"vsc_laps": [], "sc_laps": []}

    result = compute_traffic_analysis(all_telemetry, laps_data, rc_data)
    cache[cache_key] = result
    return result
