"""JSON data loader with in-memory LRU caching.

Reads race data from the filesystem and caches results to avoid
repeated disk I/O on subsequent requests.
"""

from functools import lru_cache
from pathlib import Path
import json
from typing import Any

from backend.app.config import DATA_DIR

# Separate cache for expensive computed results (traffic, etc.)
_computed_cache: dict[str, Any] = {}


def get_race_dir(race_id: str) -> Path:
    """Return the data directory for a given race ID."""
    return DATA_DIR / race_id


@lru_cache(maxsize=32)
def load_json(file_path: str) -> dict | list:
    """Load and cache a JSON file. Raises FileNotFoundError if missing."""
    with open(file_path) as f:
        return json.load(f)


def load_races() -> list[dict]:
    """Load the global races index. Returns empty list if file missing."""
    path = DATA_DIR / "races.json"
    if not path.exists():
        return []
    return load_json(str(path))


def load_race_info(race_id: str) -> dict:
    """Load race metadata for a specific race."""
    return load_json(str(get_race_dir(race_id) / "race_info.json"))


def load_laps(race_id: str) -> dict:
    """Load all lap data for a race (all drivers)."""
    return load_json(str(get_race_dir(race_id) / "laps.json"))


def load_energy(race_id: str, driver: str) -> dict:
    """Load energy inference data for a single driver."""
    return load_json(
        str(get_race_dir(race_id) / "energy" / f"{driver.lower()}.json")
    )


def load_all_energy(race_id: str) -> dict[str, dict]:
    """Load energy data for all drivers in a race.

    Returns a dict keyed by uppercase driver abbreviation.
    """
    energy_dir = get_race_dir(race_id) / "energy"
    result: dict[str, dict] = {}
    if energy_dir.exists():
        for f in sorted(energy_dir.glob("*.json")):
            driver = f.stem.upper()
            result[driver] = load_json(str(f))
    return result


def load_strategy(race_id: str) -> dict:
    """Load pit stop strategy data for a race."""
    return load_json(str(get_race_dir(race_id) / "strategy.json"))


def load_race_control(race_id: str) -> dict:
    """Load race control messages (SC, VSC, flags)."""
    return load_json(str(get_race_dir(race_id) / "race_control.json"))


def load_weather(race_id: str) -> dict:
    """Load weather data for a race."""
    return load_json(str(get_race_dir(race_id) / "weather.json"))


def load_annotations(race_id: str) -> dict:
    """Load descriptor annotations. Returns empty list if file missing."""
    path = get_race_dir(race_id) / "annotations.json"
    if not path.exists():
        return {"annotations": []}
    return load_json(str(path))


def load_qualifying(race_id: str) -> dict:
    """Load qualifying session data for a race."""
    return load_json(str(get_race_dir(race_id) / "qualifying.json"))


def load_telemetry(race_id: str, driver: str) -> dict:
    """Load per-sample telemetry data for a single driver."""
    return load_json(
        str(get_race_dir(race_id) / "telemetry" / f"{driver.lower()}.json")
    )


def load_telemetry_lap(race_id: str, driver: str, lap: int) -> dict | None:
    """Load telemetry for a single driver, returning only the requested lap.

    Uses the cached full file but filters before returning, avoiding
    serialization of unused laps over the wire.
    """
    data = load_telemetry(race_id, driver)
    for l in data.get("laps", []):
        if l["lap"] == lap:
            return {**data, "laps": [l]}
    return None


def load_all_telemetry(race_id: str) -> dict[str, dict]:
    """Load telemetry for all drivers in a race.

    Returns a dict keyed by uppercase driver abbreviation.
    Uses the LRU-cached load_telemetry per driver.
    """
    telemetry_dir = get_race_dir(race_id) / "telemetry"
    result: dict[str, dict] = {}
    if telemetry_dir.exists():
        for f in sorted(telemetry_dir.glob("*.json")):
            driver = f.stem.upper()
            result[driver] = load_telemetry(race_id, driver)
    return result


def get_computed_cache() -> dict[str, Any]:
    """Access the computed results cache."""
    return _computed_cache


def load_circuit(race_id: str) -> dict:
    """Load circuit info (corners, outline, track length)."""
    return load_json(str(get_race_dir(race_id) / "circuit.json"))
