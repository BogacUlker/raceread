"""Generate race annotations using Claude API.

Exports race data via export_for_annotations, sends to Claude API
with system prompt, saves resulting annotations JSON.

Usage:
    cd /root/raceread
    ANTHROPIC_API_KEY=sk-xxx python -m backend.scripts.generate_annotations --race 2026-australia

Requirements:
    pip install anthropic
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Generate annotations via Claude API")
    parser.add_argument("--race", required=True, help="Race ID (e.g. 2026-australia)")
    parser.add_argument("--model", default="claude-sonnet-4-6", help="Claude model to use")
    parser.add_argument("--dry-run", action="store_true", help="Export data only, don't call API")
    args = parser.parse_args()

    race_id = args.race
    script_dir = Path(__file__).parent
    data_dir = Path(os.environ.get("DATA_DIR", "/root/raceread/data"))
    race_dir = data_dir / race_id

    if not race_dir.exists():
        print(f"Error: Race directory not found: {race_dir}", file=sys.stderr)
        sys.exit(1)

    # 1. Export race data as markdown
    print(f"[1/4] Exporting race data for {race_id}...", file=sys.stderr)
    result = subprocess.run(
        [sys.executable, "-m", "backend.scripts.export_for_annotations", "--race", race_id],
        capture_output=True, text=True, cwd="/root/raceread"
    )
    if result.returncode != 0:
        print(f"Export failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    race_data_md = result.stdout
    print(f"  Exported {len(race_data_md)} chars", file=sys.stderr)

    if args.dry_run:
        print(race_data_md)
        print("\n[DRY RUN] Skipping API call.", file=sys.stderr)
        sys.exit(0)

    # 2. Load system prompt
    print("[2/4] Loading system prompt...", file=sys.stderr)
    prompt_path = script_dir / "annotation_system_prompt.md"
    if not prompt_path.exists():
        print(f"Error: System prompt not found: {prompt_path}", file=sys.stderr)
        sys.exit(1)
    system_prompt = prompt_path.read_text(encoding="utf-8")

    # 3. Call Claude API
    print(f"[3/4] Calling Claude API ({args.model})...", file=sys.stderr)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.", file=sys.stderr)
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("Error: 'anthropic' package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    message = client.messages.create(
        model=args.model,
        max_tokens=16384,
        system=system_prompt,
        messages=[
            {
                "role": "user",
                "content": f"Generate annotations for this race:\n\n{race_data_md}"
            }
        ]
    )

    response_text = message.content[0].text
    print(f"  Response: {len(response_text)} chars, {message.usage.input_tokens} input tokens, {message.usage.output_tokens} output tokens", file=sys.stderr)

    # 4. Parse and save
    print("[4/4] Saving annotations...", file=sys.stderr)

    # Strip markdown code fences if present
    clean = response_text.strip()
    if clean.startswith("```"):
        clean = clean.split("\n", 1)[1]  # remove first line
    if clean.endswith("```"):
        clean = clean.rsplit("```", 1)[0]
    clean = clean.strip()

    try:
        annotations = json.loads(clean)
    except json.JSONDecodeError as e:
        print(f"Error: Failed to parse API response as JSON: {e}", file=sys.stderr)
        print(f"Response:\n{response_text[:500]}...", file=sys.stderr)
        # Save raw response for debugging
        raw_path = race_dir / "annotations_raw.txt"
        raw_path.write_text(response_text, encoding="utf-8")
        print(f"  Raw response saved to: {raw_path}", file=sys.stderr)
        sys.exit(1)

    # Validate structure
    ann_list = annotations.get("annotations", [])
    print(f"  Generated {len(ann_list)} annotations", file=sys.stderr)

    # Save
    output_path = race_dir / "annotations.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(annotations, f, ensure_ascii=False, indent=2)

    print(f"  Saved to: {output_path}", file=sys.stderr)

    # Summary
    categories = {}
    for a in ann_list:
        cat = a.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1

    print("\n  Category distribution:", file=sys.stderr)
    for cat, count in sorted(categories.items()):
        print(f"    {cat}: {count}", file=sys.stderr)

    print(f"\nDone! {len(ann_list)} annotations generated for {race_id}.", file=sys.stderr)


if __name__ == "__main__":
    main()
