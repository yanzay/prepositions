# Contributing

Thanks for considering a contribution! This deck is community-curated and
welcomes new sentences, error reports, additional L1-interference data, and
corrections.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 validate_anki_data.py
```

`validate_anki_data.py` AND `lint_anki_data.py` must pass before any PR is
reviewed (CI runs both automatically).

## Two-tier check pipeline

| Script | Purpose | Severity |
|---|---|---|
| `validate_anki_data.py` | Structural integrity (column counts, required tags, AudioRef format, duplicates) | Errors block CI |
| `lint_anki_data.py`     | Quality lints distilled from the original 4-auditor review pass — 13 deterministic rules | Errors block CI; warnings reported |

Run them locally before pushing:

```bash
python3 validate_anki_data.py
python3 lint_anki_data.py
```

If you intentionally introduce a row that triggers a lint warning, document
the rationale in the PR description so reviewers don't bounce it back.

## What the lint checks (and what it doesn't)

**Lint covers (deterministic):**
- module ↔ sense consistency · image-schema ↔ preposition · CEFR-band sanity
- dependent-subtag presence in modules 05/06/07 · field ↔ tag agreement
- placeholder Trajector/Landmark · Module 12 self-contradiction
- Listening transcript is real English not metadata · no Translate-from-LX prompts
- animacy match for animate-only idioms · BrE/AmE dialect mixing
- cloze hint leaks the answer · Module 10 missing l1: tag
- cross-file Recognition⇔Cloze duplicates (info-only)

**Manual review checklist (lint cannot judge these):**
- [ ] **Sentence naturalness** — does it sound like something a native
      speaker would actually say? Stilted, translated-sounding, or LLM-flat
      sentences should be rewritten.
- [ ] **L1-trap linguistic reality** — is the claimed interference attested
      in CLC / EFCAMDAT, or is it folk-grammar? Cite the source.
- [ ] **Why-field pedagogical depth** — does the explanation actually teach
      the cognitive-linguistic distinction, or is it generic ("because
      that's the rule")?
- [ ] **Production-prompt memorability** — is the prompt anchored in a
      concrete scenario the learner would encounter, or is it generic
      ("describe your daily routine")?
- [ ] **Sample-answer voice** — does it sound like a real person speaking,
      or LLM-template exposition?
- [ ] **Trajector / Landmark plausibility** — for spatial Recognition rows,
      are these the actual noun phrases from the sentence, not abstract
      placeholders like "subject" or "condition"?
- [ ] **Register accuracy** — does a row tagged `register:formal` actually
      sound formal, and `register:informal` actually informal?

## What we welcome

- 🟢 **New sentences** for under-populated cells in `CONTENT_PLAN.md` § 4.
  Open an issue first if a module is already at its target count.
- 🟢 **L1-interference rows** sourced from a published learner-corpus
  reference (CLC, EFCAMDAT, ICLE, …). Cite the source in the PR body.
- 🟢 **Picture-cue images** (CC0 / Pexels / Pixabay / Unsplash only).
  Add a credit line to `media/pictures/CREDITS.txt`.
- 🟢 **Bug fixes** in build scripts, validators, templates.
- 🟢 **Translations** of the README into the six target L1s.

## What we ask you to avoid

- 🔴 Hand-written sentences that aren't grounded in a corpus or canonical
  reference grammar — this is a *premium-grade* deck, not a sentence-soup.
- 🔴 Adding new tag axes without updating the validator and CONTENT_PLAN § 6.
- 🔴 Adding cards that violate the **6 pedagogical principles** in
  CONTENT_PLAN § 0.
- 🔴 Changing the FSRS / card-UX defaults without referencing evidence in
  the PR description.

## Pull-request checklist

- [ ] `python3 validate_anki_data.py` passes locally.
- [ ] New rows have all 8 required tag axes.
- [ ] Spatial Recognition rows populate `Trajector`, `Landmark`, `ImageSchema`.
- [ ] L1-interference rows cite a corpus source.
- [ ] CHANGELOG.md updated under `[Unreleased]`.
- [ ] No duplicate Sentence / Prompt / Text / AudioRef.

## Style guide

- **Sentences**: prefer COCA / BNC-attested wording; aim for naturalness
  over cleverness.
- **Length**: keep example sentences ≤ 18 words for screen real-estate.
- **Register tag**: be explicit — `register:informal` vs `register:formal`.
- **Image schema**: when in doubt, consult Tyler & Evans (2003) ch. 4.

## Code of conduct

This project follows the [Contributor Covenant 2.1](https://www.contributor-covenant.org/version/2/1/code_of_conduct/).
Unkind PRs and issues will be closed without comment.

## Maintainer cadence

- PRs reviewed within 2 weeks.
- Quarterly minor releases (vX.Y.0) with batched accepted PRs.
- Patch releases (vX.Y.Z) for build-pipeline bugs only.
