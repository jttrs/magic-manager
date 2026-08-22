---
name: cart-check
description: Audit a live Mana Pool cart against your collection and a set family — three atomic checks in one pass. (1) OWNED — cart lines you already own (redundant, remove them); (2) MISSING — set-family gaps NOT in the cart (should-add); (3) OVERPAY — lines priced over true Scryfall/TCG market. Deterministic, well-formatted markdown tables relayed to chat, with the full uncapped report written to queries/. Triggers "/cart-check", "audit my manapool cart", "what can I remove from my cart", "what am I still missing from my cart for <set>", "is my cart complete / am I overpaying", "check my cart against my collection".
---

# cart-check

Deterministic, script-driven cart audit. Claude invokes `scripts/manapool_cart_check.py`, then **relays the script's stdout markdown tables verbatim into chat** and surfaces the `file://` link to the full report. No inline computation, no eyeballing prices or ownership — the script is the single source of truth.

This is the superset of the `price-check` skill's `manapool` mode: `price-check` answers *only* "am I overpaying"; `cart-check` also answers "what can I remove" and "what am I still missing."

## When to use

- **Cart cleanup** — "what can I remove from my cart?" → the `owned` check flags redundant lines.
- **Completeness** — "what am I still missing from <set> for my cart?" → the `missing` check lists family gaps not yet in the cart.
- **Sanity/price** — "am I overpaying?" / "is this cart a good deal?" → the `overpay` check (same comparison as `price-check`).
- **Full audit** — "audit my cart" / "check my cart" → run all three (default).

**Don't** use for:
- **A pure overpay check with no set context** — that's the `price-check` skill's two-script pipeline (`manapool_cart.py | manapool_price_check.py`); it needs no `--set`.
- **Non-Mana-Pool carts** — this drives the Mana Pool cart fetch specifically. TCGplayer/other markets aren't wired up.
- **Adding cards to inventory** — that's [[import-list]] / [[bulk-add]] / [[import-precon]].

## The canonical recipe

```bash
uv run python scripts/manapool_cart_check.py --set <CODE> --check all
```

That's the whole happy path: it fetches the live cart (headless, else stdin), does ONE cart→card mapping pass, runs the requested checks, prints the concise chat report to stdout, and writes the full report to `queries/cart-check-<anchor>-<ts>.md`.

**Relay the entire stdout verbatim in your chat reply** so the markdown renders as tables, and include the `🧾 Full cart check … (file://…)` link the script prints. Do not re-render, summarize-instead-of-showing, or paste the file's full overpay table inline — the chat report is already the right shape.

## Flags

| Flag | Effect |
|---|---|
| `--set CODE` | Set-family anchor (e.g. `tla`). **Required** for the `missing` check (and thus for `--check all`). Scopes `owned`/`overpay` to `set:CODE+related`; out-of-family cart lines are counted + reported on stderr, never misclassified. |
| `--check owned\|missing\|overpay\|all` | Which check(s) to run. Default `all`. Each is atomic — run just one when that's all the user asked. |
| `--file PATH` / `--file -` | Read cart JSON from a file / stdin (bookmarklet output) instead of the live headless fetch. |
| `--method headless\|bookmarklet` | Force the cart fetch path. Default: try headless, else read stdin. |
| `--over-market-pct N` | ⚠️ flag threshold for the overpay check: % over Scryfall market. Default 50. |
| `--treatment-class CLASS` | Treatment class for the `missing` check (forwarded to `missing.missing_printings`). Default `preferred`. |

## The three checks

| Check | Answers | How |
|---|---|---|
| `owned` | Cart lines you **already own** (redundant — remove) | **Finish-level**: matched on (scryfall_id, finish), so a *foil* cart line isn't flagged just because you own the nonfoil. Reads local `inventory`. |
| `missing` | Family gaps **not in the cart** (should-add) | Reuses the missing-set union (`magic_manager.missing.missing_printings`) minus cart membership on (scryfall_id, finish). **Requires `--set`.** |
| `overpay` | Priced over true market | Reuses `manapool_common.overpay_rows` (same comparison as the `price-check` skill), live Scryfall/TCG market via `/cards/collection`. |

All three run off a **single cart→card mapping pass** (`map_cart`): each cart line's mtgjson uuid → ManaPool product → scryfall_id, the join key shared by every check.

## Output shape

STDOUT is a concise, chat-ready markdown report — relay it verbatim:

1. `## Summary` — a metrics table (set family, cart lines, owned count·$, missing count·$, overpay flagged·$).
2. `## Owned` — full list, row-capped at 40 with a `_+N more (see file)_` marker beyond that; closed by a bold `Total (N)` row.
3. `## Missing` — same shape.
4. `## Overpay (flagged)` — **only** lines ≥ threshold; the Total row reads `N/total` so the full denominator is visible.
5. A `🧾 Full cart check (N priced lines): [queries/cart-check-<anchor>-<ts>.md](file://…)` link — the file holds the **complete, uncapped** overpay table.

STDERR carries commentary (family scoping, skipped out-of-family / unmapped / no-market lines). Surface it briefly beneath the tables if it's non-trivial; don't let it clutter the report.

Every table is data-only (no prose, empty sections still emit header + `Total (0)`), fixed columns, fixed sort — so same-day re-runs are byte-identical.

## Determinism guarantees

- **One mapping pass**, `_mp_product` cached 24h at the wrapper — same cart, same day → identical output.
- **Fixed sorts**: owned/missing by `(set, cn, finish)`; overpay by `%-over` descending.
- **Fixed money** (`$X.XX`), hand-built `https://scryfall.com/card/<set>/<cn>` links (no query-string drift).
- **Chat report and file** are both deterministic; the file is the uncapped superset of the chat overpay table.

## Guardrails

- **Read-only**: never writes the DB or modifies the cart. The only write is the `queries/cart-check-*.md` report artifact (ephemeral; pruned by [[cleanup-queries]]).
- **Secrets only from `.env`** (gitignored): `MANAPOOL_*`. The headless session JWT is held in memory only — never logged or written.
- **Sanctioned API via the rate-limited wrapper** (`manapool-search/manapool.sh`); the Supabase cart fetch lives in `scripts/manapool_cart.py`, which handles the short-lived JWT correctly.
- **Undocumented-backend caveat**: the headless cart path reads Mana Pool's Supabase backend, subject to change. If it breaks, fall back to the bookmarklet (`--file -`), same as the `price-check` skill.

## Cross-references

- `scripts/manapool_cart_check.py` — the script this skill drives.
- `scripts/manapool_common.py` — shared cart plumbing (`load_cart`, `map_cart`, `overpay_rows`).
- `src/magic_manager/missing.py:missing_printings` — the missing-set union the `missing` check reuses.
- [[price-check]] — the overpay-only sibling (two-script pipeline, no `--set` needed).
- [[missing-from-set]] — the family buy-list this cart is usually built from.
- [[foil-diff]] — sibling deterministic script-driven price skill.
- [[cleanup-queries]] — prunes the `queries/cart-check-*.md` artifacts this skill writes.
