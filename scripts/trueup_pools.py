"""True up the deconstructed-precon collection by attributing LOOSE cards to the
products they came from — scene boxes, precon/jumpstart decks, card pools, and
complete Secret Lair drops — and re-labelling their provenance in the ledger.

The V19 backfill left copies in the ``unattributed-backfill`` bucket that are
really unregistered products (a scene box's cards sitting loose, a jumpstart
pack's ``tle`` half, …). This script matches the user's FREE (unpledged)
inventory against known product recipes and, for any product whose FULL recipe
is present, registers a tracked ``deconstructed`` deck row (so precon unit counts
become correct — no inventory double-count) AND moves those copies in the ledger
from ``unattributed-backfill`` → a real ``precon`` event.

Safety model:
  - **Full coverage only**: a product is claimed only when every recipe card is
    present in free inventory.
  - **Report conflicts, don't auto-resolve**: when candidate products contend for
    the same loose copy and copies are insufficient for all, they are REPORTED,
    not written; the user resolves via ``--pick``.
  - **Dry-run by default**: writes only under ``--apply``.
  - A loose card backs at most as many products as the user owns copies of it.

Modes (which products to test):
  --from-unattributed  (default) only products in sets that still have
                       unattributed-backfill copies — bounds the work and
                       directly shrinks the unknown bucket.
  <target>             a set code / family (sets.resolve) or product-name substr.
  --all                every set the user owns loose cards from.

Usage
-----
    uv run python scripts/trueup_pools.py [--from-unattributed | --all | <target>]
        [--apply] [--pick slug,slug] [--sld-partial-threshold 0.9] [--json]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import (  # noqa: E402
    db, decks as decks_mod, ingest as ingest_mod, mtgjson as mtgjson_mod,
    sets as sets_mod, sld as sld_mod,
)

# Jumpstart + precon-shaped DeckList types worth matching (Secret Lair handled
# separately via sld.py; digital/MTGO excluded like precon-list does).
_MATCHABLE_TYPES_EXCLUDED = {"MTGO", "Secret Lair Drop"}


# ---------- contest-priority config ----------

# Baked-in defaults (mirror config/product_priority.toml). Higher tier wins a
# contested shared card; unlisted types fall to DEFAULT_TIER. Overridable by the
# TOML file so the user can retune without code changes.
_DEFAULT_TIER = 50
_DEFAULT_TIERS = {
    "Commander Deck": 100,
    "Box Set": 90,
    "Starter Kit": 90,
    "Jumpstart": 80,
    "Secret Lair Drop": 80,
    "Arena Starter Deck": 60,
    "Bundle Land Pack": 10,  # basic-land filler — loses shared basics to real products
}
_CONFIG_PATH = ROOT / "config" / "product_priority.toml"


def _load_priority_config() -> dict:
    """Load contest-priority config (TOML), falling back to baked-in defaults so
    the tool works with no file. Returns {tiers, default_tier, prefer_lower_version}."""
    cfg = {"tiers": dict(_DEFAULT_TIERS), "default_tier": _DEFAULT_TIER,
           "prefer_lower_version": True}
    try:
        import tomllib
        with open(_CONFIG_PATH, "rb") as f:
            data = tomllib.load(f)
        if isinstance(data.get("tiers"), dict):
            cfg["tiers"] = {str(k): int(v) for k, v in data["tiers"].items()}
        if "default_tier" in data:
            cfg["default_tier"] = int(data["default_tier"])
        if "prefer_lower_version" in data:
            cfg["prefer_lower_version"] = bool(data["prefer_lower_version"])
    except FileNotFoundError:
        pass
    except Exception as e:  # noqa: BLE001 — bad config shouldn't break the run
        print(f"  warn: could not parse {_CONFIG_PATH} ({e!r}); using defaults", file=sys.stderr)
    return cfg


def _version_number(product: dict) -> int:
    """Trailing version number of a variant product (Adept (2) / Gliding2_TLE → 2),
    else 0. Used as the same-tier tiebreak (lower version preferred)."""
    import re
    name = product.get("name") or ""
    m = re.search(r"\((\d+)\)\s*$", name)
    if m:
        return int(m.group(1))
    fn = product.get("fileName") or ""
    stem = fn.rsplit("_", 1)[0] if "_" in fn else fn
    m = re.search(r"(\d+)$", stem)
    return int(m.group(1)) if m else 0


def _priority_key(product: dict, cfg: dict) -> tuple:
    """Sort key for contest allocation: HIGHER priority first. Returns a tuple
    ordered so Python's ascending sort puts the winner first:
      (−tier, version, release_date, fileName).
    Higher tier wins; among equal tiers a LOWER version number wins (the '(2)'
    quirk); then earlier release; then fileName for determinism."""
    tier = cfg["tiers"].get(product.get("type"), cfg["default_tier"])
    ver = _version_number(product) if cfg.get("prefer_lower_version", True) else 0
    return (-tier, ver, product.get("releaseDate") or "", product.get("fileName") or "")


# ---------- candidate enumeration ----------

def _backfill_set_codes(conn) -> set[str]:
    """Set codes with any RE-ATTRIBUTABLE balance — cards still held by a
    best-effort backfill event (``status='backfill'``). The default
    ``--from-unattributed`` scope: sets whose provenance is still a backfill
    guess and could be refined into product attributions."""
    rows = conn.execute(
        """
        SELECT DISTINCT c.set_code
        FROM inventory_events ie
        JOIN ingest_events ev ON ev.ingest_id = ie.ingest_id
        JOIN cards c ON c.scryfall_id = ie.scryfall_id
        WHERE ev.status = 'backfill' AND ie.delta > 0
        """
    ).fetchall()
    return {r["set_code"].lower() for r in rows}


def _loose_set_codes(conn) -> set[str]:
    """Every set code the user owns at least one copy from (the ``--all`` scope).

    Scope only — the actual coverage check runs against the unattributed balance
    per card, so a set with only fully-attributed cards simply yields no
    coverable products. Owning ≥1 copy is a cheap superset filter."""
    return {
        r["set_code"].lower()
        for r in conn.execute(
            "SELECT DISTINCT c.set_code FROM inventory i "
            "JOIN cards c ON c.scryfall_id = i.scryfall_id"
        )
    }


def _enumerate_products(set_codes: set[str]) -> list[dict]:
    """DeckList products (precon/jumpstart/pool decks) for the given sets.

    Returns entries ``{fileName, name, code, type}`` excluding SLD/MTGO. SLD
    drops are enumerated separately.
    """
    products: list[dict] = []
    seen: set[str] = set()
    for sc in sorted(set_codes):
        try:
            for d in mtgjson_mod.deck_list(set_code=sc):
                fn = d.get("fileName")
                if not fn or fn in seen:
                    continue
                if d.get("type") in _MATCHABLE_TYPES_EXCLUDED:
                    continue
                seen.add(fn)
                products.append(d)
        except Exception as e:  # noqa: BLE001
            print(f"  warn: deck_list({sc}) failed: {e!r}", file=sys.stderr)
    return products


# ---------- matching ----------

def _already_registered(conn, file_name: str) -> bool:
    """True if a deconstructed deck row already exists for this fileName (so the
    product is already tracked and shouldn't be re-claimed)."""
    row = conn.execute(
        "SELECT 1 FROM decks WHERE source_precon_file_name = ? "
        "AND precon_state = 'deconstructed' LIMIT 1",
        (file_name,),
    ).fetchone()
    return row is not None


def _owned_map(conn) -> dict[tuple[str, str], int]:
    """Raw owned copies per ``(scryfall_id, finish)`` — before any attribution.
    Used to distinguish 'committed to another product' from 'never owned'."""
    return {
        (r["scryfall_id"], r["finish"]): r["quantity"]
        for r in conn.execute("SELECT scryfall_id, finish, quantity FROM inventory")
    }


def _match_products(conn, products: list[dict], supply: dict) -> tuple[list[dict], dict]:
    """Compute per-product coverage against the UNATTRIBUTED-BALANCE ``supply``.

    ``supply`` maps ``(sid, finish) -> copies not yet attributed to any product``
    (the ``unattributed-backfill`` ledger balance). A product is COVERABLE iff
    every recipe card has ``supply >= need`` — i.e. its cards are genuinely
    unaccounted-for, so it could be the product they came from. This is the
    one-copy-one-product rule: a card already attributed to a precon/checklist
    has 0 balance and can't back a new product.

    Returns ``(covered, need_map)``; each covered product carries ``needs``,
    ``recipe_qty``, and coverage detail (``covered_qty``/``committed``/``missing``
    vs the raw owned map) for tier reporting. ``need_map`` sums demand across
    covered products (for conflict detection).
    """
    owned = _owned_map(conn)
    covered: list[dict] = []
    need_map: dict[tuple[str, str], int] = defaultdict(int)
    for d in products:
        fn = d["fileName"]
        if _already_registered(conn, fn):
            continue
        try:
            needs = decks_mod.precon_recipe_needs(fn)
        except Exception as e:  # noqa: BLE001
            print(f"  warn: recipe fetch failed for {fn}: {e!r}", file=sys.stderr)
            continue
        if not needs:
            continue
        if all(supply.get(k, 0) >= qty for k, qty in needs.items()):
            covered.append({
                "fileName": fn, "name": d.get("name") or fn,
                "type": d.get("type"), "needs": needs,
                "recipe_qty": sum(needs.values()),
            })
            for key, qty in needs.items():
                need_map[key] += qty
    return covered, need_map


def _partition_ready_conflicts(covered: list[dict], need_map: dict, supply: dict,
                               picks: set[str], cfg: dict | None = None
                               ) -> tuple[list[dict], list[dict], list[dict]]:
    """Allocate the unattributed ``supply`` to covered products by PRIORITY.

    One physical copy backs at most one product, so when several full-coverage
    products share a card that can't cover them all, the contest is resolved by
    priority (``cfg`` tiers → version tiebreak → release → fileName; see
    ``_priority_key``) instead of dumping every clash on the user. Walk products
    in priority order over a running ``balance`` (copy of ``supply``); a product
    whose full recipe still fits the balance is claimed (**ready**) and consumes
    its cards; one that no longer fits — because a higher-priority product took a
    shared card — is **conflicted**.

    ``--pick`` forces a product to the FRONT of the order (user override beats
    priority). A conflicted product is reported with the specific cards it lost
    and to whom, so a genuine same-tier tie is actionable via ``--pick``.
    """
    cfg = cfg or _load_priority_config()
    picked = [p for p in covered if p["fileName"] in picks or _slug_of(p) in picks]
    rest = sorted((p for p in covered if p not in picked),
                  key=lambda p: _priority_key(p, cfg))
    ordered = picked + rest  # picks first, then priority order

    balance = dict(supply)
    claimed_by: dict[tuple[str, str], list[str]] = defaultdict(list)  # key -> winner names
    ready: list[dict] = []
    conflicted: list[dict] = []
    for p in ordered:
        if all(balance.get(k, 0) >= qty for k, qty in p["needs"].items()):
            for k, qty in p["needs"].items():
                balance[k] -= qty
                claimed_by[k].append(p["name"])
            ready.append(p)
        else:
            # Record which cards it lost and to whom (the current claimants).
            lost = [{"scryfall_id": k[0], "finish": k[1], "need": qty,
                     "remaining": balance.get(k, 0),
                     "lost_to": claimed_by.get(k, [])}
                    for k, qty in p["needs"].items() if balance.get(k, 0) < qty]
            conflicted.append({**p, "lost": lost})

    contested_cards = []
    seen = set()
    for p in conflicted:
        for lo in p["lost"]:
            key = (lo["scryfall_id"], lo["finish"])
            if key in seen:
                continue
            seen.add(key)
            contested_cards.append({
                "scryfall_id": lo["scryfall_id"], "finish": lo["finish"],
                "demand": need_map.get(key, 0), "free": supply.get(key, 0),
                "products": [pp["name"] for pp in covered if key in pp["needs"]],
                "won_by": claimed_by.get(key, []),
            })
    return ready, conflicted, contested_cards


def _slug_of(product: dict) -> str:
    from magic_manager.decks import _slug
    return _slug(product.get("name") or product["fileName"])


# ---------- SLD ----------

def _sld_status(conn, threshold: float) -> tuple[list[dict], list[dict]]:
    """Return (complete, partial) Secret Lair drops by CN ownership.

    A drop is COMPLETE if every one of its collector numbers is owned (any
    finish, qty>=1). PARTIAL if the owned fraction >= threshold but < 1.0.
    """
    complete: list[dict] = []
    partial: list[dict] = []
    try:
        drops = sld_mod.all_drops()
    except Exception as e:  # noqa: BLE001
        print(f"  warn: sld.all_drops failed: {e!r}", file=sys.stderr)
        return complete, partial

    owned_cn = {
        r["collector_number"]
        for r in conn.execute("SELECT DISTINCT collector_number FROM cards c "
                              "JOIN inventory i ON i.scryfall_id=c.scryfall_id "
                              "WHERE LOWER(c.set_code)='sld'")
    }
    for name, drop in drops.items():
        try:
            ids = sld_mod.collect_drop_ids(drop.get("file_names", []))
        except Exception:  # noqa: BLE001
            continue
        # Map the drop's cards to collector numbers via the local cards table.
        cns = {r["collector_number"] for r in conn.execute(
            f"SELECT collector_number FROM cards WHERE scryfall_id IN "
            f"({','.join('?' * len(ids))})", ids)} if ids else set()
        if not cns:
            continue
        owned = cns & owned_cn
        frac = len(owned) / len(cns)
        entry = {"name": name, "cns": len(cns), "owned": len(owned), "frac": round(frac, 3),
                 "file_names": list(drop.get("file_names", []))}
        if frac >= 1.0:
            complete.append(entry)
        elif frac >= threshold:
            partial.append(entry)
    return complete, partial


def _sld_products(sld_complete: list[dict], supply: dict) -> list[dict]:
    """Turn complete SLD drops into matchable products — ONE per logical drop.

    A drop merges base + Foil-Edition siblings (same cards, different finish).
    Emitting both would double-count if the user owns both finishes, so we pick
    a SINGLE representative fileName per drop: the first sibling whose recipe is
    fully covered by the unattributed ``supply`` (base preferred by file_names
    order). This keeps a physical drop as one product through the
    coverage/conflict/apply path — exactly like any other precon.
    """
    products: list[dict] = []
    for d in sld_complete:
        chosen = None
        for fn in d["file_names"]:  # base first (group_drops order)
            try:
                needs = decks_mod.precon_recipe_needs(fn)
            except Exception:  # noqa: BLE001
                continue
            if needs and all(supply.get(k, 0) >= qty for k, qty in needs.items()):
                chosen = fn
                break
        if chosen is None:
            # No single edition fully covered on its own — fall back to the
            # first sibling so the drop still surfaces (may land in conflicts).
            chosen = d["file_names"][0] if d["file_names"] else None
        if chosen:
            products.append({"fileName": chosen, "name": d["name"],
                             "code": "SLD", "type": "Secret Lair Drop"})
    return products


# ---------- supply (re-attributable backfill balance) ----------

def _backfill_supply(conn) -> dict[tuple[str, str], int]:
    """Per-printing copies that are still RE-ATTRIBUTABLE — held by any
    best-effort backfill event (``status='backfill'``: the unattributed bucket
    PLUS the generic backfill:precon / backfill:checklist reconstructions). These
    were all guesses the product-coverage pass refines; real post-V19 ingests
    (``status!='backfill'``) are NOT re-attributable and are excluded.
    """
    bal: dict[tuple[str, str], int] = defaultdict(int)
    for r in conn.execute(
        "SELECT ie.scryfall_id, ie.finish, SUM(ie.delta) s "
        "FROM inventory_events ie JOIN ingest_events ev ON ev.ingest_id = ie.ingest_id "
        "WHERE ev.status = 'backfill' GROUP BY ie.scryfall_id, ie.finish"
    ):
        if r["s"]:
            bal[(r["scryfall_id"], r["finish"])] = r["s"]
    return bal


def _backfill_events_holding(conn) -> list[int]:
    """The backfill event ids that hold re-attributable copies, in draw order:
    unattributed FIRST (least-committed), then precon, then checklist."""
    rows = conn.execute(
        "SELECT ingest_id, method FROM ingest_events WHERE status = 'backfill'"
    ).fetchall()
    order = {"unattributed-backfill": 0, "precon": 1, "checklist": 2}
    return [r["ingest_id"] for r in sorted(rows, key=lambda r: order.get(r["method"], 9))]


# ---------- apply ----------

def _apply(conn, ready: list[dict]) -> dict:
    """Register each ready product as a deconstructed deck + re-attribute its
    copies from the BACKFILL buckets onto a per-product precon event. One
    transaction (the caller's). Verifies reconciliation before returning.

    Each recipe card is drawn from the backfill events that hold it (unattributed
    first, then precon, then checklist), capped to what each holds, decrementing
    a running per-event balance so no source goes negative and no copy is moved
    twice. The DECK ROW registers regardless; the ledger move is balance-limited
    (a card with no backfill balance left just isn't moved — inventory==SUM(delta)
    always holds).
    """
    # Per-event, per-card balances we can draw down.
    event_ids = _backfill_events_holding(conn)
    ev_bal: dict[int, dict[tuple[str, str], int]] = {}
    for eid in event_ids:
        m: dict[tuple[str, str], int] = defaultdict(int)
        for r in conn.execute(
            "SELECT scryfall_id, finish, SUM(delta) s FROM inventory_events "
            "WHERE ingest_id = ? GROUP BY scryfall_id, finish", (eid,)
        ):
            if r["s"] > 0:
                m[(r["scryfall_id"], r["finish"])] = r["s"]
        ev_bal[eid] = m

    registered = 0
    reattributed = 0
    partial_products = 0
    for p in ready:
        decks_mod.register_precon_from_loose(p["fileName"], name=p["name"])
        registered += 1
        to_id = ingest_mod.create_event(
            conn, "precon", label=f"trueup:{p['fileName']}",
            notes="product-coverage — attributed from backfill buckets",
        )
        moved_total = 0
        capped = False
        for (sid, fin), qty in p["needs"].items():
            need = qty
            for eid in event_ids:
                if need <= 0:
                    break
                avail = ev_bal[eid].get((sid, fin), 0)
                take = min(need, avail)
                if take > 0:
                    ingest_mod.record_delta(conn, eid, sid, fin, -take)
                    ingest_mod.record_delta(conn, to_id, sid, fin, take)
                    ev_bal[eid][(sid, fin)] -= take
                    need -= take
                    moved_total += take
            if need > 0:
                capped = True
        if capped:
            partial_products += 1
        reattributed += moved_total

    drift = ingest_mod.reconcile_inventory_ledger(conn)
    if drift:
        raise SystemExit(f"FAIL: ledger drift after true-up ({len(drift)} rows); rolled back")
    return {"registered": registered, "reattributed": reattributed,
            "partial_ledger_moves": partial_products}


# ---------- orchestration ----------

def run(*, mode: str, target: str | None, apply: bool, picks: set[str],
        sld_threshold: float, json_out: bool, refute: set[str] | None = None) -> int:
    with db.connect() as conn:
        # Supply = per-(sid,finish) copies still held by BEST-EFFORT backfill
        # events (status='backfill': unattributed + generic precon/checklist
        # reconstructions). These are all guesses this pass refines into concrete
        # product attributions. Real post-V19 ingests are excluded (not
        # re-attributable). Matching against this — not free inventory — enforces
        # one-copy-one-product.
        supply = _backfill_supply(conn)

        # Determine candidate set codes.
        if target:
            try:
                r = sets_mod.resolve(target)
                set_codes = {c.lower() for c in r.all_codes}
            except LookupError:
                set_codes = {target.lower()}
        elif mode == "all":
            set_codes = _loose_set_codes(conn)
        else:  # from-unattributed (default): sets with any re-attributable balance
            set_codes = _backfill_set_codes(conn)

        products = _enumerate_products(set_codes)

        # SLD (only when sld is in scope or --all). Complete drops become
        # matchable products (one per sibling fileName) folded into the same
        # coverage/conflict/apply pipeline; partials are advisory-only.
        sld_complete, sld_partial = ([], [])
        if "sld" in set_codes or mode == "all":
            sld_complete, sld_partial = _sld_status(conn, sld_threshold)
            products = products + _sld_products(sld_complete, supply)

        # --refute: products the user reviewed and says they did NOT buy. Drop
        # them from the candidate pool entirely (before matching), so their cards
        # stay in the unattributed pool for a legitimate lower-priority claimant.
        refute = refute or set()
        if refute:
            products = [p for p in products
                        if p["fileName"] not in refute and _slug_of(p) not in refute]

        covered, need_map = _match_products(conn, products, supply)
        cfg = _load_priority_config()
        ready, conflicted, contested = _partition_ready_conflicts(
            covered, need_map, supply, picks, cfg)

        result = {
            "mode": mode, "target": target, "set_codes": sorted(set_codes),
            "ready": [{"fileName": p["fileName"], "name": p["name"],
                       "recipe_qty": p["recipe_qty"]} for p in ready],
            "conflicts": [{"fileName": p["fileName"], "name": p["name"]} for p in conflicted],
            "contested_cards": contested,
            "sld_complete": sld_complete, "sld_partial": sld_partial,
            "applied": False,
        }

        if apply and ready:
            result.update(_apply(conn, ready))
            result["applied"] = True

    _report(result, json_out=json_out, apply=apply)
    return 0


def _report(result: dict, *, json_out: bool, apply: bool) -> None:
    if json_out:
        json.dump(result, sys.stdout, indent=2, default=str)
        sys.stdout.write("\n")
        return
    ready, conflicts = result["ready"], result["conflicts"]
    contested, sld_c, sld_p = result["contested_cards"], result["sld_complete"], result["sld_partial"]
    reattr = sum(p["recipe_qty"] for p in ready)

    print(f"Product coverage — scope: {result['mode']}"
          + (f" ({result['target']})" if result["target"] else "")
          + f" — {len(result['set_codes'])} set(s)")
    print()
    print(f"OWNED — covered from unattributed cards ({len(ready)} product(s), "
          f"{reattr} copies): products you can fully account for → likely purchased.")
    for p in ready:
        print(f"  {p['name']}  [{p['fileName']}]  {p['recipe_qty']} cards")
    if conflicts:
        print(f"\nNOT COVERED — lost a shared card to a higher-priority product "
              f"({len(conflicts)} product(s)). Priority auto-resolved these; "
              f"override with --pick <fileName> if you actually opened one:")
        for p in conflicts:
            won = sorted({w for lo in p.get("lost", []) for w in lo.get("lost_to", [])})
            tail = f"  (cards went to: {', '.join(won[:3])}{'…' if len(won) > 3 else ''})" if won else ""
            print(f"  {p['name']}  [{p['fileName']}]{tail}")
    if sld_c:
        print(f"\nSECRET LAIR — complete drops owned ({len(sld_c)}):")
        for d in sld_c:
            print(f"  {d['name']}  ({d['owned']}/{d['cns']} CNs)")
    if sld_p:
        print(f"\nSECRET LAIR — near-complete (>= threshold, confirm) ({len(sld_p)}):")
        for d in sld_p:
            print(f"  {d['name']}  ({d['owned']}/{d['cns']} CNs, {d['frac']*100:.0f}%)")

    print()
    if result.get("applied"):
        msg = (f"APPLIED: imputed {result['registered']} product acquisition(s) "
               f"(deconstructed deck row + precon ingest event), attributing "
               f"{result['reattributed']} card copies out of the unattributed bucket.")
        if result.get("partial_ledger_moves"):
            msg += (f" ({result['partial_ledger_moves']} product(s) had some cards "
                    f"already attributed elsewhere — deck row still registered, "
                    f"attribution capped to the unattributed balance.)")
        print(msg)
    else:
        print(f"(read-only report — no writes. Review the OWNED list above, then re-run "
              f"with --apply to impute the {len(ready)} covered product(s). Strike any "
              f"erroneous one with --refute <fileName>."
              + (" Override a NOT-COVERED loss with --pick <fileName>." if conflicts else "") + ")")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trueup_pools")
    parser.add_argument("target", nargs="?", default=None,
                        help="Set code/family or product-name substring to scope to.")
    parser.add_argument("--from-unattributed", action="store_true",
                        help="(default) only sets with unattributed-backfill copies.")
    parser.add_argument("--all", action="store_true", help="Every set with loose cards.")
    parser.add_argument("--apply", action="store_true", help="Write (default is dry-run).")
    parser.add_argument("--pick", default="", help="Comma-separated fileNames/slugs to claim from conflicts.")
    parser.add_argument("--refute", default="",
                        help="Comma-separated fileNames/slugs you did NOT buy — dropped from "
                             "candidates (their cards stay available for other products).")
    parser.add_argument("--sld-partial-threshold", type=float, default=0.9)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mode = "all" if args.all else ("target" if args.target else "from-unattributed")
    picks = {s.strip() for s in args.pick.split(",") if s.strip()}
    refute = {s.strip() for s in args.refute.split(",") if s.strip()}
    return run(mode=mode, target=args.target, apply=args.apply, picks=picks,
               sld_threshold=args.sld_partial_threshold, json_out=args.json, refute=refute)


if __name__ == "__main__":
    sys.exit(main())
