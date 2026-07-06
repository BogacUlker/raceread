"""Fetch championship standings from the Jolpica-F1 API into data/standings.json.

Includes current driver/constructor standings plus round-by-round points
progression for the championship chart. Run after each race import:

    python3 backend/scripts/fetch_standings.py [year]
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
BASE = "https://api.jolpi.ca/ergast/f1"

# Jolpica constructor names -> FastF1 team names used across the site (TEAM_COLORS)
TEAM_NAMES = {
    "Red Bull": "Red Bull Racing",
    "Alpine F1 Team": "Alpine",
    "RB F1 Team": "Racing Bulls",
    "Cadillac F1 Team": "Cadillac",
    "Sauber": "Kick Sauber",
}


def team_name(name: str) -> str:
    return TEAM_NAMES.get(name, name)


def get(url):
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.load(resp)


def driver_rows(standings_list):
    rows = []
    for s in standings_list.get("DriverStandings", []):
        d = s["Driver"]
        rows.append(
            {
                "position": int(s["position"]),
                "code": d.get("code") or d["familyName"][:3].upper(),
                "name": f"{d['givenName']} {d['familyName']}",
                "team": team_name(s["Constructors"][0]["name"]) if s["Constructors"] else "",
                "points": float(s["points"]),
                "wins": int(s["wins"]),
            }
        )
    return rows


def main():
    year = sys.argv[1] if len(sys.argv) > 1 else "2026"

    data = get(f"{BASE}/{year}/driverstandings.json")
    lists = data["MRData"]["StandingsTable"]["StandingsLists"]
    if not lists:
        raise SystemExit(f"no standings for {year}")
    current = lists[0]
    rounds_completed = int(current["round"])

    cons = get(f"{BASE}/{year}/constructorstandings.json")
    constructors = [
        {
            "position": int(s["position"]),
            "name": team_name(s["Constructor"]["name"]),
            "points": float(s["points"]),
            "wins": int(s["wins"]),
        }
        for s in cons["MRData"]["StandingsTable"]["StandingsLists"][0][
            "ConstructorStandings"
        ]
    ]

    # Round-by-round progression (one request per completed round)
    progression = []
    for rnd in range(1, rounds_completed + 1):
        rd = get(f"{BASE}/{year}/{rnd}/driverstandings.json")
        rl = rd["MRData"]["StandingsTable"]["StandingsLists"]
        if rl:
            points = {}
            for s in rl[0]["DriverStandings"]:
                code = s["Driver"].get("code") or s["Driver"]["familyName"][:3].upper()
                points[code] = float(s["points"])
            progression.append({"round": rnd, "points": points})
        time.sleep(0.4)  # stay well under Jolpica rate limits

    out = {
        "season": int(year),
        "rounds_completed": rounds_completed,
        "drivers": driver_rows(current),
        "constructors": constructors,
        "progression": progression,
    }
    path = DATA_DIR / "standings.json"
    path.write_text(json.dumps(out, indent=2) + "\n")
    print(
        f"Wrote standings after round {rounds_completed}: "
        f"{len(out['drivers'])} drivers, {len(constructors)} constructors -> {path}"
    )


if __name__ == "__main__":
    main()
