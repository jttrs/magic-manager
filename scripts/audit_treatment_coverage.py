"""Doc-coverage backstop: does every characterized family's doc NAME the
alt-treatment classes that actually exist in its print data?

The CLB/AFR miss (2026-09-30) happened because a promo_types-only audit
flattened showcase / extendedart / etched structure — which lives in
``frame_effects`` / ``finishes`` — into one ``boosterfun`` bucket, so the doc
silently omitted it. This script is the mechanical backstop that turns a
*silent* miss into a *loud* GAP:

For every ``docs/sets/<anchor>.md``:
  1. Resolve the family, pull every print from the local ``cards`` table.
  2. Compute which alt-treatment classes are PRESENT (showcase, extendedart,
     etched, borderless) from frame_effects / finishes / border_color — the
     same signals ``treatments.compute_treatment`` keys on.
  3. Check whether the doc's prose NAMES each present class (a keyword grep).
  4. Print one PASS / GAP line per family, and a summary.

A GAP is a REVIEW PROMPT, not a hard error — it means "this family has a
treatment class the doc doesn't discuss; re-run the enhanced survey and decide
keep/exclude." It is deliberately heuristic (keyword presence), erring toward
flagging rather than silence.

This is ALSO the engine the Part-B family sweep rides on: run with no args to
scan every characterized family; pass anchor codes to scan a subset.

Usage:
    uv run python scripts/audit_treatment_coverage.py            # all docs
    uv run python scripts/audit_treatment_coverage.py vow c21    # subset
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import sets as sets_mod  # noqa: E402

DB_PATH = ROOT / "db" / "magic_manager.db"
DOCS_DIR = ROOT / "docs" / "sets"

# Alt-treatment classes we care about, mapped to:
#   detect:  predicate over a card row's parsed (frame_effects, finishes, border)
#   keywords: strings whose presence in the doc counts as "named"
#   severity: HIGH = KEPT by the preferred filter AND easy to overlook, so an
#             un-named one is the CLB/AFR failure mode. LOW = auto-dropped by
#             the pipeline (ext class / ff-dupe collapse) or already covered by
#             an adjacent class, so an un-named one is a doc-completeness nit.
#
# CRITICAL distinction learned from the CLB/AFR miss AND the first sweep's
# false positives (2026-09-30): a BLACK-bordered showcase (CLB/AFR D&D rulebook
# frame) is a SEPARATE frame that coexists with a distinct borderless treatment
# and is the thing that got missed — HIGH severity. A BORDERLESS showcase
# (TLA/SPM modern combined frame) is just the family's borderless treatment,
# which the doc already discusses under "borderless" — LOW severity. Splitting
# them stops the backstop from crying wolf on every modern-borderless family
# while still catching the real CLB/AFR pattern.
CLASSES = {
    "showcase-black": {
        "detect": lambda fe, fin, bc: "showcase" in fe and bc != "borderless",
        "keywords": ("showcase",),
        "severity": "HIGH",  # KEPT by default, the CLB/AFR failure mode
    },
    "showcase-borderless": {
        "detect": lambda fe, fin, bc: "showcase" in fe and bc == "borderless",
        "keywords": ("showcase", "borderless"),
        "severity": "LOW",  # the ordinary modern combined frame; doc covers via "borderless"
    },
    "extendedart": {
        "detect": lambda fe, fin, bc: "extendedart" in fe,
        "keywords": ("extendedart", "extended-art", "extended art", "`ext`", " ext "),
        "severity": "LOW",  # auto-dropped by preferred (ext class)
    },
    "etched": {
        "detect": lambda fe, fin, bc: "etched" in fin or "etched" in fe,
        "keywords": ("etched",),
        "severity": "LOW",  # collapses as ff-dupe
    },
    "borderless": {
        "detect": lambda fe, fin, bc: bc == "borderless",
        "keywords": ("borderless",),
        "severity": "HIGH",  # KEPT by default
    },
}


def _decode(raw):
    if not raw:
        return []
    try:
        return json.loads(raw) if isinstance(raw, str) else list(raw)
    except (ValueError, TypeError):
        return []


def _family_class_counts(con: sqlite3.Connection, anchor: str) -> dict[str, int] | None:
    try:
        resolved = sets_mod.resolve(anchor)
    except LookupError:
        return None
    family = tuple(resolved.all_codes)
    placeholders = ",".join("?" for _ in family)
    rows = con.execute(
        f"SELECT frame_effects, finishes, border_color "
        f"FROM cards WHERE set_code IN ({placeholders})",
        family,
    ).fetchall()
    counts = {k: 0 for k in CLASSES}
    for r in rows:
        fe = {x.lower() for x in _decode(r["frame_effects"])}
        fin = {x.lower() for x in _decode(r["finishes"])}
        bc = (r["border_color"] or "").lower()
        for cls, spec in CLASSES.items():
            if spec["detect"](fe, fin, bc):
                counts[cls] += 1
    return counts


def _doc_names_class(doc_text: str, cls: str) -> bool:
    low = doc_text.lower()
    return any(kw.lower() in low for kw in CLASSES[cls]["keywords"])


def audit(anchors: list[str]) -> int:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row

    if not anchors:
        anchors = sorted(
            p.stem for p in DOCS_DIR.glob("*.md") if p.stem != "_TEMPLATE"
        )

    gaps_total = 0
    high_gaps_total = 0
    print(f"Treatment-coverage audit over {len(anchors)} characterized families")
    print("(GAP = a treatment class present in data but not NAMED in the doc §2)")
    print("=" * 78)
    for anchor in anchors:
        doc_path = DOCS_DIR / f"{anchor}.md"
        if not doc_path.exists():
            print(f"  {anchor.upper():<6} — no doc at {doc_path.name}; skipping")
            continue
        counts = _family_class_counts(con, anchor)
        if counts is None:
            print(f"  {anchor.upper():<6} — family not resolvable / not synced; skipping")
            continue
        doc_text = doc_path.read_text(encoding="utf-8")
        present = {c: n for c, n in counts.items() if n > 0}
        high_gaps, low_gaps = [], []
        for cls, n in present.items():
            if not _doc_names_class(doc_text, cls):
                if CLASSES[cls]["severity"] == "HIGH":
                    high_gaps.append(f"{cls}×{n}")
                else:
                    low_gaps.append(f"{cls}×{n}")
        present_str = ", ".join(f"{c}×{n}" for c, n in present.items()) or "(no alt-treatments)"
        if high_gaps:
            gaps_total += 1
            high_gaps_total += 1
            print(f"  {anchor.upper():<6} ⚠ HIGH present: {present_str}")
            print(f"         └─ un-named KEPT class(es): {', '.join(high_gaps)}"
                  + (f"   (also low: {', '.join(low_gaps)})" if low_gaps else ""))
        elif low_gaps:
            gaps_total += 1
            print(f"  {anchor.upper():<6} gap   present: {present_str}")
            print(f"         └─ un-named auto-dropped class(es): {', '.join(low_gaps)}")
        else:
            print(f"  {anchor.upper():<6} PASS  present: {present_str}")

    print("=" * 78)
    print(f"{high_gaps_total} families with an un-named KEPT-by-default class "
          f"(⚠ HIGH — the CLB/AFR failure mode); {gaps_total} families with any gap.")
    print("A ⚠ HIGH gap is the one that can leave unwanted prints in missing-set.")
    print("Review it: run")
    print("  uv run python scripts/survey_treatment_signature.py <ANCHOR>")
    print("read the PREFERRED PREVIEW, and decide keep vs exclude per class.")
    return gaps_total


def main():
    anchors = [a.lower() for a in sys.argv[1:]]
    audit(anchors)


if __name__ == "__main__":
    main()
