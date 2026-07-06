"""Generate a 3-4 sentence bilingual race story from verified annotations.

Runs after generate_annotations.py + fact-checking, so the story is built
ONLY from claims that already survived verification. Writes
data/<race>/story.json with {story_en, story_tr}.

Usage (on the VPS, system python3 has `anthropic`):
    export ANTHROPIC_API_KEY=... && python3 -m backend.scripts.generate_story --race 2026-<slug>
"""

import argparse
import json
import os
from pathlib import Path

import anthropic

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))
MODEL = "claude-sonnet-4-6"

SYSTEM = """You write the opening summary block for an F1 post-race analysis dashboard.

Input: verified race annotations (already fact-checked against telemetry) and race metadata.

Write a "race story": 3-4 sentences that tell a first-time visitor what decided this race.
Lead with the winner and the decisive moment, mention at most 2-3 drivers, and only use
facts and numbers that literally appear in the annotations or metadata. Do not invent or
recompute anything. No em dashes. Refer to drivers by surname.

Then translate it to natural Turkish with proper diacritics (ş, ç, ğ, ü, ö, ı, İ).
Turkish must be a faithful translation, not a new text.

Return ONLY valid JSON: {"story_en": "...", "story_tr": "..."}"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--race", required=True)
    args = parser.parse_args()

    race_dir = DATA_DIR / args.race
    info = json.loads((race_dir / "race_info.json").read_text())
    ann = json.loads((race_dir / "annotations.json").read_text())
    anns = ann.get("annotations", ann) if isinstance(ann, dict) else ann

    facts = [a.get("text_en", "") for a in anns if a.get("text_en")]
    user = (
        f"Race: {info['name']}, {info['circuit']}, {info['date']}. "
        f"Winner: {info['winner']}. Total laps: {info['total_laps']}.\n\n"
        "Verified annotations:\n- " + "\n- ".join(facts)
    )

    client = anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM,
        messages=[{"role": "user", "content": user}],
        # forced tool use guarantees schema-valid structured output
        tools=[
            {
                "name": "submit_story",
                "description": "Submit the bilingual race story.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "story_en": {"type": "string"},
                        "story_tr": {"type": "string"},
                    },
                    "required": ["story_en", "story_tr"],
                },
            }
        ],
        tool_choice={"type": "tool", "name": "submit_story"},
    )
    story = next(b.input for b in resp.content if b.type == "tool_use")
    assert story.get("story_en") and story.get("story_tr"), "incomplete story"

    out = race_dir / "story.json"
    out.write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n")
    print(f"{args.race}: story written ({len(story['story_en'])} chars EN)")


if __name__ == "__main__":
    main()
