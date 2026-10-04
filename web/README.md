# magic-manager web

React + TypeScript + Vite SPA — the web adapter over the Python engine. Architecture:
`../docs/webapp-architecture-decision.md` (Part III); visual system: `../DESIGN.md`;
product truth: `../PRODUCT.md`.

```bash
uv run mm serve            # API on :8765 (from repo root)
npm run dev                # SPA on :5173, proxies /api → :8765
npm run gen:api            # regenerate src/core/api from FastAPI's OpenAPI
npm run tokens             # tokens/*.tokens.json → src/styles/tokens.css
npm run check              # tsc · oxlint · stylelint · dependency-cruiser · knip · vitest
npm run e2e                # Playwright pinning suite (offline fixtures)
npm run build              # → dist/, served by `mm serve`
```

Layers: `src/core` (framework-free; guarded), `src/components` (presentational),
`src/views` (route views), `src/app` (router, queries, theme, hooks).
