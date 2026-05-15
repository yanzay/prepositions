#!/usr/bin/env python3
"""Tier-2 audio rendering for the English Prepositions Anki package.

Generates one MP3 per unique sentence pulled from the five staging files,
using Google Cloud Text-to-Speech (Neural2 voices). Idempotent: a sentence
already present (and unchanged) in the manifest is skipped on subsequent
runs. The MP3 filename is the first 12 hex chars of sha1(sentence) so the
same sentence shared across cards or staging files is rendered exactly once.

Backend: Google Cloud Text-to-Speech (Neural2 voices).
Auth:    GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json
         (see https://cloud.google.com/text-to-speech/docs/before-you-begin)
Cost:    First 1,000,000 characters per month are free for Neural2 voices.
         The full 1,407-card deck has ~1,336 unique sentences × ~80 chars
         ≈ 107,000 chars — well within the free tier.

Usage:
    python3 build_audio.py                # render everything that's missing
    python3 build_audio.py --dry-run      # report what would change, render nothing
    python3 build_audio.py --voice en-GB-Neural2-B  # choose another voice
    python3 build_audio.py --rate 0.95    # slightly slower
    python3 build_audio.py --limit 10     # smoke-test first 10 sentences
    python3 build_audio.py --prune        # also delete MP3s no longer referenced
    python3 build_audio.py --rehash       # recompute sha256 fingerprints

Environment overrides (alternative to flags):
    PREP_TTS_VOICE  default 'en-US-Neural2-F'  (warm female, natural)
    PREP_TTS_LANG   default 'en-US'
    PREP_TTS_RATE   default '1.00'

Output:
    media/audio/<hash>.mp3            (one file per unique sentence)
    media/audio_manifest.json         (hash → metadata, including sha256 +
                                       voice + lang + rate, used to skip
                                       work and detect drift on re-runs)
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List

# ── Tunables (env or CLI) ────────────────────────────────────────────────
DEFAULT_VOICE = os.environ.get("PREP_TTS_VOICE", "en-US-Neural2-F")  # warm female
DEFAULT_LANG  = os.environ.get("PREP_TTS_LANG",  "en-US")
DEFAULT_RATE  = float(os.environ.get("PREP_TTS_RATE", "1.00"))

# ── Paths ────────────────────────────────────────────────────────────────
ROOT          = Path(__file__).resolve().parent
MEDIA_DIR     = ROOT / "media"
AUDIO_DIR     = MEDIA_DIR / "audio"
AUDIO_INDEX   = MEDIA_DIR / "audio_manifest.json"

STAGING_FILES = [
    "prepositions_recognition.txt",
    "prepositions_contrast.txt",
    "prepositions_production.txt",
    "prepositions_cloze.txt",
    "prepositions_listening.txt",
]

DRY_RUN = False  # set by --dry-run
THROTTLE_S = 0.05  # gentle pacing between TTS calls (50 ms)


# ── Google Cloud TTS client ──────────────────────────────────────────────
_CLIENT = None

def _client():
    """Lazy-init Google Cloud TextToSpeechClient."""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    try:
        from google.cloud import texttospeech as tts  # type: ignore
    except ImportError:
        raise SystemExit(
            "google-cloud-texttospeech is not installed.\n"
            "  pip install google-cloud-texttospeech\n"
            "and set GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account.json"
        )
    if not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        sys.stderr.write(
            "WARN: GOOGLE_APPLICATION_CREDENTIALS is not set; the client may fail.\n"
        )
    _CLIENT = tts.TextToSpeechClient()
    return _CLIENT


def _audio_encoding():
    from google.cloud import texttospeech as tts  # type: ignore
    return tts.AudioEncoding.MP3


# ── Hashing ──────────────────────────────────────────────────────────────
def text_hash(text: str) -> str:
    """First 12 hex chars of sha1(canonical text). Stable across runs."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Synthesis ────────────────────────────────────────────────────────────
def synth_mp3(text: str, out_path: Path, *, rate: float, voice_name: str,
              lang: str) -> None:
    """Synthesise *text* to *out_path* via Google Cloud TTS."""
    if DRY_RUN:
        out_path.touch()
        return

    from google.cloud import texttospeech as tts  # type: ignore

    # Use SSML with a <speak><prosody rate=...>...</prosody></speak> wrapper so
    # we can apply per-call rate without changing the voice. Escape minimal XML.
    safe = (text.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))
    ssml = f'<speak><prosody rate="{rate:.2f}">{safe}</prosody></speak>'

    synthesis_input = tts.SynthesisInput(ssml=ssml)
    voice = tts.VoiceSelectionParams(language_code=lang, name=voice_name)
    audio_cfg = tts.AudioConfig(
        audio_encoding=_audio_encoding(),
        sample_rate_hertz=24000,
        # speaking_rate is also applied by SSML; leave at 1.0 here so the
        # SSML wins. Using both can over-compress in edge cases.
        speaking_rate=1.0,
    )

    response = _client().synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_cfg
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.audio_content)


# ── Sentence collection ──────────────────────────────────────────────────
def load_tsv(path: Path):
    """Yield non-comment, non-empty rows as lists of strings."""
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            yield line.split("\t")


_CLOZE_RE = re.compile(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}")


def _strip_cloze(text: str) -> str:
    """Replace {{c1::word}} with word so the cloze sentence is utterable."""
    return _CLOZE_RE.sub(lambda m: m.group(1), text).strip()


def _fill_blank(sentence: str, answer: str) -> str:
    """Replace one or more `___` placeholders with the answer."""
    return re.sub(r"_{3,}", answer, sentence).strip()


def collect_sentences() -> List[str]:
    """Return unique, ordered list of sentences across all staging files.

    For each card type the audible sentence is:
        Recognition  → field 0 (Sentence) with <b>...</b> markup stripped
        Contrast     → field 0 (Sentence) with `___` filled by Answer (field 3)
        Production   → field 3 (Sample) — the model answer
        Cloze        → field 0 with {{c1::x}} unwrapped
        Listening    → field 3 (Transcript) — the spoken cue itself
    """
    seen: Dict[str, None] = {}

    def add(text: str):
        text = re.sub(r"</?[a-z]+[^>]*>", "", text).strip()  # strip HTML tags
        text = re.sub(r"\s+", " ", text)
        if text and text not in seen:
            seen[text] = None

    for fname in STAGING_FILES:
        path = ROOT / fname
        if "recognition" in fname or "cloze" in fname:
            for row in load_tsv(path):
                if not row:
                    continue
                txt = _strip_cloze(row[0]) if "cloze" in fname else row[0]
                add(txt)
        elif "contrast" in fname:
            for row in load_tsv(path):
                if len(row) < 4:
                    continue
                add(_fill_blank(row[0], row[3]))
        elif "production" in fname:
            for row in load_tsv(path):
                if len(row) < 4:
                    continue
                add(row[3])  # Sample (model answer)
        elif "listening" in fname:
            for row in load_tsv(path):
                if len(row) < 4:
                    continue
                add(row[3])  # Transcript

    return list(seen.keys())


# ── Manifest ─────────────────────────────────────────────────────────────
def load_manifest() -> dict:
    if AUDIO_INDEX.exists():
        return json.loads(AUDIO_INDEX.read_text(encoding="utf-8"))
    return {}


def save_manifest(manifest: dict) -> None:
    if DRY_RUN:
        return
    AUDIO_INDEX.parent.mkdir(parents=True, exist_ok=True)
    AUDIO_INDEX.write_text(
        json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def manifest_entry(text: str, *, voice: str, rate: float, lang: str,
                   file_path: Path) -> dict:
    return {
        "text":       text,
        "voice":      voice,
        "lang":       lang,
        "rate":       rate,
        "file":       file_path.name,
        "sha256":     file_sha256(file_path) if file_path.exists() else "",
        "size":       file_path.stat().st_size if file_path.exists() else 0,
        "normalized": False,
    }


def entry_matches(entry: dict, *, text: str, voice: str, rate: float,
                  lang: str, file_path: Path, rehash: bool) -> bool:
    if not entry:
        return False
    if entry.get("text") != text:
        return False
    if entry.get("voice") != voice:
        return False
    if entry.get("lang") != lang:
        return False
    if abs(float(entry.get("rate", 1.0)) - rate) > 1e-6:
        return False
    if not file_path.exists():
        return False
    if rehash and entry.get("sha256") != file_sha256(file_path):
        return False
    return True


# ── Driver ───────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(
        description="Tier-2 audio builder (Google Cloud TTS, idempotent + incremental)"
    )
    ap.add_argument("--voice", default=DEFAULT_VOICE,
                    help=f"Google Neural2 voice name (default: {DEFAULT_VOICE})")
    ap.add_argument("--lang",  default=DEFAULT_LANG,
                    help=f"BCP-47 language code (default: {DEFAULT_LANG})")
    ap.add_argument("--rate",  type=float, default=DEFAULT_RATE,
                    help=f"Speaking rate multiplier (default: {DEFAULT_RATE})")
    ap.add_argument("--limit", type=int, default=0,
                    help="Render only first N missing/changed sentences (smoke test)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Don't call TTS or write manifest; report planned actions")
    ap.add_argument("--prune", action="store_true",
                    help="Delete MP3s and manifest entries no longer referenced")
    ap.add_argument("--rehash", action="store_true",
                    help="Recompute file sha256 in manifest (slow, idempotency check)")
    args = ap.parse_args()

    if args.dry_run:
        global DRY_RUN
        DRY_RUN = True

    sentences = collect_sentences()
    print(f"Unique sentences across staging: {len(sentences)}")

    total_chars = sum(len(s) for s in sentences)
    print(f"Total characters: {total_chars:,}  (Google free tier: 1,000,000/month)")

    manifest = load_manifest()
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    referenced_hashes = set()
    written = up_to_date = 0
    reasons: Dict[str, int] = {}
    rendered = 0

    for sent in sentences:
        h = text_hash(sent)
        referenced_hashes.add(h)
        out = AUDIO_DIR / f"{h}.mp3"
        entry = manifest.get(h)

        if entry_matches(entry, text=sent, voice=args.voice, rate=args.rate,
                         lang=args.lang, file_path=out, rehash=args.rehash):
            up_to_date += 1
            continue

        # Decide why we're (re-)rendering — useful in dry-run reports
        if not entry:
            reasons["new-sentence"] = reasons.get("new-sentence", 0) + 1
        elif not out.exists():
            reasons["missing-file"] = reasons.get("missing-file", 0) + 1
        elif entry.get("voice") != args.voice:
            reasons["voice-changed"] = reasons.get("voice-changed", 0) + 1
        elif entry.get("rate") != args.rate:
            reasons["rate-changed"] = reasons.get("rate-changed", 0) + 1
        elif args.rehash and entry.get("sha256") != file_sha256(out):
            reasons["sha256-mismatch"] = reasons.get("sha256-mismatch", 0) + 1
        else:
            reasons["other"] = reasons.get("other", 0) + 1

        if args.limit and rendered >= args.limit:
            continue

        if DRY_RUN:
            written += 1
            rendered += 1
            continue

        try:
            synth_mp3(sent, out, rate=args.rate, voice_name=args.voice,
                      lang=args.lang)
        except Exception as e:
            sys.stderr.write(f"FAIL {h} '{sent[:60]}…': {e}\n")
            continue

        manifest[h] = manifest_entry(sent, voice=args.voice, rate=args.rate,
                                     lang=args.lang, file_path=out)
        written += 1
        rendered += 1

        if rendered % 25 == 0:
            print(f"  …rendered {rendered}")
            save_manifest(manifest)

        time.sleep(THROTTLE_S)

    # Pruning pass
    pruned = 0
    if args.prune:
        for h in list(manifest.keys()):
            if h not in referenced_hashes:
                f = AUDIO_DIR / manifest[h].get("file", f"{h}.mp3")
                if f.exists() and not DRY_RUN:
                    f.unlink()
                if not DRY_RUN:
                    del manifest[h]
                pruned += 1

    save_manifest(manifest)

    print()
    print(f"✓ Done. written={written}  up-to-date={up_to_date}  pruned={pruned}")
    if reasons:
        print("  re-render reasons: " +
              "  ".join(f"{k}={v}" for k, v in sorted(reasons.items())))
    print(f"  Manifest: {AUDIO_INDEX.relative_to(ROOT)}")
    print(f"  Output dir: {AUDIO_DIR.relative_to(ROOT)}/")


if __name__ == "__main__":
    sys.exit(main())
