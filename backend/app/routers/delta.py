"""Delta router - driver-vs-driver pace delta matrix."""

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import DeltaMatrixResponse
from backend.app.services.data_loader import load_laps, load_race_control
from backend.app.services.preprocessing import compute_delta_matrix

router = APIRouter(tags=["delta"])


@router.get("/races/{race_id}/delta", response_model=DeltaMatrixResponse)
def get_delta_matrix(race_id: str) -> DeltaMatrixResponse:
    """Return NxN median lap time delta matrix.

    matrix[i][j] = median(driver_i) - median(driver_j).
    Positive values mean driver i was slower than driver j.

    Filters out lap 1, pit laps, SC/VSC laps, and inaccurate laps.
    Only includes drivers with sufficient valid laps.
    """
    try:
        laps_data = load_laps(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Lap data not found for race '{race_id}'",
        )

    try:
        race_control = load_race_control(race_id)
    except FileNotFoundError:
        # Proceed without race control filtering if file is missing
        race_control = {"vsc_laps": [], "sc_laps": []}

    result = compute_delta_matrix(laps_data, race_control)

    return DeltaMatrixResponse(
        race_id=race_id,
        drivers=result["drivers"],
        matrix=result["matrix"],
    )
