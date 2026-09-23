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
from magic_manager.inventory import free_quantity  # noqa: E402

# Jumpstart + precon-shaped DeckList types worth matching (Secret Lair handled
# separately via sld.py; digital/MTGO excluded like precon-list does).
_MATCHABLE_TYPES_EXCLUDED = {"MTGO", "Secret Lair Drop"}


# ---------- candidate enumeration ----------

def _unattributed_event_id(conn) -> int | None:
    row = conn.execute(
        "SELECT ingest_id FROM ingest_events WHERE method='unattributed-backfill' "
        "ORDER BY ingest_id LIMIT 1"
    ).fetchone()
    return row["ingest_id"] if row else None


def _unattributed_set_codes(conn) -> set[str]:
    """Set codes that still have copies in the unattributed bucket."""
    uid = _unattributed_event_id(conn)
    if uid is None:
        return set()
    rows = conn.execute(
        """
        SELECT DISTINCT c.set_code
        FROM inventory_events ie
        JOIN cards c ON c.scryfall_id = ie.scryfall_id
        WHERE ie.ingest_id = ? AND ie.delta > 0
        """,
        (uid,),
    ).fetchall()
    return {r["set_code"].lower() for r in rows}


def _loose_set_codes(conn) -> set[str]:
    """Every set code the user owns at least one FREE (unpledged) copy from."""
    rows = conn.execute(
        """
        SELECT c.set_code, i.scryfall_id, i.finish, i.quantity
        FROM inventory i JOIN cards c ON c.scryfall_id = i.scryfall_id
        """
    ).fetchall()
    out: set[str] = set()
    for r in rows:
        if free_quantity(r["scryfall_id"], r["finish"], conn=conn) > 0:
            out.add(r["set_code"].lower())
    return out


# ---------- not-owned exclusions (persistent registry) ----------

def _excluded_file_names(conn) -> set[str]:
    """Every fileName the user has marked not-owned (skipped by the true-up)."""
    return {r["file_name"] for r in conn.execute("SELECT file_name FROM excluded_products")}


def resolve_exclude_pattern(conn, pattern: str) -> list[dict]:
    """Resolve an --exclude pattern to concrete DeckList products.

    A pattern matches a product if:
      - it equals the product's fileName exactly (e.g. ``Marauders1_LTR``); OR
      - it is ``<setcode>:<selector>`` where selector is either a product TYPE
        (case-insensitive, e.g. ``ltr:jumpstart``) or a name substring
        (``tle:(2)``); OR
      - it is a bare name substring matched across all DeckList products
        (slower; scoped forms are preferred).
    Returns matching ``{fileName, name, code, type}`` dicts.
    """
    pat = pattern.strip()
    # setcode:selector
    if ":" in pat:
        sc, sel = pat.split(":", 1)
        sc, sel = sc.strip().lower(), sel.strip()
        entries = mtgjson_mod.deck_list(set_code=sc)
        sel_l = sel.lower()
        by_type = [e for e in entries if (e.get("type") or "").lower() == sel_l]
        if by_type:
            return by_type
        return [e for e in entries if sel_l in (e.get("name") or "").lower()]
    # exact fileName
    sc_guess = pat.rsplit("_", 1)[-1].lower() if "_" in pat else None
    if sc_guess:
        for e in mtgjson_mod.deck_list(set_code=sc_guess):
            if e.get("fileName") == pat:
                return [e]
    # bare name substring across everything the user has loose cards from
    hits: list[dict] = []
    for sc in sorted(_loose_set_codes(conn)):
        hits += [e for e in mtgjson_mod.deck_list(set_code=sc)
                 if pat.lower() in (e.get("name") or "").lower()]
    return hits


def add_exclusions(conn, file_names: list[dict], *, reason: str) -> int:
    """Persist products to the not-owned registry. Returns rows inserted."""
    from magic_manager import db as _db
    n = 0
    for e in file_names:
        fn = e.get("fileName")
        if not fn:
            continue
        cur = conn.execute(
            "INSERT OR IGNORE INTO excluded_products (file_name, name, reason, excluded_at) "
            "VALUES (?, ?, ?, ?)",
            (fn, e.get("name"), reason, _db._utcnow_iso()),
        )
        n += cur.rowcount
    return n


def _enumerate_products(set_codes: set[str], *, excluded: set[str] | None = None) -> list[dict]:
    """DeckList products (precon/jumpstart/pool decks) for the given sets.

    Returns entries ``{fileName, name, code, type}`` excluding SLD/MTGO and any
    fileName in ``excluded`` (the not-owned registry). SLD drops are enumerated
    separately.
    """
    excluded = excluded or set()
    products: list[dict] = []
    seen: set[str] = set()
    for sc in sorted(set_codes):
        try:
            for d in mtgjson_mod.deck_list(set_code=sc):
                fn = d.get("fileName")
                if not fn or fn in seen or fn in excluded:
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


def _match_products(conn, products: list[dict]) -> tuple[list[dict], dict]:
    """Compute per-product coverage against FREE inventory.

    Returns ``(covered, need_map)`` where ``covered`` is products whose FULL
    recipe is present in free inventory (each ``{fileName, name, needs:
    {(sid,finish): qty}, recipe_qty}``), and ``need_map`` maps
    ``(sid, finish) -> total qty demanded across all covered products`` (for
    conflict detection).
    """
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
        # Full coverage: every recipe card present in free inventory.
        if all(free_quantity(sid, fin, conn=conn) >= qty for (sid, fin), qty in needs.items()):
            covered.append({
                "fileName": fn, "name": d.get("name") or fn,
                "type": d.get("type"), "needs": needs,
                "recipe_qty": sum(needs.values()),
            })
            for key, qty in needs.items():
                need_map[key] += qty
    return covered, need_map


def _partition_ready_conflicts(conn, covered: list[dict], need_map: dict,
                               picks: set[str]) -> tuple[list[dict], list[dict], list[dict]]:
    """Split covered products into (ready, conflicted, contested_cards).

    A card is CONTESTED when total demand across covered products exceeds free
    copies. A product is CONFLICTED if it needs any contested card (unless the
    user --picked it). Picked products are treated as ready and their demand is
    removed from the contest for the remainder (first-come by pick order).
    """
    # Free supply per key.
    free: dict[tuple[str, str], int] = {}
    for key in need_map:
        sid, fin = key
        free[key] = free_quantity(sid, fin, conn=conn)

    # Honor picks first: subtract their demand from the pool + contest.
    remaining_need = dict(need_map)
    picked_products = [p for p in covered if p["fileName"] in picks or _slug_of(p) in picks]
    for p in picked_products:
        for key, qty in p["needs"].items():
            remaining_need[key] = remaining_need.get(key, 0) - qty
            free[key] = free.get(key, 0) - qty  # reserve for the pick

    contested = {key for key, dem in remaining_need.items() if dem > free.get(key, 0)}

    ready = list(picked_products)
    conflicted: list[dict] = []
    for p in covered:
        if p in picked_products:
            continue
        if any(key in contested for key in p["needs"]):
            conflicted.append(p)
        else:
            ready.append(p)

    contested_cards = [
        {"scryfall_id": k[0], "finish": k[1], "demand": need_map[k], "free": free_quantity(k[0], k[1], conn=conn),
         "products": [p["name"] for p in covered if k in p["needs"]]}
        for k in sorted(contested)
    ]
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


def _sld_products(conn, sld_complete: list[dict]) -> list[dict]:
    """Turn complete SLD drops into matchable products — ONE per logical drop.

    A drop merges base + Foil-Edition siblings (same cards, different finish).
    Emitting both would double-count if the user owns both finishes, so we pick
    a SINGLE representative fileName per drop: the first sibling whose recipe is
    fully covered by free inventory (base preferred by file_names order). This
    keeps a physical drop as one product through the coverage/conflict/apply
    path — exactly like any other precon.
    """
    products: list[dict] = []
    excluded = _excluded_file_names(conn)
    for d in sld_complete:
        chosen = None
        for fn in d["file_names"]:  # base first (group_drops order)
            if fn in excluded:
                continue
            try:
                needs = decks_mod.precon_recipe_needs(fn)
            except Exception:  # noqa: BLE001
                continue
            if needs and all(free_quantity(sid, fin, conn=conn) >= qty
                             for (sid, fin), qty in needs.items()):
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


# ---------- apply ----------

def _unattributed_balance(conn, uid: int) -> dict[tuple[str, str], int]:
    """Current per-printing balance held by the unattributed-backfill event."""
    bal: dict[tuple[str, str], int] = defaultdict(int)
    for r in conn.execute(
        "SELECT scryfall_id, finish, SUM(delta) s FROM inventory_events "
        "WHERE ingest_id = ? GROUP BY scryfall_id, finish", (uid,)
    ):
        bal[(r["scryfall_id"], r["finish"])] = r["s"]
    return bal


def _apply(conn, ready: list[dict], uid: int) -> dict:
    """Register each ready product as a deconstructed deck + re-attribute its
    copies in the ledger (unattributed → new precon event). One transaction
    (the caller's). Verifies reconciliation before returning.

    Re-attribution is CAPPED to what the unattributed-backfill event actually
    holds per printing (decremented as products consume it): a product's recipe
    card may already be attributed to a checklist/precon event, in which case we
    must NOT move it (that would push the unattributed balance negative and
    break inventory==SUM(delta)). The DECK ROW is still registered regardless —
    the product is genuinely owned; only the ledger move is balance-limited.
    """
    balance = _unattributed_balance(conn, uid)
    registered = 0
    reattributed = 0
    partial_products = 0
    for p in ready:
        decks_mod.register_precon_from_loose(p["fileName"], name=p["name"])
        registered += 1
        # Cap each printing to the remaining unattributed balance.
        deltas: list[tuple[str, str, int]] = []
        capped = False
        for (sid, fin), qty in p["needs"].items():
            take = min(qty, max(0, balance.get((sid, fin), 0)))
            if take < qty:
                capped = True
            if take > 0:
                deltas.append((sid, fin, take))
                balance[(sid, fin)] -= take
        if capped:
            partial_products += 1
        if deltas:
            ingest_mod.reattribute(
                conn, from_ingest_id=uid, to_method="precon",
                deltas=deltas, to_label=f"trueup:{p['fileName']}",
                to_notes="pool true-up — attributed from unattributed-backfill",
            )
            reattributed += sum(q for _, _, q in deltas)
    drift = ingest_mod.reconcile_inventory_ledger(conn)
    if drift:
        raise SystemExit(f"FAIL: ledger drift after true-up ({len(drift)} rows); rolled back")
    return {"registered": registered, "reattributed": reattributed,
            "partial_ledger_moves": partial_products}


# ---------- orchestration ----------

def run(*, mode: str, target: str | None, apply: bool, picks: set[str],
        sld_threshold: float, json_out: bool,
        exclude: list[str] | None = None, unexclude: list[str] | None = None,
        list_excluded: bool = False) -> int:
    with db.connect() as conn:
        # --- exclusion management (persistent not-owned registry) ---
        if exclude:
            added_total = 0
            resolved: list[dict] = []
            for pat in exclude:
                matches = resolve_exclude_pattern(conn, pat)
                resolved += matches
                added_total += add_exclusions(conn, matches, reason=f"pattern:{pat}")
            if json_out:
                json.dump({"excluded_added": added_total,
                           "resolved": [{"fileName": m["fileName"], "name": m.get("name")}
                                        for m in resolved]}, sys.stdout, indent=2, default=str)
                sys.stdout.write("\n")
            else:
                print(f"Excluded {added_total} product(s) (marked not-owned):")
                for m in resolved:
                    print(f"  {m.get('name')}  [{m['fileName']}]")
            return 0
        if unexclude:
            removed = 0
            for pat in unexclude:
                for m in resolve_exclude_pattern(conn, pat):
                    removed += conn.execute(
                        "DELETE FROM excluded_products WHERE file_name = ?",
                        (m["fileName"],)).rowcount
            print(f"Un-excluded {removed} product(s).")
            return 0
        if list_excluded:
            rows = conn.execute(
                "SELECT file_name, name, reason, excluded_at FROM excluded_products "
                "ORDER BY file_name").fetchall()
            if json_out:
                json.dump([dict(r) for r in rows], sys.stdout, indent=2, default=str)
                sys.stdout.write("\n")
            else:
                print(f"Excluded (not-owned) products: {len(rows)}")
                for r in rows:
                    print(f"  {r['name']}  [{r['file_name']}]  ({r['reason'] or '—'})")
            return 0

        uid = _unattributed_event_id(conn)
        excluded_fns = _excluded_file_names(conn)
        # Determine candidate set codes.
        if target:
            try:
                r = sets_mod.resolve(target)
                set_codes = {c.lower() for c in r.all_codes}
            except LookupError:
                set_codes = {target.lower()}
        elif mode == "all":
            set_codes = _loose_set_codes(conn)
        else:  # from-unattributed (default)
            set_codes = _unattributed_set_codes(conn)

        products = _enumerate_products(set_codes, excluded=excluded_fns)

        # SLD (only when sld is in scope or --all). Complete drops become
        # matchable products (one per sibling fileName) folded into the same
        # coverage/conflict/apply pipeline; partials are advisory-only.
        sld_complete, sld_partial = ([], [])
        if "sld" in set_codes or mode == "all":
            sld_complete, sld_partial = _sld_status(conn, sld_threshold)
            products = products + _sld_products(conn, sld_complete)

        covered, need_map = _match_products(conn, products)
        ready, conflicted, contested = _partition_ready_conflicts(conn, covered, need_map, picks)

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
            if uid is None:
                raise SystemExit("no unattributed-backfill event to re-attribute from")
            result.update(_apply(conn, ready, uid))
            result["applied"] = True
        elif not apply:
            # dry-run: roll back any (there are none, but be explicit)
            pass

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

    print(f"Scope: {result['mode']}"
          + (f" ({result['target']})" if result["target"] else "")
          + f" — {len(result['set_codes'])} set(s)")
    print()
    print(f"READY ({len(ready)} product(s), {reattr} copies to re-attribute):")
    for p in ready:
        print(f"  {p['name']}  [{p['fileName']}]  {p['recipe_qty']} cards")
    if conflicts:
        print(f"\nCONFLICTS ({len(conflicts)} product(s) contend for shared loose cards — use --pick):")
        for p in conflicts:
            print(f"  {p['name']}  [{p['fileName']}]")
        for c in contested[:15]:
            print(f"    contested: {c['scryfall_id']} [{c['finish']}] "
                  f"demand {c['demand']} > free {c['free']}  ({', '.join(c['products'][:4])})")
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
        msg = (f"APPLIED: registered {result['registered']} deconstructed deck(s), "
               f"re-attributed {result['reattributed']} copies from unattributed.")
        if result.get("partial_ledger_moves"):
            msg += (f" ({result['partial_ledger_moves']} product(s) had some cards "
                    f"already attributed to a checklist/precon — deck row still "
                    f"registered, ledger move capped to the unattributed balance.)")
        print(msg)
    else:
        print(f"(dry-run — no writes. Re-run with --apply to register the {len(ready)} "
              f"ready product(s)." + (" Resolve conflicts with --pick." if conflicts else "") + ")")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="trueup_pools")
    parser.add_argument("target", nargs="?", default=None,
                        help="Set code/family or product-name substring to scope to.")
    parser.add_argument("--from-unattributed", action="store_true",
                        help="(default) only sets with unattributed-backfill copies.")
    parser.add_argument("--all", action="store_true", help="Every set with loose cards.")
    parser.add_argument("--apply", action="store_true", help="Write (default is dry-run).")
    parser.add_argument("--pick", default="", help="Comma-separated fileNames/slugs to claim from conflicts.")
    parser.add_argument("--sld-partial-threshold", type=float, default=0.9)
    parser.add_argument("--exclude", action="append", default=[],
                        help="Mark products NOT-owned (persistent). Pattern: fileName, "
                             "<setcode>:<type> (e.g. ltr:jumpstart), or <setcode>:<name-substr>.")
    parser.add_argument("--unexclude", action="append", default=[],
                        help="Remove products from the not-owned registry (same patterns).")
    parser.add_argument("--list-excluded", action="store_true",
                        help="List the not-owned registry and exit.")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    mode = "all" if args.all else ("target" if args.target else "from-unattributed")
    picks = {s.strip() for s in args.pick.split(",") if s.strip()}
    return run(mode=mode, target=args.target, apply=args.apply, picks=picks,
               sld_threshold=args.sld_partial_threshold, json_out=args.json,
               exclude=args.exclude, unexclude=args.unexclude,
               list_excluded=args.list_excluded)


if __name__ == "__main__":
    sys.exit(main())
