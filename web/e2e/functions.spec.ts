import { COLLECTION_URL, COMPARE_URL, expect, fixtures, mockApi, test } from './support';

const card = (name: string) => fixtures.compare.cards.find((c) => c.name === name)!;
const label = (key: string) => fixtures.compare.functions.find((f) => f.key === key)!.label;

test('Group by Function regroups each column under Tagger function roots (P4)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await expect(page).not.toHaveURL(/groupBy=/);
  const aOnly = page.locator('section[aria-labelledby="col-a_only"]');
  await expect(aOnly.getByRole('heading', { name: /^Creatures/, level: 3 })).toBeVisible();

  await page.getByRole('radio', { name: 'Function' }).click();
  await expect(page).toHaveURL(/groupBy=function/);
  await expect(aOnly.getByRole('heading', { name: /^Ramp/, level: 3 })).toBeVisible();
  await expect(aOnly.getByRole('heading', { name: /^Creatures/, level: 3 })).toHaveCount(0);

  // A card serving several functions is listed under each, noting the others.
  const charm = card("Archdruid's Charm");
  const others = charm.functions.slice(1).map(label).join(', ');
  const tile = aOnly.getByRole('article').filter({ hasText: charm.name }).first();
  await expect(tile).toContainText(`also: ${others}`);

  await expect(page.getByText('A card with several roles is listed under each')).toBeVisible();

  // List view keeps the also-note inline.
  await page.getByRole('radio', { name: 'List' }).click();
  await expect(aOnly.getByText(`also: ${others}`).first()).toBeVisible();

  await page.reload();
  await expect(page.getByRole('radio', { name: 'Function' })).toHaveAttribute('aria-checked', 'true');
});

test('card inspector lists its functions and Scryfall tags', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const signet = card('Arcane Signet');
  await page.locator('section[aria-labelledby="col-both"]').getByRole('button', { name: `Inspect ${signet.name}` }).first().click();
  const tags = page.getByRole('dialog', { name: signet.name }).getByRole('list', { name: 'Scryfall tags' });
  await expect(tags).toBeVisible();
  for (const t of signet.oracle_tags) await expect(tags).toContainText(t.label);
  await expect(page.getByText(signet.functions.map(label).join(' · '), { exact: true })).toBeVisible();
});

test('without synced tags, Function grouping explains how to sync', async ({ page }) => {
  const untagged = { ...fixtures.compare, cards: fixtures.compare.cards.map((c) => ({ ...c, functions: [], oracle_tags: [] })) };
  await mockApi(page, { '/api/edhrec/compare': () => ({ json: untagged }) });
  await page.goto(`${COMPARE_URL}&groupBy=function`);
  await expect(page.getByRole('note')).toContainText('No Scryfall function tags yet');
  await expect(page.getByRole('link', { name: 'Sync Scryfall tags' })).toHaveAttribute('href', '/jobs');
  await expect(page.locator('section[aria-labelledby="col-a_only"]').getByRole('heading', { name: /^No tagged function/, level: 3 })).toBeVisible();
});

test('Jobs can sync the Scryfall tag cache', async ({ page }) => {
  const sse = [
    ['status', { status: 'running' }],
    ['progress', { done: 1, total: null, message: 'Parsing oracle-tags…', level: 'info' }],
    ['result', { summary: '4561 tags · 235054 taggings · synced', artifacts: [] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  let body: unknown = null;
  await page.route('**/api/jobs/scryfall.sync_tags', (r) => {
    body = r.request().postDataJSON();
    return r.fulfill({ status: 202, json: { id: 'tags1', name: 'scryfall.sync_tags', title: 'Sync Scryfall tags', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/tags1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.goto('/jobs');
  await page.getByRole('button', { name: 'Sync tags' }).click();
  await expect(page.getByText('4561 tags · 235054 taggings · synced')).toBeVisible();
  expect(body).toEqual({ refresh: false });
});

test('Collection filters by Tagger function; untagged cards are their own option', async ({ page }) => {
  const cards = fixtures.collectionBlb.cards;
  const draw = cards.filter((c) => c.functions.includes('draw')).length;
  const none = cards.filter((c) => !c.functions.length).length;
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('article')).toHaveCount(cards.length);
  await page.getByRole('button', { name: /Function/ }).click();
  await page.getByRole('checkbox', { name: /Card draw/ }).check();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/fn=/);
  await expect(page.getByRole('article')).toHaveCount(draw);
  await page.getByRole('button', { name: /Function/ }).click();
  await page.getByRole('checkbox', { name: /Card draw/ }).uncheck();
  await page.getByRole('checkbox', { name: /No tagged function/ }).check();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('article')).toHaveCount(none);
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page.getByRole('article')).toHaveCount(cards.length);
});
