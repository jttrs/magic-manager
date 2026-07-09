---
name: foil-diff
description: Rank a list of cards by the price gap between the simple-foil and nonfoil versions, sorted ascending by percent difference. Excludes fancy foils (surgefoil / etched / textured / rainbowfoil / etc.) and foil-only prints (nothing to compare against). Output is a deterministic markdown table with hyperlinked card/set/CN, nonfoil USD, foil USD, % diff, and $ diff columns. Every price live-fetched via the /cards/collection batch endpoint. Triggers: "/foil-diff", "rank foil vs nonfoil for <X>", "which foils are cheap upgrades", "foil-diff for this cart", "is foil worth it for <X>", "foil premium for missing <X>", or any question about how much extra foil costs for a purchase list.
---

# foil-diff

Deterministic script-driven skill. Claude parses the user's intent to pick the input mode, invokes `scripts/foil_price_diff.py`, and relays the script's markdown table + stderr summary verbatim. No inline computation, no eyeballing prices from a Scryfall page.

## When to use

- **Purchase-list review** — the user has a `queries/missing-<code>-manapool-<ts>.txt` (or the corresponding `-checklist-<ts>.xlsx`) and wants to know which of those cards have foils that aren't a meaningful upgrade cost.
- **Ad-hoc chat list** — the user pastes a Moxfield-style block of cards and asks "which of these should I foil?"
- **Selector output** — the user asks "for everything missing from LTR, which foils are cheap?" — pipe an `mm export moxfield` output into the script.

**Don't** use for:
- **Single-card decisions** — the user can eyeball a Scryfall page for one card. Only run this skill for lists ≥ ~5 cards where the ranking output is genuinely more efficient.
- **Fancy-foil vs nonfoil questions** — this skill deliberately excludes surgefoil, etched, textured, rainbowfoil, etc. (anything mapping to the `ff` treatment keyword). Those are separate premium products, not a "should I foil this card" question. If the user asks about fancy-foil pricing specifically, address that manually via `mm scryfall <query>`.
- **Foil-only prints** — the script excludes any print whose `.finishes` is `["foil"]` because there's no nonfoil price to compare. These are counted in the stderr summary but not in the table.

## The canonical recipe

```bash
uv run python scripts/foil_price_diff.py [--file PATH]
```

Three input modes; pick based on what the user provided.

### Mode A: user references a `queries/` file

```bash
uv run python scripts/foil_price_diff.py --file queries/missing-ltr-manapool-2026-07-08-004128.txt
# or
uv run python scripts/foil_price_diff.py --file queries/missing-ltr-checklist-2026-07-08-004128.xlsx
```

The script auto-detects `.txt` (Moxfield-style parse) vs `.xlsx` (reads the `set` + `collector_number` columns from the first data sheet). Works for both master-list checklists and missing-set results.

### Mode B: user pastes a chat block

```bash
printf '%s' "$BLOCK" | uv run python scripts/foil_price_diff.py
```

Where `$BLOCK` is the user's Moxfield-style text like:

```
1 Nazgûl (LTR) 100
1 Cid, Timeless Artificer (FIN) 216
1 Ringwraiths (LTR) 385
```

The `1 ` quantity prefix and the `*F*` foil marker are both **ignored** by the script — foil-diff is always evaluated per-print, both finishes, regardless of what the user typed.

### Mode C: user references a selector

Run the export first, pipe to the script:

```bash
uv run mm export moxfield 'set:ltr+related missing' | uv run python scripts/foil_price_diff.py
```

`mm export moxfield` emits the same Moxfield-style block that Mode B expects.

## Output shape

The script writes a markdown table to stdout, sorted ascending by percent difference:

```
| Card | Nonfoil | Foil | % diff | $ diff |
|---|---:|---:|---:|---:|
| [Nazgûl (LTR) 338](https://scryfall.com/card/ltr/338) | $24.23 | $26.99 | +11.4% | +$2.76 |
| [Cid, Timeless Artificer (FIN) 407](https://scryfall.com/card/fin/407) | $2.60 | $5.83 | +124.2% | +$3.23 |
...
```

And a one-line summary to stderr:

```
Ranked N cards. Excluded: fancy-foil=X, foil-only=Y, nonfoil-only=Z, unpriced=W, unresolved=V, filtered=F.
```

**Relay both.** Print the summary line to the user beneath the table so they can see the exclusion counts. Don't reformat the table — the script's Markdown is the canonical shape.

## Filter flags

The script supports optional post-sort filters. Sort order is stable; filters only trim rows. All bounds are inclusive on the "keep" side.

| Flag | Effect |
|---|---|
| `--min-pct N` / `--max-pct N` | Drop rows whose percent-diff is below / above N (in percent, e.g. `--max-pct 0` keeps only rows where foil is cheaper than nonfoil). |
| `--min-raw N` / `--max-raw N` | Drop rows whose dollar-diff is below / above N (in USD, e.g. `--max-raw 10` drops rows where the foil upgrade costs more than $10). |
| `--drop-expensive PCT:RAW` | Compound filter: drop rows where BOTH `%-diff > PCT` AND `$-diff >= RAW`. This is the "cheap-upgrade lens" — keeps cheap-but-high-multiple rows like $0.30→$2.36 (+594%/+$2.02, art-price signal) while dropping expensive-and-high-multiple rows like $195→$423 (+117%/+$228, real cost). |

**When to reach for each:**
- "Foil is a free upgrade" → `--max-pct 0`.
- "Cap the absolute foil premium" → `--max-raw 10` (never pay more than $10 extra per card).
- "Cheap-upgrade ranking, but ignore the low-cost curiosity spikes" → `--min-raw 1 --drop-expensive 100:10`.
- "The user's canonical 'sensible foils' filter" → `--drop-expensive 100:10` (mirrors the LTR walkthrough).

Filters apply **after** the fancy-foil / foil-only / nonfoil-only / unpriced buckets, and are reported separately as `filtered=N` in the stderr summary.

## Determinism guarantees

- **Sort key** is `(round(pct, 4), name, set, cn_int_or_lex)`. Rounding percent-diff to 4 decimals before compare stabilizes ordering across Scryfall's 24h cache windows when prices flip by pennies.
- **URLs** are hand-constructed `https://scryfall.com/card/<set>/<cn>` — no `?utm_source=api` query string, no slug drift.
- **Bucket precedence** is fixed: fancy-foil → foil-only → nonfoil-only → unpriced → included. Each card lands in exactly one bucket; the summary counts are non-overlapping.
- **Live prices** via `/cards/collection` (batch 75 per request), rate-limited and 24h-cached at the wrapper layer. Same input → same output within a day.

## Guardrails

- Read-only: no DB writes, no artifact files under `queries/`.
- Never fails on unresolved rows — one typo doesn't nuke a 165-row run. Unresolved cards are counted in the stderr summary.
- Empty input → exit 0 with `Ranked 0 cards. …` on stderr.
- The script never touches the DB. It re-fetches prices from Scryfall on every invocation (subject to the 24h wrapper cache).

## Cross-references

- `scripts/foil_price_diff.py` — the script this skill drives.
- `src/magic_manager/parsers.py:CARD_RE` — the Moxfield-style parse regex the script reuses.
- `src/magic_manager/scryfall.py:collection()` — the batch price fetch.
- `src/magic_manager/treatments.py:compute_treatment()` — the `ff` discriminator used for the fancy-foil filter.
- [[missing-from-set]] — produces the `queries/missing-*` files that this skill most often runs against.
- [[bulk-add]] — the natural upstream skill for "I just decided which foils to buy, now let me add them to inventory."
