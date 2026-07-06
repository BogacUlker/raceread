"""Spice score for 2024-2025 races from Jolpica results — candidate Classics."""
import json
import time
import urllib.request

BASE = "https://api.jolpi.ca/ergast/f1"


def get(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                return json.load(r)
        except Exception:
            time.sleep(2 + attempt * 2)
    raise SystemExit(f"failed: {url}")


def gap_seconds(t):
    # "+5.123" / "+1:02.456"
    t = t.lstrip("+")
    if ":" in t:
        m, s = t.split(":")
        return int(m) * 60 + float(s)
    try:
        return float(t)
    except ValueError:
        return None


rows = []
for year in (2024, 2025):
    sched = get(f"{BASE}/{year}.json?limit=30")["MRData"]["RaceTable"]["Races"]
    for race in sched:
        rnd = race["round"]
        res = get(f"{BASE}/{year}/{rnd}/results.json?limit=30")
        lst = res["MRData"]["RaceTable"]["Races"]
        if not lst:
            continue
        results = lst[0]["Results"]
        finishers = [r for r in results if r["status"] == "Finished" or "+" in r["status"]]
        dnfs = len(results) - len(finishers)
        # winner margin
        margin = None
        for r in results:
            if r["position"] == "2" and "Time" in r:
                margin = gap_seconds(r["Time"]["time"])
        # position volatility: |grid - finish| over classified, grid 0 -> 20 (pit lane)
        vol = 0
        for r in finishers:
            g = int(r["grid"]) or 20
            vol += abs(g - int(r["position"]))
        # winner came from where?
        wgrid = next((int(r["grid"]) or 20 for r in results if r["position"] == "1"), 1)
        winner = next((r["Driver"].get("code", "?") for r in results if r["position"] == "1"), "?")

        margin_score = 0 if margin is None else max(0, 20 - margin) / 20 * 30       # close finish: 0-30
        vol_score = min(vol, 90) / 90 * 35                                           # shuffle: 0-35
        dnf_score = min(dnfs, 8) / 8 * 15                                            # attrition: 0-15
        charge_score = min(max(wgrid - 1, 0), 9) / 9 * 20                            # winner charged: 0-20
        spice = round(margin_score + vol_score + dnf_score + charge_score, 1)

        rows.append({
            "year": year, "round": int(rnd), "name": race["raceName"],
            "spice": spice, "winner": winner, "wgrid": wgrid,
            "margin": margin, "vol": vol, "dnfs": dnfs,
        })
        time.sleep(0.5)

rows.sort(key=lambda r: -r["spice"])
print(f"{'SPICE':>5}  {'YIL':>4}  {'YARIŞ':<28} {'KAZANAN':<8} {'GRID':>4} {'FARK':>7} {'VOL':>4} {'DNF':>3}")
for r in rows[:16]:
    m = f"{r['margin']:.1f}s" if r["margin"] is not None else "SC/-"
    print(f"{r['spice']:>5}  {r['year']:>4}  {r['name']:<28} {r['winner']:<8} P{r['wgrid']:<3} {m:>7} {r['vol']:>4} {r['dnfs']:>3}")
print(f"\ntoplam {len(rows)} yarış skorlandı")
