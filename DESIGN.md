---
name: magic-manager web
description: After-Hours Price Guide for MTG collection, set, and commander comparison work.
colors:
  charcoal-950: "#100d09"
  charcoal-900: "#16130e"
  charcoal-850: "#1c1812"
  charcoal-800: "#221e17"
  charcoal-700: "#2e2920"
  charcoal-600: "#433c30"
  bone-50: "#f7f2e7"
  bone-100: "#efe7d6"
  bone-200: "#e4dac4"
  bone-300: "#d3c6aa"
  ink-900: "#1d1912"
  ink-700: "#3d3529"
  ink-600: "#625846"
  taupe-400: "#a59b87"
  taupe-500: "#8a8170"
  amber-300: "#f7c66b"
  amber-400: "#f4b347"
  amber-500: "#f0a531"
  amber-800: "#7a4b00"
  rust-400: "#e2785e"
  rust-700: "#9c3a22"
  on-chrome: "var(--theme-on-chrome)"
  paper: "var(--theme-paper)"
  ink: "var(--theme-ink)"
  accent: "var(--theme-accent)"
  on-accent: "var(--theme-on-accent)"
typography:
  display:
    fontFamily: "Archivo Variable, Archivo, Helvetica Neue, Arial Narrow, sans-serif"
    fontSize: "var(--font-size-3xl)"
    fontWeight: 680
    lineHeight: 1
    letterSpacing: "-0.01em"
    fontVariation: "'wdth' var(--font-width-condensed)"
  headline:
    fontFamily: "Archivo Variable, Archivo, Helvetica Neue, Arial Narrow, sans-serif"
    fontSize: "var(--font-size-2xl)"
    fontWeight: 680
    lineHeight: 1
    fontVariation: "'wdth' var(--font-width-condensed)"
  body:
    fontFamily: "Archivo Variable, Archivo, Helvetica Neue, Arial Narrow, sans-serif"
    fontSize: "var(--font-size-md)"
    fontWeight: 400
    lineHeight: 1.5
    fontVariation: "'wdth' var(--font-width-normal)"
  label:
    fontFamily: "Archivo Variable, Archivo, Helvetica Neue, Arial Narrow, sans-serif"
    fontSize: "var(--font-size-sm)"
    fontWeight: 520
    letterSpacing: "0.06em"
    fontVariation: "'wdth' var(--font-width-semi)"
rounded:
  none: "0"
  xs: "2px"
  sm: "3px"
  pill: "999px"
spacing:
  px: "1px"
  0-5: "0.125rem"
  1: "0.25rem"
  1-5: "0.375rem"
  2: "0.5rem"
  3: "0.75rem"
  4: "1rem"
  5: "1.25rem"
  6: "1.5rem"
  8: "2rem"
  10: "2.5rem"
  12: "3rem"
components:
  button-primary:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.75rem"
    height: "2.25rem"
  button-quiet-chrome:
    backgroundColor: "transparent"
    textColor: "{colors.on-chrome}"
    rounded: "{rounded.sm}"
    padding: "0.5rem 0.75rem"
    height: "2.25rem"
  chip-on:
    backgroundColor: "{colors.accent}"
    textColor: "{colors.on-accent}"
    rounded: "{rounded.pill}"
    padding: "0.375rem 0.625rem"
  sheet:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.sm}"
---

# Design System: magic-manager web

## Overview

**Creative North Star: "After-Hours Price Guide"**

magic-manager renders collection work as a living collector's price guide, not a SaaS dashboard. The app frame is dark charcoal chrome; the work surface is a ruled guide sheet where cards, set gaps, commander overlaps, prices, and copyable lists read like late-night catalog annotations. The implemented world comes from `web/index.html`'s direction contract, the DTCG token files in `web/tokens/`, the generated `web/src/styles/tokens.css`, and the React components in `web/src/components/`.

Light mode keeps the chrome dark and prints the content on bone paper. Dark mode moves the same guide onto charcoal stock with bone ink. Amber is deliberately rare: it marks active navigation, focus, primary actions, progress, and user highlighter marks. It is not a general accent palette.

**Key Characteristics:**
- Charcoal application chrome around paper or stock guide sheets.
- One variable grotesque, Archivo, with `wdth` voices instead of separate typefaces.
- Tabular figures for prices, collector numbers, percentages, counts, and progress.
- Hairline rules and two-pixel strong rules replace card shadows and dashboard panels.
- User-selected cards are highlighter marks, never filled selection cards.
- Dense desktop columns with resizable separators; phones collapse columns into tabs.

## Colors

The palette is a narrow guide-book system: charcoal, bone, ink/taupe, amber, and rust.

### Primary
- **Amber highlighter** (`amber-500`, `accent`, `highlight`, `highlight-solid`): active nav underline, focus outline, primary buttons, selected chips, progress fill, marked cards, and separator handles in active/hover states.
- **The Amber-Only Rule.** Amber appears only as highlighter, active/focus, progress, or primary action. Do not use amber for decorative fills, secondary charts, badges, or background variety.

### Secondary
- **Rust danger** (`rust-700` in light, `rust-400` in dark via `danger`): error copy, failed job lines, and destructive/failed states only.

### Neutral
- **Charcoal chrome** (`chrome`, `chrome-raised`, `chrome-line`): topbar, sidebar, theme switch, text fields, and chrome-side control borders.
- **Bone paper** (`paper`, `paper-raised`, `paper-sunk` in light): guide sheet, empty states, card placeholders, skeletons, paper hover fills.
- **Charcoal stock** (`paper`, `paper-raised`, `paper-sunk` in dark): dark-mode guide material; the content surface remains distinct from the app chrome but stays charcoal.
- **Ink and muted ink** (`ink`, `ink-muted`): content text, captions, CN · SET · rarity guide lines, values, labels, and metadata.
- **Rules** (`rule`, `rule-strong`): row dividers, group heads, column heads, inclusion tracks, and panel separators.

### Theme token roles
- **Light:** `chrome=#16130e`, `chrome-raised=#221e17`, `chrome-line=#433c30`, `on-chrome=#efe7d6`, `paper=#efe7d6`, `paper-raised=#f7f2e7`, `paper-sunk=#e4dac4`, `ink=#1d1912`, `ink-muted=#625846`, `accent=#f0a531`, `focus=#f0a531`.
- **Dark:** `chrome=#100d09`, `chrome-raised=#1c1812`, `chrome-line=#2e2920`, `on-chrome=#efe7d6`, `paper=#221e17`, `paper-raised=#2e2920`, `paper-sunk=#1c1812`, `ink=#efe7d6`, `ink-muted=#a59b87`, `accent=#f0a531`, `focus=#f4b347`.
- `scrim` supports popover/drop-shadow depth; `on-accent` stays ink-dark for readable amber controls in both themes.

## Typography

**Display Font:** Archivo Variable (`@fontsource-variable/archivo/wdth.css`) with Archivo, Helvetica Neue, Arial Narrow, sans-serif fallback.  
**Body Font:** same family.  
**Label/Mono Font:** no mono face; numeric tables use `font-variant-numeric: tabular-nums lining-nums`.

**Character:** One condensed newsprint grotesque carries the whole interface. Distinction comes from the variable width axis: `voice-condensed` for mastheads and running heads, `voice-semi` for controls and labels, normal width for body text.

### Hierarchy
- **Display** (`voice-condensed`, 680, `--font-size-3xl`, tight): guide-sheet `h1`, app title at desktop scale.
- **Headline** (`voice-condensed`, 680, `--font-size-2xl`, uppercase): column headers, family headers, empty/error note titles, job section headings.
- **Title** (`voice-condensed`, 680, `--font-size-xl`/`2xl`): mobile tabs, top navigation, status titles.
- **Body** (`--font-size-md`, 400, relaxed only where explanatory): empty text, job copy, form helper copy.
- **Label** (`voice-semi` or `voice-condensed`, `--font-size-xs`/`sm`, often uppercase with `0.06em` tracking): side-section headings, filters, suggestion metadata, progress rows.
- **Figures** (`tabular`): prices, percentages, counts, collector numbers, set codes, timestamps, progress, and list totals.

### Named Rules
**The One Typeface Rule.** Do not introduce display, serif, mono, or card-flavor faces; use Archivo width and weight to change voice.  
**The Tabular Ledger Rule.** Any collection fact that can be compared in a column uses `tabular` figures.

## Layout

The global shell is a two-row grid: `--size-topbar` (3.5rem) masthead/nav above the view body. The primary nav is full-width in the topbar; the sidebar begins below it inside `ViewLayout`, matching `web/src/components/AppShell.tsx`.

Desktop view bodies use `lg:grid-cols-[var(--size-sidebar)_minmax(0,1fr)]` with a 16rem sidebar and a scrollable main region capped to `calc(100dvh - var(--size-topbar))`. Main content has compact padding (`0.5rem` → `1rem`) because the guide itself supplies the rhythm.

Guide sheets (`GuideSheet`) are full-height paper panels with a compact title block and a flexible body. Compare views split the sheet into horizontal resizable columns using `react-resizable-panels`; each visible column has a ruled heading, optional legend, virtualized body, and hide control. Width layout persists per visible-set key in localStorage.

Cards have two view types (sidebar `View type`: Grid · List, URL `view`). Grid calculates columns from the scroll-region width with a 12px gap and minimum card widths (`120px`, or `128px` for Collection). List is a 2rem ruled checklist line. `CardRow` uses container-query breakpoints at `18rem` (show crop thumbnail), `22rem` (show bars and wider price), and `30rem` (show set/CN metadata and wider bars).

Responsive behavior is task-specific, not generic stacking. At `max-width: 47.99rem`, `GuideColumns` becomes a tabbed single-column view. At `min-width: 64rem`, sidebar controls are always visible; below that, `ViewLayout` uses a disclosure button with `aria-expanded` and `aria-controls`.

## Elevation & Depth

Depth is mostly tonal and ruled, not shadowed. The app chrome, raised chrome controls, paper sheets, sunk paper, hairline rules, and paper grain carry the material model. Shadows appear only where the implementation needs separation from the stock: the guide sheet has a restrained ambient drop, hover-card art previews use `drop-shadow`, and command suggestions use a small popover shadow.

### Shadow Vocabulary
- **Sheet settle** (`0_1px_0_var(--theme-chrome-line),0_18px_40px_-28px_var(--theme-scrim)`): one shadow on `GuideSheet`, enough to separate paper from chrome.
- **Preview float** (`0_10px_24px_var(--theme-scrim)`): card-art hover preview above rows/tiles.
- **Popover float** (`0_12px_28px_-12px_var(--theme-scrim)`): commander suggestion panel.

### Named Rules
**The Ruled-First Rule.** Prefer borders, hairlines, and tonal stock changes before shadows. Shadows are for floating previews, popovers, and the sheet resting on chrome.

## Shapes

The shape language is nearly square, like printed stock and clipped guide labels. Default radii are tiny: `radius-xs` 2px, `radius-sm` 3px. Pills are reserved for chips, bars, highlighter handles, jobs pulse dots, and segmented capsule details. Actual card images keep their physical card radius via `rounded-[4.5%/3.2%]`; art crops and thumbnails use `radius-xs`.

Hairline borders are the main geometry. `ruled` is a 1px bottom border; column and section headings use 2px `rule-strong`; split separators use a 1px vertical rule plus a pill handle. The `highlighter` utility is a ragged linear-gradient stroke behind text/rows, not a rectangular selected background.

## Components

### AppShell + ViewLayout
- **Purpose:** global masthead, primary nav, jobs link, theme switch, sidebar-below-nav layout.
- **Nav:** Collection · Decks · Explore · Market. On phones the tabs tighten (smaller condensed type, no gaps) so all four fit at 360px. **Jobs is not a destination:** background jobs are housekeeping, so they sit beside the theme switch as a quiet queue-mark icon (tooltip *Background jobs*, amber dot while one runs) — never a nav tab or a word.
- **Restore point:** a quiet undo-arrow icon left of the jobs icon, shown only once a restore point exists (tooltip `Restore point · 3:31 PM`). Confirm dialog (`Restore your collection to 3:31 PM?`): why it was taken, a plain list of what changes (`3 fewer copies`, `1 more deck`), and that it swaps — restoring again comes back. One slot; taken automatically before the first change of each session.
- **States:** active nav uses amber underline; the jobs icon shows an amber dot when queued/running; theme can be system/light/dark and persists to `localStorage` as `mm.theme`.
- **A11y contract:** skip link to `#main`, `nav aria-label="Primary"`, `main tabIndex={-1}`, sidebar labelled by the view, mobile disclosure uses `aria-expanded`/`aria-controls`.

### GuideSheet
- **Purpose:** paper/stock host for each view's title, summary, actions, and guide body.
- **Style:** `paper-grain`, `bg-paper`, `text-ink`, `rounded-sm`, ambient sheet shadow.
- **States:** empty, error, and skeleton states render inside the sheet rather than replacing the shell.
- **Sheet tabs (`nav` slot):** a view with sibling sheets puts a ruled tab strip at the sheet's top edge (small condensed uppercase links, amber underline on the active one, `nav aria-label`). Collection uses it for `Cards · Purchase history`; the top-nav tab stays active on both.

### Sidebar primitives
- **SideSection:** uppercase condensed side heading plus vertical control stack.
- **Segmented:** single-choice `ToggleGroup`, ruled chrome border, `chrome-raised` selected state.
- **ChipToggles:** multi-select `ToggleGroup`, pill chips; selected chips fill amber and show optional tabular counts. **Only for ≤5 options that fit on ONE line** — if they'd wrap, use a `MultiSelect` picker (counts beside each option).
- **Active state for categorical controls:** every on segment/toggle (Segmented, SegmentedToggles, ChipToggles) fills **amber** (`accent` / `on-accent`), off stays `on-chrome-muted` on chrome — one active language across the sidebar. Every control carries a visible label.
- **SelectField:** single choice from a short list — same trigger as MultiSelect, opening a Radix radio menu (✓ + amber checked item, optional counts). Never a native `<select>` in the sidebar.
- **SegmentedToggles:** the `Segmented` look with toggle behavior — each segment independently on/off (Collection `Show: Owned | Missing`, counts inline). Binary include/exclude choices use plain `Segmented` `Include | Exclude` (Collection `Chase`, with an ⓘ `InfoTip` defining the term).
- **MultiSelect:** any choice set larger than 5 (set families, EDHREC lists). A compact trigger summarizing the selection (`Final Fantasy +2 ▾`) opens a searchable checkbox popover; selected options are pinned first; bulk-select is scoped to the current search, never "select everything".
- **SortBuilder:** the one sort control for every card view. Trigger shows the hierarchy (`Set › Rarity › #`); the popover edits ordered levels (direction toggle, ▲▼ buttons and drag handles via Pragmatic drag-and-drop, add/remove) and offers presets. The first level groups the sheet into sections. Rules live in the URL (`core/sort.ts` codec).
- **Grouped MultiSelect (Card types):** trait filters (Finish · Rarity · Treatment · Chase) are ONE grouped checkbox picker, everything checked by default; unchecking a trait hides every card carrying it — except Finish (Nonfoil · Foil · Fancy foil), which ORs: a printing shows while any of its finishes is checked, and owned/missing are judged on the checked finishes only. Fancy foil = a foil printing whose treatment carries `ff` (surge, etched, galaxy…). Collection splits card types into one control per dimension, in order: `Rarity` · `Finish` · `Treatment` pickers (authored order kept, counts beside each option, trigger `All rarities` / `Hiding Uncommon, Common`), then `Chase` `Include | Exclude`. (Grouped pickers lay groups out in two balanced columns ≥sm;) the trigger summarizes exclusions (`All card types` / `Hiding Common, Uncommon +1`). No explanatory copy under controls.
- **TextField:** labelled search input on `chrome-raised`, `chrome-line` border, amber focus border.
- **A11y contract:** groups carry explicit `aria-label`; labels wrap inputs or target by `htmlFor`.

### Group by (Commanders)
- **Purpose:** re-section every compare column without changing ranking: `Card type` (EDHREC's type-based lists, the default) or `Function` (Scryfall Tagger function roots in config order — Ramp, Card draw, Removal, …; untagged cards last under "No tagged function").
- **Style:** a two-option `Segmented` in the Display section (two options → segmented, never chips). Group heads reuse VirtualGuide's level-2 ruled subheads; no per-function colors (one-accent rule).
- **Multi-membership:** a card serving several functions is listed under each, with a muted `GuideNote` ("also: Removal, Tutor") under its caption (inline after the set metadata in List); a one-line helper under the control says so and that column totals count each card once. Marking is per card, so every appearance highlights together.
- **Empty state:** when the tag cache was never synced, a chrome-muted note links to Jobs → Sync Scryfall tags.

### Missing means (Collection)
- Under `Cards: Owned | Missing`, when Missing is on: `Missing means: This printing | The card` ⓘ. **Default is *This printing*** — the exact printing you don't have (the collector's view). *The card* (deck-building flavor, opt-in) keeps only missing printings of cards you own in **no printing from any set** (`card_owned` from the engine) — the gaps in what you can play — and the sheet summary switches to `N cards you own in no printing · $X at the cheapest printing of each`. URL `gaps`.

### Find products in your cards (Collection)
- Toolbar icon → dialog that scans at once (`trueup.scan` job: progress rule `Checking products · n of N · <product>`; first scan reads every product list, minutes; later under a minute). **Review:** `Your cards complete · N` — one ruled row per product (checkbox checked by default, name, `type · SET · year`, `N cards · $`), unchecking strikes it through and remembers it as *not mine* (never suggested again, `localStorage`). `Shared a card with another product` rows carry *I opened this one* (re-scans with that pick). Commit: `Record N products` (`trueup.apply` re-checks exactly the reviewed list and refuses if your cards changed) → `Recorded N products. M cards now show where they came from under Acquired from.`

### Check my Mana Pool cart (Collection · internal, `cart_check` flag)
- Hidden unless the flag is on (`config/features.local.toml` or `MM_FEATURES=cart_check`). A quiet chrome `Button` under the Buy strip opens the dialog: *Read my cart* reads the cart with the Mana Pool account in this machine's `.env` (disabled, with setup instructions, when `MANAPOOL_*` aren't configured). Results: one summary line, then ruled sections `Bought twice` · `Already in your collection` · `Over market` (red `+N%`) · `Still missing from <FAM>` (≈ $) · `Couldn't identify`, each with a plain empty sentence. **Never ask users for Mana Pool credentials** — they're tied to real money; the flag keeps this internal. (A cart-page bookmarklet was considered and parked: it won't get used.)
- Buy strips (Collection, Market) end their lead with `≈ $X at market`: the cart total to expect after pasting.

### Function filter (Collection)
- **Purpose:** keep printings serving any chosen Tagger function root (OR), plus a "No tagged function" option; sits under Card types in Show and is cleared by Reset filters.
- **Style:** 13 options → `MultiSelect` (never chips); trigger reads "Any function" when empty. Hidden until the tag cache has data.

### CardMeta (hover preview + guide note)
- **CardPreview:** art first, then — below the art, never over it — a ruled `paper-raised` panel with a `Functions` label line and up to six tag chips (hairline `rule` border, `ink-muted`, no fill, no amber).
- **GuideNote:** one truncated `2xs` `ink-muted` line under the guide line; `title` carries the full text.

### CommanderPicker
- **Purpose:** commander search field with local suggestions and free-text commit.
- **Style:** condensed large input on chrome; suggestions are a raised chrome popover.
- **States:** arrow keys move `aria-activedescendant`, Enter commits active/free text, Escape closes and resets draft, blur commits after a short delay.
- **A11y contract:** ARIA 1.2 combobox (`role="combobox"`, `aria-expanded`, `aria-controls`, `aria-autocomplete="list"`) with listbox/options.

### GuideColumns
- **Purpose:** horizontally stacked diff/compare pools with individually toggleable columns.
- **States:** hidden columns removed; empty visible set shows an instruction; narrow screens switch to tabs.
- **A11y contract:** separators are keyboard-operable window splitters via `react-resizable-panels`; mobile tabs use `role="tablist"`, `role="tab"`, `aria-selected`, and `role="tabpanel"`.

### VirtualGuide
- **Purpose:** one virtualized scroll region for grouped card lists in grid or rows density.
- **Style:** section heads are ruled; grid uses real card art; rows use checklist lines.
- **A11y contract:** scroll container is `role="region"` with caller-provided label and `tabIndex={0}`.

### CardTile and CardRow
- **Purpose:** two densities for the same `GuideCard` view-model from `web/src/core/guideCard.ts`.
- **Tile state:** button is `aria-pressed`; selected cards get an amber ring and highlighter caption.
- **Row state:** checkbox marks a card; selected rows receive the highlighter utility.
- **Preview:** names trigger hover-card previews (`CardPreview`: art, then functions + Scryfall tags below it); card links open Scryfall when present.

### CardFace parts
- **CardArt:** fixed 488×680 card aspect or art crop; missing image becomes a ruled paper placeholder.
- **GuideLine:** CN · SET · rarity · finish + inclusion/price in tabular figures.
- **InclusionBars:** two stacked bars for shared commander cards, with ARIA label carrying both percentages.
- **Holdings:** owned copies per finish (`×N`, foil `✦×N` in accent ink) or a rust **MISSING** mark, on its own caption line.
- **Tags:** short printed facts (Chase, Borderless, Showcase, Ext. art, Reskin) as one truncated uppercase line; Chase in accent ink.
- Missing printings dim their art (`opacity-55 grayscale`) — state is shown on the art's tone, never drawn over it.

### Card inspector
- **Trigger:** pressing the card art (grid) or the card name (list) opens the inspector; normal pointer cursor. Marking is a separate `MarkToggle` (list-plus → amber list-check, `Add to list` / `Remove from list`) on the Holdings line under the art (grid) or at the row start (list). Nothing overlays the art. The marked list is product-neutral (buy lists today; bulk add/remove/tag later) — never call it a "buy list".
- **Dialog (`CardInspector`, rendered once per `VirtualGuide`):** large Scryfall image left (stacked on phones), then name (`Dialog.Title`), type line, a `dl` of Printing · Mana value · Price (nonfoil / ✦ foil) · Owned · Functions, the printed Tags, Tagger chips, and, under a small `View on` label, ghost links `Scryfall` / `TCGplayer` (same treatment as `Add cards`), each led by its site mark (TCGplayer = name search; no product id is stored).

### Sheet actions + external links
- **Sheet actions are icons** (`IconAction`: amber-ink mark, tooltip names it, `paper-sunk` wash on hover/focus — **no lift, no underline**; a pressed toggle (`aria-pressed`, e.g. *Count cards*) keeps the wash plus an amber underline) grouped in a `role=toolbar` — Collection: *Add cards* · *Find products in your cards*; Decks: *New deck* · *Import a deck*. Outbound links are ghost links (mark + label, same wash). Reserve the filled amber `Button` for a flow's single commit (e.g. `Add 8 copies`, `Save deck`, `Record 3 products`).
- **Icon action** (`IconAction`) = the same treatment without the words, for a ROW of related actions where labels would crowd (the deck header). The tooltip carries the words and is the accessible name; disabled icons go muted with a tooltip naming why. Two or more sibling actions → icons; a lone sheet action keeps its label.
- **Every link or button that leaves the app carries the destination's monochrome mark** (`StoreMarks.tsx`, 24px stroke grid, `accent-ink` on paper / `accent` on chrome) instead of a generic ↗. The word is optional: keep it where there's room and the pair scans faster (inspector, phones' buy strip); drop it in tight rows (desktop buy strip), keeping `aria-label`/`title` `Open on <Site>` / `Copy <Store> list`. New external targets get a mark drawn after the site's own logo before they ship.

### Explore (`/explore`, was Commanders)
- **One card, a chosen role.** Sidebar: `Card` (any card) + `Compare with` (optional) + `Explore as: As commander | As a card` (commander disabled with a reason when a card can't lead; unset = commander when it can). Both sides of a comparison share one role.
- **Card plate** above the guide: art (opens the inspector), condensed name (+ `A`/`B` marker when comparing), type line, a fact line (`Played in N of M possible decks (x%)` · Salt ⓘ · From $ · You own n · m free), Tagger tags, the deck mix ("Typical deck it's in"), and ghost outbound links with marks (EDHREC · Scryfall). Comparing: plates sit side by side with a quiet `vs`, compact (smaller art; tags move to the tag split row: Only A · Both · Only B).
- **As commander:** the commander's recommended cards (single) or today's three resizable columns `A only · Both · B only` (compare).
- **As a card:** sections `Commanders that run it` (share of their decks), `Played alongside` (by type, lift order, `1.09× lift` notes), `Similar cards`; comparing splits each into the three columns, the Both column carrying both shares as stacked bars and both lifts in the note. Descriptive only — never a verdict.
- Every card inspector has `Explore this card`.

### Market (`/market`)
- **The price guide, literally.** Sidebar: `Subject: Set family | Deck | Secret Lair` (+ `Deals` with its flag), a searchable one-of picker (`SearchSelect`: filter box over a listbox; ↑/↓, Enter picks, picking closes).
- **Set family → Sealed:** ruled guide table grouped by product category (`Booster boxes · 2` sticky-style heads): `Product · Sealed · Cards inside ⓘ · Difference`. Difference is signed; cards worth more than the box reads `+$` in accent-ink, otherwise muted `−$`. When some fixed cards have no price at their exact printing (e.g. Collector's Edition foils), *Cards inside* shows `$X+` (muted plus; tooltip `N of M cards have a price…`) and Difference stays `—` — unknown is never $0. Pricing runs as the `market.value_family` job (a thin amber progress rule `Pricing 13 of 36 · <product>`; cells show `…` until priced; results kept 12 h per family in `localStorage`). A product row discloses its contents tree (`Contents · Market · Cards inside`, indented per level) plus fixed-card totals at these vs the cheapest printings and a TCGplayer ghost link.
- **Set family → Cards:** `Card (SET CN · treated) · This printing · Cheapest (SET CN where it differs) · Premium · You own`; `Printings: All | Not cheapest`, sort by premium/price/set; 200 rows then `Show more`.
- **Deck:** a three-row **ledger**, not hero metrics: `Buy it sealed` (precons; the product named beneath) · `Buy every card` · `Use your free cards first`, × `Deck’s printings | Cheapest printings`; the lowest cell is bold accent-ink with a `lowest` tag. Then `To buy` and `Covered by your free cards · worth $` line tables. Sidebar *Buy*: `Printing: Cheapest | Deck’s` + the store-mark copy strip. Decks' toolbar gains *Cost to build* (price tag mark) → here.

- **Deals** (internal `deals` flag; third subject): sidebar *Show: Open tabs | Watching* (URL `deals=tabs|watching`) chooses the product set; both share ONE product table + inspector (`DealsWorkspace`: resizable split like Deck Manager, list 60 / inspector 40, one panel at a time on phones with `‹ All products`). *Open tabs*: *Read my open tabs* (on demand, never cached) → one ruled section per store (`Many Realms 15 · price read from the store · no sales tax`) listing each product page; *Read N prices* runs `deals.read_prices` (progress `Reading 3 of 12 · store`; errors that apply to the whole read, e.g. Chrome's *Allow JavaScript from Apple Events*, show once). After prices the per-store sections give way to the table; listings that aren't a known product (ambiguous, unmatched, skipped, errors) stay under **Needs a look** with the `Identity` picker (`This one`, `not this?`, `you confirmed this · change`) and move into the table once confirmed; then `Stores without a recipe yet` and a muted footer counting carts/other/local/duplicate tabs. *Watching* is instant (no valuation); *Read watched prices* runs `deals.watchlist` `{refresh: true}`. **Table** (one row per product; the same product at several stores is one row): Product (button; `SET · Type`) · Best (price, store, `↗` link, trend arrow, `Sold out` in red) · Gap vs the chosen basis (`−21%` accent-ink under, red over, `$` under it) · Sealed · Cards inside (exact, `cheapest $` and the cards + boosters split beneath, `+` when some cards are unpriced); Sealed and Cards inside drop out by container width. A muted line counts `12 of 17 products · compared to …`. Values fill in as each product's cost loads (muted `…`; `—` on error). **Sidebar *Find***: Search (name or set code), Stores, Type chips with counts, Discount (Any | 10%+ | 20%+ | 30%+ under the *Compare to* price), Compare to (Sealed price | Cards, exact | Cards, cheapest), Sort, In stock only; changing a filter keeps the open product only while it still matches; *Nothing matches these filters* offers `Clear filters`. **Inspector**: name · `SET · Type · released` with Watch / Stop watching (confirm; a single is watched as its exact printing + finish); *Stores* (underlined link ↗, price, stock, read age, trend, per-store errors, *Read from your open tab — keep the page open to refresh*); *What it's worth* ledger (sealed price, cards inside exact / cheapest, boosters' expected value, totals, each with its gap to the best price; unpriced-cards note); *Contents* (the product tree, market beside cards inside); *Cards* (sortable by price columns). Reader warnings (a second automation Chrome, windows not read) show as plain sentences with the fix; with a warning and no store tabs the empty state says *Couldn't see your store tabs*.

- **Secret Lair** (subject, always on; URL `subject=sld`): the newest drops (Show: 10 / 30 / 60 / 120 newest, `sldN`), one row per drop at the sidebar's `Edition: Regular | Foil` (a drop sold in one edition shows that one with `foil only` / `regular only`). Shares the Deals building blocks — `MasterDetail` (split / one-at-a-time on phones, `‹ All drops`), the same table rhythm, `CardLines`, the ledger `Row`. **Table:** Drop (button; release date, `· watching`) · Sealed · Gap (sealed vs the *Compare to* cards: `−33%` accent-ink when sealed is cheaper, red when dearer, `$` beneath) · Cards inside (the compared total, the other basis muted beneath, `+`/unpriced note); values fill per row (`…`, `—` on error) and the status line counts `pricing N…`. **Sidebar *Find*:** Search, Edition, Show, Discount (Any | 10%+ | 20%+ | 30%+), Compare to (`Exact | Cheapest`, URL `sbasis`), Sort (biggest discount % / $, lowest sealed price, newest, name). With the `deals` flag the Subject control wraps two-by-two (`Segmented wrap`) so `Secret Lair` stays whole. **Inspector:** name · `SLD · Secret Lair · Regular edition · released`; *What it's worth* ledger (Sealed price + source, cards inside exact / cheapest each with sealed's % vs it, the bonus card's expected value when it's a random bonus pack; a sentence naming the bonus card; `TCGplayer ↗`); *Contents* tree when the bonus is a pack; *Cards* with a small accent `bonus` tag on the bonus card's line. *Watch* (deals flag only) tracks the drop at its TCGplayer product page, refreshed from its TCGplayer **market** price (store `TCGplayer market` in Watching) — disabled with a tooltip until TCGplayer lists it; `Stop watching` confirms. A foil-only drop (named `… Foil Edition`) matches its watched entry by `watchKey` (the watchlist returns it without the suffix).

### Deck Manager (`/decks`)
- **Two resizable panels** (list ~1/3 · inspector ~2/3, `react-resizable-panels`, persisted); phones show one at a time (list → deck, `‹ All decks` back).
- **Deck list:** sticky ruled group heads (`Group decks by`: Set · Year · Deck type · Built/not built · Source; newest first), one ruled row per playable deck RECIPE (card pools — land packs, scene boxes, most Secret Lair drops — never appear) — art crop, name, `type · SET · year`, value, and a `×1 built` counter (amber-ink). **"Loose" is not tracked in the app:** a broken-down deck is just cards in the collection, traced by Collection's *Acquired from*. The open deck carries the highlighter. The list is ONE tab stop (roving focus: ↑/↓, Home/End, Enter opens); groups use `content-visibility:auto`. Sidebar: search (deck/set/author/type), `Decks: All | Built`, a `Deck type` picker (**defaults to Commander**; clearing it shows every type), a `Group decks by` menu, `Card view: Cards | List`. Sheet actions (icon toolbar): `New deck` (name + format → editor) · `Import a deck from a link` (saves the decklist only, never built; *Also add these cards to my collection* continues into the add-cards review).
- **Inspector:** deck title + one fact line (set · year · source · author · cards · value · built/pledged %), then a toolbar of **icon actions**: *Add deck cards to collection* (opens the add-cards review; nothing is written until its commit) · *Edit deck* — or *Copy to edit* for precons, whose decklists are read-only reference data · *Build from your cards* (confirm dialog: N of M free, the missing list, `Build deck` / `Build with N missing`) · *Break down* (confirm: cards return as free copies, the list stays). Marked cards add `Add N marked cards to collection` + `N marked · Clear`. An ⓘ defines built / pledged / free; phones get a `List view` / `Card view` switch in the header pre-filled with exact printings. Cards render through `VirtualGuide` sectioned like a decklist: Commander · Companion · Creatures … Lands · Sideboard · Maybe · Tokens; captions add `×N in deck · M pledged` and `N free to use`.

### Purchase history (`/collection/history`, a Collection sheet)
- **Same split as Deck Manager** (shared `SplitPanes`; list 40 · inspector 60; phones one panel at a time, `‹ All entries`).
- **Timeline:** newest first, sticky month heads with `N held · $` totals; one ruled row per ledger entry — day, title (product name, `Checklist · Set`, `Added from search`…), `Kind · SET · file` and `identified` when Find products dated it, value + `+in −out` on the right. Pre-ledger ingests show `N rows` muted instead of value. **Deck moves are quiet:** smaller muted single lines, and a day's moves gather into one run row (`Built 4 decks`, chevron expands). `Provenance unknown` titles are muted. ONE tab stop (roving ↑/↓, Home/End).
- **Sidebar:** search (product, set, file) · `Kind of entry` picker with counts · `From`/`To` day fields (`DateField`) · `Clear filters` · a glossary of the kinds (Precon, Card pool, Singles, Checklist — source product not recorded, Unknown, Deck move).
- **Inspector:** title + fact line (kind · date · set · file, ⓘ kind help), a plain dating note when the date isn't the purchase (*Identified in your cards by Find products — not the purchase date*; *Reconstructed when the ledger began*), facts `Came in · Removed / Moved to products · Still held · Worth today`, `Open deck` for playable products and moves, then the exact printings through `VirtualGuide` (list by default) sectioned by type, held copies as the owned count, `+in −out` captions only when copies left. Pre-ledger entries explain where their cards are counted and link to *Checklists before the ledger*; moves say nothing was bought. What was paid is not recorded yet — never shown as a blank field.

### Deck editor (`/decks/<slug>/edit`)
- **Two-pane workbench** (resizable, persisted; phones: `Deck · N | Find cards` tabs). Header: `‹ Back to deck`, the deck name as an inline-editable title, `Cards N / target` (100 Commander/Brawl, 60 otherwise; amber-ink until on target), `Changes +a −r`, `Discard changes` and the one filled commit `Save deck`.
- **Draft decklist (left):** sections like the deck view; each ruled row = `− n +` stepper, name, `SET · #cn · finish · N free`, a diff mark (`NEW`, `+n`, `−n`, `REMOVED` — amber-ink adds, rust removals), price, and a `⋯` menu (Move to board · Finish when building · Remove / Undo remove). Removed rows stay struck-through until saved so a mistake is one click back.
- **Find cards (right):** `Search | Suggestions` tabs. Search covers all of Magic but lists **your free copies first** (`3 free` in amber-ink), offers `As commander` for legendary leaders when the commander slot is empty. Suggestions = EDHREC's picks for the commander with inclusion %, `Free in my collection` and `Hide cards in deck` filters.
- **Checks** (header, `Legal · B3+`): a popover with format legality (Scryfall's per-format legality; errors in rust) and, for Commander-like formats, the **bracket floor** from Wizards' published criteria (Game Changers, mass land denial, extra turns; two-card combos only on request via Commander Spellbook). Copy states brackets are guidelines, not rules — never a verdict, never blocks Save.
- **Card names** in the draft and in results open the shared `CardInspector` (with *Your copies*).
- **Save** cuts a new deck version (history kept). A built deck first shows **Update your built deck** — `Take out · Put in · Missing` lists — and saving moves its pledges to match. Leaving with unsaved edits asks first.

### Count cards — checklist mode (Collection)
- **Purpose:** the desk ritual of filling a set checklist, in place. Sheet action icon *Count cards* (card with tally marks; pressed = `paper-sunk` wash + amber underline, URL `count`) swaps the guide for a dense ruled count table over the same filters + sort; *Done counting* switches back.
- **Table:** sticky `Printing · Nonfoil · Foil ✦` header; family/set heads as in the guide (no disclosure); one 40px ruled line per printing — art crop (≥26rem container), name, `SET · # · R · tags`, then one right-aligned count cell per finish (`—` where the printing has no such finish; etched counts as foil). Virtualized.
- **Keys:** typing selects-and-replaces; Enter/Tab go DOWN the same finish column (skipping printings without it), Shift reverses, ↑/↓ too, ←/→ switch finish, Esc puts the cell back. Not-a-number turns the cell's border rust (`aria-invalid`) and isn't counted.
- **Diff:** an edited line takes the highlighter; the cell's value goes semibold with a signed mark left of it (`+2` accent-ink, `−1` rust). The sheet summary becomes the running diff: `Counting · 12 changes · +8 −3 copies · +$14.20 at market (2 unpriced)`; after saving, `Saved 12 counts · +8 −3 copies`.
- **Commit:** `Discard` (quiet, confirms `Discard N counts?`) + the one filled `Save N changes`, left of the icons. Save = one ledger event; a count below copies in built decks shows a rust note (*break it down before counting fewer*) and keeps Save off; if the collection moved since you started counting, the save is refused, the numbers refresh and each moved cell is **flagged** (amber ring, `now N` beside it, tooltip names both counts) under a note `N counts changed in your collection since you started counting…` with *Keep all my counts*; retype a flagged cell or press Enter on it to keep yours — Save stays off until none are flagged. Cells stay editable while saving; anything typed meanwhile is kept (rebased on the count just saved).
- **Draft:** kept in this browser (`mm.collection.checklist`) until Save or Discard — survives reloads, mode and family switches (the icon tooltip says `Count cards · N unsaved`); leaving Collection asks `Leave with unsaved counts?`.
### Add cards dialog (Collection)
- **Why a modal:** a protected multi-step flow (stage → review → commit) that must not leak half-edits into the sheet. Trigger: a **ghost button** in the sheet header's upper right (`GuideSheet actions`; may later move nearer the card list) — `AddCardMark` (card + plus badge) + `Add cards` in `accent-ink`, no border or fill; hover/focus adds a faint `paper-sunk` wash (no lift, no underline). Paper sheet inset 3dvh, title + text tabs (`Search · Paste a list · Deck or precon`, amber underline on the active tab, like the nav).
- **One review model for every mode:** search stages printings, paste/deck lines resolve server-side, and all of them end in the same `ReviewTable` checklist (ruled rows: include checkbox, art crop, name + source line/note, printing picker, finish toggle, unit price, qty). Ambiguous lines carry an amber-ink `BEST GUESS` mark; unresolved lines a rust `NOT FOUND` and are left out. Narrow containers wrap the controls under the name (`@container`, `contents` at ≥44rem).
- **Printing picker:** a ruled trigger naming the pick (`DSC · 114 · U`) + candidate count, opening a popover grid of every printing's art with price and owned copies; the current pick gets an amber outline.
- **Footer:** what will happen in plain numbers (`8 copies · 2 best-guess printings to check · 1 not found`) and one primary `Add N copies`. Success shows a highlighter `Added …` status in the dialog; the collection refetches behind it.
- **Precons add directly** (a job; `Keep it`: Suggested / Keep built / Break into loose cards); **deck URLs fetch first** (a job) and land in review before anything is written.

### Button and CopyButton
- **Button:** one component with `tone="chrome|paper"` and `emphasis="primary|quiet"`; primary fills amber, quiet variants are ruled outlines.
- **CopyButton:** wraps Button, copies generated list text, and announces result through `aria-live="polite"`.

### States
- **EmptyNote:** centered guide copy, no illustration.
- **ErrorNote:** `role="alert"`, rust heading, optional ruled retry button.
- **GridSkeleton:** pulsing card-aspect blocks with `role="status"` and `aria-live="polite"`.

## Do's and Don'ts

### Do:
- **Do** build all reusable colors through `web/tokens/*.tokens.json` → `web/src/styles/tokens.css` → `web/src/index.css` theme utilities.
- **Do** keep light mode as bone-paper guide sheets on dark charcoal chrome and dark mode as all-charcoal stock with bone ink.
- **Do** use amber only for highlighter/focus/active/primary/progress states.
- **Do** prefer `GuideCard` mapping in `web/src/core/guideCard.ts` so tile, row, grid, and preview stay shared across domains.
- **Do** preserve URL-backed controls from `web/src/core/search.ts`; filters, visibility, sort, density, and commander/set choices are shareable state.
- **Do** use `voice-condensed`, `voice-semi`, `tabular`, `highlighter`, `ruled`, `ease-guide`, and `paper-grain` instead of inventing one-off visual classes.
- **Do** keep mobile behavior as controls disclosure plus column tabs, not a squeezed desktop splitter; the collapsed disclosure shows a one-line summary of the active scope.
- **Do** put every card fact (owned counts, missing, pools, treatments, chase) in the caption under the card.
- **Do** keep the heading outline unbroken: sheet `h1`, family/column `h2`, groups `h3`.
- **Do** keep visual regression evidence pinned through Playwright's offline fixture suite (`web/playwright.config.ts`, `.playwright-mcp/final-*.png`, `.playwright-mcp/verdict-*.png`).

### Don't:
- **Don't** introduce raw colors in authored CSS; `web/.stylelintrc.json` forbids hex/named/rgb/hsl/oklch functions outside generated tokens.
- **Don't** use `transition: all`; the stylelint guard disallows it and components enumerate transitioned properties.
- **Don't** add React or UI imports to `web/src/core`; `web/.dependency-cruiser.cjs` keeps that layer portable and framework-free.
- **Don't** let components import views/routes; presentational components take props and stay reusable.
- **Don't** use dashboards cards, broad rounded corners, multi-accent category colors, or decorative gradients; the built system is printed stock, rules, and amber marks.
- **Don't** turn highlighter marks into persistent filled cards. The mark is a user annotation over the guide, not a new surface.
- **Don't** overlay anything on card art — no stamps, badges, counts or ribbons. The card image is the artifact.
- **Don't** render more than 5 options as chips; use `MultiSelect`.
- **Section heads (VirtualGuide):** every head is a disclosure (`aria-expanded` button inside the h2/h3, chevron left) with ▲▼ jump buttons on the right that scroll to and focus the previous/next head of the same level (`Next set family`, `Next set`, `Next card type`). Collapsing a level-1 head hides its level-2 sections. Level-1 heads say what they are inline beside the name (`BLOOMBURROW  SET FAMILY · BLB · BLC`, never a kicker above it); set sub-heads pair the code with the set name.
- **Sheet header vs section heads:** the sheet title names the view (`Collection`) and its summary describes what the current filters SHOW; family heads carry family-wide facts (progress, owned/printings, copies, value). Never repeat the same numbers at both levels.
- **Buy (bulk buy lists):** sidebar section `Buy` (single-word section titles); a label line `Copy bulk lists · 157 missing shown` (or `· 3 marked`) over a full-width ruled strip of equal 32px-tall cells, one per store (names beside the marks when the strip is ≥21.5rem wide, marks only when narrower): a monochrome store mark in amber (`StoreMarks.tsx`, drawn on a 24px stroke grid after each store's logo). Hover darkens the cell and lifts the mark 1px; a successful copy swaps the mark for a ✓ for 1.6s. Each cell has `aria-label`/`title` `Copy <Store> list`; one shared polite status line, where a store that can't take exact printings (Card Kingdom) says so. Kept small on purpose: an occasional action for most collectors. Owner-approved exception to the Amber-Only Rule: store marks are amber at rest.
