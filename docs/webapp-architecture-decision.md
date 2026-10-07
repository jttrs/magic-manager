# Decision doc — publishing `magic-manager` as a multi-user web app

**Status:** proposed · **Date:** 2026-10-02 · **Scope:** greenfield infrastructure for a
published, multi-user web product built *on top of* the existing `magic-manager` Python core.

> This is a design/architecture record, not an implementation. It exists to be read by the
> new session that lays the infrastructure. It records *why* each choice was made so the
> decisions are re-litigable later with the reasoning intact.

> **Part I (§1–10)** was authored first and scopes the *published multi-user product*
> (FastAPI + Postgres + auth + job queue). **Part II (§11+)** was added afterward by a
> second agent to capture the *originating user prompt* that triggered this work and the
> *feature-level, local-first* decisions it implies (two specific views, a component/token
> system, resizable panels, an amber palette, printing-selection rules, Playwright UX
> pinning). Part II is deliberately narrower than Part I and notes where the two scopes
> meet — read §11.1 first for that reconciliation.

---

## 1. The decision in one paragraph

Do **not** rewrite the engine, and do **not** treat this as a "React vs vanilla" question.
The web app is a **third thin adapter** over the existing `src/magic_manager/*` modules —
siblings to the two adapters that already exist (`cli.py` for the terminal, `.claude/skills/*`
for Claude). Build a **FastAPI** HTTP layer + **task queue** + **Postgres** behind it, and lead
the frontend with **server-rendered HTML + HTMX + Alpine islands** (escalating to **SvelteKit**
only for genuinely app-like views such as a live deckbuilder). React is not called for by
anything in the current or stated-future requirements.

---

## 2. Context & requirements (what changed)

The original tool is **local-first, single-user, no service, view-mostly** — under those
premises vanilla HTML (as already shipped in `gallery.py`) was correct. The new requirements
remove every one of those premises:

- **Published** — real users, on the internet, with a build/deploy pipeline.
- **Auth** — accounts, sessions, per-user data isolation.
- **Significant live DB mutation** — inventory edits, intake, deck building from the browser.
- **Lots of external fetching** — Scryfall + deck-host endpoints (Moxfield/Archidekt/MTGGoldfish/
  ManaBox/Scryfall), i.e. long-running, rate-limited, cache-sensitive I/O.
- **Every script becomes a user-runnable UI feature** — the ~20 `scripts/*.py` + CLI commands
  each need a UI surface to configure and run.

Each of these individually weakens the vanilla case; together they flip it.

---

## 3. The load-bearing principle: scripts are already decoupled from delivery

The repo's **core engineering rule #1** — *thin skill wrappers over deterministic scripts; the
real work lives in `scripts/*.py` / `src/magic_manager/*`* — is the thing that makes this a
modest lift rather than a rewrite. Logic is already decoupled from its delivery mechanism:

```
                 ┌─ cli.py (Typer)          → terminal (you)
src/magic_manager ┼─ .claude/skills/*        → Claude
   (the engine)   └─ NEW: web API + UI       → published users
```

**Hard constraint that cascades into everything else:** the web backend MUST be Python and MUST
call the existing modules as a library. Re-implementing Scryfall/EDHREC/valuation logic in
TypeScript would violate DRY catastrophically and discard the tested engine (selectors,
provenance ledger, valuation, family resolution, …). This is settled before framework choice.

---

## 4. The non-obvious core: these are *jobs*, not request/response

"Lots of external fetching" + "significant mutation" means most script-runs are **long-running**
(seconds→minutes: a bulk EDHREC warm, a sealed-value batch, a Moxfield import, a family sync).
They cannot be modeled as synchronous HTTP — the browser would hang/time out. **Every** script
UI therefore shares one interaction shape:

> **configure inputs → enqueue job → stream progress → render artifact(s)**

The engine already has the seams for this: `edhrec.sync_bulk(..., progress=...)` takes a progress
callback; the report tooling already thinks in *progress + artifacts* (md/json/xlsx/html). That
callback becomes **server-sent events** to the browser. A script is uniformly:

```
typed inputs  →  job (off the request thread)  →  artifacts (table | gallery | xlsx | json)
```

So the UI is **one job-runner chassis** reused ~20 times — not 20 bespoke pages. This single
decision is independent of frontend framework and is the most important one in the doc.

---

## 5. Backend architecture

| Concern | Choice | Why |
|---|---|---|
| HTTP layer | **FastAPI** | async (matches heavy concurrent external I/O); Pydantic maps onto existing dataclasses; first-class SSE/WebSocket for progress; thin — it only marshals calls into `src/magic_manager/*`. |
| Job execution | **Task queue** (arq or Dramatiq on Redis) | runs scripts off the request thread; where Playwright/Moxfield import runs **server-side** (never in a user browser); natural home for the `progress=` callback → SSE bridge. |
| Database | **Postgres, user-scoped** | single-file SQLite + "one user" does not survive multi-user live mutation. Every table grows a `user_id`; `inventory`/`decks`/`wishlist`/`earmarks` become per-user. |
| External I/O | **Shared, compliant fetch layer** (see §7) | server-wide cache + central rate limiter, not per-user wrappers. |

**Postgres migration is eased by the existing design:** the provenance ledger (V19) is already
**event-sourced** — `inventory_events` is an append-only signed-delta fact table and
`inventory.quantity` is the derived projection `SUM(delta)`. Multi-user systems *want* exactly
this shape (per-user isolation, audit, reconciliation are trivial over an append-only log). The
hard part is already built; the migration is mechanical ("add `user_id`, change the dialect"),
not a redesign. The selector DSL, valuation engines, and family resolution are
storage-agnostic and port unchanged.

---

## 6. Frontend architecture

The interaction shape (§4) is overwhelmingly *form → launch job → watch progress → view a
table/gallery/download*. That is **many simple interactive views**, not one deeply-stateful SPA.

**Lead with server-rendered HTML + HTMX + Alpine islands:**

- **Jinja** server-renders each view in Python — rendering logic sits next to the Python that
  produces the data; continuous with how the repo already works.
- **HTMX** handles form-submit / fragment-swap / **SSE progress** natively — it *is* the
  job-runner pattern, with no separate JSON API contract to maintain and no second language.
- **`gallery.py`'s existing client JS** (filter/sort/search/chips) survives **verbatim** as an
  **Alpine island** — already framework-free, already working, drops straight in as view #1.
- Minimal build step (asset bundling for publish only).

**Escalation condition → SvelteKit (not React):** only where the UI becomes genuinely *app-like*
with rich interdependent client state — e.g. live drag-and-drop deckbuilding, real-time
collaboration. Script-runners don't have that; a deckbuilder might. If/when that lands, pick
**Svelte/SvelteKit** (compiles away, tiny runtime — closest to the no-heavy-runtime instinct that
made vanilla attractive) and treat `gallery.py`'s logic as a Svelte component fed by the same
JSON. **Do not default to React out of habit** — nothing described specifically needs it.

### Why not React (for the baseline)
React's strengths — large-team component reuse, complex client-side state, SPA routing, a
data-fetching ecosystem — solve problems the **job-runner baseline doesn't have**. It would add
a second language/ecosystem, a mandatory bundler, and a JSON API contract to maintain, for
interactions HTMX serves directly. Reconsider only under the escalation condition above, and
even then Svelte is the better fit for this project's instincts.

---

## 7. Publishing changes the compliance posture (hard requirements)

Two current mechanisms are fine personally but **do not survive as a public service**:

1. **Scryfall** — explicit API guidelines (~10 req/s, mandatory caching, no bulk hammering). The
   personal 24h-cache wrapper must become a **server-wide shared cache + central rate limiter**
   (Redis) serving all users from one polite upstream pipe. This is both a compliance requirement
   *and* a performance win (500 users valuing FIN hit one warm cache, not 500 cold fetches). The
   multi-user constraint and the correct design point the same way.
2. **Moxfield import via headed Chrome through Cloudflare** — fine for personal use; as a
   published service it does not scale (a real browser per import) and is very likely against ToS.
   **Drop or demote to "paste your export."** The clean API-based importers (Archidekt,
   MTGGoldfish, ManaBox, Scryfall) are fine to keep.

Also net-new for "published": secrets move out of a repo-root `.env` into a real secret manager;
per-user OAuth/credentials for any service that needs them; rate-limit/abuse protection on the
job queue itself.

---

## 8. What survives vs what's net-new

**Survives unchanged (the engine):** selectors DSL, valuation (`sealed`/`construct`), family
resolution, provenance ledger, EDHREC client+engine, `gallery.py` renderer + its client JS, all
`exports/*`, the JSON data contract (already called "the eventual web-app data contract" in the
docs).

**Net-new (the "publish" word creates these):**
- Auth + per-user data model (`user_id` across tables).
- Job/progress infrastructure (queue + SSE chassis).
- SQLite → Postgres multi-user migration.
- Shared compliant external-fetch layer (cache + rate limiter).
- The HTMX UI chassis (one job-runner, reused per script).
- Retiring browser-driven Moxfield scraping.

---

## 9. Phased plan (blueprint for the new space)

1. **Library-ify** — stabilize a clean Python API surface over `src/magic_manager/*` so the web
   layer calls functions, not CLI. (Mostly already true; formalize signatures + typed return
   objects. Each script → `inputs → artifacts` function.)
2. **Chassis** — FastAPI + task queue + SSE; one generic "run a job, stream progress, return
   artifacts" endpoint + one HTMX job-runner view. Wire **one** script end-to-end as the vertical
   slice (suggest `edhrec sync_bulk` — it already has a `progress=` callback).
3. **Data** — SQLite → Postgres; add `user_id`; port the event-sourced ledger (ports cleanly);
   auth + sessions.
4. **UI breadth** — port `gallery.py` as view #1 (Alpine island); generate the per-script
   configure-forms from the uniform input contract.
5. **Compliance** — shared Scryfall cache + central rate limiter; secret manager; demote Moxfield
   import to paste-export.

Each phase is independently shippable and keeps the engine as the single source of truth.

---

## 10. Open questions to resolve in the new space

- Hosting target (VPS / Fly.io / Render / container platform) — drives deploy + Playwright story.
- Expected concurrency / scale (shapes queue sizing + Scryfall rate-limit budget).
- Which scripts are "safe to expose" vs "admin-only" (e.g. anything that mutates shared data or
  drives a browser).
- Deckbuilder on the roadmap? (the one feature that would justify the SvelteKit escalation).
- Multi-tenancy model: one shared `cards`/price cache across users (recommended) vs per-user.

---

# Part II — the originating feature request (local-first UI upgrade)

**Status:** proposed · **Date:** 2026-10-02 · **Added by:** second agent (after Part I), to
record the *verbatim user prompt* that kicked off this work and the concrete, feature-level
decisions it implies. Part I reasons about the eventual *published* product; Part II is the
*next actual increment* — a component-and-token UI for two existing deterministic views,
running locally. They are the same trajectory at two zoom levels (see §11.1).

## 11. The user's initiating prompt (verbatim)

> for missing set card diff display, showing exact printings is important. for the edhrec
> commander diff display, having random treatments and sets is visually confusing, we should
> standardize on the chronologically first standard printing of it (no foil or borderless
> treatment unless there is no other option). having the distinct pools (a_only, both, b_only)
> as vertically stacked in the same view isn't really helpful, they should each be in their own
> horizontally stacked panels that can be individually toggled and resized with a divider drag.
> if you need to start building a web app framework to handle this with components and tokens
> and no hand-rolled or in-line building so we can centralize it and guard it, you need to start
> doing that. also the light green pallette from cabbage should shifted to an amber focused
> palette instead. playwright headless tests to pinned behavior after you have thoroughly
> evaluated those behaviors looking at them with playwright to evaluate UX of it. we want the
> missing set card display to also use the same scripts and components so we will need to
> understand how to factor these two different kinds of views to avoid DRY violations and for
> ease of ongoing maintenance. there should be a shell with a header for the entire web app and
> a topnav to navigate between the two different kinds of views, and dropdown menus to input
> cards for the diff along with the other kind of filter config in the sidepanel. sidepanel
> should not go up to the top of the entire view, the top nav should go across. use
> /frontend-design:frontend-design to evaluate thoroughly.

### 11.1 How Part II relates to Part I (scope reconciliation)

Part I answers *"how do we publish this as a multi-user product?"* Part II answers *"what is the
next build, now?"* The prompt itself contains the bridge — "if you need to start building a web
app framework … you need to start doing that" — i.e. this feature is explicitly the **seed of the
Part I frontend**, not a throwaway.

The reconciliation that keeps them from fighting:

- **Build the component + token layer now (Part II), framework-agnostically**, so it is the same
  layer Part I's frontend consumes later. Tokens as CSS variables and components with a clean
  data-in contract survive the HTMX/Alpine (or SvelteKit) decision in Part I §6 — none of them
  rewrite CSS tokens or a card-tile's markup.
- **`gallery.py`'s client JS is named in Part I §6/§8 as surviving verbatim as an Alpine island.**
  Part II's refactor (componentizing + tokenizing it) must therefore *preserve that drop-in
  property*: the output stays framework-free, data-driven HTML/CSS/JS. Don't adopt a component
  runtime (React/Svelte) in Part II that would contradict Part I's "lead with HTMX + Alpine,
  escalate to Svelte only for app-like views." The two resizable-panel diff views are **not** the
  app-like escalation case — they are filter/sort/view surfaces, exactly the island shape.
- **Data delivery:** Part II can ship against the **static JSON contract** that already exists
  (`output/edhrec/reports/*.json`) OR a thin local read-only server, but it should NOT invent a
  bespoke data path that Part I's FastAPI layer would then have to replace. The card-input
  dropdowns (below) are the one place this tension is real — see Open Decision D2.

**Net guidance for the implementing agent:** treat Part II as *Part I Phase 4 ("UI breadth")
brought forward*, built in a way that is forward-compatible with Phases 2–3, not as a separate
UI that will be thrown away.

## 12. Feature-level decisions the prompt fixes (not open)

These are stated requirements, recorded so the new agent treats them as settled:

| # | Requirement | Detail |
|---|---|---|
| F1 | **Two distinct views, shared components** | "missing-set card-diff" view AND "edhrec commander-diff" view, factored over ONE component/script set (no DRY violation). |
| F2 | **Missing-set shows EXACT printings** | The card-diff/missing-set view must keep rendering the precise printing the user owns-or-lacks. Do **not** apply the oracle-collapse from F3 here. |
| F3 | **EDHREC-diff shows the chronologically-first STANDARD printing** | Per oracle card, pick the oldest *standard* printing — no foil, no borderless/showcase/extended/etc. treatment — *unless no standard printing exists*, then fall back. Kills the "random treatments and sets" visual noise. |
| F4 | **Pools become horizontal resizable panels** | The EDHREC `a_only` / `both` / `b_only` buckets stop being vertically stacked sections in one scroll; each becomes its own horizontally-stacked panel, **individually toggleable** and **resizable via a draggable divider**. |
| F5 | **Component + token architecture; no hand-rolled inline building** | Centralize into guarded components and design tokens. The current `gallery.py` string-concatenation + inline `_STYLE`/`_SCRIPT` is the thing being replaced for maintainability. |
| F6 | **Amber palette** | Shift the "cabbage" light-green accent (oklch hue ~145) to an amber-focused palette (hue ~70–85). Tokenized, single source. |
| F7 | **App shell: header + top-nav; sidebar below the nav** | A global header + horizontal top-nav spanning the full width to switch between the two views. The side-panel must NOT extend to the very top — the top-nav crosses the whole width; the sidebar starts below it. |
| F8 | **Side-panel inputs** | Dropdown menus to input the cards for the diff, plus the other filter config, live in the side-panel. |
| F9 | **Playwright: evaluate UX first, then pin** | Use Playwright to *look at and evaluate* the behaviors (headed, interactive UX assessment) BEFORE writing headless Playwright tests that pin the finalized behavior. Evaluation precedes pinning — not test-first. |
| F10 | **Use `/frontend-design:frontend-design`** | Run that skill to evaluate the design thoroughly (bold, non-generic aesthetic; tokenized; distinctive typography — see its guidance, quoted in §14). |

## 13. Codebase findings that constrain the implementation

From a thorough read of the current code (file paths for the implementing agent):

- **No JS/TS tooling exists.** Pure Python + `uv`; `pyproject.toml` build-backend is `uv_build`;
  no `package.json`, `web/`, `node_modules`, bundler, or `.css` files anywhere. A component/token
  layer is genuinely net-new (greenfield subdir), not a refactor of existing JS.
- **The only HTML/CSS/JS today is `src/magic_manager/gallery.py`** — a single module that
  string-builds the whole document: `_STYLE` (the `:root` token block + rules), `_SCRIPT`
  (filter/sort/search/export JS), `_tile_html`, `render_gallery`. This is F5's target.
  - Public surface already generalized (from PR #77): `PoolSpec{key,label,color_var}`,
    `GallerySection{code,name,summary}`, `SortSpec`, `ExportSpec`, `render_gallery(...)`,
    `merge_tiles`, `tile_sort_key`, and a documented **tile dict contract** (name/set/cn/
    rarity/finish/usd/image_uri/scryfall_url/pools/badge/sort_values/data_attrs/row).
  - **Color tokens to retokenize for F6** live in `gallery.py` `_STYLE :root`:
    `--accent: oklch(0.78 0.11 145)`, `--accent-soft: oklch(0.30 0.05 145)`,
    `--accent-soft-fg: oklch(0.92 0.06 145)`, and `--p3: oklch(0.78 0.11 145)` are the
    cabbage greens (hue 145 → amber ~75-80). Neutrals (hue 60), `--info` (blue 250), `--warning`
    (golden 72), and `--p1/p2/p4..p8` can stay; `--p3` collides with the new amber accent so it
    should be reassigned a distinct hue.
- **Two views already produce the needed data, but asymmetrically:**
  - EDHREC `compare` **emits JSON** (`scripts/edhrec_report.py` → `_write_compare_json` /
    `_compare_card_dict`): top-level `{kind,name_a,name_b,slug_a,slug_b,prices_as_of,
    generated_at, cards:[...]}`; each card `{name,oracle_id,slug,bucket,tags,a_pct,b_pct,
    a_decks,b_decks,delta,synergy_a,synergy_b,trend_a,trend_b,type_line,cmc,mana_cost,
    color_identity,rarity,lowest_usd,lowest_usd_foil,scryfall_id,set_code,collector_number}`.
    This is the de-facto web-app contract for the compare view.
  - **card-diff / missing-set emit NO JSON today** — only HTML (`scripts/card_diff_html.py`) and
    buy-list txt/xlsx (`mm query missing-set`). The dataclasses exist and are clean
    (`card_diff.FamilyDiff` → `CardDiffPool{name,count,usd,rows}`; rows are
    `selectors.MaterializedRow{scryfall_id,quantity,finish,card}` or
    `missing.FunctionalMissingCard`). **A JSON writer for card-diff is a prerequisite** for F1's
    "same components" — the components should consume a JSON contract, and card-diff needs one to
    match the compare view's shape.
- **F3's "chronologically-first standard printing" has no existing helper.** `sets.lowest_price_
  by_oracle` ranks by `(prices_usd IS NULL), prices_usd, collector_number` — cheapest, not
  oldest-standard. The pieces to build the sibling exist:
  - `treatments.compute_treatment(row, finish="nonfoil")` returns `""` **iff** the printing is
    standard (no b/fa/shw/ext/sm/ff). This is the "is standard" predicate.
  - **Set release dates are NOT stored locally** — the `cards` table has `set_code` but no
    `released_at`, and there is no `sets` table. `scryfall.all_sets()` returns per-set
    `released_at`; chronology must come from there (cache per-run, or persist via a small
    migration — see Open Decision D4).
  - Recommended new seam: `sets.standard_printing_by_oracle(oracle_ids)` — a sibling of
    `lowest_price_by_oracle` returning the same dict shape, ranked
    `ORDER BY is_nonstandard ASC, set_released_at ASC, collector_number ASC`. The EDHREC enrich
    path (`edhrec.compare_commanders` → the `lowest_price_by_oracle` call) swaps to it for the
    *image/printing* fields while **keeping `lowest_usd` from the price helper** (the displayed
    floor price should stay the cheapest, independent of which printing's art is shown).
- **Playwright is already a core dep** (`pyproject.toml`), used **only for scraping**
  (`scripts/moxfield_session.py`, `import_deck.py`), **sync API, headed-capable**. No UI tests
  exist. F9's tests are net-new under `tests/` and should mirror the sync-API pattern; a static
  gallery opens over `file://` (no server needed to pin behavior) unless D2 picks a server.
- **DRY/convention guards to honor:** core rule #1 (thin wrappers over deterministic scripts) and
  #2 (don't duplicate; lift shared logic to a shared home). The component layer is the UI analog:
  one `card-tile`, one `resizable-panels`, one `app-shell`, one token file — both views compose
  them. `util.output_dir(type,category)` remains the single artifact-location seam.

## 14. `frontend-design` skill guidance (quoted, for F10)

The skill (`.claude/plugins/cache/.../frontend-design/skills/frontend-design/SKILL.md`) directs:
commit to a **bold, intentional aesthetic**; **CSS variables for theming**; **distinctive
typography** (explicitly *avoid* Inter/Roboto/Arial/system fonts and "cliched purple-gradient-on-
white" AI-slop); dominant colors with sharp accents over timid even palettes; atmosphere/texture
over flat fills; **match code complexity to the aesthetic** (refined-minimal needs restraint +
precision). For this project that argues for a confident dark, amber-accented, card-dense
aesthetic with a characterful display face — not a generic dashboard. Run the skill to generate
the concrete direction before locking tokens/typography.

## 15. Open decisions + recommendations (for the new agent to confirm)

These were surfaced but NOT settled — each carries my recommendation and reasoning so the new
(more recent) model can decide fast.

- **D1 — Frontend runtime.** *Recommendation:* **vanilla + Vite + TypeScript web components with
  CSS-variable tokens** — NOT React. Reasoning: it satisfies F5 (real components, no inline
  building, a build to guard/tree-shake) while staying forward-compatible with Part I §6, which
  explicitly leads with HTMX+Alpine and names Svelte (not React) as the only escalation. Web
  components (or a micro-lib) render framework-free HTML that drops into an Alpine island later.
  React would contradict Part I and over-weight two filter/sort views. *Alternative if the new
  model disagrees:* SvelteKit — also Part-I-sanctioned, better DX, compiles small; acceptable if
  the agent judges the resizable-panel state richer than I estimate.
- **D2 — Data delivery / card-input dropdowns.** The one real tension. F8's "dropdown menus to
  input cards for the diff" implies the UI triggers *new* compares (pick commander A + B → run),
  which static JSON can't do. *Recommendation:* a **thin local read-only `mm serve`** (stdlib
  `http.server` or minimal FastAPI) exposing `GET /api/edhrec/compare?a=&b=` and
  `GET /api/card-diff?families=` over the existing library functions, so dropdowns re-query live;
  this is literally Part I §4's job-runner chassis in miniature and the natural seed for it.
  *Lighter alternative:* ship static-JSON-driven views now (dropdowns only *filter* an
  already-generated dataset; new compares still run via CLI) to defer the server to Part I. Pick
  based on how much "input new cards from the browser" must work in this increment.
- **D3 — Scope of this increment.** *Recommendation:* **app shell + tokens + the EDHREC-compare
  view (with F4 resizable panels) first**, then fold in the card-diff view once the shared
  component factoring (F1) is proven on one consumer — lower risk than building both blind. The
  card-diff view also needs its net-new JSON writer first (see §13). *Alternative:* both views at
  once if the agent wants to validate the shared-component abstraction against two consumers
  immediately (stronger DRY proof, more up-front work).
- **D4 — Set release-date source for F3.** *Recommendation:* **persist release dates** (a small
  `sets` table or a `cards.released_at` column backfilled from `scryfall.all_sets()`) rather than
  fetch per-run — chronology becomes offline/fast and reusable, and it's a natural companion to
  Part I's Postgres move. *Alternative:* cache `all_sets()` in-process per run (zero migration,
  recomputed each run) if the agent wants to avoid schema churn now.
- **D5 — Where the component layer lives.** *Recommendation:* a new top-level `web/` dir
  (`web/src/{tokens.css,components/*,views/*}`, `web/vite.config.ts`, `web/package.json`) — keeps
  JS tooling quarantined from the Python package, matches Part I's "third adapter" framing.
  `gallery.py` is then either retired (its JSON contract feeds the web app) or kept as the
  CLI/offline renderer while the components become the canonical UI — the agent should decide
  whether to keep a no-server self-contained HTML path for portability.
- **D6 — Migration of the existing self-contained HTML.** `gallery.py` currently ships a working
  `file://` gallery for both card-diff and compare. *Recommendation:* keep it running until the
  web app reaches parity (don't break the shipped feature), then decide retire-vs-coexist. Any
  retokenizing (F6) should happen in BOTH places until then, or the amber shift should land in
  `gallery.py` first (cheap, immediate) and be the token source the web layer imports.

## 16. Suggested first moves for the new session

1. Run `/frontend-design:frontend-design` to lock the amber aesthetic + typography (F6/F10).
2. Decide D1/D2/D3 (framework, data delivery, scope) — the rest is downstream of these.
3. Build `sets.standard_printing_by_oracle` + a release-date source (F3/D4); unit-test it against
   known oracles (e.g. a card with many treatments resolves to its oldest plain printing).
4. Add a **card-diff JSON writer** so both views share one contract shape (F1 prerequisite).
5. Scaffold `web/` with the token file (amber) + `app-shell` (header + full-width top-nav +
   below-nav sidebar, F7) + `resizable-panels` (F4) + `card-tile` + the two views.
6. Evaluate UX in Playwright headed (F9), iterate, THEN write headless pinning tests.

---

# Part III — Decisions locked (2026-10-02, `feat/webapp-chassis`)

Reconciles Parts I–II after a product interview (see `PRODUCT.md`) and research. **Supersedes**
Part I §6 ("lead with HTMX + Alpine; not React") and §15 D1. Rationale: with the product
understood as a published, multi-user, *app-like* collection manager (thousands-of-card galleries,
URL-addressable filters, live inventory mutation, mobile + desktop first-class, deck composition
next) and agents maintaining the code, migration cost from the prototype is explicitly discounted
in favor of the best end product.

## 17. Stack

| Concern | Decision | Why |
|---|---|---|
| Frontend | **React + TypeScript + Vite SPA** (no Next.js) | Deepest *original* a11y/interaction ecosystem; strongest agent fluency (stable API since 2019 vs Svelte 5 runes churn); React Compiler 1.0 removes manual memoization. No SEO need behind auth → no Node server tier. |
| URL state | **TanStack Router** + zod-validated search params | Filters, panel layout, diff inputs are deep-linkable and typed. |
| Server data | **TanStack Query** + a TS client **generated from FastAPI OpenAPI** | One typed contract; optimistic mutations. |
| Large lists | **TanStack Virtual** | Virtualize >50 items. |
| F4 panels | **react-resizable-panels** | Collapsible panels + WAI-ARIA Window Splitter keyboard separators. |
| Primitives | **Radix via shadcn/ui** (owned code) | Accessible combobox/menu/popover/dialog restyled by tokens. |
| Drag & drop (future deckbuilder) | **Atlassian Pragmatic drag-and-drop** (framework-agnostic core) | Portability. |
| Tokens | **DTCG JSON → Style Dictionary → CSS variables → Tailwind v4 `@theme`**; default palette disabled; lint bans arbitrary values | Single guarded source; amber (F6). |
| Backend | **FastAPI + Pydantic v2 + native SSE**; jobs via **Taskiq** (InMemory broker locally, Redis in Phase 3) | arq is maintenance-only; Taskiq runs without Redis today. |
| Tests | **Vitest** (pure TS) + **Playwright Test (TS)** E2E | E2E pins behavior independent of framework. |

## 18. Portability architecture (React → Svelte stays feasible)

Svelte was judged a modestly better *end product* on phone first-load and large-grid interaction
smoothness; React won on maturity, a11y originals, typed URL state, and agent fluency. To keep a
later migration ~30–40% of frontend code and incremental per route:

1. Domain logic stays in Python (engine = single source of truth).
2. Frontend logic in **plain TS modules** (`web/src/core/`): API client, zod URL schemas, pure
   view-model derivations — framework-free, Vitest-tested.
3. Prefer framework-neutral cores (TanStack Query/Virtual, Pragmatic DnD).
4. Components are presentational (props in, events out); no business logic in components.
5. Tokens are CSS variables (survive any framework).
6. Playwright E2E is the migration safety net.
7. Avoid React-only lock-in (RSC, Next.js). Router glue is the accepted rewrite cost.

## 19. Remaining Part II decisions

- **D2:** live local server (FastAPI) — dropdowns trigger new compares.
- **D3:** sequence on this branch: typed API/job layer → shell + amber tokens (impeccable
  new-work) → EDHREC-compare view → card-diff view.
- **D4:** persist set release dates (small `sets` table backfilled from `scryfall.all_sets()`).
- **D5:** frontend in top-level `web/`; Python adapter in `src/magic_manager/web/`.
- **D6:** `gallery.py` keeps working until the app reaches parity; then retire/coexist decision.
- **IA:** domain-oriented sections (Collection, Sets, Decks, Commanders, Market); long-running
  jobs are background infrastructure (progress tray), not "run script X" pages.

## 20. Status (end of first build on `feat/webapp-chassis`)

- **Built:** `magic_manager.api` (typed reads + `JobSpec` registry), `magic_manager.web` (FastAPI + Taskiq in-memory + SSE job chassis; vertical slice `edhrec.sync_bulk` end-to-end with progress, incl. a new optional `on_resolve` pre-pass callback), V27 `cards.released_at` + `sets.standard_printing_by_oracle` (F3), card-diff JSON contract (F1), and the `web/` SPA: shell (F7), amber "After-Hours Price Guide" world with light/dark tokens (F6/F10), commander compare with toggleable + resizable columns (F4), missing-set view with exact printings (F2), Grid/Rows density, highlighter marks → buy/pull lists. Visual record: `DESIGN.md`; product record: `PRODUCT.md`.
- **Guards:** pytest (`tests/test_web_api.py`), vitest (`web/src/core`), Playwright pinning suite (`web/e2e`, offline fixtures), stylelint (no raw colors), dependency-cruiser (`core/` framework-free; no cycles), knip.
- **Not yet done / honest gaps:** React Compiler is *not* enabled yet (§17 cites it as the memoization answer; enable when the Vite React plugin path is settled — TanStack Virtual is flagged incompatible with compiler memoization and will need an opt-out). Collection/Decks/Market sections, Postgres/auth (Phase 3), shared Scryfall cache + rate limiter (Phase 5) remain future splits. `gallery.py` still ships the `file://` galleries (D6: keep until parity, then decide).

## 21. Status — iteration 2, P1 (`feat/web-collection`)

Plan: `~/.claude/plans/splits/web-iteration-2.md` (approved 2026-10-04). P1 delivered: **Collection** replaces Sets as the first tab (whole families with per-finish owned counts; owned/missing + finish + a grouped Card-types picker (rarity / treatment subtypes / chase) in one Show section; Reset), engine seam `collection_view.family_cards` (3 queries/family) + `buy_lines`; `scryfall.all_sets` memo (family listing 5 s → 0.1 s); `treatments.is_standard_frame` lifted as the shared "plain printing" predicate; `MultiSelect` (>5 options) and the hierarchical `SortBuilder` (URL-encoded rules, presets, Pragmatic DnD + ▲▼) shared by Collection and Commanders; card facts moved under the art; "Commanders" title. Card-diff web API retired (the CLI/gallery keep `card_diff`). Process fix: impeccable `critique` (dual-agent) run on fully loaded real data — 26/40, all P1/P2 issues applied; snapshot in `.impeccable/critique/`. Next: P2 ingest modals → P3 Deck Manager; P4 Scryfall tags in PR #79.

## 22. Status — iteration 2, P4 (`feat/scryfall-tags`)

V28 rebuildable cache `scryfall_tags` + `card_oracle_tags` from Scryfall's OFFICIAL `oracle_tags` bulk file (via `scryfall.sh bulk`, host-locked to `data.scryfall.io`; guard hook extended), keyed on tag UUID. `magic_manager.scryfall_tags` (sync / roll-up through the hierarchy / batched `card_summaries`), curated function roots in `config/function_tags.toml`, `mm scryfall tags sync|show`, `scryfall.sync_tags` JobSpec (Jobs view button). The compare contract gains `CompareCardOut.functions` + `oracle_tags` and `CompareOut.functions` (root key/label, display order) via ONE batched lookup. Commanders view: **Group by** `Card type | Function` (URL `groupBy`); multi-function cards appear in each group with an "also: …" note; the card hover preview lists functions + top tags below the art. After P1 merged: Collection gains a **Function** MultiSelect in Show (URL `fn`, OR across roots + a "No tagged function" option; Reset clears it), fed by `CollectionCardOut.functions` + `CollectionOut.functions` from one batched lookup; Collection hover previews list functions too. `GuideCard.oracleTags` (preview-only) is distinct from P1's printed-fact `tags`. Not yet: art tags; touch access to the preview.

## 23. Status — iteration 2, P2 (`feat/web-ingest`)

Add-cards dialog on Collection: **Search** (live printing search, stage copies), **Paste a list** (Moxfield/ManaPool/Arena/TCGplayer/names → server resolve → review → commit), **Deck or precon** (deck URL → `ingest.fetch_deck` job → review; precon catalog → `ingest.precon` job). Engine `magic_manager.addcards`, API `api.ingest` (contract written first so UI and engine were built in parallel). Every commit is ONE ingest event (`adhoc` / `import-block`, label `web:*`) — no migration; the ledger reconciles. Shared `useJob` hook (lifted out of JobsView). Undo stays deferred (a reversing event).

## 24. Status — iteration 2, P3 (`feat/web-decks`)

Deck Manager at `/decks`: grouped deck-recipe list (set / year / state / format / source, search, built/loose) + resizable inspector (decklist sections, cards or list view, card inspector), with "Add deck to collection" / "Add N marked" feeding the P2 add-cards review (exact printings, one ingest event). Engine `magic_manager.deck_view` (set-based summaries, ~0.25 s for 580 decks), API `api.decks`. The card detail sheet planned for P3 shipped earlier as the card inspector (#83). Deck editing (versions, compose/decompose) stays CLI for now.

## 25. Phase 3 — hosting, login and per-user profiles (shaped 2026-10-06, `torre/hosting-auth-profiles`)

**Status:** decisions signed off by the owner 2026-10-07. Supersedes Part I §5's "Postgres,
user-scoped" row and §9 phase 3 ("SQLite → Postgres; add `user_id`"). Nothing is built yet.

**Facts that drove it.** Of the 677 MB DB, ~650 MB is shared cache (EDHREC pages, `cards`,
Tagger tags); one user's data (the 14 `undo.USER_TABLES`) is ~6 MB. The engine has ~346 raw
SQLite queries. SQLite resolves unqualified table names across `ATTACH`ed databases, so the same
queries run against one file or against a catalog file + a user file. Research (shared schema +
Postgres RLS is the SaaS default; database-per-tenant is increasingly preferred for many small
tenants because isolation is physical and export/delete is a file operation; hybrids with a
shared catalog are emerging):
[Redis](https://redis.io/blog/data-isolation-multi-tenant-saas/),
[asadali.dev](https://asadali.dev/blog/multi-tenant-saas-practical-comparison-database-per-tenant-vs-shared-schema/),
[Augmented Dev](https://theaugmenteddev.com/blog/multi-tenant-data-isolation-patterns-saas).

### 25.0 Binding principle — users' security (owner, 2026-10-07)

> "we should also be very aware of security concerns users may have and develop in a way that we
> cannot be used by a malicious actor to harm our users."

Every Phase 3 decision is held to this. Concretely, for hosting:

- **Per-user isolation enforced server-side.** The user is derived only from the server-side
  session; client-sent user ids are never trusted. Each request opens only that user's DB file
  (H1), and a test proves one user cannot read or write another's file.
- **Auth/session hardening.** HttpOnly + Secure + SameSite cookies, CSRF protection on every write,
  OAuth state + PKCE, session expiry/rotation, and rate limits on login and writes.
- **No admin "act as user".** Admins manage invites and flags; they cannot impersonate users or
  read their collections through the app.
- **Secrets only in the host's secret store.** Never in the repo, images, logs or the client (H13).
- **Export and delete-my-data** are self-serve (H10).
- **Dependency and supply-chain hygiene.** Lockfiles committed (`uv.lock`, `package-lock.json`),
  automated dependency/vulnerability updates, pinned CI actions and base images, minimal
  extension permissions (H12).
- **Security review before any hosted launch.** No outside user gets access until a security
  review of the hosted build passes.

The browser companion (H12) applies the same principle with its own threat model.

### 25.1 Decisions

| # | Concern | Decision |
|---|---|---|
| H1 | Data model | **Shared catalog DB + one small SQLite DB per user**, `ATTACH`ed per connection. Catalog = cards, prices, sets, Tagger/art tags, EDHREC, MTGJSON caches. User DB = `undo.USER_TABLES` (inventory + ledger, decks/cards/versions/assignments, wishlist, earmarks + prices, set targets, settings, imports). `inventory == SUM(inventory_events.delta)` holds per user file. No `user_id` columns. |
| H2 | Database | **Plain SQLite files on the server's persistent disk** (`/data/catalog.db`, `/data/users/<id>.db`, `/data/auth.db`), continuously replicated offsite with **Litestream** (object storage, e.g. Cloudflare R2). Not Postgres, not Turso. |
| H3 | Owner's data | **Hosted becomes the owner's source of truth.** First account = the owner's user tables split out of today's DB (rehearsed per `db-upgrade`). Local mode keeps working for dev/CLI/skills against a copy. No two-way sync. |
| H4 | Auth | **Self-hosted OAuth only — Discord + Google** (Authlib, state + PKCE). No passwords, no email sender, no magic links (cheapest, smallest attack surface; providers own MFA/recovery). Server-side sessions in `auth.db` (users, linked identities, sessions); HttpOnly + Secure + SameSite=Lax cookie; CSRF protection on writes. |
| H5 | Access | **Invite-only** (allowlist / invite codes). The owner is **admin**. |
| H6 | Feature flags | Layered: `config/features.toml` defaults < local overrides < **per-user overrides set by the admin**. Flags that need the owner's machine are **pinned off** for everyone else. |
| H7 | Hosting (beta) | **A server in the owner's house during beta**, running the app **natively** (`uv run mm serve` as an always-on service — launchd on a Mac, systemd on Linux — deployed by `git pull`, like today's `.worktrees/live`), data under one data dir. Native keeps the H9 macOS features working on a Mac mini (Docker on macOS is a Linux VM: no `osascript`, no visible Chrome). **Docker is for the vendor move** (e.g. Fly.io/Railway take images; SPA optionally on Cloudflare Pages/Vercel): a `Dockerfile` (SPA + API + worker, data under `/data`) is **built in CI on every PR** so Linux portability stays honest; H9 features stay off there. Litestream makes the move a restore. |
| H8 | Worker | Single host ⇒ keep Taskiq's **in-process broker**; Redis only when a second host appears. Writes serialize **per user DB**; catalog writes (syncs) serialize globally. |
| H9 | Local-only features | Tab reading + AppleScript store reads (Deals), the Mana Pool cart (machine `.env` account), Moxfield browser import. **Interim:** admin-only flags that run only where the server is the owner's Mac running natively; hidden for everyone else. **Target: a Chrome extension (H12) replaces all of them**, so they work against any server — Docker/Linux included. Users are never asked for marketplace credentials. |
| H10 | Privacy | Store only OAuth subject id + display name + email. **Self-serve export** (download my user DB + CSV) and **delete my account** (removes the user file + auth rows; offsite backups age out of retention, e.g. 30 days). |
| H11 | Local mode | **Same engine, two layouts, one `MM_MODE` switch.** `local` = no login, today's single file untouched (or the split layout); `hosted` = login, catalog + the signed-in user's file. CLI/skills keep `MAGIC_MANAGER_DB`. |
| H12 | Chrome extension | A **Manifest V3 Chrome extension** is the browser-side companion that does, in the *user's own* browser, what the server can't: (a) **tabs** — `chrome.tabs` lists the user's open store/product tabs and posts them to the API (replaces `tabs.py`/`osascript`; a server reading its own browser is wrong once users are remote); (b) **rendered store pages** — `chrome.scripting` reads price/stock from a page the user already has open (replaces AppleScript `execute javascript`); (c) **Mana Pool cart** — reads the cart from the user's own logged-in Mana Pool tab and posts only cart lines (H13); (d) **Moxfield import** — fetches the deck JSON from the user's own browser session (Cloudflare already cleared), replacing the headed-Playwright path. It authenticates to our API with a token minted from the signed-in session (no cookies shared cross-site), requests narrow `host_permissions` per store, and only posts normalized page data to existing engine seams (`deals`, `cart`, `decksource`) — no logic in the extension. Chosen over bookmarklets (more legitimate, persistent permissions, works across tabs, store-distributable). |
| H13 | Mana Pool credentials (owner decision 2026-10-07) | **Split by purpose.** (1) **Personal cart reads** use each user's OWN Mana Pool account and their password **never reaches the server**: the cart is read client-side in the user's browser (export/paste or a browser-side reader, H12c) and the app receives only cart lines. No admin or admin-only workflow ever uses another person's credentials. Locally the owner's login lives in the **macOS Keychain**, not `.env`. (2) **Catalog/price lookups** (`manapool.sh`, product mapping, overpay) use a **project-owned service account** (email + API access token, no password), stored only in the host's secret store, used only by server code, never visible to admins, and shared through the server-side cache (Phase 5). Until hosted, `cart_check` stays internal + local-only behind its flag. |
| H14 | Analytics (owner decision 2026-10-07) | **A separate store from user data.** Hosted, it is its own Postgres database and role on a managed instance (columnar later only if volume needs it), with its own retention and backups. Locally it is a separate SQLite file (built by the analytics-layer session). Dashboard roles read analytics only, never user data. **Joins only by IDs:** `event_id`, `session_id`, `request_id`/`trace_id` (also carried in server logs and error responses) and app ids (`job_id`, `ingest_id`). **Users are a pseudonymous key** = HMAC(user_id, a server secret held in the host's secret store, rotatable); delete-my-data (H10) computes the key and deletes those events. |

### 25.2 Pinned / open

- **External access (partly decided, rest pinned):** the owner reaches the server over
  **Tailscale** (admin access, no open ports). Friends' access is pinned until the first outside
  user needs it — leaning **Cloudflare Tunnel + own domain** (~$10/yr, most polished) or
  **Tailscale Funnel** (free public HTTPS on a `ts.net` name). Either way invite-only OAuth (H4/H5)
  is the gate. Rejected: Tailscale node sharing for friends (every friend installs Tailscale),
  ngrok + basic auth (free-tier browser interstitial, bandwidth caps; demos only), router port
  forwarding (exposes the home IP). Until then the beta is LAN + owner's tailnet.
- **Home server hardware:** not decided. A Mac mini (native) keeps every H9 admin feature; an
  old PC/laptop (Linux, native or the Docker image, e.g. Proxmox + one container) works for
  everything except the macOS-only H9 features.
- **Analytics host vs H2/H7:** H14 names a managed Postgres instance, while user data is SQLite
  on a home server (H2/H7) with no managed instance yet. Open: a managed Postgres just for
  analytics, Postgres on the home server, or the SQLite analytics file until the vendor move.
- **Budget:** not set; expected beta cost ≈ a domain (~$10/yr) + free-tier object storage.

### 25.3 Consequences for the build

- **Migrations split in two:** catalog migrations (run once) and user migrations (run on every
  user file, at startup and on first login). `db.MIGRATIONS` needs a target per entry; the
  `db-upgrade` rehearsals cover both layouts.
- **`db.connect()` becomes layout-aware:** opens the user file as `main`, attaches the catalog
  (hosted) — or opens the single file (local). Table names must stay unique across the two
  files (a test guards it).
- **Undo** (`undo.py`) becomes per user (`users/<id>.undo.db`); `SessionGuard` keys on the user.
- **Request scoping:** the web layer resolves session → user → that user's connection; the
  engine stays unaware of users (no `user_id` parameters threaded through it).
- **Jobs** carry the user id; a user's job gets that user's connection.

### 25.4 Build order (small PRs, after sign-off)

1. Layout-aware `db.connect` + catalog/user table split + uniqueness test (no behavior change in
   local mode).
2. Migration targets (catalog vs user) + `db-upgrade` rehearsal support for the split layout.
3. Splitter: today's DB → `catalog.db` + `users/<owner>.db` (rehearsed; owner OK before apply).
4. `auth.db` + Discord/Google OAuth + sessions + CSRF + invite codes + admin role.
5. Per-request user connection, per-user undo, jobs carry the user.
6. Per-user feature flags + admin page; pin H9 features to the owner's machine.
7. Export / delete-my-account.
8. Litestream + native home deploy runbook (launchd/systemd). The Dockerfile + CI build land
   first, alongside this doc.
9. Chrome extension (H12): API token endpoint → tabs → rendered store reads → Mana Pool cart →
   Moxfield import; then drop the macOS-only paths' admin pinning (H9 interim).
10. Security review of the hosted build (§25.0) — gate before any outside user.
11. Owner admin access over Tailscale; friends' external access when the pinned item resolves.

Phase 5 (shared server-side Scryfall/MTGJSON/EDHREC cache + rate limiter; the browser-driven
Moxfield import is retired by H12) is re-evaluated **after** this lands.
