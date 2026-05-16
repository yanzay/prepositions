#!/usr/bin/env python3
"""
Tier-2 image-schema SVG builder for the English Prepositions Anki package.

v3 coverage expansion — instead of one SVG per generic preposition base,
this version ships **one SVG per sense-tagged Recognition label** by
combining:

  1. A library of ~50 spatial / temporal / abstract image-schema specs
     (CONTAINER, SUPPORT, POINT, PATH, DEADLINE, DURATION, STATE,
     MEANS, AGENT, …).
  2. A label → schema routing map that fans the same primitive out
     to every sense in the deck.

The result: previously 5/565 labels (≈1%) had a diagram;
this build gets us to ~85–95% coverage of canonical Recognition labels.

Diagrams auto-invert in Anki dark mode via @media (prefers-color-scheme: dark).

Outputs:
  media/diagrams/<slug>.svg            — one SVG per canonical Label
  media/diagrams_index.json            — { Label: filename }
"""
from __future__ import annotations

import collections
import json
import re
from pathlib import Path

OUT_DIR    = Path("media/diagrams")
INDEX_JSON = Path("media/diagrams_index.json")
RECOGNITION_TSV = Path("prepositions_recognition.txt")


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
  .figure-3 {{ fill:#16a34a; stroke:#14532d; stroke-width:1.2; }}
  .arrow    {{ fill:none; stroke:#1d4ed8; stroke-width:2; marker-end:url(#arrowhead); }}
  .arrow-dim {{ fill:none; stroke:#9ca3af; stroke-width:1.5; stroke-dasharray:4,3; }}
  .label    {{ fill:#6b7280; font-size:10px; }}
  .title    {{ font-size:13px; fill:#111827; font-weight:600; }}
  @media (prefers-color-scheme: dark) {{
    .ground       {{ fill:#1f2937; stroke:#9ca3af; }}
    .ground-line  {{ stroke:#9ca3af; }}
    .figure       {{ fill:#93c5fd; stroke:#bfdbfe; }}
    .figure-2     {{ fill:#fca5a5; stroke:#fecaca; }}
    .figure-3     {{ fill:#86efac; stroke:#bbf7d0; }}
    .arrow        {{ stroke:#93c5fd; }}
    .arrow-dim    {{ stroke:#64748b; }}
    .label        {{ fill:#9ca3af; }}
    .title        {{ fill:#f9fafb; }}
  }}
</style>
<defs><marker id="arrowhead" markerWidth="8" markerHeight="8" refX="7" refY="3"
       orient="auto"><path d="M0,0 L7,3 L0,6 Z" class="arrow"/></marker></defs>
<title>{title}</title>
'''
FOOTER = "\n</svg>\n"


def box(x, y, w, h, cls="ground"):
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" class="{cls}"/>'


def circle(cx, cy, r=10, cls="figure"):
    return f'<circle cx="{cx}" cy="{cy}" r="{r}" class="{cls}"/>'


def line(x1, y1, x2, y2, cls="ground-line"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}"/>'


def arrow(x1, y1, x2, y2, cls="arrow"):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" class="{cls}"/>'


def text(x, y, s, cls="label", anchor="middle"):
    return f'<text x="{x}" y="{y}" text-anchor="{anchor}" class="{cls}">{s}</text>'


def path(d, cls="arrow"):
    return f'<path d="{d}" class="{cls}" fill="none"/>'


def write_svg(label: str, body: str) -> str:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    fname = f"{slug(label)}.svg"
    OUT_DIR.joinpath(fname).write_text(
        HEADER.format(title=label) + body + FOOTER, encoding="utf-8")
    return fname


# ── Schema primitives ───────────────────────────────────────────────────
# A "schema" is a parameterless function returning the SVG body for one
# canonical image-schema. We route many labels to the same schema.
GROUND = box(80, 80, 160, 80) + text(160, 175, "landmark")
GROUND_LARGE = box(40, 70, 240, 90) + text(160, 178, "region")


def _sch_container():
    # CONTAINER: dot inside bounded enclosure
    return GROUND + circle(160, 120) + text(160, 102, "trajector")


def _sch_area():
    # AREA: dot inside a larger bounded region (city / country)
    return GROUND_LARGE + circle(160, 115) + text(160, 100, "in the region")


def _sch_medium():
    # MEDIUM: dot suspended in fluid medium (water, air)
    body = '<defs><pattern id="water" patternUnits="userSpaceOnUse" width="12" height="12">'
    body += '<path d="M0,6 Q3,2 6,6 T12,6" stroke="#93c5fd" fill="none"/></pattern></defs>'
    body += box(60, 80, 200, 80, "ground")
    body += '<rect x="60" y="80" width="200" height="80" fill="url(#water)" opacity="0.4"/>'
    body += circle(160, 120) + text(160, 102, "trajector in medium")
    body += text(160, 175, "medium")
    return body


def _sch_support_horizontal():
    # SUPPORT: dot on top
    return GROUND + circle(160, 75) + text(160, 60, "trajector")


def _sch_support_vertical():
    # Picture/clock on a wall
    return (line(80, 60, 80, 170) + line(80, 170, 240, 170) +
            box(140, 90, 40, 50, "figure") + text(160, 80, "on the wall") +
            text(160, 185, "vertical surface"))


def _sch_support_inverted():
    # On the ceiling: figure hanging from upper surface
    return (line(60, 80, 260, 80, "ground-line") +
            text(160, 70, "ceiling") +
            circle(160, 100) + text(160, 125, "hangs from above"))


def _sch_point():
    # POINT: figure adjacent to one focal point
    return (line(160, 80, 160, 160) + circle(160, 160, 6) +
            circle(180, 120) + text(180, 105, "trajector") +
            text(160, 175, "point"))


def _sch_point_role():
    # Position/role: figure standing at a podium-like marker
    return (line(155, 100, 165, 100, "ground-line") +
            line(160, 100, 160, 160, "ground-line") +
            text(160, 175, "role / post") +
            circle(160, 90) + text(160, 75, "trajector at post"))


def _sch_under():
    return GROUND + circle(160, 180) + text(160, 195, "trajector")


def _sch_over():
    return GROUND + circle(160, 60) + text(160, 45, "trajector")


def _sch_over_spanning():
    # Arched path crossing above the landmark
    return (GROUND + path("M60,140 Q160,30 260,140") +
            text(160, 55, "arches over"))


def _sch_above():
    return (line(80, 160, 240, 160) + text(160, 175, "landmark") +
            circle(160, 90) + text(160, 75, "trajector"))


def _sch_below():
    return (line(80, 80, 240, 80) + text(160, 65, "landmark") +
            circle(160, 150) + text(160, 165, "trajector"))


def _sch_between():
    return (box(60, 80, 60, 80) + box(200, 80, 60, 80) +
            circle(160, 120) + text(160, 105, "trajector") +
            text(90, 175, "L1") + text(230, 175, "L2"))


def _sch_among():
    out = []
    for x in (70, 110, 150, 190, 230):
        out.append(circle(x, 100, 6, "figure-2"))
        out.append(circle(x, 140, 6, "figure-2"))
    out.append(circle(160, 120, 9))
    out.append(text(160, 90, "trajector among many"))
    return "".join(out)


def _sch_in_front_of():
    return (box(140, 100, 40, 60) + text(160, 175, "landmark") +
            circle(110, 130) + text(110, 115, "trajector"))


def _sch_behind():
    return (box(140, 100, 40, 60) + text(160, 175, "landmark") +
            circle(210, 130) + text(210, 115, "trajector"))


def _sch_next_to():
    return (box(140, 100, 40, 60) + text(160, 175, "landmark") +
            box(95, 100, 40, 60, "figure") + text(115, 90, "trajector"))


def _sch_beside():
    return _sch_next_to()


def _sch_near():
    return (circle(160, 130, 14, "ground") + text(160, 175, "landmark") +
            path("M160,130 m-50,0 a50,50 0 1,0 100,0 a50,50 0 1,0 -100,0", "arrow-dim") +
            circle(210, 95) + text(210, 80, "trajector nearby"))


def _sch_far_from():
    return (circle(80, 130, 10, "ground") + text(80, 150, "landmark") +
            circle(260, 130) + text(260, 115, "trajector") +
            arrow(95, 130, 245, 130, "arrow-dim"))


def _sch_through():
    return (box(120, 80, 80, 80) + text(160, 175, "landmark") +
            arrow(60, 120, 260, 120))


def _sch_across():
    return (box(80, 100, 160, 40) + text(160, 155, "landmark (river/road)") +
            arrow(160, 180, 160, 90))


def _sch_along():
    return (line(60, 130, 260, 130) + text(160, 175, "linear landmark") +
            arrow(70, 110, 250, 110))


def _sch_around():
    return (circle(160, 120, 18, "ground") + text(160, 175, "landmark") +
            path("M160,120 m-50,0 a50,50 0 1,0 100,0 a50,50 0 1,0 -100,0", "arrow"))


def _sch_to():
    return (circle(60, 130) + text(60, 115, "start") +
            arrow(75, 130, 245, 130) +
            circle(260, 130, 6, "ground") + text(260, 115, "goal"))


def _sch_into():
    return (GROUND + arrow(40, 120, 155, 120) +
            circle(170, 120) + text(170, 102, "trajector enters"))


def _sch_onto():
    return (GROUND + arrow(120, 40, 155, 75) +
            circle(160, 75) + text(160, 60, "lands on"))


def _sch_out_of():
    return (GROUND + arrow(170, 120, 290, 120) +
            circle(155, 120) + text(155, 102, "trajector exits"))


def _sch_off():
    return (GROUND + arrow(160, 75, 160, 30) +
            circle(160, 70) + text(160, 25, "leaves surface"))


def _sch_from():
    return (circle(60, 130, 6, "ground") + text(60, 115, "source") +
            arrow(75, 130, 250, 130))


def _sch_towards():
    return (arrow(60, 130, 230, 130) +
            circle(255, 130, 10, "ground") + text(255, 115, "target"))


def _sch_past():
    return (box(150, 110, 20, 40) + text(160, 165, "landmark") +
            arrow(50, 130, 290, 130))


def _sch_up():
    return (line(60, 180, 260, 180) +
            arrow(160, 180, 160, 50) + circle(160, 50))


def _sch_down():
    return (line(60, 50, 260, 50) +
            arrow(160, 50, 160, 180) + circle(160, 180))


def _sch_inside():
    return (box(60, 60, 200, 110) + text(160, 185, "interior") +
            circle(160, 115) + text(160, 95, "trajector inside"))


def _sch_outside():
    return (box(120, 80, 80, 80) + text(160, 175, "interior") +
            circle(60, 120) + text(60, 105, "trajector outside"))


def _sch_against():
    return (line(120, 60, 120, 170, "ground-line") +
            text(120, 185, "surface") +
            circle(135, 120) + text(150, 110, "presses against"))


def _sch_via():
    # via: A → waypoint → B
    return (circle(40, 130, 8, "ground") + text(40, 115, "A") +
            circle(160, 80, 9, "figure-2") + text(160, 65, "via") +
            circle(280, 130, 8, "ground") + text(280, 115, "B") +
            arrow(50, 130, 152, 87) + arrow(168, 87, 270, 130))


def _sch_about():
    # about: orbit-of-discussion around topic
    return (circle(160, 120, 16, "ground") + text(160, 100, "topic") +
            path("M160,120 m-60,0 a60,60 0 1,0 120,0 a60,60 0 1,0 -120,0", "arrow-dim") +
            text(160, 195, "discussion encircles topic"))


def _sch_above_relative():  # ahead of, in advance of (spatial-temporal)
    return (arrow(60, 130, 250, 130) +
            circle(110, 130, 9, "figure-3") + text(110, 115, "trajector") +
            circle(210, 130, 9, "ground") + text(210, 115, "landmark"))


# ── Temporal schemas ────────────────────────────────────────────────────
def _sch_time_point():
    # AT a clock time: vertical mark on a horizontal timeline
    return (line(40, 120, 280, 120) +
            text(40, 110, "past", anchor="start") +
            text(280, 110, "future", anchor="end") +
            line(160, 105, 160, 135, "ground-line") +
            circle(160, 120, 6, "figure") + text(160, 95, "at this moment"))


def _sch_time_period():
    # IN a year/month/season: shaded band on a timeline
    return (line(40, 120, 280, 120) +
            text(40, 110, "past", anchor="start") +
            text(280, 110, "future", anchor="end") +
            f'<rect x="115" y="108" width="90" height="24" '
            f'fill="#bfdbfe" stroke="#1d4ed8" stroke-width="1.5" opacity="0.6"/>' +
            text(160, 150, "within this period"))


def _sch_time_day():
    # ON a day: tab on timeline (more discrete than IN)
    return (line(40, 120, 280, 120) +
            text(40, 110, "past", anchor="start") +
            text(280, 110, "future", anchor="end") +
            box(150, 95, 20, 30, "figure") + text(160, 85, "on this day"))


def _sch_duration():
    # FOR a period: arrow spanning a stretch of timeline
    return (line(40, 120, 280, 120) +
            text(40, 110, "past", anchor="start") +
            text(280, 110, "future", anchor="end") +
            arrow(90, 145, 230, 145) + arrow(230, 145, 90, 145) +
            text(160, 168, "spans this duration"))


def _sch_before():
    return (line(40, 120, 280, 120) +
            circle(110, 120, 9, "figure") + text(110, 105, "trajector") +
            circle(210, 120, 9, "ground") + text(210, 105, "landmark event") +
            text(160, 150, "trajector precedes"))


def _sch_after():
    return (line(40, 120, 280, 120) +
            circle(110, 120, 9, "ground") + text(110, 105, "landmark event") +
            circle(210, 120, 9, "figure") + text(210, 105, "trajector") +
            text(160, 150, "trajector follows"))


def _sch_ago():
    return (line(40, 120, 280, 120) +
            circle(260, 120, 8, "ground") + text(260, 105, "now") +
            circle(80, 120, 9, "figure") + text(80, 105, "past event") +
            arrow(260, 140, 90, 140) + text(170, 165, "backwards from now"))


def _sch_since():
    return (line(40, 120, 280, 120) +
            circle(80, 120, 9, "figure") + text(80, 105, "anchor") +
            arrow(95, 120, 270, 120) + text(180, 145, "from anchor → now"))


def _sch_until():
    return (line(40, 120, 280, 120) +
            arrow(50, 120, 220, 120) +
            circle(230, 120, 8, "ground") + text(230, 105, "endpoint") +
            text(140, 145, "continues up to"))


def _sch_by_deadline():
    return (line(40, 120, 280, 120) +
            f'<rect x="40" y="108" width="200" height="24" '
            f'fill="#bfdbfe" stroke="#1d4ed8" stroke-width="1.2" opacity="0.5"/>' +
            line(240, 100, 240, 140, "ground-line") +
            circle(240, 120, 6, "figure-2") +
            text(240, 95, "deadline") +
            text(140, 168, "any time up to deadline"))


def _sch_during():
    return (line(40, 120, 280, 120) +
            f'<rect x="100" y="108" width="120" height="24" '
            f'fill="#bbf7d0" stroke="#16a34a" stroke-width="1.5" opacity="0.6"/>' +
            text(160, 150, "throughout the event") +
            text(160, 100, "event boundary"))


def _sch_throughout():
    return (line(40, 120, 280, 120) +
            f'<rect x="40" y="108" width="240" height="24" '
            f'fill="#bbf7d0" stroke="#16a34a" stroke-width="1.5" opacity="0.6"/>' +
            text(160, 155, "every moment of period"))


def _sch_within():
    return (line(40, 120, 280, 120) +
            f'<rect x="100" y="108" width="120" height="24" '
            f'fill="#fde68a" stroke="#92400e" stroke-width="1.5" opacity="0.6"/>' +
            circle(170, 120, 6, "figure") + text(170, 95, "any time inside"))


def _sch_in_from_now():
    return (line(40, 120, 280, 120) +
            circle(80, 120, 8, "ground") + text(80, 105, "now") +
            arrow(80, 145, 230, 145) +
            circle(240, 120, 8, "figure") + text(240, 105, "future point") +
            text(160, 168, "interval ahead"))


# ── Abstract / functional schemas ───────────────────────────────────────
def _sch_means():
    # BY/VIA means: instrument arrow
    return (circle(60, 130) + text(60, 115, "agent") +
            arrow(75, 130, 245, 130) +
            box(150, 100, 50, 25, "figure-2") + text(175, 95, "instrument") +
            circle(265, 130, 8, "ground") + text(265, 115, "result"))


def _sch_agent():
    # BY agent (passive): tool driven by hand
    return (circle(60, 130, 12) + text(60, 113, "actor") +
            arrow(78, 130, 215, 130) +
            box(225, 110, 50, 40, "ground") + text(250, 105, "patient"))


def _sch_state():
    # IN a state: figure surrounded by a colored aura
    return ('<circle cx="160" cy="120" r="55" fill="#fde68a" '
            'stroke="#d97706" stroke-width="1.5" opacity="0.6"/>' +
            circle(160, 120) + text(160, 95, "trajector in state") +
            text(160, 185, "state envelope"))


def _sch_topic():
    return _sch_about()


def _sch_recipient():
    # TO recipient: arrow from giver to receiver
    return (circle(60, 130) + text(60, 113, "giver") +
            arrow(75, 130, 245, 130) +
            box(225, 110, 40, 40, "ground") + text(245, 100, "recipient") +
            box(140, 120, 18, 18, "figure-2") + text(149, 113, "gift"))


def _sch_beneficiary():
    # FOR someone: arrow pointing to a beneficiary
    return (box(40, 110, 60, 40, "figure") + text(70, 100, "action") +
            arrow(105, 130, 220, 130) +
            circle(245, 130, 12, "ground") + text(245, 113, "beneficiary"))


def _sch_purpose():
    return (circle(60, 130) + text(60, 115, "actor") +
            arrow(75, 130, 235, 130) +
            box(245, 110, 40, 40, "ground") + text(265, 100, "goal"))


def _sch_cause():
    # BECAUSE OF / DUE TO: cause arrow → effect
    return (circle(70, 130, 14, "figure-2") + text(70, 115, "cause") +
            arrow(90, 130, 235, 130) +
            box(245, 110, 40, 40, "ground") + text(265, 100, "effect"))


def _sch_exception():
    # EXCEPT FOR: set with one element excluded
    out = []
    for x in (80, 120, 160, 240):
        out.append(circle(x, 120, 9, "figure"))
    out.append(circle(200, 120, 9, "figure-2"))
    out.append('<line x1="190" y1="110" x2="210" y2="130" stroke="#dc2626" stroke-width="2"/>')
    out.append('<line x1="210" y1="110" x2="190" y2="130" stroke="#dc2626" stroke-width="2"/>')
    out.append(text(160, 155, "set minus excluded element"))
    return "".join(out)


def _sch_inclusion():
    # ALONG WITH / INCLUDING: group with arrow indicating addition
    return (circle(100, 120) + circle(140, 120) + circle(180, 120) +
            arrow(225, 120, 200, 120) +
            circle(245, 120, 10, "figure-2") + text(245, 105, "added") +
            text(140, 150, "set + addition"))


def _sch_resemblance():
    # LIKE: two similar shapes side-by-side
    return (circle(110, 120, 16) + text(110, 100, "X") +
            text(160, 125, "≈", cls="title") +
            circle(210, 120, 16, "figure-2") + text(210, 100, "Y"))


def _sch_composition():
    # OF (PARTITION / MADE OF / CONSIST OF)
    return (box(60, 80, 60, 80) + text(90, 175, "part 1") +
            text(160, 125, "+", cls="title") +
            box(200, 80, 60, 80) + text(230, 175, "part 2") +
            text(160, 60, "whole = parts"))


def _sch_dependence():
    # DEPEND ON: figure resting on support
    return (line(60, 160, 260, 160) +
            box(120, 110, 80, 50, "ground") + text(160, 175, "support") +
            circle(160, 100) + text(160, 85, "rests on (depends)"))


def _sch_focus():
    # FOCUS/CONCENTRATE ON: arrows converging on target
    return (circle(160, 120, 14, "figure-2") + text(160, 100, "target") +
            arrow(40, 50, 145, 110) + arrow(40, 190, 145, 130) +
            arrow(280, 50, 175, 110) + arrow(280, 190, 175, 130))


def _sch_object_of():
    # transitive verb taking bare object: arrow into object
    return (circle(60, 130) + text(60, 115, "actor") +
            arrow(75, 130, 195, 130) +
            box(205, 110, 60, 40, "ground") + text(235, 100, "object (bare)"))


def _sch_zero_prep():
    # zero preposition: dotted ring where a preposition would normally sit
    return ('<rect x="125" y="105" width="70" height="30" fill="none" '
            'stroke="#9ca3af" stroke-width="1.5" stroke-dasharray="4,4"/>' +
            text(160, 95, "no preposition needed") +
            circle(60, 120, 8, "figure") + text(60, 105, "X") +
            circle(260, 120, 8, "ground") + text(260, 105, "Y"))


def _sch_ratio():
    # OUT OF (ratio): N out of M visualized
    out = []
    for i in range(10):
        x = 60 + i * 22
        cls = "figure" if i < 3 else "ground"
        out.append(circle(x, 120, 7, cls))
    out.append(text(160, 90, "3 out of 10"))
    return "".join(out)


def _sch_depletion():
    # OUT OF (depletion): empty container
    return (box(80, 80, 160, 80) + text(160, 175, "container") +
            text(160, 120, "∅", cls="title") + text(160, 145, "empty"))


def _sch_emission():
    # OUT OF (emission): arrows radiating from source
    return (circle(160, 120, 16, "ground") + text(160, 100, "source") +
            arrow(160, 120, 60, 60) + arrow(160, 120, 260, 60) +
            arrow(160, 120, 60, 180) + arrow(160, 120, 260, 180))


# ── Label → schema routing ──────────────────────────────────────────────
# A label matches by EXACT match first, then by base-prefix + keyword fallback.
SCHEMAS = {
    # Containers / surfaces / points
    "container":          _sch_container,
    "enclosure":          _sch_container,
    "interior":           _sch_inside,
    "area":               _sch_area,
    "region":             _sch_area,
    "medium":             _sch_medium,
    "support":            _sch_support_horizontal,
    "support-clothing":   _sch_support_horizontal,
    "support-film":       _sch_support_horizontal,
    "support-vertical":   _sch_support_vertical,
    "support-inverted":   _sch_support_inverted,
    "point":              _sch_point,
    "point-role":         _sch_point_role,
    "point-large-venue":  _sch_area,
    # Spatial extended
    "under":              _sch_under,
    "over":               _sch_over_spanning,
    "over-spanning":      _sch_over_spanning,
    "above":              _sch_above,
    "below":              _sch_below,
    "between":            _sch_between,
    "among":              _sch_among,
    "in-front-of":        _sch_in_front_of,
    "behind":             _sch_behind,
    "next-to":            _sch_next_to,
    "beside":             _sch_beside,
    "near":               _sch_near,
    "far":                _sch_far_from,
    "inside":             _sch_inside,
    "outside":            _sch_outside,
    "against":            _sch_against,
    # Movement
    "through":            _sch_through,
    "across":             _sch_across,
    "along":              _sch_along,
    "around":             _sch_around,
    "to":                 _sch_to,
    "into":               _sch_into,
    "onto":               _sch_onto,
    "out-of":             _sch_out_of,
    "off":                _sch_off,
    "from":               _sch_from,
    "towards":            _sch_towards,
    "past":               _sch_past,
    "up":                 _sch_up,
    "down":               _sch_down,
    "via":                _sch_via,
    # Temporal
    "time-point":         _sch_time_point,
    "time-period":        _sch_time_period,
    "time-day":           _sch_time_day,
    "duration":           _sch_duration,
    "before":             _sch_before,
    "after":              _sch_after,
    "ago":                _sch_ago,
    "since":              _sch_since,
    "until":              _sch_until,
    "by-deadline":        _sch_by_deadline,
    "during":             _sch_during,
    "throughout":         _sch_throughout,
    "within-period":      _sch_within,
    "in-from-now":        _sch_in_from_now,
    # Abstract / functional
    "means":              _sch_means,
    "agent":              _sch_agent,
    "state":              _sch_state,
    "topic":              _sch_about,
    "about":              _sch_about,
    "recipient":          _sch_recipient,
    "beneficiary":        _sch_beneficiary,
    "purpose":            _sch_purpose,
    "cause":              _sch_cause,
    "exception":          _sch_exception,
    "inclusion":          _sch_inclusion,
    "resemblance":        _sch_resemblance,
    "composition":        _sch_composition,
    "dependence":         _sch_dependence,
    "focus":              _sch_focus,
    "object-of":          _sch_object_of,
    "zero-prep":          _sch_zero_prep,
    "ratio":              _sch_ratio,
    "depletion":          _sch_depletion,
    "emission":           _sch_emission,
    "ahead-of":           _sch_above_relative,
}


# ── Sense-tag → schema-key resolver ─────────────────────────────────────
# Given a Recognition Label like "in (TIME-POINT-PERIOD)" we extract the
# parenthesised sense tag and map it to a schema key. Matching is
# permissive: lowercased, hyphenated, then keyword-substring.
SENSE_KEYWORDS = [
    # Order matters — most-specific first
    ("clock-time",        "time-point"),
    ("clock",             "time-point"),
    ("time-of-day",       "time-point"),
    ("point-in-time",     "time-point"),
    ("temporal point",    "time-point"),
    ("named-festival",    "time-point"),
    ("routine-event",     "time-point"),
    ("event-activity",    "time-point"),
    ("point-role",        "point-role"),
    ("point-intersection","point"),
    ("corner-point",      "point"),
    ("corner-street",     "point"),
    ("corner-interior",   "container"),
    ("spatial point",     "point"),
    ("point-location",    "point"),
    ("point-venue",       "point"),
    ("point-large-venue", "area"),
    ("point",             "point"),
    ("date-day",          "time-day"),
    ("recurring-days",    "time-day"),
    ("day",               "time-day"),
    ("date",              "time-day"),
    ("month",             "time-period"),
    ("year",              "time-period"),
    ("season",            "time-period"),
    ("part-of-day",       "time-period"),
    ("temporal: year",    "time-period"),
    ("from-now",          "in-from-now"),
    ("within-period",     "within-period"),
    ("within",            "within-period"),
    ("past-relative",     "before"),
    ("past absence distance","ago"),
    ("past distance",     "ago"),
    ("past temporal anchor","ago"),
    ("backward-from-now", "ago"),
    ("ago",               "ago"),
    ("habitual",          "time-period"),
    ("deadline",          "by-deadline"),
    ("duration",          "duration"),
    ("temporal duration", "duration"),
    ("following-event",   "after"),
    ("temporal posterior","after"),
    ("temporal sequence", "after"),
    ("all-of-period",     "throughout"),
    ("pervasive duration","throughout"),
    ("recurring span",    "throughout"),
    ("container-venue",   "container"),
    ("container egress",  "out-of"),
    ("container",         "container"),
    ("corner-interior",   "container"),
    ("enclosure",         "container"),
    ("small-transport",   "container"),
    ("interior",          "inside"),
    ("bounded interior",  "inside"),
    ("protected interior","inside"),
    ("area",              "area"),
    ("region",            "area"),
    ("arrive destination","to"),
    ("medium",            "medium"),
    ("support-vertical",  "support-vertical"),
    ("support-inverted",  "support-inverted"),
    ("support-clothing",  "support-horizontal"),
    ("support-film",      "support-horizontal"),
    ("support",           "support"),
    ("activity focus",    "focus"),
    ("focus",             "focus"),
    ("line-route",        "along"),
    ("page-line",         "support"),
    ("event scheduled",   "time-day"),
    ("large-transport",   "support"),
    ("higher",            "above"),
    ("orbital altitude",  "above"),
    ("overhead elevation","above"),
    ("lower",             "below"),
    ("lower altitude",    "below"),
    ("depth measurement", "below"),
    ("rear",              "behind"),
    ("concealment in nature","behind"),
    ("rear concealment",  "behind"),
    ("rear side",         "behind"),
    ("alongside",         "next-to"),
    ("alongside linear",  "along"),
    ("adjacent specific", "next-to"),
    ("adjacent close",    "next-to"),
    ("immediate adjacency","next-to"),
    ("protective proximity","near"),
    ("road-adjacent",     "next-to"),
    ("flank positioning", "next-to"),
    ("building adjacency","next-to"),
    ("walkable distance", "near"),
    ("general vicinity",  "near"),
    ("proximity",         "near"),
    ("broad projection",  "across"),
    ("lateral crossing",  "across"),
    ("transverse trajectory","across"),
    ("facing separation", "across"),
    ("opposite side",     "across"),
    ("guided linear",     "along"),
    ("lengthwise progress","along"),
    ("parallel motion",   "along"),
    ("celestial orbit",   "around"),
    ("circular motion",   "around"),
    ("encirclement",      "around"),
    ("orbital circuit",   "around"),
    ("static perimeter",  "around"),
    ("thermal encirclement","around"),
    ("avoidance",         "about"),
    ("spatial: encircling","around"),
    ("interior transit",  "through"),
    ("penetrative excavation","through"),
    ("traversal",         "through"),
    ("completion",        "throughout"),
    ("via process",       "via"),
    ("spatial path",      "through"),
    ("evasive speed",     "past"),
    ("lateral bypass",    "past"),
    ("swift bypass",      "past"),
    ("continuous ascent", "up"),
    ("upward ascent",     "up"),
    ("vertical launch",   "up"),
    ("vertical fall",     "down"),
    ("downward",          "down"),
    ("descent",           "down"),
    ("detachment",        "off"),
    ("surface removal",   "off"),
    ("systematic removal","off"),
    ("intermediate stopover","via"),
    ("route mediation",   "via"),
    ("transit route",     "via"),
    ("divergence",        "from"),
    ("divergent evasion", "from"),
    ("emergency evasion", "from"),
    ("egression",         "out-of"),
    ("emission",          "emission"),
    ("exit",              "out-of"),
    ("depletion",         "depletion"),
    ("ratio",             "ratio"),
    ("composition",       "composition"),
    ("material",          "composition"),
    ("partition",         "composition"),
    ("resemblance",       "resemblance"),
    ("auditory",          "resemblance"),
    ("behavioral",        "resemblance"),
    ("gustatory",         "resemblance"),
    ("olfactory",         "resemblance"),
    ("sensation",         "resemblance"),
    ("beneficiary",       "beneficiary"),
    ("agent in passive",  "agent"),
    ("means/instrument",  "means"),
    ("instrumental",      "means"),
    ("instrument",        "means"),
    ("agent",             "agent"),
    ("state/condition",   "state"),
    ("abstract: state",   "state"),
    ("state",             "state"),
    ("topic",             "topic"),
    ("about",             "about"),
    ("verb+prep",         "object-of"),
    ("adj+prep",          "object-of"),
    ("noun+prep",         "object-of"),
    ("bare transitive",   "object-of"),
    ("bare destination",  "to"),
    ("bare noun of place","to"),
    ("zero preposition",  "zero-prep"),
    ("zero",              "zero-prep"),
    ("role-article-zero", "zero-prep"),
    ("habitual",          "time-period"),
    ("standard-reference","resemblance"),
    ("reason-inherent",   "cause"),
    ("grounds",           "cause"),
    ("causation",         "cause"),
    ("causal",            "cause"),
    ("ahead-of",          "ahead-of"),
    ("spatial-temporal",  "ahead-of"),
    ("exception",         "exception"),
    ("inclusion",         "inclusion"),
    ("emotional: finished with","after"),
    # Additional senses missed in coverage pass 1
    ("conditional",       "before"),
    ("contrast-formal",   "exception"),
    ("additive",          "inclusion"),
    ("parity",            "resemblance"),
    ("essence",           "resemblance"),
    ("substitution-formal","exception"),
    ("alignment",         "along"),
    ("formal-domain",     "topic"),
    ("framing",           "topic"),
    ("standards-formal",  "resemblance"),
    ("procedure-formal",  "resemblance"),
    ("decision-context",  "cause"),
    ("universality",      "exception"),
    ("negation-legal",    "exception"),
    ("negation-expectation","exception"),
    ("concessive",        "exception"),
    ("temporal-prospective","in-from-now"),
    ("temporal-pastarchaic","ago"),
    ("bare time adverbial","time-period"),
    ("temporal span",     "duration"),
    ("time-span",         "duration"),
    ("bounded interval",  "duration"),
    ("terminal",          "after"),
    ("start",             "before"),
    ("persistence",       "duration"),
    ("closing",           "after"),
    ("layered underneath","under"),
    ("under/formal",      "under"),
    ("underlying",        "under"),
    ("role",              "point-role"),
    ("idiomatic-vehicle", "means"),
    ("idiomatic-manner",  "means"),
    ("idiomatic-error",   "means"),
    ("idiomatic-unintentional","means"),
    ("idiomatic-degree",  "means"),
    ("idiomatic-media",   "support"),
    ("idiomatic-blame",   "state"),
    ("idiomatic-performance","state"),
    ("idiomatic-availability-c1","state"),
    ("idiomatic-command-c1","cause"),
    ("idiomatic-opportune","time-point"),
    ("idiomatic-opportunity","time-point"),
    ("idiomatic-price",   "state"),
    ("idiomatic-struggle-c1","state"),
    ("idiomatic-location-small","container"),
    ("route-manner",      "via"),
    ("route-path",        "via"),
    ("verb-b2",           "object-of"),
    ("verb-c1",           "object-of"),
    ("bare",              "object-of"),
    # Coverage pass 2 — formal & idiomatic mop-up
    ("sequence-formal",   "after"),
    ("idiomatic-location-large","area"),
    ("idiomatic-locomotion","means"),
    ("idiomatic-intentional","purpose"),
    ("idiomatic-punctuality","time-point"),
    ("idiomatic-digital", "support"),
    ("idiomatic-basis-c1","cause"),
    ("idiomatic-threshold-b2","before"),
    ("idiomatic-threshold-transition-c1","before"),
    ("idiomatic-threshold-imminent-b2","before"),
    ("representation",    "agent"),
    ("representation-voice","agent"),
    ("clothing",          "support"),
    ("film",              "support"),
    ("german-trap",       None),  # interference rows skip diagrams
    ("french-trap",       None),
    ("russian-trap",      None),
    ("spanish-trap",      None),
    ("mandarin-trap",     None),
    ("japanese-trap",     None),
    ("portuguese-trap",   None),
]

# Base preposition fallback: if no sense matches, route by base alone.
BASE_DEFAULTS = {
    "in":      "container",
    "on":      "support",
    "at":      "point",
    "under":   "under",
    "over":    "over",
    "above":   "above",
    "below":   "below",
    "between": "between",
    "among":   "among",
    "in front of": "in-front-of",
    "behind":  "behind",
    "next to": "next-to",
    "beside":  "beside",
    "near":    "near",
    "far from":"far",
    "inside":  "inside",
    "outside": "outside",
    "against": "against",
    "through": "through",
    "across":  "across",
    "along":   "along",
    "around":  "around",
    "to":      "to",
    "into":    "into",
    "onto":    "onto",
    "out of":  "out-of",
    "off":     "off",
    "from":    "from",
    "towards": "towards",
    "toward":  "towards",
    "past":    "past",
    "up":      "up",
    "down":    "down",
    "via":     "via",
    "by":      "means",
    "for":     "purpose",
    "with":    "means",
    "about":   "about",
    "of":      "composition",
    "before":  "before",
    "after":   "after",
    "ago":     "ago",
    "since":   "since",
    "until":   "until",
    "during":  "during",
    "throughout":"throughout",
    "within":  "within-period",
    "across from":"across",
    "ahead of":"ahead-of",
    "away from":"from",
    "out from":"out-of",
    "depend on":"dependence",
    "focus on": "focus",
    "consist of":"composition",
    "like":    "resemblance",
    "such as": "inclusion",
    "including":"inclusion",
    "except":  "exception",
    "except for":"exception",
    "instead of":"exception",
    "according to":"resemblance",
    "due to":  "cause",
    "owing to":"cause",
    "thanks to":"cause",
    "because of":"cause",
    "as a result of":"cause",
    "by virtue of":"cause",
    "by means of":"means",
    "in front of": "in-front-of",
    "on account of":"cause",
    "in spite of":"exception",
    "regardless of":"exception",
    "in case of":"cause",
    "interested in":"focus",
    "afraid of":"object-of",
    "married to":"object-of",
    "dream of": "object-of",
    "look into":"focus",
    "agree on": "object-of",
    "agree to": "object-of",
    "agree with":"object-of",
    "discuss":  "object-of",
    "enter":    "object-of",
    "listen to":"object-of",
    "wait for": "object-of",
    "look at":  "object-of",
    "home":     "to",
    # Multi-word + bare-adverbial bases
    "beneath":  "under",
    "below":    "below",
    "as":       "resemblance",
    "as if":    "resemblance",
    "as such":  "resemblance",
    "as well as":"inclusion",
    "as long as":"duration",
    "as opposed to":"exception",
    "as … as":  "resemblance",
    "in accordance with":"resemblance",
    "in addition to":"inclusion",
    "in conformity with":"resemblance",
    "in lieu of":"exception",
    "in line with":"along",
    "in respect of":"topic",
    "in terms of":"topic",
    "in view of":"cause",
    "in spite of":"exception",
    "in case of":"cause",
    "contrary to":"exception",
    "despite":  "exception",
    "notwithstanding":"exception",
    "irrespective of":"exception",
    "from-to":  "duration",
    "from … to …":"duration",
    "begin with":"before",
    "end in":   "after",
    "continue with":"duration",
    "finish with":"after",
    "here":     "point",
    "henceforth":"in-from-now",
    "heretofore":"ago",
    "last week":"time-period",
    "next year":"time-period",
    "hospital": "to",
    "corroborate":"object-of",
    "gainsay":  "object-of",
    "by way of":"via",
    "by bus":   "means",
    "by car":   "means",
    "by plane": "means",
    "by hand":  "means",
    "by heart": "means",
    "by sight": "means",
    "by chance":"means",
    "by far":   "means",
    "by mistake":"means",
    "by accident":"means",
    "in a car": "container",
    "in the morning":"time-period",
    "in the news":"support",
    "in the photo":"support",
    "in the throes":"state",
    "in time":  "time-point",
    "on TV":    "support",
    "on Monday":"time-day",
    "at fault": "state",
    "at his best":"state",
    "at a discount":"state",
    "at one's disposal":"state",
    "at the behest":"cause",
    "at the right time":"time-point",
}


def resolve_schema(label: str) -> str | None:
    """Return the schema-key for a given Recognition label, or None."""
    low = label.lower()
    paren = re.search(r"\(([^)]+)\)", low)
    if paren:
        sense = paren.group(1)
        for kw, key in SENSE_KEYWORDS:
            if kw in sense:
                return key  # may be None (interference rows skip)
    base = re.split(r" \(", label, maxsplit=1)[0].lower()
    return BASE_DEFAULTS.get(base)


# ── Build ───────────────────────────────────────────────────────────────
def collect_labels() -> list[str]:
    labels = set()
    if not RECOGNITION_TSV.exists():
        return []
    with RECOGNITION_TSV.open(encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 13:
                continue
            labels.add(cols[1])
    return sorted(labels)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Clean stale SVGs from previous builds so renames are reflected.
    for old in OUT_DIR.glob("*.svg"):
        old.unlink()

    index: dict[str, str] = {}
    skipped: list[str] = []
    per_schema = collections.Counter()
    for label in collect_labels():
        key = resolve_schema(label)
        if key is None or key not in SCHEMAS:
            skipped.append(label)
            continue
        body = SCHEMAS[key]()
        fname = write_svg(label, body)
        index[label] = fname
        per_schema[key] += 1

    INDEX_JSON.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8")
    total = len(index) + len(skipped)
    print(f"✓ Wrote {len(index)}/{total} diagram SVGs "
          f"({100*len(index)//max(1,total)}% coverage)")
    print(f"  Distinct schemas used: {len(per_schema)}")
    print(f"  Skipped (no schema): {len(skipped)}")
    if skipped and len(skipped) <= 25:
        for s in skipped:
            print(f"    - {s}")


if __name__ == "__main__":
    main()
