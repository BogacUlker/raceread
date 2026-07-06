"""Fetch team-radio clips from OpenF1 and match them to lap numbers.

Writes data/<race>/radio.json with clips the frontend can play directly
(audio is hosted by F1/OpenF1; we store only metadata + URLs).
OpenF1 coverage starts in 2023, so classics before that have no radio.

Usage: python3 -m backend.scripts.fetch_radio --race 2026-great-britain
"""

import argparse
import json
import os
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))
BASE = "https://api.openf1.org/v1"


def get(url):
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(4 * (attempt + 1))
    raise SystemExit(f"openf1 failed: {url}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True)
    args = ap.parse_args()

    race_dir = DATA_DIR / args.race
    info = json.loads((race_dir / "race_info.json").read_text())
    date = info["date"]
    year = date[:4]

    sessions = get(f"{BASE}/sessions?year={year}&session_name=Race")
    sess = next((s for s in sessions if s["date_start"][:10] == date), None)
    if not sess:
        raise SystemExit(f"no OpenF1 race session on {date}")
    key = sess["session_key"]

    drivers = get(f"{BASE}/drivers?session_key={key}")
    code_of = {d["driver_number"]: d.get("name_acronym", "?") for d in drivers}

    clips = get(f"{BASE}/team_radio?session_key={key}")
    if not clips:
        raise SystemExit("no radio clips")

    out = []
    lap_cache = {}
    for c in clips:
        num = c["driver_number"]
        if num not in lap_cache:
            lap_cache[num] = get(f"{BASE}/laps?session_key={key}&driver_number={num}")
            time.sleep(1.5)
        lap_no = None
        for lp in lap_cache[num]:
            if lp.get("date_start") and lp["date_start"] <= c["date"]:
                lap_no = lp["lap_number"]
            else:
                break
        out.append({
            "driver": code_of.get(num, "?"),
            "lap": lap_no,
            "date": c["date"],
            "url": c["recording_url"],
        })

    (race_dir / "radio.json").write_text(
        json.dumps({"session_key": key, "clips": out}, ensure_ascii=False, indent=2) + "\n"
    )
    print(f"{args.race}: {len(out)} radio clips ({sum(1 for c in out if c['lap'])} lap-matched)")


if __name__ == "__main__":
    main()
