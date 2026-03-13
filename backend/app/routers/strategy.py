"""Strategy router - pit stop and tyre strategy data."""

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    DriverStrategy,
    Stint,
    StrategyResponse,
)
from backend.app.services.data_loader import load_strategy

router = APIRouter(tags=["strategy"])


def _parse_driver_strategy(entry: dict) -> DriverStrategy:
    """Parse a raw driver strategy entry into the schema."""
    stints = [
        Stint(
            compound=s["compound"],
            start_lap=s["start_lap"],
            end_lap=s["end_lap"],
            laps=s["laps"],
        )
        for s in entry.get("stints", [])
    ]
    return DriverStrategy(
        driver=entry["driver"],
        team=entry.get("team", "Unknown"),
        stints=stints,
        pit_laps=entry.get("pit_laps", []),
    )


@router.get("/races/{race_id}/strategy", response_model=StrategyResponse)
def get_strategy(race_id: str) -> StrategyResponse:
    """Return tyre strategy and pit stop data for all drivers."""
    try:
        raw = load_strategy(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Strategy data not found for race '{race_id}'",
        )

    # Normalize: can be a list of driver entries or dict with "drivers" key
    drivers_list: list[dict] = []
    if isinstance(raw, list):
        drivers_list = raw
    elif isinstance(raw, dict) and "drivers" in raw:
        drivers_list = raw["drivers"]

    drivers = [_parse_driver_strategy(d) for d in drivers_list]
    return StrategyResponse(race_id=race_id, drivers=drivers)
