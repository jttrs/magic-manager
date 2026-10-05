⚠️ DEGRADED: single-context (nested critique sub-agents are prohibited in this sub-agent context; source was read-only, detector and browser evidence were still run)

# Deck Manager View — Impeccable Critique + Audit

**Target:** `web/src/views/DecksView.tsx`  
**Date:** 2026-10-05T00:06:40Z  
**Mode:** Operate  
**Surface:** Magic Manager web app, Deck Manager recipe library  
**Evidence:** live real-data app at `http://localhost:5173/decks` with 580 decks; desktop 1440×900 and phone 390×844; light and dark themes; screenshots in `.playwright-mcp/`.

## Evidence collected

- `node .../impeccable/scripts/context.mjs --target web/src/views/DecksView.tsx`
- `node .../impeccable/scripts/detect.mjs --json web/src/views/DecksView.tsx` → `[]` (no deterministic detector findings)
- Desktop screenshots:
  - `.playwright-mcp/decks-desktop-light.png`
  - `.playwright-mcp/decks-commander-desktop-dark.png`
  - `.playwright-mcp/decks-commander-desktop-light.png`
  - `.playwright-mcp/decks-card-inspector-light-waited.png`
  - `.playwright-mcp/decks-add-marked-dialog-light.png`
  - `.playwright-mcp/decks-group-year-light.png`
  - `.playwright-mcp/decks-search-fin-light.png`
- Phone screenshots:
  - `.playwright-mcp/decks-mobile-deck-viewport-dark.png`
  - `.playwright-mcp/decks-mobile-list-viewport-dark.png`
- Accessibility snapshots:
  - `.playwright-mcp/decks-desktop-light-snapshot.yml`
  - `.playwright-mcp/decks-commander-snapshot.yml`

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|---|---:|---|
| 1 | Visibility of System Status | 3 | Loading/error states exist; add review gives clear staged state, but deck-level bulk actions do not say they open review rather than write. |
| 2 | Match System / Real World | 3 | Strong recipe-library model and MTG facts; built vs loose is visible, but captions mix `free`, `in deck`, and hidden zero-pledged state in a way that can read as contradictory. |
| 3 | User Control and Freedom | 3 | Phone has `All decks`; filters/search can be cleared manually; no explicit reset/clear filters action in Decks. |
| 4 | Consistency and Standards | 4 | Matches After-Hours Price Guide: charcoal chrome, guide sheet, amber active/primary/focus, ghost actions, no art overlays. |
| 5 | Error Prevention | 3 | Add actions route to review, not immediate write; however “Add deck to collection” wording does not advertise the safety step or token exclusion. |
| 6 | Recognition Rather Than Recall | 2 | Density control and grouping live only in sidebar/phone disclosure; inspector users must remember to open Deck Controls to switch Cards/List. |
| 7 | Flexibility and Efficiency | 2 | Search/group/state filters are efficient, but keyboard traversal through the deck list is impractical with 580 deck buttons. |
| 8 | Aesthetic and Minimalist Design | 3 | Clear, authored guide aesthetic; deck header/action area gets crowded on phone and the deck list dominates desktop before a deck is picked. |
| 9 | Error Recovery | 3 | Dialogs close with Escape/close, review can back out; failed add has role alert. No undo after add, but outside this view’s immediate read-only review. |
| 10 | Help and Documentation | 3 | Labels are present, but there is no inline explanation of recipe library, built/loose, or “free to use” where it first matters. |
| **Total** |  | **29/40** | **Good, with major interaction debt in keyboard/touch efficiency.** |

## Audit Health Score

| # | Dimension | Score | Key Finding |
|---|---|---:|---|
| 1 | Accessibility | 2 | Keyboard path hits hundreds of deck buttons before inspector; repeated 28px section/mark controls miss the 44px target guideline. |
| 2 | Performance | 2 | Inspector cards are virtualized, but the deck list renders all 580 real buttons/images and creates a long tab order. |
| 3 | Responsive Design | 3 | Phone list→deck→All decks works, but card controls/action affordances crowd the first viewport and touch targets are small. |
| 4 | Theming | 4 | Light/dark themes honor tokens and amber-only usage; no raw-color detector findings. |
| 5 | Implementation Integrity | 4 | Product-specific system is coherent; detector returned zero findings. |
| **Total** |  | **15/20** | **Good; accessibility/performance need targeted hardening.** |

## Design Specificity Verdict

This feels authored for magic-manager, not interchangeable SaaS. The surface reads as a collector’s guide sheet: ruled sections, tabular prices/counts, real card art, amber highlighter marks, and ghost actions all align with `DESIGN.md`. The strongest product-specific move is the split between a recipe library on the left and exact-printing deck cards on the right: it makes precons, imported decks, Jumpstart packs, built decks, and loose recipes coexist without pretending they are the same as inventory.

The weakness is not visual identity; it is operational ergonomics at collection scale. The UI has 580 recipes but still exposes the deck list as a giant button stack. That undermines the Operate-mode promise for keyboard users and creates avoidable rendering/focus work.

**Deterministic scan:** clean (`[]`). No raw-color/system-drift findings. Browser/manual review found the substantive issues below.

## What’s Working

1. **The deck inspector is visually right for the product.** Sections like Commander / Creatures / Tokens, card art, price, owned count, free count, and `×N in deck` captions match the collection/deck mental model. Evidence: `.playwright-mcp/decks-commander-desktop-light.png`.
2. **The Add-cards handoff is safe.** “Add 2 marked” opens the shared review dialog and does not commit until `Add 2 copies`, exactly the protected-flow pattern in `DESIGN.md`. Evidence: `.playwright-mcp/decks-add-marked-dialog-light.png`.
3. **Responsive navigation basically works.** On phone, a selected deck opens as the primary surface and `All decks` returns to the list. Evidence: `.playwright-mcp/decks-mobile-deck-viewport-dark.png` and `.playwright-mcp/decks-mobile-list-viewport-dark.png`.

## Priority Findings

### [P1] The 580-deck list is a keyboard and performance wall

- **Location:** `web/src/views/DecksView.tsx:96-140`; supporting derivation in `web/src/core/decks.ts:30-58`
- **Category:** Accessibility / Performance / Flexibility
- **Evidence:** The browser reported **665 buttons** on the loaded deck page. The captured focus sequence tabs through global nav, sidebar controls, then deck rows one by one (`Agents of S.H.I.E.L.D.`, `Analyzed`, `Animal`, …) before reaching the inspector. Screenshot: `.playwright-mcp/decks-commander-desktop-light.png`; code renders every grouped row via `groups.map(...g.decks.map(...DeckRow))`.
- **Impact:** Keyboard users cannot efficiently reach the inspector, section jump controls, card marks, or add-review actions. Screen-reader users also get an enormous navigation region before the actual selected recipe contents. Rendering all deck rows/images also burns work for a library whose expected scale is hundreds of decks.
- **WCAG/Standard:** WCAG 2.4.3 Focus Order; WCAG 2.4.1 Bypass Blocks (spirit); Operate-mode efficiency.
- **Concrete fix:** Replace the deck list with a virtualized, keyboard-managed listbox/tree: one tab stop for the deck list, arrow keys to move within rows, Enter/Space to pick, typeahead/search retained, `aria-activedescendant` or roving `tabIndex`, and a visible “Skip to deck cards”/“Deck details” link after selection. Keep group heads sticky visually, but do not put every deck row in the Tab sequence. Consider pinning the active/selected deck group or active row after filtering.
- **Suggested command:** `/impeccable harden`

### [P1] Touch targets are systematically below mobile guidance for repeated controls

- **Location:** `web/src/components/MarkToggle.tsx:4-16`; `web/src/components/VirtualGuide.tsx:198-207`; `web/src/views/DecksView.tsx:160-179`
- **Category:** Accessibility / Responsive
- **Evidence:** Runtime measurement found mark toggles and section jump buttons at **28×28px**. The phone deck screenshot shows these in the primary card/section path: `.playwright-mcp/decks-mobile-deck-viewport-dark.png`.
- **Impact:** Marking cards and jumping/collapsing sections are high-frequency actions in the deck inspector. Small targets increase mis-taps, especially when card captions are dense and users are standing at a store/table rather than seated at a desktop.
- **WCAG/Standard:** WCAG 2.5.8 Target Size (Minimum) and mobile platform convention (44×44px comfortable target).
- **Concrete fix:** Preserve the compact visual mark, but enlarge the hit area: `min-h-11 min-w-11` on touch breakpoints or a pseudo-element/hitbox wrapper. For section heads, make the whole head row a larger disclosure target and move previous/next buttons to 40–44px hitboxes (the icon can remain small). Keep amber only on focus/active/highlight.
- **Suggested command:** `/impeccable adapt`

### [P2] Cards/List density is hidden in the sidebar, away from the deck task on phone

- **Location:** `web/src/views/DecksView.tsx:57-62`, `web/src/views/DecksView.tsx:144-185`
- **Category:** Recognition / Responsive / User Control
- **Evidence:** The view control is in the Deck Controls sidebar/disclosure, while the deck inspector is the active phone screen. On phone evidence (`.playwright-mcp/decks-mobile-deck-viewport-dark.png`), the first viewport shows deck title/actions and cards, but the density toggle is collapsed above under “Deck Controls.”
- **Impact:** The user’s requested task — “Cards vs List view” while reading the inspector — is not discoverable at the point of use. A user who wants a compact checklist must leave the deck context mentally, open controls, change density, and return.
- **Concrete fix:** Duplicate or move the density toggle into the deck inspector header on narrow screens: a two-option `Segmented` beside/under the deck actions (`Cards · List`). Keep URL-backed state; on desktop it can remain in sidebar. This is not a new visual pattern — it reuses the existing segmented control where the decision is made.
- **Suggested command:** `/impeccable adapt`

### [P2] Bulk add actions are safe, but their labels undersell the review step and scope

- **Location:** `web/src/views/DecksView.tsx:172-180`; `web/src/core/decks.ts:119-132`; `web/src/components/addcards/AddCardsDialog.tsx:23-71`
- **Category:** Error Prevention / Match System / Clarify
- **Evidence:** “Add deck to collection” opens Add Cards review; it does not write immediately. “Add 2 marked” also opens review. `deckReviewLines` excludes tokens by default (`withTokens = false`) and normalizes `either` to nonfoil. Screenshot: `.playwright-mcp/decks-add-marked-dialog-light.png`.
- **Impact:** In a real collection DB, “Add deck to collection” sounds like a commit, especially next to the user’s explicit warning not to press `Add N copies`. The current safety is good, but users have to trust/learn it. Token exclusion and finish normalization are also hidden until review.
- **Concrete fix:** Rename deck-level triggers to review-oriented labels: `Review deck cards`, `Review 2 marked`, or `Add via review`. Add a one-line helper/status near actions: “Opens review first · tokens excluded” (only if tokens exist) / “No copies are added until the final Add button.” Preserve ghost-action styling; keep the filled amber button only inside the commit dialog.
- **Suggested command:** `/impeccable clarify`

### [P2] Built/loose and pledged/free facts need one explanatory anchor in the inspector

- **Location:** `web/src/views/DecksView.tsx:166-170`; `web/src/core/decks.ts:96-100`; `web/src/components/CardTile.tsx:33-43`
- **Category:** Match System / Help / Cognitive Load
- **Evidence:** A built deck header can show `built, 0% pledged`, while card captions show `4 free to use`, `✦×4`, and `×1 in deck`. This is accurate, but the terms are dense and appear without a legend. Evidence: `.playwright-mcp/decks-commander-desktop-light.png` and `.playwright-mcp/decks-mobile-deck-viewport-dark.png`.
- **Impact:** The view is a recipe library, not just inventory. New users need to understand that `×1 in deck` is recipe count, `pledged` is physically assigned, and `free to use` is owned but unpledged. Without one inline explanation, users can misread a built deck as physically complete or assume free copies are duplicates of the deck copy.
- **Concrete fix:** Add a compact guide note under the deck metadata or as an info affordance: “Recipe counts are shown as ×N in deck; pledged copies are physically in this built deck; free copies are owned but unpledged.” Keep it one line on desktop and collapsible/truncated on mobile.
- **Suggested command:** `/impeccable clarify`

## Minor Observations

- The desktop split handle is visually on-world and discoverable on hover/focus (`web/src/views/DecksView.tsx:82-91`), but it should inherit the same keyboard splitter guarantees as the compare columns; verify arrow-key resizing from `react-resizable-panels` in a follow-up accessibility pass.
- The active selected card highlighter on phone is strong but acceptable under `DESIGN.md` because it reads as an amber annotation under the art, not an overlay on art.
- The card inspector is strong after images load (`.playwright-mcp/decks-card-inspector-light-waited.png`). The first screenshot captured during load showed a large blank art area; no finding unless this appears under normal network timing.
- The Add Cards seeded review uses the shared modal correctly, but two marked rows in a 94dvh sheet leave a very large blank middle. Acceptable now; if this becomes common, consider a more compact seeded-review height.

## Persona Red Flags

**Alex — power collector with keyboard-heavy workflow**
- Red flag: Tabs through hundreds of deck buttons before card controls. This turns a 580-deck library into a focus marathon.
- Red flag: No deck-list typeahead/arrow roving once inside the list; search helps, but keyboard traversal still enters the rendered row stack.

**Jordan — first-time collector using recipes vs inventory**
- Red flag: `built`, `loose`, `pledged`, `free to use`, and `×1 in deck` are all present but not defined in the moment. Jordan can read the facts but not confidently interpret the inventory implications.
- Red flag: “Add deck to collection” sounds like an immediate write even though the flow is safely staged.

**Riley — phone user checking cards at a table/store**
- Red flag: 28px mark/jump targets are too small for repeated phone use.
- Red flag: The density toggle that would make the deck easier to scan is hidden in the top Deck Controls disclosure rather than in the deck header.

## Recommended Actions

1. **[P1] `/impeccable harden`** — virtualize/roving-focus the 580-deck list and add a bypass path from recipe list to inspector.
2. **[P1] `/impeccable adapt`** — enlarge touch targets for mark toggles and section jump controls; surface Cards/List density in the phone deck header.
3. **[P2] `/impeccable clarify`** — rename add-review triggers and add a compact built/loose/pledged/free legend.
4. **[final] `/impeccable polish`** — re-run after the structural fixes for visual tightening only.
