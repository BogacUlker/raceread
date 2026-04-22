"""RaceRead FastAPI application.

F1 post-race telemetry analysis API serving lap data, inferred energy states,
strategy timelines, delta matrices, and pre-generated descriptor annotations.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import CORS_ORIGINS

_is_dev = os.getenv("ENVIRONMENT", "production") != "production"
from backend.app.routers import annotations, delta, energy, laps, pitstops, qualifying, qualifying_telemetry, races, strategy, telemetry

app = FastAPI(
    title="RaceRead API",
    description=(
        "F1 post-race telemetry analysis - interactive charts, "
        "AI-generated descriptor annotations, and inferred energy states."
    ),
    version="0.1.0",
    docs_url="/docs" if _is_dev else None,
    redoc_url="/redoc" if _is_dev else None,
    openapi_url="/openapi.json" if _is_dev else None,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register all routers under /api prefix
app.include_router(races.router, prefix="/api")
app.include_router(laps.router, prefix="/api")
app.include_router(energy.router, prefix="/api")
app.include_router(strategy.router, prefix="/api")
app.include_router(delta.router, prefix="/api")
app.include_router(annotations.router, prefix="/api")
app.include_router(qualifying.router, prefix="/api")
app.include_router(pitstops.router, prefix="/api")
app.include_router(telemetry.router, prefix="/api")
app.include_router(qualifying_telemetry.router, prefix="/api")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    return {"status": "ok"}
