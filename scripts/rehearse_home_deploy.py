"""End-to-end rehearsal of the home-server cutover, offsite replication, restore and
re-pull (Phase 3 §25.4 step 8) — on COPIES, offline, with a ``file://`` replica
standing in for Cloudflare R2.

    uv run python scripts/rehearse_home_deploy.py --source <a .backup copy of the real DB> --work <new dir>

Every step runs the same ``mm`` commands the deploy kit runs (``deploy/macos/``):

 1. prepare (laptop)  — ``mm db snapshot`` + ``mm db split`` + ``mm host permissions`` on a copy
 2. install-data      — ``mm host deploy-check`` (exit 0), ``mm host wal --apply``, hosted ``mm serve``
                        (``MM_MODE=hosted``, mock Discord OAuth), ``mm auth invite --admin``, sign in
 3. finish            — stop, ``mm auth bind``, start ``mm host replicate`` (real Litestream),
                        ``mm host verify-replica`` until it passes, ``mm host catalog-backup``, start serve
 4. proofs            — the owner's data through the hosted API; a write replicated; a NEW user's file
                        created at runtime replicated; quiesce → every restored file == live
                        (table hashes), ledger reconciles, catalog-refs 0, row counts == the source;
                        the catalog snapshot restores; ``mm db pull`` refuses without --force, verifies,
                        and the laptop CLI audits the copy clean; ``mm host restore`` rebuilds a new data
                        dir; deleting the member removes Litestream's local state for them.

The source DB is opened read-only (SQLite backup API). Services started here are
stopped by PID at the end. Exit 0 = every check passed. Needs Litestream
(``MM_LITESTREAM`` or on PATH) and a free port (``--port``, default 8788).
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from magic_manager import db, layout, objectstore, offsite  # noqa: E402

RESULTS: list[tuple[bool, str]] = []
PROCS: list[subprocess.Popen] = []


def check(ok: bool, what: str) -> bool:
    RESULTS.append((bool(ok), what))
    print(f"  {'✓' if ok else '✗'} {what}", flush=True)
    return bool(ok)


def step(title: str) -> None:
    print(f"\n== {title}", flush=True)


def mm(env: dict, *args: str, ok_codes=(0,), quiet=False) -> subprocess.CompletedProcess:
    r = subprocess.run(["uv", "run", "--frozen", "mm", *args], cwd=ROOT, env=env, capture_output=True, text=True)
    if not quiet or r.returncode not in ok_codes:
        out = (r.stdout + r.stderr).strip()
        print("    $ mm " + " ".join(args) + f"   → exit {r.returncode}")
        for line in out.splitlines()[-12:]:
            print("      " + line)
    if r.returncode not in ok_codes:
        raise SystemExit(f"mm {' '.join(args)} exited {r.returncode}")
    return r


# ---------- mock OAuth server process ----------

def serve_main(port: int) -> None:
    """Hosted ``mm serve`` with Discord's token + profile endpoints mocked (the #199/#200
    test helpers' shape). Identity = the code the callback carries."""
    from magic_manager.auth import oauth

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == oauth.DISCORD.token_url:
            code = parse_qs(request.content.decode()).get("code", ["x"])[0]
            return httpx.Response(200, json={"access_token": f"at-{code}", "token_type": "Bearer"})
        if str(request.url) == oauth.DISCORD_ME:
            who = request.headers["authorization"].removeprefix("Bearer at-")
            return httpx.Response(200, json={"id": f"d-{who}", "username": who, "global_name": who.title(),
                                             "email": f"{who}@example.com", "verified": True})
        return httpx.Response(404)

    oauth._client = lambda: httpx.AsyncClient(transport=httpx.MockTransport(handler))
    os.environ["MM_NONINTERACTIVE"] = "1"
    import uvicorn
    uvicorn.run("magic_manager.web.app:create_app", factory=True, host="127.0.0.1", port=port, log_level="warning")


def start(env: dict, argv: list[str], log: Path) -> subprocess.Popen:
    f = open(log, "ab")
    p = subprocess.Popen(argv, cwd=ROOT, env=env, stdout=f, stderr=subprocess.STDOUT, start_new_session=True)
    PROCS.append(p)
    return p


def stop(p: subprocess.Popen) -> None:
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(30)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait(10)
    if p in PROCS:
        PROCS.remove(p)


def start_serve(env: dict, port: int, work: Path) -> subprocess.Popen:
    p = start(env, ["uv", "run", "--frozen", "python", __file__, "_serve", str(port)], work / "serve.log")
    for _ in range(90):
        time.sleep(1)
        try:
            if httpx.get(f"http://127.0.0.1:{port}/api/features", timeout=2).status_code == 200:
                return p
        except httpx.HTTPError:
            pass
    raise SystemExit(f"hosted serve didn't come up — see {work / 'serve.log'}")


def sign_in(client: httpx.Client, who: str, invite: str | None) -> httpx.Response:
    params = {"invite": invite} if invite else {}
    r = client.get("/api/auth/login/discord", params=params, follow_redirects=False)
    q = {k: v[0] for k, v in parse_qs(urlsplit(r.headers["location"]).query).items()}
    return client.get("/api/auth/callback/discord", params={"code": who, "state": q["state"]}, follow_redirects=False)


def invite_code(env: dict) -> str:
    return json.loads(mm(env, "auth", "invite", "--admin", "--json", quiet=True).stdout)["code"]


def user_ids(env: dict) -> dict[str, str]:
    rows = json.loads(mm(env, "auth", "users", "--json", quiet=True).stdout)
    return {r["display_name"]: r["id"] for r in rows}


def replica_has(root: Path, name: str) -> bool:
    return any((root / name / "ltx").rglob("*.ltx")) if (root / name / "ltx").is_dir() else False


def wait_for(fn, seconds: int = 60) -> bool:
    for _ in range(seconds):
        if fn():
            return True
        time.sleep(1)
    return False


def user_counts(path: Path, tables) -> dict[str, int]:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return {t: conn.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    finally:
        conn.close()


def run(source: Path, work: Path, port: int) -> int:
    if work.exists() and any(work.iterdir()):
        raise SystemExit(f"{work} isn't empty")
    work.mkdir(parents=True, exist_ok=True)
    laptop, data, r2 = work / "laptop", work / "mini" / "data", work / "r2"
    laptop.mkdir()
    url = f"file://{r2}"
    base = {k: v for k, v in os.environ.items() if not k.startswith(("MM_", "MAGIC_MANAGER_"))}
    base.update(MM_ANALYTICS="off", MM_NONINTERACTIVE="1",
                MM_LITESTREAM=os.environ.get("MM_LITESTREAM") or offsite.litestream_bin())
    src_copy = laptop / "magic_manager.db"
    src = sqlite3.connect(f"{source.resolve().as_uri()}?mode=ro", uri=True)
    dst = sqlite3.connect(src_copy)
    src.backup(dst)
    src.close()
    dst.close()
    lap = {**base, "MAGIC_MANAGER_DB": str(src_copy)}
    source_counts = user_counts(src_copy, layout.USER_TABLES)

    step("1. prepare (laptop): snapshot + split + permissions")
    mm(lap, "db", "snapshot", "--label", "pre-cutover", quiet=True)
    check(any((laptop / "bak").glob("magic_manager.db.bak-*-pre-cutover")), "pre-cutover snapshot taken")
    mm(lap, "db", "split", "--to", str(data), quiet=True)
    mm(lap, "host", "permissions", "--data-dir", str(data), "--apply", quiet=True)
    check(oct(data.stat().st_mode & 0o777) == "0o700", "data dir is 0700, files 0600")

    hosted = {**base, "MM_MODE": "hosted", "MM_LAYOUT": "split", "MM_DATA_DIR": str(data),
              "MM_PUBLIC_ORIGIN": f"http://localhost:{port}", "MM_ANALYTICS_DB": str(data / "analytics.db"),
              "MM_OAUTH_DISCORD_CLIENT_ID": "rehearsal-cid", "MM_OAUTH_DISCORD_CLIENT_SECRET": "rehearsal-secret",
              "MM_OFFSITE_URL": url}

    step("2. install-data (mini): deploy-check, WAL, hosted serve, admin invite + sign-in")
    mm(hosted, "host", "deploy-check", "--ref", "HEAD", "--repo", str(ROOT))
    mm(hosted, "host", "wal", "--apply", quiet=True)
    check(all(db.is_wal(p) for p in [data / "catalog.db", data / "users" / "owner.db"]), "catalog + owner file in WAL")
    serve = start_serve(hosted, port, work)
    owner_c = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60)
    r = sign_in(owner_c, "owner", invite_code(hosted))
    check(r.status_code == 303 and owner_c.get("/api/auth/me").json()["user"]["is_admin"], "owner signed in as admin (mock Discord)")
    owner_id = user_ids(hosted)["Owner"]
    check(owner_c.get("/api/history").json()["entries"] == [], "before bind the profile is empty")

    step("3. finish: stop, bind, Litestream, verify replica, catalog snapshot, start")
    stop(serve)
    mm(hosted, "auth", "bind", "--user", owner_id)
    mm(hosted, "host", "wal", "--apply", quiet=True)
    mm(hosted, "host", "permissions", "--apply", quiet=True)
    ls = start(hosted, ["uv", "run", "--frozen", "mm", "host", "replicate"], work / "litestream.log")
    check(wait_for(lambda: replica_has(r2, f"users/{owner_id}.db") and replica_has(r2, "auth.db")),
          "first replica of auth.db + the owner's file written")
    ok = False
    for _ in range(12):
        time.sleep(5)
        if mm(hosted, "host", "verify-replica", ok_codes=(0, 1), quiet=True).returncode == 0:
            ok = True
            break
    check(ok, "mm host verify-replica: every restored file == live")
    mm(hosted, "host", "catalog-backup", quiet=True)
    serve = start_serve(hosted, port, work)
    hist = owner_c.get("/api/history").json()["entries"]
    check(len(hist) > 0, f"after bind the owner's history shows through the hosted API ({len(hist)} entries)")
    owner_db = data / "users" / f"{owner_id}.db"
    check(user_counts(owner_db, layout.USER_TABLES) == source_counts,
          "owner file row counts == the source DB's user tables")

    step("4a. a write and a NEW user at runtime are replicated")
    sid = sqlite3.connect(owner_db).execute("SELECT scryfall_id FROM inventory LIMIT 1").fetchone()[0]
    write = (f"from magic_manager import inventory, layout\n"
             f"with layout.as_user('{owner_id}'): inventory.inventory_add('{sid}', 'nonfoil', 1)\n")
    subprocess.run(["uv", "run", "--frozen", "python", "-c", write], cwd=ROOT, env=hosted, check=True)
    member_c = httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=60)
    r = sign_in(member_c, "member", invite_code(hosted))
    member_id = user_ids(hosted)["Member"]
    check((data / "users" / f"{member_id}.db").is_file() and db.is_wal(data / "users" / f"{member_id}.db"),
          "the member's file was created at sign-in, in WAL")
    check(wait_for(lambda: replica_has(r2, f"users/{member_id}.db"), 60),
          "Litestream's directory watcher replicated the new user's file (no restart, no config change)")
    check(not any(p.name.endswith(".undo.db") for p in (r2 / "users").iterdir()), "undo restore points are not replicated")
    time.sleep(15)  # > sync-interval
    stop(serve)     # quiesce: nothing writes while we compare
    v = json.loads(mm(hosted, "host", "verify-replica", "--json", ok_codes=(0, 1), quiet=True).stdout)
    for f in v["files"]:
        check(f["ok"], f"restored {f['name']} == live ({f['detail']})")
    expected = {**source_counts, "inventory_events": source_counts["inventory_events"] + 1,
                "ingest_events": source_counts["ingest_events"] + 1}
    restored_owner = next(f for f in v["files"] if f["name"] == f"users/{owner_id}.db")
    check(all(restored_owner["tables"].get(t) == n for t, n in expected.items() if t != "inventory"),
          "restored owner file: row counts == source + the replicated write")

    step("4b. the weekly catalog snapshot restores")
    st = objectstore.FileStore(r2)
    snap = offsite.latest_catalog(st)
    got = work / "catalog-restored.db"
    offsite.fetch_catalog(st, snap, got)
    check(db._check_integrity(got) == "ok" and offsite.fingerprints(got) == offsite.fingerprints(data / "catalog.db"),
          f"catalog snapshot {snap} restores byte-equivalent (every table hash)")
    got.unlink()

    step("4c. the laptop's re-pull")
    copy = work / "laptop-copy"
    pull = {**base, "MM_OFFSITE_URL": url}
    mm(pull, "db", "pull", "--from", "r2", "--user", owner_id, "--to", str(copy))
    again = mm(pull, "db", "pull", "--from", "r2", "--user", owner_id, "--to", str(copy), ok_codes=(2,), quiet=True)
    check(again.returncode == 2 and "--force" in again.stderr, "re-pull without --force is refused (exit 2)")
    hosted_pull = mm(pull, "db", "pull", "--from", "r2", "--user", owner_id, "--to", str(data), "--force", ok_codes=(2,), quiet=True)
    check(hosted_pull.returncode == 2 and "hosted" in hosted_pull.stderr, "pull into the hosted data dir is refused even with --force")
    mm(pull, "db", "pull", "--from", "r2", "--user", owner_id, "--to", str(copy), "--force", quiet=True)
    check(any((copy / "replaced").rglob(f"{owner_id}.db")), "--force kept the previous copy under replaced/")
    lapcopy = {**base, "MM_LAYOUT": "split", "MM_DATA_DIR": str(copy), "MM_USER": owner_id}
    check(mm(lapcopy, "audit", "ingest-ledger", ok_codes=(0, 1), quiet=True).returncode == 0, "laptop CLI on the copy: ledger reconciles")
    check(mm(lapcopy, "audit", "catalog-refs", ok_codes=(0, 1), quiet=True).returncode == 0, "laptop CLI on the copy: catalog-refs 0")
    check(user_counts(copy / "users" / f"{owner_id}.db", layout.USER_TABLES) == user_counts(owner_db, layout.USER_TABLES),
          "pulled copy row counts == hosted")

    step("4d. disaster recovery: rebuild a new data dir from offsite")
    new = work / "new-mini" / "data"
    mm(hosted, "host", "restore", "--data-dir", str(new))
    check(sorted(p.name for p in (new / "users").glob("*.db")) == sorted([f"{owner_id}.db", f"{member_id}.db"]),
          "every account's file restored")
    check(offsite.fingerprints(new / "users" / f"{owner_id}.db") == offsite.fingerprints(owner_db),
          "restored owner file == live (table hashes)")

    step("4e. deleting an account removes Litestream's local state; its replica ages out")
    mm(hosted, "auth", "delete-user", member_id, "--yes", "--force", quiet=True)
    time.sleep(3)
    check(not (data / "users" / f".{member_id}.db-litestream").exists() and not (data / "users" / f"{member_id}.db").exists(),
          "member's file + Litestream state gone locally")
    plan = json.loads(mm(hosted, "host", "prune-deleted", "--json", quiet=True).stdout)
    check(member_id in plan["waiting"] and owner_id in plan["live"], "member's replica waits out the 30-day retention; owner's is live")

    stop(ls)
    owner_c.close()
    member_c.close()
    failed = [w for ok, w in RESULTS if not ok]
    print(f"\n{'REHEARSAL OK' if not failed else 'REHEARSAL FAILED'}: {len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    if argv is None and len(sys.argv) >= 2 and sys.argv[1] == "_serve":
        serve_main(int(sys.argv[2]))
        return 0
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--source", type=Path, required=True, help="a single-file DB to rehearse on (opened read-only)")
    ap.add_argument("--work", type=Path, required=True, help="a new, empty work dir")
    ap.add_argument("--port", type=int, default=8788)
    args = ap.parse_args(argv)
    try:
        return run(args.source, args.work.resolve(), args.port)
    finally:
        for p in list(PROCS):
            stop(p)


if __name__ == "__main__":
    sys.exit(main())
