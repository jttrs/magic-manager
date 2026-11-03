"""The shared lock / pacing / backoff library the external-API wrappers source.

Offline and Linux-portable: small bash snippets source the lib against temp
state dirs; nothing here touches a network or a real wrapper cache.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / ".claude" / "skills"
LIB = SKILLS / "_lib" / "ratelimit.sh"

WRAPPERS = [
    "scryfall-search/scryfall.sh",
    "edhrec-search/edhrec.sh",
    "commander-spellbook/spellbook.sh",
    "manapool-search/manapool.sh",
    "mtgjson-search/mtgjson.sh",
    "sealed-value/tcgcsv.sh",
    "sealed-value/tcgapi.sh",
    "sealed-value/ebay.sh",
]


def run(state, body, env_extra=None):
    """Run `body` in bash with the lib sourced and the caller's variables set."""
    script = f"""
set -euo pipefail
STATE_DIR="{state}"
LOCK_FILE="$STATE_DIR/lock"
LAST_CALL_FILE="$STATE_DIR/last_call_ms"
BACKOFF_FILE="$STATE_DIR/backoff_until"
RL_NAME=test.sh
. "{LIB}"
{body}
"""
    env = {**os.environ, **(env_extra or {})}
    return subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)


def test_check_backoff_in_future_exits_3_with_message(tmp_path):
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) + 60_000))
    r = run(tmp_path, "rl_check_backoff; echo reached")
    assert r.returncode == 3
    assert "reached" not in r.stdout
    assert r.stderr.startswith("test.sh: in backoff window after a 429, ")
    assert "s remaining. Aborting." in r.stderr
    assert (tmp_path / "backoff_until").exists()


def test_check_expired_backoff_is_removed(tmp_path):
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) - 1000))
    r = run(tmp_path, "rl_check_backoff; echo reached")
    assert r.returncode == 0, r.stderr
    assert "reached" in r.stdout
    assert not (tmp_path / "backoff_until").exists()


def test_set_backoff_then_check_blocks(tmp_path):
    r = run(tmp_path, "rl_set_backoff 35; rl_check_backoff")
    assert r.returncode == 3
    assert "test.sh: in backoff window" in r.stderr
    until = int((tmp_path / "backoff_until").read_text())
    assert 30_000 < until - int(time.time() * 1000) <= 35_000


SCRIPT_HEAD = (
    'set -euo pipefail\nSTATE_DIR="{state}"\nLOCK_FILE="$STATE_DIR/lock"\n'
    'LAST_CALL_FILE="$STATE_DIR/last_call_ms"\nBACKOFF_FILE="$STATE_DIR/backoff_until"\n'
    'RL_NAME=test.sh\n. "{lib}"\n'
)


def spawn(state, body, env_extra=None):
    env = {**os.environ, "RL_DEBUG_SLOT": "1", **(env_extra or {})}
    script = SCRIPT_HEAD.format(state=state, lib=LIB) + body
    return subprocess.Popen(["bash", "-c", script], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True, env=env)


def slot_of(stderr):
    return int(stderr.strip().splitlines()[0])


def hold_flock(state, seconds=30):
    """A python process holding the wrapper lock's flock; returns once it holds it."""
    code = (
        "import fcntl, os, sys, time\n"
        "fd = os.open(sys.argv[1], os.O_RDWR | os.O_CREAT, 0o600)\n"
        "fcntl.flock(fd, fcntl.LOCK_EX)\n"
        "print('held', flush=True)\n"
        "time.sleep(float(sys.argv[2]))\n"
    )
    p = subprocess.Popen(["python3", "-c", code, str(state / "lock.flock"), str(seconds)],
                         stdout=subprocess.PIPE, text=True)
    assert p.stdout.readline().strip() == "held"
    return p


def test_concurrent_reserves_are_spaced_but_downloads_overlap(tmp_path):
    t = time.time()
    procs = [spawn(tmp_path, "rl_reserve 300; sleep 2") for _ in range(3)]
    results = [(p.wait(), p.stderr.read()) for p in procs]
    elapsed = time.time() - t
    assert all(rc == 0 for rc, _ in results), results
    assert elapsed < 4.5  # serialized downloads would take >= 6 s
    slots = sorted(slot_of(err) for _, err in results)
    assert slots[1] - slots[0] >= 300 and slots[2] - slots[1] >= 300


def test_stress_slots_never_closer_than_gap(tmp_path):
    gap = 50
    for _ in range(10):
        procs = [spawn(tmp_path, f"rl_reserve {gap}") for _ in range(5)]
        results = [(p.wait(), p.stderr.read()) for p in procs]
        assert all(rc == 0 for rc, _ in results), results
        slots = sorted(slot_of(err) for _, err in results)
        assert all(b - a >= gap for a, b in zip(slots, slots[1:])), slots


def test_sigkilled_holder_does_not_block(tmp_path):
    holder = hold_flock(tmp_path)
    holder.kill()
    holder.wait()
    t = time.time()
    r = run(tmp_path, "rl_reserve 0; echo reached")
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 1
    assert "reached" in r.stdout


def test_live_holder_times_out_with_exit_2(tmp_path):
    holder = hold_flock(tmp_path)
    try:
        r = run(tmp_path, "rl_reserve 0; echo reached", {"RL_LOCK_TIMEOUT_MS": "300"})
    finally:
        holder.kill()
        holder.wait()
    assert r.returncode == 2
    assert r.stderr.strip() == "test.sh: lock timeout"
    assert "reached" not in r.stdout


def test_backoff_before_reserve_exits_3_with_message(tmp_path):
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) + 60_000))
    r = run(tmp_path, "rl_reserve 0; echo reached")
    assert r.returncode == 3
    assert "reached" not in r.stdout
    assert r.stderr.startswith("test.sh: in backoff window after a 429, ")
    assert r.stderr.strip().endswith("s remaining. Aborting.")
    assert (tmp_path / "backoff_until").exists()


def test_expired_backoff_is_removed_by_reserve(tmp_path):
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) - 1000))
    r = run(tmp_path, "rl_reserve 0; echo reached")
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "backoff_until").exists()


def test_backoff_written_during_sleep_stops_the_sleeper(tmp_path):
    first = spawn(tmp_path, "rl_reserve 1500")
    first.wait()
    second = spawn(tmp_path, "rl_reserve 1500; echo reached")
    time.sleep(0.5)  # second is now sleeping toward its slot
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) + 60_000))
    out, err = second.communicate(timeout=15)
    assert second.returncode == 3
    assert "reached" not in out
    assert "in backoff window after a 429" in err


def test_reserve_without_backoff_file_works(tmp_path):
    r = run(tmp_path, "unset BACKOFF_FILE; rl_reserve 0; echo reached")
    assert r.returncode == 0, r.stderr
    assert "reached" in r.stdout


def test_leftover_mkdir_lock_directory_is_ignored(tmp_path):
    (tmp_path / "lock").mkdir()
    (tmp_path / "lock" / "owner").write_text("999999 1\n")
    t = time.time()
    r = run(tmp_path, "rl_reserve 0; echo reached")
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 1
    assert (tmp_path / "lock").is_dir()  # left alone


def test_first_reserve_does_not_wait(tmp_path):
    t = time.time()
    r = run(tmp_path, "rl_reserve 5000")
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 4
    assert (tmp_path / "last_call_ms").exists()


def test_reserve_under_errexit_with_corrupt_last_call(tmp_path):
    (tmp_path / "last_call_ms").write_text("garbage")
    r = run(tmp_path, "rl_reserve 0; echo reached")
    assert r.returncode == 0, r.stderr
    assert "reached" in r.stdout


@pytest.mark.parametrize("rel", WRAPPERS)
def test_wrapper_uses_shared_lib(rel):
    text = (SKILLS / rel).read_text()
    name = rel.rsplit("/", 1)[1]
    assert f"RL_NAME={name}\n" in text
    assert '/../_lib/ratelimit.sh"' in text
    for old in ("acquire_lock() {", "pace() {", "check_backoff() {", "now_ms() {"):
        assert not any(line.startswith(old) for line in text.splitlines()), (rel, old)
    assert "rl_reserve" in text
    # The lock is held only inside rl_reserve: a wrapper must never touch it
    # (an EXIT trap rmdir-ing LOCK_FILE would delete another process's lock).
    for line in text.splitlines():
        if "trap " in line:
            assert "LOCK_FILE" not in line, (rel, line)
    for dead in ("rl_acquire_lock", "rl_release_lock", "rl_pace"):
        assert dead not in text, (rel, dead)
    r = subprocess.run(["bash", "-n", str(SKILLS / rel)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_lib_syntax_and_no_hosts():
    r = subprocess.run(["bash", "-n", str(LIB)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    text = LIB.read_text()
    assert "://" not in text  # no network, nothing for the guards to trip on
    assert "stat -f" not in text and "stat -c" not in text
