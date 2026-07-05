"""Fetch the F1 season calendar from the Jolpica-F1 API into data/calendar.json.

Jolpica (https://api.jolpi.ca) is the community successor to the Ergast API.
Run whenever the schedule changes or at season start:

    python3 backend/scripts/fetch_calendar.py [year]

The frontend homepage and /api/calendar serve this file, so the calendar
no longer needs to be hardcoded anywhere.
"""

import json
import sys
import urllib.request
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# Stable circuitId -> 3-letter display code mapping
CIRCUIT_CODES = {
    "albert_park": "AUS",
    "shanghai": "CHN",
    "suzuka": "JPN",
    "bahrain": "BHR",
    "jeddah": "SAU",
    "miami": "MIA",
    "imola": "IMO",
    "villeneuve": "CAN",
    "monaco": "MON",
    "catalunya": "BCN",
    "red_bull_ring": "AUT",
    "silverstone": "GBR",
    "spa": "BEL",
    "hungaroring": "HUN",
    "zandvoort": "NED",
    "monza": "ITA",
    "madring": "MAD",
    "baku": "AZE",
    "marina_bay": "SGP",
    "americas": "USA",
    "rodriguez": "MEX",
    "interlagos": "SAO",
    "vegas": "LAS",
    "losail": "QAT",
    "yas_marina": "ABU",
}


def main() -> None:
    year = sys.argv[1] if len(sys.argv) > 1 else "2026"
    url = f"https://api.jolpi.ca/ergast/f1/{year}.json?limit=30"
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = json.load(resp)

    races = data["MRData"]["RaceTable"]["Races"]
    if not races:
        raise SystemExit(f"Jolpica returned no races for {year}")

    calendar = []
    for race in races:
        circuit = race["Circuit"]
        country = circuit.get("Location", {}).get("country", "")
        calendar.append(
            {
                "round": int(race["round"]),
                "code": CIRCUIT_CODES.get(circuit["circuitId"], country[:3].upper()),
                "name": race["raceName"].replace("Grand Prix", "GP").strip(),
                "full_name": race["raceName"],
                "date": race["date"],
                "circuit_id": circuit["circuitId"],
            }
        )

    out_path = DATA_DIR / "calendar.json"
    out_path.write_text(json.dumps(calendar, indent=2) + "\n")
    print(f"Wrote {len(calendar)} races to {out_path}")


if __name__ == "__main__":
    main()
