"""The one same-site rule: a browser marks every request with ``Sec-Fetch-Site``, so a
request another website (or another localhost port) made is told apart from this
app's own pages. Non-browser clients (CLI, tests) send no header and pass.
See docs/browser-companion-security.md."""
from __future__ import annotations

from fastapi import Request

from .. import companion as companion_engine

CODE = "request.cross_site"
ALLOWED = ("same-origin", "none")


def cross_site(request: Request) -> str | None:
    """The ``Sec-Fetch-Site`` value when it isn't this app's own page, else None."""
    site = request.headers.get("sec-fetch-site")
    return site if site is not None and site not in ALLOWED else None


def message(site: str) -> str:
    return companion_engine.error(CODE, site=site)
