"""Build data/classics.json from imported classic race directories.

Pulls spice/code/tags from generate_classic_annotations.META and the
winner's team from the race's own laps.json. Sorted chronologically.

Usage: python3 -m backend.scripts.build_classics 2021-bahrain 2021-abu-dhabi ...
"""

import json
import os
import sys
from pathlib import Path

from backend.scripts.generate_classic_annotations import META, match

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))


def main() -> None:
    ids = sys.argv[1:]
    if not ids:
        raise SystemExit("usage: build_classics <race_id> [...]")

    entries = []
    for rid in ids:
        d = DATA_DIR / rid
        info = json.loads((d / "race_info.json").read_text())
        teams = json.loads((d / "laps.json").read_text())["teams"]
        meta = match(rid, META) or (None, "", [])
        entries.append({
            "id": rid,
            "name": info["name"],
            "year": int(info["date"][:4]),
            "date": info["date"],
            "circuit": info["circuit"],
            "winner": info["winner"],
            "winner_team": teams.get(info["winner"], ""),
            "total_laps": info["total_laps"],
            "spice": meta[0],
            "code": meta[1],
            "tags": meta[2],
        })

    entries.sort(key=lambda e: e["date"])
    out = DATA_DIR / "classics.json"
    out.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n")
    print(f"classics.json: {len(entries)} races")


if __name__ == "__main__":
    main()
