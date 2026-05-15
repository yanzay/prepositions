#!/usr/bin/env python3
"""
Tier-2 image-schema SVG builder for the English Prepositions Anki package.

Whereas ../verbs/build_timelines.py renders one SVG per tense label on a
PAST/NOW/FUTURE axis, this script renders one SVG per **preposition (or
contrast pair)** on a 2-D figure/ground canvas, showing the trajector
(blue dot/box) in the canonical spatial relation to the landmark (grey
container/surface/line).

Output:
  media/diagrams/<slug>.svg            — one SVG per canonical Label
  media/diagrams_index.json            — { Label: filename }

The diagrams auto-invert in Anki dark mode via
@media (prefers-color-scheme: dark).

Coverage (≥ one diagram per canonical Recognition Label in Modules 01, 02, 04
and the spatial-prototype senses of Modules 11/12). Non-spatial senses
(temporal, dependent, idiomatic) fall back to text-only on the card.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

OUT_DIR    = Path("media/diagrams")
INDEX_JSON = Path("media/diagrams_index.json")


def slug(label: str) -> str:
    s = label.lower()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s).strip("-")
    return s or "untitled"


# ── SVG primitives ──────────────────────────────────────────────────────
HEADER = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 320 200" \
font-family="-apple-system, Segoe UI, Arial, sans-serif" font-size="11">
<style>
  .ground   {{ fill:#f3f4f6; stroke:#374151; stroke-width:1.5; }}
  .ground-line {{ stroke:#374151; stroke-width:2; fill:none; }}
  .figure   {{ fill:#1d4ed8; stroke:#1e3a8a; stroke-width:1.2; }}
  .figure-2 {{ fill:#dc2626; stroke:#7f1d1d; stroke-width:1.2; }}
  .arrow    {{ fill:none; stroke:#1d4ed8; stroke-width:2; marker-end:url(#arrowhead); }}
  .label    {{ fill:#6b7280; font-size:10px; }}
  .title    {{ font-size:13px; fill:#111827; font-weight:600; }}
  @media (prefers-color-scheme: dark) {{
    .ground       {{ fill:#1f2937; stroke:#9ca3af; }}
    .ground-line  {{ stroke:#9ca3af; }}
    .figure       {{ fill:#93c5fd; stroke:#bfdbfe; }}
    .figure-2     {{ fill:#fca5a5; stroke:#fecaca; }}
    .arrow        {{ stroke:#93c5fd; }}
    .label        {{ fill:#9ca3af; }}
    .title        {{ fill:#f9fafb; }}
  }}
</style>
<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="3"
       orient="auto"><path d="M0,0 L7,3 L0,6 Z" class="arrow"/></marker></defs>
<text x="10" y="20" class="title">{title}</text>
'''
FOOTER = "\n</svg>\n"


def box(x: int, y: int, w: int, h: int, cls: str = "ground") -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>'


def circle(cx: int, cy: int, r: int = 10, cls: str = "figure") -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="{cls}"/>'


def line(x1: int, y1: int, x2: int, y2: int, cls: str = "ground-line") -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}"/>'


def arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="arrow"/>'


def text(x: int, y: int, s: str, cls: str = "label", anchor: str = "middle") -> str:
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{s}</text>'


def write_svg(label: str, body: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{slug(label)}.svg"
    OUT_DIR.joinpath(fname).write_text(
        HEADER.format(title=label) + body + FOOTER, encoding="utf-8")
    return fname


# ── Per-label specs ─────────────────────────────────────────────────────
# Coordinate convention: 320 × 200 viewport. Ground (landmark) typically a
# rectangle around (80, 80) → (240, 160). Figure (trajector) is a 10 px
# blue dot positioned to express the spatial relation.

GROUND = box(80, 80, 160, 80) + text(160, 175, "landmark")


def _spec_in() -> str:
    # CONTAINER schema: figure inside the box
    return GROUND + circle(160, 120) + text(160, 100, "trajector")


def _spec_on() -> str:
    # SUPPORT schema: figure on top of the box
    return GROUND + circle(160, 75) + text(160, 60, "trajector")


def _spec_at() -> str:
    # POINT schema: figure adjacent to a single point on the landmark
    return line(160, 80, 160, 160) + circle(160, 160, 6) + circle(180, 120) + \
           text(180, 105, "trajector") + text(160, 175, "point")


def _spec_under() -> str:
    return GROUND + circle(160, 180) + text(160, 195, "trajector")


def _spec_over() -> str:
    return GROUND + circle(160, 50) + text(160, 35, "trajector")


def _spec_above() -> str:
    return GROUND + circle(160, 50) + text(160, 35, "higher than")


def _spec_below() -> str:
    return GROUND + circle(160, 180) + text(160, 195, "lower than")


def _spec_between() -> str:
    return box(60, 100, 60, 60) + box(200, 100, 60, 60) + circle(160, 130) + \
           text(160, 175, "trajector between two landmarks")


def _spec_among() -> str:
    parts = [box(60 + i * 40, 100, 30, 60) for i in range(6)]
    return "".join(parts) + circle(140, 130, 8) + \
           text(160, 185, "trajector among many landmarks")


def _spec_in_front_of() -> str:
    return GROUND + circle(60, 120) + text(60, 105, "trajector") + \
           text(160, 60, "(viewer)")


def _spec_behind() -> str:
    return GROUND + circle(260, 120) + text(260, 105, "trajector") + \
           text(160, 60, "(viewer)")


def _spec_next_to() -> str:
    return GROUND + circle(260, 120) + text(260, 105, "trajector adjacent")


def _spec_beside() -> str:
    return _spec_next_to()


def _spec_near() -> str:
    return GROUND + circle(280, 120, 8) + text(280, 105, "close, not touching")


def _spec_through() -> str:
    return GROUND + arrow(40, 120, 280, 120) + \
           text(160, 105, "path through interior")


def _spec_across() -> str:
    return line(80, 120, 240, 120) + arrow(40, 100, 280, 100) + \
           text(160, 90, "path across surface")


def _spec_along() -> str:
    return line(80, 130, 240, 130) + arrow(80, 110, 240, 110) + \
           text(160, 100, "path parallel to landmark")


def _spec_around() -> str:
    return circle(160, 130, 40, "ground") + arrow(120, 90, 200, 90) + \
           text(160, 175, "path encircling landmark")


def _spec_to() -> str:
    return arrow(60, 120, 220, 120) + circle(240, 120) + \
           text(240, 105, "destination")


def _spec_into() -> str:
    return GROUND + arrow(40, 120, 155, 120) + circle(160, 120) + \
           text(120, 105, "path → CONTAINER")


def _spec_onto() -> str:
    return GROUND + arrow(40, 50, 155, 75) + circle(160, 75) + \
           text(120, 40, "path → SUPPORT")


def _spec_out_of() -> str:
    return GROUND + arrow(160, 120, 280, 120) + circle(160, 120) + \
           text(220, 105, "path leaving CONTAINER")


def _spec_off() -> str:
    return GROUND + arrow(160, 75, 280, 75) + circle(160, 75) + \
           text(220, 60, "path leaving SUPPORT")


def _spec_from() -> str:
    return circle(60, 120) + arrow(70, 120, 240, 120) + \
           text(60, 105, "source")


def _spec_towards() -> str:
    return circle(60, 120) + arrow(70, 120, 240, 120, ) + \
           text(240, 105, "direction toward (not arrived)")


def _spec_past() -> str:
    return GROUND + arrow(40, 50, 280, 50) + \
           text(160, 40, "path bypassing landmark")


def _spec_up() -> str:
    return arrow(160, 180, 160, 40) + text(160, 30, "vertical path up")


def _spec_down() -> str:
    return arrow(160, 40, 160, 180) + text(160, 195, "vertical path down")


def _spec_inside() -> str:
    return GROUND + circle(160, 120) + text(160, 100, "interior region")


def _spec_outside() -> str:
    return GROUND + circle(40, 40) + text(40, 25, "exterior region")


def _spec_against() -> str:
    return GROUND + circle(72, 120) + text(72, 105, "contact + pressure")


# ── Map of canonical Recognition labels → spec function ────────────────
SPECS: dict[str, str] = {
    # Module 01 — Spatial Core
    "in (CONTAINER)":      _spec_in(),
    "on (SUPPORT)":        _spec_on(),
    "at (POINT)":          _spec_at(),
    # Module 02 — Spatial Extended
    "under":               _spec_under(),
    "over":                _spec_over(),
    "above":               _spec_above(),
    "below":               _spec_below(),
    "between":             _spec_between(),
    "among":               _spec_among(),
    "in front of":         _spec_in_front_of(),
    "behind":              _spec_behind(),
    "next to":             _spec_next_to(),
    "beside":              _spec_beside(),
    "near":                _spec_near(),
    "inside":              _spec_inside(),
    "outside":             _spec_outside(),
    "against":             _spec_against(),
    # Module 04 — Movement & Direction
    "to":                  _spec_to(),
    "into":                _spec_into(),
    "onto":                _spec_onto(),
    "out of":              _spec_out_of(),
    "off":                 _spec_off(),
    "from":                _spec_from(),
    "through":             _spec_through(),
    "across":              _spec_across(),
    "along":               _spec_along(),
    "around":              _spec_around(),
    "towards":             _spec_towards(),
    "past":                _spec_past(),
    "up":                  _spec_up(),
    "down":                _spec_down(),
}


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index: dict[str, str] = {}
    for label, body in SPECS.items():
        fname = write_svg(label, body)
        index[label] = fname
    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")
    print(f"✓ Wrote {len(SPECS)} image-schema diagram SVGs to {OUT_DIR}/")
    print(f"  Index: {INDEX_JSON}")


if __name__ == "__main__":
    main()
