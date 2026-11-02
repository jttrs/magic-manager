"""Nightly canary for the vendor recipe book: read every server-read store's
sample product live and fail when a recipe no longer finds a price/title.

    uv run python scripts/vendor_canary.py [--markdown]

Each recipe ends in one of three outcomes (from ``scrape_canary.check_store``):

* ok          -- the recipe read a price/title.
* fail        -- the store changed its page: update the recipe in
                 config/vendors.toml + re-capture its fixture. Fails CI.
* unverified  -- the check couldn't run from here (the store blocks GitHub's
                 datacenter IPs, or is unreachable). NOT a failure: the daily
                 scrape canary on the owner's machine (scripts/check_scrapers.py
                 --live) reads from the owner's network and covers it. The one
                 exception is ``scrape.sample_gone`` (the sample product was
                 removed -- pick a new sample_url), which is actionable and fails.

Exit 0 when no row fails; 1 otherwise (the CI workflow then opens or updates an
issue, and closes it again once green). Open-tab (`rendered`) stores can't run
here -- they need your browser -- so they're listed as skipped.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from magic_manager import scrape_canary, vendors  # noqa: E402


def fails_ci(outcome: str, code: str | None) -> bool:
    """A failed recipe, or a removed sample product (actionable: new sample_url)."""
    return outcome == "fail" or code == "scrape.sample_gone"


def run() -> tuple[list[tuple], list[str]]:
    """Thin driver over ``scrape_canary.check_store`` (the one store check the
    scheduled scraper-health run also uses). Rows are
    ``(vendor, outcome, code, price, available, note)``."""
    rows, skipped = [], []
    for v in vendors.catalog():
        if v.mode == "rendered" or not v.sample_url:
            skipped.append(v.name)
            continue
        c = scrape_canary.check_store(v)
        d = c.detail
        note = "" if c.outcome == "ok" else (c.message or c.code or "")
        rows.append((v, c.outcome, c.code, d.get("price"), d.get("available"), note))
    return rows, skipped


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--markdown", action="store_true")
    args = ap.parse_args()
    rows, skipped = run()
    failed = [r for r in rows if fails_ci(r[1], r[2])]
    ok = [r for r in rows if r[1] == "ok"]
    unchecked = [r for r in rows if r[1] != "ok" and not fails_ci(r[1], r[2])]
    if args.markdown:
        print("| Store | Mode | Result | Price | In stock | Note |\n|---|---|---|--:|---|---|")
        for v, outcome, code, price, avail, note in rows:
            if outcome == "ok":
                mark = "✅"
            elif fails_ci(outcome, code):
                mark = "❌"
            else:
                mark = "⚠️"
                note = (f"Couldn't check from CI: {note} — the daily check on the "
                        "owner's machine covers it.")
            print(f"| {v.name} | {v.mode} | {mark} | {'' if price is None else f'${price:,.2f}'} | "
                  f"{'' if avail is None else ('yes' if avail else 'no')} | {note} |")
        print(f"\nSkipped (read from your open tab, not CI): {', '.join(skipped) or '—'}")
    else:
        for v, outcome, code, price, avail, note in rows:
            word = "ok  " if outcome == "ok" else ("FAIL" if fails_ci(outcome, code) else "skip")
            print(f"{word} {v.key:16} {v.mode:8} {price!s:>10} {avail!s:>6} {note}")
    print(f"\n{len(ok)} of {len(rows)} recipes read; {len(unchecked)} couldn't be checked "
          f"from CI; {len(failed)} failed", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
