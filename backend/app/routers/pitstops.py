"""Pit stop analysis router - time loss and compound change tracking."""

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import PitStatsResponse
from backend.app.services.data_loader import load_laps, load_race_control, load_strategy
from backend.app.services.pit_analysis import compute_pit_stats

router = APIRouter(tags=["pitstops"])


@router.get("/races/{race_id}/pitstops", response_model=PitStatsResponse)
def get_pitstops(race_id: str) -> PitStatsResponse:
    """Return pit stop time loss analysis for all drivers in a race."""
    try:
        laps = load_laps(race_id)
        strategy = load_strategy(race_id)
        rc = load_race_control(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Race data not found for race '{race_id}'",
        )

    result = compute_pit_stats(laps, strategy, rc)
    return PitStatsResponse(race_id=race_id, **result)
