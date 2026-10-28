"""
RaceRead import pipeline - OpenF1 data source.

Since October 2026 the F1 livetiming archive that FastF1 reads requires an
F1TV login (HTTP 401 without it). This script keeps imports going without it:
it builds FastF1-shaped Session objects from api.openf1.org and runs the
UNCHANGED ``import_race.run_import`` pipeline on them. Every JSON file is
written by the same exporter code, so the schemas are identical.

``import_race.py`` stays the primary FastF1 path; nothing here modifies it.

Fields OpenF1 does not provide directly are derived:
    - TrackStatus      rebuilt from race-control flag / safety-car messages
    - IsAccurate       lap > 1, not pit in/out, sectors sum to the lap time
    - IsPersonalBest   running best over non-deleted laps
    - SpeedFL          car speed interpolated at the lap's end timestamp
    - DriverAhead      car one position ahead (OpenF1 position stream)
    - DistanceToDriverAhead  OpenF1 interval (s) x own speed (m/s)

Usage (run by file path, see the CWD note in the import workflow):
    PYTHONPATH=<root> DATA_DIR=<data> FASTF1_CACHE_DIR=<cache> \\
        python backend/scripts/import_race_openf1.py --year 2026 --event "United States Grand Prix"
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import warnings
from pathlib import Path

import fastf1
import numpy as np
import pandas as pd
import requests

_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.app.config import FASTF1_CACHE_DIR
from backend.scripts import import_race

# pandas Timedelta arithmetic trips this NumPy 2.5 deprecation once per lap.
warnings.filterwarnings("ignore", message="The 'generic' unit for NumPy timedelta")

OPENF1_URL = "https://api.openf1.org/v1"
_MIN_INTERVAL_S = 0.4  # stay well under OpenF1's free-tier request rate
_CHUNK = pd.Timedelta(minutes=30)
_last_request = 0.0


# ---------------------------------------------------------------------------
# OpenF1 client (disk-cached; finished sessions do not change)
# ---------------------------------------------------------------------------

def _get(endpoint: str, **params) -> list[dict]:
    """GET an OpenF1 endpoint. Keys may carry comparison operators, e.g.
    ``{"date>=": "..."}``; they are appended to the query string verbatim."""
    global _last_request
    query = "&".join(
        f"{k}{v}" if k.endswith((">", "<", ">=", "<=")) else f"{k}={v}"
        for k, v in params.items()
    )
    url = f"{OPENF1_URL}/{endpoint}?{query}"

    cache_dir = FASTF1_CACHE_DIR / "openf1"
    cache_path = cache_dir / (hashlib.sha1(url.encode()).hexdigest() + ".json")
    if cache_path.exists():
        return json.loads(cache_path.read_text())

    for attempt in range(6):
        wait = _MIN_INTERVAL_S - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        _last_request = time.monotonic()
        try:
            resp = requests.get(url, timeout=120)
        except requests.RequestException as exc:
            print(f"    [WARN] OpenF1 request failed ({exc}), retrying")
            time.sleep(2 ** attempt)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            time.sleep(2 ** attempt * 2)
            continue
        if resp.status_code == 404:
            data = []  # OpenF1 answers 404 "No results found" for empty sets
        else:
            resp.raise_for_status()
            data = resp.json()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(data))
        return data
    raise RuntimeError(f"OpenF1 request kept failing: {url}")


def _get_windowed(endpoint: str, start: pd.Timestamp, end: pd.Timestamp, **params) -> list[dict]:
    """Fetch a high-frequency stream in time windows to keep responses small."""
    rows: list[dict] = []
    t = start
    while t < end:
        t_next = min(t + _CHUNK, end)
        rows += _get(endpoint, **params,
                     **{"date>=": t.strftime("%Y-%m-%dT%H:%M:%S"),
                        "date<": t_next.strftime("%Y-%m-%dT%H:%M:%S")})
        t = t_next
    return rows


def _ts(values) -> pd.Series:
    return pd.to_datetime(pd.Series(values), utc=True, format="ISO8601")


def _ns(values) -> np.ndarray:
    return _ts(values).astype("int64").to_numpy()


# ---------------------------------------------------------------------------
# FastF1-shaped containers
# ---------------------------------------------------------------------------

_STREAMS: dict[int, "_Streams"] = {}


class OLap(pd.Series):
    """One lap row; mirrors the subset of fastf1.core.Lap the exporters use."""

    @property
    def _constructor(self):
        return OLap

    @property
    def _constructor_expanddim(self):
        return OLaps

    def get_telemetry(self) -> pd.DataFrame:
        return _STREAMS[int(self["_SessionKey"])].lap_frame(self)

    def get_car_data(self) -> pd.DataFrame:
        return self.get_telemetry()


class OLaps(pd.DataFrame):
    """Lap table; mirrors the subset of fastf1.core.Laps the exporters use."""

    @property
    def _constructor(self):
        return OLaps

    @property
    def _constructor_sliced(self):
        return OLap

    def pick_drivers(self, drivers) -> "OLaps":
        if isinstance(drivers, str):
            drivers = [drivers]
        return self[self["Driver"].isin(drivers)]

    def pick_fastest(self) -> OLap:
        timed = self[self["LapTime"].notna()]
        return timed.loc[timed["LapTime"].idxmin()]


class _Streams:
    """Lazy per-driver car_data / location / interval streams for one session."""

    def __init__(self, session_key: int, start: pd.Timestamp, end: pd.Timestamp,
                 positions: list[dict], driver_numbers: list[int], with_gaps: bool):
        self.session_key = session_key
        self.start, self.end = start, end
        self.with_gaps = with_gaps
        self.driver_numbers = driver_numbers
        self._car: dict[int, pd.DataFrame] = {}
        self._loc: dict[int, pd.DataFrame] = {}
        self._ivl: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        self._pos: dict[int, tuple[np.ndarray, np.ndarray]] = {}
        by_drv: dict[int, list[dict]] = {}
        for p in positions:
            by_drv.setdefault(p["driver_number"], []).append(p)
        for num, rows in by_drv.items():
            rows.sort(key=lambda r: r["date"])
            self._pos[num] = (_ns([r["date"] for r in rows]),
                              np.array([r["position"] for r in rows], dtype=float))

    def car(self, num: int) -> pd.DataFrame:
        if num not in self._car:
            rows = _get_windowed("car_data", self.start, self.end,
                                 session_key=self.session_key, driver_number=num)
            df = pd.DataFrame(rows)
            if len(df):
                df["t"] = _ns(df["date"])
                df = df.sort_values("t").drop_duplicates("t").reset_index(drop=True)
            self._car[num] = df
        return self._car[num]

    def loc(self, num: int) -> pd.DataFrame:
        if num not in self._loc:
            rows = _get_windowed("location", self.start, self.end,
                                 session_key=self.session_key, driver_number=num)
            df = pd.DataFrame(rows)
            if len(df):
                df = df[(df["x"] != 0) | (df["y"] != 0)].copy()
                df["t"] = _ns(df["date"])
                df = df.sort_values("t").drop_duplicates("t").reset_index(drop=True)
            self._loc[num] = df
        return self._loc[num]

    def intervals(self, num: int) -> tuple[np.ndarray, np.ndarray]:
        if num not in self._ivl:
            rows = _get("intervals", session_key=self.session_key, driver_number=num)
            rows.sort(key=lambda r: r["date"])
            vals = [r["interval"] if isinstance(r.get("interval"), (int, float)) else np.nan
                    for r in rows]
            self._ivl[num] = (_ns([r["date"] for r in rows]) if rows else np.array([], dtype=np.int64),
                              np.array(vals, dtype=float))
        return self._ivl[num]

    def position_at(self, num: int, t: np.ndarray) -> np.ndarray:
        if num not in self._pos:
            return np.full(len(t), np.nan)
        dates, pos = self._pos[num]
        idx = np.searchsorted(dates, t, side="right") - 1
        return np.where(idx >= 0, pos[np.clip(idx, 0, None)], np.nan)

    def speed_at(self, num: int, t_ns: int) -> float:
        car = self.car(num)
        if not len(car) or t_ns is None:
            return np.nan
        return float(np.interp(t_ns, car["t"].to_numpy(), car["speed"].to_numpy(dtype=float)))

    def lap_frame(self, lap: OLap) -> pd.DataFrame:
        """Per-lap telemetry in FastF1 column names (Time is lap-relative)."""
        num = int(lap["DriverNumber"])
        s, e = lap["_Start"], lap["_End"]
        car = self.car(num)
        if pd.isna(s) or pd.isna(e) or not len(car):
            return pd.DataFrame()
        s_ns, e_ns = s.value, e.value
        ct = car["t"].to_numpy()
        inner = (ct > s_ns) & (ct < e_ns)
        if inner.sum() < 5:
            return pd.DataFrame()

        # FastF1's get_telemetry() merges the car and position streams onto the
        # union of their timestamps (roughly doubling the sample rate). The energy
        # classifier smooths over a fixed number of samples, so match that density.
        loc = self.loc(num)
        lt = loc["t"].to_numpy() if len(loc) else np.array([], dtype=np.int64)
        stamps = np.union1d(ct[inner], lt[(lt > s_ns) & (lt < e_ns)])

        # Pad the exact lap start/end like FastF1 does, so Distance spans the lap.
        t = np.concatenate([[s_ns], stamps, [e_ns]])

        def lin(col):
            return np.interp(t, ct, car[col].to_numpy(dtype=float))

        def nearest(col):
            idx = np.clip(np.searchsorted(ct, t, side="right") - 1, 0, len(ct) - 1)
            return car[col].to_numpy()[idx]

        speed = lin("speed")
        dt = np.diff(t, prepend=t[0]) / 1e9
        distance = np.cumsum(speed / 3.6 * dt)

        frame = pd.DataFrame({
            "Date": pd.to_datetime(t, utc=True).tz_localize(None),
            "Time": pd.to_timedelta(t - s_ns, unit="ns"),
            "Speed": speed,
            "RPM": lin("rpm"),
            "nGear": nearest("n_gear").astype(int),
            "Throttle": lin("throttle"),
            "Brake": nearest("brake").astype(float) > 0,
            "Distance": distance,
        })

        if len(loc) >= 2:
            frame["X"] = np.interp(t, lt, loc["x"].to_numpy(dtype=float))
            frame["Y"] = np.interp(t, lt, loc["y"].to_numpy(dtype=float))
        else:
            frame["X"] = 0.0
            frame["Y"] = 0.0

        frame["DriverAhead"] = None
        frame["DistanceToDriverAhead"] = np.nan
        if self.with_gaps:
            mine = self.position_at(num, t)
            others = [n for n in self.driver_numbers if n != num]
            if others:
                grid = np.vstack([self.position_at(n, t) for n in others])
                match = grid == (mine - 1)[None, :]
                has = match.any(axis=0)
                ahead = np.array(others)[match.argmax(axis=0)]
                frame["DriverAhead"] = [str(a) if h else None for a, h in zip(ahead, has)]
                it, iv = self.intervals(num)
                if len(it):
                    idx = np.searchsorted(it, t, side="right") - 1
                    gap_s = np.where(idx >= 0, iv[np.clip(idx, 0, None)], np.nan)
                    frame["DistanceToDriverAhead"] = np.where(has, gap_s * speed / 3.6, np.nan)
        return frame


class OSession:
    """The subset of fastf1.core.Session that run_import and the exporters read."""

    def __init__(self, event: pd.Series, date: pd.Timestamp, circuit_key: int):
        self.event = event
        self.date = date
        self.session_info = {"Meeting": {"Circuit": {"Key": circuit_key}}}
        self.laps: OLaps = OLaps()
        self.results: pd.DataFrame = pd.DataFrame()
        self.race_control_messages: pd.DataFrame = pd.DataFrame()
        self.weather_data: pd.DataFrame = pd.DataFrame()

    def load(self, *args, **kwargs) -> None:
        pass  # built eagerly in _build_session

    def get_circuit_info(self):
        # Force the exporter onto its low-level MultiViewer path (not IP/auth gated).
        raise NotImplementedError("circuit info comes from fastf1.mvapi")


# ---------------------------------------------------------------------------
# Derived fields
# ---------------------------------------------------------------------------

def _status_timeline(rc: list[dict]) -> list[tuple[int, str]]:
    """Track status changes (FastF1 codes: 1 green, 2 yellow, 4 SC, 5 red,
    6 VSC, 7 VSC ending) rebuilt from race-control messages."""
    sc, vsc, red = False, None, False
    yellow: set = set()

    def code() -> str:
        if red:
            return "5"
        if sc:
            return "4"
        if vsc:
            return vsc
        return "2" if yellow else "1"

    changes = [(np.iinfo(np.int64).min, "1")]
    for m in rc:
        msg = (m.get("message") or "").upper()
        flag = (m.get("flag") or "").upper()
        scope = m.get("scope")
        if m.get("category") == "SafetyCar":
            if "VIRTUAL" in msg or "VSC" in msg:
                if "DEPLOYED" in msg:
                    vsc = "6"
                elif "ENDING" in msg:
                    vsc = "7"
            elif "DEPLOYED" in msg:
                sc = True
        elif flag == "RED":
            red = True
        elif flag in ("GREEN", "CLEAR") and scope == "Track":
            sc, vsc, red = False, None, False
            yellow.clear()
        elif flag in ("YELLOW", "DOUBLE YELLOW"):
            yellow.add(m.get("sector") if scope == "Sector" else "track")
        elif flag == "CLEAR" and scope == "Sector":
            yellow.discard(m.get("sector"))
        c = code()
        if c != changes[-1][1]:
            changes.append((_ns([m["date"]])[0], c))
    return changes


def _lap_status(changes: list[tuple[int, str]], s_ns, e_ns) -> str | None:
    if s_ns is None:
        return None
    times = np.array([c[0] for c in changes])
    i0 = int(np.searchsorted(times, s_ns, side="right")) - 1
    codes = [changes[i0][1]] + [c for t, c in changes[i0 + 1:] if e_ns is not None and t <= e_ns]
    return "".join(dict.fromkeys(codes))


_DELETED_RE = re.compile(
    r"CAR (\d+) \(\w+\) (?:TIME (\d+):([\d.]+) |LAP )(DELETED|REINSTATED).*?\bLAP (\d+)\b")


def _deleted_laps(rc: list[dict], laps_raw: list[dict]) -> set[tuple[int, int]]:
    """(driver_number, lap_number) of deleted laps. Matched on the quoted lap
    time, because the LAP number in qualifying messages runs one ahead of
    OpenF1's numbering; the message's LAP is only a fallback."""
    durations = {(l["driver_number"], l["lap_number"]): l.get("lap_duration") for l in laps_raw}
    deleted: set[tuple[int, int]] = set()
    for m in rc:
        hit = _DELETED_RE.search(m.get("message") or "")
        if not hit:
            continue
        num = int(hit.group(1))
        key = (num, int(hit.group(5)))
        if hit.group(2):
            quoted = int(hit.group(2)) * 60 + float(hit.group(3))
            match = [k for k, d in durations.items() if k[0] == num and d and abs(d - quoted) < 0.0006]
            if match:
                key = match[0]
        if hit.group(4) == "DELETED":
            deleted.add(key)
        else:
            deleted.discard(key)
    return deleted


# ---------------------------------------------------------------------------
# Session builder
# ---------------------------------------------------------------------------

def _resolve_meeting(year: int, event: str) -> dict:
    meetings = _get("meetings", year=year)
    wanted = event.strip().lower()
    for m in meetings:
        if m["meeting_name"].lower() == wanted:
            return m
    for m in meetings:
        if wanted in m["meeting_name"].lower() or wanted in m["location"].lower():
            return m
    names = ", ".join(m["meeting_name"] for m in meetings)
    raise SystemExit(f"No OpenF1 meeting matches '{event}' in {year}. Known: {names}")


def _build_session(meeting: dict, session: dict, is_race: bool) -> OSession:
    sk = session["session_key"]
    print(f"  Building {session['session_name']} (OpenF1 session {sk}) ...")

    drivers = {d["driver_number"]: d for d in _get("drivers", session_key=sk)}
    laps_raw = _get("laps", session_key=sk)
    stints = _get("stints", session_key=sk)
    pits = _get("pit", session_key=sk)
    rc = sorted(_get("race_control", session_key=sk), key=lambda m: m["date"])
    weather = sorted(_get("weather", session_key=sk), key=lambda w: w["date"])
    positions = _get("position", session_key=sk) if is_race else []

    # Session-time origin. Only relative times are exported, so any fixed
    # reference works; use the earliest weather / race-control timestamp.
    firsts = [x[0]["date"] for x in (weather, rc) if x]
    t0 = min(_ts(firsts)) if firsts else _ts([session["date_start"]])[0]

    lap_starts = [l["date_start"] for l in laps_raw if l.get("date_start")]
    start = min(_ts(lap_starts)) - pd.Timedelta(minutes=2) if lap_starts else _ts([session["date_start"]])[0]
    end = _ts([session["date_end"]])[0] + pd.Timedelta(minutes=10)

    streams = _Streams(sk, start, end, positions, sorted(drivers), with_gaps=is_race)
    _STREAMS[sk] = streams

    status_changes = _status_timeline(rc)
    deleted = _deleted_laps(rc, laps_raw)
    pit_in: dict[tuple[int, int], pd.Timestamp] = {
        (p["driver_number"], p["lap_number"]): _ts([p["date"]])[0] for p in pits if p.get("lap_number")
    }
    stints_by_drv: dict[int, list[dict]] = {}
    for st in stints:
        stints_by_drv.setdefault(st["driver_number"], []).append(st)

    laps_by_drv: dict[int, list[dict]] = {}
    for l in laps_raw:
        laps_by_drv.setdefault(l["driver_number"], []).append(l)

    rows = []
    for num, dlaps in laps_by_drv.items():
        info = drivers.get(num, {})
        abbr = info.get("name_acronym") or str(num)
        team = info.get("team_name") or "Unknown"
        dlaps.sort(key=lambda l: l["lap_number"])
        # A retirement leaves a final lap with no duration. FastF1 keeps it (untimed)
        # when the car stopped out on track, but has no row when the car crawled
        # down the pit lane instead; then the previous lap is its pit-in lap.
        if is_race and len(dlaps) > 1 and dlaps[-1].get("lap_duration") is None and dlaps[-1].get("date_start"):
            car = streams.car(num)
            t_open = _ts([dlaps[-1]["date_start"]])[0].value
            window = car[(car["t"] >= t_open) & (car["t"] < t_open + 20_000_000_000)] if len(car) else car
            if not len(window) or window["speed"].max() < 150:
                dlaps.pop()
                pit_in.setdefault((num, dlaps[-1]["lap_number"]), _ts([dlaps[-1]["date_start"]])[0]
                                  + pd.Timedelta(seconds=dlaps[-1].get("lap_duration") or 0))
        best = None
        for i, l in enumerate(dlaps):
            n = l["lap_number"]
            s = _ts([l["date_start"]])[0] if l.get("date_start") else pd.NaT
            nxt = dlaps[i + 1] if i + 1 < len(dlaps) else None
            is_out = bool(l.get("is_pit_out_lap"))
            dur = l.get("lap_duration")
            if not is_race and is_out:
                # Qualifying out-laps start in the garage; FastF1 leaves them untimed.
                dur = None
            if dur is None and not is_out and nxt is not None and nxt.get("date_start") and pd.notna(s):
                # OpenF1 occasionally leaves a lap open; close it at the next start.
                dur = (_ts([nxt["date_start"]])[0] - s).total_seconds()
            # Telemetry window: an untimed out-lap still runs until the next lap starts.
            span = dur
            if span is None and nxt is not None and nxt.get("date_start") and pd.notna(s):
                span = (_ts([nxt["date_start"]])[0] - s).total_seconds()
            e = s + pd.Timedelta(seconds=span) if (span is not None and pd.notna(s)) else pd.NaT
            s_ns = s.value if pd.notna(s) else None
            e_ns = e.value if pd.notna(e) else None

            dstints = stints_by_drv.get(num, [])
            st = next((x for x in dstints if x["lap_start"] <= n <= (x["lap_end"] or n)), None)
            if st is None and dstints and n > max(x["lap_end"] or 0 for x in dstints):
                # OpenF1 closes the last stint before an untimed retirement lap.
                st = max(dstints, key=lambda x: x["stint_number"])
            sectors = [l.get(f"duration_sector_{k}") for k in (1, 2, 3)]
            is_in = (num, n) in pit_in
            is_deleted = (num, n) in deleted
            status = _lap_status(status_changes, s_ns, e_ns)

            # Every FastF1-imported race marks SC/VSC/red-flag laps inaccurate,
            # which keeps them out of the site's median pace.
            accurate = (n > 1 and dur is not None and not is_in and not is_out
                        and not any(c in (status or "") for c in "4567")
                        and all(x is not None for x in sectors)
                        and abs(sum(sectors) - dur) < 0.01)
            is_pb = False
            if n > 1 and dur is not None and not is_deleted and (best is None or dur < best):
                best, is_pb = dur, True

            pos = np.nan
            if is_race and e_ns is not None:
                pos = streams.position_at(num, np.array([e_ns + 1_000_000_000]))[0]

            rows.append({
                "Driver": abbr,
                "DriverNumber": str(num),
                "Team": team,
                "LapNumber": float(n),
                "LapTime": pd.to_timedelta(dur, unit="s") if dur is not None else pd.NaT,
                "Sector1Time": pd.to_timedelta(sectors[0], unit="s") if sectors[0] is not None else pd.NaT,
                "Sector2Time": pd.to_timedelta(sectors[1], unit="s") if sectors[1] is not None else pd.NaT,
                "Sector3Time": pd.to_timedelta(sectors[2], unit="s") if sectors[2] is not None else pd.NaT,
                "Compound": st["compound"] if st else None,
                "Stint": float(st["stint_number"]) if st else np.nan,
                "TyreLife": float((st.get("tyre_age_at_start") or 0) + n - st["lap_start"] + 1) if st else np.nan,
                "Position": pos,
                "TrackStatus": status,
                "IsPersonalBest": is_pb,
                "IsAccurate": accurate,
                "Deleted": is_deleted,
                "SpeedI1": l.get("i1_speed"),
                "SpeedI2": l.get("i2_speed"),
                "SpeedST": l.get("st_speed"),
                "SpeedFL": float(round(streams.speed_at(num, e_ns))) if (is_race and dur is not None and e_ns is not None) else np.nan,
                "PitInTime": (pit_in[(num, n)] - t0) if is_in else pd.NaT,
                "PitOutTime": (s - t0) if (is_out and pd.notna(s)) else pd.NaT,
                "LapStartTime": (s - t0) if pd.notna(s) else pd.NaT,
                "Time": (e - t0) if pd.notna(e) else pd.NaT,
                "_Start": s,
                "_End": e,
                "_SessionKey": sk,
            })

    event_date = _ts([session["date_start"]])[0] + pd.to_timedelta(session.get("gmt_offset") or "00:00:00")
    event = pd.Series({
        "EventName": meeting["meeting_name"],
        "EventDate": pd.Timestamp(event_date.date()),
        "Location": meeting["location"],
        "Country": meeting["country_name"],
        "year": meeting["year"],
    })
    osess = OSession(event, _ts([session["date_start"]])[0], meeting["circuit_key"])
    osess.laps = OLaps(rows)

    osess.race_control_messages = pd.DataFrame([{
        "Time": _ts([m["date"]])[0].tz_localize(None),
        "Category": m.get("category"),
        "Message": m.get("message"),
        "Status": None,
        "Flag": m.get("flag"),
        "Scope": m.get("scope"),
        "Sector": m.get("sector"),
        "RacingNumber": str(m["driver_number"]) if m.get("driver_number") is not None else None,
        "Lap": m.get("lap_number"),
    } for m in rc])

    osess.weather_data = pd.DataFrame([{
        "Time": _ts([w["date"]])[0] - t0,
        "AirTemp": w.get("air_temperature"),
        "TrackTemp": w.get("track_temperature"),
        "Humidity": w.get("humidity"),
        "Pressure": w.get("pressure"),
        "Rainfall": bool(w.get("rainfall")),
        "WindDirection": w.get("wind_direction"),
        "WindSpeed": w.get("wind_speed"),
    } for w in weather])

    results = []
    for r in _get("session_result", session_key=sk):
        info = drivers.get(r["driver_number"], {})
        dur = r.get("duration")
        q = dur if isinstance(dur, list) else [None, None, None]
        results.append({
            "Abbreviation": info.get("name_acronym") or str(r["driver_number"]),
            "TeamName": info.get("team_name") or "Unknown",
            "Position": float(r["position"]) if r.get("position") is not None else np.nan,
            "GridPosition": np.nan,
            "Q1": pd.to_timedelta(q[0], unit="s") if q[0] is not None else pd.NaT,
            "Q2": pd.to_timedelta(q[1], unit="s") if q[1] is not None else pd.NaT,
            "Q3": pd.to_timedelta(q[2], unit="s") if q[2] is not None else pd.NaT,
        })
    osess.results = pd.DataFrame(results).sort_values("Position", na_position="last").reset_index(drop=True)

    print(f"    {len(drivers)} drivers, {len(rows)} laps, {len(rc)} race-control messages, "
          f"{len(weather)} weather samples")
    return osess


def main() -> None:
    parser = argparse.ArgumentParser(description="RaceRead import from OpenF1")
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--event", type=str, required=True,
                        help='Meeting name as OpenF1 lists it, e.g. "United States Grand Prix"')
    parser.add_argument("--energy-only", action="store_true")
    parser.add_argument("--telemetry-only", action="store_true")
    args = parser.parse_args()

    meeting = _resolve_meeting(args.year, args.event)
    sessions = {s["session_name"]: s for s in _get("sessions", meeting_key=meeting["meeting_key"])}
    if "Race" not in sessions:
        raise SystemExit(f"OpenF1 has no Race session for {meeting['meeting_name']}")

    print(f"OpenF1 meeting {meeting['meeting_key']}: {meeting['meeting_name']} ({meeting['location']})")
    built = {"R": _build_session(meeting, sessions["Race"], is_race=True)}
    if "Qualifying" in sessions:
        built["Q"] = _build_session(meeting, sessions["Qualifying"], is_race=False)

    def get_session(year, event, identifier, *a, **kw):
        if identifier not in built:
            raise ValueError(f"OpenF1 import has no '{identifier}' session")
        return built[identifier]

    # Route the unchanged FastF1 pipeline onto the OpenF1-backed sessions.
    fastf1.get_session = get_session
    import_race.run_import(args.year, meeting["meeting_name"],
                           energy_only=args.energy_only, telemetry_only=args.telemetry_only)


if __name__ == "__main__":
    main()
