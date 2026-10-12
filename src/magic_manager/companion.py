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
TOKENS_CSS = EXT_DIR / "src" / "tokens.css"
WEB_TOKENS = EXT_DIR.parent / "web" / "tokens"
# Archivo Variable (wdth axis, latin), bundled from the web app's @fontsource-variable/archivo:
# extension pages can't load the app's CSS or anything from the internet.
FONT_FILE = "fonts/archivo-latin-wdth-normal.woff2"
_LATIN = ("U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,"
          "U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD")

# Hosts the extension may be granted. Install-time: only the Mana Pool site (cart
# page — never its API host). Everything else is optional and asked for at the
# moment the user switches a feature on.
MANAPOOL_HOSTS = ["https://manapool.com/*"]
MOXFIELD_HOSTS = ["https://moxfield.com/*", "https://*.moxfield.com/*"]
# Archidekt decks (opt-in): the deck page, read with the user's own session.
ARCHIDEKT_HOSTS = ["https://archidekt.com/*", "https://www.archidekt.com/*"]
APP_HOSTS = ["http://localhost/*", "http://127.0.0.1/*", "https://*.ts.net/*"]
# Order history (purchases): TCGplayer's account site + Card Kingdom (optional "Order history" feature).
ORDER_HOSTS = ["https://store.tcgplayer.com/*", "https://www.cardkingdom.com/*"]
# Other carts (one opt-in switch per store): each cart page's own host.
CART_HOSTS = ["https://www.tcgplayer.com/*", "https://www.cardkingdom.com/*"]

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


def _token_values(*files: str) -> dict[str, object]:
    """Flatten DTCG token files (``web/tokens``) to ``{"color.bone.100": value, …}``,
    resolving ``{a.b.c}`` references the way style-dictionary does."""
    flat: dict[str, object] = {}

    def walk(node: dict, path: tuple[str, ...]) -> None:
        if "$value" in node:
            flat[".".join(path)] = node["$value"]
            return
        for k, v in node.items():
            if not k.startswith("$") and isinstance(v, dict):
                walk(v, path + (k,))

    for f in files:
        walk(json.loads((WEB_TOKENS / f).read_text()), ())

    def resolve(v: object) -> object:
        while isinstance(v, str) and v.startswith("{") and v.endswith("}"):
            v = flat[v[1:-1]]
        return v

    return {k: resolve(v) for k, v in flat.items()}


def _tokens_css() -> str:
    """The extension's tokens: the app's semantic theme colours (light + dark by OS
    setting), its type family and width voices, and the bundled Archivo face."""
    light = _token_values("primitives.tokens.json", "light.tokens.json")
    dark = _token_values("primitives.tokens.json", "dark.tokens.json")

    def theme(vals: dict[str, object], indent: str) -> str:
        return "\n".join(f"{indent}--theme-{k[6:]}: {v};" for k, v in vals.items() if k.startswith("theme."))

    family = ", ".join(f"'{f}'" if " " in f else f for f in light["font.family.guide"])  # type: ignore[union-attr]
    ease = ", ".join(str(x) for x in light["motion.ease.out"])  # type: ignore[union-attr]
    return (
        "/* GENERATED from web/tokens/*.tokens.json by scripts/build_extension.py — do not edit. */\n"
        "@font-face {\n  font-family: 'Archivo Variable';\n  font-style: normal;\n  font-display: swap;\n"
        "  font-weight: 100 900;\n  font-stretch: 62% 125%;\n"
        f"  src: url({FONT_FILE}) format('woff2-variations');\n  unicode-range: {_LATIN};\n}}\n"
        ":root {\n  color-scheme: light dark;\n"
        f"  --font-guide: {family};\n"
        f"  --font-width-condensed: {light['font.width.condensed']};\n"
        f"  --font-width-semi: {light['font.width.semi']};\n"
        f"  --font-width-normal: {light['font.width.normal']};\n"
        f"  --ease-out: cubic-bezier({ease});\n"
        f"  --duration-base: {light['motion.duration.base']};\n"
        f"{theme(light, '  ')}\n}}\n"
        f"@media (prefers-color-scheme: dark) {{\n  :root {{\n{theme(dark, '    ')}\n  }}\n}}\n"
    )


def generated_files() -> dict[Path, str]:
    """What the generated files must contain, keyed by path."""
    manifest = json.loads(MANIFEST.read_text())
    manifest["host_permissions"] = MANAPOOL_HOSTS
    manifest["optional_host_permissions"] = list(dict.fromkeys(APP_HOSTS + MOXFIELD_HOSTS + ARCHIDEKT_HOSTS + ORDER_HOSTS + CART_HOSTS + store_host_permissions()))
    return {MANIFEST: json.dumps(manifest, indent=2) + "\n", STORES_JS: _stores_js(), TOKENS_CSS: _tokens_css()}


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
