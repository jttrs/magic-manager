import { test as base, expect, type Page } from '@playwright/test';
import compare from './fixtures/compare.json' with { type: 'json' };
import commanders from './fixtures/commanders-tifa.json' with { type: 'json' };
import families from './fixtures/families.json' with { type: 'json' };
import cardDiffFin from './fixtures/card-diff-fin.json' with { type: 'json' };

// 1×1 transparent PNG stands in for every Scryfall image.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');

export const fixtures = { compare, commanders, families, cardDiffFin };

export async function mockApi(page: Page, overrides: Record<string, (url: URL) => { status?: number; json: unknown }> = {}) {
  await page.route('https://cards.scryfall.io/**', (r) => r.fulfill({ status: 200, contentType: 'image/png', body: PNG }));
  await page.route((u) => u.pathname.startsWith('/api/'), (route) => {
    const url = new URL(route.request().url());
    for (const [prefix, fn] of Object.entries(overrides)) {
      if (url.pathname.startsWith(prefix)) {
        const { status = 200, json } = fn(url);
        return route.fulfill({ status, json });
      }
    }
    if (url.pathname === '/api/edhrec/compare') return route.fulfill({ json: compare });
    if (url.pathname === '/api/edhrec/commanders') return route.fulfill({ json: commanders });
    if (url.pathname === '/api/card-diff/families') return route.fulfill({ json: families });
    if (url.pathname === '/api/card-diff') return route.fulfill({ json: cardDiffFin });
    if (url.pathname === '/api/jobs') return route.fulfill({ json: [] });
    return route.fulfill({ status: 404, json: { detail: `unmocked ${url.pathname}` } });
  });
}

export const test = base.extend<{ mocked: void }>({
  mocked: [async ({ page }, use) => {
    await mockApi(page);
    await use();
  }, { auto: true }],
});
export { expect };

export const COMPARE_URL = '/commanders?a=Tifa%20Lockhart&b=Cloud%2C%20Ex-SOLDIER';
export const SETS_URL = '/sets?families=%5B%22fin%22%5D';
