#!/usr/bin/env python3
"""build_images.py — fetch CC-licensed cover images for picture-cue cards.

This is a Tier-2 builder. It scans the staging files for rows tagged with
`picture-cue:yes`, then fetches one CC-licensed photo per unique caption
from Wikimedia Commons (CC-BY/CC0/PD content), saves JPEGs to
`media/images/{hash}.jpg`, and writes `media/images_index.json` mapping
`caption-hash -> {file, attribution, license, query, ...}`.

Idempotent + incremental: re-running only fetches images for rows whose
caption hash isn't already present in the manifest. Pruning of orphaned
files happens automatically.

Wikimedia Commons API is keyless and ToS-friendly for non-commercial
agentic use. We respect their User-Agent guideline and throttle requests.
If a search returns nothing, we fall back to a deterministic placeholder
(picsum.photos seeded by the caption hash) so the deck still builds.

Per-row tag conventions:
  picture-cue:yes               — this row should have a picture
  picture-query:"<query text>"  — optional explicit search query
                                  (otherwise: derived from Sentence + Label)

Usage:
  python3 build_images.py            # fetch all missing
  python3 build_images.py --limit 5  # smoke-test 5 rows only
  python3 build_images.py --force    # re-download everything

Output:
  media/images/<sha1-12>.jpg
  media/images_index.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
STAGING_FILES = [
    ROOT / "prepositions_recognition.txt",
    ROOT / "prepositions_contrast.txt",
    ROOT / "prepositions_production.txt",
    ROOT / "prepositions_cloze.txt",
    ROOT / "prepositions_listening.txt",
]

IMAGES_DIR       = ROOT / "media" / "images"
IMAGES_INDEX     = ROOT / "media" / "images_index.json"
USER_AGENT = (
    "EnglishPrepositionsAnkiBot/1.0 "
    "(https://github.com/yanzay/english-prepositions-anki; cc-image-fetch)"
)
WMC_SEARCH_URL   = "https://commons.wikimedia.org/w/api.php"
PLACEHOLDER_URL  = "https://picsum.photos/seed/{seed}/640/480.jpg"
REQUEST_TIMEOUT  = 30
THROTTLE_SECONDS = 0.4   # be polite to Commons


# ── Helpers ────────────────────────────────────────────────────────────────
def caption_hash(caption: str) -> str:
    return hashlib.sha1(caption.strip().encode("utf-8")).hexdigest()[:12]


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def parse_tags(tags: str) -> dict[str, str]:
    """Return {axis: value} from a space-separated tag string. Quoted values
    (e.g. picture-query:"in the corner") are preserved as a single value."""
    out: dict[str, str] = {}
    # Match key:value or key:"quoted value"
    for m in re.finditer(r'([\w\-]+):(?:"([^"]*)"|(\S+))', tags):
        out[m.group(1)] = m.group(2) if m.group(2) is not None else m.group(3)
    return out


def derive_query(sentence: str, label: str) -> str:
    """Build a Wikimedia search query from the sentence + label.

    Strategy:
      - Strip HTML/cloze markup from the sentence.
      - If a Label is present, use it as a hint suffix.
      - Limit to ~6 informative tokens to keep the API happy.
    """
    txt = strip_html(sentence)
    txt = re.sub(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}", r"\1", txt)
    txt = re.sub(r"[^\w\s]", " ", txt).strip()
    tokens = [t for t in txt.split() if len(t) > 2 and t.lower() not in {
        "the", "and", "but", "for", "you", "she", "her", "his", "him",
        "are", "was", "were", "have", "had", "has", "this", "that",
        "they", "them", "with", "from", "their",
    }]
    head = " ".join(tokens[:6])
    if label:
        # Strip "(LABEL...)" parens from canonical labels
        bare_label = re.sub(r"\s*\(.*?\)\s*", "", label).strip()
        if bare_label:
            return f"{head} {bare_label}"
    return head


# ── Staging-file scanner ───────────────────────────────────────────────────
def collect_picture_cue_rows():
    """Scan all staging files; yield {hash, caption, query, source_file, lineno}
    for each row tagged picture-cue:yes (deduplicated by hash)."""
    seen: dict[str, dict] = {}
    for path in STAGING_FILES:
        if not path.exists():
            continue
        for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw or raw.startswith("#"):
                continue
            fields = raw.split("\t")
            if not fields:
                continue
            tags = fields[-1]
            if "picture-cue:yes" not in tags:
                continue
            tag_map = parse_tags(tags)
            # Pick the source caption: usually field 0 (Sentence/Text/Prompt)
            caption = strip_html(fields[0])
            caption = re.sub(r"\{\{c\d+::([^:}]+)(?:::[^}]+)?\}\}", r"\1", caption)
            # For Listening cards, prefer the Transcript over the AudioRef
            if path.name == "prepositions_listening.txt" and len(fields) >= 4:
                caption = strip_html(fields[3])
            if not caption:
                continue
            # Query: explicit picture-query tag wins, else derived
            label = fields[1] if path.name == "prepositions_recognition.txt" and len(fields) > 1 else ""
            query = tag_map.get("picture-query") or derive_query(caption, label)
            h = caption_hash(caption)
            if h not in seen:
                seen[h] = {
                    "hash": h,
                    "caption": caption,
                    "query": query,
                    "source_file": path.name,
                    "lineno": lineno,
                }
    return list(seen.values())


# ── HTTP ────────────────────────────────────────────────────────────────────
def http_get_json(url: str, params: dict) -> dict:
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{qs}",
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def http_get_bytes(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
        return resp.read()


# ── Wikimedia Commons search ───────────────────────────────────────────────
def search_wikimedia(query: str):
    """Return list of {url, descriptionurl, license, artist, title, mime} hits."""
    params = {
        "action":      "query",
        "list":        "search",
        "srsearch":    f"{query} filetype:bitmap",
        "srnamespace": 6,         # File namespace
        "srlimit":     5,
        "format":      "json",
    }
    try:
        sr = http_get_json(WMC_SEARCH_URL, params).get("query", {}).get("search", [])
    except Exception as e:
        print(f"    ! search error: {e}", file=sys.stderr)
        return []
    titles = [r["title"] for r in sr if r.get("title", "").startswith("File:")]
    if not titles:
        return []
    params2 = {
        "action":     "query",
        "titles":     "|".join(titles[:5]),
        "prop":       "imageinfo",
        "iiprop":     "url|extmetadata|size|mime",
        "iiurlwidth": "640",
        "format":     "json",
    }
    try:
        info = http_get_json(WMC_SEARCH_URL, params2).get("query", {}).get("pages", {})
    except Exception as e:
        print(f"    ! imageinfo error: {e}", file=sys.stderr)
        return []
    out = []
    for _pageid, page in info.items():
        ii = (page.get("imageinfo") or [{}])[0]
        if not ii:
            continue
        meta = ii.get("extmetadata", {})
        url = ii.get("thumburl") or ii.get("url")
        if not url:
            continue
        mime = ii.get("mime", "")
        if not mime.startswith("image/"):
            continue
        license_short = (meta.get("LicenseShortName") or {}).get("value", "")
        # Reject non-free licenses
        if license_short and any(
            bad in license_short.lower()
            for bad in ("non-commercial", "fair use", "unknown")
        ):
            continue
        artist = (meta.get("Artist") or {}).get("value", "")
        out.append({
            "url":            url,
            "descriptionurl": ii.get("descriptionurl", ""),
            "license":        license_short or "Wikimedia Commons (see source)",
            "artist":         strip_html(artist)[:200],
            "title":          page.get("title", ""),
            "mime":           mime,
        })
    return out


def fetch_one(query: str, caption: str):
    """Search Commons, download first viable result, return (jpeg_bytes, meta)."""
    cands = search_wikimedia(query)
    for c in cands:
        try:
            data = http_get_bytes(c["url"])
            if len(data) < 1500:
                continue
            return data, c
        except Exception as e:
            print(f"    ! download skipped: {e}", file=sys.stderr)
            continue
    # Fallback: deterministic placeholder
    seed = caption_hash(caption)
    try:
        data = http_get_bytes(PLACEHOLDER_URL.format(seed=seed))
        return data, {
            "url":            PLACEHOLDER_URL.format(seed=seed),
            "descriptionurl": "https://picsum.photos",
            "license":        "Picsum placeholder (CC0 Lorem-Ipsum-of-images)",
            "artist":         "Picsum",
            "title":          "Placeholder",
            "mime":           "image/jpeg",
        }
    except Exception as e:
        print(f"    ! placeholder failed: {e}", file=sys.stderr)
        return None, None


# ── Driver ─────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, default=0,
                    help="Process only N rows (smoke test).")
    ap.add_argument("--force", action="store_true",
                    help="Re-fetch even rows already in the manifest.")
    ap.add_argument("--dry-run", action="store_true",
                    help="Show what would be fetched, but don't download.")
    args = ap.parse_args()

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if IMAGES_INDEX.exists():
        try:
            manifest = json.loads(IMAGES_INDEX.read_text(encoding="utf-8"))
        except Exception:
            manifest = {}

    rows = collect_picture_cue_rows()
    if not rows:
        print("No rows tagged 'picture-cue:yes' found in any staging file.")
        print("To enable picture-cue cards, append 'picture-cue:yes' to the")
        print("Tags column of the rows you want photographs for. Optionally,")
        print("add 'picture-query:\"<custom search>\"' to override the auto-")
        print("derived Wikimedia query.")
        # Still prune any orphans left over from a previous run
        if not args.dry_run and (manifest or any(IMAGES_DIR.glob("*.jpg"))):
            for h in list(manifest.keys()):
                f = IMAGES_DIR / manifest[h].get("file", "")
                if f.exists():
                    f.unlink()
            manifest.clear()
            for f in IMAGES_DIR.glob("*.jpg"):
                f.unlink()
            IMAGES_INDEX.write_text("{}\n", encoding="utf-8")
            print("(pruned all images and reset manifest)")
        return 0

    if args.limit:
        rows = rows[: args.limit]

    print(f"Found {len(rows)} unique picture-cue rows.")
    if args.dry_run:
        for r in rows:
            print(f"  [{r['hash']}] {r['source_file']}:{r['lineno']}  "
                  f"query={r['query']!r}")
            print(f"             caption={r['caption'][:70]!r}")
        return 0

    fetched = skipped = failed = 0
    valid_hashes: set[str] = set()

    for i, r in enumerate(rows, 1):
        h = r["hash"]
        valid_hashes.add(h)
        out_path = IMAGES_DIR / f"{h}.jpg"
        if not args.force and h in manifest and out_path.exists() and out_path.stat().st_size > 0:
            skipped += 1
            continue
        print(f"  [{i:3d}/{len(rows)}] {r['query']!r} → {h}")
        data, meta = fetch_one(r["query"], r["caption"])
        if not data or not meta:
            failed += 1
            continue
        out_path.write_bytes(data)
        manifest[h] = {
            "file":        f"{h}.jpg",
            "caption":     r["caption"],
            "query":       r["query"],
            "license":     meta["license"],
            "attribution": meta["artist"],
            "source":      meta.get("descriptionurl", meta["url"]),
            "mime":        meta["mime"],
            "size":        len(data),
        }
        fetched += 1
        time.sleep(THROTTLE_SECONDS)

    # Prune orphans
    pruned = 0
    for h in list(manifest.keys()):
        if h not in valid_hashes:
            f = IMAGES_DIR / manifest[h].get("file", "")
            if f.exists():
                f.unlink()
            del manifest[h]
            pruned += 1
    for f in IMAGES_DIR.glob("*.jpg"):
        if f.stem not in valid_hashes:
            f.unlink()
            pruned += 1

    IMAGES_INDEX.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    print()
    print(f"\u2713 Done. fetched={fetched}  up-to-date={skipped}  failed={failed}  pruned={pruned}")
    print(f"  Manifest: {IMAGES_INDEX.relative_to(ROOT)}")
    print(f"  Output dir: {IMAGES_DIR.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
