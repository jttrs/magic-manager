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

from . import db, ownership as _ownership, sets as sets_mod, selectors as sel_mod
from .card_floor import cheapest_floor as _cheapest


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

    # 1c. Tokens NEVER belong in a missing-set buy-list — the user won't buy
    # tokens (or emblems) to "complete" a set. One chokepoint over all four
    # sub-selectors (they all funnel through sub_rows before the union).
    for slug_key in list(sub_rows.keys()):
        sub_rows[slug_key] = _drop_tokens(sub_rows[slug_key])

    # 2. Union by scryfall_id (printing-level dedup).
    union: dict[str, sel_mod.MaterializedRow] = {}
    for slug_key in sub_rows:
        for r in sub_rows[slug_key]:
            union[r.scryfall_id] = r
    return list(union.values())


def _drop_tokens(
    rows: list[sel_mod.MaterializedRow],
) -> list[sel_mod.MaterializedRow]:
    """Drop tokens/emblems. Explicit ``is_token`` guard rather than a rarity
    gate: rare/mythic tokens DO exist and would otherwise leak into a buy-list.
    The single token chokepoint, shared by ``missing_printings`` and
    ``physical_buyable``."""
    return [r for r in rows if not r.card.get("is_token")]


def physical_buyable(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
    *,
    drop_tokens: bool = True,
    drop_digital: bool = True,
    drop_family_unobtainable: bool = True,
    drop_datestamped_siblings: bool = True,
    drop_meld_backs: bool = True,
) -> list[sel_mod.MaterializedRow]:
    """The 'would a physical collector actually buy this printing?' gate for a
    FLAT list of rows — the intentional, uniform filter every buy-list producer
    (jumpstart-buildable, etc.) runs so none of them silently leak tokens,
    digital-only prints, hand-ruled unobtainable prints, or meld-back faces.

    Composes the same primitives ``missing_printings`` applies, each toggleable
    so a producer can opt out of a single exclusion (the ``--no-filter`` escape
    hatch disables the whole gate): digital-only + family-unobtainable
    (:func:`selectors.preferred_exclusions`), datestamped-with-sibling
    (:func:`drop_datestamped_with_sibling`), meld-backs
    (:func:`_drop_meld_back_faces`), tokens (:func:`_drop_tokens`).

    NOTE: this is for flat producers, NOT a drop-in for ``missing_printings`` —
    that function applies the digital/unobtainable/datestamped filter only to
    its REGULAR sub-selectors (the alt sub-selector was already filtered,
    finish-aware, at materialize time), so routing its union through this gate
    would double-apply the datestamped scan. The two share primitives, not the
    composition.
    """
    # Digital-only + family-unobtainable are the two independent row-wise steps
    # that selectors.preferred_exclusions composes; apply each only if its toggle
    # is on. (No branch for "both on" — the two guards together ARE
    # preferred_exclusions, so there's nothing to special-case.)
    if drop_digital:
        rows = [r for r in rows if not sel_mod._is_digital_only(r.card)]
    if drop_family_unobtainable:
        rows = [r for r in rows if not sel_mod._is_family_unobtainable(r.card, anchor_code)]
    # The two family-index sub-filters both need the family's set codes; resolve
    # ONCE here and thread it in so they don't each re-run sets.resolve (an
    # uncached subprocess) + a family-wide card scan.
    family_codes = None
    if drop_datestamped_siblings or drop_meld_backs:
        try:
            family_codes = set(sets_mod.resolve(anchor_code).all_codes)
        except LookupError:
            family_codes = {anchor_code}
    if drop_datestamped_siblings:
        rows = drop_datestamped_with_sibling(rows, anchor_code, family_codes=family_codes)
    if drop_meld_backs:
        rows = _drop_meld_back_faces(rows, anchor_code, family_codes=family_codes)
    if drop_tokens:
        rows = _drop_tokens(rows)
    return rows


def _apply_preferred_post_filter(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
) -> list[sel_mod.MaterializedRow]:
    """Post-filter rows for `mm query missing-set` regular sub-selectors when
    `--treatment-class=preferred`. The selector grammar's `treatment=preferred`
    already applies these to the alt sub-selector; the regular (rare/mythic/
    uncommon-chase) sub-selectors need them here so the two agree. Composed of
    the two shared steps:

    1. :func:`selectors.preferred_exclusions` — digital-only (Arena/Alchemy
       rebalanced + serialized) and family-unobtainable prints.
    2. :func:`drop_datestamped_with_sibling` — datestamped reprints that have a
       non-stamped same-name same-codes sibling (e.g. PFIN's prerelease-stamped
       FIN cards, visually identical to the FIN versions).
    """
    if not rows:
        return rows
    # Step 1: digital-only + serialized + family-unobtainable. ONE home shared
    # with the selector-side preferred filter (selectors._filter_treatment_preferred
    # Step 0) so the rare/mythic-regular sub-selectors of `mm query missing-set`
    # match the alt sub-selector.
    rows = sel_mod.preferred_exclusions(rows, anchor_code)
    if not rows:
        return rows
    # Step 2: datestamped reprints with a non-stamped sibling.
    return drop_datestamped_with_sibling(rows, anchor_code)


def _family_codes_for(anchor_code: str) -> set[str]:
    """Resolve the family's set codes, falling back to just ``anchor_code`` when
    the anchor isn't a resolvable Scryfall set. Shared fallback for the two
    family-index filters (and so ``physical_buyable`` can resolve once + thread)."""
    try:
        return set(sets_mod.resolve(anchor_code).all_codes)
    except LookupError:
        return {anchor_code}


def drop_datestamped_with_sibling(
    rows: list[sel_mod.MaterializedRow],
    anchor_code: str,
    *,
    family_codes: set[str] | None = None,
) -> list[sel_mod.MaterializedRow]:
    """Drop datestamped (prerelease-stamped) reprints that have a non-stamped
    sibling at the same name + same treatment codes anywhere in the family —
    the stamped print is a visual dupe of a cheaper obtainable one (e.g. PFIN's
    prerelease-stamped FIN cards). A datestamped print with NO non-stamped
    sibling is kept (nothing cheaper to substitute).

    ``family_codes`` (the family's set codes) is resolved lazily when ``None``;
    ``physical_buyable`` resolves it once and threads it into both family-index
    filters to avoid a redundant ``sets.resolve`` per filter.

    NOTE (intentional deviation from the selector-side scan in
    ``selectors._filter_treatment_preferred``): here the sibling index computes
    treatment PRINTING-LEVEL (finish-unaware) because the regular missing-set
    sub-selectors are already printing-grained; the selector side keys
    finish-aware on collectible-alt rows. Same datestamped rule, different row
    population — so the two scans are deliberately NOT merged into one call.
    """
    import json as _json
    from . import treatments as _treatments

    if not rows:
        return rows
    if family_codes is None:
        family_codes = _family_codes_for(anchor_code)
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
    *,
    family_codes: set[str] | None = None,
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

    ``family_codes`` is resolved lazily when ``None`` (see
    :func:`drop_datestamped_with_sibling`).
    """
    if not rows:
        return rows
    if family_codes is None:
        family_codes = _family_codes_for(anchor_code)
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


def owned_oracle_ids(family_codes: set[str]) -> set[str]:
    """oracle_ids the user owns ANY printing/finish of, within the given family
    set codes. ``family_codes`` must already be lowercased (callers resolve the
    family via ``sets.resolve(...).all_codes`` and lowercase them).

    Re-export of :func:`ownership.owned_oracle_ids` — kept here as the historical
    name its callers (``functional_missing``, ``variant_chase_printings``,
    ``card_diff``, tests) already import."""
    return _ownership.owned_oracle_ids(family_codes)


def functional_missing(
    code: str,
    treatment_class: str = "preferred",
    *,
    precomputed_missing: list | None = None,
    anywhere_floor_fn: Callable[[str], tuple[float | None, str | None] | None] | None = None,
    precomputed_owned: set[str] | None = None,
) -> FunctionalMissing:
    """Mechanically-unique cards (by oracle_id) in the family owned in ZERO
    printings, each with its cheapest in-family fill price (and, if
    ``anywhere_floor_fn`` is supplied, the cheapest-anywhere fill).

    ``precomputed_missing`` lets a caller that already ran ``missing_printings``
    pass those rows in (avoids recompute — the overview does this).
    ``precomputed_owned`` lets a caller that already computed
    ``owned_oracle_ids({c.lower() for c in sets.resolve(code).all_codes})`` pass
    that set in directly, skipping the resolve + query here (``card_diff``
    does this — it computes the same owned set once and threads it into both
    this function and ``variant_chase_printings``). When ``None``, behavior is
    unchanged — this function resolves the family and queries ownership itself.
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

    owned = precomputed_owned if precomputed_owned is not None else owned_oracle_ids(family_codes)
    with db.connect() as conn:
        fam_ph = ",".join("?" for _ in family_codes)
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


# ---------- variant-chase (missing printings whose card you already own) ----------
#
# `variant_chase_printings` answers a THIRD question, the complement of
# functional_missing within missing_printings: not "cards I own zero printings
# of" but "printings I lack of a card I DO already own" — the borderless /
# alt-art / fancy-foil chase for a card whose base copy is already in hand.
# Formally: missing_printings rows whose oracle_id ∈ owned_oracle_ids(family) —
# i.e. (printing-missing) ∩ (owned-oracle), the mirror image of
# functional_missing's (candidate-oracle) − (owned-oracle) set subtraction.

def variant_chase_printings(
    code: str,
    treatment_class: str = "preferred",
    *,
    precomputed_missing: list | None = None,
    precomputed_owned: set[str] | None = None,
) -> list:
    """missing_printings rows whose oracle_id the user ALREADY owns in the
    family (the printing-missing ∩ owned-oracle diff — variant/alt-art/fancy-
    foil printings of cards you have). ``precomputed_missing`` reuses rows if
    the caller already ran ``missing_printings``. ``precomputed_owned`` lets a
    caller that already computed ``owned_oracle_ids({c.lower() for c in
    sets.resolve(code).all_codes})`` pass that set in directly (see
    ``functional_missing``'s matching param); ``None`` preserves current
    behavior exactly (resolve + query here)."""
    rows = precomputed_missing if precomputed_missing is not None \
        else missing_printings(code, treatment_class)
    if not rows:
        return []
    if precomputed_owned is not None:
        owned = precomputed_owned
    else:
        try:
            family_codes = {c.lower() for c in sets_mod.resolve(code).all_codes}
        except LookupError:
            family_codes = {code.lower()}
        owned = owned_oracle_ids(family_codes)
    return [r for r in rows if (r.card or {}).get("oracle_id") in owned]
