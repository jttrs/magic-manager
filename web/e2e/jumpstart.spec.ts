import { expect, fixtures, mockApi, test } from './support';

type Page = Parameters<typeof mockApi>[0];

const printing = (id: string, name: string, type: string) => ({
  scryfall_id: id, oracle_id: null, name, set_code: 'msh', set_name: 'Marvel Super Heroes', collector_number: '1', rarity: 'common', finishes: ['nonfoil'],
  treatment: '', image_uri: null, price_usd: 0.2, price_usd_foil: null, released_at: '2026-06-26', type_line: type, cmc: 2, owned: { nonfoil: 1 }, free: 1,
});
const card = (id: string, name: string, type: string, count: number, free: number) => ({
  printing: printing(id, name, type), board: 'main', finish: 'nonfoil', count, type_line: type, cmc: 2, color_identity: ['R'], pledged_here: 0, free,
});
const row = (key: string) => fixtures.recipes.recipes.find((r) => r.key === key)!;

const ARMED = {
  recipe: row('fn:Armed_MSH'), ready: true, unknown: [],
  cards: [card('g', 'Iron Fist', 'Legendary Creature — Human', 1, 1), card('h', 'Mountain', 'Basic Land — Mountain', 8, 0)],
};

const SHOP = { code: 'msh', name: 'Marvel Super Heroes', ready: true, close_short: 3, themes: 20, packs: [], buildable: { cards: 30, copies: 42, usd: 29.25 }, whole: { cards: 50, copies: 60, usd: 41 }, whole_packs: 2 };

function sse(events: [string, unknown][]) {
  return events.map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
}
const DONE = sse([['status', { status: 'running' }], ['progress', { done: 1, total: 2, message: 'Spider Society', level: 'info' }], ['result', { summary: 'Read 1 deck recipe', artifacts: [] }], ['status', { status: 'succeeded' }]]);

async function mockJob(page: Page, submitted: unknown[], onDone: () => void) {
  await page.route('**/api/jobs/decks.read_recipes', (r) => {
    submitted.push(r.request().postDataJSON());
    return r.fulfill({ status: 202, json: { id: 'rr1', name: 'decks.read_recipes', title: 'Read deck recipes', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/rr1/events', async (r) => {
    onDone();
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: DONE });
  });
}

test('Jumpstart lives in Decks: Collection has no Jumpstart tab, old links open the same pack there', async ({ page }) => {
  await mockApi(page, { '/api/recipes/Armed_MSH': () => ({ json: ARMED }) });
  await page.goto('/collection');
  await expect(page.getByRole('navigation', { name: 'Collection views' }).getByRole('link', { name: 'Jumpstart' })).toHaveCount(0);

  await page.goto('/collection/jumpstart?set=msh&pack=Armed_MSH&show=build');
  await expect(page).toHaveURL(/\/decks\?/);
  await expect(page).toHaveURL(/deck=fn%3AArmed_MSH/);
  const list = page.getByRole('navigation', { name: 'Deck recipes' });
  await expect(list.getByRole('button')).toHaveCount(1);
  await expect(list.getByRole('button', { name: /^Armed/ })).toHaveAttribute('aria-current', 'true');
  await expect(page.getByRole('heading', { level: 2, name: 'Armed' })).toBeVisible();
  await expect(page.getByText('Free cards cover')).toBeVisible();
  await page.getByRole('radio', { name: 'List' }).click();
  await expect(page.getByText('None free')).toBeVisible();
  await expect(page.getByText('×8 in deck')).toBeVisible();
});

test('one Jumpstart set in view: the Buy strip copies either shopping list', async ({ page }) => {
  const buys: unknown[] = [];
  await mockApi(page, { '/api/jumpstart/msh': () => ({ json: SHOP }) });
  await page.route('**/api/jumpstart/msh/buy-list', (r) => {
    const body = r.request().postDataJSON() as { shop: string; target: string };
    buys.push(body);
    return r.fulfill({ json: { text: `${body.shop}:${body.target}`, lines: 1 } });
  });
  await page.goto('/decks?sets=%5B%22msh%22%5D');
  await expect(page.getByText('Copy bulk lists · 42 cards to build every theme · ≈ $29.25 at market')).toBeVisible();
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('buildable:manapool');
  await page.getByRole('radio', { name: 'Packs I don’t own' }).click();
  await expect(page).toHaveURL(/shop=packs/);
  await page.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  expect(buys).toEqual([{ shop: 'buildable', target: 'manapool' }, { shop: 'packs', target: 'tcgplayer' }]);
  // A set without Jumpstart packs has no Buy strip.
  await page.goto('/decks?sets=%5B%22msc%22%5D');
  await expect(page.getByRole('navigation', { name: 'Deck recipes' }).getByRole('button').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: /Buy/ })).toHaveCount(0);
});

test('a recipe never read reads its card list once, then shows it', async ({ page }) => {
  let ready = false;
  const submitted: unknown[] = [];
  const spider = { recipe: row('fn:SpiderSociety_MSC'), unknown: [] };
  await mockApi(page, {
    '/api/recipes/SpiderSociety_MSC': () => ({ json: ready ? { ...spider, ready: true, cards: ARMED.cards } : { ...spider, ready: false, cards: [] } }),
  });
  await mockJob(page, submitted, () => (ready = true));
  await page.goto('/decks?own=%5B%22none%22%5D&deck=fn%3ASpiderSociety_MSC&view=list');
  await expect(page.getByRole('button', { name: 'Inspect Iron Fist' })).toBeVisible();
  expect(submitted).toEqual([{ file_names: ['SpiderSociety_MSC'] }]);
});

test('a failed read says why and Try again starts it once more', async ({ page }) => {
  const submitted: unknown[] = [];
  const spider = { recipe: row('fn:SpiderSociety_MSC'), unknown: [], ready: false, cards: [] };
  await mockApi(page, { '/api/recipes/SpiderSociety_MSC': () => ({ json: spider }) });
  await page.route('**/api/jobs/decks.read_recipes', (r) => {
    submitted.push(r.request().postDataJSON());
    return r.fulfill({ status: 202, json: { id: `rf${submitted.length}`, name: 'decks.read_recipes', title: 'Read deck recipes', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  const FAILED = sse([['status', { status: 'running' }], ['error', { error: 'Couldn’t sync prices for card set(s): MSC.' }], ['status', { status: 'failed' }]]);
  await page.route('**/api/jobs/rf*/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: FAILED }));
  await page.goto('/decks?own=%5B%22none%22%5D&deck=fn%3ASpiderSociety_MSC');
  await expect(page.getByRole('alert')).toContainText('MSC');
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect.poll(() => submitted.length).toBe(2);
});

test('one set in view: read every unread recipe in it', async ({ page }) => {
  const submitted: unknown[] = [];
  await mockApi(page);
  await mockJob(page, submitted, () => {});
  await page.goto('/decks?own=%5B%22built%22%2C%22loose%22%2C%22none%22%5D&sets=%5B%22msc%22%5D');
  await page.getByRole('toolbar', { name: 'Deck list actions' }).getByRole('button', { name: 'Read 1 unread recipe in MSC' }).click();
  await expect.poll(() => submitted).toEqual([{ set: 'msc' }]);
});
