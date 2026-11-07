// The BUILT SPA under the hosted Content-Security-Policy (web/security.py): every view loads
// with no CSP violation. The dev server injects inline scripts (React refresh), so this spec
// builds the SPA itself and serves web/dist through page.route with the server's exact headers.
import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import type { Page } from '@playwright/test';
import { COLLECTION_URL, COMPARE_URL, expect, mockApi, test } from './support';

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
  // Hosted + signed in, so the Account popover and the delete-account alert dialog exist too.
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: {}, owner_paths: {}, mode: 'hosted' } }),
    '/api/auth/me': () => ({ json: {
      user: { id: 'mmmmmmmmmmmmmmmm', display_name: 'Friend', email: 'friend@example.com', is_admin: false, providers: ['discord'] },
      csrf_token: 'csrf-1', providers: [{ name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' }], profiles_open: true,
      signed_in_at: new Date().toISOString(), reauth_minutes: 10, reauth_seconds_left: 540,
    } }),
  });

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

  // Every Radix primitive the app uses, opened once (they inject their own styles / portals):
  // Dialog, Tabs, Switch, ToggleGroup, AlertDialog, Popover, Tooltip, DropdownMenu, HoverCard.
  const violations = () => page.evaluate(() => (window as unknown as { __csp: string[] }).__csp);
  await page.goto(COLLECTION_URL);
  await page.waitForLoadState('networkidle');

  // Tooltip: hover an icon button.
  await page.getByRole('link', { name: 'Background jobs' }).hover();
  await expect(page.getByRole('tooltip').first()).toBeVisible();
  await page.mouse.move(0, 0);

  // Popover: the Account popover.
  await page.getByRole('button', { name: /Signed in as Friend/ }).click();
  await expect(page.getByRole('dialog', { name: 'Your account' })).toBeVisible();
  await page.keyboard.press('Escape');

  // Dialog + Switch + ToggleGroup + AlertDialog, all inside Settings.
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await expect(settings).toBeVisible();
  await expect(settings.getByRole('switch').first()).toBeVisible();
  await expect(settings.getByRole('radio').first()).toBeVisible();
  await settings.getByRole('switch').first().click();
  await settings.getByRole('button', { name: 'Delete account…' }).click();
  await expect(page.getByRole('alertdialog', { name: 'Delete your account' })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.keyboard.press('Escape');
  await expect(settings).toBeHidden();

  // Dialog + Tabs: Add cards.
  await page.getByRole('button', { name: 'Add cards' }).click();
  const add = page.getByRole('dialog', { name: 'Add cards' });
  await expect(add.getByRole('tablist', { name: 'How to add' })).toBeVisible();
  await add.getByRole('tab').nth(1).click();
  await page.keyboard.press('Escape');
  await expect(add).toBeHidden();

  // Popover: the sort builder.
  await page.getByRole('button', { name: /^Sort/ }).first().click();
  await expect(page.getByRole('dialog').first()).toBeVisible();
  await page.keyboard.press('Escape');

  // DropdownMenu: a Select field in the view rail.
  await page.goto('/decks');
  await page.getByRole('button', { name: /^Group by/ }).click();
  await expect(page.getByRole('menuitemradio').first()).toBeVisible();
  await page.keyboard.press('Escape');

  // Popover (listbox): a searchable select in Market.
  await page.goto('/market');
  await page.getByRole('button', { name: /^Set family/ }).click();
  await expect(page.getByRole('combobox', { name: 'Filter families' })).toBeVisible();
  await page.keyboard.press('Escape');

  // HoverCard: a card name's art preview.
  await page.goto(COMPARE_URL);
  await page.waitForLoadState('networkidle');
  await page.getByRole('radio', { name: 'List' }).click();   // list rows carry the hover preview
  const tile = page.getByRole('region', { name: 'Tifa Lockhart only cards' }).getByRole('button', { name: /^Inspect / }).first();
  await tile.hover();
  await expect(page.locator('[data-radix-popper-content-wrapper]').first()).toBeVisible();

  // Dialog (sheet): the card inspector.
  await tile.click();
  await expect(page.getByRole('dialog').first()).toBeVisible();
  await page.keyboard.press('Escape');

  expect(await violations(), 'CSP violations while opening overlays').toEqual([]);
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
