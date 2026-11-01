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
* :func:`icon_png` — the toolbar/store icons (``extension/icons/``), rasterized
  here from the app's favicon shapes, so they're generated and checked too.
* :func:`store_url` / :func:`bump_version` — Chrome Web Store distribution
  (listing + release: ``extension/store/``, ``docs/browser-companion.md``).
"""
from __future__ import annotations

import io
import json
import os
import re
import struct
import tomllib
import urllib.parse
import zipfile
import zlib
from functools import lru_cache
from pathlib import Path

from . import vendors

EXT_DIR = Path(__file__).resolve().parents[2] / "extension"
MANIFEST = EXT_DIR / "manifest.json"
STORES_JS = EXT_DIR / "src" / "stores.js"
ERRORS = EXT_DIR / "errors.json"
CART_READER = EXT_DIR / "src" / "readers" / "manapool-cart.js"
TOKENS_CSS = EXT_DIR / "src" / "tokens.css"
ICONS_DIR = EXT_DIR / "icons"
ICON_SIZES = (16, 32, 48, 128)
# Store listing assets + metadata — kept beside the extension, never shipped in the zip.
STORE_DIR = EXT_DIR / "store"
STORE_TOML = STORE_DIR / "store.toml"
STORE_URL_ENV = "MM_COMPANION_STORE_URL"
STORE_URL_PREFIX = "https://chromewebstore.google.com/detail/"
# The public privacy policy the store listing (and the setup dialog) links to.
PRIVACY_URL = "https://github.com/jttrs/magic-manager/blob/main/docs/privacy-companion.md"
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

# Files that ship in the zip (everything under extension/ except these names and folders).
_EXCLUDE = {"README.md"}
_EXCLUDE_DIRS = {"store"}
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


# ---------- icons ----------

# The app's favicon (web/public/favicon.svg) on a 32-unit grid: a dark tile, a bone
# card, an amber band. (x, y, w, h, radius, rgba)
_ICON_SHAPES = (
    (0, 0, 32, 32, 4, (0x16, 0x13, 0x0E, 255)),
    (9, 6, 14, 20, 1.5, (0xEF, 0xE7, 0xD6, 255)),
    (7, 17, 18, 4, 1, (0xF0, 0xA5, 0x31, 217)),
)
_SUPERSAMPLE = 4


def _inside(x: float, y: float, rx: float, ry: float, w: float, h: float, r: float) -> bool:
    if not (rx <= x < rx + w and ry <= y < ry + h):
        return False
    cx = min(max(x, rx + r), rx + w - r)
    cy = min(max(y, ry + r), ry + h - r)
    return (x - cx) ** 2 + (y - cy) ** 2 <= r * r


def _png(size: int, rows: list[bytes]) -> bytes:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b"".join(b"\x00" + r for r in rows)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


@lru_cache(maxsize=None)
def icon_png(size: int) -> bytes:
    """The companion icon as an RGBA PNG, ``size`` px square, deterministic bytes.
    At 128 px the art is 96 px with 16 px of transparent padding (Chrome Web Store's
    icon guideline); smaller sizes fill the square."""
    pad = 16 if size >= 128 else 0
    scale = (size - 2 * pad) / 32
    n = _SUPERSAMPLE
    rows: list[bytes] = []
    for py in range(size):
        row = bytearray()
        for px in range(size):
            acc = [0.0, 0.0, 0.0, 0.0]  # premultiplied rgb + alpha
            for sy in range(n):
                for sx in range(n):
                    x = (px + (sx + 0.5) / n - pad) / scale
                    y = (py + (sy + 0.5) / n - pad) / scale
                    r = g = b = a = 0.0
                    for (rx, ry, w, h, rad, (cr, cg, cb, ca)) in _ICON_SHAPES:
                        if _inside(x, y, rx, ry, w, h, rad):
                            al = ca / 255
                            r, g, b = cr * al + r * (1 - al), cg * al + g * (1 - al), cb * al + b * (1 - al)
                            a = al + a * (1 - al)
                    acc[0] += r; acc[1] += g; acc[2] += b; acc[3] += a
            k = n * n
            a = acc[3] / k
            if a <= 0:
                row += b"\x00\x00\x00\x00"
            else:
                row += bytes(min(255, round(c / k / a)) for c in acc[:3]) + bytes([round(a * 255)])
        rows.append(bytes(row))
    return _png(size, rows)


def _icon_paths() -> dict[int, str]:
    return {s: f"icons/icon-{s}.png" for s in ICON_SIZES}


# ---------- generated files ----------

def generated_files() -> dict[Path, str | bytes]:
    """What the generated files must contain, keyed by path (text, or bytes for icons)."""
    manifest = json.loads(MANIFEST.read_text())
    manifest["host_permissions"] = MANAPOOL_HOSTS
    manifest["optional_host_permissions"] = list(dict.fromkeys(APP_HOSTS + MOXFIELD_HOSTS + ARCHIDEKT_HOSTS + ORDER_HOSTS + CART_HOSTS + store_host_permissions()))
    icons = {str(s): p for s, p in _icon_paths().items()}
    manifest["icons"] = icons
    manifest.setdefault("action", {})["default_icon"] = {k: v for k, v in icons.items() if int(k) <= 48}
    out: dict[Path, str | bytes] = {MANIFEST: json.dumps(manifest, indent=2) + "\n", STORES_JS: _stores_js(), TOKENS_CSS: _tokens_css()}
    for s, rel in _icon_paths().items():
        out[EXT_DIR / rel] = icon_png(s)
    return out


def _current(p: Path, want: str | bytes) -> bool:
    if not p.exists():
        return False
    return (p.read_bytes() if isinstance(want, bytes) else p.read_text()) == want


def stale_files() -> list[Path]:
    """Generated files whose committed content differs from :func:`generated_files`."""
    return [p for p, want in generated_files().items() if not _current(p, want)]


def write_generated() -> list[Path]:
    changed = stale_files()
    for p, want in generated_files().items():
        if p in changed:
            p.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(want, bytes):
                p.write_bytes(want)
            else:
                p.write_text(want)
    return changed


def manifest() -> dict:
    if not MANIFEST.exists():
        raise CompanionError(f"The extension folder is missing ({EXT_DIR}).")
    return json.loads(MANIFEST.read_text())


def version() -> str:
    return str(manifest().get("version") or "0")


_VERSION = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def bump_version(part: str) -> str:
    """Bump the manifest version (``major`` | ``minor`` | ``patch``) and return it.
    The Chrome Web Store refuses an upload whose version isn't higher than the last."""
    m = _VERSION.match(version())
    if not m:
        raise CompanionError(f"The manifest version {version()!r} isn't MAJOR.MINOR.PATCH.")
    major, minor, patch = (int(x) for x in m.groups())
    if part == "major":
        new = f"{major + 1}.0.0"
    elif part == "minor":
        new = f"{major}.{minor + 1}.0"
    elif part == "patch":
        new = f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"part must be major, minor or patch, not {part!r}")
    data = manifest()
    data["version"] = new
    MANIFEST.write_text(json.dumps(data, indent=2) + "\n")
    return new


def store_url() -> str | None:
    """The companion's Chrome Web Store page, once it's published — ``None`` until then.

    ``MM_COMPANION_STORE_URL`` wins (set it on a host before the repo catches up);
    else ``url`` in ``extension/store/store.toml`` (empty until the owner publishes).
    Only a ``chromewebstore.google.com/detail/…`` address counts — anything else is
    ignored, so a typo can't send users to another site."""
    url = (os.environ.get(STORE_URL_ENV) or "").strip()
    if not url and STORE_TOML.exists():
        url = str(tomllib.loads(STORE_TOML.read_text()).get("chrome_web_store", {}).get("url") or "").strip()
    return url if url.startswith(STORE_URL_PREFIX) else None


def _files() -> list[Path]:
    return sorted(p for p in EXT_DIR.rglob("*")
                  if p.is_file() and p.name not in _EXCLUDE and not p.name.startswith(".")
                  and p.relative_to(EXT_DIR).parts[0] not in _EXCLUDE_DIRS)


ZIP_FOLDER = "magic-manager-companion/"


def build_zip(*, store: bool = False) -> bytes:
    """A reproducible zip of the extension: sorted entries, fixed timestamps and
    permissions, so the same source always yields the same bytes (users and
    reviewers can compare a download to the repo). The download unzips to a
    ``magic-manager-companion/`` folder (for Load unpacked); ``store=True`` puts
    ``manifest.json`` at the zip root, as the Chrome Web Store requires."""
    prefix = "" if store else ZIP_FOLDER
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for p in _files():
            info = zipfile.ZipInfo(f"{prefix}{p.relative_to(EXT_DIR).as_posix()}", _ZIP_DATE)
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
