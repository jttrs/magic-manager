"""Personal secrets: the macOS Keychain first for the personal login, else the environment.

Personal credentials (your own Mana Pool login, used only to read YOUR cart) never
live in the repo's ``.env``. Store them once with ``mm secret set <NAME>`` — the
macOS ``security`` tool prompts for the value, so it never appears in a command
line, shell history or file — and read them here. Service credentials that are
not personal (e.g. a catalog API token) may still come from ``.env``.

Your personal login (``PERSONAL``) prefers the Keychain, falling back to the environment: its
email shares a name with the service-account email the catalog API may export, which must not
shadow it. Any other name is environment first, then Keychain.

Keychain items: generic passwords, service ``magic-manager``, account = the name.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

SERVICE = "magic-manager"

# Your own Mana Pool login — used only to read your cart, never from .env.
PERSONAL = ("MANAPOOL_EMAIL", "MANAPOOL_PASSWORD")

TIMEOUT_S = 10
# `set` is interactive: security waits for you to type the value, so allow time.
SET_TIMEOUT_S = 120


def keychain_available() -> bool:
    return sys.platform == "darwin" and shutil.which("security") is not None


def keychain_get(name: str) -> str | None:
    if not keychain_available():
        return None
    try:
        r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
                           capture_output=True, text=True, timeout=TIMEOUT_S)
    except (subprocess.TimeoutExpired, OSError):
        return None
    value = r.stdout.rstrip("\n") if r.returncode == 0 else ""
    return value or None


def get(name: str) -> str | None:
    """Personal names: the Keychain item, else the environment. Others: environment, else Keychain."""
    if name in PERSONAL:
        return keychain_get(name) or os.environ.get(name)
    return os.environ.get(name) or keychain_get(name)


def set_interactive(name: str) -> int:
    """Store ``name`` in the Keychain; ``security`` prompts for the value (twice)."""
    if not keychain_available():
        print("The macOS Keychain isn't available here; set the value as an environment variable instead.", file=sys.stderr)
        return 2
    try:
        return subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE, "-a", name, "-w"],
                              timeout=SET_TIMEOUT_S).returncode
    except (subprocess.TimeoutExpired, OSError):
        print("Couldn't reach the macOS Keychain (timed out or `security` failed to run).", file=sys.stderr)
        return 1


def delete(name: str) -> bool:
    if not keychain_available():
        return False
    try:
        return subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", name],
                              capture_output=True, timeout=TIMEOUT_S).returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        print("Couldn't reach the macOS Keychain (timed out or `security` failed to run).", file=sys.stderr)
        return False
