#!/usr/bin/env python3
"""Validate the prepositions Anki staging files (v2 schema).

Mirrors ../verbs/validate_anki_data.py. Currently enforces:
  * header lines are present and well-formed
  * each data row has the exact number of columns the header declares
  * contrast Answer matches OptionA or OptionB byte-for-byte
  * cloze Text contains exactly one {{c1::...}} deletion
  * listening AudioRef matches [sound:<12-hex>.mp3] format
  * spatial Recognition rows have non-empty Trajector / Landmark / ImageSchema
  * no duplicate keys within a single file
  * every data row carries the 8 required tag axes

Run:
    python3 validate_anki_data.py
Exits non-zero on any failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

FILES = {
    "prepositions_recognition.txt": {
        "columns": ["Sentence", "Label", "Sense", "Pattern",
                    "Trajector", "Landmark", "FrameOfRef", "ImageSchema",
                    "MainUse", "QuickCue", "Contrast", "WhenNotToUse", "Tags"],
        "key": "Sentence",
    },
    "prepositions_contrast.txt": {
        "columns": ["Sentence", "OptionA", "OptionB", "Answer", "Why",
                    "Tip", "Tags"],
        "key": "Sentence",
    },
    "prepositions_production.txt": {
        "columns": ["Prompt", "Target", "Sense", "Sample", "Why", "Tags"],
        "key": "Prompt",
    },
    "prepositions_cloze.txt": {
        "columns": ["Text", "Hint", "Tags"],
        "key": "Text",
    },
    "prepositions_listening.txt": {
        "columns": ["AudioRef", "Question", "Answer", "Transcript", "Tags"],
        "key": "AudioRef",
    },
}

REQUIRED_TAG_AXES = (
    "module:", "type:", "sense:", "frequency:",
    "register:", "cefr:", "image-schema:", "generalisable:",
)

CLOZE_RE = re.compile(r"\{\{c1::[^}]+\}\}")
AUDIO_RE = re.compile(r"^\[sound:[0-9a-f]{12}\.mp3\]$")


def _read_rows(path: Path):
    """Yield (lineno, fields) for data rows; check header columns line."""
    expected = FILES[path.name]["columns"]
    saw_header = False
    with path.open(encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.rstrip("\n")
            if not line:
                continue
            if line.startswith("#columns:"):
                cols = line[len("#columns:"):].split("\t")
                if cols != expected:
                    raise SystemExit(
                        f"{path.name}:{lineno}: column header mismatch.\n"
                        f"  expected: {expected}\n  got:      {cols}")
                saw_header = True
                continue
            if line.startswith("#"):
                continue
            fields = line.split("\t")
            if len(fields) != len(expected):
                raise SystemExit(
                    f"{path.name}:{lineno}: expected {len(expected)} cols, "
                    f"got {len(fields)}")
            yield lineno, dict(zip(expected, fields))
    if not saw_header:
        raise SystemExit(f"{path.name}: missing #columns: header line")


def _check_tags(path: Path, lineno: int, tags: str) -> None:
    parts = tags.split()
    for axis in REQUIRED_TAG_AXES:
        if not any(t.startswith(axis) for t in parts):
            raise SystemExit(
                f"{path.name}:{lineno}: missing required tag axis '{axis}*'")


def validate_file(path: Path) -> int:
    spec = FILES[path.name]
    key = spec["key"]
    seen: set[str] = set()
    n = 0
    for lineno, row in _read_rows(path):
        n += 1
        k = row[key].strip()
        if not k:
            raise SystemExit(f"{path.name}:{lineno}: empty {key}")
        if k in seen:
            raise SystemExit(f"{path.name}:{lineno}: duplicate {key}: {k!r}")
        seen.add(k)
        _check_tags(path, lineno, row["Tags"])
        if path.name == "prepositions_contrast.txt":
            if row["Answer"] not in (row["OptionA"], row["OptionB"]):
                raise SystemExit(
                    f"{path.name}:{lineno}: Answer {row['Answer']!r} does "
                    f"not match OptionA/OptionB")
        if path.name == "prepositions_cloze.txt":
            matches = CLOZE_RE.findall(row["Text"])
            if len(matches) != 1:
                raise SystemExit(
                    f"{path.name}:{lineno}: expected exactly one {{c1::...}} "
                    f"deletion, found {len(matches)}")
        if path.name == "prepositions_listening.txt":
            if not AUDIO_RE.match(row["AudioRef"]):
                raise SystemExit(
                    f"{path.name}:{lineno}: AudioRef must match "
                    f"[sound:<12-hex>.mp3], got {row['AudioRef']!r}")
        if path.name == "prepositions_recognition.txt":
            tag_parts = row["Tags"].split()
            is_spatial = any(t in ("sense:spatial", "sense:movement")
                             for t in tag_parts)
            if is_spatial:
                for fld in ("Trajector", "Landmark", "ImageSchema"):
                    if not row[fld].strip():
                        raise SystemExit(
                            f"{path.name}:{lineno}: spatial/movement row "
                            f"missing required field {fld!r}")
                if row["ImageSchema"].strip() == "none":
                    raise SystemExit(
                        f"{path.name}:{lineno}: spatial/movement row cannot "
                        f"have image-schema 'none'")
    return n


def main() -> int:
    total = 0
    for name in FILES:
        path = ROOT / name
        if not path.exists():
            raise SystemExit(f"missing staging file: {name}")
        n = validate_file(path)
        print(f"  {name}: {n} rows OK")
        total += n
    print(f"validate_anki_data.py: {total} rows passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
