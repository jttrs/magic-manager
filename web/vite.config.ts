import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import tailwindcss from '@tailwindcss/vite';

// Dev: Vite serves the SPA and proxies /api to `uv run mm serve` (port 8765, or
// $MM_API_PORT when a parallel worktree runs its API elsewhere).
// Prod: `npm run build` → web/dist, served by the FastAPI app itself.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: { '/api': { target: `http://127.0.0.1:${process.env.MM_API_PORT ?? 8765}`, changeOrigin: false } },
  },
  test: { include: ['src/**/*.test.ts'] },
});
