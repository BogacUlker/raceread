"""Qualifying telemetry router - per-driver qualifying lap telemetry for animation."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import (
    QualifyingTelemetryDriver,
    QualifyingTelemetryResponse,
    QualifyingTelemetrySample,
)
from backend.app.services.data_loader import load_qualifying_telemetry

router = APIRouter(tags=["qualifying"])


@router.get(
    "/races/{race_id}/qualifying/telemetry",
    response_model=QualifyingTelemetryResponse,
)
def get_qualifying_telemetry(
    race_id: str,
    d1: str = Query(..., description="First driver abbreviation"),
    d2: str = Query(..., description="Second driver abbreviation"),
) -> QualifyingTelemetryResponse:
    """Return qualifying telemetry for two drivers for animated comparison."""
    drivers_out: list[QualifyingTelemetryDriver] = []

    for driver_abbr in (d1, d2):
        try:
            raw = load_qualifying_telemetry(race_id, driver_abbr)
        except FileNotFoundError:
            raise HTTPException(
                status_code=404,
                detail=f"Qualifying telemetry not found for {driver_abbr} in race '{race_id}'",
            )

        samples = [
            QualifyingTelemetrySample(
                time_s=s.get("time_s", 0),
                dist=s.get("dist", 0),
                speed=s.get("speed", 0),
                x=s.get("x", 0),
                y=s.get("y", 0),
                throttle=s.get("throttle"),
                brake=s.get("brake", False),
                gear=s.get("gear"),
            )
            for s in raw.get("samples", [])
        ]

        drivers_out.append(
            QualifyingTelemetryDriver(
                driver=raw.get("driver", driver_abbr),
                team=raw.get("team", "Unknown"),
                session=raw.get("session", "Q3"),
                lap_time_s=raw.get("lap_time_s", 0),
                samples=samples,
            )
        )

    return QualifyingTelemetryResponse(race_id=race_id, drivers=drivers_out)
