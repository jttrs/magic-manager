Method: dual-agent (A: design-reviewer · B: detector-auditor)

# Impeccable critique + audit: Add cards dialog

Target: `web/src/components/addcards`  
Surface: Collection → Add cards dialog  
Mode: Operate  
Screens exercised: desktop 1440×900 and phone 390×844, light/dark theme states, search, paste-list review, printing picker, deck URL validation, precon expansion, Escape/focus return.  
Screenshots saved under `.playwright-mcp/`:

- `addcards-desktop-light-search-results.png`
- `addcards-desktop-light-search-staged.png`
- `addcards-desktop-light-paste-review.png`
- `addcards-desktop-light-printing-picker.png`
- `addcards-desktop-light-paste-edited.png`
- `addcards-desktop-light-deck-precon.png`
- `addcards-desktop-light-deck-url-error.png`
- `addcards-phone-dark-open.png`

Detector: `node "/Users/torre/Library/Application Support/com.github.githubapp/app-skills/impeccable/scripts/detect.mjs" --json web/src/components/addcards` returned `[]`.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|------:|-----------|
| 1 | Visibility of System Status | 3 | Search/paste/deck jobs report state, but precon catalog has no loading state and precon success stays local to the row. |
| 2 | Match System / Real World | 4 | Exact printings, finishes, copies, built/loose precons, and best-guess language match collector workflows. |
| 3 | User Control and Freedom | 3 | Search/paste/deck-review flows are reversible; precon add is direct and has no review/undo affordance. |
| 4 | Consistency and Standards | 2 | Search, paste, and deck URL converge on a review footer; precons bypass it and write from an inline row. |
| 5 | Error Prevention | 3 | Quantity bounds, unresolved-line exclusion, and validation help; deck URL validation copy contradicts accepted `http://`. |
| 6 | Recognition Rather Than Recall | 3 | Main modes are visible; staged work and tab-specific drafts are not signaled in tab labels. |
| 7 | Flexibility and Efficiency | 3 | Search, paste, deck URL, and precon paths cover novice/power use; search requests are not truly debounced. |
| 8 | Aesthetic and Minimalist Design | 3 | Strong price-guide material system; dense review controls become visually crowded on touch/phone. |
| 9 | Error Recovery | 3 | Paste review has Edit list, exclude, picker, finish switching; precon job failure recovery is row-local and sparse. |
| 10 | Help and Documentation | 2 | The dialog lacks an accessible/visible summary of the three workflows and their different risk levels. |
| **Total** |  | **29/40** | **Good, with one major model break and several accessibility/responsive fixes.** |

## Audit Health Score

| # | Dimension | Score | Key Finding |
|---|-----------|------:|-------------|
| 1 | Accessibility | 3 | Strong Radix baseline, but no dialog description, misleading picker listbox semantics, and undersized touch targets. |
| 2 | Performance | 3 | Lazy images and bounded job logs are good; live search/precon search can issue per-keystroke requests. |
| 3 | Responsive Design | 3 | Layout is responsive, but several touch controls are under 44px and phone density is high. |
| 4 | Theming | 4 | Uses semantic `paper`/`ink`/`rule`/`accent` tokens; dark mode matched the committed world in inspection. |
| 5 | Implementation Integrity | 4 | Product-specific, coherent, no detector drift. |
| **Total** |  | **17/20** | **Good.** |

## Design Specificity Verdict

**Pass, but with a trust-breaking exception.** The dialog feels authored for magic-manager: it uses exact printing identity, card art, finish selection, owned counts, price-guide rules, bone/charcoal material, amber focus/action states, and provenance-aware vocabulary. It does not look interchangeable with a generic import modal.

The exception is conceptual, not visual: `Add cards` teaches a reassuring “stage → review → Add N copies” ritual, then preconstructed products use a different direct-write job inside a list row. That violates the dialog’s own review contract and makes the highest-volume operation feel less safe than a one-line paste.

Deterministic scan found no anti-patterns. Manual audit found accessibility and touch-target issues the detector does not catch.

## Overall Impression

This is a strong first-class app replacement for an agent workflow. The pasted-list review is the best part: it acknowledges ambiguity, shows exact printings, and lets the collector fix the machine’s guesses before writing. The biggest opportunity is to make every write path feel equally deliberate and reversible—especially precons.

## What's Working

1. **The review table is the right core primitive.** It exposes printing, finish, quantity, price, ambiguity, unresolved state, and inclusion in one compact ledger (`ReviewTable.tsx:12-74`).
2. **The visual world is committed and consistent.** Paper, rules, tabular figures, restrained amber, and card art follow `DESIGN.md` rather than generic SaaS modal habits (`AddCardsDialog.tsx:67-99`, `SearchPane.tsx:39-64`).
3. **Paste flow supports trust.** Original list text is preserved, “Edit list” is available, unresolved lines are excluded by default, and warnings are explicit (`AddCardsDialog.tsx:116-126`, `169-173`; `core/ingest.ts:66-76`).

## Prioritized Findings

### P1 — Precon adds bypass the dialog's staged review contract

- **Location:** `web/src/components/addcards/AddCardsDialog.tsx:17-18`, `141-152`; `web/src/components/addcards/DeckPane.tsx:9`, `116-151`
- **Category:** Consistency / Error prevention / Emotional safety
- **Evidence:** The dialog comment and UI pattern establish that add paths end in a review checklist and footer commit. Deck URL follows that pattern through `onFetched`; precons instead call `start('ingest.precon', ...)` directly from a row-level `Add to collection` button.
- **Impact:** The largest write path can modify the real collection without the same final checkpoint used for one pasted line. Users must mentally switch models: “Deck URL is reviewed; precon is immediate.” That increases accidental writes and weakens trust in the dialog.
- **Concrete fix:** Either stage precon selections into the same review/commit footer, or make the direct path explicit: rename the row action to `Add precon directly`, show a confirmation summary (`1 product · suggested built · N cards`) before starting the job, and provide a clear post-add reversal path or link to the created deck/precon record.
- **Suggested command:** `/impeccable shape`

### P1 — Dialog has no accessible description for a multi-path, write-capable flow

- **Location:** `web/src/components/addcards/AddCardsDialog.tsx:67-73`
- **Category:** Accessibility / Help and documentation
- **Evidence:** `Dialog.Content` sets `aria-describedby={undefined}` and provides only `Dialog.Title`. There is no `Dialog.Description` summarizing Search, Paste, Deck URL, and Precon behaviors.
- **Impact:** Screen-reader users enter a complex, write-capable modal with only “Add cards” as context. The different risk levels are not announced, especially the precon direct-write exception.
- **Concrete fix:** Add a visually hidden `Dialog.Description` tied to the content, e.g. “Search printings, paste a card list, or fetch a deck for review before adding. Preconstructed products are added directly after choosing copies and built/loose state.” If precons are changed to review-first, update the copy accordingly.
- **Suggested command:** `/impeccable harden`

### P2 — Printing picker advertises listbox semantics but behaves as a button grid

- **Location:** `web/src/components/addcards/PrintingPicker.tsx:45-61`
- **Category:** Accessibility / Implementation integrity
- **Evidence:** The popover renders `ul role="listbox"` and `li role="option"`, but each option contains a focusable native `button`; no roving focus or arrow-key listbox behavior is implemented.
- **Impact:** Assistive tech receives a listbox model while keyboard users interact with buttons. This can produce confusing announcements and broken expectations for arrow-key navigation.
- **Concrete fix:** Pick one pattern. Prefer a simple `aria-label`ed grid/list of buttons for this image-heavy picker, removing `listbox`/`option` roles; or implement the full ARIA listbox pattern with active descendant/roving focus and arrow keys.
- **Suggested command:** `/impeccable audit`

### P2 — Search finish selection is asymmetric and easy to miss

- **Location:** `web/src/components/addcards/SearchPane.tsx:42-63`
- **Category:** Recognition / Error prevention / Touch
- **Evidence:** Clicking the card image adds nonfoil (`onPick(p, 'nonfoil')`), while foil is a tiny `+✦ Foil` text button in a metadata row. The price shown before selection uses `price_usd ?? price_usd_foil`, so the default finish/price relationship is not obvious.
- **Impact:** Users can stage the wrong finish by pressing the most prominent target. Foil is discoverable but visually subordinate, despite being a first-class collection fact.
- **Concrete fix:** Make finish explicit in the result action: use `Add nonfoil` and `Add foil` controls with equal hit areas, or one primary `Add` plus adjacent finish toggle. Keep card art artifact-first, but do not make an unlabeled default finish the dominant action.
- **Suggested command:** `/impeccable clarify`

### P2 — Dense review controls are below comfortable touch size

- **Location:** `web/src/components/addcards/ReviewTable.tsx:28-34`, `55-66`, `81-92`; `web/src/components/addcards/PrintingPicker.tsx:36-43`; `web/src/components/addcards/DeckPane.tsx:138-148`
- **Category:** Accessibility / Responsive
- **Evidence:** Include checkbox is `size-4`, quantity input `h-8`, remove button `size-7`, finish toggles `min-h-7`, picker trigger `min-h-8`, precon number/select controls `h-8`.
- **Impact:** On phone, the dialog is usable but fiddly. The highest-error controls—include/exclude, quantity, finish, remove—are small enough to cause mis-taps during collection edits.
- **Concrete fix:** Preserve the dense ledger look but enlarge hit areas to ~44px using padding or invisible hit targets. Keep visual affordances compact while making the pointer/touch box larger.
- **Suggested command:** `/impeccable adapt`

### P2 — Paste review headline overstates success by counting lines instead of outcome

- **Location:** `web/src/components/addcards/AddCardsDialog.tsx:116-123`, `141-152`, `169-173`
- **Category:** Visibility of status / Copy clarity
- **Evidence:** The review title says `5 lines read`, while the actual outcome—copies to add, best guesses, unresolved, skipped—is split between footer text and a collapsed warnings disclosure.
- **Impact:** A user can see “5 lines read” and miss that `Notacard` is unresolved or a line is excluded. The headline reports parsing volume, not collection impact.
- **Concrete fix:** Change the heading/summary to outcome language: `5 lines · 8 copies · 1 not found`, and keep unresolved/skipped counts visible near the table title. Reserve `<details>` for raw warning text.
- **Suggested command:** `/impeccable clarify`

### P2 — Deck URL validation copy contradicts the implementation

- **Location:** `web/src/components/addcards/DeckPane.tsx:38-41`
- **Category:** Error prevention / Trust
- **Evidence:** Validation accepts `http://` or `https://` (`/^https?:\/\//`) but the message says “starting with https://”.
- **Impact:** Small mismatch, high trust cost. This is the kind of precise import workflow where copy and constraint must agree.
- **Concrete fix:** Prefer requiring `https://` and supported hostnames before starting the fetch job. If `http://` must remain valid, change the message to “starting with http:// or https://” and add host-specific unsupported-site feedback.
- **Suggested command:** `/impeccable harden`

### P2 — Live searches are deferred, not debounced

- **Location:** `web/src/components/addcards/SearchPane.tsx:11-13`; `web/src/components/addcards/DeckPane.tsx:70-84`; `web/src/app/queries.ts:57-70`
- **Category:** Performance
- **Evidence:** `useDeferredValue` smooths rendering but still changes query keys as the user types; precon search passes `q` directly into `preconCatalogQuery(q)`.
- **Impact:** Longer card/product searches can create avoidable request sequences and result churn. The real-data test tolerated it, but this will be noisy under latency.
- **Concrete fix:** Add a short debounce before constructing query keys, while preserving React Query cancellation and minimum query length.
- **Suggested command:** `/impeccable optimize`

### P3 — Precon catalog has no initial loading state

- **Location:** `web/src/components/addcards/DeckPane.tsx:70-92`
- **Category:** Visibility of status / Accessibility
- **Evidence:** The catalog renders error and empty states, but no `res.isPending`/`res.isFetching` status before data exists.
- **Impact:** On slower connections, the precon half of the tab can appear empty with no explanation.
- **Concrete fix:** Add a polite status/skeleton while the first query is pending, and optionally `aria-busy` on the precon list region.
- **Suggested command:** `/impeccable harden`

### P3 — Tab labels do not disclose preserved staged work

- **Location:** `web/src/components/addcards/AddCardsDialog.tsx:22-36`, `71-89`, `102-138`
- **Category:** Recognition / User control
- **Evidence:** Search, paste, and deck states are preserved separately, but tab labels remain static (`Search`, `Paste a list`, `Deck or precon`).
- **Impact:** Users can stage search cards, switch tabs, and forget they still have uncommitted draft work elsewhere.
- **Concrete fix:** Add subtle tab counters or a compact persistent draft notice, e.g. `Search · 2`, `Paste · 5`, or `Uncommitted cards staged in Search`.
- **Suggested command:** `/impeccable clarify`

## Persona Red Flags

### Alex, power collector importing lots of cards

- The pasted-list path is efficient, but the headline `5 lines read` makes Alex scan a second area to know actual copies/not-found count.
- The printing picker is rich but keyboard semantics are not a real listbox; rapid keyboard correction is less reliable than the visual UI implies.
- Search/precon queries can churn while typing, which will be more noticeable with broad searches like “sol ring” and “final fantasy.”

### Jordan, first-time collection user

- Jordan sees one dialog title, three tabs, and one final footer pattern—then precons use a direct row-level `Add to collection`. That is a surprising risk shift.
- The tiny `+✦ Foil` control is easy to miss; Jordan may think pressing the card chooses the printing, not specifically nonfoil.
- There is no dialog description or short “how this works” line to establish whether actions are staged or immediately write to the collection.

### Sam, phone-first on-the-go user

- The phone layout stays within the viewport, but the important review controls (checkboxes, finish, quantity, remove) are small for touch.
- Dense rows require careful taps at the moment Sam is most likely to be multitasking with physical cards.

## Minor Observations

- Escape closed the dialog and returned focus to the `Add cards` trigger in runtime inspection.
- The dark theme matched the After-Hours Price Guide direction: charcoal stock, bone ink, amber only as active/focus/action. No theming issue found.
- Empty image `alt=""` is acceptable here because buttons carry explicit card/printing labels and adjacent text names the card.
- The successful staged commit status is strong (`Added … Your collection is refreshing behind this dialog.`), but precon success should reuse a comparable dialog-level status.

## Recommended Actions

1. **P1 — `/impeccable shape`**: Resolve the precon mental model: stage it into the shared review footer or make direct-add explicit with confirmation and recovery.
2. **P1/P2 — `/impeccable harden`**: Add dialog description, fix URL validation/copy, add precon loading/success/error states.
3. **P2 — `/impeccable audit`**: Correct printing-picker ARIA semantics and confirm keyboard behavior with interaction tests.
4. **P2 — `/impeccable adapt`**: Increase touch hit areas for review controls without making the ledger visually bulky.
5. **P2/P3 — `/impeccable clarify`**: Improve outcome summaries, finish-action labels, and staged-work tab counters.
6. **P2 — `/impeccable optimize`**: Add real debouncing to card/precon searches.
7. **Final — `/impeccable polish`**: Re-run screenshots across desktop/phone and light/dark once fixes land.

## Questions to Consider

- Should **every** collection write in this dialog pass through the same review footer, or is “precon direct add” intentionally a faster power path?
- Is the default search action supposed to mean “add nonfoil,” or should users always choose a finish before staging?
- On phone, should the review table remain dense, or should it switch to larger stacked cards once a row has editable controls?
