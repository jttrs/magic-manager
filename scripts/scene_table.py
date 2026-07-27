"""Standardized, deterministic scene-completion table for a set family.

A "scene" is a curated group of collector numbers that form one multi-card
artwork/theme (borderless-inverted scene runs, poster panels, date-scene
cycles). Scryfall does not tag scene membership, so the groupings live in
``selectors.FAMILY_SCENES`` (hand-verified, documented in docs/sets/<anchor>.md
§4). This script renders them into a consistent Markdown report:

  - one section per scene, in FAMILY_SCENES order
  - per-scene header: name, artist, CN range, owned/total tally
  - per-card row: CN, name, owned-nonfoil qty, owned-foil qty, live nonfoil $,
    live foil $, %-diff (foil vs nonfoil), $-diff
  - per-scene footer: cost to FINISH the scene in all-nonfoil vs all-foil
    (summing only the CNs not yet owned in that finish)
  - a grand-total footer across all scenes

Prices are fetched live via Scryfall's /cards/collection batch endpoint
through the rate-limited wrapper (24h cache), so the numbers are current and
re-runs the same day are instant. Ownership comes from the local ``inventory``
table joined to ``cards`` by (set_code, collector_number).

Deterministic: scenes render in config order; cards sort by numeric CN within
a scene; prices round to cents; %-diff computed as (foil-nonfoil)/nonfoil.

Usage:
    uv run python scripts/scene_table.py ltr
    uv run python scripts/scene_table.py ltr --owned-only     # hide fully-unowned rows
    uv run python scripts/scene_table.py ltr --missing-only   # only rows you don't own

Exit codes:
    0 — rendered
    2 — bad invocation / anchor has no FAMILY_SCENES entry
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import db, scryfall, selectors  # noqa: E402


def _fmt_usd(v: float | None) -> str:
    return f"${v:.2f}" if v is not None else "—"


def _fmt_pct(nonfoil: float | None, foil: float | None) -> str:
    if not nonfoil or foil is None:
        return "—"
    return f"{(foil - nonfoil) / nonfoil * 100:+.1f}%"


def _fmt_diff(nonfoil: float | None, foil: float | None) -> str:
    if nonfoil is None or foil is None:
        return "—"
    d = foil - nonfoil
    return f"{'+' if d >= 0 else '-'}${abs(d):.2f}"


def _price(prices: dict, key: str) -> float | None:
    v = (prices or {}).get(key)
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def _scryfall_url(set_code: str, cn: str) -> str:
    """Stable printing URL — no query string / utm suffix (matches
    foil_price_diff.py)."""
    return f"https://scryfall.com/card/{set_code.lower()}/{cn}"


def _ownership(set_code: str) -> dict[tuple[str, str], int]:
    """(collector_number, finish) -> owned quantity, for one set code."""
    out: dict[tuple[str, str], int] = {}
    with db.connect() as conn:
        rows = conn.execute(
            """
            SELECT c.collector_number AS cn, inv.finish AS finish, inv.quantity AS qty
            FROM inventory inv JOIN cards c ON c.scryfall_id = inv.scryfall_id
            WHERE c.set_code = ?
            """,
            (set_code.lower(),),
        ).fetchall()
    for r in rows:
        out[(str(r["cn"]), r["finish"])] = r["qty"]
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Scene-completion table for a set family.")
    ap.add_argument("anchor", help="Set-family anchor code (e.g. ltr).")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--owned-only", action="store_true",
                     help="Show only cards you own at least one finish of.")
    grp.add_argument("--missing-only", action="store_true",
                     help="Show only cards you own zero copies of.")
    args = ap.parse_args()

    anchor = args.anchor.lower()
    scenes = selectors.FAMILY_SCENES.get(anchor)
    if not scenes:
        configured = ", ".join(sorted(selectors.FAMILY_SCENES)) or "(none)"
        print(f"error: no FAMILY_SCENES config for anchor {anchor!r}. "
              f"Configured: {configured}. Add an entry in selectors.py "
              f"(and docs/sets/{anchor}.md §4) first.", file=sys.stderr)
        return 2

    # Collect every (set, cn) identifier across all scenes for one batch fetch.
    identifiers: list[dict] = []
    for sc in scenes:
        for cn in range(sc["cn_lo"], sc["cn_hi"] + 1):
            identifiers.append({"set": sc["set"], "collector_number": str(cn)})
    try:
        found, _not_found = scryfall.collection(identifiers)
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2

    # Index cards by (set, cn).
    card_by = {}
    for c in found:
        card_by[(c["set"].lower(), c["collector_number"])] = c

    # Ownership per set code (fetch once per distinct set in the scenes).
    own_by_set = {sc["set"].lower(): _ownership(sc["set"]) for sc in scenes}

    grand = {"cards": 0, "owned": 0, "finish_nf": 0.0, "finish_f": 0.0}
    out: list[str] = []

    for sc in scenes:
        setc = sc["set"].lower()
        own = own_by_set[setc]
        rows = []
        owned_ct = 0
        total_ct = 0
        scene_nf_to_finish = 0.0
        scene_f_to_finish = 0.0
        for cn in range(sc["cn_lo"], sc["cn_hi"] + 1):
            c = card_by.get((setc, str(cn)))
            if c is None:
                continue  # gap in the numeric range (non-scene CN); skip silently
            total_ct += 1
            onf = own.get((str(cn), "nonfoil"), 0)
            off = own.get((str(cn), "foil"), 0)
            if onf or off:
                owned_ct += 1
            nf = _price(c.get("prices"), "usd")
            ff = _price(c.get("prices"), "usd_foil")
            # cost-to-finish: add the price of finishes not yet owned
            if onf == 0 and nf is not None:
                scene_nf_to_finish += nf
            if off == 0 and ff is not None:
                scene_f_to_finish += ff
            if args.owned_only and not (onf or off):
                continue
            if args.missing_only and (onf or off):
                continue
            rows.append((cn, c.get("name") or "", onf, off, nf, ff))

        artist = f" · {sc['artist']}" if sc.get("artist") else ""
        out.append(
            f"### {sc['name']}{artist} "
            f"({setc.upper()} {sc['cn_lo']}–{sc['cn_hi']}) — {owned_ct}/{total_ct} owned"
        )
        out.append("| CN | Card | Own NF | Own Foil | NF $ | Foil $ | % diff | $ diff |")
        out.append("|---:|---|---:|---:|---:|---:|---:|---:|")
        for cn, name, onf, off, nf, ff in rows:
            onf_s = f"**{onf}**" if onf else "0"
            off_s = f"**{off}**" if off else "0"
            safe = (name or "").replace("|", "\\|")
            link = f"[{safe}]({_scryfall_url(setc, str(cn))})"
            out.append(
                f"| {cn} | {link} | {onf_s} | {off_s} | "
                f"{_fmt_usd(nf)} | {_fmt_usd(ff)} | "
                f"{_fmt_pct(nf, ff)} | {_fmt_diff(nf, ff)} |"
            )
        out.append(
            f"\n*Finish this scene: all-nonfoil {_fmt_usd(scene_nf_to_finish)} · "
            f"all-foil {_fmt_usd(scene_f_to_finish)}*\n"
        )

        grand["cards"] += total_ct
        grand["owned"] += owned_ct
        grand["finish_nf"] += scene_nf_to_finish
        grand["finish_f"] += scene_f_to_finish

    print("\n".join(out))
    print(
        f"**Total: {grand['owned']}/{grand['cards']} owned across {len(scenes)} scenes · "
        f"finish all-nonfoil {_fmt_usd(grand['finish_nf'])} · "
        f"all-foil {_fmt_usd(grand['finish_f'])}**"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
