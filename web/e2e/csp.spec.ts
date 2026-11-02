// The BUILT SPA under the hosted Content-Security-Policy (web/security.py): every view loads
// with no CSP violation. The dev server injects inline scripts (React refresh), so this spec
// builds the SPA itself and serves web/dist through page.route with the server's exact headers.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';
import { COLLECTION_URL, COMPARE_URL, expect, test } from './support';

const WEB = path.resolve(import.meta.dirname, '..');
const OUT = path.join(WEB, 'test-results', 'csp-dist');
const TYPES: Record<string, string> = {
  '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml', '.woff2': 'font/woff2', '.woff': 'font/woff', '.html': 'text/html',
};

type Hosted = { page: Record<string, string>; asset: Record<string, string>; index: string };

/** What the hosted server sends (one source of truth: magic_manager.web.security): the SPA page
 *  with its style nonce (headers + rendered index.html) and the headers on every other file. */
function hosted(): Hosted {
  const py = [
    'import json, sys; from magic_manager.web import security as s',
    'n = s.new_nonce(); h = lambda x: {k.decode(): v.decode() for k, v in x}',
    'o = "https://cards.example.com"',
    'print(json.dumps({"page": h(s.response_headers(o, n)), "asset": h(s.response_headers(o)), '
      + '"index": s.render_index(open(sys.argv[1]).read(), n)}))',
  ].join('\n');
  const out = execFileSync('uv', ['run', '--project', '..', 'python', '-c', py, path.join(OUT, 'index.html')], { cwd: WEB, encoding: 'utf8' });
  return JSON.parse(out) as Hosted;
}

async function serveBuilt(page: Page, h: Hosted) {
  await page.route((u) => (u.hostname === 'localhost' || u.hostname === '127.0.0.1') && !u.pathname.startsWith('/api/'), async (route) => {
    const url = new URL(route.request().url());
    const rel = decodeURIComponent(url.pathname).replace(/^\/+/, '');
    const file = path.join(OUT, rel);
    if (rel && rel !== 'index.html' && file.startsWith(OUT + path.sep) && existsSync(file)) {
      await route.fulfill({ status: 200, headers: { ...h.asset, 'content-type': TYPES[path.extname(file)] ?? 'application/octet-stream' }, body: readFileSync(file) });
      return;
    }
    await route.fulfill({ status: 200, headers: { ...h.page, 'content-type': 'text/html' }, body: h.index });
  });
}

test.describe.configure({ mode: 'serial' });

test('the built SPA runs under the hosted CSP with no violations', async ({ page }) => {
  test.setTimeout(120_000);
  execFileSync('npx', ['vite', 'build', '--outDir', OUT, '--emptyOutDir', '--logLevel', 'error'], { cwd: WEB, stdio: 'inherit' });
  const h = hosted();
  for (const csp of [h.page['content-security-policy'], h.asset['content-security-policy']]) {
    expect(csp).toContain("script-src 'self';");
    expect(csp).not.toMatch(/unsafe-(inline|eval)/);
  }
  await page.addInitScript(() => {
    (window as unknown as { __csp: string[] }).__csp = [];
    document.addEventListener('securitypolicyviolation', (e) => {
      (window as unknown as { __csp: string[] }).__csp.push(`${e.violatedDirective} ${e.blockedURI} ${e.sourceFile}:${e.lineNumber}:${e.columnNumber} ${e.sample}`);
    });
  });
  const refused: string[] = [];
  page.on('console', (m) => {
    if (/Content Security Policy/i.test(m.text())) refused.push(m.text());
  });
  await serveBuilt(page, h);

  const views: [string, () => Promise<void>][] = [
    [COMPARE_URL, () => expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()],
    [COLLECTION_URL, () => expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()],
    ['/decks', () => expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()],
    ['/explore', () => expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()],
    ['/market', () => expect(page.getByRole('heading', { level: 1 }).first()).toBeVisible()],
  ];
  for (const [url, ready] of views) {
    await page.goto(url);
    await ready();
    await page.waitForLoadState('networkidle');
    // Open the settings dialog once per view: dialogs/portals mount their own styles.
    await page.getByRole('button', { name: 'Settings' }).click();
    await expect(page.getByRole('dialog', { name: 'Settings' })).toBeVisible();
    await page.keyboard.press('Escape');
    const seen = await page.evaluate(() => (window as unknown as { __csp: string[] }).__csp);
    expect(seen, `CSP violations on ${url}`).toEqual([]);
  }
  expect(refused).toEqual([]);

  // The policy is really in force: an injected inline script is refused.
  const ran = await page.evaluate(() => {
    const s = document.createElement('script');
    s.textContent = 'window.__inline = 1';
    document.head.append(s);
    return (window as unknown as { __inline?: number }).__inline === 1;
  });
  expect(ran).toBe(false);
  await expect.poll(() => page.evaluate(() => (window as unknown as { __csp: string[] }).__csp)).toContainEqual(expect.stringMatching(/^script-src/));
});
