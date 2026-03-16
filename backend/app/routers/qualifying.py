"""Qualifying router - qualifying session times and positions."""

from fastapi import APIRouter, HTTPException

from backend.app.models.schemas import (
    QualifyingAttempt,
    QualifyingDriver,
    QualifyingResponse,
    QualifyingSessionResult,
)
from backend.app.services.data_loader import load_qualifying

router = APIRouter(tags=["qualifying"])


def _parse_session_sectors(entry: dict, key: str) -> QualifyingSessionResult:
    """Parse per-session sector data from a qualifying entry."""
    raw = entry.get(key, {}) or {}
    return QualifyingSessionResult(
        s1=raw.get("s1"),
        s2=raw.get("s2"),
        s3=raw.get("s3"),
    )


def _parse_qualifying_driver(entry: dict) -> QualifyingDriver:
    """Parse a raw qualifying driver entry into the schema."""
    sectors = _parse_session_sectors(entry, "sectors")
    sectors_q1 = _parse_session_sectors(entry, "sectors_q1")
    sectors_q2 = _parse_session_sectors(entry, "sectors_q2")
    sectors_q3 = _parse_session_sectors(entry, "sectors_q3")

    attempts_raw = entry.get("attempts", [])
    attempts = [
        QualifyingAttempt(
            attempt_number=a.get("attempt_number", 0),
            session=a.get("session", ""),
            time_s=a.get("time_s"),
            time_str=a.get("time_str"),
            s1=a.get("s1"),
            s2=a.get("s2"),
            s3=a.get("s3"),
            compound=a.get("compound"),
            is_deleted=a.get("is_deleted", False),
            is_personal_best=a.get("is_personal_best", False),
        )
        for a in attempts_raw
    ]

    return QualifyingDriver(
        driver=entry["driver"],
        team=entry.get("team", "Unknown"),
        position=entry.get("position"),
        grid_position=entry.get("grid_position"),
        q1=entry.get("q1"),
        q1_s=entry.get("q1_s"),
        q2=entry.get("q2"),
        q2_s=entry.get("q2_s"),
        q3=entry.get("q3"),
        q3_s=entry.get("q3_s"),
        eliminated_in=entry.get("eliminated_in"),
        sectors=sectors,
        sectors_q1=sectors_q1,
        sectors_q2=sectors_q2,
        sectors_q3=sectors_q3,
        gap_to_pole=entry.get("gap_to_pole"),
        attempts=attempts,
    )


@router.get("/races/{race_id}/qualifying", response_model=QualifyingResponse)
def get_qualifying(race_id: str) -> QualifyingResponse:
    """Return qualifying session data for all drivers."""
    try:
        raw = load_qualifying(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Qualifying data not found for race '{race_id}'",
        )

    drivers_list: list[dict] = []
    if isinstance(raw, list):
        drivers_list = raw
    elif isinstance(raw, dict) and "drivers" in raw:
        drivers_list = raw["drivers"]

    drivers = [_parse_qualifying_driver(d) for d in drivers_list]
    return QualifyingResponse(race_id=race_id, drivers=drivers)
