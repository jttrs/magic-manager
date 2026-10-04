"""Write the web API's OpenAPI schema to web/openapi.json (input to the TS client
generator: `npm --prefix web run gen:api`). Deterministic; no server needed."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from magic_manager.web.app import create_app  # noqa: E402

out = ROOT / "web" / "openapi.json"
out.write_text(json.dumps(create_app(serve_frontend=False).openapi(), indent=2) + "\n", encoding="utf-8")
print(f"wrote {out}")
