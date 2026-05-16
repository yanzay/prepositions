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
# Model IDs bumped to 2xx (v1.1.0) for the design-system v3 CSS rewrite.
# Bumping forces Anki to re-import the templates/CSS instead of merging
# them with the previous (hardcoded-color) note types.
MODEL_RECOGNITION = 1_700_000_201
MODEL_CONTRAST    = 1_700_000_202
MODEL_PRODUCTION  = 1_700_000_203
MODEL_CLOZE       = 1_700_000_204
MODEL_LISTENING   = 1_700_000_205

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


# ── Card UX: shared CSS — design system v3 (semantic tokens) ────────────
# Mirrors the gold-standard system used by the sister `../verbs` deck:
# single source of truth for colors via CSS custom properties; light +
# dark themes via .nightMode / .night_mode AND prefers-color-scheme; full
# semantic callout palette so success / info / warn / danger / target are
# never invisible on any theme.
SHARED_CSS = """
/* ============================================================
   English Prepositions — Card Design System v3
   ------------------------------------------------------------
   Single source of truth for colors. Everything below the
   token block uses var(--*) so light <-> dark theming is
   automatic and no class can ever fall through to
   invisible-on-dark text.
   ============================================================ */

/* Light theme tokens (default) */
.card {
  --bg-card:        #ffffff;
  --bg-surface:     #f9fafb;
  --bg-surface-2:   #f3f4f6;

  --fg-strong:      #111827;
  --fg-default:     #1f2937;
  --fg-muted:       #4b5563;
  --fg-faint:       #6b7280;
  --fg-fainter:     #9ca3af;

  --border-default: #e5e7eb;
  --border-muted:   #d1d5db;
  --border-strong:  #9ca3af;

  /* Semantic callout palette (bg / fg / border) */
  --success-bg:     #dcfce7;  --success-fg:    #166534;  --success-border: #86efac;
  --info-bg:        #eff6ff;  --info-fg:       #1d4ed8;  --info-border:    #bfdbfe;
  --warn-bg:        #fef3c7;  --warn-fg:       #92400e;  --warn-border:    #fde68a;
  --danger-bg:      #fef2f2;  --danger-fg:     #991b1b;  --danger-border:  #fecaca;
  --hint-bg:        #f0fdf4;  --hint-fg:       #166534;  --hint-border:    #86efac;
  --ipa-bg:         #fef3c7;  --ipa-fg:        #78350f;  --ipa-key-fg:     #92400e;  --ipa-border: #fde68a;
  --sample-fg:      #1e40af;
  --target-bg:      #eff6ff;  --target-fg:     #1d4ed8;  --target-border:  #bfdbfe;
  --cloze-fg:       #1d4ed8;

  --shadow-image:   0 2px 8px rgba(0,0,0,0.15);
}

/* Dark theme tokens. Anki applies the night-mode class in DIFFERENT
   ways across versions / clients — we cover all the documented forms. */
.card.nightMode,  .card.night_mode,
.nightMode .card, .night_mode .card,
.nightMode.card, .night_mode.card,
body.nightMode .card, body.night_mode .card,
html.nightMode .card, html.night_mode .card {
  --bg-card:        #0f172a;
  --bg-surface:     #1e293b;
  --bg-surface-2:   #334155;

  --fg-strong:      #f8fafc;
  --fg-default:     #e2e8f0;
  --fg-muted:       #cbd5e1;
  --fg-faint:       #94a3b8;
  --fg-fainter:     #64748b;

  --border-default: #334155;
  --border-muted:   #475569;
  --border-strong:  #64748b;

  --success-bg:     #064e3b;  --success-fg:    #bbf7d0;  --success-border: #047857;
  --info-bg:        #1e3a8a;  --info-fg:       #dbeafe;  --info-border:    #2563eb;
  --warn-bg:        #422006;  --warn-fg:       #fef3c7;  --warn-border:    #92400e;
  --danger-bg:      #450a0a;  --danger-fg:     #fecaca;  --danger-border:  #b91c1c;
  --hint-bg:        #052e16;  --hint-fg:       #bbf7d0;  --hint-border:    #22c55e;
  --ipa-bg:         #422006;  --ipa-fg:        #fef3c7;  --ipa-key-fg:     #fde68a;  --ipa-border: #92400e;
  --sample-fg:      #93c5fd;
  --target-bg:      #1e3a8a;  --target-fg:     #dbeafe;  --target-border:  #2563eb;
  --cloze-fg:       #93c5fd;

  --shadow-image:   0 2px 8px rgba(0,0,0,0.5);
}
/* OS-level dark mode fallback for clients that forget the class */
@media (prefers-color-scheme: dark) {
  .card {
    --bg-card:        #0f172a;
    --bg-surface:     #1e293b;
    --bg-surface-2:   #334155;
    --fg-strong:      #f8fafc;
    --fg-default:     #e2e8f0;
    --fg-muted:       #cbd5e1;
    --fg-faint:       #94a3b8;
    --fg-fainter:     #64748b;
    --border-default: #334155;
    --border-muted:   #475569;
    --border-strong:  #64748b;
    --success-bg:     #064e3b;  --success-fg:    #bbf7d0;  --success-border: #047857;
    --info-bg:        #1e3a8a;  --info-fg:       #dbeafe;  --info-border:    #2563eb;
    --warn-bg:        #422006;  --warn-fg:       #fef3c7;  --warn-border:    #92400e;
    --danger-bg:      #450a0a;  --danger-fg:     #fecaca;  --danger-border:  #b91c1c;
    --hint-bg:        #052e16;  --hint-fg:       #bbf7d0;  --hint-border:    #22c55e;
    --ipa-bg:         #422006;  --ipa-fg:        #fef3c7;  --ipa-key-fg:     #fde68a;  --ipa-border: #92400e;
    --sample-fg:      #93c5fd;
    --target-bg:      #1e3a8a;  --target-fg:     #dbeafe;  --target-border:  #2563eb;
    --cloze-fg:       #93c5fd;
    --shadow-image:   0 2px 8px rgba(0,0,0,0.5);
  }
}

/* ============================================================
   Layout primitives
   ============================================================ */
.card {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif;
  font-size: 19px;
  line-height: 1.5;
  color: var(--fg-default);
  background: var(--bg-card);
  max-width: 860px;
  margin: 0 auto;
  padding: 4px 0;
  color-scheme: light dark;
}
.front { text-align: center; }
.front .audio-row { display: flex; justify-content: center; }

/* ============================================================
   Typography
   ============================================================ */
.instruction {
  font-size: 0.82em;
  color: var(--fg-fainter);
  letter-spacing: 0.02em;
  text-transform: uppercase;
  margin-bottom: 10px;
}
.sentence {
  font-size: 1.15em;
  font-weight: 600;
  color: var(--fg-strong);
  margin-bottom: 6px;
  line-height: 1.4;
}
.prompt {
  font-size: 0.82em;
  color: var(--fg-fainter);
  letter-spacing: 0.02em;
  text-transform: uppercase;
  margin-bottom: 10px;
}

/* ============================================================
   A/B options on contrast cards
   ============================================================ */
.options {
  margin-top: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.option {
  padding: 9px 14px;
  border: 1.5px solid var(--border-default);
  border-radius: 8px;
  font-size: 0.97em;
  color: var(--fg-default);
  background: var(--bg-surface);
  text-align: left;
}
.option .opt-letter {
  font-weight: 700;
  color: var(--fg-faint);
  margin-right: 6px;
}

/* ============================================================
   Answer block (answer-label = the preposition Label)
   ============================================================ */
hr#answer, hr {
  border: none;
  border-top: 2px solid var(--border-default);
  margin: 20px 0 16px;
}
.answer-block { text-align: center; }
.answer-label, .label {
  font-size: 1.6em;
  font-weight: 700;
  color: var(--info-fg);
  margin-bottom: 6px;
  line-height: 1.25;
  display: block;
}
.answer-correct, .answer {
  display: inline-block;
  background: var(--success-bg);
  color: var(--success-fg);
  border: 1px solid var(--success-border);
  border-radius: 6px;
  padding: 2px 10px;
  font-size: 1.05em;
  font-weight: 600;
  margin-bottom: 10px;
}

/* ============================================================
   Tier / info / meta blocks
   ============================================================ */
.tier {
  margin: 10px auto 0;
  max-width: 560px;
  padding: 8px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-default);
  border-left: 3px solid var(--border-muted);
  border-radius: 6px;
  font-size: 0.92em;
  color: var(--fg-default);
  text-align: left;
}
.tier h4 {
  margin: 0 0 4px 0;
  font-size: 0.78em;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--fg-fainter);
  font-weight: 700;
}
.meta-grid {
  display: inline-grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin: 10px auto 14px;
  font-size: 0.93em;
  text-align: left;
  max-width: 560px;
}
.meta-key {
  color: var(--fg-faint);
  font-weight: 600;
  white-space: nowrap;
}
.meta-val { color: var(--fg-default); }

/* ============================================================
   Why / tip blocks (Contrast / Production)
   ============================================================ */
.why-block, .why {
  margin: 10px auto 0;
  max-width: 560px;
  font-size: 0.93em;
  color: var(--fg-default);
  line-height: 1.5;
  text-align: left;
}
.why-block .why-label {
  font-weight: 700;
  color: var(--fg-strong);
}
.tip-block, .tip {
  margin-top: 8px;
  font-size: 0.87em;
  color: var(--fg-muted);
  font-style: italic;
  border-left: 3px solid var(--border-muted);
  padding-left: 10px;
  text-align: left;
}

/* ============================================================
   Production: target badge + sample answer
   ============================================================ */
.target, .target-badge {
  display: inline-block;
  background: var(--target-bg);
  color: var(--target-fg);
  border: 1px solid var(--target-border);
  border-radius: 6px;
  padding: 2px 10px;
  font-size: 0.9em;
  font-weight: 600;
  margin: 4px 0 0 0;
}
.sample-label {
  font-size: 0.8em;
  color: var(--fg-fainter);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: 4px;
}
.sample-answer {
  font-size: 1.05em;
  font-weight: 600;
  color: var(--sample-fg);
  margin-bottom: 10px;
}

/* ============================================================
   IPA — collapsed by default, quiet styling
   ============================================================ */
.ipa, .ipa-box {
  margin: 10px auto;
  max-width: 560px;
  padding: 5px 10px;
  background: var(--ipa-bg);
  color: var(--ipa-fg);
  border: 1px solid var(--ipa-border);
  border-radius: 6px;
  font-family: "Charis SIL", "Doulos SIL", "DejaVu Serif", serif;
  font-size: 0.95em;
  text-align: center;
  display: block;
}

/* ============================================================
   Transcript (Listening)
   ============================================================ */
.transcript {
  font-family: "Charis SIL", "DejaVu Serif", serif;
  color: var(--fg-default);
  font-size: 1.05em;
  background: var(--bg-surface);
  padding: 8px 12px;
  border-radius: 6px;
}

/* ============================================================
   Image-schema diagrams + picture cues
   ============================================================ */
.diagram {
  display: block;
  margin: 10px auto;
  max-width: 320px;
  height: auto;
}
.picture {
  display: block;
  margin: 10px auto;
  max-width: 100%;
  max-height: 280px;
  width: auto;
  height: auto;
  border-radius: 8px;
  box-shadow: var(--shadow-image);
}
.img-credit, .attribution {
  display: block;
  text-align: center;
  font-size: 0.75em;
  color: var(--fg-fainter);
  margin-top: 2px;
  margin-bottom: 10px;
  font-style: italic;
}

/* ============================================================
   Cloze blank styling
   ============================================================ */
.cloze {
  font-weight: 700;
  color: var(--cloze-fg);
  background: var(--target-bg);
  padding: 0 4px;
  border-radius: 3px;
}

/* ============================================================
   <details> reveal (Contrast Why / Recognition show-context)
   ============================================================ */
details {
  margin: 8px auto;
  max-width: 560px;
}
details summary {
  cursor: pointer;
  user-select: none;
  color: var(--info-fg);
  font-size: 0.88em;
  font-weight: 600;
  letter-spacing: 0.01em;
  list-style: none;
  outline: none;
  padding: 4px 8px;
  border-radius: 4px;
}
details summary::-webkit-details-marker { display: none; }
details summary::before {
  content: "▸ ";
  display: inline-block;
  transition: transform 0.15s ease;
}
details[open] > summary::before { content: "▾ "; }
details summary:hover { background: var(--bg-surface); }

/* ============================================================
   Mobile
   ============================================================ */
@media (max-width: 600px) {
  .card { font-size: 17px; padding: 2px 0; }
  .sentence { font-size: 1.05em; }
  .answer-label, .label { font-size: 1.35em; }
  .option { padding: 7px 10px; font-size: 0.94em; }
  .tier, .why-block, .why, details, .ipa, .ipa-box { max-width: 100%; }
  .picture { max-height: 220px; }
}
"""

# ── Card templates (Anki front/back HTML) ───────────────────────────────
# All templates use the design-system v3 classes defined in SHARED_CSS:
#   .front          centered prompt + sentence wrapper
#   .instruction    small uppercase prompt label
#   .sentence       the example sentence (the cue)
#   .answer-block   centered answer-side container
#   .answer-label   large prominent answer (preposition label)
#   .answer-correct green confirmation pill (✓ Answer)
#   .tier           supporting context callout
#   .meta-grid      Pattern / Main use key-value rows
#   .why-block      explanation prose under answer
#   .tip-block      muted italic afterthought
#   .target / .target-badge   blue pill (Production target)
#   .options / .option        Contrast A/B options
#   .ipa / .transcript / .picture / .diagram   media display
RECOGNITION_FRONT = """
<div class="front">
  <div class="instruction">Identify the preposition's sense</div>
  <div class="sentence">{{Sentence}}</div>
</div>
"""
RECOGNITION_BACK = """
<div class="front">
  <div class="instruction">Identify the preposition's sense</div>
  <div class="sentence">{{Sentence}}</div>
  {{#Audio}}<div class="audio-row">{{Audio}}</div>{{/Audio}}
</div>
<hr id="answer">
<div class="answer-block">
  <div class="answer-label">{{Label}}</div>
  {{#Diagram}}<div>{{Diagram}}</div>{{/Diagram}}
  {{#Picture}}<div>{{Picture}}</div>{{/Picture}}
  <div class="meta-grid">
    {{#Pattern}}<span class="meta-key">Pattern</span><span class="meta-val">{{Pattern}}</span>{{/Pattern}}
    {{#MainUse}}<span class="meta-key">Main use</span><span class="meta-val">{{MainUse}}</span>{{/MainUse}}
    {{#QuickCue}}<span class="meta-key">Quick cue</span><span class="meta-val">{{QuickCue}}</span>{{/QuickCue}}
  </div>
  {{#IPA}}<div class="ipa">/{{IPA}}/</div>{{/IPA}}

  <details>
    <summary>Show full reference</summary>
    {{#Trajector}}<div class="tier">
      <h4>Trajector → Landmark{{#FrameOfRef}} ({{FrameOfRef}}){{/FrameOfRef}}</h4>
      <div>{{Trajector}} → {{Landmark}}</div>
    </div>{{/Trajector}}
    {{#ImageSchema}}<div class="tier">
      <h4>Image schema</h4><div>{{ImageSchema}}</div>
    </div>{{/ImageSchema}}
    {{#Contrast}}<div class="tier">
      <h4>Often confused with</h4><div>{{Contrast}}</div>
    </div>{{/Contrast}}
    {{#WhenNotToUse}}<div class="tier">
      <h4>When not to use</h4><div>{{WhenNotToUse}}</div>
    </div>{{/WhenNotToUse}}
  </details>
</div>
"""

CONTRAST_FRONT = """
<div class="front">
  <div class="instruction">Choose the correct preposition</div>
  <div class="sentence">{{Sentence}}</div>
  <div class="options">
    <div class="option"><span class="opt-letter">A.</span>{{OptionA}}</div>
    <div class="option"><span class="opt-letter">B.</span>{{OptionB}}</div>
  </div>
</div>
"""
CONTRAST_BACK = """
<div class="front">
  <div class="instruction">Choose the correct preposition</div>
  <div class="sentence">{{Sentence}}</div>
  {{#Audio}}<div class="audio-row">{{Audio}}</div>{{/Audio}}
</div>
<div class="options">
  <div class="option"><span class="opt-letter">A.</span>{{OptionA}}</div>
  <div class="option"><span class="opt-letter">B.</span>{{OptionB}}</div>
</div>
<hr id="answer">
<div class="answer-block">
  <span class="answer-correct">✓ {{Answer}}</span>
  <div class="why-block"><span class="why-label">Why: </span>{{Why}}</div>
  {{#Tip}}<div class="tip-block">{{Tip}}</div>{{/Tip}}
  {{#IPA}}<div class="ipa">/{{IPA}}/</div>{{/IPA}}
</div>
"""

PRODUCTION_FRONT = """
<div class="front">
  <div class="instruction">Write a response using the target</div>
  <div class="sentence">{{Prompt}}</div>
  <div><span class="target-badge">{{Target}}</span></div>
</div>
"""
PRODUCTION_BACK = """
<div class="front">
  <div class="instruction">Write a response using the target</div>
  <div class="sentence">{{Prompt}}</div>
  <div><span class="target-badge">{{Target}}</span></div>
  {{#Audio}}<div class="audio-row">{{Audio}}</div>{{/Audio}}
</div>
<hr id="answer">
<div class="answer-block">
  <div class="sample-label">Sample answer</div>
  <div class="sample-answer">{{Sample}}</div>
  {{#Why}}<details>
    <summary>Why this works</summary>
    <div class="tier"><div class="why">{{Why}}</div></div>
  </details>{{/Why}}
</div>
"""

# Cloze uses Anki's built-in cloze model (one template only).
CLOZE_FRONT = """
<div class="front">
  <div class="instruction">Fill in the missing preposition</div>
  <div class="sentence">{{cloze:Text}}</div>
  {{#Hint}}<div class="tier"><h4>Hint</h4><div>{{Hint}}</div></div>{{/Hint}}
</div>
"""
CLOZE_BACK = """
<div class="front">
  <div class="instruction">Fill in the missing preposition</div>
  <div class="sentence">{{cloze:Text}}</div>
  {{#Audio}}<div class="audio-row">{{Audio}}</div>{{/Audio}}
</div>
"""

LISTENING_FRONT = """
<div class="front">
  <div class="instruction">Listen and answer</div>
  <div class="audio-row">{{AudioRef}}</div>
  <div class="sentence">{{Question}}</div>
</div>
"""
LISTENING_BACK = """
<div class="front">
  <div class="instruction">Listen and answer</div>
  <div class="audio-row">{{AudioRef}}</div>
  <div class="sentence">{{Question}}</div>
</div>
<hr id="answer">
<div class="answer-block">
  <span class="answer-correct">✓ {{Answer}}</span>
  <div class="tier">
    <h4>Transcript</h4>
    <div class="transcript">{{Transcript}}</div>
  </div>
  {{#IPA}}<div class="ipa">/{{IPA}}/</div>{{/IPA}}
</div>
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
        MODEL_RECOGNITION, "Prepositions Recognition v3",
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
        MODEL_CONTRAST, "Prepositions Contrast v3",
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
        MODEL_PRODUCTION, "Prepositions Production v3",
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
        MODEL_CLOZE, "Prepositions Cloze v3",
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
        MODEL_LISTENING, "Prepositions Listening v3",
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
