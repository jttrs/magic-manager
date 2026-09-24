"""Fetch a deck from Moxfield / Archidekt / MTGGoldfish and emit normalized cards.

This is the NETWORK front door for deck import. It owns all external fetching (per
the repo's sanctioned-wrapper rule: the CLI does no network except rate-limited
Scryfall). It emits a normalized-cards JSON object to stdout; feed that to the CLI:

    uv run python scripts/import_deck.py <deck-url> \\
        | uv run mm deck import-deck --slug my-deck -

Per-source strategy (see the module-level design doc in decksource.py):
  - ARCHIDEKT   — plain GET archidekt.com/api/decks/{id}/  (open JSON API)
  - MTGGOLDFISH — plain GET mtggoldfish.com/deck/download/{id}  (text block)
  - MOXFIELD    — Playwright authed context → api2.moxfield.com/v3/decks/all/{id}
                  (Cloudflare-gated; needs a real browser). Session cascade lives
                  in moxfield_session.py: persisted → auto-login → headed manual.

Fallbacks that need no browser (always available if the above breaks):
  --file -/PATH  — pass through JSON the Moxfield BOOKMARKLET copied to clipboard.
  For any source, the site's own UI Export/Download block pastes straight into
  `mm deck import <slug> -` (the pre-existing text importer).

Output shape (stdout):
    {"source": "<src>", "id": "<deck-id>", "name": "<deck name|null>",
     "cards": [ <normalized-card dict>, ... ]}
The which-path-ran diagnostics go to stderr. Nothing here writes the DB.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import decksource  # noqa: E402

UA = "ClaudeCode-magic-manager-DeckImport/1.0 (personal collection tool; respects rate-limits)"


def _http_get(url: str, *, accept: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": accept})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


# ---------- Archidekt: open JSON API ----------

def fetch_archidekt(deck_id: str) -> tuple[list[dict], str | None]:
    url = f"https://archidekt.com/api/decks/{deck_id}/"
    data = json.loads(_http_get(url, accept="application/json"))
    return decksource.parse_archidekt(data), data.get("name")


# ---------- MTGGoldfish: per-deck text download ----------

def fetch_mtggoldfish(deck_id: str) -> tuple[list[dict], str | None]:
    url = f"https://www.mtggoldfish.com/deck/download/{deck_id}"
    text = _http_get(url, accept="text/plain")
    return decksource.parse_mtggoldfish(text), None


# ---------- Moxfield: Playwright authed context ----------

def fetch_moxfield(deck_id: str, *, fresh: bool) -> tuple[list[dict], str | None]:
    from moxfield_session import MoxfieldSession

    api = f"https://api2.moxfield.com/v3/decks/all/{deck_id}"
    with MoxfieldSession(fresh=fresh) as ctx:
        resp = ctx.request.get(api, headers={"Accept": "application/json"})
        if resp.status == 403:
            raise RuntimeError(
                "Moxfield returned 403 even through the browser context — Cloudflare "
                "likely changed its challenge. Use the bookmarklet fallback: click it "
                "on the deck page, then `pbpaste | uv run python scripts/import_deck.py "
                "--file -`."
            )
        if resp.status >= 400:
            raise RuntimeError(f"Moxfield api2 returned HTTP {resp.status}")
        data = resp.json()
    return decksource.parse_moxfield(data), data.get("name")


# ---------- --file passthrough (bookmarklet / manual JSON) ----------

def fetch_from_file(path: str) -> tuple[list[dict], str | None]:
    raw = sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")
    payload = json.loads(raw)
    if isinstance(payload, dict):
        cards = payload.get("cards") or []
        return cards, payload.get("name")
    return payload, None


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch a deck from Moxfield/Archidekt/MTGGoldfish.")
    ap.add_argument("url", nargs="?", help="Deck URL (moxfield/archidekt/mtggoldfish).")
    ap.add_argument("--file", help="Read normalized-cards JSON from a file, or '-' for stdin (bookmarklet path).")
    ap.add_argument("--fresh", action="store_true", help="Moxfield: force re-login (ignore persisted session).")
    args = ap.parse_args()

    if args.file is not None:
        cards, name = fetch_from_file(args.file)
        source, deck_id = "file", None
    elif args.url:
        source = decksource.source_of(args.url)
        deck_id = decksource.deck_id_from_url(args.url)
        print(f"import_deck: source={source} id={deck_id}", file=sys.stderr)
        try:
            if source == "archidekt":
                cards, name = fetch_archidekt(deck_id)
            elif source == "mtggoldfish":
                cards, name = fetch_mtggoldfish(deck_id)
            else:
                cards, name = fetch_moxfield(deck_id, fresh=args.fresh)
        except (urllib.error.HTTPError, urllib.error.URLError) as e:
            print(f"import_deck: fetch failed: {e}", file=sys.stderr)
            return 1
        except RuntimeError as e:
            print(f"import_deck: {e}", file=sys.stderr)
            return 1
    else:
        ap.error("provide a deck URL or --file")
        return 2

    if not cards:
        print("import_deck: no cards parsed (empty deck, or the payload shape changed)", file=sys.stderr)
        return 1

    print(f"import_deck: parsed {len(cards)} card rows", file=sys.stderr)
    json.dump({"source": source, "id": deck_id, "name": name, "cards": cards},
              sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
