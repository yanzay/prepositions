#!/usr/bin/env python3
"""
Quality lint for the prepositions Anki staging files.

Companion to validate_anki_data.py:
  - validate_anki_data.py = STRUCTURAL checks (column counts, required tags,
    answer integrity). MUST pass before build.
  - lint_anki_data.py     = QUALITY checks distilled from the 4-auditor
    review pass (linguistic / taxonomic / pedagogical / slop). Failures are
    WARNINGS by default; use --strict to make them errors.

The lint encodes ~14 deterministic rules that a human auditor would otherwise
spot manually. It does NOT replace human judgment for sentence naturalness,
L1-trap linguistic reality, or LLM-flatness of sample answers — those still
require a periodic human review.

Run:
    python3 lint_anki_data.py            # warn-only, exit 0
    python3 lint_anki_data.py --strict   # exit 1 on any warning
    python3 lint_anki_data.py --json     # machine-readable output
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parent

FILES = {
    "prepositions_recognition.txt": ["Sentence", "Label", "Sense", "Pattern",
                                     "Trajector", "Landmark", "FrameOfRef",
                                     "ImageSchema", "MainUse", "QuickCue",
                                     "Contrast", "WhenNotToUse", "Tags"],
    "prepositions_contrast.txt":    ["Sentence", "OptionA", "OptionB", "Answer",
                                     "Why", "Tip", "Tags"],
    "prepositions_production.txt":  ["Prompt", "Target", "Sense", "Sample",
                                     "Why", "Tags"],
    "prepositions_cloze.txt":       ["Text", "Hint", "Tags"],
    "prepositions_listening.txt":   ["AudioRef", "Question", "Answer",
                                     "Transcript", "Tags"],
}


# ───────────────────────── Reference vocabularies ─────────────────────────

# Module ↔ sense expected mapping (audit B, dimension 1)
MODULE_TO_SENSE = {
    "01": {"spatial"},
    "02": {"spatial"},
    "03": {"temporal"},
    "04": {"movement"},
    "05": {"dependent"},
    "06": {"dependent"},
    "07": {"dependent"},
    "08": {"phrasal"},
    "09": {"idiomatic"},
    "10": {"interference"},
    "11": {"polysemy"},
    # 12 allows zero or sometimes idiomatic when teaching the contrast
    "12": {"zero", "idiomatic"},
}

# CEFR band per preposition (audit B, dimension 3)
# CEFR base-band per CANONICAL preposition, per English Vocabulary Profile.
# This is the BARE-PREP base band; cards using the prep in extended/abstract
# senses legitimately drift one or two bands higher (and the lint tolerates
# ±2 bands of drift). Only severe outliers (>2 bands) are flagged.
CEFR_BAND = {
    "in": "a1", "on": "a1", "at": "a1", "to": "a1", "of": "a1",
    "for": "a1", "with": "a1", "from": "a1", "about": "a1",
    "by": "a2", "into": "a2", "between": "a2", "among": "b1",
    "near": "a2", "before": "a2", "after": "a2", "under": "a2", "over": "a2",
    "during": "b1", "since": "a2", "until": "a2", "behind": "a2",
    "above": "a2", "below": "a2", "through": "a2", "across": "a2",
    "along": "b1", "onto": "b1", "out of": "a2", "off": "a2",
    "towards": "b1", "around": "a2", "without": "b1",
    "despite": "b2", "in spite of": "b2", "because of": "b1",
    "instead of": "b1", "according to": "b2", "due to": "b2",
    "regardless of": "c1", "on behalf of": "c1", "in light of": "c1",
    "by means of": "c1", "with regard to": "c1", "ahead of": "b2",
    "in case of": "b2", "in terms of": "b2",
    "notwithstanding": "c2", "by virtue of": "c2",
    "in accordance with": "c1",
}
CEFR_ORDER = {"a1": 1, "a2": 2, "b1": 3, "b2": 4, "c1": 5, "c2": 6}

# Image-schema mapping per canonical preposition (audit B, dimension 2)
SCHEMA_FOR_PREP = {
    "in": "container", "into": "path", "out of": "path", "outside": "container",
    "inside": "container",
    "on": "support", "onto": "path", "off": "path",
    "at": "point",
    "to": "path", "from": "path", "through": "path", "across": "path",
    "along": "path", "around": "path", "towards": "path", "past": "path",
    "up": "path", "down": "path",
    "over": "over", "above": "over",
    "under": "under", "below": "under", "beneath": "under",
    "between": "between", "among": "cluster", "amongst": "cluster",
    "in front of": "between", "next to": "between", "across from": "between",
    "ahead of": "between", "behind": "between",
    # 'near' / 'beside' / 'around (static perimeter)' are pedagogically
    # acceptable as POINT or CLUSTER per Tyler & Evans (proximity-without-
    # touching is a point-vicinity relation; static perimeter is the cluster
    # of points around a landmark). Flagging them as 'between' would be
    # over-prescriptive — accept whatever the data has.
    "by": "point",
}

# Placeholder trajector/landmark values (audit D, slop pattern 1)
PLACEHOLDERS = {"subject", "object", "event", "condition", "time", "place",
                "thing", "trajector", "landmark", "person",
                "(person)", "(thing)", "(event)"}

# Idioms that require an animate subject (audit A, agency check)
ANIMATE_REQUIRING_IDIOMS = {
    "at fault", "in love", "in trouble", "in pain", "in a hurry",
    "under arrest", "out of breath", "on purpose",
}

# Inanimate subject heads — flag if used with the above idioms
INANIMATE_SUBJECTS = {
    "the accident", "the building", "the road", "the weather", "the rain",
    "the meeting", "the report", "the shop", "the system",
}

# AmE/BrE dialect-sensitive lexical pairs (audit A, dialect consistency)
BRE_LEXIS = {"cinema", "petrol", "lorry", "lift", "rubbish", "queue",
             "trousers", "biscuit", "flat (apartment)", "holiday", "underground"}
AME_LEXIS = {"movie theater", "gas (station)", "truck", "elevator", "trash",
             "line", "pants", "cookie", "apartment", "vacation", "subway"}
BRE_PREP_PATTERNS = ["at the weekend", "in hospital", "different to"]
AME_PREP_PATTERNS = ["on the weekend", "in the hospital", "different than"]

# Self-contradiction trap for Module 12 (audit C, M12 critical)
ZERO_PREP_FORBIDDEN_FOLLOWERS = {
    "to ", "from ", "for ", "with ", "of ", "about ", "by ",
    "into ", "onto ", "off ", "through ",
}

# Cloze cue-leakage patterns (audit D, F)
def hint_leaks_answer(hint: str, answer: str) -> bool:
    """Return True if the hint leaks the answer in a way that defeats recall.

    Allowed (NOT a leak):
      - Hint shows the canonical collocation chunk being taught:
        e.g. hint="depend on" for cloze answer "on" (the hint IS the collocation
        the learner is meant to internalise).
      - Hint references the answer inside quotes: e.g. "'at night' is a fixed phrase".
      - Hint names a function rather than the form: "deadline marker", "container",
        "support surface" — these don't accidentally contain a one-letter word.
    Flagged (real leak):
      - Hint plainly states the answer in running prose with no scaffold around it.
    """
    if not hint or not answer:
        return False
    if not re.search(rf"\b{re.escape(answer)}\b", hint, re.I):
        return False
    # Allowed: answer is inside a quoted string (the hint references an idiom)
    if re.search(rf"['\"][^'\"]*\b{re.escape(answer)}\b[^'\"]*['\"]", hint, re.I):
        return False
    # Allowed: hint contains a known collocation pattern with the answer as the
    # second token (e.g. 'depend on', 'interested in', 'good at', 'married to')
    coll_pattern = re.compile(
        rf"\b\w+\s+{re.escape(answer)}\b",
        re.I,
    )
    if coll_pattern.search(hint):
        m = coll_pattern.search(hint)
        prev = m.group().split()[0].lower() if m else ""
        if prev not in {"a", "an", "the", "of", "to", "for", "with",
                        "in", "on", "at", "by", "from"}:
            return False
    # Allowed: hint IS the multi-word lexical chunk being taught
    # (Module 08 phrasal heads, Module 09 idioms). When the hint and the
    # answer have the same lowercased text (within ±1 word), the hint is
    # by-design the canonical chunk the learner must reproduce.
    if hint.strip().lower() == answer.strip().lower():
        return False
    # Allowed: answer is a multi-word phrase (≥2 tokens) and the hint is
    # essentially a label/synonym of that phrase
    if len(answer.split()) >= 2:
        return False
    return True


# ─────────────────────── File reader ───────────────────────────────────────
def read_rows(path: Path) -> Iterable[tuple[int, dict[str, str]]]:
    cols = FILES[path.name]
    if not path.exists():
        return
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(),
                                 start=1):
        if not raw or raw.startswith("#"):
            continue
        fields = raw.split("\t")
        if len(fields) != len(cols):
            continue  # structural error — caught by validate_anki_data.py
        yield lineno, dict(zip(cols, fields))


# ─────────────────────── Helpers ───────────────────────────────────────────
def tag_value(tags_str: str, axis: str) -> str | None:
    for t in tags_str.split():
        if t.startswith(axis + ":"):
            return t.split(":", 1)[1]
    return None


def strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def cloze_strip(text: str) -> str:
    return re.sub(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}", r"\1", text)


def cloze_answer(text: str) -> str:
    m = re.search(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}", text)
    return m.group(1).strip() if m else ""


# Multi-word prepositions get their canonical schema directly, not via
# their first-token (which mis-maps "in front of" → schema-of-'in').
MULTIWORD_PREP_SCHEMA = {
    "in front of": "between",
    "next to":     "between",
    "across from": "between",
    "out of":      "path",
    "in spite of": "none",
    "instead of":  "none",
    "ahead of":    "between",
    "in front":    "between",
    "behind of":   "between",
    "apart from":  "none",
    "according to":"none",
    "due to":      "none",
    "because of":  "none",
    "in addition to":"none",
    "as for":      "none",
    "in light of": "none",
    "in case of":  "none",
    "by means of": "none",
    "by virtue of":"none",
    "regardless of":"none",
    "on behalf of":"none",
    "owing to":     "none",
    "in line with": "none",
    "aside from":   "none",
    "on account of":"none",
    "in view of":   "none",
    "with regard to":"none",
    "in respect of":"none",
    "at a loss":    "none",
}

# CEFR overrides for advanced multi-word phrasal heads (audit B):
# these are correctly B2/C1 even though their first token is A1.
MULTIWORD_CEFR = {
    "owing to":      "b2",
    "in line with":  "b2",
    "aside from":    "b2",
    "on account of": "b2",
    "in view of":    "b2",
    "with regard to":"b2",
    "in respect of": "c1",
    "at a loss":     "b2",
}

def label_to_prep(label: str) -> str:
    """'in (CONTAINER)' → 'in';  'depend on (verb+prep)' → 'on';
    'in front of (FORWARD SIDE)' → 'in front of' (multi-word retained)."""
    bare = re.sub(r"\s*\(.*\)\s*", "", label).strip().lower()
    if bare in MULTIWORD_PREP_SCHEMA:
        return bare
    # If a 2-3 token sequence matches a known multi-word prep, return it whole
    tokens = bare.split()
    for n in (3, 2):
        cand = " ".join(tokens[:n])
        if cand in MULTIWORD_PREP_SCHEMA:
            return cand
    if not tokens:
        return ""
    # If the LAST token is in our prep schema (e.g. 'depend on' / 'interested in'),
    # treat it as a dependent collocation: return the last token.
    if len(tokens) >= 2 and tokens[-1] in SCHEMA_FOR_PREP:
        return tokens[-1]
    return tokens[0]


def first_subject_np(sentence: str) -> str:
    """Heuristic: lowercase first 2-3 word noun phrase before the verb-like word."""
    s = strip_html(sentence).lower()
    s = re.sub(r"^[\W_]+", "", s)
    # Take everything up to the first verb-ish word ("is/was/has/had/will/be...")
    m = re.match(r"((?:\w+\s+){0,3}?)(?=\b(?:is|was|are|were|has|have|had|will|would|"
                 r"can|could|should|may|must|do|does|did|seems|appears)\b)", s)
    return (m.group(1) if m else s[:30]).strip()


# ─────────────────────── Lint checks ───────────────────────────────────────
class Lint:
    def __init__(self):
        self.issues: list[dict] = []

    def add(self, severity: str, file: str, lineno: int, rule: str, msg: str,
            *, fix: str = ""):
        self.issues.append({
            "severity": severity, "file": file, "line": lineno,
            "rule": rule, "msg": msg, "fix": fix,
        })

    # ── R1: module ↔ sense consistency ────────────────────────────────────
    def check_module_sense(self, file: str, lineno: int, row: dict):
        tags = row.get("Tags", "")
        m = tag_value(tags, "module")
        s = tag_value(tags, "sense")
        if not m or not s:
            return
        expected = MODULE_TO_SENSE.get(m)
        if expected and s not in expected:
            self.add("ERROR", file, lineno, "module-sense-mismatch",
                     f"module:{m} should have sense∈{sorted(expected)}, got sense:{s}",
                     fix=f"replace 'sense:{s}' with 'sense:{next(iter(expected))}'")

    # ── R2: image-schema ↔ preposition consistency ────────────────────────
    def check_image_schema(self, file: str, lineno: int, row: dict):
        if file != "prepositions_recognition.txt":
            return
        sense = tag_value(row.get("Tags", ""), "sense")
        if sense not in ("spatial", "movement"):
            return
        label = row.get("Label", "")
        # Skip deliberate cluster-tagged 'around' rows with STATIC/PERIMETER/ENCIRCLEMENT.
        # Per Tyler & Evans, static perimeter uses cluster schema, not path.
        if "around" in label.lower() and any(
            keyword in label.upper()
            for keyword in ("STATIC PERIMETER", "ENCIRCLEMENT STATIC", "THERMAL ENCIRCLEMENT")
        ):
            return
        prep = label_to_prep(label)
        expected = SCHEMA_FOR_PREP.get(prep)
        if not expected:
            return
        actual = row.get("ImageSchema", "").strip()
        actual_tag = tag_value(row.get("Tags", ""), "image-schema")
        if actual and actual != expected:
            self.add("WARN", file, lineno, "image-schema-mismatch",
                     f"label '{label}' (prep='{prep}') expects image-schema:{expected}, "
                     f"got '{actual}'",
                     fix=f"set ImageSchema and image-schema tag to '{expected}'")
        elif actual_tag and actual_tag != expected:
            self.add("WARN", file, lineno, "image-schema-tag-mismatch",
                     f"image-schema tag '{actual_tag}' disagrees with prep '{prep}' (expected '{expected}')")

    # ── R3: CEFR ↔ preposition consistency ─────────────────────────────────
    def check_cefr(self, file: str, lineno: int, row: dict):
        tags = row.get("Tags", "")
        cefr = tag_value(tags, "cefr")
        if not cefr:
            return
        # Find canonical prep from Label or Answer or Target
        prep = ""
        if file == "prepositions_recognition.txt":
            prep = label_to_prep(row.get("Label", ""))
        elif file == "prepositions_contrast.txt":
            prep = row.get("Answer", "").strip().lower()
        elif file == "prepositions_production.txt":
            prep = row.get("Target", "").strip().lower().split("/")[0].strip()
        elif file == "prepositions_cloze.txt":
            prep = cloze_answer(row.get("Text", "")).lower()
        elif file == "prepositions_listening.txt":
            prep = row.get("Answer", "").strip().lower()
        prep = re.sub(r"\(.*\)", "", prep).strip()
        # Multi-word phrasal heads override the bare-prep base band
        expected = MULTIWORD_CEFR.get(prep) or CEFR_BAND.get(prep)
        if not expected:
            return
        actual_band = CEFR_ORDER.get(cefr, 0)
        expected_band = CEFR_ORDER.get(expected, 0)
        # Suppress for dependent collocations and idiomatic phrases — for those,
        # the WHOLE LEXICAL CHUNK has its own CEFR rating that is independent
        # of the bare preposition's base band. e.g. 'subordinate to' is B2 even
        # though 'to' is A1; 'oblivious to' is B2; 'in lieu of' is C1.
        sense = (row.get("Sense") or "").lower()
        is_collocation = any(s in sense for s in (
            "verb+prep", "adj+prep", "noun+prep", "phrasal",
            "idiomatic", "fixed", "verb-prep", "adj-prep", "noun-prep",
            "multi-word", "high-register", "academic",
        ))
        if is_collocation or "dependent:" in tags:
            return
        # Allow ±2 band tolerance — basic preps used in advanced senses are
        # legitimately tagged higher (e.g. 'in trouble' = abstract container, B1+
        # not A1). Only flag when the drift is >2 bands.
        if actual_band and abs(actual_band - expected_band) > 2:
            self.add("WARN", file, lineno, "cefr-band-off",
                     f"prep '{prep}' base band {expected.upper()}; got {cefr.upper()} "
                     f"(distance {abs(actual_band - expected_band)} bands)")

    # ── R4: dependent: sub-tag for Modules 05/06/07 ────────────────────────
    def check_dependent_subtag(self, file: str, lineno: int, row: dict):
        tags = row.get("Tags", "")
        m = tag_value(tags, "module")
        if m not in ("05", "06", "07"):
            return
        expected_sub = {"05": "verb", "06": "adjective", "07": "noun"}[m]
        sub = tag_value(tags, "dependent")
        if sub != expected_sub:
            self.add("WARN", file, lineno, "dependent-subtag-missing",
                     f"module:{m} should carry dependent:{expected_sub}, got '{sub}'")

    # ── R5: Recognition Sense field ↔ sense: tag agreement ────────────────
    def check_field_tag_agreement(self, file: str, lineno: int, row: dict):
        if file == "prepositions_recognition.txt":
            sense_field = row.get("Sense", "").strip().lower()
            sense_tag = tag_value(row.get("Tags", ""), "sense")
            if sense_field and sense_tag and sense_field != sense_tag:
                self.add("WARN", file, lineno, "sense-field-tag-disagree",
                         f"Sense field '{sense_field}' ≠ sense:{sense_tag}",
                         fix=f"set Sense field to '{sense_tag}'")
            schema_field = row.get("ImageSchema", "").strip().lower()
            schema_tag = tag_value(row.get("Tags", ""), "image-schema")
            if schema_field and schema_tag and schema_field != schema_tag:
                self.add("WARN", file, lineno, "schema-field-tag-disagree",
                         f"ImageSchema field '{schema_field}' ≠ image-schema:{schema_tag}",
                         fix=f"set ImageSchema field to '{schema_tag}'")
        elif file == "prepositions_production.txt":
            sense_field = row.get("Sense", "").strip().lower()
            sense_tag = tag_value(row.get("Tags", ""), "sense")
            if sense_field and sense_tag and sense_field != sense_tag:
                self.add("WARN", file, lineno, "sense-field-tag-disagree",
                         f"Sense field '{sense_field}' ≠ sense:{sense_tag}")

    # ── R6: Placeholder Trajector / Landmark ──────────────────────────────
    def check_placeholders(self, file: str, lineno: int, row: dict):
        if file != "prepositions_recognition.txt":
            return
        sense = tag_value(row.get("Tags", ""), "sense")
        if sense not in ("spatial", "movement"):
            return
        for fld in ("Trajector", "Landmark"):
            v = row.get(fld, "").strip().lower()
            if v in PLACEHOLDERS:
                self.add("WARN", file, lineno, "placeholder-trajector-landmark",
                         f"{fld} field is placeholder '{v}', should be the actual noun phrase")

    # ── R7: Module 12 self-contradiction (zero-prep but sentence has prep) ─
    def check_zero_prep_contradiction(self, file: str, lineno: int, row: dict):
        if file != "prepositions_recognition.txt":
            return
        if tag_value(row.get("Tags", ""), "sense") != "zero":
            return
        text = strip_html(row.get("Sentence", ""))
        # If the sentence contains '{{c1::ø::...}}' AND a real preposition
        # immediately after — that's the bug pattern.
        if "{{c1::ø" in text or "{{c1::Ø" in text.lower():
            after_cloze = re.split(r"\{\{c1::[øØ][^}]*\}\}", text, maxsplit=1)
            if len(after_cloze) > 1:
                tail = after_cloze[1].lstrip()
                for forb in ZERO_PREP_FORBIDDEN_FOLLOWERS:
                    if tail.lower().startswith(forb):
                        self.add("ERROR", file, lineno, "zero-prep-contradiction",
                                 f"row tagged sense:zero but cloze is followed by "
                                 f"required preposition '{forb.strip()}': {text[:80]}",
                                 fix="delete row OR move to module:05/08, OR remove "
                                     "the '" + forb.strip() + "' from the sentence")
                        return

    # ── R8: Listening Transcript = parenthesized metadata, not English ────
    def check_listening_transcript(self, file: str, lineno: int, row: dict):
        if file != "prepositions_listening.txt":
            return
        t = row.get("Transcript", "").strip()
        if not t:
            return
        if t.startswith("(") and t.endswith(")"):
            self.add("ERROR", file, lineno, "listening-metadata-transcript",
                     f"Transcript looks like a label, not utterable English: '{t}'",
                     fix="replace with the exact English sentence the audio contains")
        elif "(bare" in t or "(transitive" in t.lower():
            self.add("WARN", file, lineno, "listening-transcript-has-metadata",
                     f"Transcript contains metadata-like parenthetical: '{t}'")

    # ── R9: Translate-from-LX Production prompts ──────────────────────────
    def check_translate_prompts(self, file: str, lineno: int, row: dict):
        if file != "prepositions_production.txt":
            return
        prompt = row.get("Prompt", "")
        if prompt.startswith("Translate:") or prompt.startswith("Translate "):
            self.add("WARN", file, lineno, "translate-from-LX-prompt",
                     f"Prompt starts with 'Translate:' — restricts card to a "
                     f"specific L1: '{prompt[:80]}'",
                     fix="rewrite as L1-agnostic scenario prompt")
        # Detect non-Latin or accented source text in prompt
        # Only flag if multiple non-English diacritics cluster (a real foreign
        # source sentence). Single 'é' (café, résumé), 'ï' (naïve), 'à' (à la
        # carte) etc. are loanwords accepted in English orthography.
        diacritic_chars = re.findall(r"[ñáíóúüçàèùâêîôûäëïöÜß]", prompt)
        if len(diacritic_chars) >= 3:
            self.add("WARN", file, lineno, "non-english-in-prompt",
                     f"Prompt contains {len(diacritic_chars)} non-English diacritics, "
                     f"likely L1 source text: '{prompt[:80]}'")

    # ── R10: Inanimate subject + animate-only idiom ───────────────────────
    def check_animacy(self, file: str, lineno: int, row: dict):
        if file != "prepositions_recognition.txt":
            return
        sentence = strip_html(row.get("Sentence", "")).lower()
        for idiom in ANIMATE_REQUIRING_IDIOMS:
            if idiom in sentence:
                subj = first_subject_np(row.get("Sentence", ""))
                # Quick check: does subj match an inanimate?
                for inan in INANIMATE_SUBJECTS:
                    if subj.startswith(inan):
                        self.add("WARN", file, lineno, "inanimate-subject-animate-idiom",
                                 f"idiom '{idiom}' requires animate subject; "
                                 f"got '{subj}': {sentence[:80]}")
                        return

    # ── R11: AmE/BrE dialect mixing ───────────────────────────────────────
    def check_dialect_mixing(self, file: str, lineno: int, row: dict):
        # Only run on the primary text field
        text_field = {
            "prepositions_recognition.txt": "Sentence",
            "prepositions_contrast.txt":    "Sentence",
            "prepositions_production.txt":  "Sample",
            "prepositions_cloze.txt":       "Text",
            "prepositions_listening.txt":   "Transcript",
        }.get(file)
        if not text_field:
            return
        text = strip_html(row.get(text_field, "")).lower()
        if not text:
            return
        bre_hits = sum(1 for w in BRE_LEXIS if re.search(rf"\b{re.escape(w)}\b", text))
        ame_hits = sum(1 for w in AME_LEXIS if re.search(rf"\b{re.escape(w)}\b", text))
        bre_prep = sum(1 for p in BRE_PREP_PATTERNS if p in text)
        ame_prep = sum(1 for p in AME_PREP_PATTERNS if p in text)
        if (bre_hits or bre_prep) and (ame_hits or ame_prep):
            self.add("WARN", file, lineno, "dialect-mixing",
                     f"sentence mixes BrE and AmE markers: '{text[:80]}'")

    # ── R12: Cloze hint leaks the answer ──────────────────────────────────
    def check_cloze_hint_leak(self, file: str, lineno: int, row: dict):
        if file != "prepositions_cloze.txt":
            return
        ans = cloze_answer(row.get("Text", ""))
        hint = row.get("Hint", "")
        if hint_leaks_answer(hint, ans):
            self.add("WARN", file, lineno, "cloze-hint-leaks-answer",
                     f"Hint '{hint}' contains the answer '{ans}'")

    # ── R13: Cross-file Recognition⇔Cloze duplicate sentences ─────────────
    # (run once at the end, not per row)

    # ── R14: Module 10 missing or impossible l1 tag ───────────────────────
    def check_l1_for_m10(self, file: str, lineno: int, row: dict):
        tags = row.get("Tags", "")
        if tag_value(tags, "module") != "10":
            return
        l1 = tag_value(tags, "l1")
        if not l1:
            self.add("ERROR", file, lineno, "missing-l1-tag",
                     "module:10 row has no l1:<lang> tag")
        elif l1 not in {"spanish", "french", "german", "russian",
                        "mandarin", "japanese"}:
            self.add("WARN", file, lineno, "unknown-l1-value",
                     f"l1:{l1} not in canonical 6-language set")


# ───────────────────── Cross-file duplicate detection ─────────────────────
def detect_cross_file_duplicates(rows_by_file):
    """Audit D, category A: Recognition⇔Cloze sentence overlap."""
    rec_sentences: dict[str, int] = {}
    for lineno, row in rows_by_file.get("prepositions_recognition.txt", []):
        s = strip_html(row.get("Sentence", "")).strip().lower()
        if s:
            rec_sentences[s] = lineno
    out = []
    for lineno, row in rows_by_file.get("prepositions_cloze.txt", []):
        text = strip_html(cloze_strip(row.get("Text", ""))).strip().lower()
        if text in rec_sentences:
            out.append((lineno, text, rec_sentences[text]))
    return out


# ───────────────────── Driver ─────────────────────────────────────────────
def run() -> Lint:
    lint = Lint()
    rows_by_file: dict[str, list] = {}
    for fname in FILES:
        path = ROOT / fname
        rows = list(read_rows(path))
        rows_by_file[fname] = rows
        for lineno, row in rows:
            lint.check_module_sense(fname, lineno, row)
            lint.check_image_schema(fname, lineno, row)
            lint.check_cefr(fname, lineno, row)
            lint.check_dependent_subtag(fname, lineno, row)
            lint.check_field_tag_agreement(fname, lineno, row)
            lint.check_placeholders(fname, lineno, row)
            lint.check_zero_prep_contradiction(fname, lineno, row)
            lint.check_listening_transcript(fname, lineno, row)
            lint.check_translate_prompts(fname, lineno, row)
            lint.check_animacy(fname, lineno, row)
            lint.check_dialect_mixing(fname, lineno, row)
            lint.check_cloze_hint_leak(fname, lineno, row)
            lint.check_l1_for_m10(fname, lineno, row)
    # Cross-file duplicates (warning only)
    for cloze_ln, text, rec_ln in detect_cross_file_duplicates(rows_by_file):
        lint.add("INFO", "prepositions_cloze.txt", cloze_ln,
                 "cross-file-duplicate-sentence",
                 f"Cloze sentence also appears in recognition.txt:{rec_ln}: "
                 f"'{text[:70]}'")
    return lint


def main() -> int:
    ap = argparse.ArgumentParser(description="Quality lint for prepositions deck")
    ap.add_argument("--strict", action="store_true",
                    help="Exit 1 on any WARN or ERROR (default: only on ERROR)")
    ap.add_argument("--json", action="store_true",
                    help="Emit JSON instead of human-readable output")
    ap.add_argument("--rule", default=None,
                    help="Only show issues matching this rule name")
    args = ap.parse_args()

    lint = run()
    issues = lint.issues
    if args.rule:
        issues = [i for i in issues if i["rule"] == args.rule]

    by_severity = defaultdict(int)
    by_rule = defaultdict(int)
    for i in issues:
        by_severity[i["severity"]] += 1
        by_rule[i["rule"]] += 1

    if args.json:
        print(json.dumps({"issues": issues, "by_severity": dict(by_severity),
                          "by_rule": dict(by_rule)},
                         indent=2, ensure_ascii=False))
    else:
        for sev in ("ERROR", "WARN", "INFO"):
            sev_issues = [i for i in issues if i["severity"] == sev]
            if not sev_issues:
                continue
            print(f"\n=== {sev} ({len(sev_issues)}) ===")
            for i in sev_issues[:200]:
                fix = f"  → {i['fix']}" if i["fix"] else ""
                print(f"  {i['file']}:{i['line']:>3d}  [{i['rule']}] {i['msg']}{fix}")
            if len(sev_issues) > 200:
                print(f"  … and {len(sev_issues) - 200} more")
        print("\n=== Summary ===")
        for sev in ("ERROR", "WARN", "INFO"):
            print(f"  {sev:6s}  {by_severity[sev]}")
        print()
        print(f"  Issues by rule:")
        for rule in sorted(by_rule, key=lambda r: -by_rule[r]):
            print(f"    {by_rule[rule]:>4d}  {rule}")

    if by_severity["ERROR"]:
        return 1
    if args.strict and (by_severity["WARN"] or by_severity["INFO"]):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
