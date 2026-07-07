"""Insights router - race control feed, weather timeline, lap-1 start traces.

Lap mapping anchor: FastF1 gives race-control times in UTC but no explicit
race-start marker. The chequered-flag message minus the leader's total race
time implies the start; lap boundaries are then walked backward from the
flag so late-race laps stay exact even when early laps have missing times
(red flags). Accuracy is about +/-1 lap, which is enough for a feed.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.app.services.data_loader import (
    get_computed_cache,
    get_race_dir,
    load_laps,
    load_race_control,
)

router = APIRouter(tags=["insights"])


def _leader_cums(race_id: str) -> tuple[list[float], float]:
    """Cumulative race time at the end of each lap, for the winner."""
    laps_data = load_laps(race_id)
    race_info = json.loads((get_race_dir(race_id) / "race_info.json").read_text())
    winner = race_info.get("winner")
    drv_laps = laps_data.get("laps", {}).get(winner)
    if not drv_laps:
        # fall back to whoever has the most timed laps
        drv_laps = max(laps_data.get("laps", {}).values(), key=lambda ls: sum(1 for l in ls if l.get("time_s")))
    cum = 0.0
    cums = []
    med = sorted(l["time_s"] for l in drv_laps if l.get("time_s"))
    med = med[len(med) // 2] if med else 90.0
    for l in sorted(drv_laps, key=lambda x: x["lap"]):
        cum += l["time_s"] if l.get("time_s") else med  # red-flag laps: fill
        cums.append(cum)
    return cums, cum


def _race_start_utc(race_id: str, cums_total: float) -> datetime | None:
    rc = load_race_control(race_id)
    for m in rc.get("messages", []):
        if "CHEQUERED" in (m.get("message") or "").upper():
            return datetime.fromisoformat(m["time"]) - timedelta(seconds=cums_total)
    return None


def _lap_at(seconds_from_start: float, cums: list[float]) -> int:
    """Lap number in progress at a given race-relative time."""
    if seconds_from_start < 0:
        return 0
    for i, c in enumerate(cums):
        if seconds_from_start < c:
            return i + 1
    return len(cums)


@router.get("/races/{race_id}/race-control")
def get_race_control_feed(race_id: str) -> dict:
    """FIA race-control messages with estimated lap numbers."""
    cache = get_computed_cache()
    key = f"rcfeed:{race_id}"
    if key in cache:
        return cache[key]
    try:
        rc = load_race_control(race_id)
        cums, total = _leader_cums(race_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail=f"No race control data for '{race_id}'")

    start = _race_start_utc(race_id, total)
    out = []
    for m in rc.get("messages", []):
        lap = None
        if start is not None and m.get("time"):
            lap = _lap_at((datetime.fromisoformat(m["time"]) - start).total_seconds(), cums)
        out.append({
            "lap": lap,
            "category": m.get("category"),
            "flag": m.get("flag"),
            "scope": m.get("scope"),
            "sector": m.get("sector"),
            "message": m.get("message"),
            "racing_number": m.get("racing_number"),
        })
    result = {"messages": out, "total_laps": len(cums)}
    cache[key] = result
    return result


@router.get("/races/{race_id}/weather")
def get_weather_timeline(race_id: str) -> dict:
    """Weather samples during the race, mapped onto the lap axis.

    Session t0 is assumed to be the first race-control message time minus
    the first weather sample offset (data recording starts together).
    """
    cache = get_computed_cache()
    key = f"weather:{race_id}"
    if key in cache:
        return cache[key]
    path = get_race_dir(race_id) / "weather.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"No weather data for '{race_id}'")
    samples = json.loads(path.read_text()).get("samples", [])
    try:
        rc = load_race_control(race_id)
        cums, total = _leader_cums(race_id)
        start = _race_start_utc(race_id, total)
    except FileNotFoundError:
        start = None
    out = []
    if samples and start is not None and rc.get("messages"):
        session_t0 = datetime.fromisoformat(rc["messages"][0]["time"]) - timedelta(seconds=samples[0]["time_s"])
        race_start_s = (start - session_t0).total_seconds()
        for s in samples:
            t = s["time_s"] - race_start_s
            if t < -60 or t > total + 60:
                continue
            out.append({
                "lap": _lap_at(max(0.0, t), cums),
                "air_temp": s.get("air_temp"),
                "track_temp": s.get("track_temp"),
                "humidity": s.get("humidity"),
                "wind_speed": s.get("wind_speed"),
                "wind_direction": s.get("wind_direction"),
                "rainfall": s.get("rainfall"),
            })
    result = {"samples": out, "total_laps": len(cums) if out else None}
    cache[key] = result
    return result


@router.get("/races/{race_id}/start-traces")
def get_start_traces(race_id: str, laps: int = 1) -> dict:
    """Lap-1 (optionally first N laps) x/y traces for every driver.

    Sample time_s is lap-relative and lap 1 starts at lights-out for the
    whole field, so traces share a common clock for animation.
    """
    laps = max(1, min(3, laps))
    cache = get_computed_cache()
    key = f"start:{race_id}:{laps}"
    if key in cache:
        return cache[key]
    tel_dir = get_race_dir(race_id) / "telemetry"
    if not tel_dir.exists():
        raise HTTPException(status_code=404, detail=f"No telemetry for '{race_id}'")

    laps_data = load_laps(race_id)
    pos_after = {}
    for drv, ls in laps_data.get("laps", {}).items():
        row = next((l for l in ls if l["lap"] == laps), None)
        pos_after[drv] = row.get("position") if row else None

    drivers = []
    for f in sorted(tel_dir.glob("*.json")):
        data = json.loads(f.read_text())
        t_offset = 0.0
        pts = []
        for lap_entry in data.get("laps", []):
            if lap_entry.get("lap", 99) > laps:
                break
            samples = lap_entry.get("samples", [])
            for s in samples[:: max(1, len(samples) // 100)]:
                if s.get("x") is not None:
                    pts.append([round(t_offset + (s.get("time_s") or 0), 2), round(s["x"], 1), round(s["y"], 1), round(s.get("speed") or 0)])
            if samples:
                t_offset += samples[-1].get("time_s") or 0
        if pts:
            drivers.append({
                "driver": data.get("driver"),
                "team": data.get("team"),
                "pos_after": pos_after.get(data.get("driver")),
                "points": pts,
            })
    result = {"drivers": drivers, "laps": laps}
    cache[key] = result
    return result
