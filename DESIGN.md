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
**Label/Mono Font:** no mono face; numeric tables use `font-variant-numeric: tabular-nums lining-nums`. One exception: the browser companion's *Show the raw data* JSON (`pre`) uses the system mono (`ui-monospace, monospace`) because it is literal data; addresses and ids elsewhere stay Archivo semi + tabular.

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

**Scrollbars** are part of the stock, not the OS: a slim pill thumb on a clear track (`::-webkit-scrollbar`; Firefox gets `scrollbar-width: thin`), tinted per surface through `--sb-thumb` — `theme.scrollbar-chrome` on chrome, `theme.scrollbar-paper` on paper sheets and dialogs — darkening on hover and lighting amber while dragged. Because they're always drawn, a row that scrolls sideways (`overflow-x: auto` — tab rows, the nav) must not overflow vertically, or it grows a stray vertical thumb: hang the **row** over its rule (`-mb-*` on the row), never the tabs inside it (`e2e/scroll-rows.spec.ts` guards this).

Hairline borders are the main geometry. `ruled` is a 1px bottom border; column and section headings use 2px `rule-strong`; split separators use a 1px vertical rule plus a pill handle. The `highlighter` utility is a ragged linear-gradient stroke behind text/rows, not a rectangular selected background.

## Components

### AppShell + ViewLayout
- **Purpose:** global masthead, primary nav, status icons, the Settings gear, sidebar-below-nav layout.
- **Nav:** Collection · Decks · Explore · Market. On phones the tabs tighten (smaller condensed type, no gaps) so all four fit at 360px. **Jobs is not a destination:** background jobs are housekeeping, so they sit at the right as a quiet queue-mark icon (tooltip *Background jobs*, amber dot while one runs) — never a nav tab or a word. Phones show it only while a job runs; Settings → About always links to the list.
- **A quiet masthead:** right of the nav sit only status icons and ONE gear — Restore point (when one exists) · Browser companion (flag) · Jobs · **Settings** · (hosted only) **Account**. Every one is the chrome tone of `IconAction` (`tone="chrome"`, or `iconActionClass('chrome')` for a router `Link`): 36px box, 18px bone-muted glyph, `chrome-raised` fill on hover/focus/open, the shared tooltip, a 52px hit area on touch (`touch-hit`). No words, no segmented controls in the masthead.
- **Restore point:** a quiet undo-arrow icon, shown only once a restore point exists (tooltip `Restore point · 3:31 PM`). Confirm dialog (`Restore your collection to 3:31 PM?`): why it was taken, a plain list of what changes (`3 fewer copies`, `1 more deck`), and that it swaps — restoring again comes back. One slot; taken automatically before the first change of each session.
- **Settings (gear):** ONE paper dialog for preferences, ruled sections in order: *Appearance* (`Theme: Auto | Light | Dark` — Auto follows the OS), any **view-registered sections** (`useSettingsSection` in `web/src/app/settings.ts`, shown only while that view is mounted — e.g. Collection's *Missing means*), *Privacy*, *About* (one sentence + ruled links: Background jobs, Analytics when the `analytics` flag is on). Each preference is a `SettingsRow` (name, one plain sentence, control at the right; stacked on phones) and single choices use `SettingsChoice` (the sidebar segmented shape in paper tokens) — `components/settings/SettingsControls.tsx`. A setting that changes how a view *reads* rather than *what it shows* belongs here, not in the sidebar.
- **Privacy** (in Settings): one ruled section per purpose — *Error reports* · *Usage analytics* — each a label, an amber Radix switch (on = amber, the one active language), one plain sentence, and a *What's recorded (n)* disclosure listing catalog events with their purpose; then retention in one sentence and a quiet *Delete my analytics data* button with a polite live result. Hosted users who haven't chosen see the same choices once, on first visit, in a standalone *Privacy* dialog with *Save my choice* (`PrivacyPrompt`). Never a banner.
- **States:** active nav uses amber underline; the jobs icon shows an amber dot when queued/running; theme can be system/light/dark and persists to `localStorage` as `mm.theme`.
- **Sub-nav strip (`ViewLayout` `subnav` slot):** a section's modes (Collection `Cards · Purchase history`, Explore `Rankings · Cards · Surfer`, Market subjects) sit in ONE full-width chrome strip directly under the top nav — above both the rail and the sheet, because a mode scopes both. Views fill it with `subnav={<SectionTabs label=… tabs=… />}`; inside the slot `SectionTabs` takes the strip look: small semi-condensed caps in `on-chrome-muted`, `on-chrome` + a 2px amber underline on the active mode (quieter than the top nav's large condensed words and 3px underline), a `chrome-line` rule under the strip, left edge aligned with the rail's content. Fewer than two modes → no strip at all. It never collapses into the rail's phone disclosure. Never put modes in the rail or as a grid of buttons.
- **A11y contract:** skip link to `#main`, `nav aria-label="Primary"`, `main tabIndex={-1}`, sidebar labelled by the view, mobile disclosure uses `aria-expanded`/`aria-controls`; the sub-nav is a labelled `nav` whose current mode carries `aria-current="page"` (or the router's `data-status="active"`).

### Sign-in + Account (hosted only, `MM_MODE=hosted`)
- **Sign-in screen** (`components/auth/AuthGate.tsx`): while signed out NOTHING of the app renders — bare chrome, then ONE bone-paper guide sheet (27rem, top third, dialog shadow): the `magic-manager` wordmark in condensed display over the one-line purpose, a strong rule, then one plain sentence (*Invite-only. Sign in with the account you joined with.* / *You're invited. Choose the account you'll sign in with from now on.*), a rust `role=alert` sentence when a sign-in was refused (`core/auth.ts` `AUTH_ERRORS`: problem + way out), the providers as full-width ruled paper buttons (`Continue with Discord`/`Google`, links via `buttonClass`), and a hairline-ruled muted footer saying exactly what we keep. No logos, no hero art. `?invite=` / `?auth_error=` are read once and removed from the address bar.
- **Account** (`components/auth/AccountButton.tsx`): the LAST masthead mark, a chrome `IconAction` person glyph (tooltip *Signed in as <name>*) opening a chrome-raised popover: name, email, *Admin* in muted lines, then a full-width ruled *Sign out*. Local mode renders neither.

### GuideSheet
- **Purpose:** paper/stock host for each view's compact header and guide body.
- **Compact header (every view, every variant):** the title is never printed — it stays the page's sr-only `h1` (the nav tab, the sub-nav strip and the body's own group heads already say where you are; where the body has one group, that group head is the visible title). One line holds the `summary` (counts, freshness — muted tabular) at the left and the header **action icons** at the right; with neither, the header takes no space. `hideTitle` is obsolete (accepted, no effect).
- **Header actions:** pass bare `IconAction`s as `actions` with an `actionsLabel` (the sheet renders the labelled `role=toolbar`); pass `marked={{ count, getText, onClear }}` when the view has markable cards and the sheet adds **CopyMarked** last. Main-view actions (refresh, open on a vendor, surf, copy marked) live here — never in the filter rail.
- **CopyMarked:** two offset sheets, the front one ruled with three dotted list lines (`CopyListMark`); an amber pill badge with the tabular count (`99+` past 99) when N > 0; disabled at 0 with tooltip `Mark cards to copy them as a list`; enabled tooltip `Copy 7 marked cards as a list`; after a copy the glyph swaps to a ✓ and the tooltip reads `Copied` (result announced politely); a small muted × beside it, `Clear marks`, while anything is marked.
- **Style:** `paper-grain`, `bg-paper`, `text-ink`, `rounded-sm`, ambient sheet shadow.
- **States:** empty, error, and skeleton states render inside the sheet rather than replacing the shell.
- **Sheet tabs (`nav` slot, legacy):** superseded by the sub-nav strip; views move their `SectionTabs` to `ViewLayout`'s `subnav`.

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
- **Empty state:** when the tag cache was never synced, a chrome-muted note links to Jobs → Sync card and art tags.

### Collection sidebar
- *Find* — `Card name` alone. *Show* — `Set families` first, then `Cards: Owned | Missing`, `Acquired from`, `Rarity`, `Finish`, `Treatment`, `Chase`, `Function`, and *Reset filters* (clears the name and every Show filter except the families; sort, view type and Missing means are not filters and stay). *Arrange* — `Sort`, `View type: Grid | List`. *Buy* — the `CopyTargets` strip with *Check my cart* right under it: a copy result briefly takes the strip's label line, so no blank status line is reserved.
- Modes `Cards · Purchase history` in the sub-nav strip (`CollectionTabs`). Sheet actions: *Bulk modify counts* · *Add cards*, then *Copy marked* (`GuideSheet marked`; Clear marks lives there, not in the rail).

### Missing means (Collection)
- A **Settings → Collection** preference, not a rail filter: `Missing means: This printing | The card` (`SettingsChoice`). **Default is *This printing*** — the exact printing you don't have (the collector's view). *The card* (deck-building flavor, opt-in) keeps only missing printings of cards you own in **no printing from any set** (`card_owned` from the engine) — the gaps in what you can play — and the sheet summary switches to `N cards you own in no printing · $X at the cheapest printing of each`. Persists in this browser (`localStorage` `mm.collection.missingMeans`, `views/collection/missingMeans.ts`), not the URL. The rail keeps one ⓘ beside `Cards: Owned | Missing` that names the current meaning and points to Settings.

### Find products in your cards (Purchase history)
- Sheet action icon on Purchase history (it is about where cards came from) → dialog that scans at once (`trueup.scan` job: progress rule `Checking products · n of N · <product>`; first scan reads every product list, minutes; later under a minute). **Review:** `Your cards complete · N` — one ruled row per product (checkbox checked by default, name, `type · SET · year`, `N cards · $`), unchecking strikes it through and remembers it as *not mine* (never suggested again, `localStorage`). `Shared a card with another product` rows carry *I opened this one* (re-scans with that pick). Commit: `Record N products` (`trueup.apply` re-checks exactly the reviewed list and refuses if your cards changed) → `Recorded N products. M cards now show where they came from under Acquired from.`

### Check my cart (Collection · internal, `cart_check` flag)
- Hidden unless the flag is on. A quiet chrome `Button` (*Check my cart*) under the Buy strip opens the dialog. Under the title a **paper store switch** (`StoreSwitch`: the sidebar `Segmented` shape in paper tokens — `rule-strong` border, `ink-muted` off, amber on) picks *Mana Pool · TCGplayer · Card Kingdom*; when the companion lacks that store's permission an ink sentence names the companion switch and *Read my cart* is disabled. The bookmarklet and Keychain-login ways show for Mana Pool only. Before a read it lists the **ways to read the cart** as ruled sections (no cards), each with its own button and inline failure: *In this browser* (the browser companion, `companion` flag; primary **Read my cart**, disabled with a pointer to the header plug icon when not connected), *With the bookmarklet* (a dashed amber draggable link `mm · Mana Pool cart` + a paste box + **Check pasted cart**), and *With your login on this computer* (only when the Keychain login exists). After a read: a muted "<Store> cart · read in this browser by the companion." source line, any read notes, then the result sections `Bought twice` · `Already in your collection` · `Over market` (red `+N%`; a muted line beneath counts played / non-English lines left out — market is Near Mint English) · `Still missing from <FAM>` (≈ $) · `Not single cards` (sealed, `not checked`) · `Couldn't identify`; a line's meta adds its condition / language when it isn't NM English (`LTR 246 · LP · Japanese`), and **Check again** returns to the ways. **Never ask users for Mana Pool credentials.**

### Browser companion (header plug icon · internal, `companion` flag)
- **Header indicator** beside Undo/Jobs: a plug glyph with a state dot — amber (connected), rust (update available), hollow ring (not connected), none while it's still looking. No word beside it. The tooltip / `aria-label` says it in full (`Browser companion · connected · v0.4.2`, `… · update available · v0.4.1 → v0.4.2`, `… · set up · not connected`). No polling beyond the bridge's hello/ping. Opens a ruled **setup dialog**: status line (`Connected` highlighter + version; or "Not connected" + this app's exact address in a sunk code chip + *Copy this app's address*, since pairing needs exactly that origin), an ordered **Install** list (download link, `chrome://extensions` + copy, the app address + copy, reload), **What it can read** (one ruled row per feature with On/Off at the right) and **What it never does** (a plain bullet list).
- **Approval is never in the app.** While the companion's own window is open, the app shows one status sentence: "Waiting for you to approve in the companion window — <summary>. Nothing is sent until you press Send there." and the button reads *Waiting for approval…*.
- **Deals → Read watched prices** with the companion connected: a muted line above the table says "Open-tab stores are read in this browser by the companion"; the same awaiting sentence, `FailureNote` and read-note lines as Read my open tabs. The companion window is two-step (the page list with *Read these pages* / *Don't read*, then the readings with *Send* / *Don't send*).
- **Failures are coded, never generic** (`FailureNote`): the message in danger ink, the fix on the next line in ink, then `Code <area>.<reason>` in small muted tabular type so users can quote it. Your own *Don't send* renders as a status in ink, not an error. Codes and copy live in `extension/errors.json`.
- **The extension's own pages** (`extension/src/page.css`) use `extension/src/tokens.css`, GENERATED from `web/tokens/*.tokens.json` by `scripts/build_extension.py` (`--check` keeps it in sync; never hand-copy a colour), and the bundled Archivo Variable face (`extension/src/fonts/`, latin wdth axis, OFL — no remote fonts) with the app's `wdth` voices (bone paper / charcoal, amber accent, light + dark by OS setting): condensed bold title over a 2px rule, uppercase ruled section heads, ruled tables with tabular numbers (the approval table is name-first: each row's card name with a muted detail line under it — set + `#number`, finish, treatments, condition, non-English language — beside Qty / Each, so it reads at the 460 px window; store and Scryfall ids live only in *Show the raw data*), a sticky action row with *Don't send* (focused) and the amber **Send to magic-manager** (enabled after 1 s).

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
- **Dialog (`CardInspector`, rendered once per `VirtualGuide`):** large Scryfall image left (stacked on phones), then name (`Dialog.Title`), type line, a `dl` of Printing · Mana value · Value (nonfoil / ✦ foil) · Cheapest (`CheapestPrinting`: the card's cheapest nonfoil and ✦ foil printing, `SET #cn` or `this printing`, with a muted scope — `among synced sets` at first; a trailing refresh icon *Recheck for cheapest* checks every printing once (then goes away), and the scope reads `checked all printings · 9:55 AM`; the scope line shows only beside a found price; no vendor named) · Owned · Functions, the printed Tags, Tagger chips, *Your copies* (`6 owned · 2 in built decks · 4 unused`), and, under a small `View on` label, ONE row of identical ghost links each led by its mark: `Scryfall` · `TCGplayer` at the left (TCGplayer = name search), the in-app `Explorer` at the right (no fill until hover, same as the others).

### Sheet actions + external links
- **Sheet actions are icons** (`IconAction`: amber-ink mark, tooltip names it, `paper-sunk` wash on hover/focus — **no lift, no underline**; a pressed toggle (`aria-pressed`, e.g. *Bulk modify counts*) keeps the wash plus an amber underline) grouped in a `role=toolbar` — Collection: *Bulk modify counts* · *Add cards*; Purchase history: *Read my orders* · *Find products in your cards*; Decks: *New deck* · *Import a deck*. Outbound links are ghost links (mark + label, same wash). Reserve the filled amber `Button` for a flow's single commit (e.g. `Add 8 copies`, `Save deck`, `Record 3 products`).
- **Icon action** (`IconAction`) = the same treatment without the words, for a ROW of related actions where labels would crowd (the deck header). The tooltip carries the words and is the accessible name; disabled icons go muted with a tooltip naming why. Two or more sibling actions → icons; a lone sheet action keeps its label.
- **Every link or button that leaves the app carries the destination's monochrome mark** (`StoreMarks.tsx`, 24px stroke grid, `accent-ink` on paper / `accent` on chrome) instead of a generic ↗. The word is optional: keep it where there's room and the pair scans faster (inspector, phones' buy strip); drop it in tight rows (desktop buy strip), keeping `aria-label`/`title` `Open on <Site>` / `Copy <Store> list`. New external targets get a mark drawn after the site's own logo before they ship.

### Explore (`/explore`, was Commanders)
- **One card, a chosen role.** Sidebar: `Card` (any card) + `Compare with` (optional) + `Explore as: As commander | As a card` (commander disabled with a reason when a card can't lead; unset = commander when it can). Both sides of a comparison share one role.
- **Card plate** above the guide: art (opens the inspector), condensed name (+ `A`/`B` marker when comparing), type line, a fact line (`Played in N of M possible decks (x%)` · Salt ⓘ · From $ · You own n · m free), Tagger tags, the deck mix ("Typical deck it's in"), and ghost outbound links with marks (EDHREC · Scryfall). Comparing: plates sit side by side with a quiet `vs`, compact (smaller art; tags move to the tag split row: Only A · Both · Only B).
- **As commander:** the commander's recommended cards (single) or today's three resizable columns `A only · Both · B only` (compare).
- **As a card:** sections `Commanders that run it` (share of their decks), `Played alongside` (by type, lift order, `1.09× lift` notes), `Similar cards`; comparing splits each into the three columns, the Both column carrying both shares as stacked bars and both lifts in the note. Descriptive only — never a verdict.
- **Combos** (plate nav, loop mark, `aria-expanded`): toggles a ruled `Combos with <card>` section under the plates (max 40dvh, scrolls), fetched on demand — the card's most played Spellbook combos, pieces you don't own in muted ink, `you own 2 of 3` in the meta line.
- Every card inspector has `Explore this card`.
- **Card surfer** (Explore's third tab, *Surfer* — tabs Rankings · Cards · Surfer; URL `mode=surf` + `surf`, one key holding the source + filters via `core/surf.ts`; a legacy `?surf=` link with no mode opens it): an endless vertical feed of random cards for calm browsing — the art leads. Layout: the standard `ViewLayout` — filters in the chrome rail (collapsing like every rail below 64rem), the feed in the paper sheet under the tabs with the summary `1,470 match · 12 seen` and icon actions *Shuffle* · *Open results in Scryfall*. Each card is one `article` (≥ feed height, `snap-y proximity`): the full card large (≤30rem, sized to the viewport), then the name (condensed display), type line under a 2px rule, the **flavor text set to be read** (`text-lg`, ≤46ch, no italics/quote marks added), a `dl` Artist · Printed in · Price · Yours (accent-ink), *More art like this* (the artwork's art tags as hairline chips — pressing one adds it to the filter), a `Rules text` disclosure, and the ghost links Scryfall · TCGplayer · Explore this card. DFCs get *Turn over · <face>*. Keys: `j`/`k` step cards (the feed is focused on open). Rail: `Draw from: All of Magic | Your cards`; *Art & printing*: Art tags (chips, amber with ×, suggestions from the tag cache; Enter adds the typed tag), Set (MultiSelect of every paper set family, newest first), Treatment, Artist (applied on Enter/blur); *Card*: Color identity (W U B R G C pips, letters shown, names for AT; colorless excludes colors) + `Exactly these | Within these`, `Flavor text: Any | Has it | None`, Card type, `Legendary: Any | Legendary | Not`, Rarity; `Reset filters · n`. The next 3 cards are drawn when the reader is within 1.5 screens of the end; states: skeleton card, `No cards match` + Reset, `That’s every card that matches — N cards` + *Shuffle and start again*, inline retry on a failed draw.
- **Rankings** (Explore's first tab, URL `mode=rankings`; with no card picked Explore opens on it). Rail: *Find* card name; *Show* `List` (Top commanders · Top cards · Saltiest cards), then **Color identity · Tag or creature type · Set family laid out together, each *Any*** (they combine — the engine reads the most selective axis from EDHREC and narrows the rest locally; on Top cards / Salt the three stay in place, disabled, with the note *Color, tag and set narrow top commanders.*), `Timeframe: Week | Month | 2 years` (disabled with a reason where EDHREC has none: salt, a set, a tag alone), `Ownership: All | You own | Unused`; *Arrange* `View type: Grid | List`. Sheet header: summary `N ranked · you own n · n unused · read <when>` + icon actions *Refresh* · *Open results in EDHREC* · copy marked. The first 100 rows show; *Load N more* (50 at a time) closes the list. A list EDHREC leaves empty is a calm note (*EDHREC lists no commanders from <set> yet.*), never an error; job failures never show exception names. URL keys `rank color tag fam tf own rq rview` (`own=free` still read as unused).
- **Ledger** (default): one ruled table row per ranked card — mark toggle · `#` · art crop (opens the inspector) · name (+ type line when wide; a real link that opens the card profile in the matching role: commander rankings → *as commander*, top cards/salt → *as a card*; hover previews art) · `Decks` (compact) or `Salt` ⓘ · `From` cheapest price · `You own` (`2 · 1 free`, free in accent-ink, `—` when none). Numeric columns are fixed width; art/From/type line drop out by container width. *Grid* reuses `VirtualGuide` (caption note `#3 · 5.1K decks`).
- **Cached reads are instant;** a ranking never read starts the `edhrec.rankings` job at once (`ProgressRule`: `Reading 1 of 1 · Matching 100 cards to your collection` + a one-line "first time" note). Sheet summary: `100 ranked · you own 47 · 41 with free copies · read from EDHREC 9 days ago`; actions: *Read again from EDHREC* (`RereadMark` icon; progress rule above the list, the old list stays) and an `EDHREC` ghost link to the same page.
- **ProgressRule** (`components/ProgressRule.tsx`): the shared thin amber job rule (`<Verb> n of N · step`), used by Market pricing and Rankings.

### Market (`/market`)
- **The value guide, literally.** Modes are the sub-nav strip `Set family · Deck · Secret Lair` (+ `Deals` with its flag; URL `subject`, switching closes the open item) — never rail buttons. Each mode's rail follows Find → Show → Arrange with a field label on every control; the family / deck is a searchable one-of picker in *Show* (`SearchSelect`: filter box over a listbox; ↑/↓, Enter picks, picking closes). The sheet prints no title; its summary leads with the family or deck name. Copy follows *Value vs Price*: a sealed product's market figure and its cards are *values*; *price* is only a store's asking price (Deals best price, targets).
- **Set family → Sealed** (rail: *Find* `Product name`; *Show* `Set family`, `Product type: Sealed | Singles`): ruled guide table grouped by product category (`Booster boxes · 2` sticky-style heads): `Product · Sealed · Cards inside ⓘ · Difference`. Difference is signed; cards worth more than the box reads `+$` in accent-ink, otherwise muted `−$`. When some fixed cards have no price at their exact printing (e.g. Collector's Edition foils), *Cards inside* shows `$X+` (muted plus; tooltip `N of M cards have a price…`) and Difference stays `—` — unknown is never $0. Valuing runs as the `market.value_family` job (a thin amber progress rule `Valuing 13 of 36 · <product>`; cells show `…` until priced; results kept 12 h per family in `localStorage`). A product row discloses its contents tree (`Contents · Market · Cards inside`, indented per level) plus fixed-card totals at these vs the cheapest printings and a TCGplayer ghost link.
- **Set family → Singles** (URL `tab=cards`): `Card (SET CN · treated) · This printing · Cheapest (SET CN where it differs) · Premium · Foil premium · You own`; *Show* adds `Printings: All | Not cheapest`, `Foil premium ⓘ: Any | Foil cheaper | Under 25% | Under 50% | Under 100%` (URL `foilMax`; `Segmented wrap`); *Arrange* sorts by premium / value / smallest foil premium / set; 200 rows then `Show more`. *Foil premium* is the plain foil vs nonfoil of the same printing from local prices (`+45%` with the signed `$` gap muted beside it); fancy foils read a muted `fancy foil`, one-finish printings `foil only` / `no foil`. The column hides on phones until a foil cap or the foil sort is active, then it's shown.
- **Deck:** a three-row **ledger**, not hero metrics: `Buy it sealed` (precons; the product named beneath) · `Buy every card` · `Use your unused cards first`, × `Deck’s printings | Cheapest printings`; the lowest cell is bold accent-ink with a `lowest` tag. Then `To buy` and `Covered by your unused cards · worth $` line tables (column `Unused`). A muted basis line under the ledger says where the cheapest printings come from (`Cheapest printings among the sets synced here.`); the sheet header's refresh icon *Recheck for cheapest* (the inspector's A12 pattern, no vendor named) → URL `live=true`, re-costs with a live floor once, then goes away and the line reads `…rechecked across every printing · 9:55 AM`. Rail: *Show* `Deck`; *Buy*: `Printing: Cheapest | Deck’s` + the store-mark copy strip. Decks' toolbar gains *Cost to build* (price tag mark) → here.

- **Deals** (internal `deals` flag; third subject): the watchlist is the only view — ONE product table + inspector (`DealsWorkspace`: resizable split like Deck Manager, list 60 / inspector 40, one panel at a time on phones with `‹ All products`). Sheet header actions (upper right): **Read my open tabs** (tabs icon; on demand, never cached — reads the tabs, then their prices with `deals.read_prices`, in one action; progress `Reading prices from your open tabs · 3 of 12 · store`; errors that apply to the whole read, e.g. Chrome's *Allow JavaScript from Apple Events*, show once) and **Read watched prices** (refresh icon). A read of your tabs is pinned at the top of the table as a **From your open tabs** row group (accent-ink uppercase group heading + count + `Dismiss all`, like Purchase history's *Needs review*; a muted `Watching` group heading follows): matched products you don't watch yet (normal cells, `Watch` / `Dismiss` text actions under the name) and listings that aren't a known product (ambiguous, unmatched, skipped, unreadable — a short status line, the price, `Dismiss`). Products you already watch merge into their watchlist row. Dismiss hides a row until the next read. A muted status line after the read says where it came from (`3 of 3 windows read · 12 product pages · 4 new to review · 2 pages at stores without a recipe yet (host)`). Old `?deals=tabs|watching` links land here. The watchlist is instant (no valuation); *Read watched prices* runs `deals.watchlist` `{refresh: true}`; when that read meets targets a ruled notice (2px rules above and below, no fill) sits above the table — `1 product hit its target` in a highlighter mark, one line per product (name button → inspector, price, `at Store ↗`, `target $`), `Dismiss`. **Table** (one row per product; the same product at several stores is one row): Product (button; `SET · Type`) · Best (price, store, `↗` link, trend arrow, `Sold out` in red; a watched product with a target shows `target $` muted, or — when met — the price in a highlighter mark and `at target $` in accent-ink) · Gap vs the chosen basis (`−21%` accent-ink under, red over, `$` under it) · Sealed · Cards inside (exact, `cheapest $` and the cards + boosters split beneath, `+` when some cards are unpriced); Sealed and Cards inside drop out by container width. A muted line counts `12 of 17 products · compared to …`. Values fill in as each product's cost loads (muted `…`; `—` on error). **Rail**: *Find* `Product name or set`; *Show* Stores, `Product type` picker with counts, Compare to (Sealed | Exact | Cheapest — sealed value or the cards' value), Discount (Any | 10%+ | 20%+ | 30%+ under that value), `Availability: Any | In stock`, `Target: Any | At or under`; *Arrange* Sort; changing a filter keeps the open product only while it still matches; *Nothing matches these filters* offers `Clear filters`. **Inspector**: name · `SET · Type · released` with Watch / Stop watching (confirm; a single is watched as its exact printing + finish); *Stores* (underlined link ↗, price, stock, read age, trend, per-store errors, *Read from your open tab — keep the page open to read it again*, *From your open tabs — not watched at this store*; for a listing read from your tabs `Matched to <name>` with `not this?` / `you confirmed this · change` / the picker + `This one` — a save opens the product it now is). A pinned listing opens a listing inspector (store, price, why, the picker when ambiguous, `Dismiss`); for watched products **Target price** (status sentence — `Target met` in a highlighter mark when the best in-stock price meets it, else `Target $ … $ to go` — then an inline form: `Target as` radios *A price | % under sealed value*, one field with `$`/`%` affix, primary `Set target`/`Update target`, quiet `Remove target`) and **Price history** (one step line per store — the store cheapest today solid ink, the rest dashed ink-muted, never coloured; dots per reading; your target as a highlighter stroke labelled `target $` in accent-ink; HTML price/date labels beside a hairline-ruled plot; `role="img"` with a one-sentence summary; a First / Low / High / Now table per store with line swatches; `All N readings` disclosure table — the text alternative); one price so far shows a sentence instead of a chart; *What it's worth* ledger (sealed value, cards inside exact / cheapest, boosters' expected value, totals, each with its gap to the best price; unpriced-cards note); *Contents* (the product tree, market beside cards inside); *Cards* (sortable by price columns). Reader warnings (a second automation Chrome, windows not read) show as plain sentences with the fix; with a warning and no store tabs the empty state says *Couldn't see your store tabs*.

- **Secret Lair** (subject, always on; URL `subject=sld`): the newest drops (Drops: 10 / 30 / 60 / 120 newest, `sldN`), one row per drop at the sidebar's `Edition: Regular | Foil` (a drop sold in one edition shows that one with `foil only` / `regular only`). Shares the Deals building blocks — `MasterDetail` (split / one-at-a-time on phones, `‹ All drops`), the same table rhythm, `CardLines`, the ledger `Row`. **Table:** Drop (button; release date, `· watching`) · Sealed · Gap (sealed vs the *Compare to* cards: `−33%` accent-ink when sealed is cheaper, red when dearer, `$` beneath) · Cards inside (the compared total, the other basis muted beneath, `+`/unpriced note); values fill per row (`…`, `—` on error) and the status line counts `pricing N…`. **Rail:** *Find* `Drop name`; *Show* Drops (count), Edition, Compare to (`Exact | Cheapest`, URL `sbasis`), Discount (Any | 10%+ | 20%+ | 30%+); *Arrange* Sort (biggest discount % / $, lowest sealed value, newest, name). **Inspector:** name · `SLD · Secret Lair · Regular edition · released`; *What it's worth* ledger (Sealed value + source, cards inside exact / cheapest each with sealed's % vs it, the bonus card's expected value when it's a random bonus pack; a sentence naming the bonus card; `TCGplayer ↗`); *Contents* tree when the bonus is a pack; *Cards* with a small accent `bonus` tag on the bonus card's line. *Watch* (deals flag only) tracks the drop at its TCGplayer product page, refreshed from its TCGplayer **market** price (store `TCGplayer market` in Watching) — disabled with a tooltip until TCGplayer lists it; `Stop watching` confirms. A foil-only drop (named `… Foil Edition`) matches its watched entry by `watchKey` (the watchlist returns it without the suffix).

### Deck Manager (`/decks`)
- **Every deck recipe, one list:** catalog precons and Jumpstart pack versions (MTGJSON) plus your imported and hand-built decks — card pools (land packs, scene boxes, most Secret Lair drops) never appear. **Opens on what you own** (built + loose + your decks); *None* in `You own` brings in the ~1,000 catalog recipes you don't own. Jumpstart is a kind of precon here, not a sheet of its own (old `/collection/jumpstart` links redirect).
- **Two resizable panels** (list ~1/3 · inspector ~2/3, `react-resizable-panels`, persisted); phones show one at a time (list → recipe, `‹ All recipes` back).
- **Recipe list:** pinned ruled group heads (`Group by`: Set · Year · Kind · Deck type · Colour · Ownership; newest first; `12 recipes · 3 ready`), the list virtualized (`@tanstack/react-virtual`, current head pinned). One ruled row per RECIPE: art crop (dimmed `opacity-55 grayscale` when you own no copy, a ruled blank before its card list is read), the name on its own line, then the **kind mark** (`PRECON` / `JUMPSTART` / `IMPORTED` / `CUSTOM` — a hairline-ruled condensed uppercase label, no fill, never amber) · the **ownership mark** (`×1 BUILT` accent-ink · `1 LOOSE` / `NOT BUILT` ink · `NOT OWNED` muted) · `type · SET · year`; right: value over free-card coverage (`All 20 free` / `2 short` accent-ink, `9 of 20 free` muted; built recipes show none), or a muted `not read` before the first read. The open recipe carries the highlighter; ONE tab stop (roving ↑/↓, Home/End, Enter opens; off-screen rows scroll in first).
- **Sidebar:** *Find* — the search field alone (`Deck, set or author`). *Show* — `You own: Built | Loose | None` toggles with counts, `Kind` · `Deck type` · `Set` pickers (counts under the other filters), `Free cards: Any · Ready to build · Ready or close`. *Arrange* — `Group by`, `Card view: Grid | List`. *Buy* appears only when the list is narrowed to ONE set that has Jumpstart packs (Jumpstart's two lists): `Shop for: Every theme | Packs I don’t own` ⓘ over the store strip (`Copy bulk lists · 421 cards to build every theme · ≈ $292.62 at market`). Sheet summary (a polite live region): `277 recipes · 269 built · 8 ready from free cards`, replaced by the read job's `ProgressRule` while it runs. Sheet actions (icon toolbar): with one set in view *Read N unread recipes in SET* / *Read SET recipes again* (`decks.read_recipes`) · `New deck` · `Import a deck from a link` (saves the decklist only, never built; *Also add these cards to my collection* continues into the add-cards review).
- **Inspector — a deck you track:** deck title + one fact line (kind mark · type · set · year · source · author · cards · value · built/pledged % · loose · free-card coverage), then a toolbar of **icon actions**: *Add deck cards to collection* (opens the add-cards review; nothing is written until its commit) · *Edit deck* — or *Copy to edit* for precons, whose decklists are read-only reference data · *Build from your cards* (confirm dialog: N of M free, the missing list, `Build deck` / `Build with N missing`) · *Break down* (confirm: cards return as free copies, the list stays) · *Cost to build* · *Combos* (loop mark; a dialog fetched when opened — the editor's Combos body without `+`). Marked cards add `Add N marked cards to collection` + `N marked · Clear`. An ⓘ defines built / pledged / free; phones get a `List view` / `Grid view` switch in the header. Cards render through `VirtualGuide` sectioned like a decklist: Commander · Companion · Creatures … Lands · Sideboard · Maybe · Tokens; captions add `×N in deck · M pledged` and `N free to use`.
- **Inspector — a catalog recipe you don't own:** name, kind mark + `product type · set · year · colour · N cards · $`, facts `Free cards cover 32 of 100` (accent when ready) · `Short` · `You own No copy` ⓘ (free / ready / close; each recipe checked on its own), one icon action *Add this deck / pack to your collection* (confirm: `Add and keep it built` / `Add the cards loose`, the `ingest.precon` job; the row then becomes your deck and stays open). **First open reads it:** the `decks.read_recipes` job starts at once (`ProgressRule` + a one-line "first time" note in a live region; failures show the error with *Try again*); afterwards it opens at once. Cards sectioned like a decklist; captions `6 free` / `1 of 2 free` / `None free`; a card your free copies don't cover reads as missing (dimmed).

### Purchase history (`/collection/history`, a Collection sheet)
- **One view for where cards came from:** ledger entries AND store orders (flag `purchases`) — there is no separate Store orders tab. Modes `Cards · Purchase history` in the sub-nav strip; sheet actions *Read my orders* (flag) · *Find products in your cards* · *Copy marked* (the open entry's marked cards).
- **Same split as Deck Manager** (shared `SplitPanes`; list 40 · inspector 60; phones one panel at a time, `‹ Purchase history`).
- **Needs review (pinned):** store orders not fully added (`Not added yet` / `Partly added`) sit above the timeline under an amber-ink `Needs review` head (`N orders · paid $`) with a one-line explainer; rows = date, `Store order #n`, `Store order · status · copies`, right column `Paid / Worth / Gain`. Selecting one opens the order review in the inspector (`order=<id>`). **Every order shows once:** an applied order is its `purchase` ledger row (status in its sub-line); a partly-added order's ledger row is hidden while it waits under Needs review; a read order with no ledger event (`Recorded only`) is its own timeline row at its order date. Filters (kind *Store order*, From/To, search on store / order number / status) apply to orders too; all-orders `paid · worth (gain)` totals ride the sheet summary (`core/history.ts mergeOrders`/`filterOrders`).
- **Timeline:** newest first, sticky month heads with `N held · $` totals; one ruled row per ledger entry — day, title (product name, `Checklist · Set`, `Added from search`…), `Kind · SET · file` and `identified` when Find products dated it, value + `+in −out` on the right. Pre-ledger ingests show `N rows` muted instead of value. **Deck moves are quiet:** smaller muted single lines, and a day's moves gather into one run row (`Built 4 decks`, chevron expands). `Provenance unknown` titles are muted. ONE tab stop (roving ↑/↓, Home/End).
- **Sidebar:** *Find* — search (product, set, file, order) · *Show* — `Kind of entry` picker with counts · `From` and `To` day fields stacked full width (`DateField`; side by side clipped the date) · `Clear filters` · a glossary of the kinds (Precon, Card pool, Singles, Checklist — source product not recorded, Unknown, Deck move, Store order).
- **Inspector:** title + fact line (kind · date · set · file, ⓘ kind help), a plain dating note when the date isn't the purchase (*Identified in your cards by Find products — not the purchase date*; *Reconstructed when the ledger began*), facts `Came in · Removed / Moved to products · Still held · Worth today`, `Open deck` for playable products and moves, then the exact printings through `VirtualGuide` (list by default) sectioned by type, held copies as the owned count, `+in −out` captions only when copies left. Pre-ledger entries explain where their cards are counted and link to *Checklists before the ledger*; moves say nothing was bought. What was paid exists only for **Store order** entries: a `Paid` fact and *Review order* (opens the order review in the same inspector); other entries never show a blank paid field.
- **Store order rows (flag `purchases`):** status `Not added yet` / `Partly added` / `In your collection` / `Recorded only`; `Paid / Worth / Gain` (losses in danger ink, gains plain with `+`). Worth/Gain read `—` when nothing has a price today and carry a `cards` qualifier + tooltip when sealed or unpriced lines aren't valued. **Order inspector:** title, date · status · copies and the store's **verification mark** (`Verified` / `Partly verified` + ⓘ note — nothing unverified is presented as verified), facts (items paid, store subtotal, shipping, tax, fees, store credit, order total, worth, gain) and a plain note when the store's item list doesn't add up to its subtotal; two quiet actions *Match to cards I own* / *Add all as new* fill per-line Match/Add number inputs (clamped to what's left and what can be matched); non-card lines say *Recorded only — not added to your collection*; footer *Save to collection* (primary) with a one-line summary, and *Forget this order* only while nothing is assigned. **Read dialog:** 1 choose store (radio rows with the verification mark + note, and the companion switch hint), 2 read the order list, 3 tick orders (status per order, *Select unread* / *Select all*), read + save in batches of 100, then a result summary.

- **Revert this import (V35):** a quiet paper button in the inspector header, only on entries the engine marks `revertible` (singles, pasted/deck imports, scan sessions, collection imports, additive set checklists). It opens `ConfirmDialog` with the engine's dry run: one plain lead sentence (*This removes 12 copies (9 printings) from your collection and deletes the decklist Goblins it saved.*), a ruled scrolling list `Name · SET CN · foil   −n`, and a muted footnote (the entry stays, marked reverted; Undo still works). The amber commit names the cost (`Remove 12 copies`). Blocked: title *Can’t revert this import yet*, the engine's reason + way out, blocking lines first with a danger-ink note each (*2 copies are in Party Time — break that deck down first.*), commit disabled; a 409 re-renders from the returned plan. After: a highlighted `role=status` result line; the row reads `· reverted` with `reverted` in the value column; the inspector notes *Reverted — See the revert*; the revert entry (kind *Revert*, `Reverted an import`, value column `−n`) says *Undid <entry>* linking back, facts `Took out · Put back`.
### Scenes in Collection (a sort group, not a sheet)
- **Scene** is a Collection sort key, offered only when a family in view configures scenes (`config/families.toml` `[[scenes.<anchor>]]`); preset `Scene › Number` leads the presets then. Each scene/poster run is a level-2 section in config order; printings outside every scene close the family under *Not in a scene*. Filters, marks, grid/list and Bulk modify counts work unchanged.
- **Scene head:** name · `Artist · LTR 399–404` (container ≥ 40rem) · the family's owned meter at 3.5rem (% held in any finish) · right side per finish `NONFOIL 2/6 · $12.12 to finish` / `FOIL 6/6 · complete` (≥ 52rem; unpriced count appended) · a basket icon action (`BuyListMark`, tooltip `Buy lists for <scene>`).
- **Buy popover** (chrome-raised, align end): scene name + one muted line (assemble in one finish; one copy of each missing printing), then per finish a small-caps label with `4 missing printings · $12.12` and the shared `CopyTargets` store strip (absent when complete). Phones keep the meter and basket; the per-finish tallies live in the popover.

### Deck editor (`/decks/<slug>/edit`)
- **Two-pane workbench** (resizable, persisted; phones: `Deck · N | Find cards` tabs). Header: `‹ Back to deck`, the deck name as an inline-editable title, `Cards N / target` (100 Commander/Brawl, 60 otherwise; amber-ink until on target), `Changes +a −r`, `Discard changes` and the one filled commit `Save deck`.
- **Draft decklist (left):** sections like the deck view; each ruled row = `− n +` stepper, name, `SET · #cn · finish · N free`, a diff mark (`NEW`, `+n`, `−n`, `REMOVED` — amber-ink adds, rust removals), price, and a `⋯` menu (Move to board · Finish when building · Remove / Undo remove). Removed rows stay struck-through until saved so a mistake is one click back.
- **Find cards (right):** `Search | Suggestions | Combos | Art` tabs. Search covers all of Magic but lists **your free copies first** (`3 free` in amber-ink), offers `As commander` for legendary leaders when the commander slot is empty. Suggestions = EDHREC's picks for the commander with inclusion %, `Free in my collection` and `Hide cards in deck` filters.
- **Combos tab** (Commander Spellbook over the unsaved draft, debounced): a summary line (`1 in this deck · 6 one card away · 7 more need another colour`), then ruled sections `One card away · N cards` — one row per missing card (art crop, name → inspector, `Completes N combos` disclosure · `2 free` in accent-ink / `owned, all pledged` / `not in your collection` · `from $`, `+` adds it) — and `In this deck · N combos`. A combo row is a disclosure: pieces joined with `+` (the card to add in accent-ink), a muted `what it does · in N decks` line; opened it shows Result (when more than two), Also needs, Setup, Mana, numbered steps and a `Commander Spellbook` ghost link with its mark (open spellbook). Outages say so in rust, never block.
- **Art tab** (on-theme printing swaps over the unsaved draft): an `Art theme` search field whose matches are pill chips (`cat 156` — label + artworks tagged), `Try cat · moon · …` quick chips when empty. Once chosen: a summary (`5 of 82 cards on theme · 3 can swap`) + a quiet `Swap all free · N` button (only picks you have free copies of), then ruled `Can swap` / `On theme` sections. A row reads current art (small, dimmed) `›` on-theme art (larger, → inspector), name `×N`, `SET #cn · 2 free` (accent-ink) / `$0.25` / `yours, all in decks`, a muted `N other printings ⌄` disclosure opening a horizontal strip of art buttons (set · free-or-price under each; click swaps to it), and a text `Swap` / `Undo` action. Swapped rows read `was SET #cn`; the deck list marks them `New art`, its ⋯ menu offers `Back to SET #cn`, and the header's Changes counts them as `N swapped` (a printing/finish change on the same card is a swap, not +/−). Below: `N cards have no <tag> printing in your catalog` + `Look on Scryfall for more` (inline status). No tag cache yet → an empty note with `Load art themes` (runs `scryfall.sync_tags`, progress rule).
- **Checks** (header, `Legal · B3+`): a popover with format legality (Scryfall's per-format legality; errors in rust) and, for Commander-like formats, the **bracket floor** from Wizards' published criteria (Game Changers, mass land denial, extra turns; two-card combos only on request via Commander Spellbook). Copy states brackets are guidelines, not rules — never a verdict, never blocks Save.
- **Card names** in the draft and in results open the shared `CardInspector` (with *Your copies*).
- **Save** cuts a new deck version (history kept). A built deck first shows **Update your built deck** — `Take out · Put in · Missing` lists — and saving moves its pledges to match. Leaving with unsaved edits asks first.

### Bulk modify counts — checklist mode (Collection)
- **Purpose:** the desk ritual of filling a set checklist, in place. Sheet action icon *Bulk modify counts* (card with tally marks; it SETS each printing's count; pressed = `paper-sunk` wash + amber underline, URL `count`) swaps the guide for a dense ruled count table over the same filters + sort; *Done modifying counts* switches back.
- **Table:** sticky `Printing · Nonfoil · Foil ✦` header; family/set heads as in the guide (no disclosure); one 40px ruled line per printing — art crop (≥26rem container), name, `SET · # · R · tags`, then one right-aligned count cell per finish (`—` where the printing has no such finish; etched counts as foil). Virtualized.
- **Keys:** typing selects-and-replaces; Enter/Tab go DOWN the same finish column (skipping printings without it), Shift reverses, ↑/↓ too, ←/→ switch finish, Esc puts the cell back. Not-a-number turns the cell's border rust (`aria-invalid`) and isn't counted.
- **Diff:** an edited line takes the highlighter; the cell's value goes semibold with a signed mark left of it (`+2` accent-ink, `−1` rust). The sheet summary becomes the running diff: `Modifying counts · 12 changes · +8 −3 copies · +$14.20 at market (2 unpriced)`; after saving, `Saved 12 counts · +8 −3 copies`.
- **Commit:** `Discard` (quiet, confirms `Discard N counts?`) + the one filled `Save N changes`, left of the icons. Save = one ledger event; a count below copies in built decks shows a rust note (*break it down before setting fewer*) and keeps Save off; if the collection moved since you started editing counts, the save is refused, the numbers refresh and each moved cell is **flagged** (amber ring, `now N` beside it, tooltip names both counts) under a note `N counts changed in your collection since you started editing counts…` with *Keep all my counts*; retype a flagged cell or press Enter on it to keep yours — Save stays off until none are flagged. Cells stay editable while saving; anything typed meanwhile is kept (rebased on the count just saved).
- **Draft:** kept in this browser (`mm.collection.checklist`) until Save or Discard — survives reloads, mode and family switches (the icon tooltip says `Bulk modify counts · N unsaved`); leaving Collection asks `Leave with unsaved counts?`.
### Add cards dialog (Collection)
- **Why a modal:** a protected multi-step flow (stage → review → commit) that must not leak half-edits into the sheet. Trigger: a **ghost button** in the sheet header's upper right (`GuideSheet actions`; may later move nearer the card list) — `AddCardMark` (card + plus badge) + `Add cards` in `accent-ink`, no border or fill; hover/focus adds a faint `paper-sunk` wash (no lift, no underline). Paper sheet inset 3dvh, title + text tabs (`Search · Bulk add a list · Add decklist or product · Import a collection`; amber underline on the active tab, like the nav; on phones the tab row scrolls sideways instead of wrapping).
- **One review model for every mode:** search stages printings, paste/deck lines resolve server-side, and all of them end in the same `ReviewTable` checklist (ruled rows: include checkbox, art crop, name + source line/note, printing picker, finish toggle, unit price, qty). **Columns align down the list:** at ≥44rem the list is one grid and every row a `subgrid` on its tracks (printing · finish · price · qty); the finish cell is one fixed width (`w-26`), and a one-finish note (`Nonfoil only`) sits in the toggle's box so its text starts where the toggle's does; price and qty right-aligned, tabular. Narrow containers put qty (and ×) on the name line and printing · finish · price on one line under it. The source line under the name shows only when it adds something (the engine's note, a misspelling/flavor name, a search hit's set name) — `1 Insist` under *Insist* is dropped (`core/ingest.ts sourceLine`). Ambiguous lines carry an amber-ink `BEST GUESS` mark; unresolved lines a rust `NOT FOUND` and are left out.
- **Printing picker:** a ruled trigger naming the pick (`DSC · 114 · U`) + candidate count, opening a popover grid of every printing's art with price and owned copies; the current pick gets an amber outline.
- **Footer:** what will happen in plain numbers (`8 copies · 2 best-guess printings to check · 1 not found`) and one primary `Add N copies`. Success shows a highlighter `Added …` status in the dialog; the collection refetches behind it.
- **Add decklist or product tab (`DeckPane`) — one field, one results list.** A single `Deck link or product` field (muted hint below naming the deck sites) decides what you mean (`core/ingest.ts readDeckQuery`): a link from a supported deck builder (a missing `https://` is assumed) becomes ONE result row under *Deck link* — link tile, `Deck on Moxfield`, the URL, *Read deck* (Enter reads too; never on paste — Moxfield may open a Chrome window); read, the row turns into the deck (its art, name, `100 cards · by goblinfan · Moxfield`) with `Add…`, which opens the review (nothing is written before it). Any other link → `aria-invalid` + a rust hint; anything else searches the product catalog (*Products · newest first* when empty). Product rows match the Decks recipe list: 40px art crop (a blank sunk tile until the deck file is read — never fetched for this list), name, `Type · SET · year`, an accent-ink ownership hint `you own 1 built · 2 broken down` (zeros dropped; the line wraps on phones), and the same `Add…`, which opens the inline form (`Copies`, `Keep it`: Suggested / Keep it assembled / Just add the cards) — products add directly as a job. The pane stays mounted under the review so *Choose another* returns to what you typed; after a deck is added it starts fresh.
- **Import a collection tab (`CollectionPane`, a diff — not the `ReviewTable`; always shown, the Moxfield part only with the `companion` flag):** source-neutral, and **every choice is one button that reads** — no pick-then-read. One muted intro line, then condensed section heads (no numbers): *From an exported file* = a dashed drop zone holding the primary *Choose a file to read* + `or drop it here. A CSV exported from <every app the engine reads> — we tell which app wrote it.` and a *Where each app keeps its export* disclosure (ruled name · path rows, stacked under 24rem); *Live from Moxfield* (inline muted `read in this browser by the companion`) = ruled source rows, title + note left, one quiet action right: *Read my collection*; *Choose a binder…* (lists via the companion, then each binder is its own button `Trade Box 1  312` that reads it); *A shared link* = URL field + *Read link* (Enter submits; invalid → `aria-invalid` + described rust hint). The pressed button carries the progress (`Waiting for approval…` / `Reading…`). The review heading names what was read (`Moxfield binder · Trade Box 1`, `ManaBox export · cards.csv`; printings count, *Read something else*), then the **per-import mode** as two ruled radio rows — *Add to what you own* / *Set your counts to match* — each with its effect on the title line (`+828 copies · −27 copies · 134 new printings`); nothing is preselected and *Import* stays disabled until one is chosen. Muted notes (skipped proxies/digital, unmatched lines, printings you own that the read leaves alone), then a **virtualized change table** (Card · Set · # · Finish · Now · After · Change; Set/Finish fold into the name line under 40rem; gains amber-ink, losses rust). Re-adding an identical read needs an explicit checkbox. When a replace would go below copies in built decks, a rust note says so and *Import* stays disabled for replace (the server refuses it too). One primary `Import · <effect>`; success = the highlighter status line.

### Analytics (`/analytics`, internal flag `analytics`)
- **A ledger, errors first.** Sidebar: `Period` Segmented (7 · 30 · 90 days), *Trace an error* (ref field + Find; validates 6–32 hex), *Store* facts (raw counts, retention, last pruned, recording state, file, the `mm analytics sql …` hint). Sheet: one ruled **totals line** (condensed tabular figures with a label beside each, rust when it counts failures — not metric cards), then two columns (xl): left = *Errors per day* (a ruled day-tally, rust bars, busiest day full height, axis dates, per-day sr-only text), *Top errors* (count · what failed · status/code · age), *Recent errors* (each linked by its short **ref** to the trace); right = *Views* (ink bar per view, the dark part = phone use), *Features*, *Collection → buy-list* funnel with session medians, *Jobs* table (runs · failed in rust · typical duration).
- **Trace:** `?ref=` opens a sunk-paper panel above the ledger listing every event linked to that request (props as `k=v`), each with a copy-request-id button.
- **Rust, not amber, for failure counts** (the Amber-Only Rule holds: amber stays on the active period and focus).

### Button and CopyButton
- **Button:** one component with `tone="chrome|paper"` and `emphasis="primary|quiet"`; primary fills amber, quiet variants are ruled outlines.
- **CopyButton:** wraps Button, copies generated list text, and announces result through `aria-live="polite"`.

### States
- **EmptyNote:** centered guide copy, no illustration.
- **Temporarily down (scraper health):** where a site read is offered and flagged down (`ScraperNotice`): a ruled notice — 2px rules above and below, no fill — heading `<what> — temporarily down` in condensed bold danger ink with a small broken-link glyph, the reason in ink plus `You can still try — a read that works clears this.`, then a muted tabular line `Since today 6:30 AM · found by the daily check · Code scrape.no_cards`. Never blocks the action. In rows (Deals stores) it is the compact `ScraperDownMark`: glyph + `DOWN` in small semibold uppercase danger ink, focusable, whose chrome tooltip carries the same three lines. Rust, never amber.
- **ErrorNote:** `role="alert"`, rust heading, optional ruled retry button. An `ApiError` adds a muted line `Ref 3f9a12c0 · stale_draft` (select-all ref) so a user can quote it; 5xx messages already end in `(ref …)`.
- **GridSkeleton:** pulsing card-aspect blocks with `role="status"` and `aria-live="polite"`.

## Glossary (web copy)
- **Unused** — copies you own that aren't in a built deck (replaces *free*, *loose* and *available* for unpledged copies). Counts read `12 owned · 8 unused`; a built deck holds `in built decks` copies. A broken-down precon copy is a different idea — say *broken down* / *not built*, never *loose*.
- **Value vs Price** — *Value* is what cards or a product's contents are worth (market value; the cheapest printing is a value). *Price* is a specific SKU at a specific store you would buy.
- **Find → Show → Arrange** — the filter rail's order: *Find* (the text search, alone), *Show* (what's included; every control has a field label; no section that swaps which filters appear, no grids of mode buttons), *Arrange* (sort, view type). Modes go in the sub-nav strip; actions go in the sheet header.
- **Earmark vs Watching** — *Earmark* marks a card you're interested in, owned or not (to collect, or a deck idea); it shows in Explore → Earmarked and the deck editor's Earmarked tab. *Watching* is a store listing whose price you follow (Deals). Don't say *considering* — deckbuilders mean the Maybe board by it.
- **Vendors in labels** — don't name a data source (Scryfall, EDHREC) in an action label unless the action opens that site: `Refresh`, `Recheck for cheapest`, not `Check every set on Scryfall`.

## Do's and Don'ts

### Do:
- **Do** build all reusable colors through `web/tokens/*.tokens.json` → `web/src/styles/tokens.css` → `web/src/index.css` theme utilities.
- **Do** keep light mode as bone-paper guide sheets on dark charcoal chrome and dark mode as all-charcoal stock with bone ink.
- **Do** use amber only for highlighter/focus/active/primary/progress states.
- **Do** prefer `GuideCard` mapping in `web/src/core/guideCard.ts` so tile, row, grid, and preview stay shared across domains.
- **Do** preserve URL-backed controls from `web/src/core/search.ts`; filters, visibility, sort, density, and commander/set choices are shareable state.
- **Do** use `voice-condensed`, `voice-semi`, `tabular`, `highlighter`, `ruled`, `ease-guide`, and `paper-grain` instead of inventing one-off visual classes.
- **Do** keep the chassis static: on a desktop window the page never scrolls or rubber-bands (`overscroll-behavior: none` on html/body); only panes that overflow scroll. Make every scroll pane its own containing block (`relative`) so an absolutely positioned child — an `sr-only` label — can't reach past the window and scroll the page. `web/e2e/chassis.spec.ts` checks every view.
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
- **Sheet header vs section heads:** the sheet's (screen-reader) title names the view (`Collection`) and its summary describes what the current filters SHOW; family heads carry family-wide facts (progress, owned/printings, copies, value). Never repeat the same numbers at both levels.
- **Buy (bulk buy lists):** sidebar section `Buy` (single-word section titles); a label line `Copy bulk lists · 157 missing shown` (or `· 3 marked`) over a full-width ruled strip of equal 32px-tall cells, one per store (names beside the marks when the strip is ≥21.5rem wide, marks only when narrower): a monochrome store mark in amber (`StoreMarks.tsx`, drawn on a 24px stroke grid after each store's logo). Hover darkens the cell and lifts the mark 1px; a successful copy swaps the mark for a ✓ for 1.6s. Each cell has `aria-label`/`title` `Copy <Store> list`; one shared polite status line, where a store that can't take exact printings (Card Kingdom) says so. Kept small on purpose: an occasional action for most collectors. Owner-approved exception to the Amber-Only Rule: store marks are amber at rest.
