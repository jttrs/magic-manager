import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, test } from './support';

const IMG = 'https://cards.scryfall.io/normal/front/x.jpg';
const printing = (id: string, o: Record<string, unknown> = {}) => ({
  scryfall_id: id, oracle_id: 'o-sol', name: 'Sol Ring', set_code: 'cmm', set_name: 'Commander Masters',
  collector_number: id.replace(/\D/g, '') || '1', rarity: 'uncommon', finishes: ['nonfoil', 'foil'], treatment: '',
  image_uri: IMG, price_usd: 1.5, price_usd_foil: 3, released_at: '2023-08-04', owned: {}, ...o,
});
const resolved = {
  format: 'moxfield', deck_name: null, warnings: [],
  lines: [
    { line: 1, raw: '4 Lightning Bolt (M10) 146', qty: 4, name: 'Lightning Bolt', finish: 'nonfoil', section: 'mainboard', status: 'exact', candidates: [printing('bolt146', { name: 'Lightning Bolt', set_code: 'm10' })], chosen: 'bolt146', note: null },
    { line: 2, raw: '1 Sol Ring', qty: 1, name: 'Sol Ring', finish: 'nonfoil', section: 'mainboard', status: 'ambiguous', candidates: [printing('sol1', { owned: { nonfoil: 2 } }), printing('sol2', { set_code: 'soc', finishes: ['foil'] })], chosen: 'sol1', note: null },
    { line: 3, raw: '1 Notacard', qty: 1, name: 'Notacard', finish: 'nonfoil', section: 'mainboard', status: 'unresolved', candidates: [], chosen: null, note: "No card named 'Notacard'" },
  ],
};

async function captureCommit(page: Page) {
  const bodies: unknown[] = [];
  await page.route('**/api/ingest/commit', (r) => {
    const b = r.request().postDataJSON() as { items: { qty: number; scryfall_id: string }[] };
    bodies.push(b);
    const copies = b.items.reduce((s, i) => s + i.qty, 0);
    return r.fulfill({ json: { ingest_id: 7, copies, printings: b.items.length, summary: `+${copies} copies · ${b.items.length} printings` } });
  });
  return bodies;
}

function sse(events: [string, unknown][]) {
  return events.map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
}
const job = (id: string, name: string) => ({ id, name, title: name, inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });

test('search: press printings to stage copies, then add them in one commit', async ({ page }) => {
  await page.route('**/api/ingest/search**', (r) => r.fulfill({ json: { query: 'sol', source: 'local', printings: [printing('sol1'), printing('sol2', { finishes: ['nonfoil', 'foil'] })] } }));
  const bodies = await captureCommit(page);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Add cards' }).click();
  await expect(page.getByRole('dialog', { name: 'Add cards' })).toBeVisible();
  await page.getByRole('searchbox', { name: 'Card name' }).fill('sol');
  await page.getByRole('button', { name: /^Add Sol Ring, CMM · 1/ }).click();
  await page.getByRole('button', { name: /^Add Sol Ring, CMM · 1/ }).click();
  await page.getByRole('button', { name: /^Add Sol Ring foil, CMM · 2/ }).click();
  await expect(page.getByRole('list', { name: 'Cards to add' }).getByRole('listitem')).toHaveCount(2);
  await page.getByRole('button', { name: 'Add 3 copies' }).click();
  await expect(page.getByRole('status')).toContainText('Added 3 copies · 2 printings');
  expect(bodies[0]).toEqual({ source: 'search', label: null, items: [{ scryfall_id: 'sol1', finish: 'nonfoil', qty: 2 }, { scryfall_id: 'sol2', finish: 'foil', qty: 1 }] });
});

test('paste: resolve → review (pick printing, finish refits, unresolved left out) → commit', async ({ page }) => {
  await page.route('**/api/ingest/resolve', (r) => r.fulfill({ json: resolved }));
  const bodies = await captureCommit(page);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Add cards' }).click();
  await page.getByRole('tab', { name: 'Paste a list' }).click();
  await page.getByRole('button', { name: 'Read list' }).click();
  await expect(page.getByRole('alert')).toContainText('Paste at least one line');
  await page.getByRole('textbox', { name: 'Card list' }).fill('4 Lightning Bolt (M10) 146\n1 Sol Ring\n1 Notacard');
  await page.getByRole('button', { name: 'Read list' }).click();
  const list = page.getByRole('list', { name: 'Pasted cards' });
  await expect(list.getByRole('listitem')).toHaveCount(3);
  await expect(page.getByText('1 not found')).toBeVisible();
  await expect(page.getByRole('checkbox', { name: 'Include Notacard' })).toBeDisabled();
  await page.getByRole('button', { name: /^Printing of Sol Ring/ }).click();
  await page.getByRole('list', { name: 'Printings of Sol Ring' }).getByRole('button').nth(1).click();
  await expect(page.getByText('Foil only')).toBeVisible();
  await page.getByRole('spinbutton', { name: 'Copies of Lightning Bolt' }).fill('3');
  await page.getByRole('button', { name: 'Add 4 copies' }).click();
  await expect(page.getByRole('status')).toContainText('Added 4 copies');
  expect(bodies[0]).toEqual({ source: 'paste', label: null, items: [{ scryfall_id: 'bolt146', finish: 'nonfoil', qty: 3 }, { scryfall_id: 'sol2', finish: 'foil', qty: 1 }] });
  await expect(page.getByRole('textbox', { name: 'Card list' })).toHaveValue('');
});

test('deck URL: fetch job streams, then the deck lands in review and commits with its name', async ({ page }) => {
  await page.route('**/api/jobs/ingest.fetch_deck', (r) => r.fulfill({ status: 202, json: job('jd', 'ingest.fetch_deck') }));
  await page.route('**/api/jobs/jd/events', (r) => r.fulfill({
    status: 200, contentType: 'text/event-stream',
    body: sse([['status', { status: 'running' }], ['progress', { done: 0, total: null, message: 'import_deck: source=archidekt', level: 'info' }], ['result', { summary: 'Goblins · 5 cards to review', artifacts: [{ kind: 'json', label: 'lines', data: { ...resolved, format: 'deck', deck_name: 'Goblins' } }] }], ['status', { status: 'succeeded' }]]),
  }));
  const bodies = await captureCommit(page);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Add cards' }).click();
  await page.getByRole('tab', { name: 'Deck or precon' }).click();
  await page.getByRole('button', { name: 'Fetch deck' }).click();
  await expect(page.getByRole('alert')).toContainText('Paste a deck link from Archidekt');
  await page.getByRole('textbox', { name: /Archidekt/ }).fill('https://archidekt.com/decks/123');
  await page.getByRole('button', { name: 'Fetch deck' }).click();
  await expect(page.getByRole('heading', { name: 'Goblins' })).toBeVisible();
  await page.getByRole('button', { name: 'Add 5 copies' }).click();
  await expect(page.getByRole('status')).toContainText('Added 5 copies');
  expect((bodies[0] as { source: string; label: string }).label).toBe('Goblins');
});

test('precon: search the catalog, add a copy via a job', async ({ page }) => {
  let submitted: unknown;
  await page.route('**/api/ingest/precons**', (r) => r.fulfill({ json: [{ file_name: 'CounterBlitz_FIC', name: 'Counter Blitz', set_code: 'fic', type: 'Commander Deck', release_date: '2025-06-13', default_state: 'built', owned_built: 1, owned_deconstructed: 0 }] }));
  await page.route('**/api/jobs/ingest.precon', (r) => { submitted = r.request().postDataJSON(); return r.fulfill({ status: 202, json: job('jp', 'ingest.precon') }); });
  await page.route('**/api/jobs/jp/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse([['result', { summary: 'Added Counter Blitz ×1 · 100 cards · built', artifacts: [] }], ['status', { status: 'succeeded' }]]) }));
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Add cards' }).click();
  await page.getByRole('tab', { name: 'Deck or precon' }).click();
  await expect(page.getByText('own 1 built, 0 loose')).toBeVisible();
  await page.getByRole('button', { name: 'Add…' }).click();
  await page.getByRole('combobox', { name: 'Keep it' }).selectOption('deconstructed');
  await page.getByRole('button', { name: 'Add to collection' }).click();
  await expect(page.getByText('Added Counter Blitz ×1 · 100 cards · built')).toBeVisible();
  expect(submitted).toEqual({ file_name: 'CounterBlitz_FIC', copies: 1, state: 'deconstructed' });
});
