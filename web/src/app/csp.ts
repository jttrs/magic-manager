// The hosted Content-Security-Policy (src/magic_manager/web/security.py) allows no eval and no
// un-nonced inline style. Imported first by main.tsx, before anything parses or renders.
import { z } from 'zod';

// zod's JIT probes `new Function` (blocked, and reported as a violation): use its plain parser.
z.config({ jitless: true });

// Radix dialogs lock scrolling with a runtime <style>; the server puts this response's nonce in
// <meta name="csp-nonce"> and the style injector (get-nonce) reads it from this global.
const nonce = document.querySelector<HTMLMetaElement>('meta[name="csp-nonce"]')?.content;
if (nonce) (globalThis as { __webpack_nonce__?: string }).__webpack_nonce__ = nonce;
