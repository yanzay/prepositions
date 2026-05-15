#!/usr/bin/env python3
"""
Tier-3 taxonomy tagger for the English Prepositions Anki package.

Augments the Tags field of every row in the five staging files with the eight
required tag axes (where they aren't already present):

    module:01..12
    type:recognition|contrast|production|cloze|listening
    sense:spatial|temporal|movement|dependent|phrasal|idiomatic|interference|polysemy|zero
    frequency:high|mid|low
    register:formal|neutral|informal|spoken|academic
    cefr:a1|a2|b1|b2|c1|c2
    image-schema:container|support|point|path|over|under|between|cluster|none
    generalisable:yes|no|partial

Inference is heuristic, deterministic, and idempotent — re-running the script
won't add duplicate tags. Existing tag values along these axes are PRESERVED;
the script only fills gaps. Hand-corrections always win.
"""
from __future__ import annotations

import csv
import io
import re
from pathlib import Path

# ── Heuristic vocabularies ──────────────────────────────────────────────

# Highest-frequency prepositions per BNC / COCA top-100. Membership →
# frequency:high.
HIGH_FREQ_PREPS = {
    "of", "in", "to", "for", "with", "on", "at", "from", "by", "about",
    "as", "into", "like", "through", "after", "over", "between", "out",
    "against", "during", "without", "before", "under", "around", "among",
}
LOW_FREQ_PREPS = {
    "amid", "amidst", "betwixt", "circa", "ere", "lest", "neath", "notwithstanding",
    "qua", "sans", "thence", "unto", "vis-à-vis", "athwart",
}

# Module → tag inferred from explicit `module:` tag if present, else from the
# `sense:` tag, else from sentence keywords.
SENSE_TO_MODULE = {
    "spatial":      None,    # could be 01 or 02 — leave alone if absent
    "temporal":     "module:03",
    "movement":     "module:04",
    "dependent":    None,    # 05/06/07 disambiguated by dependent:* sub-tag
    "phrasal":      "module:08",
    "idiomatic":    "module:09",
    "interference": "module:10",
    "polysemy":     "module:11",
    "zero":         "module:12",
}
DEPENDENT_TO_MODULE = {
    "dependent:verb":      "module:05",
    "dependent:adjective": "module:06",
    "dependent:noun":      "module:07",
}

# Register heuristics keyed off the sentence text.
FORMAL_PATTERNS = [
    r"\bwith regard to\b", r"\bin accordance with\b", r"\bnotwithstanding\b",
    r"\bhereby\b", r"\bin respect of\b", r"\bby virtue of\b",
    r"\bon behalf of\b", r"\bin light of\b",
]
INFORMAL_PATTERNS = [
    r"\bgonna\b", r"\bwanna\b", r"\bgotta\b", r"\bsorta\b", r"\bkinda\b",
    r"\bkidding\b", r"\bya\b", r"\bdunno\b",
]
ACADEMIC_PATTERNS = [
    r"\bthesis\b", r"\bhypothesis\b", r"\bdissertation\b", r"\bthe study\b",
    r"\bresearch shows\b", r"\bin contrast\b", r"\bfurthermore\b",
]
SPOKEN_PATTERNS = [
    r"^[A-Z][^.?!]*\?$", r"\.\.\.$", r"\bI mean\b", r"\bkind of\b",
    r"\bsort of\b", r"\byou know\b", r"\blike\b,",
]

# CEFR per English Vocabulary Profile (criterial-feature based, *per sense*).
CEFR_A1_PREPS = {"in", "on", "at", "to", "from", "of", "with"}      # core spatial / time / instrument
CEFR_A2_PREPS = {"by", "for", "about", "between", "near", "before", "after", "under", "over"}
CEFR_B1_PREPS = {"during", "since", "until", "behind", "above", "below", "through", "across",
                 "along", "into", "onto", "out of", "off", "towards", "around"}
CEFR_B2_PREPS = {"despite", "instead of", "in spite of", "according to", "due to",
                 "because of", "regardless of", "in addition to", "apart from"}
CEFR_C1_PREPS = {"on behalf of", "in light of", "by means of", "with regard to",
                 "in respect of", "ahead of", "in case of", "in terms of"}
CEFR_C2_PREPS = {"notwithstanding", "by virtue of", "in accordance with"}

# Image-schema mapping derived from the Recognition Label / canonical sense.
LABEL_TO_SCHEMA = {
    "in":           "container",
    "on":           "support",
    "at":           "point",
    "into":         "path",
    "onto":         "path",
    "out of":       "path",
    "off":          "path",
    "to":           "path",
    "from":         "path",
    "through":      "path",
    "across":       "path",
    "along":        "path",
    "around":       "path",
    "towards":      "path",
    "past":         "path",
    "up":           "path",
    "down":         "path",
    "over":         "over",
    "above":        "over",
    "under":        "under",
    "below":        "under",
    "beneath":      "under",
    "between":      "between",
    "among":        "cluster",
}

# Card-type per file.
TYPE_BY_FILE = {
    "prepositions_recognition.txt": "recognition",
    "prepositions_contrast.txt":    "contrast",
    "prepositions_production.txt":  "production",
    "prepositions_cloze.txt":       "cloze",
    "prepositions_listening.txt":   "listening",
}

# Tag-axis prefixes the script is responsible for.
NEW_PREFIXES = (
    "module:", "type:", "sense:", "frequency:", "register:",
    "cefr:", "image-schema:", "generalisable:",
)


# ── Inference helpers ───────────────────────────────────────────────────

def _has_axis(tags: list[str], axis: str) -> bool:
    return any(t.startswith(axis) for t in tags)


def _strip_axis(tags: list[str], axis: str) -> list[str]:
    return [t for t in tags if not t.startswith(axis)]


def _first_match_pattern(text: str, patterns: list[str]) -> bool:
    for p in patterns:
        if re.search(p, text, flags=re.IGNORECASE):
            return True
    return False


def infer_register(text: str) -> str:
    if _first_match_pattern(text, FORMAL_PATTERNS):
        return "register:formal"
    if _first_match_pattern(text, ACADEMIC_PATTERNS):
        return "register:academic"
    if _first_match_pattern(text, INFORMAL_PATTERNS):
        return "register:informal"
    if _first_match_pattern(text, SPOKEN_PATTERNS):
        return "register:spoken"
    return "register:neutral"


def _label_lower(tag_set: list[str], row: dict) -> str:
    """Best-effort guess at the canonical preposition for the row."""
    label = row.get("Label", "") or row.get("Answer", "") or row.get("Target", "")
    if label:
        # Strip parenthesised qualifier: "in (CONTAINER)" → "in"
        return re.sub(r"\s*\(.*\)\s*", "", label).strip().lower()
    # Fallback: take first token from the sentence/text
    text = row.get("Sentence", "") or row.get("Text", "") or row.get("Transcript", "")
    m = re.search(r"\b([a-z]+(?:\s+of)?)\b", text.lower())
    return m.group(1) if m else ""


def infer_frequency(prep: str) -> str:
    if prep in HIGH_FREQ_PREPS:
        return "frequency:high"
    if prep in LOW_FREQ_PREPS:
        return "frequency:low"
    return "frequency:mid"


def infer_cefr(prep: str) -> str:
    if prep in CEFR_C2_PREPS: return "cefr:c2"
    if prep in CEFR_C1_PREPS: return "cefr:c1"
    if prep in CEFR_B2_PREPS: return "cefr:b2"
    if prep in CEFR_B1_PREPS: return "cefr:b1"
    if prep in CEFR_A2_PREPS: return "cefr:a2"
    if prep in CEFR_A1_PREPS: return "cefr:a1"
    return "cefr:b1"  # safe default for unmapped


def infer_image_schema(prep: str, existing_tags: list[str], sense: str) -> str:
    # Honour an explicit image-schema:* tag if already set.
    for t in existing_tags:
        if t.startswith("image-schema:"):
            return t
    if prep in LABEL_TO_SCHEMA:
        return f"image-schema:{LABEL_TO_SCHEMA[prep]}"
    if sense in ("temporal", "dependent", "idiomatic", "phrasal", "zero"):
        return "image-schema:none"
    return "image-schema:none"


def infer_generalisable(sense: str, existing_tags: list[str]) -> str:
    for t in existing_tags:
        if t.startswith("generalisable:"):
            return t
    # Dependent prepositions are atomic chunks → not generalisable.
    if sense == "dependent":
        return "generalisable:no"
    # Spatial / movement core senses are highly generalisable.
    if sense in ("spatial", "movement", "polysemy"):
        return "generalisable:yes"
    return "generalisable:partial"


def infer_module(existing_tags: list[str], sense: str) -> str | None:
    for t in existing_tags:
        if t.startswith("module:"):
            return t
    # Disambiguate dependent-* sub-tag first.
    for t in existing_tags:
        if t in DEPENDENT_TO_MODULE:
            return DEPENDENT_TO_MODULE[t]
    return SENSE_TO_MODULE.get(sense)


def infer_sense(existing_tags: list[str], prep: str) -> str:
    for t in existing_tags:
        if t.startswith("sense:"):
            return t.split(":", 1)[1]
    if prep in {"in", "on", "at", "under", "over", "between", "among",
                "behind", "near", "by", "next to", "beside", "above", "below"}:
        return "spatial"
    if prep in {"to", "into", "onto", "from", "out of", "off", "through",
                "across", "along", "around", "towards", "past", "up", "down"}:
        return "movement"
    if prep in {"during", "since", "until", "for", "before", "after", "by"}:
        return "temporal"
    return "spatial"  # conservative default for the largest module


def augment_tags(tags_str: str, row: dict, *, file_card_type: str) -> str:
    tags = tags_str.split()
    tag_set_lower = [t.lower() for t in tags]
    prep = _label_lower(tag_set_lower, row)
    text = (row.get("Sentence") or row.get("Sample") or row.get("Text")
            or row.get("Transcript") or "")

    # Resolve sense first — many other axes depend on it.
    sense = infer_sense(tag_set_lower, prep)
    if not _has_axis(tags, "sense:"):
        tags.append(f"sense:{sense}")

    if not _has_axis(tags, "type:"):
        tags.append(f"type:{file_card_type}")

    module = infer_module(tag_set_lower, sense)
    if module and not _has_axis(tags, "module:"):
        tags.append(module)

    if not _has_axis(tags, "frequency:"):
        tags.append(infer_frequency(prep))

    if not _has_axis(tags, "register:"):
        tags.append(infer_register(text))

    if not _has_axis(tags, "cefr:"):
        tags.append(infer_cefr(prep))

    if not _has_axis(tags, "image-schema:"):
        tags.append(infer_image_schema(prep, tag_set_lower, sense))

    if not _has_axis(tags, "generalisable:"):
        tags.append(infer_generalisable(sense, tag_set_lower))

    # Deduplicate while preserving order.
    seen: set[str] = set()
    out: list[str] = []
    for t in tags:
        if t not in seen:
            out.append(t)
            seen.add(t)
    return " ".join(out)


# ── File processing ─────────────────────────────────────────────────────

def _parse_columns_header(lines: list[str]) -> list[str]:
    for ln in lines:
        if ln.startswith("#columns:"):
            return ln[len("#columns:"):].split("\t")
    raise SystemExit("Missing #columns: header line")


def process_file(path: Path) -> int:
    if not path.exists():
        return 0
    card_type = TYPE_BY_FILE[path.name]
    lines = path.read_text(encoding="utf-8").splitlines()
    columns = _parse_columns_header(lines)
    if "Tags" not in columns:
        raise SystemExit(f"{path.name}: no Tags column")
    tag_idx = columns.index("Tags")

    out_lines: list[str] = []
    rows_changed = 0
    for line in lines:
        if not line or line.startswith("#"):
            out_lines.append(line)
            continue
        reader = csv.reader([line], delimiter="\t", quotechar='"')
        row_list = next(reader)
        if len(row_list) != len(columns):
            out_lines.append(line)
            continue
        row_dict = dict(zip(columns, row_list))
        new_tags = augment_tags(row_dict["Tags"], row_dict,
                                file_card_type=card_type)
        if new_tags != row_dict["Tags"]:
            row_list[tag_idx] = new_tags
            rows_changed += 1
        buf = io.StringIO()
        csv.writer(buf, delimiter="\t", quotechar='"',
                   quoting=csv.QUOTE_MINIMAL).writerow(row_list)
        out_lines.append(buf.getvalue().rstrip("\r\n"))
    path.write_text("\n".join(out_lines) + "\n", encoding="utf-8")
    return rows_changed


def main():
    total = 0
    for fname in TYPE_BY_FILE:
        n = process_file(Path(fname))
        if n:
            print(f"  {fname}: {n} rows updated")
        total += n
    print(f"\n✓ Tier-3 taxonomy tags applied to {total} rows.")


if __name__ == "__main__":
    main()
