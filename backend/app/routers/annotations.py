"""Annotations router - pre-generated descriptor annotations for chart tooltips."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import Annotation, AnnotationsResponse
from backend.app.services.data_loader import load_annotations

router = APIRouter(tags=["annotations"])


@router.get(
    "/races/{race_id}/annotations",
    response_model=AnnotationsResponse,
)
def get_annotations(
    race_id: str,
    driver: str | None = Query(
        default=None,
        description="Filter annotations by driver abbreviation",
    ),
    chart_type: str | None = Query(
        default=None,
        description="Filter by chart type (e.g. pace, energy, strategy)",
    ),
    category: str | None = Query(
        default=None,
        description="Filter by annotation category",
    ),
) -> AnnotationsResponse:
    """Return pre-generated descriptor annotations for a race.

    These are NOT live AI chat - they are pre-computed explanations
    of detected events (pace anomalies, energy shifts, SC/VSC, etc.)
    displayed as hover tooltips on charts.

    Optional filters narrow the result set.
    """
    try:
        raw = load_annotations(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Annotations not found for race '{race_id}'",
        )

    annotations_raw: list[dict] = raw.get("annotations", [])

    # Apply optional filters
    if driver:
        driver_upper = driver.upper()
        annotations_raw = [
            a for a in annotations_raw
            if a.get("driver", "").upper() == driver_upper
        ]

    if chart_type:
        chart_type_lower = chart_type.lower()
        annotations_raw = [
            a for a in annotations_raw
            if a.get("chart_type", "").lower() == chart_type_lower
        ]

    if category:
        category_lower = category.lower()
        annotations_raw = [
            a for a in annotations_raw
            if a.get("category", "").lower() == category_lower
        ]

    annotations = [Annotation(**a) for a in annotations_raw]

    return AnnotationsResponse(race_id=race_id, annotations=annotations)
