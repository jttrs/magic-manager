"""Write the web API's OpenAPI schema to web/openapi.json (input to the TS client
generator: `npm --prefix web run gen:api`). Deterministic; no server needed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager.web import auth_routes  # noqa: E402
from magic_manager.web.app import create_app  # noqa: E402

app = create_app(serve_frontend=False)
# The sign-in routes exist only in hosted mode; the client is generated with them.
if not any(getattr(r, "path", "") == "/api/auth/me" for r in app.routes):
    app.include_router(auth_routes.router)
out = ROOT / "web" / "openapi.json"
out.write_text(json.dumps(app.openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")
