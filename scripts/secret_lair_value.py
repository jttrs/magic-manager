"""Deterministic markdown table of the most recent N Secret Lair drops.

A "drop" is the MTGJSON DeckList notion of one Secret Lair Drop product,
merged across its base printing and any ``... Foil Edition`` sibling (MTGJSON
lists foil-edition-only Secret Lairs as separate deck entries; we treat them
as the same logical drop). Drops are sorted newest-first by release date
(name ascending as the tie-break) and rendered with live Scryfall singles
prices, nonfoil and foil in separate columns plus a combined "buy everything"
figure.

Every price is fetched live via Scryfall's ``/cards/collection`` batch
endpoint through the project's rate-limited wrapper. Prices are cached
inside the wrapper (24h TTL) so re-runs the same day are instant. Deck
metadata comes from the MTGJSON wrapper (also cached).

Input:
  - positional ``limit`` (default 10) or ``--limit N`` — how many of the most
    recent drops to render. ``--limit`` wins if both are given.

Output:
  - stdout: a markdown title line, a legend line, then a table with columns
    Drop (hyperlinked to a Scryfall search for that drop's exact collector
    numbers), Release, Cards, Nonfoil $, Foil $, NF floor $, Foil floor $.
    The two "floor" columns sum, per card, the CHEAPEST printing of that same
    card anywhere on Scryfall (matched by oracle id) — i.e. the cheapest way
    to assemble the drop's cards for a deck, regardless of the Secret Lair
    treatment. The plain Nonfoil/Foil columns value the Secret Lair printings
    themselves.
  - stderr: a one-line summary of how many drops were rendered out of the
    total known SLD drops, how many distinct printings were fetched, and how
    many distinct cards were priced for the floor lookup.

Exit codes:
  0 — ran to completion.
  2 — bad invocation, or MTGJSON/Scryfall lookup failure.

Determinism notes:
  - Drops sort by release date descending, name ascending tie-break.
  - Drop identity = base + Foil-Edition merged by stripping the
    " Foil Edition" suffix from the entry name; a base entry's name/date win
    as canonical regardless of encounter order.
  - Scryfall IDs are the de-duplicated union across a drop's sibling decks,
    preserving first-seen order.
  - Floor prices are the min over every printing (``oracleid:<id>
    unique=prints``) of that card's ``usd`` / ``usd_foil``; the per-oracle
    lookup is de-duplicated across all drops and 24h-cached at the wrapper.
  - Search URLs are built from ``set:sld (cn:... or ...)`` with collector
    numbers sorted via ``util.cn_sort_key`` and any trailing "★" stripped.

Usage:
    uv run python scripts/secret_lair_value.py
    uv run python scripts/secret_lair_value.py 5
    uv run python scripts/secret_lair_value.py --limit 20
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from urllib.parse import quote_plus

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import mtgjson, scryfall, util  # noqa: E402


def _price(card: dict, key: str) -> float | None:
    """Extract a nested Scryfall price. ``card["prices"][key]`` returns a
    string or None; we coerce to float or None."""
    prices = card.get("prices") or {}
    v = prices.get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _card_floors(oracle_id: str) -> tuple[float | None, float | None]:
    """Cheapest ``(usd, usd_foil)`` across every printing of a card.

    Enumerates all printings via ``oracleid:<id> unique=prints`` and returns
    the min non-null price in each finish (None if no printing has that
    finish priced). This is the "cheapest to buy for a deck" figure — it
    ignores which set the cheapest copy lives in.
    """
    nf: list[float] = []
    ff: list[float] = []
    for p in scryfall.search(f"oracleid:{oracle_id}", unique="prints"):
        v = _price(p, "usd")
        if v is not None:
            nf.append(v)
        v = _price(p, "usd_foil")
        if v is not None:
            ff.append(v)
    return (min(nf) if nf else None), (min(ff) if ff else None)


def _strip_foil_edition(name: str) -> str:
    suffix = " Foil Edition"
    if name.endswith(suffix):
        return name[: -len(suffix)]
    return name


def _group_drops(entries: list[dict]) -> dict[str, dict]:
    """Merge base + Foil-Edition siblings into one logical drop per key.

    Key is the stripped name. A later BASE entry (no " Foil Edition" suffix)
    always wins as canonical for display name + release date, regardless of
    whether a foil-edition placeholder was seen first.
    """
    groups: dict[str, dict] = {}
    for e in entries:
        raw_name = e.get("name") or ""
        key = _strip_foil_edition(raw_name)
        is_base = raw_name == key
        if key not in groups:
            groups[key] = {
                "name": raw_name,
                "release_date": e.get("releaseDate"),
                "file_names": [e.get("fileName")],
            }
            continue
        groups[key]["file_names"].append(e.get("fileName"))
        if is_base:
            groups[key]["name"] = raw_name
            groups[key]["release_date"] = e.get("releaseDate")
    return groups


def _collect_drop_ids(file_names: list[str]) -> list[str]:
    """De-duplicated union of Scryfall IDs across a drop's sibling decks,
    preserving first-seen order."""
    seen: set[str] = set()
    out: list[str] = []
    for fn in file_names:
        deck = mtgjson.deck(fn)
        for sid in mtgjson.deck_card_scryfall_ids(deck):
            if sid in seen:
                continue
            seen.add(sid)
            out.append(sid)
    return out


def _search_url(collector_numbers: list[str]) -> str:
    cns = sorted(
        {cn.strip().rstrip("★").strip() for cn in collector_numbers},
        key=util.cn_sort_key,
    )
    if not cns:
        return "https://scryfall.com/search?q=" + quote_plus("set:sld")
    terms = "set:sld (" + " or ".join(f"cn:{cn}" for cn in cns) + ")"
    return "https://scryfall.com/search?q=" + quote_plus(terms)


def _cell(total: float, priced_ct: int, card_ct: int) -> str:
    if priced_ct == 0:
        return "—"
    s = util.fmt_usd(total)
    return s if priced_ct == card_ct else f"{s} ({priced_ct})"


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Deterministic value table for the most recent N Secret Lair drops.",
    )
    ap.add_argument(
        "limit", nargs="?", type=int, default=10,
        help="Number of most recent drops to render (default 10).",
    )
    ap.add_argument(
        "--limit", type=int, default=None, dest="limit_opt",
        help="Same as the positional argument; wins if both are given.",
    )
    args = ap.parse_args()

    n = args.limit_opt if args.limit_opt is not None else args.limit
    if n <= 0:
        print("error: limit must be a positive integer", file=sys.stderr)
        return 2

    try:
        entries = [
            e for e in mtgjson.deck_list(set_code="SLD")
            if e.get("type") == "Secret Lair Drop"
        ]
    except mtgjson.MtgJsonError as e:
        print(f"error: mtgjson lookup failed: {e}", file=sys.stderr)
        return 2

    groups = _group_drops(entries)
    total = len(groups)

    chosen = sorted(groups.values(), key=lambda g: g["name"])
    chosen.sort(key=lambda g: g["release_date"], reverse=True)
    chosen = chosen[:n]

    all_ids: list[str] = []
    seen_ids: set[str] = set()
    for g in chosen:
        try:
            ids = _collect_drop_ids(g["file_names"])
        except mtgjson.MtgJsonError as e:
            print(f"error: mtgjson lookup failed: {e}", file=sys.stderr)
            return 2
        g["ids"] = ids
        for sid in ids:
            if sid in seen_ids:
                continue
            seen_ids.add(sid)
            all_ids.append(sid)

    try:
        found, not_found = scryfall.collection([{"id": i} for i in all_ids])
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    card_by_id = {c["id"]: c for c in found}

    # Floor prices: cheapest printing of each card anywhere on Scryfall,
    # keyed + de-duplicated by oracle id (cards recur across drops), 24h-cached.
    floors: dict[str, tuple[float | None, float | None]] = {}
    try:
        for card in found:
            oid = card.get("oracle_id")
            if oid and oid not in floors:
                floors[oid] = _card_floors(oid)
    except scryfall.ScryfallError as e:
        print(f"error: scryfall floor lookup failed: {e}", file=sys.stderr)
        return 2

    print(
        f"Rendered {len(chosen)} drops (of {total} SLD drops). "
        f"Fetched {len(all_ids)} distinct printings; {len(not_found)} unresolved. "
        f"Floor-priced {len(floors)} distinct cards.",
        file=sys.stderr,
    )

    print(f"## Secret Lair Drop value — top {n} by release (newest first)")
    print()
    print(
        "*Nonfoil $ / Foil $ sum live Scryfall singles for the drop's own "
        "Secret Lair printings. NF floor $ / Foil floor $ sum, per card, the "
        "CHEAPEST printing of that same card anywhere on Scryfall — the "
        "cheapest way to get these cards into a deck regardless of treatment. "
        "`$X (n)` = only n of the drop's cards are priced in that finish.*"
    )
    print()
    print("| Drop | Release | Cards | Nonfoil $ | Foil $ | NF floor $ | Foil floor $ |")
    print("|---|---|---:|---:|---:|---:|---:|")
    for g in chosen:
        card_count = len(g["ids"])
        nf_total = 0.0
        nf_ct = 0
        foil_total = 0.0
        foil_ct = 0
        nf_floor_total = 0.0
        nf_floor_ct = 0
        foil_floor_total = 0.0
        foil_floor_ct = 0
        cns: list[str] = []
        for sid in g["ids"]:
            card = card_by_id.get(sid)
            if card is None:
                continue
            cns.append(card.get("collector_number") or "")
            nf = _price(card, "usd")
            if nf is not None:
                nf_total += nf
                nf_ct += 1
            ff = _price(card, "usd_foil")
            if ff is not None:
                foil_total += ff
                foil_ct += 1
            nf_floor, foil_floor = floors.get(card.get("oracle_id"), (None, None))
            if nf_floor is not None:
                nf_floor_total += nf_floor
                nf_floor_ct += 1
            if foil_floor is not None:
                foil_floor_total += foil_floor
                foil_floor_ct += 1
        safe = g["name"].replace("|", "\\|")
        url = _search_url(cns)
        print(
            f"| [{safe}]({url}) | {g['release_date']} | {card_count} | "
            f"{_cell(nf_total, nf_ct, card_count)} | "
            f"{_cell(foil_total, foil_ct, card_count)} | "
            f"{_cell(nf_floor_total, nf_floor_ct, card_count)} | "
            f"{_cell(foil_floor_total, foil_floor_ct, card_count)} |"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
