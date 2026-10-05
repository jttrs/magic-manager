"""Read the user's open browser tabs (macOS) — the deals pipeline's first step.

Deterministic, read-only: ``osascript`` enumerates every window's tabs of a
running Chrome or Safari. Encodes the failure modes in docs/deals-scraping.md:

* results are keyed by URL (indices shift between reads; tabs close) and
  de-duplicated;
* local/dev tabs (``localhost``, ``127.0.0.1``, …) and non-web URLs are dropped;
* AppleScript can latch onto ONE window when a second Chrome (an automation /
  Playwright instance) competes for the bundle id — detected and explained, as
  is a window count that disagrees with the windows that returned tabs;
* browser not running / automation permission denied / not macOS → a clear
  :class:`TabsUnavailable` message, never a guess.
"""
from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass, field
from typing import Callable
from urllib.parse import urlsplit

_FIELD = "\x1f"
_ROW = "\x1e"

_ENGINES = {"chrome": ("Google Chrome", "title"), "safari": ("Safari", "name")}

_SCRIPT = '''
tell application "System Events"
  if not (exists process "{app}") then error "{app} is not running"
end tell
tell application "{app}"
  set out to (count windows) as text
  set out to out & "{R}"
  set wi to 0
  repeat with w in windows
    set wi to wi + 1
    set ti to 0
    repeat with t in tabs of w
      set ti to ti + 1
      set u to (URL of t)
      if u is missing value then set u to ""
      set nm to ({prop} of t)
      if nm is missing value then set nm to ""
      set out to out & u & "{F}" & nm & "{F}" & wi & "{F}" & ti & "{R}"
    end repeat
  end repeat
  return out
end tell
'''

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]"}


class TabsUnavailable(RuntimeError):
    """The tabs couldn't be read (with a plain explanation + fix)."""


@dataclass(frozen=True)
class Tab:
    url: str
    title: str
    host: str
    window: int
    tab: int


@dataclass
class TabRead:
    browser: str
    tabs: list[Tab]
    windows: int                     # what the browser reports
    windows_read: int                # windows that returned at least one tab
    dropped_local: int = 0
    duplicates: int = 0
    warnings: list[str] = field(default_factory=list)


def _osascript(script: str) -> str:
    res = subprocess.run(["osascript", "-e", script], text=True, capture_output=True, check=False)
    if res.returncode != 0:
        raise TabsUnavailable(_explain(res.stderr.strip()))
    return res.stdout


def _ps() -> str:
    return subprocess.run(["ps", "-axo", "pid,command"], text=True, capture_output=True, check=False).stdout


def _explain(err: str) -> str:
    low = err.lower()
    if "is not running" in low:
        return "Your browser isn’t running — open it with your shopping tabs, then read again."
    if "not allowed" in low or "-1743" in low or "not authorized" in low:
        return ("macOS blocked reading the browser. Allow it in System Settings → Privacy & Security → "
                "Automation (let the app running magic-manager control your browser), then read again.")
    return f"Couldn’t read the browser’s tabs: {err or 'osascript failed'}"


def _second_chrome(ps_out: str) -> bool:
    """More than one main Chrome process, at least one an automation instance."""
    mains = [ln for ln in ps_out.splitlines() if "MacOS/Google Chrome" in ln and "Helper" not in ln]
    automation = [ln for ln in mains if "--remote-debugging" in ln or "playwright" in ln.lower() or "--user-data-dir" in ln]
    return len(mains) > 1 and bool(automation)


def parse(raw: str) -> tuple[int, list[tuple[str, str, int, int]]]:
    """``(window count, [(url, title, window, tab)])`` from the script's output."""
    rows = raw.split(_ROW)
    try:
        windows = int(rows[0].strip() or 0)
    except ValueError:
        windows = 0
    out = []
    for row in rows[1:]:
        parts = row.strip("\n").split(_FIELD)
        if len(parts) < 4:
            continue
        try:
            out.append((parts[0], parts[1], int(parts[2]), int(parts[3])))
        except ValueError:
            continue
    return windows, out


def read_tabs(browser: str = "chrome", *, runner: Callable[[str], str] | None = None,
              ps: Callable[[], str] | None = None, system: str | None = None) -> TabRead:
    """Every open web tab of ``browser`` (chrome | safari), local tabs dropped,
    one entry per URL, plus warnings for the known ways this read goes wrong."""
    if browser not in _ENGINES:
        raise TabsUnavailable(f"Unsupported browser {browser!r} — use chrome or safari.")
    if (system or platform.system()) != "Darwin":
        raise TabsUnavailable("Reading open tabs works on macOS only.")
    app, prop = _ENGINES[browser]
    windows, rows = parse((runner or _osascript)(_SCRIPT.format(app=app, prop=prop, F=_FIELD, R=_ROW)))

    seen: set[str] = set()
    tabs: list[Tab] = []
    dropped = dupes = 0
    for url, title, w, t in rows:
        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        if parts.scheme not in ("http", "https") or not host:
            continue
        if host in _LOCAL_HOSTS or host.endswith(".localhost"):
            dropped += 1
            continue
        if url in seen:
            dupes += 1
            continue
        seen.add(url)
        tabs.append(Tab(url=url, title=title, host=host.removeprefix("www."), window=w, tab=t))

    read = TabRead(browser=browser, tabs=tabs, windows=windows,
                   windows_read=len({w for _, _, w, _ in rows}), dropped_local=dropped, duplicates=dupes)
    if browser == "chrome" and _second_chrome((ps or _ps)()):
        read.warnings.append(
            "Another Chrome (an automation/test instance) is running, so macOS may show only one window’s tabs. "
            "Quit it, or click into the window with your shopping tabs, then read again.")
    if read.windows_read < read.windows:
        read.warnings.append(
            f"Only {read.windows_read} of {read.windows} windows returned tabs. Click into the window with your "
            "shopping tabs to bring it to the front, then read again.")
    return read
