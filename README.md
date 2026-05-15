# English Prepositions Anki Package

A premium-grade English-prepositions Anki study package covering spatial,
temporal, movement, dependent, phrasal, and idiomatic uses, plus a
**Polysemy Networks** module, a **Zero-Preposition** module, and L1
interference for the six most common learner backgrounds.

Modeled on the sister project [`../verbs`](../verbs) — same field schemas,
same build pipeline, same Tier-1 / Tier-2 / Tier-3 layering — but rebuilt
against three independent audits (SLA pedagogy, cognitive science,
premium-deck parity). See **`CONTENT_PLAN.md` § 0** for the principles and
**§ 12** for the audit trail.

## What is included

| File | Purpose |
|------|---------|
| `prepositions_recognition.txt` | Recognition notes — 12 fields per row (adds Trajector / Landmark / FrameOfRef / ImageSchema) |
| `prepositions_contrast.txt` | Contrast notes — 7 fields per row |
| `prepositions_production.txt` | Production notes — 6 fields per row |
| `prepositions_cloze.txt` | Cloze deletion notes (3 fields) |
| `prepositions_listening.txt` | **NEW** — Audio-discrimination notes (5 fields) |
| `apply_taxonomy_tags.py` | Auto-injects `module:* / type:* / sense:* / frequency:* / register:* / cefr:* / image-schema:* / generalisable:*` tags |
| `anki_premium_schema_package.txt` | Schema and study-strategy reference |
| `build_anki_package.py` | Builds the `.apkg` package from the source files (Tier 1 + Tier 2 media) |
| `build_audio.py` | **Tier 2a** — generates one MP3 per unique sentence via Google Cloud Text-to-Speech (Neural2 voices) |
| `normalize_audio.py` | **Tier 2a** — EBU R128 loudness-normalises every MP3 to a uniform -16 LUFS / -1.5 dB true-peak via `ffmpeg loudnorm` |
| `build_ipa.py` | **Tier 2b** — generates broad GA IPA transcriptions per sentence |
| `build_diagrams.py` | **Tier 2c** — generates 31 SVG image-schema diagrams per canonical preposition |
| `build_images.py` | **Tier 2d** — fetches CC-licensed photographs from Wikimedia Commons for rows tagged `picture-cue:yes` (Picsum fallback) |
| `build_pictures.py` | **Tier 2d** — manifest validator for hand-curated picture-cue images (CC0 / Pexels / Pixabay / Unsplash) |
| `validate_anki_data.py` | Validates field structure, labels, tag axes, answer integrity |
| `requirements.txt` | Pinned Python dependencies |
| `ANKI_SETTINGS.md` | Recommended Anki deck options (FSRS-5) and study path |
| `CONTENT_PLAN.md` | Module-by-module content plan with card targets and audit trail |
| `LICENSE` | CC-BY-SA-4.0 |
| `CHANGELOG.md` | Keep-a-Changelog format |
| `CONTRIBUTING.md` | How to file issues, propose new sentences, run validators |
| `media/audio/` | Generated MP3s (one per unique sentence, hashed filename) |
| `media/audio_manifest.json` | Hash → audio-metadata lookup with sha256 + `normalized:true` flag |
| `media/diagrams/` | Generated SVG image-schema diagrams (31 files) |
| `media/diagrams_index.json` | Label → diagram-file lookup |
| `media/images/` | Wikimedia Commons photos (auto-fetched by `build_images.py`) |
| `media/images_index.json` | Hash → image-metadata lookup with attribution + license |
| `media/pictures/` | Hand-curated picture-cue images (manifest validated by `build_pictures.py`) |
| `media/ipa_index.json` | Hash → IPA lookup used by the build script |

## Deck structure (v2 — 12 modules, 5 card types, ~1,460 cards)

```
English Prepositions
├── 01 - Spatial Core (in / on / at)              (170)
├── 02 - Spatial Extended                          (150)
├── 03 - Time Prepositions                         (170)
├── 04 - Movement & Direction                      (130)
├── 05 - Dependent — Verb + Prep                   (185)
├── 06 - Dependent — Adjective + Prep              (110)
├── 07 - Dependent — Noun + Prep                   ( 80)
├── 08 - Phrasal & Multi-word Prepositions         (100)
├── 09 - Abstract & Idiomatic Uses                 (125)
├── 10 - L1 Interference (6 langs × top-5 errors)  ( 95)
├── 11 - Polysemy Networks                         ( 80)
└── 12 - Zero Preposition & Ellipsis               ( 65)
```

Each module has five card-type subdecks ordered by pedagogical acquisition
sequence (Anki sorts them alphabetically and the numeric prefix is what gets
us the correct order):

```
01 - Spatial Core
├── 1 - Recognition   passive cued recall
├── 2 - Contrast      discrimination between confusable forms
├── 3 - Cloze         scaffolded production in context
├── 4 - Production    full constrained narrative writing
└── 5 - Listening     auditory transfer-appropriate processing
```

See `CONTENT_PLAN.md` § 4 for per-module R/C/P/Cl/L counts.

## Card UX (cognitive-load disciplined)

- **Recognition back uses three-tier progressive reveal** — Tier A (Label +
  audio + IPA) shown by default, Tier B (context fields) and Tier C (full
  reference + image-schema diagram) revealed by tap. No 9-field flat dumps.
- **Contrast and Production "Why?" fields are gated** behind a tap, forcing
  the learner to generate their own explanation first (Slamecka-Graf
  generation effect).
- **Audio is on the back** of every card type **except Listening** (where
  audio is the cue and lives on the front).
- Light / dark / sepia themes via `prefers-color-scheme`; mobile-first
  typography (18 px base, 36 em max width).

## Tier 2 — multimodal layer

### 🔊 Audio
- **Google Cloud Text-to-Speech** Neural2 voices (`en-US-Neural2-F` warm female default; switch via `PREP_TTS_VOICE`). First 1M chars/month free; full 1,407-card corpus is ~62k chars.
- One MP3 per unique sentence, content-addressed (`<sha1[:12]>.mp3`).
- Optional native-actor recordings post-v1.0 for the top-200 highest-frequency sentences.

### 🔤 IPA transcription
- Every sentence has a broad General-American IPA transcription on the back.
- Computed offline with `eng-to-ipa`. UTF-8 NFC-normalised.

### 🗺️ Image-schema SVG diagrams
- One SVG per preposition (or contrast pair) showing the trajector / landmark
  / image-schema relationship (CONTAINER, SUPPORT, POINT, PATH, OVER, …).
- Cards whose canonical Label/Answer matches a known preposition get a
  diagram; the rest fall back to text only.

### 📷 Picture-cue images
- ~200 photographic stimuli for the spatial core (Modules 01, 02) and
  abstract/idiomatic core (Module 09). Sourced CC0 from Pexels / Pixabay /
  Unsplash, manually curated.

## Quality assurance — two-tier checks

The deck has **two complementary check scripts** that together encode the
findings of the original 4-auditor review pass:

| Script | What it checks | Severity | When |
|---|---|---|---|
| `validate_anki_data.py` | **Structural**: column counts, required tag axes, answer integrity, AudioRef format, duplicate detection | Errors block build | every commit (CI) |
| `lint_anki_data.py`     | **Quality**: 13 deterministic rules — module↔sense / image-schema↔preposition / CEFR-band sanity / dependent-subtag / field↔tag agreement / placeholder trajector-landmark / Module 12 self-contradiction / listening-transcript-not-metadata / no-translate-from-LX-prompts / animacy match / dialect mixing / cloze-hint-leak / Module 10 l1-tag / cross-file duplicates | Errors block build; warnings reported | every commit (CI) |

```bash
python3 validate_anki_data.py   # exit 1 on any structural error
python3 lint_anki_data.py       # exit 1 on ERROR; --strict to also fail on WARN/INFO
python3 lint_anki_data.py --rule <rule>   # filter to one rule
python3 lint_anki_data.py --json          # machine-readable output
```

**Current baseline (1,044-card deck): 0 ERRORs, 23 WARNs, 79 INFOs.**
The 79 INFOs are intentional Recognition⇔Cloze sentence reuse for shared
audio. The 23 WARNs are flagged for periodic human polish but do not block
shipping. Things the lint deliberately does NOT check (because they require
judgment) are listed in `CONTRIBUTING.md` § "Manual review checklist".

---

## How to build and import

### Minimal build (no media)
```bash
python3 -m pip install -r requirements.txt
python3 validate_anki_data.py            # structural integrity
python3 lint_anki_data.py                # quality lints
python3 build_anki_package.py --no-media # writes english_prepositions_anki.apkg
```

### Full build (with multimodal media)
```bash
# 1. Free / instant — no API keys needed
python3 build_diagrams.py                # 31 SVG image-schema diagrams (~instant)
python3 build_ipa.py                     # broad GA IPA per sentence (~30 s)
python3 build_images.py                  # Wikimedia Commons fetch (throttled, free)

# 2. Audio — needs Google Cloud TTS credentials
python3 build_audio.py --dry-run         # preview cost; counts unique sentences
export GOOGLE_APPLICATION_CREDENTIALS=.secrets/gcp-adc.json
python3 build_audio.py                   # ~1.4k MP3s; first 1M chars/month free on GCP
python3 normalize_audio.py               # EBU R128 loudness pass (needs ffmpeg)

# 3. Final assembly
python3 build_anki_package.py            # bundles all media into the .apkg
```

Open Anki → File → Import. The `.apkg` contains all referenced media inline.

### Switching voices
```bash
PREP_TTS_VOICE=en-GB-Neural2-B python3 build_audio.py  # British male
PREP_TTS_VOICE=en-US-Neural2-D python3 build_audio.py  # US male
PREP_TTS_VOICE=en-US-Neural2-F python3 build_audio.py  # US female (default)
```

## Field schemas (revised v2)

### Recognition (`prepositions_recognition.txt`)
| Field | Purpose |
|-------|---------|
| `Sentence` | Example sentence with the target preposition in bold |
| `Label` | Canonical preposition or sense label e.g. *at (point in space)* |
| `Sense` | spatial / temporal / movement / dependent / idiomatic / polysemy / zero |
| `Pattern` | Structural pattern e.g. *be + at + place noun* |
| `Trajector` | Figure: the moving / located entity |
| `Landmark` | Ground: the reference object / region |
| `FrameOfRef` | relative / intrinsic / absolute / N-A |
| `ImageSchema` | container / support / point / path / over / under / between / cluster / none |
| `MainUse` | Primary communicative function |
| `QuickCue` | Signal words or features in the sentence |
| `Contrast` | What this is often confused with and why it isn't that |
| `WhenNotToUse` | Common pitfalls |
| `Tags` | Space-separated tag string |

### Contrast (`prepositions_contrast.txt`)
| Field | Purpose |
|-------|---------|
| `Sentence` | Sentence with `___` where the preposition belongs |
| `OptionA` | First preposition option |
| `OptionB` | Second preposition option |
| `Answer` | Correct preposition (must match OptionA or OptionB) |
| `Why` | Explanation (gated behind a tap on the card) |
| `Tip` | Study tip or memory rule |
| `Tags` | Space-separated tag string |

### Production (`prepositions_production.txt`)
| Field | Purpose |
|-------|---------|
| `Prompt` | Multi-sentence narrative writing prompt |
| `Target` | Target preposition or pattern (e.g. *on / on top of*) |
| `Sense` | Semantic role of the target |
| `Sample` | A strong sample answer |
| `Why` | Why the sample answer demonstrates the target preposition (gated tap) |
| `Tags` | Space-separated tag string |

### Cloze (`prepositions_cloze.txt`)
| Field | Purpose |
|-------|---------|
| `Text` | Sentence with `{{c1::preposition}}` cloze deletion |
| `Hint` | Optional sense hint shown on the front |
| `Tags` | Space-separated tag string |

### Listening (`prepositions_listening.txt`) — NEW
| Field | Purpose |
|-------|---------|
| `AudioRef` | `[sound:<sha1[:12]>.mp3]` — cue lives on the front |
| `Question` | e.g. "Was the key inside or on top of the table?" |
| `Answer` | The correct preposition (or sense) |
| `Transcript` | Sentence as spoken (revealed on back) |
| `Tags` | Space-separated tag string |

## Tag axes (8 required, plus optional)

`module:* / type:* / sense:* / frequency:* / register:* / cefr:* / image-schema:* / generalisable:*`

Optional: `variant:brE|amE`, `l1:<lang>`, `domain:*`, `mnemonic:yes`, `picture-cue:yes`, `contrast:<pair>`.

## Spaced repetition algorithm

The deck is engineered for **FSRS-5** (default in Anki 24.04+) with desired
retention 0.85. SM-2 fallback settings are documented in
`ANKI_SETTINGS.md` for users on Anki ≤ 23.10.

## Distribution

- GitHub Releases: signed `.apkg` per SemVer tag (`v1.0.0`, `v1.1.0`, …)
- AnkiHub: collaborative deck listing (post-v1.0) for continuous community updates
- AnkiWeb: shared-deck mirror for casual users

## Notes

- The build script auto-installs `genanki` if it is missing.
- All rows must pass `validate_anki_data.py` before each build (tag-axis lint
  included).
- See **`CONTENT_PLAN.md`** for the per-module content plan, audit trail,
  and the six pedagogical principles the deck is engineered against.
- See **`ANKI_SETTINGS.md`** for full FSRS-aware deck options.
- See **`CHANGELOG.md`** for release history.
