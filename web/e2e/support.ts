import { test as base, expect, type Page } from '@playwright/test';
import compare from './fixtures/compare.json' with { type: 'json' };
import commanders from './fixtures/commanders-tifa.json' with { type: 'json' };
import families from './fixtures/families.json' with { type: 'json' };
import collectionBlb from './fixtures/collection-blb.json' with { type: 'json' };
import decks from './fixtures/decks.json' with { type: 'json' };
import deckDetail from './fixtures/deck-detail.json' with { type: 'json' };

// 1×1 transparent PNG stands in for every Scryfall image.
const PNG = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=', 'base64');

export const fixtures = { compare, commanders, families, collectionBlb, decks, deckDetail };

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
    if (url.pathname === '/api/collection/families') return route.fulfill({ json: families });
    if (url.pathname === '/api/collection') return route.fulfill({ json: collectionBlb });
    if (url.pathname === '/api/collection/buy-list') {
      const body = route.request().postDataJSON() as { target: string; items: { scryfall_id: string }[] };
      const text = body.items.map((i) => `1 ${i.scryfall_id} [${body.target}]`).join('\n');
      return route.fulfill({ json: { text, lines: body.items.length } });
    }
    if (url.pathname === '/api/decks') return route.fulfill({ json: decks });
    if (url.pathname.startsWith('/api/decks/')) {
      const slug = decodeURIComponent(url.pathname.slice('/api/decks/'.length));
      return slug === deckDetail.deck.slug ? route.fulfill({ json: deckDetail }) : route.fulfill({ status: 404, json: { detail: `deck with slug '${slug}' not found` } });
    }
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
export const COLLECTION_URL = '/collection?families=%5B%22blb%22%5D';
