# Design brief — adding cards in Collection (replaces the XLSX checklist)

Status: **implemented** (2026-11-27; shaped with impeccable `shape`). Read with DESIGN.md (§ Collection sidebar, § Bulk modify counts, § CardTile and CardRow).

## 1. Job and audience

- **Who:** the owner (later: any collector) at the desk with a stack of cards, a fresh booster or a binder page, the Collection view open. Mode: **Operate**. Desktop first; phone is a real second (tapping in cards from a pack on the couch).
- **Two speeds of the same job:**
  - *Ad hoc* — "I just pulled these 6 cards": find the card in the grid, tap, tap, tap, confirm.
  - *Checklist* — "I'm cataloguing a whole set": walk a family printing by printing. Today that's the XLSX `master-list → fill → ingest` ritual; in the app it's **Bulk modify counts**.
- **Blocker today:** the Set families picker only lists families you already own, so a new family can't be opened, browsed or filled. And the only way to add from the grid is the Add cards modal, which makes you search again for a card that's already on screen.

## 2. Outcome and proof

- Success = a new family opened from the picker, 20 cards tapped in from the grid, one **Add 23 copies** press, one ledger event, the grid updated. No modal, no file.
- Product truth this keeps: exact printing + finish per tap; nothing is written until you confirm; one confirm = one ingest event (Ground truth first, PRODUCT.md).

## 3. Direction — one draft, two ways to fill it

**The thesis:** the grid's tap-to-add and Bulk modify counts' table are two inputs on **the same staged draft** (`useChecklist`, `mm.collection.checklist`, `sets.apply_counts`). A tap writes the cell `owned + pending` with `expected = owned`; the table writes the cell directly. Same running status line, same Discard / Save, same stale-count protection, same leave-guard. No second pending model, no new engine for the write path (DRY rule 2).

- What you see while staging is the card's own **Holdings caption** turning into the control — the count you read is the thing you press. Nothing overlays the art (DESIGN.md rule kept).
- The commit lives where the draft status already lives: the in-sheet status line, promoted to a **sticky ruled bar** at the foot of the sheet while the draft is non-empty.

## 4. Scope and boundaries

In scope:
1. **Set families picker — "families you don't own" switch** (off by default).
2. **Tally controls** on every card in grid and list (nonfoil + foil), click = +1, press-and-hold = amount picker.
3. **Pending bar** shared with Bulk modify counts.
4. Behaviour when the scope is a family you own nothing from.

Untouched: the Add cards modal (still the route for *search across everything*, decklists, products, imports), Bulk modify counts' table and keys, sort/arrange controls, the mark toggle and inspector.

Anti-goals: a cart/tray drawer that floats over the grid; a +/− stepper on every tile (doubles the noise of a price guide); removals by tap (setting a count *down* stays in Bulk modify counts, where it's deliberate); amber used to decorate pending cards beyond the existing highlighter.

## 5. The pieces

### 5.1 Set families picker

Inside the `MultiSelect` popover, between the filter box and the option list, one ruled row:

```
[ Filter…                         ]
[☐] Include families you don't own          0 selected
─────────────────────────────────────────
 Aetherdrift            1,204
 Assassin's Creed         88
 …
```

- `Check` + label *Include families you don't own*. **Off by default.** Remembered in this browser (`localStorage mm.collection.unownedFamilies`), not the URL — it changes what the picker *offers*, not what the sheet shows.
- On: the list gains a second group, **Not in your collection**, every top-level paper family newest first (`sets.paper_families()`, the list Explore's rankings already use), each with its year as muted meta instead of a count. Owned families stay first and keep their counts.
- A chosen unowned family stays pinned at the top (existing "selected first" rule) even after the switch is turned off, so the trigger never names something the list hides.
- **Filter falls through:** with the switch off, a filter that matches no owned family shows `No family you own matches "edge"` + a link button *Search all families (2 match)* that turns the switch on.
- Bulk buttons (*Select all / Clear all*) act on owned families only, even with the switch on — selecting 140 unowned families is never what *Select all* means. (Mode `scope` gains that rule.)

**Engine/API:** `GET /api/collection/families?include=unowned` → `FamilyOption` gains `owned: bool` and `year`. Owned list unchanged.

### 5.2 Opening a family you own nothing from

- **Catalog not read yet** (no printings synced locally): the sheet shows an `EmptyNote` — *Edge of Eternities isn't in your catalog yet* · primary *Read this family* (a `sets.sync` job with progress: `Reading Edge of Eternities · 3 of 7 sets`). Hosted: this is a `catalog`-scope job (admins only today) — see open decision D1.
- **Read, but you own none and Ownership is `Owned` only:** don't show a blank sheet. Picking a family you own nothing from turns on `Missing` in the same URL update (announced once in the status line: *Showing missing cards — you don't own any from Edge of Eternities yet*). Back/forward restore the old filter.

### 5.3 Tally controls (grid + list)

The Holdings caption line today: `[mark] ×2  ✦×1` or `[mark] MISSING`. It becomes:

```
grid tile caption           [☰]  [＋ 2]  [✦＋ 1]
pending                      [☰]  [＋ 2 +3] [✦＋ 1]      ← +3 accent-ink, caption takes the highlighter
missing printing            [☰]  [＋ —]  [✦＋ —]          ← MISSING moves to the art tone (already dimmed)
no foil printing            [☰]  [＋ 0]                    ← ✦ button absent, not disabled
```

- Two compact `IconAction`-family buttons (new `TallyButton` control, so `noHandRolled` stays green): plus glyph + owned count in tabular figures; foil uses the existing `✦` mark. Etched counts as foil (as everywhere else).
- **Click / tap / Enter / Space = +1 pending.** Pending shows as a signed accent-ink `+N` after the owned count — the same mark the count table uses. The whole caption takes the `highlighter` (an edited line in the table does too), so a pending card is findable while scrolling.
- **Press-and-hold (≥ 400 ms) / long-press on touch / Shift+Enter / context-menu key = amount picker.** While held, a 2px amber underline grows across the button (amber = progress; `prefers-reduced-motion`: no growth, opens at the threshold). Releasing early is a click. The browser's own long-press menu is suppressed on these buttons only.
- **Amount picker** (`Popover`, `menuPanelClass`, anchored to the button):
  ```
  NONFOIL · Sheoldred, the Apocalypse
  Add  [ − ][  3  ][ + ]        quick: 1  2  3  4
  2 owned → 5                    $78.40 at market
  [ Remove from draft ]                    [ Add 3 ]
  ```
  The number is the **pending amount** (a delta), not a total — the grid is for adding; setting totals is Bulk modify counts. Field is focused + selected on open; typing replaces; Enter applies, Esc closes unchanged. `−` floors at 0; 0 + Enter = remove from draft. `4` is the quick-chip ceiling (a playset). Over 99 asks nothing — it's a number field.
- **Shift-click = −1 pending** (undo a mis-tap without the picker). Never goes below 0 pending; never removes owned copies.
- **List view:** the same two buttons sit in the row's right edge, aligned as columns (`Nonfoil · Foil ✦`) so a list reads like the count table, compact.
- **A11y:** accessible name `Add one nonfoil — 2 owned, 3 to add`; the picker is a labelled dialog; the pending bar is the `aria-live="polite"` region (`3 to add · Sheoldred, nonfoil`) — tiles don't announce on their own.

### 5.4 The pending bar

The Bulk modify counts status line, promoted to a sticky bar at the sheet's foot whenever the draft is non-empty (grid, list or table — it's one draft):

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 To add · 14 printings · 23 copies · +$61.20 at market (2 unpriced)   Review   Discard   [ Add 23 copies ]
```

- 2px `rule-strong` top edge on paper; no shadow beyond the sheet's own (Ruled-First Rule).
- Primary label follows the draft: adds only → **Add N copies**; any lowered count (from the table) → **Save N changes**.
- **Review** filters the sheet to pending cards (a temporary filter chip in the status line, *Showing 14 pending · Show all*) — the honest checkout without a new surface.
- **Discard** confirms `Discard 23 copies?` (existing copy rule).
- After saving: the bar collapses to the highlighter status `Added 23 copies · 14 printings` with *Undo* (the session undo already covers it) for 8 s, then goes.
- Everything else is inherited unchanged: draft survives reloads and family switches, *Leave with unsaved counts?*, built-deck floor, stale flags with *Keep all my counts*.

### 5.5 Bulk modify counts (checklist mode) — what changes

Nothing in its table or keys. It inherits the unowned-families switch (so a new family can be filled printing by printing), and its status line becomes the pending bar. This is the XLSX replacement; the tally buttons are the ad hoc path into the same draft.

## 6. States and ranges

| State | Shape |
|---|---|
| Family picker | owned 5–60 families; all paper families ~300 |
| Family size | 80 (SLD-ish child) – 1,200+ printings (FIN family); grid is virtualized already |
| Draft | 1 tap – ~1,500 cells (whole set by table) |
| Catalog not read | EmptyNote + *Read this family* job |
| Read, own none | Missing auto-on, one status line |
| Pending | caption highlighter + `+N`; bar visible |
| Saving | buttons stay live; taps during save rebase on the saved count (existing behaviour) |
| Stale on save | existing flagged-cell flow; tiles of flagged cards show the amber ring like table cells |
| Hosted member, unsynced family | D1 |

## 7. Constraints and open decisions

- **D1 — who may read a new family's catalog when hosted.** `sets.sync` is catalog-scope (admins only). Options: let members trigger a read of a *single family* (rate-limited, `scope="catalog"` exception), or show *Ask an admin to read this family*. Recommend: allow a single-family read for members (it's the only way they can catalogue).
- **D2 — provenance of grid adds.** `apply_counts` writes a `checklist` (replace-mode) event, which History can't revert. An adds-only draft should post as an **additive** event (method `adhoc`, label `web:collection · <families>`) so *Revert this import* works; mixed drafts stay `checklist`. Engine change in `sets.apply_counts` (or route adds-only drafts to `addcards.commit`) — decide before build.
- **D3 — tally buttons always visible, or behind an "Add" toggle in the header strip?** Recommend always visible: the caption already carries holdings, and staging makes a mis-tap cheap. If the price-guide reading gets noisy at 120px tiles, fall back to showing them on hover/focus on pointer devices (always on touch).
- Reuse: `useChecklist`/`core/checklist` (draft), `MultiSelect` (+ a `footerToggle`/`header` slot), `Popover` + `menuPanelClass`, `TextInput`, `IconAction` styles, `EmptyNote`, job chassis. New control: `TallyButton` (+ a tiny `usePressHold` hook in `app/`).
- Tests to add: press-hold vs click timing (vitest with fake timers), picker keyboard, the families `include=unowned` route, an e2e that opens an unowned family, taps three cards, holds one to 4, and saves → one ledger event.


## 8. Owner decisions at build

- Add buttons are **always visible** on Collection cards (D3); the hold amount is a **delta** (copies to add) and the grid never lowers owned counts.
- Picking a family you own nothing from while Ownership is Owned-only turns *Missing* on in the same URL update.
- An unread family is **read automatically** by `collection.read_family` (once per visit; failure shows Retry, never loops).
- Adds-only drafts are revertible (D2).
- "Every family you own" stays the default scope: the unowned-families switch never widens it.
