"""Self-contained .apkg builder on top of the official `anki` package.

Exposes a Model / Deck / Note / Package API (originally inspired by the
third-party `genanki` library, but with no runtime dependency on it).

WHY THIS EXISTS
---------------
genanki produces legacy v11-format .apkg files. Even when we hand-inject a
deck_config row and bind decks to it, Anki's importer rewrites every imported
deck's config_id back to 1 (Default) unless the package was exported through
the official Anki backend with `with_deck_configs=true` and `legacy=false`.

This module exposes a tiny subset of the genanki public API (Model / Deck /
Note / Package) but implements it on top of `anki.Collection` so the produced
.apkg uses the modern v18 schema with proper deck-options binding that
auto-applies on import in Anki Desktop 23.10+.

DESIGN
------
* Lazy: nothing touches the Anki backend until `Package.write_to_file()` is
  called. Models, decks, and notes are accumulated as plain Python objects
  and materialised in a single batch at the end.
* Compatible: Model(model_id, name, fields=, templates=, css=, model_type=)
  and Note(model=, fields=, tags=) signatures match genanki 0.13.
* Stable IDs: model and deck IDs given by the caller are preserved in the
  output (we use direct SQLite UPDATE after add_notetype/add_deck since the
  backend assigns fresh ids; see notes inside `_install_*`).

This is intentionally minimal — it does NOT implement the full genanki API.
Only the surface used by `build_anki_package.py`.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# Public constants matching genanki's surface
class _ModelTypes:
    FRONT_BACK = 0
    CLOZE = 1


class Model:
    """genanki.Model lookalike. Accumulates schema; installed at write time."""

    FRONT_BACK = _ModelTypes.FRONT_BACK
    CLOZE = _ModelTypes.CLOZE

    def __init__(self, model_id, name, fields=None, templates=None,
                 css='', model_type=FRONT_BACK):
        self.model_id = int(model_id)
        self.name = name
        self.fields = list(fields or [])
        self.templates = list(templates or [])
        self.css = css
        self.model_type = model_type

    # genanki.Note uses model.fields to map names → ord. We keep the same shape.
    def field_names(self):
        return [f['name'] for f in self.fields]


class Deck:
    """genanki.Deck lookalike. Holds notes; installed at write time."""

    def __init__(self, deck_id, name, description=''):
        self.deck_id = int(deck_id)
        self.name = name
        self.description = description
        self.notes: list[Note] = []

    def add_note(self, note: 'Note'):
        self.notes.append(note)


class Note:
    """genanki.Note lookalike. Stores model + field values + tags."""

    def __init__(self, model: Model, fields=None, tags=None, guid=None):
        self.model = model
        self.fields = list(fields or [])
        self.tags = list(tags or [])
        self.guid = guid  # ignored — Anki backend assigns/dedupes via field hash


class Package:
    """genanki.Package lookalike. Materialises everything via anki.Collection.

    On `write_to_file(path)`:
      1. Open a fresh anki.Collection in a temp dir.
      2. Install all unique models (with stable IDs).
      3. Install all decks (with stable IDs) + descriptions.
      4. Add all notes.
      5. Copy media files into col.media.dir().
      6. Create the 'English Verb System' FSRS preset and bind every
         non-default deck to it via set_config_id_for_deck_dict.
      7. Export with with_deck_configs=true, legacy=false (modern format).

    The result is a .apkg whose preset auto-binds on import in Anki 23.10+.
    """

    # Default preset names — can be overridden per-instance via the
    # `preset_name` and `l1_deck_prefix` ctor args (so this packager is
    # reusable across sister projects).
    PRESET_NAME = 'English Verb System'
    L1_PRESET_NAME = 'English Verb System (L1 — opt in)'
    L1_DECK_PREFIX = '13 - L1 Interference::'
    PRESET_DEF = {
        'name': PRESET_NAME,
        'fsrs': True,
        'desiredRetention': 0.9,
        'maxTaken': 60,
        'autoplay': True,
        'timer': 0,
        'replayq': True,
        'new': {
            'bury': True,
            'delays': [1.0, 10.0],
            'initialFactor': 2500,
            'ints': [1, 4, 0],
            'order': 1,
            'perDay': 10,
            'separate': True,
        },
        'rev': {
            'bury': True,
            'ease4': 1.3,
            'ivlFct': 1.0,
            'maxIvl': 365,
            'perDay': 150,
            'hardFactor': 1.2,
        },
        'lapse': {
            'delays': [10.0],
            'leechAction': 0,
            'leechFails': 8,
            'minInt': 1,
            'mult': 0.0,
        },
        'dyn': False,
        'fsrsParams5': [],
        'fsrsWeightSearch': '',
    }

    def __init__(self, decks, preset_name=None, l1_deck_prefix=None):
        self.decks: list[Deck] = list(decks)
        self.media_files: list[str] = []
        # Per-instance overrides — fall back to class defaults
        if preset_name is not None:
            self.PRESET_NAME = preset_name
            self.L1_PRESET_NAME = f'{preset_name} (L1 — opt in)'
            self.PRESET_DEF = {**self.__class__.PRESET_DEF, 'name': preset_name}
        if l1_deck_prefix is not None:
            self.L1_DECK_PREFIX = l1_deck_prefix

    # ------------------------------------------------------------------
    def write_to_file(self, out_path: str):
        try:
            from anki.collection import Collection
            from anki.import_export_pb2 import (
                ExportAnkiPackageOptions, ExportLimit,
            )
            from anki.generic_pb2 import Empty
        except ImportError as e:
            raise SystemExit(
                f'genanki-shim: missing dependency `anki`: {e}\n'
                f'Install with: pip install "anki>=24.0"'
            ) from e

        out_path = os.path.abspath(out_path)
        workdir = tempfile.mkdtemp(prefix='genanki_shim_')
        col_path = os.path.join(workdir, 'collection.anki2')
        col = Collection(col_path)
        try:
            # ── 1. Install all unique models with stable IDs ──────────
            models_by_id: dict[int, Model] = {}
            for d in self.decks:
                for n in d.notes:
                    models_by_id[n.model.model_id] = n.model

            installed_models: dict[int, dict] = {}  # mid → notetype dict
            for mid, m in models_by_id.items():
                installed_models[mid] = self._install_model(col, m)

            # ── 2. Install all decks with stable IDs ──────────────────
            installed_decks: dict[int, int] = {}  # original did → final did
            for d in self.decks:
                installed_decks[d.deck_id] = self._install_deck(col, d)

            # ── 3. Add notes ──────────────────────────────────────────
            n_added = 0
            for d in self.decks:
                final_did = installed_decks[d.deck_id]
                for note in d.notes:
                    nt = installed_models[note.model.model_id]
                    new_note = col.new_note(nt)
                    # Pad / truncate fields to match notetype
                    expected = len(nt['flds'])
                    fields = list(note.fields)
                    if len(fields) < expected:
                        fields += [''] * (expected - len(fields))
                    elif len(fields) > expected:
                        fields = fields[:expected]
                    new_note.fields = fields
                    new_note.tags = list(note.tags)
                    col.add_note(new_note, final_did)
                    n_added += 1

            # ── 4. Copy media files into col.media.dir() ──────────────
            media_dir = col.media.dir()
            n_media = 0
            for src in self.media_files:
                src_path = Path(src)
                if not src_path.exists() or src_path.stat().st_size == 0:
                    continue
                dst = Path(media_dir) / src_path.name
                if not dst.exists():
                    shutil.copy(src_path, dst)
                n_media += 1

            # ── 5. Create FSRS preset + bind every non-default deck ───
            preset_id = self._ensure_preset(col)
            l1_preset_id = self._ensure_l1_preset(col)
            bound = 0
            for d in col.decks.all_names_and_ids():
                if d.id == 1:
                    continue
                deck = col.decks.get(d.id)
                if deck is None or deck.get('dyn'):
                    continue
                # L1 Interference sub-decks ship OPTED-OUT: bound to a
                # zero-cards-per-day preset. Each user enables only
                # their L1 by switching that one sub-deck to the main
                # 'English Verb System' preset.
                target_preset = (
                    l1_preset_id
                    if self.L1_DECK_PREFIX in deck.get('name', '')
                    else preset_id
                )
                col.decks.set_config_id_for_deck_dict(deck, target_preset)
                col.decks.save(deck)
                bound += 1

            col.save()

            # ── 6. Export modern .apkg with deck configs included ─────
            export_opts = ExportAnkiPackageOptions(
                with_scheduling=False,
                with_deck_configs=True,
                with_media=True,
                legacy=False,
            )
            limit = ExportLimit(whole_collection=Empty())
            exported = col.export_anki_package(
                out_path=out_path,
                options=export_opts,
                limit=limit,
            )
            print(f'  [anki-packager] notes: {n_added}, decks: {len(installed_decks)}, '
                  f'models: {len(installed_models)}, media: {n_media}, '
                  f'preset bound to {bound} decks → {exported} cards exported')
        finally:
            col.close()

    # ------------------------------------------------------------------
    def _install_model(self, col, m: Model) -> dict:
        """Create the notetype with auto-id, then UPDATE id → m.model_id.

        We want stable model IDs across versions so re-imports update notes
        in place rather than duplicating. The Anki backend asserts id==0 on
        add (auto-assign), so we patch the id post-add via direct SQLite.
        """
        nt = col.models.new(m.name)
        nt['type'] = int(m.model_type)
        nt['css'] = m.css
        for fdef in m.fields:
            f = col.models.new_field(fdef['name'])
            nt['flds'].append(f)
        for tdef in m.templates:
            t = col.models.new_template(tdef['name'])
            t['qfmt'] = tdef.get('qfmt', '')
            t['afmt'] = tdef.get('afmt', '')
            nt['tmpls'].append(t)
        col.models.add(nt)
        old_id = nt['id']
        new_id = m.model_id
        if old_id != new_id:
            # Re-key in all child tables and the parent
            col.db.execute('UPDATE notetypes SET id = ? WHERE id = ?',
                           new_id, old_id)
            col.db.execute('UPDATE fields SET ntid = ? WHERE ntid = ?',
                           new_id, old_id)
            col.db.execute('UPDATE templates SET ntid = ? WHERE ntid = ?',
                           new_id, old_id)
        # Re-fetch the dict with the final id
        return col.models.get(new_id)

    # ------------------------------------------------------------------
    def _install_deck(self, col, d: Deck) -> int:
        """Create deck with auto-id, then UPDATE id → d.deck_id."""
        result = col.decks.add_normal_deck_with_name(d.name)
        old_id = result.id
        new_id = d.deck_id
        if old_id != new_id:
            # Avoid clash if new_id already exists (shouldn't, but be safe)
            existing = col.decks.get(new_id)
            if existing is None:
                col.db.execute('UPDATE decks SET id = ? WHERE id = ?',
                               new_id, old_id)
                # No child tables to re-key for decks (cards.did references
                # the deck id, but no cards exist yet at this point).
                old_id = new_id
        deck = col.decks.get(old_id)
        if deck is not None and d.description:
            deck['desc'] = d.description
            col.decks.save(deck)
        return old_id

    # ------------------------------------------------------------------
    def _ensure_l1_preset(self, col) -> int:
        """Create/update the opt-in preset (zero new + zero review/day).

        L1 Interference sub-decks bind to this preset by default so a
        Russian speaker doesn't get drowned in Spanish/French/Mandarin
        cards. To activate any L1 deck the user simply opens
        gear → Deck options on that one sub-deck and switches the
        preset selector to 'English Verb System'.
        """
        existing = next(
            (c for c in col.decks.all_config()
             if c.get('name') == self.L1_PRESET_NAME),
            None,
        )
        l1_def = {**self.PRESET_DEF, 'name': self.L1_PRESET_NAME}
        l1_def['new'] = {**l1_def['new'], 'perDay': 0}
        l1_def['rev'] = {**l1_def['rev'], 'perDay': 0}
        if existing:
            existing.update({k: v for k, v in l1_def.items() if k != 'name'})
            col.decks.update_config(existing)
            return int(existing['id'])
        new_id = col.decks.add_config_returning_id(self.L1_PRESET_NAME)
        full = col.decks.get_config(new_id)
        full.update({k: v for k, v in l1_def.items() if k != 'name'})
        col.decks.update_config(full)
        return int(new_id)

    # ------------------------------------------------------------------
    def _ensure_preset(self, col) -> int:
        """Create the 'English Verb System' preset (or update existing)."""
        existing = next(
            (c for c in col.decks.all_config()
             if c.get('name') == self.PRESET_NAME),
            None,
        )
        if existing:
            existing.update({k: v for k, v in self.PRESET_DEF.items()
                             if k != 'name'})
            col.decks.update_config(existing)
            return int(existing['id'])
        new_id = col.decks.add_config_returning_id(self.PRESET_NAME)
        full = col.decks.get_config(new_id)
        full.update({k: v for k, v in self.PRESET_DEF.items() if k != 'name'})
        col.decks.update_config(full)
        return int(new_id)


# Re-exports for `from anki_packager import Model, Deck, Note, Package`
__all__ = ['Model', 'Deck', 'Note', 'Package']
