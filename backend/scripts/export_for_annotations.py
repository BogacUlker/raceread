"""Export race data as a single markdown file for annotation generation.

Aggregates all API data sources into a readable markdown document that
Opus (claude.ai) can ingest to produce descriptor annotation JSONs.

Usage:
    PYTHONPATH=. python backend/scripts/export_for_annotations.py 2026-australia
"""

import json
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
        # Group consecutive laps into ranges
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


def build_strategy_section(strategy):
    drivers = strategy.get("drivers", [])
    lines = ["## Strategy Summary (all drivers)\n"]

    for d in drivers:
        lines.append(f"### {d['driver']} ({d.get('team', '?')})")
        lines.append("")

        # Stints
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


def build_lap_data_section(laps_data, top_n=10):
    """Full lap data for top N drivers by final position."""
    laps_dict = laps_data.get("laps", {})
    teams = laps_data.get("teams", {})

    # Determine top N drivers by final lap position
    driver_final_pos = []
    for drv, drv_laps in laps_dict.items():
        positions = [l.get("position") for l in drv_laps if l.get("position") is not None]
        final_pos = positions[-1] if positions else 99
        driver_final_pos.append((drv, final_pos))
    driver_final_pos.sort(key=lambda x: x[1])
    top_drivers = [d for d, _ in driver_final_pos[:top_n]]

    lines = [f"## Top {top_n} Drivers - Lap Data\n"]

    for drv in top_drivers:
        drv_laps = laps_dict.get(drv, [])
        team = teams.get(drv, "?")
        lines.append(f"### {drv} ({team})\n")
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


def build_energy_data_section(all_energy, laps_data, top_n=10):
    """Lap-by-lap energy data for top N drivers."""
    laps_dict = laps_data.get("laps", {})

    # Same top N logic
    driver_final_pos = []
    for drv, drv_laps in laps_dict.items():
        positions = [l.get("position") for l in drv_laps if l.get("position") is not None]
        final_pos = positions[-1] if positions else 99
        driver_final_pos.append((drv, final_pos))
    driver_final_pos.sort(key=lambda x: x[1])
    top_drivers = [d for d, _ in driver_final_pos[:top_n]]

    lines = [f"## Energy Data - Top {top_n} Drivers\n"]

    for drv in top_drivers:
        energy = all_energy.get(drv)
        if not energy:
            lines.append(f"### {drv} - No energy data available\n")
            continue

        team = energy.get("team", "?")
        energy_laps = energy.get("laps", [])
        lines.append(f"### {drv} ({team})\n")
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


def build_delta_matrix_section(delta):
    drivers = delta.get("drivers", [])
    matrix = delta.get("matrix", [])
    lines = ["## Delta Matrix\n"]

    if not drivers:
        lines.append("No delta data available.\n")
        return "\n".join(lines)

    lines.append("Positive = row driver slower than column driver.\n")

    # Header
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


def build_detection_section(events):
    lines = [
        "## Descriptor Detection Results\n",
        f"Total events detected: **{len(events)}**\n",
    ]

    if not events:
        lines.append("No events detected.\n")
        return "\n".join(lines)

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
            lines.append("| Driver | Lap | Positions | Direction | From | To | Severity |")
            lines.append("|--------|-----|-----------|-----------|------|----|----------|")
            for ev in cat_events:
                d = ev.get("detail", {})
                lines.append(
                    f"| {ev['driver']} | {ev['lap']} "
                    f"| {d.get('positions', '-')} | {d.get('direction', '-')} "
                    f"| P{d.get('from_position', '-')} | P{d.get('to_position', '-')} "
                    f"| {ev.get('severity', '-')} |"
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
    if len(sys.argv) < 2:
        print("Usage: PYTHONPATH=. python backend/scripts/export_for_annotations.py <race_id>")
        print("Example: PYTHONPATH=. python backend/scripts/export_for_annotations.py 2026-australia")
        sys.exit(1)

    race_id = sys.argv[1]
    race_dir = DATA_DIR / race_id

    if not race_dir.exists():
        print(f"Error: Race directory not found: {race_dir}")
        sys.exit(1)

    print(f"Exporting annotation data for: {race_id}")
    print(f"Data directory: {race_dir}")

    # Load all data
    race_info = load_race_info(race_id)
    laps_data = load_laps(race_id)
    strategy = load_strategy(race_id)
    race_control = load_race_control(race_id)
    all_energy = load_all_energy(race_id)

    print(f"  Drivers in laps: {len(laps_data.get('laps', {}))}")
    print(f"  Drivers with energy: {len(all_energy)}")
    print(f"  Strategy drivers: {len(strategy.get('drivers', []))}")

    # Compute derived data
    energy_comparison = compute_energy_comparison(all_energy)
    delta = compute_delta_matrix(laps_data, race_control)
    events = detect_all_events(laps_data, all_energy, race_control)

    print(f"  Delta matrix drivers: {len(delta.get('drivers', []))}")
    print(f"  Detected events: {len(events)}")

    # Build markdown
    sections = [
        f"# {race_info['name']} - Annotation Data Export\n",
        f"Exported for descriptor annotation generation. Race ID: `{race_id}`\n",
        build_race_info_section(race_info),
        build_energy_comparison_section(energy_comparison),
        build_vsc_section(race_control),
        build_strategy_section(strategy),
        build_lap_data_section(laps_data),
        build_energy_data_section(all_energy, laps_data),
        build_delta_matrix_section(delta),
        build_detection_section(events),
    ]

    output = "\n".join(sections)

    # Write to file
    output_path = race_dir / "annotation_data.md"
    output_path.write_text(output, encoding="utf-8")

    # Stats
    line_count = output.count("\n")
    size_kb = len(output.encode("utf-8")) / 1024

    print(f"\nOutput: {output_path}")
    print(f"  Lines: {line_count}")
    print(f"  Size: {size_kb:.1f} KB")
    print("Done.")


if __name__ == "__main__":
    main()
