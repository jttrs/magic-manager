// App side of the browser companion, with a stand-in for the extension's bridge
// (the real extension is driven end to end in companion-extension.spec.ts).
import type { Page } from '@playwright/test';
import { COLLECTION_URL, COMPANION_INFO, expect, test } from './support';

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
  await page.getByRole('button', { name: 'Check my cart' }).click();
  return page.getByRole('dialog', { name: 'Check my cart' });
}

test.describe('setup', () => {
  test('the header shows the companion only with its flag on, and explains how to install and pair', async ({ page }) => {
    await page.goto(COLLECTION_URL);
    await expect(page.getByRole('button', { name: /Browser companion/ })).toHaveCount(0);
    await flags(page, { companion: true });
    await page.goto(COLLECTION_URL);
    await expect(page.getByRole('button', { name: 'Browser companion · set up · not connected' })).toBeVisible();
    await page.getByRole('button', { name: 'Browser companion · set up' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('status')).toContainText('Not connected');
    await expect(d.getByRole('link', { name: 'Download the companion' })).toHaveAttribute('href', '/api/companion/extension.zip');
    await expect(d.getByRole('link', { name: /Add to Chrome/ })).toHaveCount(0);   // not published: the developer install leads
    await expect(d.getByRole('link', { name: /Add to Edge/ })).toHaveCount(0);     // no Edge listing configured: no Edge link
    await expect(d).toContainText('isn’t on the Chrome Web Store yet');
    await expect(d).toContainText(new URL(page.url()).origin);
    await expect(d).toContainText('Read cookies, passwords, email or addresses.');
    await expect(d).toContainText('Send a sign-in token anywhere.');
  });

  test('published: Add to Chrome leads and the developer install is folded away', async ({ page }) => {
    const STORE = 'https://chromewebstore.google.com/detail/magic-manager-companion/abcdefghijklmnopabcdefghijklmnop';
    await flags(page, { companion: true });
    await page.route('**/api/companion', (r) => r.fulfill({ json: { ...COMPANION_INFO, store_url: STORE } }));
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · set up' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    const add = d.getByRole('link', { name: /Add to Chrome/ });
    await expect(add).toHaveAttribute('href', STORE);
    await expect(add).toHaveAttribute('target', '_blank');
    await expect(d.getByRole('link', { name: 'Download the companion' })).toBeHidden();
    await d.getByText('Developer install').click();
    await expect(d.getByRole('link', { name: 'Download the companion' })).toBeVisible();
    await expect(d.getByRole('link', { name: 'Privacy policy' })).toHaveAttribute('href', COMPANION_INFO.privacy_url);
    await expect(d.getByRole('link', { name: /Add to Edge/ })).toHaveCount(0);     // Edge stays opt-in
    await expect(d).toContainText('From the Chrome Web Store. Chrome keeps it up to date.');
  });

  test('an Edge Add-ons listing adds Add to Edge beside Add to Chrome', async ({ page }) => {
    const STORE = 'https://chromewebstore.google.com/detail/magic-manager-companion/abcdefghijklmnopabcdefghijklmnop';
    const EDGE = 'https://microsoftedge.microsoft.com/addons/detail/magic-manager-companion/abcdefghijklmnopabcdefghijklmnop';
    await flags(page, { companion: true });
    await page.route('**/api/companion', (r) => r.fulfill({ json: { ...COMPANION_INFO, store_url: STORE, edge_store_url: EDGE } }));
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · set up' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('link', { name: /Add to Chrome/ })).toHaveAttribute('href', STORE);
    const edge = d.getByRole('link', { name: /Add to Edge/ });
    await expect(edge).toHaveAttribute('href', EDGE);
    await expect(edge).toHaveAttribute('target', '_blank');
    await expect(d).toContainText('Your browser keeps it up to date.');
    await expect(d.getByRole('link', { name: 'Download the companion' })).toBeHidden();
  });

  test('Edge only: Add to Edge leads and the developer install is folded away', async ({ page }) => {
    const EDGE = 'https://microsoftedge.microsoft.com/addons/detail/magic-manager-companion/abcdefghijklmnopabcdefghijklmnop';
    await flags(page, { companion: true });
    await page.route('**/api/companion', (r) => r.fulfill({ json: { ...COMPANION_INFO, edge_store_url: EDGE } }));
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · set up' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('link', { name: /Add to Chrome/ })).toHaveCount(0);
    await expect(d.getByRole('link', { name: /Add to Edge/ })).toHaveAttribute('href', EDGE);
    await expect(d).toContainText('From Microsoft Edge Add-ons. Edge keeps it up to date.');
    await expect(d.getByRole('link', { name: 'Download the companion' })).toBeHidden();
  });

  test('published + an older install: the store copy updates once that version is published', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { version: '0.0.9' });
    await page.route('**/api/companion', (r) => r.fulfill({ json: { ...COMPANION_INFO, store_url: 'https://chromewebstore.google.com/detail/x/abcdefghijklmnopabcdefghijklmnop' } }));
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Browser companion · update available' }).click();
    await expect(page.getByRole('dialog', { name: 'Browser companion' })).toContainText('updates itself once that version is published on the Chrome Web Store');
  });

  test('connected: version and what each feature may read', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { features: { cart: true, deals: false, moxfield: true } });
    await page.goto(COLLECTION_URL);
    await expect(page.getByRole('button', { name: 'Browser companion · connected · v0.1.0' })).toBeVisible();
    await page.getByRole('button', { name: 'Browser companion · connected' }).click();
    const d = page.getByRole('dialog', { name: 'Browser companion' });
    await expect(d.getByRole('status')).toContainText('Connected · version 0.1.0');
    await expect(d.getByText('Deals — your open store tabs').locator('../..')).toContainText('Off');
  });

  test('an older install is asked to update', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { version: '0.0.9' });
    await page.goto(COLLECTION_URL);
    await expect(page.getByRole('button', { name: 'Browser companion · update available · v0.0.9 → v0.1.0' })).toBeVisible();
    await page.getByRole('button', { name: 'Browser companion · update available' }).click();
    await expect(page.getByRole('dialog', { name: 'Browser companion' })).toContainText('Version 0.1.0 is available');
  });
});

const TCG_CART = {
  store: 'tcgplayer',
  items: [
    { kind: 'single', tcgplayer_product_id: 487805, name: 'The One Ring', set_name: 'Universes Beyond: The Lord of the Rings: Tales of Middle-earth', number: '246', finish: 'nonfoil', condition: 'LP', language: 'English', quantity: 1, price: 108.15 },
    { kind: 'sealed', tcgplayer_product_id: null, name: 'FINAL FANTASY - Play Booster Pack', set_name: 'FINAL FANTASY', number: null, finish: 'nonfoil', condition: null, language: null, quantity: 1, price: 8.49 },
  ],
  warnings: [],
};
const TCG_AUDIT = {
  lines: 2, copies: 2, total: 116.64, unidentified: [], family: null, families: ['ltr'], dupes: [], missing: [], no_market: [], overpay: [],
  owned: [{ scryfall_id: 'd5806e68-1054-458e-866d-1f2470f682b2', name: 'The One Ring', set: 'LTR', num: '246', fin: 'nonfoil', owned_qty: 1, your: 108.15, condition: 'LP', language: 'English' }],
  not_cards: [{ name: 'FINAL FANTASY - Play Booster Pack', kind: 'sealed', qty: 1, price: 8.49 }],
  not_compared: 1,
};

test.describe('TCGplayer and Card Kingdom carts', () => {
  test('other carts need the companion’s Allow access switch; the bookmarklet is Mana Pool only', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    await fakeCompanion(page, { version: '0.3.0' });
    const d = await openCart(page);
    await expect(d.getByRole('heading', { name: 'With the bookmarklet' })).toBeVisible();
    await d.getByRole('radio', { name: 'Card Kingdom' }).click();
    await expect(d.getByRole('heading', { name: 'With the bookmarklet' })).toHaveCount(0);
    await expect(d).toContainText('Switch on Allow access in the companion’s settings');
    await expect(d.getByRole('button', { name: 'Read my cart' })).toBeDisabled();
  });

  test('a TCGplayer cart: read in this browser, audited by store, played lines named and left out of Over market', async ({ page }) => {
    await flags(page, { companion: true, cart_check: true });
    await fakeCompanion(page, { version: '0.3.0', features: { cart: true, deals: false, moxfield: false, cart_tcgplayer: true } as never, answers: { cart: { ok: true, data: TCG_CART } } });
    let body: unknown = null;
    await page.route('**/api/cart/lines', (r) => { body = r.request().postDataJSON(); return r.fulfill({ json: TCG_AUDIT }); });
    const d = await openCart(page);
    await d.getByRole('radio', { name: 'TCGplayer' }).click();
    await d.getByRole('button', { name: 'Read my cart' }).click();
    await expect(d).toContainText('TCGplayer cart · read in this browser by the companion.');
    await expect(d.getByRole('region', { name: 'Already in your collection' })).toContainText('LTR 246 · LP');
    await expect(d.getByRole('region', { name: 'Not single cards' })).toContainText('sealed · not checked');
    await expect(d).toContainText('1 played or non-English line left out — market prices are Near Mint English.');
    expect(await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests)).toEqual([{ kind: 'cart', params: { store: 'tcgplayer' } }]);
    expect(body).toMatchObject({ source: 'extension', store: 'tcgplayer', family: 'blb' });
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
    await expect(d).toContainText('Mana Pool cart · read in this browser by the companion.');
    await expect(d).toContainText('this is the browser’s guest cart');
    expect(body).toEqual({ items: CART.items, source: 'extension', store: 'manapool', family: 'blb' });
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
    await expect(d.getByRole('alert')).toContainText('the store may have changed its page');
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
    await expect(d).toContainText('Mana Pool cart · pasted from the bookmarklet.');
    expect(body).toEqual({ items: CART.items, source: 'bookmarklet', store: 'manapool', family: 'blb' });
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

  test('reads tabs in this browser and hands open-tab pages to the price read, in one action', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    await fakeCompanion(page, { answers: { tabs: { ok: true, data: TABS } } });
    let tabsBody: unknown = null;
    let jobBody: { urls: string[]; pages: Record<string, unknown> } | null = null;
    await page.route('**/api/deals/watched', (r) => r.fulfill({ json: [] }));
    await page.route('**/api/deals/tabs', (r) => { tabsBody = r.request().postDataJSON(); return r.fulfill({ json: SORTED }); });
    await page.route('**/api/jobs/deals.read_prices', (r) => { jobBody = r.request().postDataJSON(); return r.fulfill({ status: 500, json: { detail: 'stop here' } }); });
    await page.goto('/market?subject=deals');
    await page.getByRole('button', { name: 'Read my open tabs' }).click();
    await expect.poll(() => jobBody).not.toBeNull();
    expect(tabsBody).toEqual({ tabs: TABS.tabs });
    expect(jobBody!.urls).toEqual([TABS.tabs[0].url, TABS.tabs[1].url]);
    expect(jobBody!.pages).toEqual(TABS.pages);
    const tabReads = await page.evaluate(() => (window as unknown as { __companionRequests: { kind: string }[] }).__companionRequests.filter((q) => q.kind === 'tabs').length);
    expect(tabReads).toBe(1);
  });

  const BESTBUY = 'https://www.bestbuy.com/site/x/123.p';
  const TARGET = 'https://www.target.com/p/x/-/A-1';
  const watchStore = (url: string, store: string, read_in_browser: boolean) => ({
    url, store, price: 40, available: true, read_at: '2026-09-10T12:00:00', read: true, read_in_browser,
    first_price: 40, first_at: '2026-09-10T12:00:00', change: null, low: 40, high: 40, history: [],
  });
  const WATCHED = [{
    product_id: 7, set_code: 'tdm', name: 'Reign of Dragons', kind: 'sealed', finish: null, category: 'deck', subtype: null, release_date: '2025-04-11',
    best_price: 40, best_store: 'Best Buy', best_url: BESTBUY, target: null, target_price: null, target_met: null,
    stores: [watchStore(BESTBUY, 'Best Buy', true), watchStore(TARGET, 'Target', true), watchStore('https://manyrealms.com/products/rod', 'Many Realms', false)],
  }];
  const watchingRoutes = async (page: Page, onJob: (body: Record<string, unknown>) => void) => {
    await page.route('**/api/deals/watched', (r) => r.fulfill({ json: WATCHED }));
    await page.route('**/api/market/product-cost?*', (r) => r.fulfill({ status: 404, json: { detail: 'n/a' } }));
    await page.route('**/api/jobs/deals.watchlist', (r) => { onJob(r.request().postDataJSON()); return r.fulfill({ status: 500, json: { detail: 'stop here' } }); });
  };

  test('Watching: open-tab stores are read in this browser, only the watched links, and handed to the read', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    const data = {
      urls: [{ url: BESTBUY, store: 'Best Buy', open: true }, { url: TARGET, store: 'Target', open: false }],
      pages: { [BESTBUY]: { title: 'Reign of Dragons', head: '', ld: [], text: '$39.99' } },
      warnings: [{ code: 'watched.load_timeout', url: TARGET }],
    };
    await fakeCompanion(page, { answers: { watched: { ok: true, data } } });
    let jobBody: Record<string, unknown> | null = null;
    await watchingRoutes(page, (b) => { jobBody = b; });
    await page.goto('/market?subject=deals&deals=watching');
    await expect(page.getByText('Open-tab stores are read in this browser by the companion')).toBeVisible();
    await page.getByRole('button', { name: 'Read watched prices' }).click();
    await expect(page.getByText('Waiting for you to approve in the companion window')).toBeVisible();
    await expect.poll(() => jobBody).not.toBeNull();
    expect(jobBody).toEqual({ refresh: true, in_browser: true, pages: data.pages });
    const asked = await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests);
    expect(asked).toEqual([{ kind: 'watched', params: { urls: [BESTBUY, TARGET] } }]);   // the server-read store isn't asked for
    await expect(page.getByText('didn’t finish loading')).toBeVisible();
  });

  test('Watching: declined in the companion window → nothing is read', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    await fakeCompanion(page, { answers: { watched: { ok: false, code: 'request.denied', message: 'You chose not to send it. Nothing was sent.' } } });
    let jobBody: unknown = null;
    await watchingRoutes(page, (b) => { jobBody = b; });
    await page.goto('/market?subject=deals&deals=watching');
    await page.getByRole('button', { name: 'Read watched prices' }).click();
    await expect(page.getByRole('status').filter({ hasText: 'Nothing was sent' })).toBeVisible();
    expect(jobBody).toBeNull();
  });

  test('Watching without the companion reads on this Mac, as before', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    let jobBody: unknown = null;
    await watchingRoutes(page, (b) => { jobBody = b; });
    await page.goto('/market?subject=deals&deals=watching');
    await page.getByRole('button', { name: 'Read watched prices' }).click();
    await expect.poll(() => jobBody).toEqual({ refresh: true });
  });

  test('Deals not allowed in the companion: points to its one Allow access switch', async ({ page }) => {
    await flags(page, { companion: true, deals: true });
    await fakeCompanion(page, { answers: { tabs: { ok: false, code: 'permission.deals_off' } } });
    await page.route('**/api/deals/watched', (r) => r.fulfill({ json: [] }));
    await page.goto('/market?subject=deals');
    await page.getByRole('button', { name: 'Read my open tabs' }).click();
    await expect(page.getByRole('alert')).toContainText('switch on Allow access');
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
    await page.getByRole('tab', { name: 'Add decklist or product' }).click();
    await page.getByRole('searchbox', { name: 'Deck link or product' }).fill(DECK.url);
    await expect(page.getByText('Read in this browser by the companion, so your private decks work too. You approve what it sends.')).toBeVisible();
    await page.getByRole('button', { name: 'Read deck' }).click();
    await page.getByRole('button', { name: 'Add…' }).click();
    await expect(page.getByRole('heading', { name: 'Goblin Party' })).toBeVisible();
    expect(body).toEqual({ source: 'moxfield', deck: DECK.deck });
    expect(await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests)).toEqual([{ kind: 'moxfield', params: { url: DECK.url } }]);
  });

  test('a private deck names the fix', async ({ page }) => {
    await flags(page, { companion: true });
    await fakeCompanion(page, { answers: { moxfield: { ok: false, code: 'moxfield.private' } } });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await page.getByRole('tab', { name: 'Add decklist or product' }).click();
    await page.getByRole('searchbox', { name: 'Deck link or product' }).fill(DECK.url);
    await page.getByRole('button', { name: 'Read deck' }).click();
    await expect(page.getByRole('alert')).toContainText('Moxfield says this is private to its owner');
  });
});
