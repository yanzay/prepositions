# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Project scaffolding mirroring the sister `../verbs` deck.
- Five staging files with header schemas (Recognition, Contrast, Production,
  Cloze, Listening).
- Stub build / validation / media scripts.
- Governance docs: LICENSE (CC-BY-SA-4.0), CONTRIBUTING.md, this CHANGELOG.

### Changed (v2 audit-driven revisions, 2026-05-15)
- **Algorithm**: SM-2 → FSRS-5 (Anki 24.04+) with desired retention 0.85.
- **Card types**: 4 → 5 (added **Listening** for transfer-appropriate
  processing — Morris et al. 1977; Roediger & Tekin 2017).
- **Modules**: 10 → 12 (added **Polysemy Networks** and **Zero Preposition
  & Ellipsis**).
- **Card-count target**: ~1,300 → ~1,460 with rebalanced R/C/P/Cl/L mix
  (Production rises 16 % → 17 %, Contrast concentrated on confusable pairs,
  Listening adds 12 %).
- **Recognition schema**: 9 fields → 13 fields, adding `Trajector`,
  `Landmark`, `FrameOfRef`, `ImageSchema` per Tyler & Evans (2003) and
  Langacker (2008).
- **Tag axes**: 6 → 8 required (adds `image-schema:*` and `generalisable:*`).
- **Card UX**: Recognition back uses three-tier progressive reveal;
  Contrast / Production "Why?" gated behind tap (generation effect,
  Slamecka & Graf 1978).
- **Audio policy**: moved to back of all card types except Listening to
  prevent split attention (Mayer 2019).
- **TTS engine**: standardised on Google Cloud Text-to-Speech (Neural2 voices, e.g. `en-US-Neural2-F`) — same provider as the sister verbs project, free tier covers the corpus.

### Planned
- Phase A MVP: Modules 01 + 03 Recognition + Listening (~250 cards).
- Phase B Core: Modules 01–04 with all card types (~600 cards).
- Phase C Collocations: Modules 05–07 (~975 cards).
- Phase D Polish: Modules 08–12 (~1,460 cards) + 200 picture-cue photos.
- Phase E Distribution: AnkiHub + GitHub Release v1.0.

[Unreleased]: https://github.com/EXAMPLE/english-prepositions-anki/compare/HEAD
