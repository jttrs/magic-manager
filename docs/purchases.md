# Purchases — store order history with what you paid (V34)

Internal while in beta: feature flag `purchases` (plus `companion`). Owner ideas this delivers: the
pinned "Order history → Purchase history" follow-up (`docs/browser-companion.md`) and PR #109's
"what you paid".

## What it does

1. **Read** — Collection → Purchase history → *Read my orders* (header action). Pick a store; the browser companion
   reads your **order list** in your own browser (click-to-read, you approve in its window). The app
   marks each order: not read / read, not added / partly added / in your collection / recorded only.
   Tick orders (or *Read all*); the companion reads those orders' lines and, after you approve, the
   app stores each as a **purchase** (`purchases` + `purchase_lines`, deduped by store + order
   number). Reading never changes your collection.
2. **Assign** — open an order. Per line, choose how many copies to **match** to copies you already
   own (net-zero: only their *source* moves to the order) and how many to **add** as new copies.
   *Match to cards I own* and *Add all as new* fill the counts; *Save to collection* writes them.
3. **See** — store orders live in Purchase history (no separate tab): orders not fully added are
   pinned under **Needs review** with Paid / Worth today / gain or loss; an applied order is one
   **Store order** timeline entry (its ledger event, with what you paid); the sheet summary carries
   the total for all orders.

## Engine (`src/magic_manager/purchases.py`)

- `save(orders)` — resolves each single line to an exact printing (Mana Pool: the Scryfall id in
  its image link, fetched + upserted via `addcards.ensure_printings` when the catalog lacks it;
  TCGplayer: the product id → `scryfall.by_tcgplayer_id` (`/cards/tcgplayer/<id>`); else set code +
  collector number). Re-reading an order you haven't assigned anything from replaces it; one you
  have is skipped. Never touches inventory.
- `review(id)` — per line: owned now, **matchable** (copies held by events whose source is
  *unknown* or *singles* — never another purchase or a product; `provenance._held`'s LIFO netting so
  a removed copy is never matched), remaining.
- `apply(id, decisions)` — ONE `purchase` ingest event per order (label
  `purchase:<store>:<order>`, dated at the order date). Adds → `inventory.inventory_add(ingest_id=)`;
  matches → `ingest.reattribute` (the seam product true-up uses; unknown buckets first, then singles
  newest first). All-or-nothing; `inventory == SUM(delta)` is checked before commit. A fully
  assigned order is refused (`AlreadyApplied`, HTTP 409).
- `forget(id)` — delete a stored order nothing was assigned from.
- `provenance`: method `purchase` → source kind `purchase` ("Mana Pool order #…"); history kind
  `purchase` carries `purchase_id` + `paid_usd` (unit price × copies still held).

Prices: `unit_price_cents` per line as the store lists it; the order's subtotal / shipping / tax /
fees / store credit / total as the store shows them. *Worth today* compares the same lines at local
prices (lines with no price today are left out of both sides).

## Schema (V34)

`ingest_events.method` widened with `purchase` (copy-rebuild, FK-off, ids preserved — like V26);
then `purchases` (UNIQUE store + store_order_id, `ingest_id` once applied) and `purchase_lines`
(kind single|sealed|other, finish, `scryfall_id` with no FK to the `cards` cache, quantity, unit
price, `matched` / `added`, `CHECK (matched + added <= quantity)`). Both tables are **precious**
(rehearse_migration, post_merge_upgrade OWNERSHIP, undo USER_TABLES).

## Verification

The owner's rule: nothing unverified reaches users as if it were verified. Each store carries a
level (`purchases.STORE_VERIFICATION`, shown in the app wherever you pick a store or review an
order), and a line kind a store isn't verified for is stored as `other` — recorded with its price,
**never added** to a collection (`purchases.line_kind_allowed`).

| Store | Verified (2026-10-10, against the owner's real pages) | Not verified |
|---|---|---|
| Mana Pool — **verified** | **Live, end to end**: the real unpacked extension (bridge → worker → its own tab → approval window → Send) read the owner's order list (5 orders) and all 5 orders (496 lines, 0 warnings, every single's printing found). Saved pages: two full orders resolved and applied (match + add) on a copy of the real DB with 0 ledger drift. | Pagination of the order list (the owner has 5 orders — one page); refunded-item rows; whether the item list is capped (one order shows exactly 200 lines). |
| TCGplayer — **partly verified** | First page of Order History (10 orders, items inline): all orders and lines read, all 22 singles resolved via product id, item sums equal each order's subtotal. | Following the pager to page 2+ (`?PageNumber=N`); other years (pick the year on TCGplayer's page — the companion never submits its forms). Sign-in reading (hCaptcha blocks automated sign-in, so captured from the owner's own Chrome). |
| Card Kingdom — **partly verified** | Order list (4 orders) and one invoice (a sealed product). | **Single cards** — the owner has no single-card orders, so every non-product line is `other` (recorded, never added). |

Known gap seen on real data: Mana Pool's item list includes **replacement** items, so the item sum
can differ from the store's subtotal (3 of 5 real orders: e.g. $3,305.32 listed vs $3,189.82
subtotal; $2,231.45 vs $1,918.34). Per-line prices are as the store lists them; the app shows both
totals and says so.

The live end-to-end run (`livecheck`) was Mana Pool only. TCGplayer and Card Kingdom order flows in
the real extension have **not** been run live (their sign-in couldn't be automated); their readers
are pinned against pages the owner saved.

## Tests

`web/e2e/companion-order-readers.spec.ts` (readers in Chromium against de-personalised saved pages
→ `tests/fixtures/companion/*order*.expected.json`) → `tests/test_companion_orders.py` (strict API
models → engine) and `tests/test_purchases.py` (engine + ledger invariant).
