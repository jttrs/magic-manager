"""Missing-set printing union — the reusable core of `mm query missing-set`.

`missing_printings(code)` returns the printing-level union of the four
missing-set sub-selectors for a family (rare-regular, mythic-regular,
uncommon-chase, and the treatment-class alt sub-selector). Both the CLI command
(`cli.query_missing_set_cmd`) and the standalone cart-check tool
(`scripts/manapool_cart_check.py`) call this so the "what am I missing from the
family?" logic lives in exactly one place.

The two post-filter helpers (`_apply_preferred_post_filter`,
`_drop_meld_back_faces`) live here because missing-set is their only caller.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from . import db, sets as sets_mod, selectors as sel_mod


def sub_selectors(code: str, treatment_class: str = "preferred") -> list[tuple[str, str]]:
    """The (slug, selector-string) pairs unioned by `missing_printings`.

    Exposed so callers (e.g. the CLI command's XLSX `_meta` selector cell) can
    describe the union without re-deriving the strings.
    """
    code_l = code.lower()
    return [
        ("rare-regular",     f"set:{code_l}+related missing rarity=rare treatment=regular"),
        ("mythic-regular",   f"set:{code_l}+related missing rarity=mythic treatment=regular"),
        # Uncommons only surface if they're a chase-variant sheet — same
        # (name, treatment) appears ≥3 times in the family (LTR Nazgûl x9,
        # FIN Cid x16). Ordinary uncommons are omitted since a completionist
        # doesn't chase every uncommon reprint. See selectors._modifier_chase.
        ("uncommon-chase",   f"set:{code_l}+related missing rarity=uncommon treatment=regular chase"),
        (treatment_class,    f"set:{code_l}+related missing treatment={treatment_class}"),
    ]


def missing_printings(
    code: str,
    treatment_class: str = "preferred",
) -> list[sel_mod.MaterializedRow]:
    """Printing-level union of the four missing-set sub-selectors for a family.

    Materializes each sub-selector, applies the preferred post-filter (when
    ``treatment_class == "preferred"``) to the three regular sub-selectors,
    drops meld-back faces from all, then unions by ``scryfall_id`` (last write
    wins — printing-level dedup). Returns rows in the materializer's native
    order; callers apply their own sort.

    Propagates ``selectors.SelectorParseError`` / ``LookupError`` to the caller.
    """
    code_l = code.lower()
    SUBS = sub_selectors(code_l, treatment_class)

    # 1. Materialize each sub-selector.
    sub_rows: dict[str, list[sel_mod.MaterializedRow]] = {}
    for slug_key, sel in SUBS:
        sub_rows[slug_key] = sel_mod.materialize(sel)

    # 1a. When using 'preferred' mode, also drop datestamped-with-sibling rows
    # from the rare/mythic regular sub-selectors. The 'preferred' filter only
    # runs on the alt sub-selector (treatment=preferred); regular-treatment
    # rows skip the filter unless we apply it here.
    if treatment_class == "preferred":
        sub_rows["rare-regular"]   = _apply_preferred_post_filter(sub_rows["rare-regular"], code_l)
        sub_rows["mythic-regular"] = _apply_preferred_post_filter(sub_rows["mythic-regular"], code_l)
        sub_rows["uncommon-chase"] = _apply_preferred_post_filter(sub_rows["uncommon-chase"], code_l)

    # 1b. Drop meld-back faces. Identified by: every printing of this card
    # name in the family has a 'b' suffix on its collector number. Meld
    # backs aren't sold as products on TCGplayer or ManaPool — they're the
    # back face of a meld pair, only obtainable as part of the front-face
    # printing.
    for slug_key in list(sub_rows.keys()):
        sub_rows[slug_key] = _drop_meld_back_faces(sub_rows[slug_key], code_l)

    # 2. Union by scryfall_id (printing-level dedup).
    union: dict[str, sel_mod.MaterializedRow] = {}
    for slug_key in sub_rows:
        for r in sub_rows[slug_key]:
            union[r.scryfall_id] = r
    return list(union.values())


def _apply_preferred_post_filter(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
) -> list[sel_mod.MaterializedRow]:
    """Post-filter rows for `mm query missing-set` regular sub-selectors when
    `--treatment-class=preferred`. Applies two exclusions that the selector
    grammar's `treatment=preferred` already applies to the alt sub-selector,
    but which need to be applied to the regular sub-selectors here:

    1. **Digital-only (Arena/Alchemy rebalanced)** — drop unconditionally.
       Same rule the selector applies; these never have physical counterparts.

    2. **Datestamped reprints with a non-stamped sibling** at the same name and
       same treatment codes in the family. Catches PFIN's prerelease-stamped
       FIN cards that are visually identical to the FIN versions.
    """
    import json as _json
    from . import treatments as _treatments
    from .selectors import (
        _is_digital_only as _digital_only,
        _is_family_unobtainable as _family_unobtainable,
    )

    if not rows:
        return rows

    # Step 1: drop digital-only + serialized prints unconditionally, then
    # apply the family's unobtainable-rules (e.g. LTR's scroll-frame
    # silverfoils). Same exclusions the selector-side preferred filter
    # applies; we run them here so the rare/mythic-regular sub-selectors
    # of `mm query missing-set` match.
    rows = [r for r in rows if not _digital_only(r.card)]
    rows = [r for r in rows if not _family_unobtainable(r.card, anchor_code)]
    if not rows:
        return rows

    # Step 2: build family index for datestamped-with-sibling check.
    try:
        family_codes = set(sets_mod.resolve(anchor_code).all_codes)
    except LookupError:
        family_codes = {anchor_code}
    placeholders = ",".join("?" for _ in family_codes)
    with db.connect() as conn:
        fam_rows = conn.execute(
            f"SELECT scryfall_id, name, frame_effects, full_art, promo_types "
            f"FROM cards WHERE set_code IN ({placeholders})",
            list(family_codes),
        ).fetchall()
    by_name_codes: dict[tuple[str | None, frozenset[str]], list[dict]] = {}
    promo_index: dict[str, set[str]] = {}
    for fr in fam_rows:
        t = _treatments.compute_treatment(dict(fr))
        codes = frozenset(t.split("|")) if t else frozenset()
        pt = set(_json.loads(fr["promo_types"] or "[]"))
        promo_index[fr["scryfall_id"]] = pt
        by_name_codes.setdefault((fr["name"], codes), []).append({
            "scryfall_id": fr["scryfall_id"],
            "promo_types": pt,
        })
    out: list[sel_mod.MaterializedRow] = []
    for r in rows:
        sid = r.scryfall_id
        my_pt = promo_index.get(sid, set())
        if "datestamped" not in my_pt:
            out.append(r)
            continue
        t = _treatments.compute_treatment(r.card)
        codes = frozenset(t.split("|")) if t else frozenset()
        siblings = by_name_codes.get((r.card.get("name"), codes), [])
        non_stamped_sibling_exists = any(
            s["scryfall_id"] != sid and "datestamped" not in s["promo_types"]
            for s in siblings
        )
        if not non_stamped_sibling_exists:
            out.append(r)  # Keep — no cheaper sibling to substitute.
    return out


def _drop_meld_back_faces(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
) -> list[sel_mod.MaterializedRow]:
    """Drop rows whose card name has ALL its family printings on a 'b'-suffix
    collector number — these are meld-back faces (not real products).

    Heuristic: a meld card has two front halves (e.g. Fang + Vanille) plus
    the merged back face (Ragnarok). Wizards prints the back face with the
    same set + a CN like ``99b``, ``381b``, ``446b``, ``526b``. Scryfall
    captures it as a separate ``cards`` row, but neither TCGplayer nor
    ManaPool sells it as a standalone product — it's only obtained as the
    back of one of the front-half printings.

    The signal: every printing of the card name in the family has a CN
    that ends in ``b``. Real cards with a 'b' variant (e.g. neon-ink
    ``Traveling Chocobo`` 551b) ALSO have non-'b' siblings under the same
    name, so they pass through. Robust across families without a per-set
    allowlist.
    """
    if not rows:
        return rows
    try:
        family_codes = set(sets_mod.resolve(anchor_code).all_codes)
    except LookupError:
        family_codes = {anchor_code}
    placeholders = ",".join("?" for _ in family_codes)
    with db.connect() as conn:
        fam_rows = conn.execute(
            f"SELECT name, collector_number "
            f"FROM cards WHERE set_code IN ({placeholders})",
            list(family_codes),
        ).fetchall()
    cns_by_name: dict[str, list[str]] = {}
    for fr in fam_rows:
        cns_by_name.setdefault(fr["name"], []).append(fr["collector_number"] or "")
    meld_back_names = {
        name for name, cns in cns_by_name.items()
        if cns and all(cn.endswith("b") for cn in cns)
    }
    return [r for r in rows if r.card.get("name") not in meld_back_names]


# ---------- scarcity-tier concentration flag (advisory, never an action) ----------
#
# When a family's missing $ is dominated by a few very expensive prints, that's
# usually a "scarcity chase tier" the collector won't realistically buy (a
# fancy-foil masterpiece run, a serialized headliner, etc.) — the pattern that
# made SPM's missing show $4,230 when the realistically-attainable gap was ~$440.
#
# CRITICAL: concentration does NOT decide exclude-vs-keep. A 2026-09 back-test
# over all 20 characterized families (reconstructing each family's before-rules
# missing distribution, labeled by how much $ its rules actually removed) found
# NO distribution statistic separates the two: `fin` (KEPT, borderless anime
# chase the user WANTS: $10.9k missing, top5=0.70, >$100-share=0.80) and `tmt`
# (KEPT, top5=0.90) are MORE concentrated than several families that got scarcity
# exclusions (`snc` top5=0.25, `one` 0.28). "Unobtainable" is the user's
# preference, not a property of the price curve. So this only FLAGS concentration
# for a human review; the exclude/keep call stays with the user (per family).
#
# Thresholds calibrated from that back-test to fire on the real scarcity tiers
# (spm-before, blb, eoe, lci, ltr, tla, …) and stay quiet on flat families
# (acr $288, inr $659, sos $905, ecl $733). fin/tmt also fire — acceptable: the
# warning says "review," and reviewing a wanted chase correctly concludes "keep."
CONCENTRATION_MIN_USD = 750.0     # below this, a concentrated shape isn't worth flagging
CONCENTRATION_OVER = 100.0        # a print above this $ counts as "high-value"
CONCENTRATION_OVER_SHARE = 0.50   # OR: high-value prints are ≥ this share of total $
CONCENTRATION_TOP5_SHARE = 0.60   # OR: the top 5 prints are ≥ this share of total $


def concentration(rows, price_fn) -> dict:
    """Summarize how concentrated a missing-list's $ value is, for a review prompt.

    ``rows`` are ``selectors.MaterializedRow`` (from ``missing_printings``);
    ``price_fn(scryfall_id, finish) -> float`` supplies the unit price (callers
    inject their own source — set-status uses live Scryfall prices, an offline
    caller can use the local ``cards`` table). Pure + side-effect-free.

    Returns ``{total_usd, n, top5_share, n_over_100, over_100_share, top_prints}``
    where ``top_prints`` is the 5 priciest as ``(name, set, cn, finish, usd)``.
    No decision is made here — see :func:`is_concentrated`.
    """
    priced = []
    for r in rows:
        usd = price_fn(r.scryfall_id, r.finish) or 0.0
        if usd > 0:
            c = r.card
            priced.append((usd, c.get("name") or "?", (c.get("set") or "").upper(),
                           c.get("collector_number") or "?", r.finish))
    priced.sort(reverse=True, key=lambda t: t[0])
    total = sum(p[0] for p in priced)
    n = len(priced)
    if not total:
        return {"total_usd": 0.0, "n": n, "top5_share": 0.0, "n_over_100": 0,
                "over_100_share": 0.0, "top_prints": []}
    over = [p for p in priced if p[0] > CONCENTRATION_OVER]
    return {
        "total_usd": round(total, 2),
        "n": n,
        "top5_share": sum(p[0] for p in priced[:5]) / total,
        "n_over_100": len(over),
        "over_100_share": sum(p[0] for p in over) / total,
        "top_prints": [(name, st, cn, fin, round(usd, 2))
                       for usd, name, st, cn, fin in priced[:5]],
    }


def is_concentrated(conc: dict) -> bool:
    """Advisory trigger: True iff the missing $ looks like a scarcity chase tier
    worth a human review. Fires when the total is non-trivial AND the value is
    concentrated (by high-value share OR top-5 share). NOT a classifier — a
    prompt to review; the exclude/keep decision is the user's (see the module
    note above; fin/tmt are the standing 'concentrated but KEPT' examples)."""
    if conc.get("total_usd", 0.0) < CONCENTRATION_MIN_USD:
        return False
    return (conc.get("over_100_share", 0.0) >= CONCENTRATION_OVER_SHARE
            or conc.get("top5_share", 0.0) >= CONCENTRATION_TOP5_SHARE)


# ---------- functional completeness (own ≥1 printing of each mechanically-unique card) ----------
#
# `functional_missing` answers a DIFFERENT question than `missing_printings`:
# not "which distinct art/frame printings do I lack" but "which MECHANICALLY-
# UNIQUE cards (by oracle_id) do I own ZERO copies of, in ANY printing/finish,
# and what's the cheapest way to get one." A card whose base you own but whose
# borderless variant you lack IS in missing_printings (variant unowned) yet is
# functionally OWNED — so this is computed from ownership-by-oracle across the
# family, NOT by collapsing the printing-missing list.
#
# Candidate cards = the oracle_ids appearing in missing_printings (which already
# applies the digital-only / family-unobtainable / meld-back / preferred filters),
# minus the oracle_ids the user owns any printing of. SCOPE NOTE: missing_printings
# only unions rare/mythic/uncommon-chase + the preferred alt class, so a COMMON
# owned in zero printings won't appear here — matching set-status's "don't chase
# every common" stance. Documented limit, not a bug.

@dataclass
class FunctionalMissingCard:
    """One mechanically-unique card the user owns in zero printings, with the
    cheapest fill price at two scopes."""
    oracle_id: str
    name: str
    set_code: str | None = None          # set of the cheapest IN-FAMILY printing
    family_cn: str | None = None         # its collector_number
    family_usd: float | None = None      # cheapest IN-FAMILY printing (either finish)
    family_finish: str | None = None     # 'nonfoil' | 'foil'
    anywhere_usd: float | None = None    # cheapest printing ANY set (None if unresolved)
    anywhere_finish: str | None = None


@dataclass
class FunctionalMissing:
    cards: list[FunctionalMissingCard] = field(default_factory=list)
    n_cards: int = 0
    family_total_usd: float = 0.0        # Σ family_usd (unpriced card → $0, still counted)
    anywhere_total_usd: float = 0.0      # Σ anywhere_usd, falling back to family_usd when unresolved


def _cheapest(nonfoil: float | None, foil: float | None) -> tuple[float | None, str | None]:
    """Cheaper of (nonfoil, foil); prefer nonfoil on tie, foil only if no nonfoil.
    Returns (price, finish) or (None, None) if neither priced."""
    if nonfoil is not None and (foil is None or nonfoil <= foil):
        return nonfoil, "nonfoil"
    if foil is not None:
        return foil, "foil"
    return None, None


def functional_missing(
    code: str,
    treatment_class: str = "preferred",
    *,
    precomputed_missing: list | None = None,
    anywhere_floor_fn: Callable[[str], tuple[float | None, str | None] | None] | None = None,
) -> FunctionalMissing:
    """Mechanically-unique cards (by oracle_id) in the family owned in ZERO
    printings, each with its cheapest in-family fill price (and, if
    ``anywhere_floor_fn`` is supplied, the cheapest-anywhere fill).

    ``precomputed_missing`` lets a caller that already ran ``missing_printings``
    pass those rows in (avoids recompute — the overview does this).
    ``anywhere_floor_fn(oracle_id) -> (usd, finish)|None`` supplies the cross-set
    floor; when ``None`` the anywhere fields stay ``None`` and ``anywhere_total_usd``
    falls back to the in-family price. Family scope matches ``missing_printings``
    (Scryfall graph via ``sets.resolve``), so the two figures are comparable.
    """
    rows = precomputed_missing if precomputed_missing is not None \
        else missing_printings(code, treatment_class)
    # Candidate oracle_ids from the (already-filtered) printing-missing list.
    candidate_oids = {
        oid for r in rows
        if (oid := (r.card or {}).get("oracle_id"))
    }
    if not candidate_oids:
        return FunctionalMissing()

    try:
        family_codes = {c.lower() for c in sets_mod.resolve(code).all_codes}
    except LookupError:
        family_codes = {code.lower()}

    with db.connect() as conn:
        fam_ph = ",".join("?" for _ in family_codes)
        # oracle_ids the user owns ANY printing/finish of, within the family.
        owned = {
            r[0] for r in conn.execute(
                f"SELECT DISTINCT c.oracle_id FROM inventory i "
                f"JOIN cards c ON c.scryfall_id = i.scryfall_id "
                f"WHERE i.quantity > 0 AND LOWER(c.set_code) IN ({fam_ph}) "
                f"AND c.oracle_id IS NOT NULL",
                list(family_codes),
            ).fetchall()
        }
        missing_oids = candidate_oids - owned
        if not missing_oids:
            return FunctionalMissing()
        # Cheapest in-family printing per missing oracle_id (local prices).
        oid_ph = ",".join("?" for _ in missing_oids)
        price_rows = conn.execute(
            f"SELECT oracle_id, name, set_code, collector_number, "
            f"prices_usd, prices_usd_foil FROM cards "
            f"WHERE LOWER(set_code) IN ({fam_ph}) AND oracle_id IN ({oid_ph})",
            list(family_codes) + list(missing_oids),
        ).fetchall()

    # Per oracle: pick the cheapest printing (either finish) across its family prints.
    best: dict[str, FunctionalMissingCard] = {}
    for r in price_rows:
        oid = r["oracle_id"]
        price, finish = _cheapest(r["prices_usd"], r["prices_usd_foil"])
        cur = best.get(oid)
        if cur is None:
            best[oid] = FunctionalMissingCard(
                oracle_id=oid, name=r["name"], set_code=r["set_code"],
                family_cn=r["collector_number"], family_usd=price, family_finish=finish,
            )
        elif price is not None and (cur.family_usd is None or price < cur.family_usd):
            cur.family_usd, cur.family_finish = price, finish
            cur.set_code, cur.family_cn = r["set_code"], r["collector_number"]
    # Missing oracles with NO family printing row at all (shouldn't happen — they
    # came from the family — but guard): still count them, $0.
    for oid in missing_oids:
        if oid not in best:
            best[oid] = FunctionalMissingCard(oracle_id=oid, name="(unknown)")

    # Anywhere floor (opt-in, injected + cached by the caller).
    if anywhere_floor_fn is not None:
        for card in best.values():
            res = anywhere_floor_fn(card.oracle_id)
            if res is not None:
                card.anywhere_usd, card.anywhere_finish = res

    cards = list(best.values())
    fam_total = round(sum(c.family_usd or 0.0 for c in cards), 2)
    any_total = round(sum(
        (c.anywhere_usd if c.anywhere_usd is not None else (c.family_usd or 0.0))
        for c in cards
    ), 2)
    return FunctionalMissing(cards=cards, n_cards=len(cards),
                             family_total_usd=fam_total, anywhere_total_usd=any_total)
