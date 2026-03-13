"""Laps router - lap-by-lap timing data per driver or all drivers."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import DriverLaps, LapData
from backend.app.services.data_loader import load_laps

router = APIRouter(tags=["laps"])


def _round_lap(lap: dict) -> dict:
    """Round all float fields in a lap record to 2 decimal places."""
    float_keys = [
        "time_s", "s1", "s2", "s3",
        "speed_i1", "speed_i2", "speed_fl", "speed_st",
    ]
    result = dict(lap)
    for key in float_keys:
        val = result.get(key)
        if val is not None:
            result[key] = round(val, 2)
    return result


def _parse_driver_laps(driver_entry: dict) -> DriverLaps:
    """Parse a raw driver entry into the DriverLaps schema."""
    laps = [
        LapData(**_round_lap(lap))
        for lap in driver_entry.get("laps", [])
    ]
    return DriverLaps(
        driver=driver_entry["driver"],
        team=driver_entry.get("team", "Unknown"),
        laps=laps,
    )


@router.get("/races/{race_id}/laps", response_model=list[DriverLaps])
def get_laps(
    race_id: str,
    driver: str | None = Query(default=None, description="Driver abbreviation (e.g. RUS)"),
) -> list[DriverLaps]:
    """Return lap data for one or all drivers in a race.

    If `driver` is specified, returns a single-element list for that driver.
    If omitted, returns data for all drivers.
    """
    try:
        raw = load_laps(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Lap data not found for race '{race_id}'",
        )

    # Normalize: our laps.json format is:
    # {"drivers": ["RUS", ...], "teams": {"RUS": "Mercedes", ...}, "laps": {"RUS": [...], ...}}
    drivers_list: list[dict] = []
    if isinstance(raw, dict) and "laps" in raw and isinstance(raw["laps"], dict):
        teams = raw.get("teams", {})
        for drv, drv_laps in raw["laps"].items():
            drivers_list.append({
                "driver": drv,
                "team": teams.get(drv, "Unknown"),
                "laps": drv_laps if isinstance(drv_laps, list) else [],
            })
    elif isinstance(raw, list):
        drivers_list = raw
    elif isinstance(raw, dict) and "drivers" in raw and isinstance(raw["drivers"], list):
        # Could be a list of driver entry dicts
        if raw["drivers"] and isinstance(raw["drivers"][0], dict):
            drivers_list = raw["drivers"]

    if driver:
        driver_upper = driver.upper()
        filtered = [
            d for d in drivers_list
            if d.get("driver", "").upper() == driver_upper
        ]
        if not filtered:
            raise HTTPException(
                status_code=404,
                detail=f"Driver '{driver}' not found in race '{race_id}'",
            )
        return [_parse_driver_laps(d) for d in filtered]

    return [_parse_driver_laps(d) for d in drivers_list]
