"""Export race data as a single markdown file for annotation generation.

Aggregates all API data sources into a readable markdown document that
Opus (claude.ai) can ingest to produce descriptor annotation JSONs.

Usage:
    python -m backend.scripts.export_for_annotations --race 2026-australia
    PYTHONPATH=. python backend/scripts/export_for_annotations.py 2026-australia
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

from backend.app.config import DATA_DIR
from backend.app.services.data_loader import (
    load_all_energy,
    load_laps,
    load_race_control,
    load_race_info,
    load_strategy,
)
from backend.app.services.descriptor import detect_all_events
from backend.app.services.preprocessing import (
    compute_delta_matrix,
    compute_energy_comparison,
    compute_traffic_analysis,
)


def fmt(val, decimals=3):
    """Format a numeric value for markdown tables."""
    if val is None:
        return "-"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


def fmt_time(seconds):
    """Format seconds as m:ss.SSS or ss.SSS."""
    if seconds is None:
        return "-"
    m = int(seconds) // 60
    s = seconds - m * 60
    if m > 0:
        return f"{m}:{s:06.3f}"
    return f"{s:.3f}"


def get_drivers_sorted_by_position(laps_data):
    """Return list of (driver, team, final_position) sorted by race finish."""
    laps_dict = laps_data.get("laps", {})
    teams = laps_data.get("teams", {})
    result = []
    for drv, drv_laps in laps_dict.items():
        positions = [l.get("position") for l in drv_laps if l.get("position") is not None]
        final_pos = positions[-1] if positions else 99
        result.append((drv, teams.get(drv, "?"), final_pos))
    result.sort(key=lambda x: x[2])
    return result


def build_race_info_section(race_info):
    lines = [
        "## Race Info\n",
        f"- **Race**: {race_info['name']}",
        f"- **Date**: {race_info['date']}",
        f"- **Circuit**: {race_info.get('circuit', 'Unknown')}",
        f"- **Winner**: {race_info['winner']}",
        f"- **Total Laps**: {race_info['total_laps']}",
        "",
    ]
    return "\n".join(lines)


def build_energy_comparison_section(entries):
    lines = [
        "## Energy Comparison (all drivers, D/C ratio sorted)\n",
        "| Rank | Driver | Team | Deploy % | Harvest % | Clip % | D/C Ratio |",
        "|------|--------|------|----------|-----------|--------|-----------|",
    ]
    for e in entries:
        lines.append(
            f"| {e['rank']} | {e['driver']} | {e['team']} | "
            f"{fmt(e['deploy_pct'])} | {fmt(e['harvest_pct'])} | "
            f"{fmt(e['clip_pct'])} | {fmt(e['dc_ratio'])} |"
        )
    lines.append("")
    return "\n".join(lines)


def build_vsc_section(race_control):
    vsc_laps = race_control.get("vsc_laps", [])
    sc_laps = race_control.get("sc_laps", [])
    messages = race_control.get("messages", [])

    lines = ["## VSC / SC Periods\n"]

    if not vsc_laps and not sc_laps:
        lines.append("No safety car periods in this race.\n")
        return "\n".join(lines)

    if vsc_laps:
        sorted_laps = sorted(vsc_laps)
        ranges = []
        start = sorted_laps[0]
        end = sorted_laps[0]
        for i in range(1, len(sorted_laps)):
            if sorted_laps[i] == end + 1:
                end = sorted_laps[i]
            else:
                ranges.append((start, end))
                start = sorted_laps[i]
                end = sorted_laps[i]
        ranges.append((start, end))

        lines.append(f"**VSC Laps**: {sorted_laps}")
        lines.append(f"**VSC Ranges**: {', '.join(f'Lap {s}-{e}' if s != e else f'Lap {s}' for s, e in ranges)}")
        lines.append("")

    if sc_laps:
        lines.append(f"**SC Laps**: {sorted(sc_laps)}")
        lines.append("")

    if messages:
        lines.append("### Race Control Messages\n")
        lines.append("| Lap | Category | Message |")
        lines.append("|-----|----------|---------|")
        for msg in messages:
            lap = msg.get("lap", "-")
            cat = msg.get("category", "-")
            text = msg.get("message", "-")
            lines.append(f"| {lap} | {cat} | {text} |")
        lines.append("")

    return "\n".join(lines)


def build_vsc_impact_section(race_control, strategy, laps_data):
    """VSC impact: who pitted, position changes during each VSC period."""
    vsc_laps = race_control.get("vsc_laps", [])
    sc_laps = race_control.get("sc_laps", [])
    all_neutralized = sorted(set(vsc_laps + sc_laps))

    lines = ["## VSC/SC Impact Summary\n"]

    if not all_neutralized:
        lines.append("No safety car periods in this race.\n")
        return "\n".join(lines)

    # Group consecutive laps into periods
    periods = []
    if all_neutralized:
        start = all_neutralized[0]
        end = all_neutralized[0]
        period_type = "VSC" if start in vsc_laps else "SC"
        for i in range(1, len(all_neutralized)):
            lap = all_neutralized[i]
            if lap == end + 1:
                end = lap
            else:
                periods.append((start, end, period_type))
                start = lap
                end = lap
                period_type = "VSC" if lap in vsc_laps else "SC"
        periods.append((start, end, period_type))

    laps_dict = laps_data.get("laps", {})

    # Build pit stop map: driver -> list of pit laps
    pit_map = {}
    for d in strategy.get("drivers", []):
        pit_map[d["driver"]] = d.get("pit_laps", [])

    for start_lap, end_lap, sc_type in periods:
        lines.append(f"### {sc_type} Period: Lap {start_lap}-{end_lap}\n")

        # Who pitted during this period?
        pitters = []
        for drv, pit_laps in pit_map.items():
            for pl in pit_laps:
                if start_lap - 1 <= pl <= end_lap + 1:
                    pitters.append((drv, pl))

        if pitters:
            lines.append("**Pit stops during this period:**\n")
            lines.append("| Driver | Pit Lap | Pos Before | Pos After | Net Change |")
            lines.append("|--------|---------|------------|-----------|------------|")

            for drv, pit_lap in pitters:
                drv_laps = laps_dict.get(drv, [])
                pos_before = None
                pos_after = None
                for l in drv_laps:
                    if l.get("lap") == pit_lap - 1 and l.get("position") is not None:
                        pos_before = l["position"]
                    if l.get("lap") == pit_lap + 1 and l.get("position") is not None:
                        pos_after = l["position"]

                net = None
                if pos_before is not None and pos_after is not None:
                    net = pos_before - pos_after  # positive = gained positions

                net_str = "-"
                if net is not None:
                    net_str = f"+{net}" if net > 0 else str(net)

                lines.append(
                    f"| {drv} | {pit_lap} | P{pos_before or '-'} | P{pos_after or '-'} | {net_str} |"
                )
        else:
            lines.append("No pit stops during this period.")

        # Position changes for all drivers across this period
        lines.append(f"\n**Position changes (Lap {start_lap-1} -> Lap {end_lap+1}):**\n")
        lines.append("| Driver | Pos Before | Pos After | Net Change |")
        lines.append("|--------|------------|-----------|------------|")

        changes = []
        for drv, drv_laps in laps_dict.items():
            pos_before = None
            pos_after = None
            for l in drv_laps:
                if l.get("lap") == start_lap - 1 and l.get("position") is not None:
                    pos_before = l["position"]
                if l.get("lap") == end_lap + 1 and l.get("position") is not None:
                    pos_after = l["position"]
            if pos_before is not None and pos_after is not None:
                net = pos_before - pos_after
                if net != 0:
                    changes.append((drv, pos_before, pos_after, net))

        changes.sort(key=lambda x: -x[3])  # biggest gainers first
        for drv, pb, pa, net in changes:
            net_str = f"+{net}" if net > 0 else str(net)
            lines.append(f"| {drv} | P{pb} | P{pa} | {net_str} |")

        if not changes:
            lines.append("| - | - | - | No changes |")

        lines.append("")

    return "\n".join(lines)


def build_strategy_section(strategy):
    drivers = strategy.get("drivers", [])
    lines = ["## Strategy Summary (all drivers)\n"]

    for d in drivers:
        lines.append(f"### {d['driver']} ({d.get('team', '?')})")
        lines.append("")

        lines.append("| Stint | Compound | Start Lap | End Lap | Laps |")
        lines.append("|-------|----------|-----------|---------|------|")
        for i, stint in enumerate(d.get("stints", []), 1):
            lines.append(
                f"| {i} | {stint['compound']} | {stint['start_lap']} | "
                f"{stint['end_lap']} | {stint['laps']} |"
            )

        pit_laps = d.get("pit_laps", [])
        if pit_laps:
            lines.append(f"\n**Pit stops**: Lap {', '.join(str(p) for p in pit_laps)}")
        lines.append("")

    return "\n".join(lines)


def build_lap_data_section(laps_data):
    """Full lap data for ALL drivers, sorted by race finish position."""
    laps_dict = laps_data.get("laps", {})
    drivers_sorted = get_drivers_sorted_by_position(laps_data)

    lines = [f"## All Drivers - Lap Data ({len(drivers_sorted)} drivers)\n"]

    for drv, team, final_pos in drivers_sorted:
        drv_laps = laps_dict.get(drv, [])
        lines.append(f"### {drv} ({team}) - Finished P{final_pos}\n")
        lines.append("| Lap | Time | S1 | S2 | S3 | Compound | Tire Age | Pos | Status | Accurate |")
        lines.append("|-----|------|----|----|----|---------|---------|----|--------|----------|")

        for lap in drv_laps:
            lines.append(
                f"| {lap.get('lap', '-')} "
                f"| {fmt_time(lap.get('time_s'))} "
                f"| {fmt_time(lap.get('s1'))} "
                f"| {fmt_time(lap.get('s2'))} "
                f"| {fmt_time(lap.get('s3'))} "
                f"| {lap.get('compound', '-')} "
                f"| {lap.get('tire_age', '-')} "
                f"| {lap.get('position', '-')} "
                f"| {lap.get('track_status', '-')} "
                f"| {lap.get('is_accurate', '-')} |"
            )
        lines.append("")

    return "\n".join(lines)


def build_energy_data_section(all_energy, laps_data):
    """Lap-by-lap energy data for ALL drivers."""
    drivers_sorted = get_drivers_sorted_by_position(laps_data)

    lines = [f"## Energy Data - All Drivers ({len(drivers_sorted)} drivers)\n"]

    for drv, team, final_pos in drivers_sorted:
        energy = all_energy.get(drv)
        if not energy:
            lines.append(f"### {drv} ({team}) - No energy data available\n")
            continue

        energy_laps = energy.get("laps", [])
        lines.append(f"### {drv} ({team}) - Finished P{final_pos}\n")
        lines.append("| Lap | Deploy % | Harvest % | Clip % | Neutral % | N.Deploy | N.Harvest | N.Clip | VSC |")
        lines.append("|-----|----------|-----------|--------|-----------|----------|-----------|--------|-----|")

        for lap in energy_laps:
            lines.append(
                f"| {lap.get('lap', '-')} "
                f"| {fmt(lap.get('deploy_pct', 0))} "
                f"| {fmt(lap.get('harvest_pct', 0))} "
                f"| {fmt(lap.get('clip_pct', 0))} "
                f"| {fmt(lap.get('neutral_pct', 0))} "
                f"| {fmt(lap.get('normalized_deploy', 0))} "
                f"| {fmt(lap.get('normalized_harvest', 0))} "
                f"| {fmt(lap.get('normalized_clip', 0))} "
                f"| {'Y' if lap.get('is_vsc') else ''} |"
            )
        lines.append("")

    return "\n".join(lines)


def build_traffic_section(traffic_result):
    """Traffic analysis section from compute_traffic_analysis output."""
    drivers = traffic_result.get("drivers", [])

    lines = ["## Traffic Analysis\n"]

    if not drivers:
        lines.append("No traffic data available.\n")
        return "\n".join(lines)

    # Summary table - all drivers
    lines.append("### Summary (all drivers, sorted by traffic %)\n")
    lines.append("| Driver | Team | Total Laps | Traffic Laps | Traffic % | Clean Air % | Pace Degradation |")
    lines.append("|--------|------|------------|-------------|-----------|-------------|------------------|")

    for d in drivers:
        clean_pct = round(100.0 - d["traffic_pct"], 1)
        deg_str = f"{d['pace_degradation']:+.2f}s" if d["pace_degradation"] is not None else "-"
        lines.append(
            f"| {d['driver']} | {d['team']} | {d['total_laps']} | {d['traffic_laps']} "
            f"| {d['traffic_pct']:.1f}% | {clean_pct:.1f}% | {deg_str} |"
        )
    lines.append("")

    # Most in traffic (top 5)
    top_traffic = [d for d in drivers if d["traffic_pct"] > 0][:5]
    if top_traffic:
        lines.append("### Most time in traffic (top 5)\n")
        for i, d in enumerate(top_traffic, 1):
            deg = f", pace loss: {d['pace_degradation']:+.2f}s" if d["pace_degradation"] is not None else ""
            lines.append(f"{i}. **{d['driver']}** ({d['team']}): {d['traffic_pct']:.1f}% in traffic{deg}")
        lines.append("")

    # Least in traffic (bottom 5)
    clean_drivers = sorted(drivers, key=lambda d: d["traffic_pct"])[:5]
    if clean_drivers:
        lines.append("### Most clean air (top 5)\n")
        for i, d in enumerate(clean_drivers, 1):
            lines.append(f"{i}. **{d['driver']}** ({d['team']}): {100.0 - d['traffic_pct']:.1f}% clean air")
        lines.append("")

    return "\n".join(lines)


def build_telemetry_speed_section(race_id):
    """Speed summary from telemetry files."""
    telemetry_dir = DATA_DIR / race_id / "telemetry"

    lines = ["## Telemetry Speed Summary\n"]

    if not telemetry_dir.exists():
        lines.append("Telemetry not available.\n")
        return "\n".join(lines)

    driver_speeds = []

    for f in sorted(telemetry_dir.glob("*.json")):
        try:
            with open(f) as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, IOError):
            continue

        drv = data.get("driver", f.stem.upper())
        team = data.get("team", "?")
        laps = data.get("laps", [])

        if not laps:
            continue

        # Per-lap max speeds
        lap_max_speeds = []
        overall_max = 0.0
        max_speed_lap = 0

        for lap_entry in laps:
            lap_num = lap_entry.get("lap", 0)
            samples = lap_entry.get("samples", [])
            if not samples:
                continue

            lap_top = max(s.get("speed", 0) for s in samples)
            lap_max_speeds.append(lap_top)

            if lap_top > overall_max:
                overall_max = lap_top
                max_speed_lap = lap_num

        avg_max_speed = statistics.mean(lap_max_speeds) if lap_max_speeds else 0.0

        driver_speeds.append({
            "driver": drv,
            "team": team,
            "max_speed": overall_max,
            "max_speed_lap": max_speed_lap,
            "avg_max_speed": avg_max_speed,
        })

    if not driver_speeds:
        lines.append("No telemetry data found.\n")
        return "\n".join(lines)

    # Sort by max speed descending for speed trap ranking
    driver_speeds.sort(key=lambda d: d["max_speed"], reverse=True)

    lines.append("### Speed Trap Ranking (by max speed)\n")
    lines.append("| Rank | Driver | Team | Max Speed (km/h) | On Lap | Avg Max Speed (km/h) |")
    lines.append("|------|--------|------|------------------|--------|----------------------|")

    for i, d in enumerate(driver_speeds, 1):
        lines.append(
            f"| {i} | {d['driver']} | {d['team']} "
            f"| {d['max_speed']:.1f} | {d['max_speed_lap']} "
            f"| {d['avg_max_speed']:.1f} |"
        )
    lines.append("")

    return "\n".join(lines)


def build_qualifying_section(race_id):
    """Qualifying results from qualifying.json."""
    qual_path = DATA_DIR / race_id / "qualifying.json"

    lines = ["## Qualifying Summary\n"]

    if not qual_path.exists():
        lines.append("Qualifying data not available.\n")
        return "\n".join(lines)

    try:
        with open(qual_path) as f:
            qual_data = json.load(f)
    except (json.JSONDecodeError, IOError):
        lines.append("Qualifying data not available.\n")
        return "\n".join(lines)

    drivers = qual_data.get("drivers", [])
    if not drivers:
        lines.append("No qualifying drivers found.\n")
        return "\n".join(lines)

    # Full results table
    lines.append("### Full Results\n")
    lines.append("| Pos | Driver | Team | Q1 | Q2 | Q3 | Gap to Pole |")
    lines.append("|-----|--------|------|----|----|----|-----------  |")

    for d in sorted(drivers, key=lambda x: x.get("position") or 99):
        q1 = d.get("q1", "-") or "-"
        q2 = d.get("q2", "-") or "-"
        q3 = d.get("q3", "-") or "-"
        gap = d.get("gap_to_pole")
        gap_str = f"+{gap:.3f}" if gap and gap > 0 else ("POLE" if gap == 0 else "-")
        lines.append(
            f"| {d.get('position', '-')} | {d['driver']} | {d['team']} "
            f"| {q1} | {q2} | {q3} | {gap_str} |"
        )
    lines.append("")

    # Eliminated drivers
    q1_elim = [d for d in drivers if d.get("eliminated_in") == "Q1"]
    q2_elim = [d for d in drivers if d.get("eliminated_in") == "Q2"]

    if q1_elim:
        lines.append("### Eliminated in Q1\n")
        for d in sorted(q1_elim, key=lambda x: x.get("position") or 99):
            lines.append(f"- **{d['driver']}** ({d['team']}): {d.get('q1', '-')}")
        lines.append("")

    if q2_elim:
        lines.append("### Eliminated in Q2\n")
        for d in sorted(q2_elim, key=lambda x: x.get("position") or 99):
            lines.append(f"- **{d['driver']}** ({d['team']}): Q1 {d.get('q1', '-')}, Q2 {d.get('q2', '-')}")
        lines.append("")

    # Best sectors (Q3 drivers only)
    q3_drivers = [d for d in drivers if d.get("q3_s") is not None and d.get("sectors")]
    if q3_drivers:
        lines.append("### Fastest Sectors (Q3)\n")
        for sector_key, sector_label in [("s1", "Sector 1"), ("s2", "Sector 2"), ("s3", "Sector 3")]:
            valid = [(d, d["sectors"][sector_key]) for d in q3_drivers if d.get("sectors", {}).get(sector_key)]
            if valid:
                valid.sort(key=lambda x: x[1])
                best_drv, best_time = valid[0]
                lines.append(f"- **{sector_label}**: {best_drv['driver']} ({best_time:.3f}s)")
        lines.append("")

    return "\n".join(lines)


def build_delta_matrix_section(delta):
    drivers = delta.get("drivers", [])
    matrix = delta.get("matrix", [])
    lines = ["## Delta Matrix\n"]

    if not drivers:
        lines.append("No delta data available.\n")
        return "\n".join(lines)

    lines.append("Positive = row driver slower than column driver.\n")

    header = "| Driver | " + " | ".join(drivers) + " |"
    sep = "|--------|" + "|".join(["--------"] * len(drivers)) + "|"
    lines.append(header)
    lines.append(sep)

    for i, drv in enumerate(drivers):
        row_vals = []
        for j, val in enumerate(matrix[i]):
            if i == j:
                row_vals.append("-")
            else:
                row_vals.append(fmt(val))
        lines.append(f"| {drv} | " + " | ".join(row_vals) + " |")

    lines.append("")
    return "\n".join(lines)


def build_detection_section(events, laps_data):
    lines = [
        "## Descriptor Detection Results\n",
        f"Total events detected: **{len(events)}**\n",
    ]

    if not events:
        lines.append("No events detected.\n")
        return "\n".join(lines)

    laps_dict = laps_data.get("laps", {})

    # Helper: get pace context around a lap
    def get_pace_context(driver, lap_num, window=2):
        drv_laps = laps_dict.get(driver, [])
        context = []
        for l in drv_laps:
            if abs(l.get("lap", 0) - lap_num) <= window and l.get("time_s") is not None:
                context.append((l["lap"], l["time_s"]))
        return context

    # Group by category
    categories = {}
    for ev in events:
        cat = ev.get("category", "unknown")
        categories.setdefault(cat, []).append(ev)

    for cat, cat_events in sorted(categories.items()):
        lines.append(f"### {cat.replace('_', ' ').title()} ({len(cat_events)} events)\n")

        if cat == "pace_anomaly":
            lines.append("| Driver | Lap | Delta (s) | Lap Time | Rolling Avg | Direction | Severity |")
            lines.append("|--------|-----|-----------|----------|-------------|-----------|----------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} "
                    f"| {fmt(d.get('delta'))} | {fmt_time(d.get('lap_time'))} "
                    f"| {fmt_time(d.get('rolling_avg'))} | {d.get('direction', '-')} "
                    f"| {ev.get('severity', '-')} |"
                )

        elif cat == "energy_shift":
            lines.append("| Driver | Lap | Field | Prev % | Curr % | Abs Change | Ratio | Direction | Severity |")
            lines.append("|--------|-----|-------|--------|--------|------------|-------|-----------|----------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} "
                    f"| {d.get('field', '-')} | {fmt(d.get('prev_value'))} "
                    f"| {fmt(d.get('curr_value'))} | {fmt(d.get('abs_change'))} "
                    f"| {d.get('ratio', '-')} | {d.get('direction', '-')} "
                    f"| {ev.get('severity', '-')} |"
                )

        elif cat == "safety_car":
            lines.append("| Lap | Type | Message |")
            lines.append("|-----|------|---------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['lap']} | {d.get('type', '-')} | {d.get('message', '-')} |"
                )

        elif cat == "pit_stop":
            lines.append("| Driver | Lap | Compound Before |")
            lines.append("|--------|-----|-----------------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} | {d.get('compound_before', '-')} |"
                )

        elif cat == "position_change":
            lines.append("| Driver | Lap | Positions | Direction | From | To | Severity | Pace Context (prev 2 + next 2 laps) |")
            lines.append("|--------|-----|-----------|-----------|------|----|----------|--------------------------------------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                # Get pace context around the position change
                ctx = get_pace_context(ev["driver"], ev["lap"], window=2)
                ctx_str = ", ".join(f"L{l}={fmt_time(t)}" for l, t in ctx) if ctx else "-"
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} "
                    f"| {d.get('positions', '-')} | {d.get('direction', '-')} "
                    f"| P{d.get('from_position', '-')} | P{d.get('to_position', '-')} "
                    f"| {ev.get('severity', '-')} | {ctx_str} |"
                )

        elif cat == "fastest_lap":
            lines.append("| Driver | Lap | Time |")
            lines.append("|--------|-----|------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} | {fmt_time(d.get('time_s'))} |"
                )

        else:
            lines.append("| Driver | Lap | Category | Severity | Detail |")
            lines.append("|--------|-----|----------|----------|--------|")
            for ev in cat_events:
                lines.append(
                    f"| {ev.get('driver', '-')} | {ev.get('lap', '-')} "
                    f"| {cat} | {ev.get('severity', '-')} "
                    f"| {json.dumps(ev.get('detail', {}), ensure_ascii=False)} |"
                )

        lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Export race data as markdown for annotation generation."
    )
    parser.add_argument(
        "--race",
        required=False,
        help="Race ID (e.g. 2026-australia)",
    )
    parser.add_argument(
        "race_id_positional",
        nargs="?",
        help="Race ID (positional, alternative to --race)",
    )

    args = parser.parse_args()
    race_id = args.race or args.race_id_positional

    if not race_id:
        parser.print_help()
        sys.exit(1)

    race_dir = DATA_DIR / race_id

    if not race_dir.exists():
        print(f"Error: Race directory not found: {race_dir}", file=sys.stderr)
        sys.exit(1)

    print(f"Exporting annotation data for: {race_id}", file=sys.stderr)
    print(f"Data directory: {race_dir}", file=sys.stderr)

    # Load all data
    race_info = load_race_info(race_id)
    laps_data = load_laps(race_id)
    strategy = load_strategy(race_id)
    race_control = load_race_control(race_id)
    all_energy = load_all_energy(race_id)

    print(f"  Drivers in laps: {len(laps_data.get('laps', {}))}", file=sys.stderr)
    print(f"  Drivers with energy: {len(all_energy)}", file=sys.stderr)
    print(f"  Strategy drivers: {len(strategy.get('drivers', []))}", file=sys.stderr)

    # Compute derived data
    energy_comparison = compute_energy_comparison(all_energy)
    delta = compute_delta_matrix(laps_data, race_control)
    events = detect_all_events(laps_data, all_energy, race_control)

    # Traffic analysis - needs telemetry
    telemetry_dir = race_dir / "telemetry"
    traffic_result = {"drivers": []}
    if telemetry_dir.exists():
        from backend.app.services.data_loader import load_telemetry
        all_telemetry = {}
        for f in sorted(telemetry_dir.glob("*.json")):
            driver = f.stem.upper()
            all_telemetry[driver] = load_telemetry(race_id, driver)
        traffic_result = compute_traffic_analysis(all_telemetry, laps_data, race_control)

    print(f"  Delta matrix drivers: {len(delta.get('drivers', []))}", file=sys.stderr)
    print(f"  Detected events: {len(events)}", file=sys.stderr)
    print(f"  Traffic drivers: {len(traffic_result.get('drivers', []))}", file=sys.stderr)

    # Build markdown
    sections = [
        f"# {race_info['name']} - Annotation Data Export\n",
        f"Exported for descriptor annotation generation. Race ID: `{race_id}`\n",
        build_race_info_section(race_info),
        build_qualifying_section(race_id),
        build_energy_comparison_section(energy_comparison),
        build_vsc_section(race_control),
        build_vsc_impact_section(race_control, strategy, laps_data),
        build_strategy_section(strategy),
        build_traffic_section(traffic_result),
        build_telemetry_speed_section(race_id),
        build_lap_data_section(laps_data),
        build_energy_data_section(all_energy, laps_data),
        build_delta_matrix_section(delta),
        build_detection_section(events, laps_data),
    ]

    output = "\n".join(sections)

    # Write to file AND stdout
    output_path = race_dir / "annotation_data.md"
    output_path.write_text(output, encoding="utf-8")

    # Print to stdout
    print(output)

    # Stats to stderr
    line_count = output.count("\n")
    size_kb = len(output.encode("utf-8")) / 1024
    print(f"\nOutput: {output_path}", file=sys.stderr)
    print(f"  Lines: {line_count}", file=sys.stderr)
    print(f"  Size: {size_kb:.1f} KB", file=sys.stderr)
    print("Done.", file=sys.stderr)


if __name__ == "__main__":
    main()
