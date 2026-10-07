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

The engine is ``magic_manager.scenes`` (the same scene progress the web
Collection's Scene group shows, over ``collection_view.family_cards``); this
script only renders it. Prices are fetched live from Scryfall's
/cards/collection batch endpoint through the rate-limited wrapper (24h cache);
``--local`` uses the local ``cards`` prices instead (no network).

Deterministic: scenes render in config order; cards sort by numeric CN within
a scene; prices round to cents; %-diff computed as (foil-nonfoil)/nonfoil.

Usage:
    uv run python scripts/scene_table.py ltr
    uv run python scripts/scene_table.py ltr --owned-only     # hide fully-unowned rows
    uv run python scripts/scene_table.py ltr --missing-only   # only rows you don't own
    uv run python scripts/scene_table.py ltr --local          # local prices, no network

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

from magic_manager import scenes as scenes_mod, scryfall, selectors  # noqa: E402


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


def _scryfall_url(set_code: str, cn: str) -> str:
    """Stable printing URL — no query string / utm suffix (matches
    foil_price_diff.py)."""
    return f"https://scryfall.com/card/{set_code.lower()}/{cn}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Scene-completion table for a set family.")
    ap.add_argument("anchor", help="Set-family anchor code (e.g. ltr).")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--owned-only", action="store_true",
                     help="Show only cards you own at least one finish of.")
    grp.add_argument("--missing-only", action="store_true",
                     help="Show only cards you own zero copies of.")
    ap.add_argument("--local", action="store_true",
                    help="Use local cards-table prices instead of a live Scryfall fetch.")
    args = ap.parse_args()

    anchor = args.anchor.lower()
    if not scenes_mod.configured(anchor):
        configured = ", ".join(sorted(selectors.FAMILY_SCENES)) or "(none)"
        print(f"error: no FAMILY_SCENES config for anchor {anchor!r}. "
              f"Configured: {configured}. Add a [[scenes.{anchor}]] entry in "
              f"config/families.toml (and docs/sets/{anchor}.md §4) first.", file=sys.stderr)
        return 2
    try:
        fc, scenes = scenes_mod.family_scenes(anchor)
        live = None if args.local else scenes_mod.live_prices([sid for s in scenes for sid in s.card_ids])
    except LookupError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except scryfall.ScryfallError as e:
        print(f"error: scryfall lookup failed: {e}", file=sys.stderr)
        return 2
    if live is not None:
        scenes = scenes_mod.progress(fc, live)
    by_id = {c.scryfall_id: c for c in fc.cards}

    grand = {"cards": 0, "owned": 0, "finish_nf": 0.0, "finish_f": 0.0}
    out: list[str] = []
    for s in scenes:
        out.append(
            f"### {s.name}{f' · {s.artist}' if s.artist else ''} "
            f"({s.set_code.upper()} {s.cn_lo}–{s.cn_hi}) — {s.owned_printings}/{s.printings} owned"
        )
        out.append("| CN | Card | Own NF | Own Foil | NF $ | Foil $ | % diff | $ diff |")
        out.append("|---:|---|---:|---:|---:|---:|---:|---:|")
        for sid in s.card_ids:
            c = by_id[sid]
            onf, off = c.owned.get("nonfoil", 0), c.owned.get("foil", 0)
            if args.owned_only and not (onf or off):
                continue
            if args.missing_only and (onf or off):
                continue
            nf, ff = (live or {}).get(sid, (c.price_usd, c.price_usd_foil))
            safe = (c.name or "").replace("|", "\\|")
            out.append(
                f"| {c.collector_number} | [{safe}]({_scryfall_url(c.set_code, c.collector_number)}) | "
                f"{f'**{onf}**' if onf else '0'} | {f'**{off}**' if off else '0'} | "
                f"{_fmt_usd(nf)} | {_fmt_usd(ff)} | {_fmt_pct(nf, ff)} | {_fmt_diff(nf, ff)} |"
            )
        nf_left, f_left = s.finishes["nonfoil"].missing_usd, s.finishes["foil"].missing_usd
        out.append(f"\n*Finish this scene: all-nonfoil {_fmt_usd(nf_left)} · all-foil {_fmt_usd(f_left)}*\n")
        grand["cards"] += s.printings
        grand["owned"] += s.owned_printings
        grand["finish_nf"] += nf_left
        grand["finish_f"] += f_left

    print("\n".join(out))
    print(
        f"**Total: {grand['owned']}/{grand['cards']} owned across {len(scenes)} scenes · "
        f"finish all-nonfoil {_fmt_usd(grand['finish_nf'])} · "
        f"all-foil {_fmt_usd(grand['finish_f'])}**"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
