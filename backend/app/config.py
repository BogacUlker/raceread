import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(BASE_DIR / "data")))
FASTF1_CACHE_DIR = Path(os.getenv("FASTF1_CACHE_DIR", str(BASE_DIR / "fastf1_cache")))

# CORS
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://raceread.app").split(",")

# Energy inference thresholds
DEPLOY_SIGMA = 1.5
CLIP_SIGMA = 2.0
HARVEST_DECEL = -0.3  # m/s^2
CLIP_THROTTLE_MIN = 95  # %
DEPLOY_THROTTLE_MIN = 80  # %
GAUSSIAN_SIGMA = 1.5
SPEED_BIN_WIDTH = 10  # km/h

# Descriptor detection thresholds
PACE_ANOMALY_DELTA = 0.5  # seconds from rolling 3-lap avg
ENERGY_SHIFT_RATIO = 2.0  # 2x change between laps
ENERGY_SHIFT_ABSOLUTE = 1.5  # % minimum absolute change
POSITION_CHANGE_THRESHOLD = 2  # positions

# Min laps for valid driver data
MIN_LAPS_THRESHOLD = 10

# Team color fallback map (FastF1 get_team_color() primary, this is backup)
TEAM_COLORS = {
    "Mercedes": "#27F4D2",
    "Red Bull Racing": "#3671C6",
    "Ferrari": "#E8002D",
    "McLaren": "#FF8000",
    "Aston Martin": "#229971",
    "Alpine": "#FF87BC",
    "Williams": "#64C4FF",
    "RB": "#6692FF",
    "Kick Sauber": "#52E252",
    "Haas F1 Team": "#B6BABD",
}

# Energy state colors
ENERGY_COLORS = {
    "deploy": "#22C55E",
    "harvest": "#3B82F6",
    "clip": "#F59E0B",
    "neutral": "#6B7280",
}
