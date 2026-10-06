"""Nightly canary for the vendor recipe book: read every server-read store's
sample product live and fail when a recipe no longer finds a price/title.

    uv run python scripts/vendor_canary.py [--markdown]

Exit 0 when every recipe reads; 1 when any fails (the CI workflow then opens or
updates an issue). Open-tab (`rendered`) stores can't run here — they need your
browser — so they're listed as skipped. A failure means: the store changed its
page (update the recipe in config/vendors.toml + re-capture its fixture), the
sample product was removed (pick a new sample_url), or it now blocks automated
reads (consider `rendered`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from magic_manager import storefetch, vendors  # noqa: E402


def run() -> tuple[list[tuple], list[str]]:
    rows, skipped = [], []
    for v in vendors.catalog():
        if v.mode == "rendered" or not v.sample_url:
            skipped.append(v.name)
            continue
        try:
            _, listing = storefetch.read(v.sample_url, fresh=True)
            ok = listing.price is not None and bool(listing.title)
            note = "" if ok else "no price/title found — the page changed"
            rows.append((v, ok, listing.price, listing.available, note))
        except Exception as e:  # noqa: BLE001 — report every store
            rows.append((v, False, None, None, f"{type(e).__name__}: {e}"))
    return rows, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    rows, skipped = run()
    failed = [r for r in rows if not r[1]]
    if args.markdown:
        print("| Store | Mode | Result | Price | In stock | Note |\n|---|---|---|--:|---|---|")
        for v, ok, price, avail, note in rows:
            print(f"| {v.name} | {v.mode} | {'✅' if ok else '❌'} | {'' if price is None else f'${price:,.2f}'} | "
                  f"{'' if avail is None else ('yes' if avail else 'no')} | {note} |")
        print(f"\nSkipped (read from your open tab, not CI): {', '.join(skipped) or '—'}")
    else:
        for v, ok, price, avail, note in rows:
            print(f"{'ok  ' if ok else 'FAIL'} {v.key:16} {v.mode:8} {price!s:>10} {avail!s:>6} {note}")
    print(f"\n{len(rows) - len(failed)} of {len(rows)} recipes read", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
