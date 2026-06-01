"""Migration rehearsal harness — run before merging a new MIGRATIONS entry.

Copies the live DB to a temp file, runs the schema migrations against the
copy, and asserts that the precious tables (``list_rows``, ``lists``,
``ingest_log``) still hold every row they did before.

When the rehearsal actually exercises the V4 migration (i.e. pre-version
< 4 and post-version >= 4), it ALSO verifies that V4's new tables
(``inventory``, ``wishlist_entries``, ``decks``, ``deck_cards``,
``set_targets``) were populated correctly from the V1 ``list_rows``/``lists``
data. See ``_verify_v4_population`` for the exact contract.

Usage
-----

    uv run python -m scripts.rehearse_migration [-h | --help]

This script takes no behavioral options — it always rehearses against the
current live DB at ``db/magic_manager.db`` and reports a per-table summary.
``--help`` prints this docstring and exits without touching anything.

Exit codes
----------

    0  — every precious table is byte-equivalent pre/post migration AND
         (if V4 was exercised) V4's new tables were populated correctly.
         Also 0 if there's no live DB to rehearse against (no-op).
    1  — something diverged; the script prints which table changed and how.
         The live DB is never touched even on failure.

This is intentionally NOT a pytest harness. It's a one-shot rehearsal
script that can be wired into pytest later if/when we adopt one.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

# We import the public surface — this is a behavioral test of the same
# migration runner the production code uses.
from magic_manager import db


PRECIOUS_TABLES = ("lists", "list_rows", "ingest_log")
V4_NEW_TABLES = ("inventory", "wishlist_entries", "decks", "deck_cards", "set_targets")


def _row_hashes(conn: sqlite3.Connection, table: str) -> tuple[int, str]:
    """Return (count, sha256-of-canonical-row-dump) for a table.

    We sort rows by every column (in column order) and hash the resulting
    text so the comparison is order-independent.
    """
    cur = conn.execute(f"SELECT * FROM {table}")
    cols = [d[0] for d in cur.description]
    rows = [tuple(r[c] for c in cols) for r in cur.fetchall()]
    rows.sort(key=lambda r: tuple("" if v is None else str(v) for v in r))
    h = hashlib.sha256()
    for r in rows:
        h.update("\x1f".join("" if v is None else str(v) for v in r).encode("utf-8"))
        h.update(b"\x1e")
    return len(rows), h.hexdigest()


def _verify_v4_population(
    pre_conn: sqlite3.Connection, post_conn: sqlite3.Connection
) -> tuple[bool, list[str]]:
    """Verify that V4 populated its new tables from V1 list_rows/lists data.

    Returns ``(ok, lines)`` where ``lines`` is one human-readable status
    line per V4 table (matching the OK/DIVERGED format the precious-table
    check uses).
    """
    lines: list[str] = []
    ok = True

    # --- inventory: SUM by (scryfall_id, finish) across set:* and owned:* with qty>0
    expected_inv: dict[tuple[str, str], int] = {}
    for r in pre_conn.execute(
        "SELECT scryfall_id, finish, SUM(quantity) AS q "
        "FROM list_rows "
        "WHERE quantity > 0 "
        "  AND (label LIKE 'set:%' OR label LIKE 'owned:%') "
        "GROUP BY scryfall_id, finish"
    ).fetchall():
        expected_inv[(r["scryfall_id"], r["finish"])] = int(r["q"])

    actual_inv: dict[tuple[str, str], int] = {
        (r["scryfall_id"], r["finish"]): int(r["quantity"])
        for r in post_conn.execute(
            "SELECT scryfall_id, finish, quantity FROM inventory"
        ).fetchall()
    }
    inv_ok = all(actual_inv.get(k, 0) >= v for k, v in expected_inv.items())
    # Live DB may have MORE rows than V1 list_rows (post-V4 interactive use)
    # so the contract is "every expected key is present with >= expected qty".
    status = "OK" if inv_ok else "DIVERGED"
    lines.append(
        f"  inventory       {len(expected_inv):>6} expected → {len(actual_inv):>6} present  {status}"
    )
    if not inv_ok:
        ok = False
        missing = [k for k, v in expected_inv.items() if actual_inv.get(k, 0) < v]
        lines.append(f"     missing/short: {missing[:5]}{' …' if len(missing) > 5 else ''}")

    # --- wishlist_entries: every wishlist:/buy:/idea: row with qty>0,
    #     keyed by (scryfall_id, finish, category=suffix-after-first-colon)
    expected_wl: dict[tuple[str, str, str], int] = {}
    for r in pre_conn.execute(
        "SELECT scryfall_id, finish, "
        "       SUBSTR(label, INSTR(label, ':') + 1) AS category, "
        "       quantity "
        "FROM list_rows "
        "WHERE quantity > 0 "
        "  AND (label LIKE 'wishlist:%' OR label LIKE 'buy:%' OR label LIKE 'idea:%')"
    ).fetchall():
        expected_wl[(r["scryfall_id"], r["finish"], r["category"])] = int(r["quantity"])

    actual_wl: dict[tuple[str, str, str], int] = {
        (r["scryfall_id"], r["finish"], r["category"]): int(r["qty_wanted"])
        for r in post_conn.execute(
            "SELECT scryfall_id, finish, category, qty_wanted FROM wishlist_entries"
        ).fetchall()
    }
    wl_ok = all(actual_wl.get(k, 0) >= v for k, v in expected_wl.items())
    status = "OK" if wl_ok else "DIVERGED"
    lines.append(
        f"  wishlist_entries{len(expected_wl):>6} expected → {len(actual_wl):>6} present  {status}"
    )
    if not wl_ok:
        ok = False
        missing = [k for k, v in expected_wl.items() if actual_wl.get(k, 0) < v]
        lines.append(f"     missing/short: {missing[:5]}{' …' if len(missing) > 5 else ''}")

    # --- decks: one row per deck:* label that has at least one row.
    #     deck_cards: one row per (scryfall_id, finish) qty>0 under that label,
    #     all on board='main'.
    expected_deck_slugs: set[str] = set()
    expected_deck_cards: dict[str, set[tuple[str, str]]] = {}  # slug -> {(scryfall_id, finish), ...}
    for r in pre_conn.execute(
        "SELECT DISTINCT label FROM list_rows WHERE label LIKE 'deck:%' AND quantity > 0"
    ).fetchall():
        slug = r["label"][len("deck:"):]
        if not slug:
            continue
        expected_deck_slugs.add(slug)
        expected_deck_cards[slug] = set()
    for r in pre_conn.execute(
        "SELECT label, scryfall_id, finish "
        "FROM list_rows "
        "WHERE label LIKE 'deck:%' AND quantity > 0"
    ).fetchall():
        slug = r["label"][len("deck:"):]
        if slug in expected_deck_cards:
            expected_deck_cards[slug].add((r["scryfall_id"], r["finish"]))

    actual_deck_slugs: dict[str, int] = {
        r["slug"]: int(r["deck_id"])
        for r in post_conn.execute("SELECT slug, deck_id FROM decks").fetchall()
    }
    decks_ok = expected_deck_slugs.issubset(actual_deck_slugs.keys())
    status = "OK" if decks_ok else "DIVERGED"
    lines.append(
        f"  decks           {len(expected_deck_slugs):>6} expected → {len(actual_deck_slugs):>6} present  {status}"
    )
    if not decks_ok:
        ok = False
        missing = sorted(expected_deck_slugs - set(actual_deck_slugs.keys()))
        lines.append(f"     missing slugs: {missing[:5]}{' …' if len(missing) > 5 else ''}")

    # deck_cards: count expected vs present, and verify each expected pair exists on main board.
    total_expected_cards = sum(len(v) for v in expected_deck_cards.values())
    cards_ok = True
    missing_pairs: list[tuple[str, str, str]] = []
    for slug, pairs in expected_deck_cards.items():
        deck_id = actual_deck_slugs.get(slug)
        if deck_id is None:
            cards_ok = False
            missing_pairs.extend((slug, p[0], p[1]) for p in pairs)
            continue
        present = {
            (r["scryfall_id"], r["finish"])
            for r in post_conn.execute(
                "SELECT scryfall_id, finish FROM deck_cards "
                "WHERE deck_id = ? AND board = 'main'",
                (deck_id,),
            ).fetchall()
        }
        for p in pairs:
            if p not in present:
                cards_ok = False
                missing_pairs.append((slug, p[0], p[1]))
    actual_card_count = post_conn.execute("SELECT COUNT(*) AS c FROM deck_cards").fetchone()["c"]
    status = "OK" if cards_ok else "DIVERGED"
    lines.append(
        f"  deck_cards      {total_expected_cards:>6} expected → {actual_card_count:>6} present  {status}"
    )
    if not cards_ok:
        ok = False
        lines.append(f"     missing pairs: {missing_pairs[:5]}{' …' if len(missing_pairs) > 5 else ''}")

    # --- set_targets: one row per set:* label that exists in V1 lists,
    #     regardless of whether any row has qty>0. related_codes = JSON [anchor].
    expected_targets: dict[str, str] = {}  # anchor -> related_codes JSON
    for r in pre_conn.execute(
        "SELECT label FROM lists WHERE label LIKE 'set:%'"
    ).fetchall():
        anchor = r["label"][len("set:"):].lower()
        if not anchor:
            continue
        expected_targets[anchor] = json.dumps([anchor])

    actual_targets: dict[str, str] = {
        r["anchor_code"]: r["related_codes"]
        for r in post_conn.execute(
            "SELECT anchor_code, related_codes FROM set_targets"
        ).fetchall()
    }
    targets_ok = all(
        anchor in actual_targets and actual_targets[anchor] == related
        for anchor, related in expected_targets.items()
    )
    status = "OK" if targets_ok else "DIVERGED"
    lines.append(
        f"  set_targets     {len(expected_targets):>6} expected → {len(actual_targets):>6} present  {status}"
    )
    if not targets_ok:
        ok = False
        bad = [
            (a, expected_targets[a], actual_targets.get(a))
            for a in expected_targets
            if actual_targets.get(a) != expected_targets[a]
        ]
        lines.append(f"     mismatches: {bad[:3]}{' …' if len(bad) > 3 else ''}")

    return ok, lines


def main(argv: list[str] | None = None) -> int:
    # Tiny argparse just for --help / -h. The rehearsal itself takes no
    # arguments — it operates on the live DB at db.db_path() unconditionally.
    parser = argparse.ArgumentParser(
        prog="rehearse_migration",
        description=(
            "Rehearse the schema migrations against a copy of the live DB and "
            "verify that precious tables are byte-equivalent before and after. "
            "Run this before shipping a new MIGRATIONS entry."
        ),
        epilog=(
            "Usage:\n"
            "  uv run python -m scripts.rehearse_migration\n\n"
            "Exit codes:\n"
            "  0  every precious table preserved (and V4-new tables populated, "
            "if the V4 migration was exercised)\n"
            "  1  something diverged; per-table report on stdout, error on stderr\n\n"
            "The live DB is never touched."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.parse_args(argv)

    live = db.db_path()
    if not live.exists():
        print(f"(no live DB at {live} — nothing to rehearse against)", file=sys.stderr)
        return 0

    # 1. Snapshot the precious tables BEFORE migration, reading the live DB
    #    directly (don't go through db.connect — that would run migrations).
    src = sqlite3.connect(str(live))
    src.row_factory = sqlite3.Row
    pre: dict[str, tuple[int, str]] = {}
    for t in PRECIOUS_TABLES:
        try:
            pre[t] = _row_hashes(src, t)
        except sqlite3.OperationalError:
            # Table doesn't exist yet — that's fine, just record absence.
            pre[t] = (0, "<absent>")
    pre_version_row = src.execute("SELECT version FROM schema_version").fetchone()
    pre_version = pre_version_row["version"] if pre_version_row else 0

    # 2. Copy live DB to a temp location and point MAGIC_MANAGER_DB at it.
    with tempfile.TemporaryDirectory(prefix="mm-rehearsal-") as tmp:
        copy_path = Path(tmp) / "magic_manager.db"
        shutil.copy2(live, copy_path)
        os.environ["MAGIC_MANAGER_DB"] = str(copy_path)

        # Force the module to re-resolve db_path() if it cached anything.
        # In our codebase db_path() reads the env on every call, so this is a no-op
        # in practice, but it's defensive.
        assert db.db_path() == copy_path, f"env override didn't stick: {db.db_path()} != {copy_path}"

        # 3. Run migrations by opening the copy through db.connect().
        with db.connect() as conn:
            cur = conn.execute("SELECT version FROM schema_version")
            row = cur.fetchone()
            post_version = row["version"] if row else 0

            # 4. Hash precious tables AFTER migration.
            post: dict[str, tuple[int, str]] = {}
            for t in PRECIOUS_TABLES:
                try:
                    post[t] = _row_hashes(conn, t)
                except sqlite3.OperationalError:
                    post[t] = (0, "<absent>")

            # 5. V4 population check — only meaningful when the migration
            #    actually ran on this rehearsal.
            v4_ok: bool | None = None
            v4_lines: list[str] = []
            if post_version >= 4 and pre_version < 4:
                v4_ok, v4_lines = _verify_v4_population(src, conn)

    src.close()

    # 6. Compare precious tables.
    print(f"schema_version: {pre_version} → {post_version}")
    fail = False
    for t in PRECIOUS_TABLES:
        n_pre, h_pre = pre[t]
        n_post, h_post = post[t]
        status = "OK" if (n_pre == n_post and h_pre == h_post) else "DIVERGED"
        if status != "OK":
            fail = True
        print(f"  {t:14}  {n_pre:>6} rows → {n_post:>6} rows  {status}")
        if status == "DIVERGED":
            print(f"     pre  hash: {h_pre}")
            print(f"     post hash: {h_post}")

    if fail:
        print("\nFAIL: precious-table contents diverged across migration.", file=sys.stderr)
        return 1

    # 7. V4 population block.
    print()
    if v4_ok is None:
        print("(V4 migration not exercised this rehearsal)")
    else:
        print("V4 population check:")
        for line in v4_lines:
            print(line)
        if not v4_ok:
            print("\nFAIL: V4 migration did not populate new tables as expected.", file=sys.stderr)
            return 1
        print("\nOK: V4 migration populated all new tables correctly.")
        return 0

    print("\nOK: every precious table is byte-equivalent before and after migration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())  # accept argv from sys.argv via argparse default
