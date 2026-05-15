#!/usr/bin/env python3
"""normalize_audio.py \u2014 EBU R128 loudness normalization for media/audio/*.mp3.

After build_audio.py has produced the per-sentence MP3s (variable loudness
because Google's synthesizer calibrates per-utterance), this script
post-processes every MP3 to a uniform -16 LUFS / -1.5 dB true-peak target
using ffmpeg's `loudnorm` filter.

Why: Anki cards play back through arbitrary device volumes, so consistent
loudness prevents jarring volume jumps between cards. EBU R128 -16 LUFS is
the broadcast-podcast standard; -1.5 dB true-peak avoids inter-sample
peaking on lossy playback.

Idempotent: each manifest entry is marked `normalized: true` after pass.
Re-running skips already-normalized files. Updates sha256 + size in
the manifest after each pass so build_audio.py's pruning still works.

Output: in-place MP3 replacement; manifest updated with new sha256.

Usage:
  python3 normalize_audio.py             # normalize all unprocessed files
  python3 normalize_audio.py --dry-run   # count files without processing
  python3 normalize_audio.py --limit 10  # smoke test on 10 files

Requires: ffmpeg in PATH (or at /opt/homebrew/bin/ffmpeg on macOS Homebrew).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
AUDIO_DIR = ROOT / "media" / "audio"
MANIFEST_PATH = ROOT / "media" / "audio_manifest.json"

# Loudness targets (EBU R128 podcast / broadcast standard)
TARGET_INTEGRATED = "-16"      # I=-16 LUFS
TARGET_TRUE_PEAK  = "-1.5"     # TP=-1.5 dB
TARGET_LRA        = "11"       # LRA=11 LU (loudness range)
OUTPUT_BITRATE    = "64k"      # plenty for spoken word
OUTPUT_SAMPLERATE = "24000"    # 24 kHz — matches Google Cloud TTS Neural2 output
OUTPUT_CHANNELS   = "1"        # mono


def find_ffmpeg() -> str:
    """Locate ffmpeg in common places. Returns the full path or raises."""
    if shutil.which("ffmpeg"):
        return "ffmpeg"
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg",
                      "/usr/bin/ffmpeg"):
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError(
        "ffmpeg not found in PATH or common Homebrew/system locations. "
        "Install with: brew install ffmpeg  (macOS) or apt install ffmpeg (Linux)."
    )


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def normalize_mp3(ffmpeg: str, in_path: Path, out_path: Path) -> bool:
    cmd = [
        ffmpeg,
        "-i", str(in_path),
        "-af", f"loudnorm=I={TARGET_INTEGRATED}:TP={TARGET_TRUE_PEAK}:LRA={TARGET_LRA}",
        "-b:a", OUTPUT_BITRATE,
        "-ar", OUTPUT_SAMPLERATE,
        "-ac", OUTPUT_CHANNELS,
        "-y",
        str(out_path),
    ]
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=60,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"version": 1, "entries": {}}


def save_manifest(manifest: dict) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    manifest["entries"] = dict(sorted(manifest["entries"].items()))
    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def process(dry_run: bool, limit: int | None) -> tuple[int, int, list[str]]:
    if not AUDIO_DIR.exists():
        print(f"Error: {AUDIO_DIR} does not exist. Run build_audio.py first.",
              file=sys.stderr)
        return 0, 0, []
    try:
        ffmpeg = find_ffmpeg()
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 0, 0, []

    manifest = load_manifest()
    entries = manifest.get("entries", {})

    mp3_files = sorted(AUDIO_DIR.glob("*.mp3"))
    if limit:
        mp3_files = mp3_files[:limit]

    processed = skipped = 0
    errors: list[str] = []

    print(f"Found {len(mp3_files)} MP3 file(s) under {AUDIO_DIR.relative_to(ROOT)}")
    print(f"Dry-run: {dry_run}")
    print(f"Target: I={TARGET_INTEGRATED} LUFS, TP={TARGET_TRUE_PEAK} dB, "
          f"LRA={TARGET_LRA} LU, {OUTPUT_BITRATE} {OUTPUT_SAMPLERATE} Hz mono")
    print()

    for idx, mp3_path in enumerate(mp3_files, 1):
        hash_key = mp3_path.stem
        entry = entries.get(hash_key, {})
        if entry.get("normalized"):
            skipped += 1
            if idx % 100 == 0:
                print(f"[{idx}/{len(mp3_files)}] processed={processed} skipped={skipped}",
                      flush=True)
            continue
        if dry_run:
            processed += 1
            if idx % 100 == 0:
                print(f"[{idx}/{len(mp3_files)}] processed={processed} skipped={skipped}",
                      flush=True)
            continue
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
        try:
            if not normalize_mp3(ffmpeg, mp3_path, tmp_path):
                errors.append(f"{hash_key}: ffmpeg normalization failed")
                tmp_path.unlink(missing_ok=True)
                continue
            os.replace(tmp_path, mp3_path)
            entry["sha256"] = file_sha256(mp3_path)
            entry["size"] = mp3_path.stat().st_size
            entry["normalized"] = True
            entries[hash_key] = entry
            processed += 1
            if idx % 100 == 0:
                print(f"[{idx}/{len(mp3_files)}] processed={processed} skipped={skipped}",
                      flush=True)
            # Checkpoint every 50 to survive interrupts
            if processed % 50 == 0 and processed > 0:
                manifest["entries"] = entries
                save_manifest(manifest)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{hash_key}: {e}")
            tmp_path.unlink(missing_ok=True)

    if not dry_run:
        manifest["entries"] = entries
        save_manifest(manifest)
    return processed, skipped, errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true",
                    help="Count files without processing")
    ap.add_argument("--limit", type=int,
                    help="Process only N files (smoke test)")
    args = ap.parse_args()

    processed, skipped, errors = process(args.dry_run, args.limit)

    print()
    print("Results:")
    print(f"  Processed: {processed}")
    print(f"  Skipped:   {skipped}")
    print(f"  Errors:    {len(errors)}")
    if errors:
        print()
        print("Errors:")
        for e in errors[:10]:
            print(f"  - {e}")
        if len(errors) > 10:
            print(f"  ... and {len(errors) - 10} more")
    return 0 if not errors else 1


if __name__ == "__main__":
    sys.exit(main())
