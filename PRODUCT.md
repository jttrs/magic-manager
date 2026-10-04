# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
- **Now:** the owner plus a small circle of friends/playgroup, each managing their own Magic: The Gathering collection. Desktop-first, mobile second.
- **Soon:** the broad MTG collector public. Desktop and phone are both first-class, but for **different feature sets** — e.g. desktop is prioritized for manual checklist ingest and dense set/diff work; phone for on-the-go tasks.

## Product Purpose
One integrated loop over a collector's real cards, in this order of origin:
1. **Collection truth & value** — what I own (exact printing + finish), where each copy came from, what it is worth.
2. **Set completion** — what's missing from a set family, by exact printing and by functional card, and what to buy.
3. **Play-aware use of the collection** — pull in deck recipes, see which cards I own and which are *available* (not pledged to a physically built deck).
4. **Deckbuilding signal** — commander-centric card stats and EDHREC inclusion, comparing cards shared by / differing across commanders.
5. **(Future) Deck composition** in-app.

Success = day-to-day collection work happens in the app, not through agent-run skills. Agents remain for developing and maintaining the scripts and app, not for routine use.

## Positioning
Not any single feature — the **integrated loop** no neighbor offers end to end: exact-printing ground truth with a provenance ledger and product-level attribution (precons, scene boxes, Secret Lair drops, built vs loose), set-family completion intelligence (treatments, chase variants, functional vs printing gaps, multi-store buy-lists), and collection-aware deckbuilding (EDHREC signal joined to what is owned and free).

## Operating Context
- Today: a Python CLI (`uv run mm …`), deterministic `scripts/*.py`, and Claude/Copilot skills drive workflows; SQLite single-file store; Scryfall/MTGJSON/EDHREC/Mana Pool/TCGplayer as external sources via rate-limited cached wrappers.
- Physical rituals: sorting cards at a desk, filling set checklists (XLSX), opening sealed product, building/breaking down precons, shopping carts at Mana Pool/TCGplayer.

## Capabilities and Constraints
- The Python engine (`src/magic_manager/*`) is the single source of truth; delivery layers (CLI, skills, web) are thin adapters. No engine logic reimplemented in the web layer.
- Many operations are long-running (syncs, bulk EDHREC warm, imports, valuations) → background jobs with progress.
- Inventory is a projection of an append-only provenance ledger (V19).
- Printing rules are view-specific: missing-set views show **exact printings**; EDHREC commander views show each card's **chronologically-first standard printing** (no foil/borderless/showcase unless no standard printing exists).
- Undecided: hosting target, scale, auth provider, which operations are admin-only, multi-tenant shared card/price cache details.

## Brand Commitments
- Binding visual constraint (from the owner): **amber-focused palette** replacing the current light-green ("cabbage") accent.
- Binding theming (from the owner): **light and dark modes**. Light = bone-paper guide panels on dark charcoal chrome; Dark = all charcoal stock with bone ink. Follows the OS setting unless overridden in-app.
- Binding structure (from the owner): global header + **full-width top-nav**; the side-panel starts **below** the nav. Diff pools render as horizontally stacked, individually toggleable, divider-resizable panels.
- Components + tokens, centralized and guarded; no hand-rolled or inline UI building.

## Evidence on Hand
- Real collection DB, set-family docs (`docs/sets/*.md`), product-type docs (`docs/product-types.md`), existing HTML galleries (`src/magic_manager/gallery.py`), EDHREC compare JSON contract (`output/edhrec/reports/*.json`).
- No users beyond the owner yet; no testimonials, metrics, or pricing — do not fabricate.

## Product Principles
1. **Ground truth first** — every number traces to owned printings and a ledger event.
2. **Deterministic engine, thin surfaces** — the app relays the engine; it never forks logic.
3. **Exact where it matters, simplified where it helps** — precise printings for ownership/completion, canonical printings for play decisions.
4. **Replace agent toil with direct manipulation** — routine workflows become first-class UI.
5. **Right device for the job** — dense desktop work and focused mobile tasks, each first-class.
