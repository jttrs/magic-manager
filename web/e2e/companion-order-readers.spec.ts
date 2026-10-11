// Pinned behaviour of the companion's ORDER HISTORY readers (extension/src/readers/*-orders.js),
// run in real Chromium against saved, de-personalised pages in tests/fixtures/companion/.
// The *.expected.json goldens are fed to the server's strict models + the purchases engine by
// tests/test_companion_orders.py, so reader → app → engine stays one chain.
//
// Re-pin on purpose:  UPDATE_GOLDEN=1 npm --prefix web run e2e -- companion-order-readers
// A site changed its page? Follow .claude/skills/scrape-doctor/SKILL.md.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ROOT = resolve(import.meta.dirname, '../..');
const FIX = resolve(ROOT, 'tests/fixtures/companion');
const reader = (name: string) => readFileSync(resolve(ROOT, 'extension/src/readers', name), 'utf8');
const fixture = (name: string) => readFileSync(resolve(FIX, name), 'utf8');

function golden(name: string, actual: unknown) {
  const path = resolve(FIX, name);
  if (process.env.UPDATE_GOLDEN || !existsSync(path)) writeFileSync(path, JSON.stringify(actual, null, 2) + '\n');
  expect(actual).toEqual(JSON.parse(readFileSync(path, 'utf8')));
}

async function serve(page: Page, url: string, html: string, script: string) {
  await page.unrouteAll();
  // Offline: the saved page is served; everything else it references (images, fonts) is refused.
  await page.route('**/*', (r) => (r.request().url() === url
    ? r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html })
    : r.fulfill({ status: 404, body: '' })));
  await page.goto(url, { waitUntil: 'domcontentloaded' });  // TCGplayer's thumbnail onerror fallback never settles offline
  await page.addScriptTag({ content: reader(script) });
}

type W = Record<string, (d: Document) => unknown>;
const call = (page: Page, fn: string) => page.evaluate((f) => (window as unknown as W)[f](document), fn);
const PERSONAL = ['Torre', '20th Ave', 'Seattle', 'Ending with', 'Tracking', 'ups.com'];

test.describe('Mana Pool order history', () => {
  test('order list: number, placed (UTC), total and page link; no replacement suborders', async ({ page }) => {
    await serve(page, 'https://manapool.com/settings/orders', fixture('manapool-orders.html'), 'manapool-orders.js');
    const out = await call(page, 'readManaPoolOrderList') as { ok: boolean; orders: { order_id: string; ordered_at: string; total: number; path: string }[] };
    expect(out.ok).toBe(true);
    expect(out.orders.map((o) => [o.order_id, o.ordered_at, o.total])).toEqual([
      ['100102', '2026-09-23T18:07:31Z', 123.45],
      ['100101', '2026-02-18T06:42:00Z', 76.36],
    ]);
    expect(out.orders.every((o) => !o.path.includes('suborder'))).toBe(true);
    golden('manapool-orders.expected.json', out);
  });

  test('order page: each line’s exact printing, finish, condition, quantity and unit price; the totals; nothing personal', async ({ page }) => {
    await serve(page, 'https://manapool.com/settings/orders/00000000-0000-4000-8000-000000000102', fixture('manapool-order.html'), 'manapool-orders.js');
    expect(await call(page, 'manaPoolShowItems')).toBe(true);
    const out = await call(page, 'readManaPoolOrder') as { ok: boolean; order: { order_id: string; ordered_on: string; lines: { name: string; kind: string; finish: string; quantity: number; price: number; set_code: string | null; scryfall_id: string | null }[]; subtotal: number; shipping: number; tax: number; fees: number; credit: number; total: number }; warnings: unknown[] };
    expect(out.ok).toBe(true);
    expect(out.warnings).toEqual([]);
    const o = out.order;
    expect([o.order_id, o.ordered_on]).toEqual(['100102', '2026-09-23']);
    expect(o.lines.map((l) => [l.name, l.kind, l.finish, l.quantity, l.price])).toEqual([
      ['The Swarmweaver', 'single', 'nonfoil', 2, 0.15],
      ['Ultra Magnus, Tactician // Ultra Magnus, Armored Carrier', 'single', 'nonfoil', 1, 0.31],
      expect.arrayContaining(['single', 'nonfoil']),
      ['Adventures in the Forgotten Realms Commander Decks Set of 4', 'sealed', 'nonfoil', 1, 375],
      ['Muldrotha, the Gravetide', 'single', 'nonfoil', 1, 1],
      expect.arrayContaining(['single', 'foil']),
      expect.arrayContaining(['single', 'foil']),
    ]);
    expect(o.lines.filter((l) => l.kind === 'single').every((l) => l.scryfall_id && l.set_code)).toBe(true);
    expect([o.subtotal, o.shipping, o.fees, o.credit, o.tax, o.total]).toEqual([494.28, 2.7, 23.85, 28.61, 51.93, 544.15]);
    const all = JSON.stringify(out);
    for (const s of [...PERSONAL, 'Seller', '/shop/', '100102-1']) expect(all).not.toContain(s);
    golden('manapool-order.expected.json', out);
  });

  test('presses the Item List tab when the page opens on packages', async ({ page }) => {
    const html = fixture('manapool-order.html').replace('data-value="items" data-orientation="horizontal" aria-selected="true"', 'data-value="items" data-orientation="horizontal" aria-selected="false"');
    await serve(page, 'https://manapool.com/settings/orders/x', html, 'manapool-orders.js');
    await page.evaluate(() => { const t = [...document.querySelectorAll('[role="tab"]')].find((x) => x.textContent?.trim() === 'Item List'); t?.addEventListener('click', () => { (window as unknown as { clicked: boolean }).clicked = true; }); });
    await call(page, 'manaPoolShowItems');
    expect(await page.evaluate(() => (window as unknown as { clicked?: boolean }).clicked)).toBe(true);
  });

  for (const [what, url, html, fn, code] of [
    ['the sign-in page', 'https://manapool.com/auth?next=%2Fsettings%2Forders', '<main><h1>Sign in</h1></main>', 'readManaPoolOrderList', 'orders.sign_in'],
    ['a signed-out order list', 'https://manapool.com/settings/orders', '<header><a href="/auth?next=%2Forders">Sign In</a></header><main><h1>Not Found</h1></main>', 'readManaPoolOrderList', 'orders.sign_in'],
    ['a redesigned order list', 'https://manapool.com/settings/orders', '<main><h1>Orders</h1><div>Order 1 $3.00</div></main>', 'readManaPoolOrderList', 'orders.page_changed'],
    ['an account with no orders', 'https://manapool.com/settings/orders', '<main><h1>Orders</h1><p>Showing 0 results</p></main>', 'readManaPoolOrderList', 'orders.none'],
    ['a redesigned order page', 'https://manapool.com/settings/orders/x', '<main><h1>Order #1</h1><div>Sol Ring $1.00</div></main>', 'readManaPoolOrder', 'orders.page_changed'],
  ] as const) {
    test(`says so for ${what} (${code})`, async ({ page }) => {
      await serve(page, url, `<!doctype html><html><body>${html}</body></html>`, 'manapool-orders.js');
      expect(await call(page, fn)).toMatchObject({ ok: false, code });
    });
  }
});

test.describe('TCGplayer order history', () => {
  test('reads every order with its items inline: product id, finish, condition, price; the next page; nothing personal', async ({ page }) => {
    await serve(page, 'https://store.tcgplayer.com/myaccount/orderhistory', fixture('tcgplayer-orders.html'), 'tcgplayer-orders.js');
    const out = await call(page, 'readTcgplayerOrders') as { ok: boolean; next: string; range: string; warnings: unknown[]; orders: { order_id: string; ordered_at: string; subtotal: number; shipping: number; tax: number; total: number; lines: { name: string; kind: string; finish: string; condition: string | null; quantity: number; price: number; tcgplayer_product_id: number }[] }[] };
    expect(out.ok).toBe(true);
    expect(out.warnings).toEqual([]);
    expect([out.next, out.range]).toEqual(['/myaccount/orderhistory?PageNumber=2', '2026']);
    expect(out.orders.map((o) => [o.order_id, o.ordered_at, o.lines.length])).toEqual([
      ['AAAA0001-000001-00001', '2026-09-23', 1], ['AAAA0002-000002-00002', expect.any(String), 1], ['AAAA0003-000003-00003', expect.any(String), 3],
    ]);
    expect(out.orders[0].lines[0]).toMatchObject({ kind: 'sealed', condition: null, price: 665, quantity: 1 });
    expect(out.orders[0]).toMatchObject({ subtotal: 665, shipping: 24.99, tax: 72.79, total: 762.78 });
    expect(out.orders[1].lines[0]).toMatchObject({ kind: 'single', finish: 'foil', condition: 'Near Mint' });
    expect(out.orders[2].lines.map((l) => l.finish)).toEqual(['nonfoil', 'nonfoil', 'foil']);
    expect(out.orders.flatMap((o) => o.lines).every((l) => l.tcgplayer_product_id > 0)).toBe(true);
    const all = JSON.stringify(out);
    for (const s of ['Buyer Name', 'Example St', 'Seller', 'Track', 'sellerfeedback']) expect(all).not.toContain(s);
    golden('tcgplayer-orders.expected.json', out);
  });

  test('a signed-out or redesigned page is named', async ({ page }) => {
    await serve(page, 'https://www.tcgplayer.com/login?returnUrl=x', '<!doctype html><main><h1>Sign in</h1></main>', 'tcgplayer-orders.js');
    expect(await call(page, 'readTcgplayerOrders')).toMatchObject({ ok: false, code: 'orders.sign_in' });
    await serve(page, 'https://store.tcgplayer.com/myaccount/orderhistory', '<!doctype html><main><h2>Order History</h2><div>Order 1</div></main>', 'tcgplayer-orders.js');
    expect(await call(page, 'readTcgplayerOrders')).toMatchObject({ ok: false, code: 'orders.page_changed' });
  });
});

test.describe('Card Kingdom order history', () => {
  test('order list: id, date, total and invoice link — never the page’s embedded order data', async ({ page }) => {
    await serve(page, 'https://www.cardkingdom.com/myaccount/order_history', fixture('cardkingdom-orders.html'), 'cardkingdom-orders.js');
    const out = await call(page, 'readCardKingdomOrderList') as { ok: boolean; orders: { order_id: string; ordered_at: string; total: number; path: string }[] };
    expect(out.ok).toBe(true);
    expect(out.orders).toHaveLength(4);
    expect(out.orders[0]).toMatchObject({ order_id: '900000004', ordered_at: '2026-09-04T16:49', total: 82.9, path: '/myaccount/invoice/900000004' });
    for (const s of ['Buyer Name', 'Example', 'CREDIT', 'track']) expect(JSON.stringify(out)).not.toContain(s);
    golden('cardkingdom-orders.expected.json', out);
  });

  test('invoice: a sealed product line and the totals (singles are unverified → kind other)', async ({ page }) => {
    await serve(page, 'https://www.cardkingdom.com/myaccount/invoice/900000004', fixture('cardkingdom-invoice.html'), 'cardkingdom-orders.js');
    const out = await call(page, 'readCardKingdomInvoice') as { ok: boolean; order: { order_id: string; lines: unknown[]; subtotal: number; shipping: number; tax: number; total: number } };
    expect(out).toMatchObject({ ok: true, order: { order_id: '900000004', subtotal: 74.99, shipping: 0, tax: 7.91, total: 82.9 } });
    expect(out.order.lines).toEqual([{ kind: 'sealed', name: "Universes Beyond: Assassin's Creed Starter Kit", detail: null, quantity: 1, price: 74.99 }]);
    golden('cardkingdom-invoice.expected.json', out);
  });

  test('a line that isn’t a plain product is kept as unverified, never guessed into a card', async ({ page }) => {
    const html = fixture('cardkingdom-invoice.html').replace('<td align=center></td>', '<td align=center>NM Foil</td>');
    await serve(page, 'https://www.cardkingdom.com/myaccount/invoice/900000004', html, 'cardkingdom-orders.js');
    expect(await call(page, 'readCardKingdomInvoice')).toMatchObject({ ok: true, order: { lines: [{ kind: 'other', detail: 'NM Foil' }] }, warnings: [{ code: 'orders.unverified_line', row: 1 }] });
  });
});
