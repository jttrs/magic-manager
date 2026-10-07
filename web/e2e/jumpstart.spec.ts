import { expect, mockApi, test } from './support';

type Page = Parameters<typeof mockApi>[0];

const pack = (o: Record<string, unknown>) => ({
  file_name: 'Angels1_J25', name: 'Angels (1)', theme: 'Angels', version: 1, color: 'W', card_count: 20, usd_total: 5.15, top_card: 'Giada, Font of Hope',
  top_card_usd: 0.5, top_card_image: 'https://cards.scryfall.io/normal/front/x.jpg', front_card: 'Angels', built: 1, deconstructed: 1, deck_slug: 'pack:angels-1-j25',
  have: 20, short: 0, status: 'build', ...o,
});

const VIEW = {
  code: 'j25', name: 'Foundations Jumpstart', ready: true, close_short: 3, themes: 3,
  packs: [
    pack({}),
    pack({ file_name: 'Angels2_J25', name: 'Angels (2)', version: 2, built: 0, deconstructed: 0, deck_slug: null, have: 18, short: 2, status: 'close' }),
    pack({ file_name: 'Pirates1_J25', name: 'Pirates (1)', theme: 'Pirates', color: 'U', top_card: 'Spyglass Siren', built: 0, deconstructed: 0, deck_slug: null, have: 9, short: 11, status: 'far' }),
    pack({ file_name: 'Wizards_J25', name: 'Wizards', theme: 'Wizards', version: null, color: 'UR', built: 0, deconstructed: 1, have: 4, short: 16, status: 'far' }),
  ],
  buildable: { cards: 30, copies: 42, usd: 29.25 },
  whole: { cards: 50, copies: 60, usd: 41 },
  whole_packs: 2,
};

const printing = (id: string, name: string, type: string) => ({
  scryfall_id: id, oracle_id: null, name, set_code: 'j25', set_name: 'Foundations Jumpstart', collector_number: '1', rarity: 'common', finishes: ['nonfoil'],
  treatment: '', image_uri: null, price_usd: 0.2, price_usd_foil: null, released_at: '2024-11-15', type_line: type, cmc: 2, owned: { nonfoil: 1 }, free: 1,
});

const DETAIL = {
  pack: VIEW.packs[1],
  cards: [
    { printing: printing('g', 'Giada, Font of Hope', 'Legendary Creature — Angel'), count: 1, foil: false, unit_usd: 0.5, free: 1 },
    { printing: printing('h', 'Herald of War', 'Creature — Angel'), count: 2, foil: false, unit_usd: 2.43, free: 0 },
  ],
  unknown: [],
};

async function mockJumpstart(page: Page, view: () => unknown = () => VIEW, buys: unknown[] = []) {
  await mockApi(page, {
    '/api/jumpstart/j25/packs/': () => ({ json: DETAIL }),
    '/api/jumpstart/j25': () => ({ json: view() }),
    '/api/jumpstart': () => ({ json: { sets: [{ code: 'j25', name: 'Foundations Jumpstart', released: '2024-11-15', packs: 121, themes: 46, owned_packs: 49 }] } }),
  });
  await page.route('**/api/jumpstart/j25/buy-list', (r) => {
    const body = r.request().postDataJSON() as { shop: string; target: string };
    buys.push(body);
    return r.fulfill({ json: { text: `${body.shop}:${body.target}`, lines: 1 } });
  });
}

test('Jumpstart is a Collection sheet: pack versions by colour, ready/close filters, a pack’s cards', async ({ page }) => {
  await mockJumpstart(page);
  await page.goto('/collection');
  await page.getByRole('navigation', { name: 'Collection views' }).getByRole('link', { name: 'Jumpstart' }).click();
  await expect(page).toHaveURL(/\/collection\/jumpstart/);
  await expect(page.getByText('Foundations Jumpstart ·')).toBeVisible();
  await expect(page.getByText('4 pack versions of 3 themes · you own 2 · 1 ready to build from free cards · 1 close')).toBeVisible();

  const list = page.getByRole('navigation', { name: 'Jumpstart packs' });
  await expect(list.getByRole('heading')).toHaveText([/White/, /Blue/, /Multicolour/]);
  await expect(list.getByRole('button', { name: /Angels \(1\)/ })).toContainText('All 20 free');
  await expect(list.getByRole('button', { name: /Angels \(1\)/ })).toContainText('×1 built');
  await expect(list.getByRole('button', { name: /Angels \(2\)/ })).toContainText('2 short');
  await expect(list.getByRole('button', { name: /Pirates/ })).toContainText('9 of 20 free');

  await page.getByRole('button', { name: /^Packs/ }).click();
  await page.getByRole('menuitemradio', { name: /Close/ }).click();
  await expect(page).toHaveURL(/show=close/);
  await expect(list.getByRole('button')).toHaveCount(1);

  await list.getByRole('button', { name: /Angels \(2\)/ }).click();
  await expect(page).toHaveURL(/pack=Angels2_J25/);
  await expect(page.getByRole('heading', { level: 2, name: 'Angels (2)' })).toBeVisible();
  await expect(page.getByText('Free cards cover')).toBeVisible();
  await expect(page.getByText('None free')).toBeVisible();
  await expect(page.getByText('×2 in pack')).toBeVisible();
});

test('the Buy strip copies either shopping list through the store targets', async ({ page }) => {
  const buys: unknown[] = [];
  await mockJumpstart(page, () => VIEW, buys);
  await page.goto('/collection/jumpstart?set=j25');
  await expect(page.getByText('Copy bulk lists · 42 cards to build every theme · ≈ $29.25 at market')).toBeVisible();
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('buildable:manapool');

  await page.getByRole('radio', { name: 'Packs I don’t own' }).click();
  await expect(page).toHaveURL(/shop=packs/);
  await expect(page.getByText('Copy bulk lists · 2 packs you don’t own · 60 cards · ≈ $41.00 at market')).toBeVisible();
  await page.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe('packs:tcgplayer');
  expect(buys).toEqual([{ shop: 'buildable', target: 'manapool' }, { shop: 'packs', target: 'tcgplayer' }]);
});

test('a set never read fetches its pack lists once, then shows them', async ({ page }) => {
  let ready = false;
  let submitted: unknown = null;
  await mockJumpstart(page, () => (ready ? VIEW : { code: 'j25', name: 'Foundations Jumpstart', ready: false, close_short: 3, packs: [], themes: 0, buildable: null, whole: null, whole_packs: 0 }));
  const sse = [
    ['status', { status: 'running' }],
    ['progress', { done: 1, total: 3, message: 'Angels (1)', level: 'info' }],
    ['result', { summary: 'J25: read 121 packs', artifacts: [] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/jobs/jumpstart.read', (r) => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ status: 202, json: { id: 'js1', name: 'jumpstart.read', title: 'Read a Jumpstart set’s packs', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/js1/events', async (r) => {
    ready = true;
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse });
  });
  await page.goto('/collection/jumpstart?set=j25');
  await expect(page.getByRole('navigation', { name: 'Jumpstart packs' }).getByRole('button', { name: /Angels \(1\)/ })).toBeVisible();
  expect(submitted).toEqual({ code: 'j25' });
});
