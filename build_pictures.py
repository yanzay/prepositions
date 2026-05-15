#!/usr/bin/env python3
"""
Tier-2 picture-cue manifest for the English Prepositions Anki package.

This script does NOT download photos itself — that's a manual curatorial
task with copyright implications. Instead it scans the staging files for
rows tagged `picture-cue:yes`, then:

  1. validates that every such row has a corresponding image file in
     media/pictures/<slug>.{jpg|png|webp};
  2. writes a manifest media/pictures_index.json mapping
     <Recognition.Label or Contrast.Answer slug> → filename + credit;
  3. enforces that every shipped image has a credit line in
     media/pictures/CREDITS.txt (CC0 / Pexels / Pixabay / Unsplash etc.).

Workflow:
  - Curator finds a CC0/Pexels/Pixabay/Unsplash photo for a tagged row.
  - Saves it as media/pictures/<slug>.jpg (slug = canonical preposition or
    sense, e.g. `cat-on-table.jpg`).
  - Adds a one-line entry to media/pictures/CREDITS.txt:
      cat-on-table.jpg | Photographer Name | https://pexels.com/photo/... | CC0
  - Re-runs `python3 build_pictures.py`.
  - The build_anki_package.py script picks up the manifest and embeds the
    image as the front of the corresponding picture-cue card.

Aim: ~200 photos covering the spatial-core trio (in/on/at), the spatial-
extended set (under/over/between/among), and the abstract/idiomatic core
(in time vs on time, on foot, by car, in love, at risk, under pressure).
"""
from __future__ import annotations

import csv as _csv
import json
import re
import sys
from pathlib import Path

PIC_DIR        = Path("media/pictures")
CREDITS_FILE   = PIC_DIR / "CREDITS.txt"
INDEX_JSON     = Path("media/pictures_index.json")

PIC_EXTS = (".jpg", ".jpeg", ".png", ".webp")


def slug(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s.strip("-") or "untitled"


def load_tsv(path: Path):
    if not path.exists():
        return
    data_lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
                  if ln and not ln.startswith("#")]
    columns = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.startswith("#columns:"):
            columns = raw[len("#columns:"):].split("\t")
            break
    if columns is None:
        return
    for row in _csv.reader(data_lines, delimiter="\t", quotechar='"'):
        if len(row) == len(columns):
            yield dict(zip(columns, row))


def collect_picture_cue_rows():
    """Return list of {slug, source_file, label, sentence}."""
    files = [
        (Path("prepositions_recognition.txt"), "Label", "Sentence"),
        (Path("prepositions_contrast.txt"),    "Answer", "Sentence"),
    ]
    out = []
    for path, label_col, sent_col in files:
        for row in load_tsv(path):
            tags = row.get("Tags", "").split()
            if "picture-cue:yes" not in tags:
                continue
            label = row.get(label_col, "").strip()
            if not label:
                continue
            out.append({
                "slug": slug(label),
                "source_file": path.name,
                "label": label,
                "sentence": row.get(sent_col, ""),
            })
    return out


def find_image(stem: str) -> Path | None:
    for ext in PIC_EXTS:
        p = PIC_DIR / f"{stem}{ext}"
        if p.exists():
            return p
    return None


def parse_credits() -> dict[str, dict]:
    if not CREDITS_FILE.exists():
        return {}
    creds: dict[str, dict] = {}
    for ln in CREDITS_FILE.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#"):
            continue
        parts = [p.strip() for p in ln.split("|")]
        if len(parts) < 4:
            continue
        fname, photographer, url, license_ = parts[:4]
        creds[fname] = {
            "photographer": photographer,
            "url": url,
            "license": license_,
        }
    return creds


def main():
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    rows = collect_picture_cue_rows()
    creds = parse_credits()

    manifest: dict[str, dict] = {}
    missing_image: list[str] = []
    missing_credit: list[str] = []

    for row in rows:
        img = find_image(row["slug"])
        if img is None:
            missing_image.append(row["slug"])
            continue
        if img.name not in creds:
            missing_credit.append(img.name)
            continue
        manifest[row["slug"]] = {
            "file": img.name,
            "label": row["label"],
            "source_file": row["source_file"],
            "credit": creds[img.name],
        }

    INDEX_JSON.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    print(f"Picture-cue rows requested: {len(rows)}")
    print(f"  ✓ matched image + credit:  {len(manifest)}")
    if missing_image:
        print(f"  ✗ missing image file:      {len(missing_image)}")
        for s in missing_image[:10]:
            print(f"      {s}.{{jpg,png,webp}}")
    if missing_credit:
        print(f"  ✗ missing CREDITS line:    {len(missing_credit)}")
        for f in missing_credit[:10]:
            print(f"      {f}")
    print(f"  Manifest: {INDEX_JSON}")
    if missing_image or missing_credit:
        sys.exit(1)


if __name__ == "__main__":
    main()
