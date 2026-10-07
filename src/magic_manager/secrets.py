"""Personal secrets: the shell environment first, then the macOS Keychain.

Personal credentials (your own Mana Pool login, used only to read YOUR cart) never
live in the repo's ``.env``. Store them once with ``mm secret set <NAME>`` — the
macOS ``security`` tool prompts for the value, so it never appears in a command
line, shell history or file — and read them here. Service credentials that are
not personal (e.g. a catalog API token) may still come from ``.env``.

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


def keychain_available() -> bool:
    return sys.platform == "darwin" and shutil.which("security") is not None


def keychain_get(name: str) -> str | None:
    if not keychain_available():
        return None
    r = subprocess.run(["security", "find-generic-password", "-s", SERVICE, "-a", name, "-w"],
                       capture_output=True, text=True)
    value = r.stdout.rstrip("\n") if r.returncode == 0 else ""
    return value or None


def get(name: str) -> str | None:
    """The environment variable ``name`` when set, else the Keychain item."""
    return os.environ.get(name) or keychain_get(name)


def set_interactive(name: str) -> int:
    """Store ``name`` in the Keychain; ``security`` prompts for the value (twice)."""
    if not keychain_available():
        print("The macOS Keychain isn't available here; set the value as an environment variable instead.", file=sys.stderr)
        return 2
    return subprocess.run(["security", "add-generic-password", "-U", "-s", SERVICE, "-a", name, "-w"]).returncode


def delete(name: str) -> bool:
    if not keychain_available():
        return False
    return subprocess.run(["security", "delete-generic-password", "-s", SERVICE, "-a", name],
                          capture_output=True).returncode == 0
