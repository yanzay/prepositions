# Recommended Anki Settings (v2, FSRS-first)

After importing `english_prepositions_anki.apkg`, apply these deck option
presets. The deck is organised into **12 modules** with **5 card types**
(Recognition / Contrast / Production / Cloze / Listening). Apply settings
per module, or create one shared preset and adjust new-cards-per-day per
module.

> **v2 change:** This release recommends **FSRS-5** (default in Anki 24.04+)
> instead of the legacy SM-2 algorithm. FSRS adapts intervals from your own
> review history and reaches the same retention with fewer reviews. SM-2
> instructions are preserved at the bottom for users on Anki ≤ 23.10.

---

## Subdeck ordering convention

Each module has five card-type subdecks named with a numeric prefix so Anki
sorts them in **pedagogical acquisition order** (alphabetical = correct):

```
01 - Spatial Core
├── 1 - Recognition   ← start here (passive cued recall)
├── 2 - Contrast      ← then discriminate confusable forms
├── 3 - Cloze         ← scaffolded production in context
├── 4 - Production    ← full constrained writing
└── 5 - Listening     ← auditory transfer-appropriate processing
```

This matches the Stage 1–5 study path below; never rename these.

---

## How to apply deck options in Anki

1. Open Anki **24.04 or later**.
2. Click the gear icon next to a deck → **Options**.
3. Create a new preset (e.g. "English Prepositions") and configure as below.
4. Apply the same preset to all module decks, or create per-module presets
   for finer control.

---

## Recommended preset: "English Prepositions" (FSRS)

### FSRS algorithm
| Setting                   | Recommended value                          |
|---------------------------|--------------------------------------------|
| Algorithm                 | **FSRS-5** (Anki 24.04+, default)          |
| Desired retention         | **0.85** (85 %)                            |
| Run optimiser             | After ≥ 400 review logs, then quarterly    |
| Reschedule on change      | On                                         |

Why 85 %: prepositions are an error-prone, high-payoff category. 85 %
balances productive accuracy (you actually use them right) against review
burden. Bump to 0.90 only if you target academic writing.

### Daily limits
| Setting                   | Recommended value                          |
|---------------------------|--------------------------------------------|
| New cards per day         | 10 (core: Modules 01, 03), 5 per other module |
| Maximum reviews per day   | 200 (FSRS surfaces fewer reviews than SM-2) |

### Learning steps
| Setting                   | Recommended value        |
|---------------------------|--------------------------|
| Learning steps            | 1m 10m                   |
| Graduating interval       | (FSRS managed)           |
| Easy interval             | (FSRS managed)           |
| New card order            | In order added           |

### Lapses
| Setting                   | Recommended value        |
|---------------------------|--------------------------|
| Relearning steps          | 10m                      |
| Minimum interval          | 1 day                    |
| Leech threshold           | 8 lapses                 |
| Leech action              | Suspend card             |

### Burying
| Setting                   | Recommended value        |
|---------------------------|--------------------------|
| Bury new siblings         | **On** (critical — 5 card types per note) |
| Bury review siblings      | **On**                   |

Sibling burying is essential because each English sentence in this deck can
generate up to 5 sibling cards (Recognition, Contrast, Production, Cloze,
Listening). Without burying, you'd see the same sentence 5× per session and
destroy the desirable-difficulty effect.

### Display order
| Setting                   | Recommended value        |
|---------------------------|--------------------------|
| New/review order          | Show reviews before new  |
| Review sort order         | Due date, then random    |
| Interleave card types     | On (within deck)         |

---

## Card UX policies

The note templates ship with **three-tier progressive reveal** on the
Recognition card and **gated "Why?" taps** on Contrast/Production. These
are not Anki settings — they are baked into the templates — but be aware:

- The Recognition back shows only **Tier A** (Label · IPA · audio replay)
  by default. Tap **"Show context"** for Tier B (Pattern · MainUse · QuickCue),
  and **"Show full reference"** for Tier C (Contrast · WhenNotToUse · image
  schema · tags).
- The Contrast / Production back hides the **"Why?"** explanation behind a
  tap. Always *generate* your own reason before tapping (Slamecka-Graf
  generation effect).
- **Audio policy**: TTS audio is on the **back** of every card type **except
  Listening** (where the audio *is* the prompt and lives on the front). This
  prevents split-attention during reading.

---

## Suggested study path (FSRS-aware)

### Stage 1 — Spatial Core (in / on / at) — Modules 01 + 11
Start with `01 - Spatial Core::1 - Recognition` and a small dose of
`11 - Polysemy Networks` for the *in / on / at* mini-network.
- New cards per day: 10 (Module 01) + 3 (Module 11)
- Goal: 90 %+ accuracy on the three highest-frequency prepositions and
  conscious awareness of CONTAINER / SUPPORT / POINT image schemas.

### Stage 2 — Add Contrast + Listening
Enable `01 - Spatial Core::2 - Contrast` and `01 - Spatial Core::5 - Listening`.
- New cards per day: 5 each.
- Listening cards are minimal-pair and sense-discrimination drills — *do
  these in a quiet room with headphones*.

### Stage 3 — Add Production
Enable `01 - Spatial Core::4 - Production`.
- New cards per day: 5
- Production prompts are multi-sentence narratives, not bare gap-fills.
  Type your answer first, then reveal.

### Stage 4 — Spatial Extended (Module 02)
- New cards per day: 5 per deck type.

### Stage 5 — Time Prepositions (Module 03)
- New cards per day: 5 per deck type.
- Heavy contrast load: in/on/at-time, by/until, for/since/during/while.

### Stage 6 — Movement & Direction (Module 04)
- to / into / onto / through / across / along / towards / off / out of / from.

### Stage 7 — Dependent Prepositions (Modules 05, 06, 07)
- The largest cluster. Pace at 5 cards/day per module for several weeks.
- These are *atomic chunks* — do not try to derive rules.

### Stage 8 — Phrasal & Multi-word (Module 08)
- because of / instead of / in spite of / on behalf of / by means of …

### Stage 9 — Abstract & Idiomatic (Module 09)
- on purpose, in time vs on time, at risk, under pressure, by accident, …
- Many cards have an associated picture-cue mnemonic.

### Stage 10 — Polysemy Networks proper (Module 11)
- Enable the full module after you've internalised core spatial + temporal +
  movement senses. The cards explicitly trace the prototype-to-extended
  radiation.

### Stage 11 — Zero Preposition & Ellipsis (Module 12)
- High-error blind spot for most learners. Drill systematically.

### Stage 12 — L1 Interference (Module 10)
- Filter to your own L1 with a tag-based filtered deck:
  `tag:l1:spanish` (or french / german / russian / mandarin / japanese).
- Suspend the other-L1 cards.

---

## Tips for effective use

- **Never skip reviews** to add more new cards. FSRS depends on review logs
  to optimise.
- **Use filtered decks** to drill a specific cluster:
  - `tag:contrast:in-vs-on-vs-at-place`
  - `tag:l1:japanese`
  - `tag:image-schema:container`
- **Suspend** any card that feels too easy immediately.
- **Generate before reveal**: on Contrast/Production cards, write or say
  your "why" before tapping.
- **Listening cards**: redo any you got wrong as audio-only review until
  you can name the preposition without the transcript.
- **Target 85 % retention** during review; if you're consistently above
  92 %, lower desired retention to 0.82 to reduce review load.
- **Leech management**: cards that trip you up 8 times will be auto-suspended.
  Review suspended cards weekly via Browse > `is:suspended`.

---

## Tag browser shortcuts

Use these searches in Anki's Browse window to study specific areas:

| Filter                              | Purpose                                |
|-------------------------------------|----------------------------------------|
| `tag:type:listening`                | All audio-discrimination cards         |
| `tag:type:contrast`                 | All contrast cards                     |
| `tag:type:production`               | All production cards                   |
| `tag:contrast:in-on-at-place`       | Spatial core trio (place)              |
| `tag:contrast:in-on-at-time`        | Time core trio                         |
| `tag:contrast:by-vs-until`          | Deadline vs duration up to             |
| `tag:contrast:for-since-during-while` | Big four duration markers            |
| `tag:contrast:to-into-onto`         | Direction vs entry vs surface contact  |
| `tag:dependent:verb`                | Verb + preposition collocations        |
| `tag:dependent:adjective`           | Adjective + preposition collocations   |
| `tag:dependent:noun`                | Noun + preposition collocations        |
| `tag:phrasal-preposition`           | Multi-word prepositions                |
| `tag:image-schema:container`        | All CONTAINER-schema senses            |
| `tag:image-schema:support`          | All SUPPORT/CONTACT senses             |
| `tag:image-schema:path`             | All PATH senses (movement)             |
| `tag:l1:spanish`                    | Spanish-speaker interference cards     |
| `tag:l1:japanese`                   | Japanese-speaker interference cards    |
| `tag:picture-cue:yes`               | Photo-front spatial/idiomatic cards    |
| `tag:mnemonic:yes`                  | Cards with explicit visual mnemonics   |

---

## Appendix — Legacy SM-2 settings (Anki ≤ 23.10)

If you cannot upgrade to Anki 24.04 (FSRS default), use these conservative
SM-2 numbers — but FSRS at 0.85 retention will give you ~30 % fewer reviews
for the same outcome.

```
Learning steps:      1m 10m
Graduating interval: 1 day
Easy interval:       4 days
Starting ease:       250 %
Maximum interval:    365 days
Interval modifier:   100 %
Hard interval:       120 %
Easy bonus:          130 %
```
