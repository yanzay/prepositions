#!/usr/bin/env python3
"""
Build english_prepositions_anki.apkg from the staging *.txt files.

Mirrors ../verbs/build_anki_package.py in spirit but rewritten for the
v2 schema:

  * 5 note types (Recognition, Contrast, Production, Cloze, Listening)
  * 12 modules with auto-routed subdecks based on `module:NN` tag
  * Recognition back uses three-tier progressive reveal (CSS toggle)
  * Contrast / Production "Why" gated behind tap (generation effect)
  * Audio plays on the BACK of every type EXCEPT Listening (front)
  * Tier-2 media: Google Cloud TTS audio + GA IPA + image-schema SVGs +
    optional photographic picture-cue images (Modules 01, 02, 09)
  * FSRS-friendly metadata (no hard-coded SM-2 ease in templates)

Usage:
    python3 build_anki_package.py [--out english_prepositions_anki.apkg]
                                  [--no-media]   (skip Tier-2 inclusion)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Iterable

# ── anki backend bootstrap ──────────────────────────────────────────────
# We use the project-local `anki_packager` shim instead of genanki because
# genanki produces legacy v11 .apkg files where deck-options bindings are
# silently rewritten to "Default" on import. The shim is a drop-in API
# (Model / Deck / Note / Package) built on top of the official `anki`
# package, producing modern v18 .apkg files whose preset auto-binds on
# import in Anki Desktop 23.10+.
def ensure_anki_backend():
    """Verify the official `anki` package is installed."""
    try:
        import anki  # noqa: F401
        return
    except ImportError:
        pass
    import subprocess
    print("  [setup] official `anki` package not found; installing…")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                           "--user", "--break-system-packages",
                           "anki>=24.0"])


# ── Stable model / deck IDs (random but fixed forever) ──────────────────
DECK_ID_BASE     = 1_700_000_000  # any unique number; subdeck IDs derive from this
MODEL_RECOGNITION = 1_700_000_101
MODEL_CONTRAST    = 1_700_000_102
MODEL_PRODUCTION  = 1_700_000_103
MODEL_CLOZE       = 1_700_000_104
MODEL_LISTENING   = 1_700_000_105

# Module → human-readable subdeck name. Any tag starting with `module:NN`
# routes the card to the matching deck. Unknown modules go to a "00 - Misc".
MODULE_NAMES = {
    "module:01": "01 - Spatial Core",
    "module:02": "02 - Spatial Extended",
    "module:03": "03 - Time Prepositions",
    "module:04": "04 - Movement & Direction",
    "module:05": "05 - Dependent · Verb + Prep",
    "module:06": "06 - Dependent · Adjective + Prep",
    "module:07": "07 - Dependent · Noun + Prep",
    "module:08": "08 - Phrasal & Multi-word",
    "module:09": "09 - Abstract & Idiomatic",
    "module:10": "10 - L1 Interference",
    "module:11": "11 - Polysemy Networks",
    "module:12": "12 - Zero Preposition & Ellipsis",
}
# Card-type subdeck names are prefixed with a digit so Anki's
# alphabetical sort surfaces them in pedagogical acquisition order
# (recognition first → listening last). Order rationale:
#   1 Recognition — passive cued recall (build foundational form-meaning links)
#   2 Contrast    — discrimination between confusable forms
#   3 Cloze       — active production within a scaffolded context
#   4 Production  — full constrained writing (highest-difficulty production)
#   5 Listening   — auditory transfer-appropriate processing
TYPE_TO_SUBDECK = {
    "recognition": "1 - Recognition",
    "contrast":    "2 - Contrast",
    "cloze":       "3 - Cloze",
    "production":  "4 - Production",
    "listening":   "5 - Listening",
}
ROOT_DECK_NAME = "English Prepositions"


# ── Media paths ─────────────────────────────────────────────────────────
MEDIA_AUDIO_DIR    = Path("media/audio")
MEDIA_DIAGRAMS_DIR = Path("media/diagrams")
MEDIA_PICTURES_DIR = Path("media/pictures")   # hand-curated picture-cue assets
MEDIA_IMAGES_DIR   = Path("media/images")     # auto-fetched (build_images.py)
MEDIA_IPA_INDEX    = Path("media/ipa_index.json")
MEDIA_DIAG_INDEX   = Path("media/diagrams_index.json")
MEDIA_PIC_INDEX    = Path("media/pictures_index.json")
MEDIA_IMG_INDEX    = Path("media/images_index.json")  # hash → metadata, by sha1(sentence)[:12]


# ── Card UX: shared CSS (light / dark / tiered reveal / mobile) ─────────
SHARED_CSS = """
/* English Prepositions deck — v2 card styling.
   Light + dark + tiered-reveal + mobile-first typography. */
.card {
  font-family: -apple-system, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 18px;
  line-height: 1.5;
  color: #111827;
  background: #ffffff;
  max-width: 36em;
  margin: 0 auto;
  padding: 0.6em 0.8em;
}
.prompt    { color: #374151; font-size: 1.05em; }
.target    { display: inline-block; background: #eff6ff; color: #1d4ed8;
             padding: 2px 8px; border-radius: 6px; font-size: 0.9em;
             font-weight: 600; margin-left: 0.4em; }
.label     { font-size: 1.4em; font-weight: 700; color: #1d4ed8; }
.ipa       { font-family: "Charis SIL", "Doulos SIL", "DejaVu Serif", serif;
             color: #92400e; background: #fffbeb; padding: 4px 8px;
             border-radius: 4px; display: inline-block; }
.tier      { margin-top: 0.6em; padding: 0.5em 0.7em;
             border-left: 3px solid #d1d5db; background: #f9fafb;
             border-radius: 4px; font-size: 0.95em; }
.tier h4   { margin: 0 0 0.3em 0; font-size: 0.85em;
             text-transform: uppercase; letter-spacing: 0.04em;
             color: #6b7280; }
.option    { display: block; padding: 0.45em 0.7em; margin: 0.3em 0;
             border: 1.5px solid #d1d5db; border-radius: 6px; }
.option.A  { background: #eff6ff; }
.option.B  { background: #fef3c7; }
.answer    { color: #16a34a; font-weight: 700; font-size: 1.15em; }
.why       { font-style: italic; color: #4b5563; }
.transcript{ font-family: "Charis SIL", "DejaVu Serif", serif;
             color: #1f2937; font-size: 1.05em; }
.diagram   { display: block; margin: 0.5em auto; max-width: 320px; }
.picture   { display: block; margin: 0.5em auto; max-width: 100%;
             max-height: 240px; border-radius: 8px; }
.img-credit{ display: block; text-align: center; font-size: 0.7em;
             color: #6b7280; margin-top: -0.3em; margin-bottom: 0.5em;
             font-style: italic; }
.nightMode .img-credit, .night_mode .img-credit { color: #94a3b8; }
details    { margin-top: 0.4em; }
details summary { cursor: pointer; color: #1d4ed8; font-size: 0.9em;
                  user-select: none; }
details summary:hover { color: #1e40af; }

/* Dark mode */
.nightMode .card, .night_mode .card,
@media (prefers-color-scheme: dark) {
  .card { background: #0f172a; color: #f1f5f9; }
}
.nightMode .label, .night_mode .label { color: #93c5fd; }
.nightMode .target, .night_mode .target { background: #1e3a8a; color: #bfdbfe; }
.nightMode .ipa, .night_mode .ipa {
  background: #422006; color: #fbbf24; }
.nightMode .tier, .night_mode .tier {
  background: #1f2937; border-left-color: #4b5563; }
.nightMode .option, .night_mode .option { border-color: #4b5563; }
.nightMode .option.A, .night_mode .option.A { background: #1e3a8a; }
.nightMode .option.B, .night_mode .option.B { background: #78350f; }
.nightMode .why, .night_mode .why { color: #cbd5e1; }
.nightMode details summary, .night_mode details summary { color: #93c5fd; }

/* Mobile tweak */
@media (max-width: 600px) {
  .card { font-size: 17px; padding: 0.5em 0.6em; }
  .label { font-size: 1.25em; }
}
"""

# ── Card templates (Anki front/back HTML) ───────────────────────────────
RECOGNITION_FRONT = """
<div class="prompt">Identify the preposition's sense:</div>
<p>{{Sentence}}</p>
"""
RECOGNITION_BACK = """
{{FrontSide}}
<hr>
<div class="label">{{Label}}</div>
{{#IPA}}<div class="ipa">{{IPA}}</div>{{/IPA}}
{{#Audio}}<div>{{Audio}}</div>{{/Audio}}

<details>
  <summary>Show context</summary>
  <div class="tier">
    <h4>Pattern</h4><div>{{Pattern}}</div>
  </div>
  <div class="tier">
    <h4>Main use</h4><div>{{MainUse}}</div>
  </div>
  {{#QuickCue}}<div class="tier"><h4>Quick cue</h4><div>{{QuickCue}}</div></div>{{/QuickCue}}
</details>

<details>
  <summary>Show full reference</summary>
  {{#Trajector}}<div class="tier">
    <h4>Trajector / Landmark / Frame</h4>
    <div>{{Trajector}} → {{Landmark}} ({{FrameOfRef}})</div>
  </div>{{/Trajector}}
  {{#ImageSchema}}<div class="tier">
    <h4>Image schema</h4><div>{{ImageSchema}}</div>
  </div>{{/ImageSchema}}
  {{#Diagram}}<div>{{Diagram}}</div>{{/Diagram}}
  {{#Contrast}}<div class="tier">
    <h4>Often confused with</h4><div>{{Contrast}}</div>
  </div>{{/Contrast}}
  {{#WhenNotToUse}}<div class="tier">
    <h4>When not to use</h4><div>{{WhenNotToUse}}</div>
  </div>{{/WhenNotToUse}}
</details>
"""

CONTRAST_FRONT = """
<div class="prompt">Choose the correct preposition:</div>
<p>{{Sentence}}</p>
<div class="option A">A — {{OptionA}}</div>
<div class="option B">B — {{OptionB}}</div>
"""
CONTRAST_BACK = """
{{FrontSide}}
<hr>
<div class="answer">✓ {{Answer}}</div>
{{#Audio}}<div>{{Audio}}</div>{{/Audio}}
<details>
  <summary>Why?</summary>
  <div class="tier"><div class="why">{{Why}}</div></div>
  {{#Tip}}<div class="tier"><h4>Tip</h4><div>{{Tip}}</div></div>{{/Tip}}
</details>
"""

PRODUCTION_FRONT = """
<div class="prompt">Write a response using:</div>
<p>{{Prompt}}</p>
<div>Target: <span class="target">{{Target}}</span></div>
"""
PRODUCTION_BACK = """
{{FrontSide}}
<hr>
<div class="tier">
  <h4>Sample answer</h4><div>{{Sample}}</div>
</div>
{{#Audio}}<div>{{Audio}}</div>{{/Audio}}
<details>
  <summary>Why this works</summary>
  <div class="tier"><div class="why">{{Why}}</div></div>
</details>
"""

# Cloze uses Anki's built-in cloze model (one template only).
CLOZE_FRONT = "{{cloze:Text}}{{#Hint}}<div class=\"tier\"><h4>Hint</h4><div>{{Hint}}</div></div>{{/Hint}}"
CLOZE_BACK  = "{{cloze:Text}}{{#Audio}}<div>{{Audio}}</div>{{/Audio}}"

LISTENING_FRONT = """
<div class="prompt">Listen and answer:</div>
<div>{{AudioRef}}</div>
<p>{{Question}}</p>
"""
LISTENING_BACK = """
{{FrontSide}}
<hr>
<div class="answer">✓ {{Answer}}</div>
<div class="tier">
  <h4>Transcript</h4>
  <div class="transcript">{{Transcript}}</div>
</div>
{{#IPA}}<div class="ipa">{{IPA}}</div>{{/IPA}}
"""


# ── Tag / sentence helpers ──────────────────────────────────────────────
def text_hash(text: str) -> str:
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


_CLOZE_RE = re.compile(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}")


def strip_cloze(text: str) -> str:
    return _CLOZE_RE.sub(r"\1", text)


def row_module(tags_str: str) -> str:
    """Return the canonical 'module:NN' tag, or 'module:00' if none."""
    for t in tags_str.split():
        if t.startswith("module:") and t in MODULE_NAMES:
            return t
    return "module:00"


def row_card_type(tags_str: str, file_default: str) -> str:
    for t in tags_str.split():
        if t.startswith("type:"):
            return t.split(":", 1)[1]
    return file_default


def deck_name_for(module_tag: str, card_type: str) -> str:
    module_part = MODULE_NAMES.get(module_tag, "00 - Misc")
    type_part   = TYPE_TO_SUBDECK.get(card_type, "Other")
    return f"{ROOT_DECK_NAME}::{module_part}::{type_part}"


def stable_deck_id(deck_name: str) -> int:
    """Derive a deterministic, stable deck ID from the deck name."""
    h = hashlib.sha1(deck_name.encode("utf-8")).hexdigest()
    return DECK_ID_BASE + (int(h[:8], 16) % 10_000_000)


# ── Staging-file readers ────────────────────────────────────────────────
def load_tsv(path: Path) -> Iterable[dict]:
    if not path.exists():
        return
    raw = path.read_text(encoding="utf-8")
    columns: list[str] | None = None
    data_lines: list[str] = []
    for ln in raw.splitlines():
        if ln.startswith("#columns:"):
            columns = ln[len("#columns:"):].split("\t")
        elif not ln or ln.startswith("#"):
            continue
        else:
            data_lines.append(ln)
    if columns is None:
        raise SystemExit(f"{path.name}: missing #columns: header")
    for row in csv.reader(data_lines, delimiter="\t", quotechar='"'):
        if len(row) == len(columns):
            yield dict(zip(columns, row))


# ── Media indices ───────────────────────────────────────────────────────
def load_media_indices(use_media: bool):
    if not use_media:
        return {}, {}, {}, {}
    ipa = json.loads(MEDIA_IPA_INDEX.read_text(encoding="utf-8")) \
        if MEDIA_IPA_INDEX.exists() else {}
    diag = json.loads(MEDIA_DIAG_INDEX.read_text(encoding="utf-8")) \
        if MEDIA_DIAG_INDEX.exists() else {}
    pic = json.loads(MEDIA_PIC_INDEX.read_text(encoding="utf-8")) \
        if MEDIA_PIC_INDEX.exists() else {}
    img = json.loads(MEDIA_IMG_INDEX.read_text(encoding="utf-8")) \
        if MEDIA_IMG_INDEX.exists() else {}
    return ipa, diag, pic, img


def media_for_sentence(sentence: str, ipa_index: dict,
                       diagram_index: dict, picture_index: dict,
                       image_index: dict,
                       *, label: str = "") -> dict:
    """Return {Audio, IPA, Diagram, Picture} as Anki-ready HTML strings.

    Picture priority: hand-curated `picture_index` (slug-keyed) wins over
    auto-fetched `image_index` (hash-keyed by sha1(sentence)[:12]).
    """
    h = text_hash(sentence)
    out = {"Audio": "", "IPA": "", "Diagram": "", "Picture": ""}
    audio_path = MEDIA_AUDIO_DIR / f"{h}.mp3"
    if audio_path.exists():
        out["Audio"] = f"[sound:{h}.mp3]"
    if h in ipa_index:
        out["IPA"] = ipa_index[h]
    # Diagram lookup by canonical Label, e.g. "in (CONTAINER)" → strip parens
    bare_label = re.sub(r"\s*\(.*\)\s*", "", label).strip()
    diag_file = diagram_index.get(label) or diagram_index.get(bare_label)
    if diag_file:
        out["Diagram"] = f'<img class="diagram" src="{diag_file}">'
    # Picture: hand-curated wins, then auto-fetched (Wikimedia Commons)
    pic_slug = re.sub(r"[^\w\s-]", "", bare_label.lower()).replace(" ", "-")
    pic_entry = picture_index.get(pic_slug)
    if pic_entry:
        out["Picture"] = f'<img class="picture" src="{pic_entry["file"]}">'
    elif h in image_index:
        img_entry = image_index[h]
        # Render with caption + tiny attribution credit
        attribution = img_entry.get("attribution", "")
        license_str = img_entry.get("license", "")
        credit = ""
        if attribution or license_str:
            credit = (f'<div class="img-credit">'
                      f'{attribution}'
                      + (f' · {license_str}' if license_str else "")
                      + f'</div>')
        out["Picture"] = (f'<img class="picture" src="{img_entry["file"]}">'
                          f'{credit}')
    return out


def collect_media_files() -> list[str]:
    media: list[str] = []
    if MEDIA_AUDIO_DIR.exists():
        media.extend(str(p) for p in MEDIA_AUDIO_DIR.glob("*.mp3"))
    if MEDIA_DIAGRAMS_DIR.exists():
        media.extend(str(p) for p in MEDIA_DIAGRAMS_DIR.glob("*.svg"))
    for d in (MEDIA_PICTURES_DIR, MEDIA_IMAGES_DIR):
        if d.exists():
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                media.extend(str(p) for p in d.glob(ext))
    return media


# ── Note-type definitions ───────────────────────────────────────────────
def make_models():
    import anki_packager as genanki  # drop-in API, see anki_packager.py
    rec_fields = ["Sentence", "Label", "Sense", "Pattern", "Trajector",
                  "Landmark", "FrameOfRef", "ImageSchema", "MainUse",
                  "QuickCue", "Contrast", "WhenNotToUse",
                  "Audio", "IPA", "Diagram", "Picture", "Tags"]
    rec_model = genanki.Model(
        MODEL_RECOGNITION, "Prepositions Recognition v2",
        fields=[{"name": f} for f in rec_fields],
        templates=[{
            "name": "Recognition",
            "qfmt": RECOGNITION_FRONT,
            "afmt": RECOGNITION_BACK,
        }],
        css=SHARED_CSS,
    )
    contrast_fields = ["Sentence", "OptionA", "OptionB", "Answer", "Why",
                       "Tip", "Audio", "IPA", "Tags"]
    contrast_model = genanki.Model(
        MODEL_CONTRAST, "Prepositions Contrast v2",
        fields=[{"name": f} for f in contrast_fields],
        templates=[{
            "name": "Contrast",
            "qfmt": CONTRAST_FRONT,
            "afmt": CONTRAST_BACK,
        }],
        css=SHARED_CSS,
    )
    production_fields = ["Prompt", "Target", "Sense", "Sample", "Why",
                         "Audio", "Tags"]
    production_model = genanki.Model(
        MODEL_PRODUCTION, "Prepositions Production v2",
        fields=[{"name": f} for f in production_fields],
        templates=[{
            "name": "Production",
            "qfmt": PRODUCTION_FRONT,
            "afmt": PRODUCTION_BACK,
        }],
        css=SHARED_CSS,
    )
    cloze_fields = ["Text", "Hint", "Audio", "Tags"]
    cloze_model = genanki.Model(
        MODEL_CLOZE, "Prepositions Cloze v2",
        model_type=genanki.Model.CLOZE,
        fields=[{"name": f} for f in cloze_fields],
        templates=[{
            "name": "Cloze",
            "qfmt": CLOZE_FRONT,
            "afmt": CLOZE_BACK,
        }],
        css=SHARED_CSS,
    )
    listening_fields = ["AudioRef", "Question", "Answer", "Transcript",
                        "IPA", "Tags"]
    listening_model = genanki.Model(
        MODEL_LISTENING, "Prepositions Listening v2",
        fields=[{"name": f} for f in listening_fields],
        templates=[{
            "name": "Listening",
            "qfmt": LISTENING_FRONT,
            "afmt": LISTENING_BACK,
        }],
        css=SHARED_CSS,
    )
    return {
        "recognition": rec_model,
        "contrast":    contrast_model,
        "production":  production_model,
        "cloze":       cloze_model,
        "listening":   listening_model,
    }


# ── Note builders per type ──────────────────────────────────────────────
def _tags_to_anki(tags_str: str) -> list[str]:
    # Anki tag separator is whitespace. Replace ":" with "_" so subdeck-style
    # tags like "module:01" become "module_01" (Anki treats `:` specially in
    # the deck-tree; this keeps tag-browser searches working).
    return [t.replace(":", "_") for t in tags_str.split() if t]


def build_recognition_note(model, row, media):
    import anki_packager as genanki  # drop-in API
    return genanki.Note(
        model=model,
        fields=[
            row.get("Sentence", ""),
            row.get("Label", ""),
            row.get("Sense", ""),
            row.get("Pattern", ""),
            row.get("Trajector", ""),
            row.get("Landmark", ""),
            row.get("FrameOfRef", ""),
            row.get("ImageSchema", ""),
            row.get("MainUse", ""),
            row.get("QuickCue", ""),
            row.get("Contrast", ""),
            row.get("WhenNotToUse", ""),
            media.get("Audio", ""),
            media.get("IPA", ""),
            media.get("Diagram", ""),
            media.get("Picture", ""),
            row.get("Tags", ""),
        ],
        tags=_tags_to_anki(row.get("Tags", "")),
    )


def build_contrast_note(model, row, media):
    import anki_packager as genanki  # drop-in API
    return genanki.Note(
        model=model,
        fields=[
            row.get("Sentence", ""), row.get("OptionA", ""),
            row.get("OptionB", ""), row.get("Answer", ""),
            row.get("Why", ""), row.get("Tip", ""),
            media.get("Audio", ""), media.get("IPA", ""),
            row.get("Tags", ""),
        ],
        tags=_tags_to_anki(row.get("Tags", "")),
    )


def build_production_note(model, row, media):
    import anki_packager as genanki  # drop-in API
    return genanki.Note(
        model=model,
        fields=[
            row.get("Prompt", ""), row.get("Target", ""),
            row.get("Sense", ""), row.get("Sample", ""),
            row.get("Why", ""), media.get("Audio", ""),
            row.get("Tags", ""),
        ],
        tags=_tags_to_anki(row.get("Tags", "")),
    )


def build_cloze_note(model, row, media):
    import anki_packager as genanki  # drop-in API
    return genanki.Note(
        model=model,
        fields=[
            row.get("Text", ""), row.get("Hint", ""),
            media.get("Audio", ""), row.get("Tags", ""),
        ],
        tags=_tags_to_anki(row.get("Tags", "")),
    )


def build_listening_note(model, row, media):
    import anki_packager as genanki  # drop-in API
    # AudioRef is already `[sound:hash.mp3]` in the staging file.
    return genanki.Note(
        model=model,
        fields=[
            row.get("AudioRef", ""), row.get("Question", ""),
            row.get("Answer", ""), row.get("Transcript", ""),
            media.get("IPA", ""), row.get("Tags", ""),
        ],
        tags=_tags_to_anki(row.get("Tags", "")),
    )


# ── Driver ──────────────────────────────────────────────────────────────
FILE_SPECS = [
    ("prepositions_recognition.txt", "recognition", "Sentence",  build_recognition_note),
    ("prepositions_contrast.txt",    "contrast",    "Sentence",  build_contrast_note),
    ("prepositions_production.txt",  "production",  "Sample",    build_production_note),
    ("prepositions_cloze.txt",       "cloze",       "Text",      build_cloze_note),
    ("prepositions_listening.txt",   "listening",   "Transcript", build_listening_note),
]


def main():
    ap = argparse.ArgumentParser(description="Build english_prepositions_anki.apkg")
    ap.add_argument("--out", default="english_prepositions_anki.apkg")
    ap.add_argument("--no-media", action="store_true",
                    help="Skip Tier-2 media inclusion (for fast smoke builds)")
    args = ap.parse_args()

    ensure_anki_backend()
    import anki_packager as genanki  # drop-in API

    models = make_models()
    ipa_index, diag_index, pic_index, img_index = load_media_indices(not args.no_media)
    decks: dict[str, "genanki.Deck"] = {}

    def get_deck(name: str) -> "genanki.Deck":
        if name not in decks:
            decks[name] = genanki.Deck(stable_deck_id(name), name)
        return name and decks[name]

    counts = {ct: 0 for ct in TYPE_TO_SUBDECK}

    for filename, default_type, sent_field, builder in FILE_SPECS:
        path = Path(filename)
        for row in load_tsv(path):
            tags = row.get("Tags", "")
            ctype = row_card_type(tags, default_type)
            module = row_module(tags)
            deck_name = deck_name_for(module, ctype)
            deck = get_deck(deck_name)
            # Resolve sentence-bound media. Cloze sentences have the form
            # "{{c1::form}}" so we must strip cloze for the audio hash.
            sentence_for_media = row.get(sent_field, "")
            if default_type == "cloze":
                sentence_for_media = strip_cloze(sentence_for_media)
            elif default_type == "contrast" and "___" in sentence_for_media:
                sentence_for_media = sentence_for_media.replace(
                    "___", row.get("Answer", ""))
            media = media_for_sentence(sentence_for_media,
                                       ipa_index, diag_index, pic_index,
                                       img_index,
                                       label=row.get("Label", ""))
            note = builder(models[ctype], row, media)
            deck.add_note(note)
            counts[ctype] += 1

    # Build package — bind every non-default deck to the
    # 'English Prepositions' FSRS preset on import. The L1 Interference
    # subdeck (module:10) ships opted-out (perDay=0) so a Russian speaker
    # doesn't drown in Spanish/Mandarin/Japanese cards. Each user enables
    # only their L1 subdeck via gear → Deck Options → preset selector.
    pkg = genanki.Package(
        list(decks.values()),
        preset_name="English Prepositions",
        l1_deck_prefix="10 - L1 Interference::",
    )
    if not args.no_media:
        pkg.media_files = collect_media_files()
    pkg.write_to_file(args.out)

    print(f"✓ Wrote {args.out}")
    print(f"  Decks: {len(decks)}  Notes: {sum(counts.values())}")
    for ct in TYPE_TO_SUBDECK:
        if counts[ct]:
            print(f"    {ct:11s} {counts[ct]:>5d}")
    if not args.no_media:
        print(f"  Media files bundled: {len(pkg.media_files)}")


if __name__ == "__main__":
    main()
