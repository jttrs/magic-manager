"""Migration rehearsal harness — run before merging a new MIGRATIONS entry.

Copies the live DB to a temp file, runs the schema migrations against the
copy, and asserts that the precious tables (``list_rows``, ``lists``,
``ingest_log``) still hold every row they did before.

Usage:

    uv run python -m scripts.rehearse_migration

Exit code 0 = OK. Non-zero = something diverged; the script prints which
table changed and how. The live DB is never touched.

This is intentionally NOT a pytest harness. It's a one-shot rehearsal
script that can be wired into pytest later if/when we adopt one.
"""

from __future__ import annotations

import hashlib
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


def main() -> int:
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
    src.close()

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

    # 5. Compare.
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
    print("\nOK: every precious table is byte-equivalent before and after migration.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
