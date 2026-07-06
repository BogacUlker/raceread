"""Build compact SVG silhouettes for all 2026 circuits from f1-circuits GeoJSON.

Source: https://github.com/bacinger/f1-circuits (MIT). Output: a JSON map of
calendar code -> SVG path string normalized into a 100x100 box, consumed by
frontend TrackSilhouette.svelte.
"""

import json
import math
import urllib.request

RAW = "https://raw.githubusercontent.com/bacinger/f1-circuits/master/circuits/{}.geojson"

FILES = {
    "AUS": "au-1953", "CHN": "cn-2004", "JPN": "jp-1962", "MIA": "us-2022",
    "CAN": "ca-1978", "MON": "mc-1929", "BCN": "es-1991", "AUT": "at-1969",
    "GBR": "gb-1948", "BEL": "be-1925", "HUN": "hu-1986", "NED": "nl-1948",
    "ITA": "it-1922", "MAD": "es-2026", "AZE": "az-2016", "SGP": "sg-2008",
    "USA": "us-2012", "MEX": "mx-1962", "SAO": "br-1940", "LAS": "us-2023",
    "QAT": "qa-2004", "ABU": "ae-2009",
}


def coords_of(gj):
    for feat in gj["features"]:
        geom = feat["geometry"]
        if geom["type"] == "LineString":
            return geom["coordinates"]
        if geom["type"] == "MultiLineString":
            return max(geom["coordinates"], key=len)
    raise ValueError("no linestring")


def to_path(coords, target_pts=110):
    lat0 = math.radians(sum(c[1] for c in coords) / len(coords))
    pts = [(c[0] * math.cos(lat0), -c[1]) for c in coords]  # flip y for SVG
    step = max(1, len(pts) // target_pts)
    pts = pts[::step]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    w, h = (maxx - minx) or 1, (maxy - miny) or 1
    s = 92 / max(w, h)
    ox, oy = (100 - w * s) / 2, (100 - h * s) / 2
    out = []
    for i, (px, py) in enumerate(pts):
        x = (px - minx) * s + ox
        y = (py - miny) * s + oy
        out.append(("M" if i == 0 else "L") + f"{x:.1f},{y:.1f}")
    return "".join(out) + "Z"


result = {}
for code, fname in FILES.items():
    with urllib.request.urlopen(RAW.format(fname), timeout=30) as r:
        gj = json.load(r)
    result[code] = to_path(coords_of(gj))
    print(code, len(result[code]), "chars")

out = "/private/tmp/claude-501/-Users-bogachanulker-Desktop-RACE-READ/03a43cd7-324d-457b-a9d0-e539dd97dd97/scratchpad/vps/circuit-paths.json"
with open(out, "w") as f:
    json.dump(result, f, separators=(",", ":"))
print("wrote", out, len(json.dumps(result)) // 1024, "KB")
