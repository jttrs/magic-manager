import type { Page } from '@playwright/test';
import collectionZnr from './fixtures/collection-znr.json' with { type: 'json' };
import familiesUnowned from './fixtures/families-unowned.json' with { type: 'json' };
import { expect, mockApi, test } from './support';

type Body = { family: string; changes: { scryfall_id: string; finish: string; qty: number; expected: number }[] };

/** The offline API plus a family you own nothing from (Zendikar Rising), listed only with include=unowned. */
async function mockUnowned(page: Page, saves: Body[]) {
  await mockApi(page);
  await page.route('**/api/collection/families**', (r) => {
    const url = new URL(r.request().url());
    return url.searchParams.get('include') === 'unowned' ? r.fulfill({ json: familiesUnowned }) : r.fallback();
  });
  await page.route('**/api/collection?**', (r) => {
    const url = new URL(r.request().url());
    return url.pathname === '/api/collection' && url.searchParams.getAll('families').includes('znr') ? r.fulfill({ json: collectionZnr }) : r.fallback();
  });
  await page.route('**/api/collection/checklist', (r) => {
    const body = r.request().postDataJSON() as Body;
    saves.push(body);
    return r.fulfill({ json: { ingest_id: 11, added: body.changes.length, updated: 0, zeroed: 0, copies_added: 7, copies_removed: 0, rows: body.changes.map((c) => ({ scryfall_id: c.scryfall_id, finish: c.finish, old_qty: 0, new_qty: c.qty })) } });
  });
}

const card = (name: string) => collectionZnr.cards.find((c) => c.name === name)!;
const plus = (page: Page, name: string) => page.getByRole('button', { name: new RegExp(`^Add one nonfoil .*\\(${name}\\)$`) });

test('open a family you own nothing from, tap in cards, hold for an amount, add them in one save', async ({ page }) => {
  const saves: Body[] = [];
  await mockUnowned(page, saves);
  await page.goto('/collection');

  // The switch lists families you don't own, newest first, after yours.
  await page.getByRole('button', { name: /Set families/ }).click();
  await expect(page.getByRole('checkbox', { name: 'Zendikar Rising' })).toHaveCount(0);
  await page.getByRole('checkbox', { name: 'Include families you don’t own' }).check();
  await page.getByRole('checkbox', { name: /^Zendikar Rising/ }).check();
  await page.keyboard.press('Escape');

  // Owning none of it, Missing turns on in the same update and the sheet says so.
  await expect(page).toHaveURL(/families=znr/);
  await expect(page.getByRole('toolbar', { name: 'Ownership' }).getByRole('button', { name: /Missing/ })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByText('Showing missing cards — you don’t own any from Zendikar Rising yet.')).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(4);

  // A click on + stages one copy.
  for (const n of ['Anticausal Vestige', 'Bygone Colossus', 'Cryogen Relic']) await plus(page, n).click();
  await expect(page.getByRole('button', { name: 'Add 3 copies' })).toBeVisible();
  await expect(page.getByText(/^To add · 3 printings · 3 copies · \+\$4\.50 at market/)).toBeVisible();

  // Holding + opens the amount picker: how many copies to add.
  const hold = plus(page, 'Dawnstrike Vanguard');
  await hold.hover();
  await page.mouse.down();
  await page.waitForTimeout(500);
  await page.mouse.up();
  const field = page.getByRole('textbox', { name: 'Copies to add' });
  await expect(field).toBeFocused();
  await field.fill('4');
  await page.getByRole('button', { name: 'Add 4', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Add 7 copies' })).toBeVisible();

  // Review narrows the sheet to what is staged.
  await page.getByRole('button', { name: 'Review' }).click();
  await expect(page.getByText(/Showing 4 pending/)).toBeVisible();
  await page.getByRole('button', { name: 'Show all' }).click();

  await page.getByRole('button', { name: 'Add 7 copies' }).click();
  await expect(page.getByText('Added 7 copies')).toBeVisible();
  expect(saves).toHaveLength(1);
  expect(saves[0].family).toBe('Zendikar Rising');
  const sent = Object.fromEntries(saves[0].changes.map((c) => [c.scryfall_id, c]));
  expect(Object.keys(sent)).toHaveLength(4);
  for (const n of ['Anticausal Vestige', 'Bygone Colossus', 'Cryogen Relic']) expect(sent[card(n).scryfall_id]).toMatchObject({ finish: 'nonfoil', qty: 1, expected: 0 });
  expect(sent[card('Dawnstrike Vanguard').scryfall_id]).toMatchObject({ finish: 'nonfoil', qty: 4, expected: 0 });
});

test('the families filter falls through to families you do not own', async ({ page }) => {
  await mockUnowned(page, []);
  await page.goto('/collection');
  await page.getByRole('button', { name: /Set families/ }).click();
  await page.getByRole('searchbox', { name: 'Filter families' }).fill('zendi');
  await expect(page.getByText('No family you own matches “zendi”.')).toBeVisible();
  await page.getByRole('button', { name: 'Search all families' }).click();
  await expect(page.getByRole('checkbox', { name: /^Zendikar Rising/ })).toBeVisible();
  // Families you don't own carry their year where owned ones carry a count.
  await expect(page.getByText('2020')).toBeVisible();
});

const sse = (events: [string, unknown][]) => events.map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
const readJob = (id: string) => ({ id, name: 'collection.read_family', title: 'collection.read_family', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });
const unread = { ...collectionZnr, cards: [], families: collectionZnr.families.map((f) => ({ ...f, printings: 0, missing_printings: 0, missing_usd: 0, catalog_read: false })) };

/** The collection answers `first` until the read job ends, then `after`; jobs records each POST body. */
async function mockRead(page: Page, events: [string, unknown][], first: unknown, after: unknown) {
  await mockApi(page);
  const jobs: unknown[] = [];
  let collectionCalls = 0;
  await page.route('**/api/collection?**', (r) => {
    const url = new URL(r.request().url());
    if (url.pathname !== '/api/collection' || !url.searchParams.getAll('families').includes('znr')) return r.fallback();
    collectionCalls += 1;
    return r.fulfill({ json: collectionCalls === 1 ? first : after });
  });
  await page.route('**/api/jobs/collection.read_family', (r) => { jobs.push(r.request().postDataJSON()); return r.fulfill({ status: 202, json: readJob(`rf${jobs.length}`) }); });
  await page.route('**/api/jobs/rf*/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse(events) }));
  return { jobs, calls: () => collectionCalls };
}

test('an unread family is read for you once, then the collection reloads with its cards', async ({ page }) => {
  const { jobs, calls } = await mockRead(page, [['status', { status: 'running' }], ['status', { status: 'succeeded' }]], unread, collectionZnr);
  await page.goto('/collection?families=znr&show=owned,missing');
  await expect(page.getByRole('article')).toHaveCount(4);
  expect(jobs).toHaveLength(1);
  expect(jobs[0]).toMatchObject({ family: 'znr' });
  expect(calls()).toBe(2);
  await expect(page.getByText('Reading Zendikar Rising')).toHaveCount(0);
  expect(jobs).toHaveLength(1);
});

test('a failed read says why and Try again starts it again', async ({ page }) => {
  const { jobs } = await mockRead(page, [['status', { status: 'running' }], ['error', { error: 'Scryfall is down' }], ['status', { status: 'failed' }]], unread, unread);
  await page.goto('/collection?families=znr&show=owned,missing');
  await expect(page.getByText('Couldn’t read Zendikar Rising: Scryfall is down')).toBeVisible();
  expect(jobs).toHaveLength(1);
  await page.getByRole('button', { name: 'Try again' }).click();
  await expect.poll(() => jobs.length).toBe(2);
  expect(jobs[1]).toMatchObject({ family: 'znr' });
});
