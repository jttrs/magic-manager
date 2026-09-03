---
name: jumpstart-reference
description: Generate the durable two-sheet XLSX reference that tells apart Jumpstart pack VERSIONS (Angels (1) vs Angels (2), …) and shows what's in each — a `packs` sheet (one row per variant: set/theme/color/top_card/value/count) and a `cards` sheet (one row per distinct card: color/value/count/rarity/collector_number). Optional set-code arg, else all Jumpstart sets. Script-driven via `scripts/jumpstart_reference.py`; writes the committed `reference/jumpstart-versions.xlsx`. Triggers: "/jumpstart-reference", "which version of a jumpstart pack is this", "jumpstart versions reference", "what's in Angels 1 vs Angels 2", "jumpstart pack reference sheet", "regenerate the jumpstart reference".
---

# jumpstart-reference

Deterministic, script-driven reference generator. Claude invokes
`scripts/jumpstart_reference.py [set_code]` and relays the stdout summary + the output path. This
is a **reference doc** (identify a version, see its contents), not a buy list and not ingestible.

## When to use

- "Which version of this Jumpstart pack do I have — Angels (1) or (2)?" / "what's in each version?"
  / "regenerate the jumpstart versions reference."

**Don't** use for:
- A shopping list — that's [[jumpstart-missing]] (whole packs) or [[jumpstart-buildable]] (cards to
  build every theme).
- Cataloging packs you opened — that's [[generate-jumpstart-checklist]] (ingestible).

## The canonical recipe

```bash
uv run python scripts/jumpstart_reference.py            # ALL Jumpstart sets (the committed snapshot)
uv run python scripts/jumpstart_reference.py <set_code>  # one set (e.g. j25)
uv run python scripts/jumpstart_reference.py --out <path>  # custom output path
```

`set_code` is optional — omit it to (re)build the full all-sets reference. Relay the stdout
summary (pack rows + card rows across N sets) and the output path.

## Output shape

`reference/jumpstart-versions.xlsx` (committed; overwritten in place) with two sheets:
- **packs** — `set, theme, color, top_card, top_card_usd, card_count, usd_total`; one row per
  variant. Sorted **set → color → theme**.
- **cards** — `set, theme, color, card_name, card_value, count, rarity, collector_number`; one row
  per distinct card in a pack. Sorted **set → theme → rarity (mythic→…) → collector number**.

Color is the deck/card letter form (actual WUBRG letters, no `M` collapse; colorless → `C`).

## Determinism guarantees

- Fixed sort keys above; color rank C→W→U→B→R→G then a trailing multicolor block.
- Card value = the card's shipped finish (foil if the pack ships it foil, else nonfoil), matching
  the pack rollup basis. Prices come from the local `cards` table (the script syncs each set's
  family first). Same-day re-runs differ only by live price drift in the `$` columns.

## Guardrails

- Read-only against inventory; writes the reference XLSX (default `reference/`, committed).
- Exit 0 on success; exit 2 on bad set code / no Jumpstart variants.

## Not to be confused with

- [[jumpstart-buildable]] — buy list for the cards to make every theme buildable. This is a
  read-only reference, not a shopping list.
- [[jumpstart-missing]] — buy list for whole packs you don't own.
- [[generate-jumpstart-checklist]] — ingestible checklist for packs you opened.

## Cross-references

- `scripts/jumpstart_reference.py` — the script this skill drives.
- `src/magic_manager/mtgjson.py` (`deck_list`, `jumpstart_variants`, `deck`), `sets.py`
  (`resolve`/`sync`, `_jumpstart_variant_summary`), `util.py` (`format_color_identity`,
  `cn_sort_key`, `apply_base_font_size`).
- [[foil-diff]] / [[secret-lair-value]] / [[set-status]] — sibling deterministic script-driven skills.
