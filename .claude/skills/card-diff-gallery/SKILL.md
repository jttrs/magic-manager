---
name: card-diff-gallery
description: "Image-first HTML gallery of the three card-diff pools (missing printing, missing functional, variant-chase) across one or more Magic set families — a visual, filterable alternative to card-diff's text tables. Writes a single self-contained local HTML file (no server) with family + pool filter chips, a name search box, and a value/name sort control; card images lazy-load from Scryfall's CDN. Triggers: \"card diff gallery\", \"html view of missing cards\", \"visual missing-set review\", \"scan missing cards as images\", \"card gallery by set family\", \"show me what I'm missing as pictures\"."
---

# card-diff-gallery

Deterministic, script-driven. Claude invokes
`uv run python scripts/card_diff_html.py [codes...] [--pool printing|functional|variant-chase|all]`
and relays the written `file://` path. No inline computation — the script
reuses `magic_manager.card_diff` (the same engine behind `mm query card-diff`)
for all pool data, and does one targeted `cards` table lookup for
`image_uri`. Opens a local HTML gallery of the three card-diff pools per
family, image-first, filterable by family + pool. No server.

## Modes

- **No codes → every owned+configured family.** Runs `card_diff.collection_diff()`,
  which does a live price fetch across the whole collection — expect ~2-4
  minutes. Use this for "give me a gallery of everything I'm missing."
- **One or more codes → just those families.** Runs `card_diff.family_diff(code)`
  per code (any member or anchor); unresolvable/unconfigured codes are skipped
  with a stderr warning, not a hard failure, unless NONE resolve (exit 2).

## The three pools (same definitions as [[card-diff]])

- **printing** — every art/frame variant not owned.
- **functional** — mechanically-unique cards (by `oracle_id`) owned in ZERO printings.
- **variant-chase** — printing-missing rows whose card you already own elsewhere
  in the family (the borderless/alt-art/fancy-foil chase).

`--pool` narrows which pool(s) render (default `all`); the in-page pool chips
let you toggle visibility after the fact without re-running the script.

## Output shape

ONE file, `output/card-diff/reports/card-diff-gallery-<ts>.html`:

- A collapsible left **sidebar** with checkbox filters for **pool** and
  **family** (each with Select All/Clear All), a **search box** (substring
  match on card name), a **sort** dropdown (value desc/asc, name A→Z,
  collector number low→high), and an **Export (shown)** section with
  **Copy ManaPool list** / **Copy TCGplayer list** buttons — each copies a
  paste-ready buy-list of exactly the tiles CURRENTLY DISPLAYED (post-filter)
  to the clipboard, in the canonical `exports` format (ManaPool `*F*` foil
  marker; TCGplayer `[SET] cn` with treatment suffixes). Works from a `file://`
  page (clipboard API with an execCommand fallback).
- One section per family (owned $ + each pool's count·$ in the header),
  containing a responsive image grid — one tile PER UNIQUE PRINTING (deduped
  across pools): the Scryfall image (lazy-loaded `<img>`, clickable through
  to the card's Scryfall page), a segmented underline bar showing which
  pool(s) it belongs to, and a caption line (name, set, collector number,
  rarity, finish, USD, pool membership).
- Cards with no `image_uri` (shouldn't happen — the local `cards` table has
  it for 100% of rows, but guarded) render a text-only tile instead of a
  broken image.
- Fully self-contained: inline CSS + a small inline vanilla-JS filter/sort —
  no CDN, no server. **Images themselves DO need network** (they load from
  `cards.scryfall.io` at browser render time); offline, tiles with no cached
  image degrade to a broken-image icon but the page itself still works.

## When to use

- "Show me my missing cards as pictures" / "visual review of what I'm missing
  from `<set>`" / "card gallery across my families."
- Scanning a large pool (e.g. variant-chase alt-arts) visually is faster than
  reading a Scryfall-link table — use this instead of [[card-diff]] when the
  user wants to actually SEE the cards.

**Don't** use for:
- The text/table report with $ figures and Scryfall URL chunks → [[card-diff]]
  (`mm query card-diff`) — this gallery's companion, same underlying data.
- The canonical buy-list workflow (XLSX + ManaPool/TCGplayer bulk-add files)
  → [[missing-from-set]] — this gallery writes no buy-list artifacts.
- Family topology / owned-$ / precon counts / characterization status →
  [[set-status]].

## Guardrails

- **Read-only.** No DB writes; the only write is the one HTML artifact under
  `output/card-diff/reports/` (pruned by [[cleanup-queries]]).
- **No network from Python.** All pricing/card data is already on the
  `FamilyDiff`/`CardDiffPool` rows the engine returns; images are fetched by
  the BROWSER from Scryfall's CDN, not by this script.
- An unresolvable/unconfigured named code is skipped with a stderr warning;
  exit 2 only if every given code fails to resolve.

## Cross-references

- `scripts/card_diff_html.py` — the script this skill drives.
- `src/magic_manager/card_diff.py` — the engine (`family_diff`, `collection_diff`),
  shared with [[card-diff]].
- `src/magic_manager/util.py` — `output_dir`, `fmt_usd`, `cn_sort_key`.
- [[card-diff]] — the text-table sibling (same data, Scryfall URL chunks + $
  figures, no images, no file artifact).
- [[missing-from-set]] — the buy-list workflow (XLSX + bulk-add files).
- [[set-status]] — family topology + both missing figures as part of a broader status block.
