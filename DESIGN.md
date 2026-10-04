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

Cards have two densities. Grid density calculates columns from the scroll-region width with a 12px gap and minimum card widths (`120px`, or `128px` for Collection). Rows density is a 2rem ruled checklist line. `CardRow` uses container-query breakpoints at `18rem` (show crop thumbnail), `22rem` (show bars and wider price), and `30rem` (show set/CN metadata and wider bars).

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
- **States:** active nav uses amber underline; jobs shows amber pulse when queued/running; theme can be system/light/dark and persists to `localStorage` as `mm.theme`.
- **A11y contract:** skip link to `#main`, `nav aria-label="Primary"`, `main tabIndex={-1}`, sidebar labelled by the view, mobile disclosure uses `aria-expanded`/`aria-controls`.

### GuideSheet
- **Purpose:** paper/stock host for each view's title, summary, actions, and guide body.
- **Style:** `paper-grain`, `bg-paper`, `text-ink`, `rounded-sm`, ambient sheet shadow.
- **States:** empty, error, and skeleton states render inside the sheet rather than replacing the shell.

### Sidebar primitives
- **SideSection:** uppercase condensed side heading plus vertical control stack.
- **Segmented:** single-choice `ToggleGroup`, ruled chrome border, `chrome-raised` selected state.
- **ChipToggles:** multi-select `ToggleGroup`, pill chips; selected chips fill amber and show optional tabular counts. **Only for ≤5 options.**
- **MultiSelect:** any choice set larger than 5 (set families, EDHREC lists). A compact trigger summarizing the selection (`Final Fantasy +2 ▾`) opens a searchable checkbox popover; selected options are pinned first; bulk-select is scoped to the current search, never "select everything".
- **SortBuilder:** the one sort control for every card view. Trigger shows the hierarchy (`Set › Rarity › #`); the popover edits ordered levels (direction toggle, ▲▼ buttons and drag handles via Pragmatic drag-and-drop, add/remove) and offers presets. The first level groups the sheet into sections. Rules live in the URL (`core/sort.ts` codec).
- **Grouped MultiSelect (Card types):** trait filters (Finish · Rarity · Treatment · Chase) are ONE grouped checkbox picker, everything checked by default; unchecking a trait hides every card carrying it — except Finish (Nonfoil · Foil · Fancy foil), which ORs: a printing shows while any of its finishes is checked, and owned/missing are judged on the checked finishes only. Fancy foil = a foil printing whose treatment carries `ff` (surge, etched, galaxy…). Group headings carry All/None; the trigger summarizes exclusions (`All card types` / `Hiding Common, Uncommon +1`). No explanatory copy under controls.
- **TextField:** labelled search input on `chrome-raised`, `chrome-line` border, amber focus border.
- **A11y contract:** groups carry explicit `aria-label`; labels wrap inputs or target by `htmlFor`.

### Group by (Commanders)
- **Purpose:** re-section every compare column without changing ranking: `Card type` (EDHREC's type-based lists, the default) or `Function` (Scryfall Tagger function roots in config order — Ramp, Card draw, Removal, …; untagged cards last under "No tagged function").
- **Style:** a two-option `Segmented` in the Display section (two options → segmented, never chips). Group heads reuse VirtualGuide's level-2 ruled subheads; no per-function colors (one-accent rule).
- **Multi-membership:** a card serving several functions is listed under each, with a muted `GuideNote` ("also: Removal, Tutor") under its caption (inline after the set metadata in Rows); a one-line helper under the control says so and that column totals count each card once. Marking is per card, so every appearance highlights together.
- **Empty state:** when the tag cache was never synced, a chrome-muted note links to Jobs → Sync Scryfall tags.

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
