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


def test_pace_spaces_two_calls(tmp_path):
    r = run(tmp_path, 'rl_pace 400; t1=$(rl_now_ms); rl_pace 400; t2=$(rl_now_ms); echo $((t2 - t1))')
    assert r.returncode == 0, r.stderr
    assert int(r.stdout.strip()) >= 390  # allow clock/rounding slack of a few ms
    assert (tmp_path / "last_call_ms").exists()


def test_pace_first_call_does_not_wait(tmp_path):
    t = time.time()
    r = run(tmp_path, "rl_pace 5000")
    assert r.returncode == 0, r.stderr
    assert time.time() - t < 4


def test_backoff_in_future_exits_3_with_message(tmp_path):
    (tmp_path / "backoff_until").write_text(str(int(time.time() * 1000) + 60_000))
    r = run(tmp_path, "rl_check_backoff; echo reached")
    assert r.returncode == 3
    assert "reached" not in r.stdout
    assert r.stderr.startswith("test.sh: in backoff window after a 429, ")
    assert "s remaining. Aborting." in r.stderr
    assert (tmp_path / "backoff_until").exists()


def test_expired_backoff_is_removed(tmp_path):
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


def test_lock_timeout_exits_2(tmp_path):
    (tmp_path / "lock").mkdir()
    r = run(tmp_path, "rl_acquire_lock; echo reached", {"RL_LOCK_TIMEOUT_MS": "200"})
    assert r.returncode == 2
    assert r.stderr.strip() == "test.sh: lock timeout"
    assert "reached" not in r.stdout
    assert (tmp_path / "lock").exists()  # not ours; left alone


def test_lock_released_on_exit(tmp_path):
    r = run(tmp_path, 'rl_acquire_lock; test -d "$LOCK_FILE"; echo held')
    assert r.returncode == 0, r.stderr
    assert "held" in r.stdout
    assert not (tmp_path / "lock").exists()


def test_lock_released_when_wrapper_resets_exit_trap(tmp_path):
    # The wrappers re-set the EXIT trap after pacing to also delete a tmp file.
    body = """rl_acquire_lock
tmp=$(mktemp "$STATE_DIR/body.XXXXXX")
trap "rm -f '$tmp'; rmdir '$LOCK_FILE' 2>/dev/null || true" EXIT
echo "$tmp" > "$STATE_DIR/tmpname"
"""
    r = run(tmp_path, body)
    assert r.returncode == 0, r.stderr
    assert not (tmp_path / "lock").exists()
    assert not Path((tmp_path / "tmpname").read_text().strip()).exists()


@pytest.mark.parametrize("rel", WRAPPERS)
def test_wrapper_uses_shared_lib(rel):
    text = (SKILLS / rel).read_text()
    name = rel.rsplit("/", 1)[1]
    assert f"RL_NAME={name}\n" in text
    assert '/../_lib/ratelimit.sh"' in text
    for old in ("acquire_lock() {", "pace() {", "check_backoff() {", "now_ms() {"):
        assert not any(line.startswith(old) for line in text.splitlines()), (rel, old)
    assert "rl_acquire_lock" in text and "rl_pace" in text
    r = subprocess.run(["bash", "-n", str(SKILLS / rel)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_lib_syntax_and_no_hosts():
    r = subprocess.run(["bash", "-n", str(LIB)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert "://" not in LIB.read_text()  # no network, nothing for the guards to trip on
