"""The browser companion — what the server knows about the extension in ``extension/``.

The extension (Manifest V3, plain readable JavaScript, no build step, no
dependencies) reads things only the user's own browser can see — their Mana Pool
cart page, their open store tabs, a Moxfield deck through their own session —
and, after the user approves in the extension's own window, hands the app the
normalized lines. Threat model: ``docs/browser-companion-security.md``.

This module is the single source of truth for the generated parts and the
artifacts the app serves:

* :func:`stores` — the Deals store list (``config/vendors.toml``) the extension
  needs at runtime; :func:`generated_files` renders ``extension/src/stores.js``
  and the manifest's ``optional_host_permissions``; ``scripts/build_extension.py
  --check`` (and a test) prove the committed files match.
* :func:`build_zip` — a byte-for-byte reproducible zip of ``extension/``.
* :func:`bookmarklet_href` — the cart bookmarklet, built from the SAME reader
  file the extension injects (``extension/src/readers/manapool-cart.js``).
* :func:`error_catalog` — every ``<area>.<reason>`` error code the companion
  path can produce, with a plain message + fix (``extension/errors.json``).
"""
from __future__ import annotations

import io
import json
import urllib.parse
import zipfile
from functools import lru_cache
from pathlib import Path

from . import vendors

EXT_DIR = Path(__file__).resolve().parents[2] / "extension"
MANIFEST = EXT_DIR / "manifest.json"
STORES_JS = EXT_DIR / "src" / "stores.js"
ERRORS = EXT_DIR / "errors.json"
CART_READER = EXT_DIR / "src" / "readers" / "manapool-cart.js"

# Hosts the extension may be granted. Install-time: only the Mana Pool site (cart
# page — never its API host). Everything else is optional and asked for at the
# moment the user switches a feature on.
MANAPOOL_HOSTS = ["https://manapool.com/*"]
MOXFIELD_HOSTS = ["https://moxfield.com/*", "https://*.moxfield.com/*"]
APP_HOSTS = ["http://localhost/*", "http://127.0.0.1/*", "https://*.ts.net/*"]

# Files that ship in the zip (everything under extension/ except these).
_EXCLUDE = {"README.md"}
_ZIP_DATE = (2024, 1, 1, 0, 0, 0)


class CompanionError(RuntimeError):
    """The extension folder is missing or inconsistent."""


def stores() -> list[dict]:
    """Every catalogued store as the extension needs it (no price patterns —
    the server applies recipes; the extension only finds tabs and reads pages)."""
    return [{"key": v.key, "name": v.name, "mode": v.mode, "hosts": list(v.hosts), "product_path": v.product_path}
            for v in vendors.catalog()]


def store_host_permissions() -> list[str]:
    """``https://<host>/*`` + ``https://*.<host>/*`` for every store host (the
    bare host and its subdomains, e.g. ``www.``)."""
    out: list[str] = []
    for s in stores():
        for h in s["hosts"]:
            out += [f"https://{h}/*", f"https://*.{h}/*"]
    return out


def _stores_js() -> str:
    body = json.dumps(stores(), indent=2)
    return ("// GENERATED from config/vendors.toml by scripts/build_extension.py — do not edit.\n"
            "// The Deals stores whose open tabs the extension may read once you switch Deals on.\n"
            f"export const STORES = {body};\n")


def generated_files() -> dict[Path, str]:
    """What the generated files must contain, keyed by path."""
    manifest = json.loads(MANIFEST.read_text())
    manifest["host_permissions"] = MANAPOOL_HOSTS
    manifest["optional_host_permissions"] = APP_HOSTS + MOXFIELD_HOSTS + store_host_permissions()
    return {MANIFEST: json.dumps(manifest, indent=2) + "\n", STORES_JS: _stores_js()}


def stale_files() -> list[Path]:
    """Generated files whose committed content differs from :func:`generated_files`."""
    return [p for p, text in generated_files().items() if not p.exists() or p.read_text() != text]


def write_generated() -> list[Path]:
    changed = stale_files()
    for p, text in generated_files().items():
        if p in changed:
            p.write_text(text)
    return changed


def manifest() -> dict:
    if not MANIFEST.exists():
        raise CompanionError(f"The extension folder is missing ({EXT_DIR}).")
    return json.loads(MANIFEST.read_text())


def version() -> str:
    return str(manifest().get("version") or "0")


def _files() -> list[Path]:
    return sorted(p for p in EXT_DIR.rglob("*")
                  if p.is_file() and p.name not in _EXCLUDE and not p.name.startswith("."))


def build_zip() -> bytes:
    """A reproducible zip of the extension: sorted entries, fixed timestamps and
    permissions, so the same source always yields the same bytes (users and
    reviewers can compare a download to the repo)."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in _files():
            info = zipfile.ZipInfo(f"magic-manager-companion/{p.relative_to(EXT_DIR).as_posix()}", _ZIP_DATE)
            info.external_attr = 0o644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, p.read_bytes())
    return buf.getvalue()


_BOOKMARKLET_TAIL = """
;(function () {
  var out = readManaPoolCart(document);
  if (!out.ok) { alert('magic-manager: ' + out.message + (out.fix ? '\\n\\n' + out.fix : '')); return; }
  var payload = JSON.stringify({ source: 'manapool-cart-page', version: %(version)s, items: out.items, warnings: out.warnings });
  var done = function () { alert('magic-manager: copied ' + out.items.length + ' cart lines (cards, quantities, finishes, prices — nothing else). Paste them into Check my Mana Pool cart.'); };
  if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(payload).then(done, function () { prompt('Copy these cart lines:', payload); });
  else prompt('Copy these cart lines:', payload);
})();
"""


def bookmarklet_source() -> str:
    """The bookmarklet's readable source: the extension's cart reader, verbatim,
    plus a few lines that copy its result to the clipboard."""
    if not CART_READER.exists():
        raise CompanionError(f"The cart reader is missing ({CART_READER}).")
    return CART_READER.read_text() + _BOOKMARKLET_TAIL % {"version": json.dumps(version())}


def bookmarklet_href() -> str:
    """``javascript:`` URL of :func:`bookmarklet_source` (newlines kept, so line
    comments in the reader stay valid)."""
    return "javascript:" + urllib.parse.quote(bookmarklet_source(), safe="")


@lru_cache(maxsize=1)
def error_catalog() -> dict[str, dict]:
    """``{code: {message, fix}}`` — the one list of companion error codes."""
    if not ERRORS.exists():
        raise CompanionError(f"The error catalog is missing ({ERRORS}).")
    return json.loads(ERRORS.read_text())["codes"]


def error(code: str, **detail) -> dict:
    """A structured error body for the API: ``{code, message, fix, ...detail}``.
    Raises ``KeyError`` for an uncatalogued code (a test keeps them in sync)."""
    e = error_catalog()[code]
    return {"code": code, "message": e["message"], "fix": e.get("fix"), **detail}
