---
name: import-deck
description: "Read a deck from Moxfield, Archidekt, MTGGoldfish, ManaBox, or Scryfall into the local DB (creating/appending a deck), or push a local deck back to Moxfield. Archidekt/MTGGoldfish/ManaBox/Scryfall fetch directly; Moxfield uses a Playwright browser session (Cloudflare-gated) with a clipboard-bookmarklet + UI-export fallback. Re-pulling a deck already imported from a source is refused unless --force (which replaces its cards). Triggers: \"import my moxfield/archidekt/mtggoldfish/manabox/scryfall deck\", \"pull this deck <url>\", \"add this decklist from <url>\", \"load <deck url> into a deck\", \"push <deck> to moxfield\", \"sync <deck> to moxfield\"."
---

# import-deck

Bridges external deck builders and the local `decks`/`deck_cards` tables. It is a
**thin relay** over deterministic scripts + CLI (per repo rule 1): the network fetch
lives in `scripts/import_deck.py`, the resolve+write lives in
`src/magic_manager/decksource.py` behind `mm deck import-deck`, and this skill only
wires the pipeline and relays output.

## Read a deck (Moxfield / Archidekt / MTGGoldfish / ManaBox / Scryfall → DB)

One pipeline for all five. `import_deck.py` detects the source from the URL and
fetches; the CLI resolves cards against Scryfall and writes them:

```
uv run python scripts/import_deck.py <deck-url> \
  | uv run mm deck import-deck --slug <deck-slug> [--name "Deck Name"] [--force] [--add-to-collection] -
```

**Defaults:** an import saves the **decklist (recipe) only** and is **never marked built**.
Ask whether the user has the cards in hand: if yes, add `--add-to-collection` (one copy
of the playable cards → inventory, one `deck` ingest event). Building (pledging those
cards to the deck) stays a separate, explicit `mm deck compose <slug>`.

- **Archidekt** (`archidekt.com/decks/<id>`) — open JSON API, plain fetch. Carries
  categories (Commander/Sideboard/Maybeboard → boards; others → main).
- **MTGGoldfish** (`mtggoldfish.com/deck/<id>`) — per-deck text download, plain fetch.
- **ManaBox** (`manabox.app/decks/<id>`) — plain fetch, no browser. The SSR page
  embeds a full card payload (set code + collector number + foil/etched variant +
  board), so it imports at full printing fidelity like Archidekt. No auth needed
  for a public deck; carries no author.
- **Scryfall** (`scryfall.com/@<user>/decks/<uuid>`) — public deck export
  (`/decks/<id>/export/json`) via the rate-limited Scryfall wrapper, no browser.
  Full printing fidelity (scryfall_id + set + CN + foil). Sections map
  commanders→commander, nonlands/lands→main, maybeboard→maybe; the "outside"
  (considering) bucket is skipped. Carries no author.
- **Moxfield** (`moxfield.com/decks/<id>`) — Cloudflare-gated; `import_deck.py` drives
  a real (headed) Chrome via Playwright and intercepts the deck page's own api2 call
  (clears Cloudflare with no interaction). A browser window flashes briefly — that's
  expected. **PUBLIC decks need no login at all.** For a PRIVATE deck the script
  escalates to a login cascade: persisted session (`.deck-sessions/`, gitignored) →
  `MOXFIELD_EMAIL`/`MOXFIELD_PASSWORD` auto-login → a visible window for manual login
  (needs an interactive terminal). `--fresh` forces re-login.

The importer is **additive** (create-or-append, summing counts) and maps all boards
(main/side/commander/companion/maybe/token). Relay the `added/updated`, any
`warning:` lines, and any `not found:` lines verbatim.

**Re-pull dedup.** URL fetches carry the deck's `source` + `id`, so a deck already
imported from that upstream is **refused** (exit 3) rather than double-counted —
re-run with `--force` to REPLACE its cards with the fresh pull (a refreshed list is
synced cleanly, not summed). `--force` targets the originally-imported deck
regardless of the `--slug` you pass. Hand-fed `--file` imports (no source id) are
unaffected and still create-or-append.

### Moxfield fallbacks (if the browser path breaks)

1. **Bookmarklet (no CLI browser).** Install `moxfield-bookmarklet.min.txt` as a
   bookmark, click it on the deck page (it copies normalized JSON to the clipboard),
   then:
   ```
   pbpaste | uv run python scripts/import_deck.py --file - \
     | uv run mm deck import-deck --slug <deck-slug> -
   ```
2. **UI export (always works, any source).** Use the site's own Export/Download to
   get the `<qty> Name (SET) CN` text block and paste it into the pre-existing text
   importer: `uv run mm deck import <slug> -` (create the deck first with
   `mm deck create`).

## Push a local deck (DB → Moxfield) — best-effort

Moxfield has **no write API**, so this drives the deck-builder UI with Playwright.
Treat it as best-effort — confirm the result on Moxfield.

```
uv run mm deck push-moxfield <slug> [--name "Deck Name"]
```

This renders the deck via the existing exporter and hands it to
`scripts/moxfield_push.py`, which pastes it into Moxfield's bulk-import box and saves.
v1 creates a NEW deck (no update-in-place). Relay the printed deck URL.

## Setup

- `uv sync` then `uv run playwright install chromium` (one-time; the Chromium binary
  isn't pulled by `uv sync`). Only the Moxfield paths need it.
- Optional `.env`: `MOXFIELD_EMAIL`, `MOXFIELD_PASSWORD` (memory-only, never logged).

## Files

- `scripts/import_deck.py` — source-dispatching fetch → normalized-cards JSON (stdout).
- `scripts/moxfield_session.py` — shared Playwright auth cascade (persist→auto→headed).
- `scripts/moxfield_push.py` — best-effort deck-builder UI automation (push).
- `src/magic_manager/decksource.py` — offline parsers + shared resolve/write core.
- `moxfield-bookmarklet.js` / `.min.txt` — the Moxfield clipboard fallback.
