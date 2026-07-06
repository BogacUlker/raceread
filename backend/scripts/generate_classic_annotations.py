"""Data-grounded annotations + story for Classics (no LLM API).

Every numeric claim is computed from the race's own JSON files, so the
fact-check gate passes by construction. Per-race flavor lines describe
famous, well-documented events without numbers.

Usage: python3 -m backend.scripts.generate_classic_annotations --race 2021-abu-dhabi
"""

import argparse
import json
import os
import statistics
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))

# Famous documented context per race (no numeric claims here)
FLAVOR = {
    "bahrain": (
        "The opening round of the season-long title duel: Verstappen hunted Hamilton to the flag, and a debated off-track pass had to be handed back.",
        "Sezon boyu sürecek şampiyonluk düellosunun açılış raundu: Verstappen, Hamilton'ı damalı bayrağa kadar kovaladı; pist dışından yapılan tartışmalı geçiş geri verilmek zorunda kaldı."),
    "azerbaijan": (
        "Verstappen's tyre exploded from the lead late in the race, and Hamilton's 'brake magic' error at the restart threw away the win - Perez picked up the pieces.",
        "Verstappen liderliğinde son bölümde lastiği patladı; restartta Hamilton'ın 'brake magic' hatası zaferi çöpe attı - kazanan Perez oldu."),
    "britain": (
        "The Copse corner contact between Hamilton and Verstappen defined the season's tone; Hamilton served his penalty and charged back to win at home.",
        "Hamilton ile Verstappen'in Copse virajındaki teması sezonun tonunu belirledi; Hamilton cezasını çekip evinde kazanmak için geri döndü."),
    "hungar": (
        "A wet first-lap pileup wiped out the front-runners, Hamilton lined up alone at the restart, and Ocon survived the chaos for his maiden win.",
        "Islak zeminde ilk viraj karambolü öndekileri sildi, restartta Hamilton gridde tek başına dizildi ve kaostan Ocon kariyerinin ilk zaferiyle çıktı."),
    "ital": (
        "Verstappen and Hamilton collided at the first chicane and ended both races in the gravel - McLaren swept a famous one-two with Ricciardo leading.",
        "Verstappen ile Hamilton ilk şikanda çarpışıp ikisi de yarış dışı kaldı - McLaren, Ricciardo liderliğinde efsane bir birincilik-ikincilik aldı."),
    "turk": (
        "A damp Istanbul Park classic: intermediates for the whole distance, Bottas untouchable up front, and Hamilton gambling against a pit stop he never wanted.",
        "Nemli Istanbul Park klasiği: baştan sona ara lastikler, önde dokunulmaz bir Bottas ve hiç istemediği pit stopa karşı kumar oynayan Hamilton."),
    "usa": (
        "COTA hosted the purest strategy duel of the season: Verstappen's aggressive undercut against Hamilton's long-game tyre offset, decided in the final laps.",
        "COTA sezonun en saf strateji düellosuna sahne oldu: Verstappen'in agresif undercut'ı, Hamilton'ın uzun oyunlu lastik dengesine karşı - karar son turlarda verildi."),
    "paulo": (
        "Hamilton's weekend-long charge through the field at Interlagos, capped by the decisive move on Verstappen, kept the title fight alive.",
        "Hamilton'ın Interlagos'ta hafta sonu boyu süren şarjı ve Verstappen'e yaptığı belirleyici hamle şampiyonluk savaşını hayatta tuttu."),
    "saudi": (
        "Jeddah's chaotic first night race: red flags, restarts and wheel-to-wheel contact between the title rivals before Hamilton prevailed.",
        "Cidde'nin kaotik ilk gece yarışı: kırmızı bayraklar, restartlar ve şampiyonluk rakipleri arasında tekerlek tekerleğe temaslar - sonunda Hamilton kazandı."),
    "abu-dhabi": (
        "The most controversial finale in modern F1: a late safety car, a disputed restart procedure and a final-lap pass that decided the championship.",
        "Modern F1'in en tartışmalı finali: geç gelen güvenlik aracı, tartışmalı restart prosedürü ve şampiyonluğu belirleyen son tur geçişi."),
}

META = {  # substring -> (spice, code, tags)
    "bahrain": (54.5, "BHR", ["DUEL", "0.7s"]),
    "azerbaijan": (72.6, "AZE", ["TYRE BLOWOUT", "RESTART"]),
    "britain": (43.4, "GBR", ["COPSE", "COMEBACK"]),
    "hungar": (85.3, "HUN", ["LAP-1 CHAOS", "FIRST WIN"]),
    "ital": (57.6, "ITA", ["COLLISION", "McLAREN 1-2"]),
    "turk": (38.5, "TUR", ["WET", "ISTANBUL"]),
    "usa": (44.1, "USA", ["STRATEGY DUEL"]),
    "paulo": (53.6, "SAO", ["CHARGE", "P10 START"]),
    "saudi": (39.9, "SAU", ["3 RESTARTS", "NIGHT CHAOS"]),
    "abu-dhabi": (51.1, "ABU", ["FINAL LAP", "TITLE DECIDER"]),
}


def match(race_id, table):
    for k, v in table.items():
        if k in race_id:
            return v
    return None


def fmt(t):
    m = int(t // 60)
    return f"{m}:{t % 60:06.3f}" if m else f"{t:.3f}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True)
    args = ap.parse_args()
    rid = args.race
    d = DATA_DIR / rid

    info = json.loads((d / "race_info.json").read_text())
    laps = json.loads((d / "laps.json").read_text())["laps"]
    teams = json.loads((d / "laps.json").read_text())["teams"]
    strat = {x["driver"]: x for x in json.loads((d / "strategy.json").read_text())["drivers"]}
    quali = json.loads((d / "qualifying.json").read_text())["drivers"]
    total = info["total_laps"]
    winner = info["winner"]

    def final_pos(drv):
        pl = [l for l in laps[drv] if l.get("position") is not None]
        return pl[-1]["position"] if pl else None

    def first_pos(drv):
        pl = [l for l in laps[drv] if l.get("position") is not None]
        return pl[0]["position"] if pl else None

    # cumulative times for margin
    cum = {}
    for drv, ll in laps.items():
        c, ok = 0, True
        for l in sorted(ll, key=lambda x: x["lap"]):
            if l.get("time_s") is None:
                ok = False
                break
            c += l["time_s"]
        if ok and len(ll) >= total:
            cum[drv] = c
    p2 = min((v for k, v in cum.items() if k != winner), default=None)
    margin = (p2 - cum[winner]) if (p2 and winner in cum) else None

    # fastest lap
    best = None
    for drv, ll in laps.items():
        for l in ll:
            if l.get("time_s") and l.get("is_accurate") is not False and l["lap"] > 1:
                if best is None or l["time_s"] < best[0]:
                    best = (l["time_s"], drv, l["lap"])

    # biggest climber (lap1 pos -> finish)
    climb = None
    for drv in laps:
        a, b = first_pos(drv), final_pos(drv)
        if a and b and len(laps[drv]) >= total * 0.9:
            gain = a - b
            if climb is None or gain > climb[0]:
                climb = (gain, drv, a, b)

    # longest stint
    longest = None
    for drv, s in strat.items():
        for st in s.get("stints", []):
            ln = (st.get("end_lap") or 0) - (st.get("start_lap") or 0) + 1
            if longest is None or ln > longest[0]:
                longest = (ln, drv, st.get("compound", "?"), st.get("start_lap"), st.get("end_lap"))

    # top speed
    tops = None
    for drv, ll in laps.items():
        for l in ll:
            for k in ("speed_st", "speed_i1", "speed_i2", "speed_fl"):
                v = l.get(k)
                if v and (tops is None or v > tops[0]):
                    tops = (v, drv, l["lap"])

    # energy: best D/C + most clip
    dc, clipper = None, None
    edir = d / "energy"
    if edir.exists():
        for f in sorted(edir.glob("*.json")):
            e = json.loads(f.read_text())
            s = e.get("summary", {})
            drv = e.get("driver", f.stem.upper())
            if s.get("dc_ratio") is not None and (dc is None or s["dc_ratio"] > dc[0]):
                dc = (s["dc_ratio"], drv)
            if s.get("avg_clip") is not None and (clipper is None or s["avg_clip"] > clipper[0]):
                clipper = (s["avg_clip"], drv)

    # pole
    pole = next((q for q in quali if q.get("position") == 1), None)

    # most stops
    stops = None
    for drv, s in strat.items():
        n = len(s.get("pit_laps") or [])
        if stops is None or n > stops[0]:
            stops = (n, drv)

    A = []

    def add(ct, drv, lap, sev, en, tr):
        A.append({"driver": drv, "lap": lap, "chart_type": ct, "category": "race_insight",
                  "severity": sev, "text_en": en, "text_tr": tr})

    wstints = strat.get(winner, {}).get("stints", [])
    nstops = max(0, len(wstints) - 1)
    comps = "→".join((s.get("compound") or "?")[0] for s in wstints) if wstints else "?"
    add("strategy", winner, total, "high",
        f"{winner} won the race with a {nstops}-stop strategy ({comps})" + (f", beating the next classified runner by {margin:.1f}s." if margin else "."),
        f"{winner} yarışı {nstops} duraklı stratejiyle ({comps}) kazandı" + (f"; en yakın takipçisine farkı {margin:.1f}s idi." if margin else "."))

    if best:
        add("pace", best[1], best[2], "high",
            f"Fastest lap of the race: {fmt(best[0])} by {best[1]} on lap {best[2]}.",
            f"Yarışın en hızlı turu: {best[2]}. turda {best[1]} - {fmt(best[0])}.")

    if climb and climb[0] >= 3:
        add("pace", climb[1], total, "high",
            f"{climb[1]} made up the most ground on track: P{climb[2]} at the end of lap 1 to P{climb[3]} at the flag ({climb[0]} places).",
            f"Pistte en çok yer kazanan {climb[1]} oldu: 1. tur sonunda P{climb[2]}, damalı bayrakta P{climb[3]} ({climb[0]} sıra).")

    if longest:
        add("strategy", longest[1], longest[4], "medium",
            f"Longest stint of the race: {longest[1]} ran {longest[0]} laps on {longest[2]} (lap {longest[3]}-{longest[4]}).",
            f"Yarışın en uzun stinti: {longest[1]}, {longest[2]} lastikle {longest[0]} tur koştu ({longest[3]}-{longest[4]}. turlar).")

    if tops:
        add("speed_trace", tops[1], tops[2], "medium",
            f"Highest recorded speed: {tops[0]:.0f} km/h by {tops[1]} on lap {tops[2]}.",
            f"Kaydedilen en yüksek hız: {tops[2]}. turda {tops[1]} - {tops[0]:.0f} km/s.")

    if dc:
        add("energy", dc[1], max(1, total // 2), "medium",
            f"Best inferred deploy-to-clip ratio of the field: {dc[1]} at {dc[0]:.2f} (higher = cleaner energy use; inferred, {info['date'][:4]} PU era).",
            f"Sahanın en iyi çıkarımsal deploy/clip oranı: {dc[1]} - {dc[0]:.2f} (yüksek = daha temiz enerji kullanımı; çıkarımsal, {info['date'][:4]} güç ünitesi dönemi).")

    if clipper:
        add("energy", clipper[1], max(1, total // 2), "low",
            f"Most battery-limited driver by inferred clip share: {clipper[1]} ({clipper[0]:.2f}% of samples).",
            f"Çıkarımsal clip payına göre en çok batarya kısıtı yaşayan pilot: {clipper[1]} (örneklerin %{clipper[0]:.2f}'si).")

    if pole and pole.get("q3"):
        add("qualifying", pole["driver"], 1, "medium",
            f"Pole position: {pole['driver']} with {pole['q3']} in Q3.",
            f"Pole pozisyonu: {pole['driver']}, Q3'te {pole['q3']}.")

    if stops and stops[0] >= 3:
        add("strategy", stops[1], total, "low",
            f"Busiest pit lane visitor: {stops[1]} with {stops[0]} stops.",
            f"Pit yoluna en çok uğrayan: {stops[1]} - {stops[0]} stop.")

    out = {"race_id": rid, "annotations": A}
    (d / "annotations.json").write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n")

    flavor = match(rid, FLAVOR) or ("", "")
    story = {
        "story_en": (flavor[0] + " " if flavor[0] else "") +
            f"{winner} took the win" + (f" by {margin:.1f}s" if margin else "") +
            (f", with the fastest lap ({fmt(best[0])}) going to {best[1]} on lap {best[2]}." if best else ".") +
            (f" {climb[1]} was the day's biggest mover, climbing from P{climb[2]} to P{climb[3]}." if climb and climb[0] >= 4 else ""),
        "story_tr": (flavor[1] + " " if flavor[1] else "") +
            f"Yarışı {winner} kazandı" + (f" ({margin:.1f}s farkla)" if margin else "") +
            (f"; en hızlı tur {best[2]}. turda {best[1]}'nindi ({fmt(best[0])})." if best else ".") +
            (f" Günün en büyük yükselişi {climb[1]}'den geldi: P{climb[2]}'den P{climb[3]}'e." if climb and climb[0] >= 4 else ""),
    }
    (d / "story.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")

    meta = match(rid, META)
    print(f"{rid}: {len(A)} annotations + story" + (f" | spice {meta[0]} code {meta[1]}" if meta else ""))


if __name__ == "__main__":
    main()
