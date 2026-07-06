"""Energy router - inferred energy state data per driver and comparisons."""

from fastapi import APIRouter, HTTPException, Query

from backend.app.models.schemas import (
    DriverEnergy,
    EnergyComparisonEntry,
    EnergyComparisonResponse,
    EnergyLap,
    VSCComparisonEntry,
    VSCComparisonResponse,
)
from backend.app.services.data_loader import (
    load_all_energy,
    load_energy,
    load_race_control,
)
from backend.app.services.preprocessing import (
    compute_energy_comparison,
    compute_vsc_comparison,
)

router = APIRouter(tags=["energy"])


def _round_energy_lap(lap: dict) -> dict:
    """Round all float fields in an energy lap record to 2 decimals."""
    float_keys = [
        "deploy_pct", "harvest_pct", "clip_pct", "neutral_pct",
        "normalized_deploy", "normalized_harvest", "normalized_clip",
    ]
    result = dict(lap)
    for key in float_keys:
        val = result.get(key)
        if val is not None:
            result[key] = round(val, 2)
    return result


@router.get("/races/{race_id}/energy", response_model=DriverEnergy)
def get_driver_energy(
    race_id: str,
    driver: str = Query(..., description="Driver abbreviation (e.g. RUS)"),
) -> DriverEnergy:
    """Return inferred energy state data for a single driver.

    Energy data is INFERRED from telemetry, not directly measured.
    """
    try:
        raw = load_energy(race_id, driver)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Energy data not found for driver '{driver}' in race '{race_id}'",
        )

    laps = [
        EnergyLap(**_round_energy_lap(lap))
        for lap in raw.get("laps", [])
    ]
    return DriverEnergy(
        driver=raw.get("driver", driver.upper()),
        team=raw.get("team", "Unknown"),
        laps=laps,
    )


@router.get(
    "/races/{race_id}/energy/comparison",
    response_model=EnergyComparisonResponse,
)
def get_energy_comparison(race_id: str) -> EnergyComparisonResponse:
    """Compare inferred energy profiles across all drivers.

    Returns deploy/harvest/clip averages and deploy-to-clip ratio
    ranked from most to least efficient.
    """
    try:
        all_energy = load_all_energy(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Energy data not found for race '{race_id}'",
        )

    if not all_energy:
        raise HTTPException(
            status_code=404,
            detail=f"No energy files found for race '{race_id}'",
        )

    entries_raw = compute_energy_comparison(all_energy)
    entries = [EnergyComparisonEntry(**e) for e in entries_raw]

    return EnergyComparisonResponse(race_id=race_id, entries=entries)


@router.get(
    "/races/{race_id}/energy/vsc",
    response_model=VSCComparisonResponse,
)
def get_vsc_comparison(race_id: str) -> VSCComparisonResponse:
    """Compare energy profiles during VSC periods vs normal racing.

    This endpoint validates the energy inference model: during VSC,
    all drivers should show increased harvesting and decreased deployment.
    """
    try:
        all_energy = load_all_energy(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Energy data not found for race '{race_id}'",
        )

    try:
        race_control = load_race_control(race_id)
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Race control data not found for race '{race_id}'",
        )

    vsc_laps: list[int] = race_control.get("vsc_laps", [])
    sc_laps: list[int] = race_control.get("sc_laps", [])

    if not all_energy:
        raise HTTPException(
            status_code=404,
            detail=f"No energy files found for race '{race_id}'",
        )

    entries_raw = compute_vsc_comparison(all_energy, vsc_laps)
    entries = [VSCComparisonEntry(**e) for e in entries_raw]

    return VSCComparisonResponse(
        race_id=race_id,
        vsc_laps=vsc_laps,
        sc_laps=sc_laps,
        entries=entries,
    )


# ---- Clip map: where on track does the field hit the clip limiter? ----

_clipmap_cache: dict[str, dict] = {}


@router.get("/races/{race_id}/energy/clipmap")
def get_clipmap(race_id: str) -> dict:
    """Aggregate clip-state telemetry samples into distance bins along the lap.

    Returns per-bin clip share (0-1) aligned with the circuit outline so the
    frontend can paint clip density onto the track shape.
    """
    from backend.app.services.data_loader import get_race_dir, load_json

    cached = _clipmap_cache.get(race_id)
    if cached is not None:
        return cached

    race_dir = get_race_dir(race_id)
    try:
        circuit = load_json(str(race_dir / "circuit.json"))
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="No circuit data")
    track_len = circuit.get("track_length") or 0
    if not track_len:
        raise HTTPException(status_code=404, detail="No track length")

    n_bins = 64
    clip = [0] * n_bins
    total = [0] * n_bins
    tel_dir = race_dir / "telemetry"
    for f in sorted(tel_dir.glob("*.json")):
        t = load_json(str(f))
        for lap in t.get("laps", []):
            for smp in lap.get("samples", []):
                d = smp.get("dist")
                e = smp.get("energy")
                if d is None or e is None:
                    continue
                b = int((d % track_len) / track_len * n_bins)
                b = min(max(b, 0), n_bins - 1)
                total[b] += 1
                if e == "C":
                    clip[b] += 1

    result = {
        "bins": n_bins,
        "clip_share": [round(c / t, 4) if t else 0.0 for c, t in zip(clip, total)],
        "total_samples": sum(total),
    }
    _clipmap_cache[race_id] = result
    return result
