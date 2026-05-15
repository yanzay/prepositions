# English Prepositions — Content Plan (v2, audit-revised)

This is the authoritative roadmap for what cards live in each module of the
`english_prepositions_anki.apkg` deck. **v2** reflects corrections from three
independent audits (SLA pedagogy, cognitive science, premium-deck parity) —
see `docs/AUDIT_NOTES.md` (forthcoming) for the full reasoning trail.

It mirrors the layered approach used in `../verbs`: every module ships
**Recognition / Contrast / Production / Cloze / Listening** subdecks (5 card
types — Listening added in v2), and the content scales from highest-frequency
core senses down to idiomatic and L1-interference edges.

---

## 0. Pedagogical principles (explicit, evidence-anchored)

The deck is engineered against six published-research principles. Every card
must be justifiable against at least one of them.

| # | Principle | Source | How the deck implements it |
|---|-----------|--------|----------------------------|
| 1 | **Cognitive linguistics / image schemas** — prepositions are polysemous radial categories rooted in a spatial prototype | Lakoff 1987; Tyler & Evans 2003; Langacker 2008 | Module 11 (Polysemy Networks); every spatial card carries trajector/landmark/frame-of-ref fields |
| 2 | **Lexical-chunk approach** — dependent prepositions are stored as collocations, not derived from rules | Lewis 1993; Nation 2013; Boers & Lindstromberg 2008 | Modules 05/06/07 ship as atomic chunks with `generalisable:yes/no/partial` flag |
| 3 | **Transfer-Appropriate Processing** — train in the modality of expected use | Morris et al. 1977; Roediger & Tekin 2017 | New 5th card type **Listening** (~10 % of deck); Production prompts upgraded to multi-sentence narratives |
| 4 | **Desirable difficulties + spacing** | Bjork & Bjork 2011; Cepeda et al. 2006 | FSRS-5 algorithm (not SM-2); hybrid blocked-then-interleaved scheduling |
| 5 | **Generation effect / elaborative interrogation** | Slamecka & Graf 1978; Dunlosky et al. 2013 | "Why" field is **gated** behind a tap — learner must generate before reveal |
| 6 | **Contrastive analysis from learner corpora** | Granger; CLC; EFCAMDAT | Module 10 sources top-5 errors per L1 from EFCAMDAT/CLC tagsets |

---

## 1. Source corpora & frequency anchoring

| Corpus | Use |
|--------|-----|
| BNC / COCA top-100 prepositions list | Frequency ranking + tag `frequency:high/mid/low` |
| Cambridge English Vocabulary Profile (English Profile, criterial features) | CEFR-level tagging per **sense**, not per **word** |
| Practical English Usage (Swan, 4th ed.) | Canonical usage distinctions, esp. for *in/on/at* |
| Longman Grammar of Spoken & Written English | Register tagging (formal / informal / neutral) |
| English Vocabulary in Use (Cambridge) — prepositions chapter | Dependent-prep collocation lists |
| Cambridge Learner Corpus (CLC) error tags | L1-interference seed errors per language |
| EFCAMDAT (Cambridge / EF) | Open learner-corpus error frequencies |
| Tyler & Evans (2003) sense inventories | Polysemy network mapping (Module 11) |
| Lindstromberg (2010) *English Prepositions Explained* | Image-schema diagrams + extended-sense mappings |

Every row gets at least one tag from each axis: `frequency:* / register:* / cefr:* / sense:* / module:* / image-schema:*`.
The `apply_taxonomy_tags.py` script enforces this after content is finalised.

---

## 2. Tier breakdown

- **Tier 1** — text content (Recognition / Contrast / Production / Cloze / Listening tab-separated files).
- **Tier 2** — multimodal media: **Google Cloud Text-to-Speech (Neural2 voices)** audio, GA IPA, SVG image-schema diagrams, ~200 photographic picture-cue images for spatial/idiomatic core.
- **Tier 3** — taxonomy tags, schema reference, sample-card screenshots, demo video, AnkiHub deck listing.

---

## 3. Card types (5, was 4)

| Type | Front | Back (tiered reveal) | Difficulty | % of deck |
|------|-------|----------------------|------------|-----------|
| Recognition | Sentence (text) | **Tier-A**: Label + audio + IPA · **Tier-B** (tap "More"): Pattern + MainUse · **Tier-C**: Contrast + WhenNotToUse + image schema + tags | Low | 24 % |
| Contrast | Sentence with `___` + OptionA / OptionB | Answer → "Why?" gated tap → Tip | Med | 24 % |
| Production | Multi-sentence narrative prompt + Target hint | Sample answer → "Why this works?" gated tap | High | 22 % |
| Cloze | `{{c1::prep}}` in context | Hint (sense) | Med-High | 18 % |
| **Listening (new)** | Audio only — "Speaker says…" minimal-pair or sense-discrimination | Transcript + correct preposition + IPA | Med | 12 % |

---

## 4. Module roadmap (revised)

Counts shown as **R / C / P / Cl / L = Total**. Re-balanced so:
- Production rises from 16 % → 22 %
- Contrast rises from 22 % → 24 % (concentrated on confusable pairs)
- New Listening type adds ~12 %
- New Modules 11 & 12 added

| #  | Module                                  | R  | C  | P  | Cl | L  | Total |
|----|-----------------------------------------|----|----|----|----|----|-------|
| 01 | Spatial Core (in / on / at)             | 50 | 50 | 25 | 25 | 20 |  170  |
| 02 | Spatial Extended                        | 55 | 35 | 25 | 20 | 15 |  150  |
| 03 | Time Prepositions                       | 55 | 50 | 25 | 25 | 15 |  170  |
| 04 | Movement & Direction                    | 45 | 30 | 20 | 20 | 15 |  130  |
| 05 | Dependent — Verb + Prep                 | 70 | 35 | 35 | 30 | 15 |  185  |
| 06 | Dependent — Adjective + Prep            | 40 | 20 | 20 | 20 | 10 |  110  |
| 07 | Dependent — Noun + Prep                 | 30 | 15 | 15 | 15 |  5 |   80  |
| 08 | Phrasal & Multi-word Prepositions       | 35 | 20 | 15 | 20 | 10 |  100  |
| 09 | Abstract & Idiomatic Uses               | 40 | 25 | 20 | 25 | 15 |  125  |
| 10 | L1 Interference (6 langs × top-5 errors)| 25 | 30 | 15 | 15 | 10 |   95  |
| 11 | **Polysemy Networks (NEW)**             | 25 | 15 | 15 | 15 | 10 |   80  |
| 12 | **Zero Preposition & Ellipsis (NEW)**   | 20 | 15 | 10 | 15 |  5 |   65  |
|    | **Totals**                              | **490** | **340** | **240** | **245** | **145** | **1,460** |

Receptive (R + Cl) ≈ 50 %, Productive (P) ≈ 17 %, Discriminative (C + L) ≈ 33 % — moves the deck from Nation's "borderline-receptive" zone into the recommended balance.

---

## 5. Module-by-module detail

### 01 — Spatial Core (in / on / at)
Goal: master the highest-frequency place trio with explicit image-schema framing.

**Senses (each tagged with image schema)**
- `in` (CONTAINER schema: in the box, in my pocket, in Tokyo, in the water)
- `on` (SUPPORT/CONTACT schema: on the wall, on the ceiling, on page 3, on the bus)
- `at` (POINT schema: at the door, at the meeting, at school)

**Trajector / landmark / frame-of-reference** populated on every Recognition card.

**Contrast pairs (≥10 each — was ≥3)**
in vs on · on vs at · in vs at · in/on/at + corner · in/on/at + transport.

**Listening cards**: minimal-pair audio (key *on* the table vs key *in* the table) + sense-discrimination ("Speaker says they're *at* the office vs *in* the office — which means physically inside?").

**Picture-cue cards**: ~30 photographic stimuli (cat *on* table, cat *in* basket, cat *under* table) — front = photo, back = preposition.

---

### 02 — Spatial Extended
Senses: under, below, beneath, over, above, between, among, behind, in front of,
opposite, next to / beside, near, by, around, through (static), inside, outside,
against, across from.

**Contrast highlights** (≥8 cards each): between vs among · over vs above · under vs below vs beneath · next-to vs beside vs by vs near · in front of (place) vs before (time).

---

### 03 — Time Prepositions
Senses: in / on / at (time) · by · until/till · for · since · during · while ·
from…to / between…and · within · throughout · before / after / ago / in (= "from now").

**Contrast clusters (≥10 each)**: in/on/at-time · by vs until · for vs since vs ago · during vs while · in vs within vs after.

---

### 04 — Movement & Direction
to · into · onto · out of · off · from · through · across · along · towards ·
away from · up · down · past · around / round · via.

**Contrast highlights**: to vs into vs onto · across vs through vs over · along vs through vs across · in (static) vs into (movement) · arrive at vs arrive in.

---

### 05 — Dependent: Verb + Preposition
Top 90 verb+prep collocations grouped by preposition:
- on · of · for · to · with · from · about · at · in · into.

**Atomic chunk treatment**: every card has a `generalisable:yes|no|partial` tag.
Contrast highlights: talk to vs talk with · arrive at vs arrive in · look at/for/after/into · agree with/to/on · think of vs about · dream of vs about.

---

### 06 — Dependent: Adjective + Preposition
Top 50 adj+prep collocations across **of, for, to, with, from, about, at, in, on**.
Contrast highlights: angry with/about/at · worried about vs nervous about ·
good at vs with vs for · different from / to / than (BrE/AmE flag) · responsible for vs to.

---

### 07 — Dependent: Noun + Preposition
Top 40 noun+prep collocations: reason for, cause of, effect on, increase in, solution to, cure for, attitude to(wards), advantage of, difference between, relationship between/with.

---

### 08 — Phrasal & Multi-word Prepositions
because of, due to, owing to, thanks to · instead of, rather than · in spite of, despite, regardless of · according to, in line with · in addition to, apart from, except for · on behalf of, on account of, in light of, by means of, in front of, in case of, in terms of, with regard to, ahead of.

Contrast: because-of vs because (prep vs conj) · despite vs in-spite-of vs although · except / except-for / apart-from / besides.

---

### 09 — Abstract & Idiomatic Uses
on/in time · by accident vs on purpose · on foot vs by car · on TV / on the radio / in the news · in love / trouble / danger / pain / a hurry · at risk / fault / war / peace · under pressure / control / construction / arrest · out of work / stock / order / breath · by hand / chance / heart · at a loss / discount / glance / distance.

**Mnemonic flag** (`mnemonic:yes`) on every opaque idiom — picture-cue or visual-metaphor card recommended for these.

---

### 10 — L1 Interference (6 languages × top-5 corpus errors)

Each language gets its 5 highest-frequency preposition errors from the
**Cambridge Learner Corpus (CLC)** error-tag database and **EFCAMDAT**, expressed
as natural English target sentences with the L1 trap encoded in the
explanation field (the deck never displays incorrect English on the front).

| L1 | Top-5 error families to drill |
|----|-------------------------------|
| Spanish | depend **on** (not *of*) · think **of/about** (not *in*) · married **to** (not *with*) · dream **of/about** (not *with*) · *en* generalisation in time-of-day (at 8 a.m., not "in 8 a.m.") |
| French | listen **to** (not bare *listen*) · wait **for** (not bare *wait*) · look **at** (not bare *look*) · interested **in** (not *by*) · *on/in* the photo (BrE *in*) |
| German | **on** Monday (not *at*) · **in** the morning (not *at*) · think **of/about** (not *on*) · afraid **of** (not *before*) · `seit + present` ≠ "since + perfect" |
| Russian | depend **on** (not *from*) · consist **of** (not *from*) · different **from** (not *of*) · article + place ("in the school" vs "in school") · go **to** (case-marking transfer) |
| Mandarin | **on** Monday + bare day-of-week · **in** 2024 + bare year · arrive **in/at** · get **on/off** (not *up/down*) · look forward **to** + V-ing |
| Japanese | **on** Monday (no time particle) · go **to** school (not bare) · **in/at** night/noon distinction · play (a sport) zero-prep vs *play at* · be good **at** (not *in*) |

Contrast cards juxtapose the corpus-attested error against the target form;
Listening cards present an audio prompt where the learner must catch the
correct preposition on the fly.

---

### 11 — Polysemy Networks (NEW, must-have)

Explicit teaching of how a single preposition radiates from its spatial
prototype to temporal, abstract, and idiomatic senses. Card types are:

- **Recognition**: shows three or four exemplar sentences for one preposition; learner identifies the shared image schema.
- **Contrast**: distinguishes prototype from extended sense (in the box vs in trouble vs in 2026).
- **Production**: prompt asks for one prototype + one extended-sense use of the same preposition.
- **Cloze**: a paragraph using the same preposition four times in different senses; learner fills each.

**Prepositions covered (≥6 senses each)**: in, on, at, by, over, through,
under, around. Each gets a single mini-network diagram (CONTAINER → STATE →
TEMPORAL ENCLOSURE etc.) shipped as SVG.

---

### 12 — Zero Preposition & Ellipsis (NEW, must-have)

High-error domain in learner corpora; absent from v1.

**Sub-clusters**:
- Bare nouns of place: home / bed / school / town / work / hospital / church / prison (+ context flag for *the*)
- Time adverbials: last week / next year / this morning (no preposition) vs *in* last week (error)
- Verb + bare object vs verb + preposition (discuss X / not "discuss about X"; enter X / not "enter into X")
- Null preposition in relative-clause stranding (the city I live in vs *that I live*)
- Days of the week with bare form (AmE: "see you Monday") vs *on Monday*

---

## 6. Tag taxonomy (revised, 8 axes)

Required on every row:
1. `module:01`..`module:12`
2. `type:recognition|contrast|production|cloze|listening`
3. `sense:spatial|temporal|movement|dependent|phrasal|idiomatic|interference|polysemy|zero`
4. `frequency:high|mid|low`
5. `register:formal|neutral|informal`
6. `cefr:a1|a2|b1|b2|c1|c2`  (criterial-feature based, *per sense* not per word)
7. **`image-schema:container|support|point|path|over|under|between|cluster|none`** (NEW)
8. **`generalisable:yes|no|partial`** (NEW; Modules 05–07 mainly)

Optional: `variant:brE|amE`, `l1:spanish|french|german|russian|mandarin|japanese`,
`domain:business|academic|everyday|travel`, `mnemonic:yes`, `picture-cue:yes`.

Optional contrast-pair drill tags: `contrast:in-on-at-place`, `contrast:by-until`, `contrast:for-since-during-while`, etc.

---

## 7. Card UX & cognitive-load discipline

### Recognition card back — three-tier reveal (was: flat 9-field dump)

| Tier | Shown by default | Content |
|------|------------------|---------|
| **A** | always | Label · IPA · audio replay button |
| **B** | "Show context" tap | Pattern · MainUse · QuickCue |
| **C** | "Show full reference" tap | Contrast · WhenNotToUse · image-schema diagram · tags |

This is the **CSS toggle pattern** used by the Lapis JP deck and recommended
by Mayer's multimedia-learning principles.

### Contrast & Production — gated "Why"
The "Why" explanation must not be visible alongside the answer. It is hidden
behind a "Why?" tap so the learner is forced to generate first (Slamecka &
Graf generation effect).

### Audio policy
- Recognition / Contrast / Production / Cloze: audio on **back** (no front auto-play; keeps reading channel uncluttered).
- **Listening** card type: audio on **front** (the cue itself), no text.
- Voice: Google Cloud Text-to-Speech Neural2 (`en-US-Neural2-F` US default; `en-GB-Neural2-A`/`B` available for BrE variant via `PREP_TTS_VOICE`). Optional native-actor pass for the highest-frequency 200 sentences (post-MVP).

### Mobile typography
- 18 px base, line-height 1.5, max-width 36 em, system-font-stack first.
- Light + dark + sepia themes via `prefers-color-scheme`.

---

## 8. Spaced-repetition algorithm: FSRS, not SM-2

Recommended in `ANKI_SETTINGS.md`:

```
Algorithm:        FSRS-5 (default in Anki 24.04+)
Desired retention: 0.85
Optimisation:     run after ≥400 review logs
Bury siblings:    on
Maximum interval: 365 d
Leech threshold:  8 lapses → suspend
```

SM-2 numbers are kept only in a "legacy fallback" appendix.

---

## 9. Build phasing (revised)

| Phase | Goal | Card target | Tier-2 media |
|-------|------|-------------|--------------|
| **A — MVP** | Modules 01 + 03 R + L only; sample screenshots; demo video | ~250 | None |
| **B — Core** | + C/P/Cl for 01 & 03; + 02, 04 R/L | ~600 | Diagrams, IPA |
| **C — Collocations** | Modules 05–07 | ~975 | + Google Neural2 TTS pass |
| **D — Polish** | Modules 08–12 | ~1,460 | + 200 picture-cue photos for 09 + 01 |
| **E — Distribution** | AnkiHub publish + GitHub release v1.0 + CHANGELOG.md | — | Optional native-actor recordings for top 200 sentences |

Each phase ends with `python3 validate_anki_data.py` (now also lint + tag-axis check) and a `git tag`.

---

## 10. Build & release rigor (premium-grade infrastructure)

Lifted from the audit:

- **CI**: `.github/workflows/validate.yml` runs on every PR — `validate_anki_data.py`, audio-existence check, IPA NFC normalisation, SVG validity, tag-axis lint.
- **Reproducible build**: `requirements.txt` pinned to exact versions; `python -m pip-compile` lockfile; Docker target for one-command rebuild.
- **Pre-commit**: trim trailing whitespace, ensure tabs in `*.txt`, validate UTF-8 NFC for IPA.
- **Snapshot tests**: golden `.apkg` hash for the empty-staging baseline — fails CI if note types or templates drift.
- **Governance docs**: `LICENSE` (CC-BY-SA-4.0), `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`, `CHANGELOG.md` (Keep-a-Changelog format), `docs/sample_cards/*.png`.
- **Distribution**: GitHub Releases (signed `.apkg`) + AnkiHub deck listing for collaborative updates + AnkiWeb shared-deck mirror for casual users.
- **Versioning**: SemVer (`v1.0.0`), embedded in deck name, surfaced in deck-info card.

---

## 11. Open decisions (need user input)

- **BrE / AmE**: ship one deck with both flagged via `variant:*` tag, OR two `.apkg` files with different audio voices? (Audit favours single deck with tag.)
- **Pricing**: free CC-BY-SA, freemium (free 300-card core + paid full deck), or fully paid? Audit notes free signals lower perceived value but maximises reach.
- **Native-actor audio**: budget a one-off ~$200–500 pass for the top 200 highest-frequency sentences post-v1.0, yes/no?
- **AnkiHub vs GitHub-only distribution**: AnkiHub gives continuous updates but locks paid users to a $5/mo subscription.

---

## 12. Audit trail

This v2 plan responds to three independent audits (SLA pedagogy, cognitive
science, premium-deck parity). Convergent must-haves applied:

- ✅ FSRS-5 instead of SM-2
- ✅ Tiered-reveal Recognition back (was 9-field flat dump)
- ✅ Listening card type added (Transfer-Appropriate Processing)
- ✅ Production rebalanced upward; Contrast concentrated on confusable pairs
- ✅ Module 11 Polysemy Networks (image-schema explicit teaching)
- ✅ Module 12 Zero Preposition & Ellipsis
- ✅ Trajector / Landmark / Frame-of-reference fields on spatial cards
- ✅ L1 module sourced from CLC + EFCAMDAT top-5 per language
- ✅ Picture-cue cards (~200) for spatial/idiomatic core
- ✅ "Why" field is gated/generated, not passively read
- ✅ Audio moved to back for non-Listening cards (split-attention fix)
- ✅ Google Cloud Text-to-Speech (Neural2 voices) — same provider as the sister verbs project, free tier covers the corpus
- ✅ CI / lockfile / governance docs added to Phase E
- ✅ AnkiHub + GitHub Release distribution strategy

Nice-to-haves deferred to post-v1.0:
- 🕓 Native-actor audio pass for top 200 sentences
- 🕓 Multi-accent variant decks (US / UK / AU)
- 🕓 Sepia theme + RTL stub (English-only deck, low value)
- 🕓 Cross-module interleaving deck (Tier 3 review phase)

Sources: Tyler & Evans 2003; Lakoff 1987; Langacker 2008; Lindstromberg 2010;
Boers & Lindstromberg 2008; Nation 2013; Schmitt 2008; Lewis 1993;
Bjork & Bjork 2011; Roediger & Karpicke 2006; Cepeda et al. 2006;
Morris et al. 1977; Slamecka & Graf 1978; Paivio 1986; Mayer 2019;
Dunlosky et al. 2013; Ye et al. 2024 (FSRS); Granger CLC; EFCAMDAT.
