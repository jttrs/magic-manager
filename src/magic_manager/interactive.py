"""The one rule for anything that waits on a human (prompts, REPLs, "press Enter").

Every command must run with flags and no terminal: agents (Copilot/Claude) and
the web app's job runner have no TTY and can't answer a prompt. A prompt is only
a convenience for a person at a terminal; consent stays explicit through a flag
(``--yes``, ``--apply``, ``--zero-untouched/--no-zero-untouched`` …).

Off a terminal, when the flag wasn't given, these helpers FAIL FAST: a stderr
message naming the flag and exit code ``EXIT_NEEDS_FLAG`` — never block on
stdin, never "Aborted." with a success-looking exit. Engine/API code never
prompts; it takes the choice as a parameter.

Framework-free on purpose (plain ``SystemExit``) so argparse scripts in
``scripts/`` use the same rule as the typer CLI.
"""

from __future__ import annotations

import os
import sys

EXIT_NEEDS_FLAG = 2

# Set MM_NONINTERACTIVE=1 to make a terminal session behave like an agent
# (handy for testing a command the way the app/agents will run it).
_FORCE_OFF = "MM_NONINTERACTIVE"


def is_interactive() -> bool:
    """True only when a person can answer: stdin is a terminal (and not forced off)."""
    if os.environ.get(_FORCE_OFF, "").strip() not in ("", "0"):
        return False
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def needs_flag(what: str, flag: str, *, hint: str | None = None) -> SystemExit:
    """Print why we stopped and return the ``SystemExit`` to raise."""
    msg = f"error: {what} needs an answer, and there's no terminal to ask on. Pass {flag}."
    if hint:
        msg += f" {hint}"
    print(msg, file=sys.stderr)
    return SystemExit(EXIT_NEEDS_FLAG)


def confirm(question: str, *, flag: str, default: bool = False) -> bool:
    """Ask a yes/no question on a terminal; off a terminal, fail fast naming ``flag``.

    Use for confirm-to-proceed (``flag="--yes"``) — the caller skips this when
    the flag was given — and for tri-state choices (``flag="--x/--no-x"``)."""
    if not is_interactive():
        raise needs_flag(f"{question!r}", flag)
    import typer
    return typer.confirm(question, default=default)


def require_terminal(what: str, *, alternative: str) -> None:
    """Refuse an inherently human flow (a REPL, a manual browser login) off a
    terminal, naming the non-interactive ``alternative``."""
    if not is_interactive():
        print(f"error: {what} needs a person at a terminal. {alternative}", file=sys.stderr)
        raise SystemExit(EXIT_NEEDS_FLAG)


def wait_for_enter(message: str, *, alternative: str) -> None:
    """Show ``message`` and wait for Enter from the person at the terminal.

    Reads stdin when it is a terminal, else the controlling terminal
    (``/dev/tty``) — a script whose stdin carries data (``moxfield_push.py``)
    can still ask its human. With neither, fail fast naming ``alternative``."""
    print(message, file=sys.stderr, flush=True)
    if is_interactive():
        input()
        return
    if os.environ.get(_FORCE_OFF, "").strip() in ("", "0"):
        try:
            with open("/dev/tty") as tty:
                tty.readline()
            return
        except OSError:
            pass
    print(f"error: no terminal to wait on. {alternative}", file=sys.stderr)
    raise SystemExit(EXIT_NEEDS_FLAG)


def can_wait_for_enter() -> bool:
    """Whether ``wait_for_enter`` could reach a person (stdin or ``/dev/tty``)."""
    if is_interactive():
        return True
    if os.environ.get(_FORCE_OFF, "").strip() not in ("", "0"):
        return False
    try:
        with open("/dev/tty"):
            return True
    except OSError:
        return False
