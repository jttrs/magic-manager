// Store orders (purchases flag): the Orders list with totals, reading orders through the
// companion (stood in for here), and matching an order's lines to cards you own.
import type { Page } from '@playwright/test';
import history from './fixtures/history.json' with { type: 'json' };
import { expect, test } from './support';

const STORES = [
  { key: 'manapool', name: 'Mana Pool', verification: 'verified', note: 'Checked against real Mana Pool order pages.', needs_permission: false },
  { key: 'tcgplayer', name: 'TCGplayer', verification: 'partial', note: 'Order list checked; order details not yet.', needs_permission: true },
  { key: 'cardkingdom', name: 'Card Kingdom', verification: 'unverified', note: 'Not checked against a real page yet.', needs_permission: true },
];
const ORDER = (o: Record<string, unknown>) => ({
  store: 'manapool', store_name: 'Mana Pool', ordered_at: '2026-09-20', read_at: '2026-09-21', lines: 2, copies: 4, assigned: 0, assignable: 3, unresolved: 1,
  status: 'new', paid_usd: 10, worth_usd: 12.5, compared_paid_usd: 10, gain_usd: 2.5, ...o,
});
const PURCHASES = {
  purchases: [
    ORDER({ purchase_id: 1, order_id: 'MP-111', status: 'new' }),
    ORDER({ purchase_id: 2, order_id: 'MP-222', status: 'partial', assigned: 1, paid_usd: 20, worth_usd: 15, compared_paid_usd: 20, gain_usd: -5, ordered_at: '2026-08-02' }),
  ],
  paid_usd: 30, compared_paid_usd: 30, worth_usd: 27.5, gain_usd: -2.5,
};
const PRINTING = { scryfall_id: '8d8432a7-1c8a-4cfb-947c-ecf9791063eb', oracle_id: null, name: 'Sol Ring', set_code: 'cmm', set_name: 'Commander Masters', collector_number: '400', rarity: 'uncommon' };
const REVIEW = {
  purchase: { ...PURCHASES.purchases[0], shipping_usd: 1.25, tax_usd: 0.5, total_usd: 11.75, subtotal_usd: 9.5 },
  lines: [
    { line_no: 1, kind: 'single', name: 'Sol Ring', set_name: 'Commander Masters', condition: 'NM', finish: 'nonfoil', printing: PRINTING, quantity: 3, unit_usd: 2, today_usd: 3, matched: 0, added: 0, remaining: 3, owned: 2, matchable: 2 },
    { line_no: 2, kind: 'sealed', name: 'Bloomburrow Play Booster Box', set_name: null, condition: null, finish: 'nonfoil', printing: null, quantity: 1, unit_usd: 4, today_usd: null, matched: 0, added: 0, remaining: 1, owned: 0, matchable: 0 },
  ],
};

async function flags(page: Page, f: Record<string, boolean>) {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: f } }));
}

/** The purchases API, recording what the app posts. */
async function purchasesApi(page: Page) {
  const posted: { orders?: unknown; apply?: unknown } = {};
  await page.route('**/api/history', (r) => r.fulfill({ json: history }));
  await page.route((u) => u.pathname.startsWith('/api/purchases'), (r) => {
    const { pathname } = new URL(r.request().url());
    const method = r.request().method();
    if (pathname === '/api/purchases/stores') return r.fulfill({ json: STORES });
    if (pathname === '/api/purchases/orders' && method === 'POST') {
      posted.orders = r.request().postDataJSON();
      return r.fulfill({ json: { saved: 1, skipped: ['MP-222'], unresolved: 1, purchase_ids: [3] } });
    }
    if (pathname === '/api/purchases') return r.fulfill({ json: PURCHASES });
    if (pathname === '/api/purchases/1/apply') {
      posted.apply = r.request().postDataJSON();
      return r.fulfill({ json: { purchase_id: 1, ingest_id: 9, matched: 2, added: 0 } });
    }
    if (pathname === '/api/purchases/1') return r.fulfill({ json: REVIEW });
    return r.fulfill({ status: 404, json: { detail: 'unmocked' } });
  });
  return posted;
}

async function fakeCompanion(page: Page, answers: Record<string, unknown>) {
  await page.addInitScript((answers) => {
    const CHANNEL = 'magic-manager/companion';
    const w = window as unknown as { __companionRequests: unknown[] };
    w.__companionRequests = [];
    const post = (m: Record<string, unknown>) => window.postMessage({ ...m, channel: CHANNEL, from: 'companion' }, location.origin);
    window.addEventListener('message', (ev) => {
      const d = ev.data;
      if (ev.source !== window || !d || d.channel !== CHANNEL || d.from !== 'app') return;
      if (d.type === 'ping') post({ type: 'hello', version: '0.2.0', features: { cart: true, deals: true, moxfield: true, orders_tcgplayer: false } });
      if (d.type === 'request') {
        w.__companionRequests.push({ kind: d.kind, params: d.params });
        post({ type: 'ack', id: d.id, ok: true, status: 'awaiting_approval', summary: 'your orders' });
        setTimeout(() => post({ type: 'result', id: d.id, kind: d.kind, ok: true, data: (answers as Record<string, unknown>)[d.kind] }), 200);
      }
    });
  }, answers);
}

test('Orders list: totals for every order, and Paid / Worth / gain on each row', async ({ page }) => {
  await flags(page, { purchases: true });
  await purchasesApi(page);
  await page.goto('/collection/history?orders=true');
  const list = page.getByRole('navigation', { name: 'Store orders' });
  const totals = list.getByLabel('All orders');
  await expect(totals).toContainText('$30.00');
  await expect(totals).toContainText('$27.50');
  await expect(totals).toContainText('−$2.50');
  const row = list.getByRole('button', { name: /Mana Pool order #MP-111/ });
  await expect(row).toContainText('Not added yet');
  await expect(row).toContainText('$10.00');
  await expect(row).toContainText('$12.50');
  await expect(row).toContainText('+$2.50');
  await expect(list.getByRole('button', { name: /MP-222/ })).toContainText('−$5.00');
});

test('reading orders: list, already-read marked, the chosen ones are read and saved', async ({ page }) => {
  await flags(page, { purchases: true });
  const posted = await purchasesApi(page);
  const orderList = {
    store: 'manapool',
    orders: [
      { order_id: 'MP-111', ordered_at: '2026-09-20', total: 11.75, lines: 2 },
      { order_id: 'MP-222', ordered_at: '2026-08-02', total: 20, lines: 1 },
      { order_id: 'MP-333', ordered_at: '2026-07-01', total: 8, lines: 1 },
    ],
    warnings: [],
  };
  const full = { order_id: 'MP-333', ordered_at: '2026-07-01', lines: [{ kind: 'single', name: 'Sol Ring', quantity: 1, price: 8 }], total: 8 };
  await fakeCompanion(page, { order_list: orderList, orders: { store: 'manapool', orders: [full], warnings: [] } });
  await page.goto('/collection/history');
  await page.getByRole('button', { name: 'Read my orders' }).click();
  const d = page.getByRole('dialog', { name: 'Read my orders' });
  await expect(d).toContainText('Verified');
  await expect(d).toContainText('Switch on Order history in the companion’s settings to read TCGplayer orders.');
  await d.getByRole('button', { name: 'Read order list' }).click();
  await expect(d.getByText('Order #MP-333')).toBeVisible();
  await expect(d.getByText('Read · Partly added')).toBeVisible();
  await expect(d.getByText('Read · Not added yet')).toBeVisible();
  await expect(d.getByRole('checkbox', { name: /MP-333/ })).toBeChecked();
  await expect(d.getByRole('checkbox', { name: /MP-222/ })).not.toBeChecked();
  await d.getByRole('button', { name: 'Read 1 order' }).click();
  await expect(d).toContainText('Saved 1 order.');
  await expect(d).toContainText('1 order skipped — already in your collection');
  await expect(d).toContainText('1 line with no exact printing — recorded only');
  expect(posted.orders).toEqual({ store: 'manapool', orders: [full], warnings: [] });
  const asked = await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests);
  expect(asked).toEqual([{ kind: 'order_list', params: { store: 'manapool' } }, { kind: 'orders', params: { store: 'manapool', ids: ['MP-333'] } }]);
});

test('reviewing an order: match to cards I own fills the boxes, Save posts them', async ({ page }) => {
  await flags(page, { purchases: true });
  const posted = await purchasesApi(page);
  await page.goto('/collection/history?orders=true&order=1');
  await expect(page.getByRole('heading', { level: 2, name: /Mana Pool order #MP-111/ })).toBeVisible();
  await expect(page.getByText('Store subtotal')).toBeVisible();
  await expect(page.getByText(/subtotal is \$9\.50/)).toBeVisible();
  await expect(page.getByText('Recorded only — not added to your collection')).toBeVisible();
  await page.getByRole('button', { name: 'Match to cards I own' }).click();
  await expect(page.getByRole('spinbutton', { name: 'Match Sol Ring' })).toHaveValue('2');
  await expect(page.getByRole('spinbutton', { name: 'Add Sol Ring' })).toHaveValue('0');
  await expect(page.getByText('Matches 2 copies you own, adds 0 new')).toBeVisible();
  await page.getByRole('button', { name: 'Save to collection' }).click();
  await expect(page.getByText('Saved: matched 2 copies, added 0 new.')).toBeVisible();
  expect(posted.apply).toEqual({ lines: [{ line_no: 1, match: 2, add: 0 }] });
});
