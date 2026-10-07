// App side of the browser companion, with a stand-in for the extension's bridge
// (the real extension is driven end to end in companion-extension.spec.ts).
import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, test } from './support';

type Answer = { ok: true; data: unknown } | { ok: false; code: string; message?: string; fix?: string | null };

/** Plays the bridge: hello on ping; ack then the configured answer per kind. */
async function fakeCompanion(page: Page, { version = '0.1.0', features = { cart: true, deals: true, moxfield: true }, answers = {} as Record<string, Answer> } = {}) {
  await page.addInitScript(({ version, features, answers }) => {
    const CHANNEL = 'magic-manager/companion';
    const w = window as unknown as { __companionRequests: unknown[] };
    w.__companionRequests = [];
    const post = (m: Record<string, unknown>) => window.postMessage({ ...m, channel: CHANNEL, from: 'companion' }, location.origin);
    window.addEventListener('message', (ev) => {
      const d = ev.data;
      if (ev.source !== window || !d || d.channel !== CHANNEL || d.from !== 'app') return;
      if (d.type === 'ping') post({ type: 'hello', version, features });
      if (d.type === 'request') {
        w.__companionRequests.push({ kind: d.kind, params: d.params });
        const a = answers[d.kind];
        if (!a) return;
        if (!a.ok && ['request.busy', 'permission.deals_off', 'moxfield.bad_url'].includes(a.code)) { post({ type: 'ack', id: d.id, ...a }); return; }
        post({ type: 'ack', id: d.id, ok: true, status: 'awaiting_approval', summary: 'the stuff' });
        setTimeout(() => post({ type: 'result', id: d.id, kind: d.kind, ...a }), 300);
      }
    });
  }, { version, features, answers });
}

const CART = {
  items: [
    { scryfall_id: '8d8432a7-1c8a-4cfb-947c-ecf9791063eb', name: 'Sire of Seven Deaths', set_name: 'Foundations', finish: 'foil', condition: 'NM', treatments: [], quantity: 2, price: 20.5 },
  ],
  warnings: [{ code: 'cart.signed_out' }],
};
const AUDIT = {
  lines: 1, copies: 2, total: 41, unidentified: [], family: null, families: [], dupes: [], missing: [], no_market: [],
  owned: [{ scryfall_id: '8d8432a7-1c8a-4cfb-947c-ecf9791063eb', name: 'Sire of Seven Deaths', set: 'FDN', num: '1', fin: 'foil', owned_qty: 1, your: 20.5 }],
  overpay: [],
};

async function flags(page: Page, f: Record<string, boolean>) {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: f } }));
  await page.route('**/api/cart/setup', (r) => r.fulfill({ json: { account: false } }));
}

async function openCart(page: Page) {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Check my Mana Pool cart' }).click();
  return page.getByRole('dialog', { name: 'Check my Mana Pool cart' });
}

test.describe('setup', () => {
  test('the header shows the companion only with its flag on, and explains how to install and pair', async ({ page }) => {
    await page.goto(COLLECTION_URL);
    await expect(page.getByRole('button', { name: /Browser companion/ })).toHaveCount(0);
    await flags(page, { companion: true });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · set up' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('status')).toContainText('Not connected');
    await expect(d.getByRole('link', { name: 'Download the companion' })).toHaveAttribute('href', '/api/companion/extension.zip');
    await expect(d).toContainText(new URL(page.url()).origin);
    await expect(d).toContainText('Read cookies, passwords, sign-in tokens, email or addresses.');
  });

  test('connected: version and what each feature may read', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { features: { cart: true, deals: false, moxfield: true } });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · connected' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('status')).toContainText('Connected · version 0.1.0');
    await expect(d.getByText('Deals — your open store tabs').locator('../..')).toContainText('Off');
  });

  test('an older install is asked to update', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { version: '0.0.9' });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · update available' }).click();
    await expect(page.getByRole('dialog', { name: 'Browser companion' })).toContainText('Version 0.1.0 is available');
  });
});

test.describe('Mana Pool cart', () => {
  test('read in this browser: waits for approval, then audits only the lines', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    await fakeCompanion(page, { answers: { cart: { ok: true, data: CART } } });
    let body: unknown = null;
    await page.route('**/api/cart/lines', (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: AUDIT }); });
    const d = await openCart(page);
    await d.getByRole('button', { name: 'Read my cart' }).click();
    await expect(d.getByText('Waiting for you to approve in the companion window — the stuff.')).toBeVisible();
    await expect(d.getByRole('region', { name: 'Already in your collection' })).toContainText('Sire of Seven Deaths');
    await expect(d).toContainText('Read in this browser by the companion.');
    await expect(d).toContainText('this is the browser’s guest cart');
    expect(body).toEqual({ items: CART.items, source: 'extension', family: 'blb' });
  });

  test('declining in the companion window says nothing was sent, with its code', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    await fakeCompanion(page, { answers: { cart: { ok: false, code: 'request.denied' } } });
    const d = await openCart(page);
    await d.getByRole('button', { name: 'Read my cart' }).click();
    const note = d.getByRole('status').filter({ hasText: 'You chose not to send it' });
    await expect(note).toContainText('Nothing was sent.');
    await expect(note).toContainText('Code request.denied');
  });

  test('a page Mana Pool changed is named with the fix', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    await fakeCompanion(page, { answers: { cart: { ok: false, code: 'cart.page_changed' } } });
    const d = await openCart(page);
    await d.getByRole('button', { name: 'Read my cart' }).click();
    await expect(d.getByRole('alert')).toContainText('Mana Pool may have changed its page');
    await expect(d.getByRole('alert')).toContainText('scrape-doctor skill');
  });

  test('without the companion: Read my cart explains setup; the bookmarklet paste still works', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    let body: unknown = null;
    await page.route('**/api/cart/lines', (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: AUDIT }); });
    const d = await openCart(page);
    await expect(d.getByText('Set up the browser companion first')).toBeVisible();
    await expect(d.getByRole('button', { name: 'Read my cart' })).toBeDisabled();
    await d.getByRole('textbox', { name: 'Paste what it copied' }).fill('not a cart');
    await d.getByRole('button', { name: 'Check pasted cart' }).click();
    await expect(d.getByRole('alert')).toContainText('That isn’t what the cart bookmarklet copies.');
    await d.getByRole('textbox', { name: 'Paste what it copied' }).fill(JSON.stringify({ source: 'manapool-cart-page', version: '0.1.0', ...CART }));
    await d.getByRole('button', { name: 'Check pasted cart' }).click();
    await expect(d).toContainText('Pasted from the bookmarklet.');
    expect(body).toEqual({ items: CART.items, source: 'bookmarklet', family: 'blb' });
  });

  test('a coded server refusal shows its message and fix', async ({ page }) => {
    await flags(page, { cart_check: true });
    await page.route('**/api/cart/lines', (r) => r.fulfill({ status: 403, json: { detail: { code: 'request.cross_site', message: 'This request came from another website, so the app refused it.', fix: 'Use the app’s own page.' }, code: 'request.cross_site', request_id: 'abcdef1234567890abcdef1234567890' } }));
    const d = await openCart(page);
    await d.getByRole('textbox', { name: 'Paste what it copied' }).fill(JSON.stringify({ source: 'manapool-cart-page', ...CART }));
    await d.getByRole('button', { name: 'Check pasted cart' }).click();
    await expect(d.getByRole('alert')).toContainText('came from another website');
    await expect(d.getByRole('alert')).toContainText('Use the app’s own page.');
    await expect(d.getByRole('alert')).toContainText('Code request.cross_site · ref abcdef12');
  });
});

test.describe('Deals', () => {
  const TABS = {
    tabs: [
      { url: 'https://manyrealms.com/products/fdn-set', title: 'Foundations Commander Set of 5', window: 1 },
      { url: 'https://www.bestbuy.com/site/x/123.p', title: 'Reign of Dragons', window: 1 },
    ],
    pages: { 'https://www.bestbuy.com/site/x/123.p': { title: 'Reign of Dragons', head: '', ld: [], text: '$44.99' } },
    warnings: [],
  };
  const SORTED = {
    browser: 'extension', windows: 1, windows_read: 1, warnings: [], uncatalogued: [], store_pages: 0, other: 0, dropped_local: 0, duplicates: 0,
    stores: [
      { key: 'manyrealms', name: 'Many Realms', mode: 'shopify', no_sales_tax: true, tabs: [{ url: TABS.tabs[0].url, title: TABS.tabs[0].title, window: 1, tab: 1 }] },
      { key: 'bestbuy', name: 'Best Buy', mode: 'rendered', no_sales_tax: false, tabs: [{ url: TABS.tabs[1].url, title: TABS.tabs[1].title, window: 1, tab: 2 }] },
    ],
  };

  test('reads tabs in this browser and hands open-tab pages to the price read', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    await fakeCompanion(page, { answers: { tabs: { ok: true, data: TABS } } });
    let tabsBody: unknown = null;
    let jobBody: { urls: string[]; pages: Record<string, unknown> } | null = null;
    await page.route('**/api/deals/tabs', (r) => { tabsBody = r.request().postDataJSON(); return r.fulfill({ json: SORTED }); });
    await page.route('**/api/jobs/deals.read_prices', (r) => { jobBody = r.request().postDataJSON(); return r.fulfill({ status: 500, json: { detail: 'stop here' } }); });
    await page.goto('/market?subject=deals');
    await expect(page.getByText('Asks the browser companion')).toBeVisible();
    await page.getByRole('button', { name: 'Read my open tabs' }).click();
    await expect(page.getByRole('region', { name: 'Best Buy' })).toContainText('price read from your open tab');
    await expect(page.getByText('Read in this browser by the companion')).toBeVisible();
    expect(tabsBody).toEqual({ tabs: TABS.tabs });
    await page.getByRole('button', { name: 'Read 2 prices' }).click();
    await expect.poll(() => jobBody).not.toBeNull();
    expect(jobBody!.pages).toEqual(TABS.pages);
  });

  test('Deals switched off in the companion: says how to switch it on', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    await fakeCompanion(page, { answers: { tabs: { ok: false, code: 'permission.deals_off' } } });
    await page.goto('/market?subject=deals');
    await page.getByRole('button', { name: 'Read my open tabs' }).click();
    await expect(page.getByRole('alert')).toContainText('switch on Deals');
  });
});

test.describe('Moxfield', () => {
  const DECK = {
    url: 'https://moxfield.com/decks/AbCd1234',
    deck: { publicId: 'AbCd1234', name: 'Goblin Party', createdByUser: { userName: 'goblinfan' }, boards: { mainboard: { cards: { 0: { quantity: 1, isFoil: false, finish: null, card: { scryfall_id: null, set: 'cmm', cn: '400', name: 'Sol Ring', finish: null } } } } } },
  };
  test('a Moxfield link is read in this browser and lands in review', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { answers: { moxfield: { ok: true, data: DECK } } });
    let body: unknown = null;
    await page.route('**/api/ingest/deck-from-browser', (r) => {
      body = r.request().postDataJSON();
      return r.fulfill({ json: { format: 'deck', deck_name: 'Goblin Party', warnings: [], deck: { source: 'moxfield', id: 'AbCd1234', name: 'Goblin Party', author: 'goblinfan', cards: [] }, lines: [] } });
    });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await page.getByRole('tab', { name: 'Deck or precon' }).click();
    await page.getByRole('textbox', { name: /Archidekt/ }).fill(DECK.url);
    await expect(page.getByText('Read in this browser by the companion — you approve what it sends.')).toBeVisible();
    await page.getByRole('button', { name: 'Fetch deck' }).click();
    await expect(page.getByRole('heading', { name: 'Goblin Party' })).toBeVisible();
    expect(body).toEqual({ source: 'moxfield', deck: DECK.deck });
    expect(await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests)).toEqual([{ kind: 'moxfield', params: { url: DECK.url } }]);
  });

  test('a private deck names the fix', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { answers: { moxfield: { ok: false, code: 'moxfield.private' } } });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await page.getByRole('tab', { name: 'Deck or precon' }).click();
    await page.getByRole('textbox', { name: /Archidekt/ }).fill(DECK.url);
    await page.getByRole('button', { name: 'Fetch deck' }).click();
    await expect(page.getByRole('alert')).toContainText('Moxfield says this deck is private');
  });
});
