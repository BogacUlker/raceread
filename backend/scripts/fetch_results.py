"""Fetch official race classification from Jolpica (Ergast-compatible).

FastF1 lap data cannot produce a trustworthy finishing gap: post-race time
penalties never appear in lap times, so summing laps puts drivers in the wrong
order (Hungary 2026: Hamilton crossed 4.3s ahead of Leclerc but was classified
behind him after a 5s pit lane penalty). Jolpica is the authoritative source.

Writes data/<race_id>/results.json.

Usage:
    python3 -m backend.scripts.fetch_results --race 2026-hungary
    python3 -m backend.scripts.fetch_results --all
"""

import argparse
import json
import os
import re
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))
BASE = "https://api.jolpi.ca/ergast/f1"

GAP_RE = re.compile(r"^\+(?:(\d+):)?(\d+)\.(\d+)$")


def get(url: str) -> dict:
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "raceread/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.load(r)
        except Exception as exc:
            if attempt == 3:
                raise SystemExit(f"jolpica failed: {url} ({exc})")
            time.sleep(3 * (attempt + 1))
    raise SystemExit("unreachable")


def parse_gap(text: str):
    """'+15.080' -> 15.08, '+1:02.500' -> 62.5. None for lap-based gaps."""
    m = GAP_RE.match(text.strip())
    if not m:
        return None
    minutes, secs, frac = m.group(1), m.group(2), m.group(3)
    total = int(secs) + float("0." + frac)
    if minutes:
        total += int(minutes) * 60
    return round(total, 3)


def round_for_date(year: str, date: str):
    data = get(BASE + "/" + year + ".json?limit=100")
    for race in data["MRData"]["RaceTable"]["Races"]:
        if race["date"] == date:
            return race["round"]
    return None


def fetch_one(race_id: str):
    race_dir = DATA_DIR / race_id
    info = json.loads((race_dir / "race_info.json").read_text())
    date = info["date"]
    year = date[:4]

    rnd = round_for_date(year, date)
    if not rnd:
        print("  " + race_id + ": no Jolpica round on " + date + ", skipped")
        return None

    payload = get(BASE + "/" + year + "/" + rnd + "/results.json?limit=100")
    races = payload["MRData"]["RaceTable"]["Races"]
    if not races:
        print("  " + race_id + ": Jolpica has no results for round " + rnd + ", skipped")
        return None

    rows = []
    for entry in races[0]["Results"]:
        t = entry.get("Time", {}).get("time")
        gap_s = None
        total_time = None
        if t:
            if t.startswith("+"):
                gap_s = parse_gap(t)
            else:
                total_time = t
        rows.append({
            "position": int(entry["position"]),
            "driver": entry["Driver"].get("code"),
            "team": entry["Constructor"]["name"],
            "grid": int(entry["grid"]),
            "laps": int(entry["laps"]),
            "status": entry["status"],
            "points": float(entry["points"]),
            "gap_s": gap_s,
            "total_time": total_time,
        })

    rows.sort(key=lambda r: r["position"])
    runner_up = next((r for r in rows if r["position"] == 2), None)
    margin = runner_up["gap_s"] if runner_up else None

    out = {
        "race_id": race_id,
        "source": "jolpica",
        "season": year,
        "round": rnd,
        "winner": rows[0]["driver"] if rows else None,
        "runner_up": runner_up["driver"] if runner_up else None,
        "winner_margin_s": margin,
        "results": rows,
    }

    tmp = race_dir / "results.json.tmp"
    tmp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")
    os.replace(tmp, race_dir / "results.json")

    if margin is not None:
        note = format(margin, ".3f") + "s"
    else:
        why = runner_up["status"] if runner_up else "no P2"
        note = "no time gap (" + why + ")"

    warn = ""
    if rows and info.get("winner") and rows[0]["driver"] != info["winner"]:
        warn = "  !! winner mismatch: race_info=" + str(info.get("winner")) + " jolpica=" + str(rows[0]["driver"])

    print("  " + race_id + ": R" + rnd + " " + str(len(rows)) + " classified, margin " + note + warn)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    if args.all:
        ids = sorted(p.name for p in DATA_DIR.iterdir()
                     if p.is_dir() and (p / "race_info.json").exists())
    elif args.race:
        ids = [args.race]
    else:
        raise SystemExit("pass --race <id> or --all")

    ok = 0
    for i, rid in enumerate(ids):
        if fetch_one(rid):
            ok += 1
        if i < len(ids) - 1:
            time.sleep(1.5)
    print("done: " + str(ok) + "/" + str(len(ids)) + " wrote results.json")


if __name__ == "__main__":
    main()
