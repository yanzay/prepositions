#!/usr/bin/env python3
"""
Tier-2 IPA helper for the English Prepositions Anki package.

Computes a per-sentence IPA transcription (broad General-American) for every
unique English sentence in the corpus, plus a per-word lookup that surfaces
preposition-pronunciation oddities (the schwa reduction in *to/of/at/for*,
the silent <h> in *of*, the linking /n/ before vowels in *an*).

Output:
  media/ipa/<sha1[:12]>.txt    — one IPA string per sentence
  media/ipa_index.json         — { sha1[:12]: ipa_string }
  media/ipa_words.json         — { word_lowercase: ipa_string } (audit)

Backend: `eng-to-ipa` library (Carnegie-Mellon dict + heuristic fallback).
"""
from __future__ import annotations

import argparse
import csv as _csv
import hashlib
import json
import re
from pathlib import Path

MEDIA_DIR  = Path("media/ipa")
INDEX_JSON = Path("media/ipa_index.json")
WORDS_JSON = Path("media/ipa_words.json")

PUNCT_RE = re.compile(r"[\u2014\u2026\u201c\u201d\u2018\u2019\".,!?;:()\[\]\u2014\u2013]")
CLOZE_RE = re.compile(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}")

# ── OOV overrides ───────────────────────────────────────────────────────
# eng-to-ipa (CMUdict) doesn't always know contractions, BrE spellings,
# proper nouns, or the weak-form pronunciations that prepositions take in
# unstressed positions. Provide hand-curated broad GA transcriptions.
IPA_OVERRIDES = {
    # Prepositions in their weak (reduced-schwa) forms — the citation
    # forms from CMUdict are wrong in connected speech for these.
    "to":     "tə",
    "of":     "əv",
    "at":     "ət",
    "for":    "fər",
    "from":   "frəm",
    "and":    "ənd",
    "than":   "ðən",
    "as":     "əz",
    # BrE spellings
    "colour":   "ˈkʌlər",
    "colours":  "ˈkʌlərz",
    "centre":   "ˈsɛntər",
    "theatre":  "ˈθiətər",
    "organised": "ˈɔrgəˌnaɪzd",
    "organising": "ˈɔrgəˌnaɪzɪŋ",
    "favourite": "ˈfeɪvərɪt",
    # Common nouns missing from CMUdict
    "motorway":  "ˈmoʊtərˌweɪ",
    "takeaway":  "ˈteɪkəˌweɪ",
    "underground": "ˈʌndərˌgraʊnd",
    "skyscraper": "ˈskaɪˌskreɪpər",
    # Time / clock
    "o'clock":   "əˈklɑk",
    "oclock":    "əˈklɑk",
    "8pm":       "eɪt pi ɛm",
    "2pm":       "tu pi ɛm",
    # Symbols
    "→":         "tu",
    # Citation-form corrections
    "get":       "gɛt",
    "gets":      "gɛts",
    "just":      "dʒʌst",
    "poor":      "pʊr",
}


def _hash(text: str) -> str:
    return hashlib.sha1(text.strip().encode("utf-8")).hexdigest()[:12]


def load_tsv(path: Path):
    if not path.exists():
        return
    data_lines = [ln for ln in path.read_text(encoding="utf-8").splitlines()
                  if ln and not ln.startswith("#")]
    for row in _csv.reader(data_lines, delimiter="\t", quotechar='"'):
        yield row


def strip_cloze(text: str) -> str:
    return CLOZE_RE.sub(r"\1", text)


def collect_sentences():
    """Collect unique sentences from all 5 staging files."""
    sentences: set[str] = set()
    # (path, field-index-of-sentence)
    sources = [
        (Path("prepositions_recognition.txt"), 0),
        (Path("prepositions_contrast.txt"),    0),
        (Path("prepositions_production.txt"),  3),  # Sample
        (Path("prepositions_listening.txt"),   3),  # Transcript
    ]
    for p, idx in sources:
        for row in load_tsv(p):
            if len(row) > idx and row[idx].strip():
                sentences.add(row[idx].strip())
    # Cloze: strip {{c1::form}} markers first
    for row in load_tsv(Path("prepositions_cloze.txt")):
        if row and row[0].strip():
            sentences.add(strip_cloze(row[0].strip()))
    # Contrast: also fill `___` blank with the answer for IPA generation
    for row in load_tsv(Path("prepositions_contrast.txt")):
        if len(row) >= 4 and "___" in row[0]:
            sentences.add(row[0].replace("___", row[3]).strip())
    return sorted(sentences)


def _apply_overrides_to_ipa_string(ipa_str: str, original_text: str) -> str:
    if "*" not in ipa_str:
        return ipa_str
    src_tokens = PUNCT_RE.sub("", original_text).split()
    out_tokens = ipa_str.split()
    if len(src_tokens) != len(out_tokens):
        fixed = []
        for tok in out_tokens:
            if tok.endswith("*"):
                key = tok[:-1].lower()
                fixed.append(IPA_OVERRIDES.get(key, tok))
            else:
                fixed.append(tok)
        return " ".join(fixed)
    fixed = []
    for src, tok in zip(src_tokens, out_tokens):
        if tok.endswith("*"):
            key = src.lower()
            fixed.append(IPA_OVERRIDES.get(key, tok))
        else:
            fixed.append(tok)
    return " ".join(fixed)


def _clean_for_ipa(text: str) -> str:
    return re.sub(r"\s+", " ", PUNCT_RE.sub(" ", text)).strip()


def sentence_to_ipa(text: str) -> str:
    import eng_to_ipa as ipa  # type: ignore
    cleaned = _clean_for_ipa(text)
    raw = ipa.convert(cleaned).strip()
    return _apply_overrides_to_ipa_string(raw, cleaned)


def collect_words(sentences):
    words: set[str] = set()
    for s in sentences:
        for w in _clean_for_ipa(s).split():
            w = w.strip().lower()
            if w:
                words.add(w)
    return sorted(words)


def main():
    ap = argparse.ArgumentParser(description="Tier-2 IPA builder")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    MEDIA_DIR.mkdir(parents=True, exist_ok=True)

    sentences = collect_sentences()
    if args.limit:
        sentences = sentences[:args.limit]

    print(f"Corpus: {len(sentences)} unique sentences. Computing IPA…")
    index: dict[str, str] = {}
    written = skipped = 0
    for i, text in enumerate(sentences, 1):
        h = _hash(text)
        out = MEDIA_DIR / f"{h}.txt"
        if out.exists() and not args.force:
            ipa_str = out.read_text(encoding="utf-8").strip()
            skipped += 1
        else:
            ipa_str = sentence_to_ipa(text)
            out.write_text(ipa_str + "\n", encoding="utf-8")
            written += 1
        index[h] = ipa_str
        if i % 200 == 0 or i == len(sentences):
            print(f"  [{i}/{len(sentences)}] written={written} skipped={skipped}")

    INDEX_JSON.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    print("Building per-word audit dictionary…")
    import eng_to_ipa as ipa  # type: ignore
    words = collect_words(sentences)

    def _word_ipa(w: str) -> str:
        if w in IPA_OVERRIDES:
            return IPA_OVERRIDES[w]
        v = ipa.convert(w)
        if v.endswith("*") and w in IPA_OVERRIDES:
            return IPA_OVERRIDES[w]
        return v

    word_index = {w: _word_ipa(w) for w in words}
    WORDS_JSON.write_text(json.dumps(word_index, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")

    print(f"\n✓ Done.  IPA files written: {written};  skipped: {skipped}.")
    print(f"  Per-sentence index: {INDEX_JSON}")
    print(f"  Per-word audit:     {WORDS_JSON}  ({len(words)} unique words)")
    oov = sum(1 for v in word_index.values() if "*" in v)
    print(f"  Out-of-dictionary words (kept with '*'): {oov}/{len(words)} "
          f"({100.0 * oov / max(1, len(words)):.1f}%)")


if __name__ == "__main__":
    main()
