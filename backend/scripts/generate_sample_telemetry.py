"""Generate synthetic telemetry and circuit data for testing.

Creates realistic-looking telemetry JSON files matching the format
produced by export_telemetry() and export_circuit() in import_race.py.
Uses Albert Park circuit characteristics.

Usage:
    python backend/scripts/generate_sample_telemetry.py
"""

import json
import math
import random
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RACE_ID = "2026-australia"

# Albert Park approximate track data
TRACK_LENGTH = 5278  # meters
NUM_CORNERS = 14

# Albert Park corners (approximate positions)
CORNERS = [
    {"number": 1, "distance": 220, "angle": 90, "letter": ""},
    {"number": 2, "distance": 420, "angle": 40, "letter": ""},
    {"number": 3, "distance": 880, "angle": 120, "letter": ""},
    {"number": 4, "distance": 1080, "angle": 30, "letter": ""},
    {"number": 5, "distance": 1320, "angle": 25, "letter": ""},
    {"number": 6, "distance": 1680, "angle": 90, "letter": ""},
    {"number": 7, "distance": 2050, "angle": 40, "letter": ""},
    {"number": 8, "distance": 2280, "angle": 30, "letter": ""},
    {"number": 9, "distance": 2780, "angle": 140, "letter": ""},
    {"number": 10, "distance": 3150, "angle": 90, "letter": ""},
    {"number": 11, "distance": 3680, "angle": 160, "letter": ""},
    {"number": 12, "distance": 4180, "angle": 100, "letter": ""},
    {"number": 13, "distance": 4550, "angle": 90, "letter": ""},
    {"number": 14, "distance": 4950, "angle": 60, "letter": ""},
]

# Generate track outline as a rough oval/lake shape
def generate_outline(n_points=200):
    """Generate Albert Park-like track outline."""
    outline = []
    for i in range(n_points):
        t = (i / n_points) * 2 * math.pi
        # Lake shape: elongated with irregular bends
        r_base = 800
        r_x = r_base * 1.3 + 150 * math.sin(3 * t) + 80 * math.cos(5 * t)
        r_y = r_base * 0.85 + 120 * math.cos(2 * t) + 60 * math.sin(4 * t)
        x = r_x * math.cos(t)
        y = r_y * math.sin(t)
        outline.append({"x": round(x, 1), "y": round(y, 1)})
    return outline


def corner_xy(outline, corners):
    """Assign X/Y to corners based on their distance fraction."""
    for c in corners:
        frac = c["distance"] / TRACK_LENGTH
        idx = int(frac * len(outline)) % len(outline)
        c["x"] = outline[idx]["x"]
        c["y"] = outline[idx]["y"]
    return corners


# Speed profile along the track
def speed_at_distance(dist, variation=0):
    """Generate realistic speed based on track position."""
    # Normalize to 0-1
    frac = (dist % TRACK_LENGTH) / TRACK_LENGTH

    # Base speed profile: high on straights, low in corners
    speed = 280  # base straight speed

    for c in CORNERS:
        c_frac = c["distance"] / TRACK_LENGTH
        delta = abs(frac - c_frac)
        if delta > 0.5:
            delta = 1.0 - delta

        # Speed reduction near corners proportional to angle
        if delta < 0.03:
            reduction = c["angle"] * 0.8
            speed -= reduction * (1 - delta / 0.03)

    # Add some randomness
    speed += random.gauss(0, 3) + variation
    speed = max(80, min(340, speed))
    return round(speed, 1)


def generate_driver_telemetry(driver, team, total_laps=58):
    """Generate telemetry for one driver."""
    outline = generate_outline()
    samples_per_lap = 150
    laps = []

    # Driver-specific variation
    driver_speed_offset = random.uniform(-5, 5)

    for lap_num in range(1, total_laps + 1):
        samples = []

        # Lap variation (tyre degradation, fuel effect)
        lap_variation = -0.5 * (lap_num / total_laps) + random.gauss(0, 1)

        for i in range(samples_per_lap):
            dist = round((i / samples_per_lap) * TRACK_LENGTH, 1)
            frac = i / samples_per_lap

            speed = speed_at_distance(dist, driver_speed_offset + lap_variation)

            # Throttle: high on straights, low in corners
            is_braking = False
            throttle = 100
            gear = 7

            for c in CORNERS:
                c_frac = c["distance"] / TRACK_LENGTH
                delta = frac - c_frac
                if -0.02 < delta < 0.01:
                    # Braking zone before corner
                    is_braking = True
                    throttle = 0
                    gear = max(2, 7 - int(c["angle"] / 30))
                elif 0 <= delta < 0.015:
                    # In corner
                    throttle = max(20, 100 - c["angle"] * 0.6)
                    gear = max(2, 7 - int(c["angle"] / 25))

            if not is_braking and throttle > 80:
                gear = min(8, max(5, int(speed / 50)))

            # Track position
            outline_idx = int(frac * len(outline)) % len(outline)
            x = outline[outline_idx]["x"]
            y = outline[outline_idx]["y"]

            # Energy state
            energy = "N"
            if is_braking and speed > 100:
                energy = "H"
            elif throttle >= 95 and random.random() < 0.15:
                energy = "D" if random.random() < 0.7 else "C"

            # Gap to driver ahead
            gap_ahead = None
            if random.random() < 0.7:
                gap_ahead = round(random.uniform(0.3, 3.0), 2)

            driver_ahead = None
            if gap_ahead is not None:
                others = ["RUS", "VER", "NOR", "LEC", "HAM", "ANT"]
                others = [d for d in others if d != driver]
                driver_ahead = random.choice(others)

            rpm = int(speed * 38 + random.gauss(0, 200))
            rpm = max(5000, min(15000, rpm))

            samples.append({
                "dist": dist,
                "speed": speed,
                "throttle": round(throttle, 0),
                "brake": is_braking,
                "gear": gear,
                "rpm": rpm,
                "x": round(x, 1),
                "y": round(y, 1),
                "driver_ahead": driver_ahead,
                "gap_ahead": gap_ahead,
                "energy": energy,
            })

        laps.append({"lap": lap_num, "samples": samples})

    return {
        "driver": driver,
        "team": team,
        "laps": laps,
    }


def main():
    race_dir = DATA_DIR / RACE_ID
    telemetry_dir = race_dir / "telemetry"
    telemetry_dir.mkdir(parents=True, exist_ok=True)

    # Generate circuit.json
    outline = generate_outline()
    corners = corner_xy(outline, CORNERS)

    circuit = {
        "corners": corners,
        "outline": outline,
        "track_length": TRACK_LENGTH,
    }

    circuit_path = race_dir / "circuit.json"
    with open(circuit_path, "w") as f:
        json.dump(circuit, f, indent=2)
    print(f"Wrote {circuit_path}")

    # Generate telemetry for each driver
    drivers = {
        "RUS": "Mercedes",
        "ANT": "Mercedes",
        "VER": "Red Bull Racing",
        "LEC": "Ferrari",
        "NOR": "McLaren",
        "HAM": "Ferrari",
    }

    for driver, team in drivers.items():
        print(f"Generating telemetry for {driver}...")
        data = generate_driver_telemetry(driver, team)

        path = telemetry_dir / f"{driver.lower()}.json"
        with open(path, "w") as f:
            json.dump(data, f)  # no indent for size

        size_kb = path.stat().st_size / 1024
        print(f"  Wrote {path} ({size_kb:.0f} KB)")

    print("\nDone! Sample telemetry and circuit data generated.")


if __name__ == "__main__":
    main()
