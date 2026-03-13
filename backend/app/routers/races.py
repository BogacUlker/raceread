"""Races router - list available races and race metadata."""

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import RaceInfo
from backend.app.services.data_loader import load_race_info, load_races

router = APIRouter(tags=["races"])


@router.get("/races", response_model=list[RaceInfo])
def list_races() -> list[RaceInfo]:
    """Return all available races."""
    raw = load_races()
    return [RaceInfo(**race) for race in raw]


@router.get("/races/{race_id}", response_model=RaceInfo)
def get_race(race_id: str) -> RaceInfo:
    """Return metadata for a single race."""
    try:
        raw = load_race_info(race_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"Race '{race_id}' not found")
    return RaceInfo(**raw)
