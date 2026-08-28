"""Transcribe team-radio clips into curation candidates.

Runs LOCALLY on the Mac only: mlx-whisper needs Apple Silicon, and the settings
below were tuned by measurement on the 2026 Dutch GP set.

    python3 backend/scripts/transcribe_radio.py --race 2026-netherlands

Writes data/<race>/radio_candidates.json, a curation worksheet. It does NOT
touch radio.json: dropping unreliable clips and writing the Turkish subtitle
are still human steps. Feed the curated file back with --apply.
"""

import argparse
import difflib
import json
import os
import re
import subprocess
import urllib.request
from pathlib import Path

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).resolve().parent.parent.parent / "data"))
MODEL = "mlx-community/whisper-large-v3-mlx"

# Two preprocessing chains. PRIMARY is the production chain; SECONDARY exists
# only so the two transcripts can be compared - a low agreement between them is
# the one reliable automatic signal for a hallucinated clip.
PRIMARY = "highpass=f=200,lowpass=f=3400,afftdn=nf=-22,loudnorm"
SECONDARY = "highpass=f=100,loudnorm"

# Agreement between the two chains is reported as a REVIEW ORDER, not a gate.
# Measured on the 31-clip Dutch GP set against hand-verified labels, the best
# possible threshold on either metric scored only 71% - it wrongly dropped the
# race winner's radio among others. Word-overlap (Jaccard) is used rather than
# difflib's sequence ratio because the sequence ratio is badly length-biased:
# median 0.911 on short good clips but 0.619 on long ones, so long good clips
# looked like hallucinations. Nothing is dropped automatically except a clip
# that produced no speech at all.
LOW_CONFIDENCE = 0.55

# Whisper repeats these on silence.
BANNED = {"thank you.", "thanks for watching!", "you", "bye.", ".", "!",
          "thank you very much.", "¶¶"}

# Keep the prompt SHORT. A ~120 token glossary made two clean clips return a
# bare "!" and sent a third into an infinite "-as-as-as" loop. ~25 tokens gave
# no regressions on the controls.
PROMPT_TAIL = "Box, stint, soft, hard, copy, understood."
MAX_PROMPT_SURNAMES = 10


def surnames() -> dict:
    """Map 3-letter code -> surname, from standings.json if it is available."""
    out = {}
    standings = DATA_DIR / "standings.json"
    if standings.exists():
        for d in json.loads(standings.read_text()).get("drivers", []):
            code, name = d.get("code"), d.get("name") or ""
            if code and name:
                out[code] = name.split()[-1]
    return out


def build_prompt(speaker, lap, laps, names) -> str:
    """Name the speaker and the cars actually around them on this lap.

    Championship order would put the same ten surnames in every prompt; the
    drivers a radio message is likely to mention are the ones nearby.
    """
    picked, speaker_pos = [], position_at(laps, speaker, lap)
    if speaker in names:
        picked.append(names[speaker])
    if speaker_pos is not None:
        near = []
        for code in names:
            if code == speaker:
                continue
            pos = position_at(laps, code, lap)
            if pos is not None:
                near.append((abs(pos - speaker_pos), names[code]))
        picked += [n for _, n in sorted(near)]
    else:
        picked += [n for c, n in names.items() if c != speaker]
    picked = picked[:MAX_PROMPT_SURNAMES]
    if not picked:
        return PROMPT_TAIL
    return ", ".join(picked) + ". " + PROMPT_TAIL


def render(mp3: Path, wav: Path, chain: str) -> None:
    if wav.exists():
        return
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3), "-af", chain,
         "-ar", "16000", "-ac", "1", str(wav)],
        check=True,
    )


def transcribe(wav: Path, prompt: str):
    import mlx_whisper

    # word_timestamps must be True or hallucination_silence_threshold is a
    # silent no-op - that is why an earlier attempt at it showed no effect.
    return mlx_whisper.transcribe(
        str(wav),
        path_or_hf_repo=MODEL,
        language="en",
        condition_on_previous_text=False,
        initial_prompt=prompt,
        word_timestamps=True,
        hallucination_silence_threshold=2.0,
    )


STOPWORDS = {"the", "a", "is", "it", "and", "to", "of", "we", "i", "you", "that",
             "for", "on", "in", "s", "t"}


def prompt_echo(text: str, prompt: str) -> bool:
    """True when a segment is just the initial_prompt read back.

    Measured: a silent Alonso clip returned the prompt verbatim ("Box, stint,
    soft, copy, understood.") and a noisy Leclerc clip returned "Box, box,
    box." - which is far more dangerous, because Leclerc really did pit on the
    next lap, so the invented line survives a fact-check.
    """
    vocab = {w.strip(".,!?").lower() for w in prompt.split()} - STOPWORDS
    words = {w.strip(".,!?").lower() for w in text.split()} - STOPWORDS
    return bool(words) and words <= vocab


def clean_segments(result, prompt: str) -> list:
    segs = []
    for s in result["segments"]:
        text = s["text"].strip()
        if not text or text.lower() in BANNED:
            continue
        words = text.lower().split()
        repetitive = len(words) > 3 and len(set(words)) <= max(2, len(words) // 4)
        segs.append({
            "s": round(s["start"], 2),
            "e": round(s["end"], 2),
            "t": text,
            "logprob": round(s.get("avg_logprob", 0.0), 2),
            "compression": round(s.get("compression_ratio", 0.0), 2),
            "weak": bool(
                s.get("avg_logprob", 0.0) < -1.0
                or s.get("compression_ratio", 0.0) > 2.4
                or repetitive
            ),
            "prompt_echo": prompt_echo(text, prompt),
        })
    return segs


def position_at(laps: dict, code: str, lap):
    if lap is None:
        return None
    for entry in laps.get(code, []):
        if entry.get("lap") == lap:
            return entry.get("position")
    return None


def name_flags(text: str, speaker: str, lap, laps: dict, names: dict) -> list:
    """Report where every driver a transcript names actually was.

    A short prompt turns phonetic junk into fluent domain words: "Next is
    science" became "Next is Sainz", which reads perfectly. Sainz was two
    places BEHIND Hulkenberg on that lap, so "next is" cannot mean him. A plain
    distance test passes that case, so report the direction and let the reader
    judge rather than thresholding it.
    """
    flags = []
    speaker_pos = position_at(laps, speaker, lap)
    for code, surname in names.items():
        if code == speaker:
            continue
        if not re.search(r"\b" + re.escape(surname) + r"\b", text, re.IGNORECASE):
            continue
        other_pos = position_at(laps, code, lap)
        if other_pos is None:
            flags.append("{}: not running on lap {}".format(surname, lap))
        elif speaker_pos is None:
            flags.append("{}: P{}, speaker position unknown".format(surname, other_pos))
        else:
            gap = other_pos - speaker_pos
            where = "ahead of" if gap < 0 else "behind"
            flags.append("{}: P{}, {} places {} speaker P{} on lap {}".format(
                surname, other_pos, abs(gap), where, speaker_pos, lap))
    return flags


def apply_curated(race_dir: Path, radio_path: Path, radio: dict, clips: list) -> None:
    curated = {c["index"]: c
               for c in json.loads((race_dir / "radio_candidates.json").read_text())["clips"]}
    kept = 0
    for i, clip in enumerate(clips):
        entry = curated.get(i)
        segs = [s for s in ((entry or {}).get("segments") or [])
                if s.get("t") and s.get("tr")]
        if entry and entry.get("decision") == "keep" and segs:
            clip["segments"] = [{"s": s["s"], "e": s["e"], "t": s["t"], "tr": s["tr"]}
                                for s in segs]
            kept += 1
        else:
            clip.pop("segments", None)
    radio_path.write_text(json.dumps(radio, ensure_ascii=False, indent=2) + "\n")
    print("applied {}/{} transcribed, {} audio-only".format(
        kept, len(clips), len(clips) - kept))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--race", required=True)
    ap.add_argument("--apply", action="store_true",
                    help="merge a curated radio_candidates.json into radio.json")
    args = ap.parse_args()

    race_dir = DATA_DIR / args.race
    radio_path = race_dir / "radio.json"
    radio = json.loads(radio_path.read_text())
    clips = radio["clips"]

    if args.apply:
        apply_curated(race_dir, radio_path, radio, clips)
        return

    laps = json.loads((race_dir / "laps.json").read_text())["laps"]
    names = surnames()
    work = race_dir / "radio_audio"
    work.mkdir(exist_ok=True)

    out = []
    for i, clip in enumerate(clips):
        code, lap = clip["driver"], clip.get("lap")
        mp3 = work / "{:02d}_{}.mp3".format(i, code)
        if not mp3.exists():
            try:
                urllib.request.urlretrieve(clip["url"], mp3)
            except Exception as exc:
                out.append({"index": i, "driver": code, "lap": lap, "decision": "drop",
                            "reason": "download failed: {}".format(exc)})
                print("{:02d} {}: download failed".format(i, code))
                continue

        prompt = build_prompt(code, lap, laps, names)
        wav_a = work / "{:02d}_{}_a.wav".format(i, code)
        wav_b = work / "{:02d}_{}_b.wav".format(i, code)
        render(mp3, wav_a, PRIMARY)
        render(mp3, wav_b, SECONDARY)

        segs = clean_segments(transcribe(wav_a, prompt), prompt)
        text_a = " ".join(s["t"] for s in segs)
        text_b = " ".join(s["text"].strip()
                          for s in transcribe(wav_b, prompt)["segments"]).strip()
        words_a, words_b = set(text_a.lower().split()), set(text_b.lower().split())
        union = words_a | words_b
        agreement = round(len(words_a & words_b) / len(union), 3) if union else 0.0

        entry = {
            "index": i, "driver": code, "lap": lap,
            "agreement": agreement,
            "alt_text": text_b,
            "name_flags": name_flags(text_a, code, lap, laps, names),
            "segments": [dict(s, tr="") for s in segs],
        }
        if not segs:
            entry.update(decision="drop", reason="no speech")
        elif agreement < LOW_CONFIDENCE:
            entry.update(decision="review",
                         reason="LOW confidence, chains overlap only {} - read first".format(
                             agreement))
        else:
            entry.update(decision="review",
                         reason="needs human read, Turkish subtitle, and name check")
        out.append(entry)
        notes = list(entry["name_flags"])
        if any(sg.get("prompt_echo") for sg in segs):
            notes.append("PROMPT ECHO")
        flag_note = "  << " + "; ".join(notes) if notes else ""
        print("{:02d} {} lap={} agree={} {}{}".format(
            i, code, lap, agreement, entry["decision"], flag_note))
        print("     " + text_a[:150])

    (race_dir / "radio_candidates.json").write_text(
        json.dumps({"race_id": args.race, "clips": out}, ensure_ascii=False, indent=2) + "\n")
    out.sort(key=lambda c: c.get("agreement", 0.0))
    dropped = sum(1 for c in out if c["decision"] == "drop")
    low = sum(1 for c in out if c.get("agreement", 1.0) < LOW_CONFIDENCE
              and c["decision"] != "drop")
    flagged = sum(1 for c in out if c.get("name_flags"))
    echoes = sum(1 for c in out
                 if any(sg.get("prompt_echo") for sg in c.get("segments", [])))
    print("\n{}: {} clips, {} empty, {} to review ({} low confidence, listed first), "
          "{} name mentions, {} possible prompt echoes".format(
              args.race, len(out), dropped, len(out) - dropped, low, flagged, echoes))
    print("Fill each kept segment's tr field, set decision to keep or drop, "
          "then rerun with --apply.")


if __name__ == "__main__":
    main()
