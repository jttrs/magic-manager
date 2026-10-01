# Web-app boundary — weaning off the agent

Status: **design + roadmap** (not yet implemented). This doc records the plan for
turning `magic-manager` from an agent-driven CLI into a web app with **no LLM in
the loop** — just UI widgets that set a deterministic script's parameters and run
it. It is the companion to the DRY-centralization work (Phases 0–5) that gave
every workflow a single deterministic home.

## The core principle

> Every decision a script makes is an **explicit parameter with a deterministic
> default**. The agent (today) or a widget (tomorrow) only *selects* parameter
> values — it never embeds logic.

A workflow is "web-app-ready" when a form of inputs + a button can reproduce it
with no model judgment. The centralization phases moved the *logic* into
`src/magic_manager/*` and `scripts/*`; this phase classifies the remaining
*agentic glue* and says how a backend reproduces each piece.

## Classification of every workflow

### DETERMINISTIC — already a widget away
These skills are pure relays to a deterministic CLI/script. A widget maps form
fields → flags and renders the output. No backend work beyond calling the script.

`set-status`, `card-diff`, `missing-from-set`, `jumpstart-missing`,
`jumpstart-buildable`, `jumpstart-reference`, `generate-{set,precon,jumpstart}-checklist`,
`inventory-query`, `export-list`, `foil-diff`, `review-earmarked-products`,
`secret-lair-value`, `edhrec-{commander,card,rankings}`, `mtgjson-search`,
`compose-deck`, `decompose-deck`, `construct-from-loose`, `cleanup/clear-queries`.

### PARTIAL — one scriptable agentic step
A single piece of model glue that is deterministically replaceable. The target
for continued weaning.

| Workflow | Agentic step today | Deterministic replacement |
|---|---|---|
| `add-cards` | parse `"SPG 60 nonfoil"` phrasing | already a CLI spec grammar (`SET CN finish qty`); widget = set/CN/finish/qty fields |
| `bulk-add` | interpret CN ranges + per-range finish | **DONE: `parsers.parse_cn_ranges`** turns `"1858-1872, 7001-7003 foil"` → explicit `(cn, finish)` pairs; widget = range textarea → preview table |
| `import-list` | pick destination (inventory/wishlist/deck); parse pasted block | `parsers.parse_block` already deterministic; widget = paste box + destination radio |
| `inventory-query` / `export-list` | English → selector DSL | selector grammar is already the deterministic contract; widget = selector builder (term dropdown + modifier checkboxes). Optional: `mm query build-selector` emitting the canonical string |
| `add-precon` / `import-precon` | fuzzy precon name → MTGJSON fileName | `mm mtgjson decks --set` is the deterministic resolver; widget = set picker + precon autocomplete |
| `missing-from-set` | resolve "Lord of the Rings" → anchor | `sets.resolve` is deterministic; widget = set autocomplete over the local `sets` table |

### FUNDAMENTALLY AGENTIC — degrade gracefully, keep as optional assist
These need either a model or the user's local environment. The web-app rule:
an **assist endpoint only ever *proposes candidate parameter values*** that flow
into the same deterministic script every other caller uses — it never runs
business logic.

| Workflow | Why it needs more than a form | Web-app strategy |
|---|---|---|
| `earmark-product`, `sealed-value` (tabs) | extract product name + price from arbitrary storefront HTML | server-side headless fetch + per-store heuristic extractor; manual name/price entry as the always-available fallback. `mm resolve-product` stays the deterministic checkpoint. |
| `scryfall-search` | NL → Scryfall query syntax | the deterministic path is a raw-query textbox; an optional LLM assist only *fills* it. |
| `characterize-set` | open-ended audit + taste calls | optional "propose `config/families.toml` edits" assist for human approval; without it the user hand-edits the TOML (now that family rules are declarative config, this is a form, not code). |
| `import-deck` (Moxfield) | Cloudflare-gated, needs a real browser | server-side Playwright pool OR the bookmarklet→paste fallback; Archidekt/MTGGoldfish/ManaBox/Scryfall already fetch deterministically. |
| `scrape-browser-tab-urls`, clipboard | the user's local browser/clipboard | a browser extension or manual URL paste; the `pbcopy` hook → a JS "copy" button (buy-list scripts have zero clipboard coupling — confirmed, see Phase 3 review). |

## What the backend reuses as-is

- **The bash network wrappers** (`scryfall.sh`, `mtgjson.sh`, `manapool.sh`,
  `edhrec.sh`, `tcgcsv.sh`, `tcgapi.sh`, `ebay.sh`) are deterministic
  cache+rate-limit+backoff CLIs a server calls directly. The `PreToolUse` guard
  hooks that force agent traffic through them are **agent-only** and don't move.
- **Config** is now the single tuning seam: `config/*.toml` loaded via
  `magic_manager.config`, repointable with one env var
  (`MAGIC_MANAGER_CONFIG_DIR`) or a `--config` path. A web admin form edits these
  (family rules, promo-type sets, precon types, product priority) with no code
  change. `tests/test_config_schema.py` guards their shape + docs sync.
- **The DB** (`MAGIC_MANAGER_DB`) is already env-redirectable — one store per
  user is a path swap.
- **The shared engines** (`missing`, `ownership`, `exports.xlsx`, `scryfall_urls`,
  `selectors`, `sealed`/`construct`, `family_status`) are importable library
  functions — a web request handler calls them exactly like the CLI does.

## Standing guards that keep it deterministic

- `tests/test_buylist_routing.py` — every buy-list producer routes through the
  shared `physical_buyable` filter (or is a documented exception).
- `tests/test_config_schema.py` — config predicate-key validity + two-way
  config↔docs §8 sync.
- `tests/test_xlsx_writer.py`, `test_scryfall_url.py`, `test_ownership.py`,
  `test_physical_buyable.py`, `test_parse_cn_ranges.py` — pin the shared seams so
  a future caller can't silently reimplement one.

## Remaining weaning work (not yet done)

- `mm inventory add-range` CLI consuming `parsers.parse_cn_ranges` → resolve via
  `scryfall.collection` → `inventory_add`, with a `--preview --json` structured
  output a widget renders (replaces the bulk-add agent loop end-to-end).
- `mm query build-selector` emitting the canonical selector string from discrete
  flags (so a widget never has to know the DSL text form).
- The service layer itself (HTTP handlers over the library functions) + the
  assist endpoints above.
