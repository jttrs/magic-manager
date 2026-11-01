import { expect, fixtures, rankingPage, test } from './support';
import partners from './fixtures/ranking-top-partners.json' with { type: 'json' };

const ranking = fixtures.ranking;

test('Explore opens on rankings, as a grid; Rankings is the first tab', async ({ page }) => {
  await page.goto('/explore');
  const tabs = page.getByRole('navigation', { name: 'Explore views' }).getByRole('link');
  await expect(tabs).toHaveText(['Rankings', 'Cards', 'Earmarked', 'Surfer']);
  await expect(tabs.first()).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('radio', { name: 'Grid' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('table')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Inspect Krenko, Mob Boss' })).toBeVisible();
  await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText('Find');
});

test('the rankings list joins what you own, with type, color and cost columns; names open the profile in the right role', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto('/explore?rview=list');
  await expect(page.getByRole('heading', { level: 1, name: ranking.title })).toBeAttached();
  const ledger = page.getByRole('table', { name: new RegExp(ranking.title) });
  await expect(ledger.getByRole('row')).toHaveCount(ranking.rows.length + 1);
  const krenko = ledger.getByRole('row', { name: /Krenko, Mob Boss/ });
  await expect(krenko).toContainText('2 · 1 unused');
  await expect(krenko.getByRole('cell', { name: 'Creature', exact: true })).toBeVisible();
  await expect(krenko.getByRole('cell', { name: 'Goblin Warrior' })).toBeVisible();
  await expect(krenko.getByRole('img', { name: 'Color identity: red' })).toBeVisible();
  await expect(krenko.getByRole('img', { name: 'Mana cost: 2, red, red' })).toBeVisible();
  await expect(page.getByText(/ranked · you own \d+ · \d+ unused · read /)).toBeVisible();
  const actions = page.getByRole('toolbar', { name: 'Ranking actions' });
  await expect(actions.getByRole('button', { name: 'Refresh' })).toBeVisible();
  await expect(actions.getByRole('link', { name: /Open results in EDHREC/ })).toHaveAttribute('href', 'https://edhrec.com/commanders/mono-red/week');

  await page.getByRole('radio', { name: 'Unused' }).click();
  await expect(page).toHaveURL(/own=unused/);
  const unused = ranking.rows.filter((r) => (r.facts.free ?? 0) > 0).length;
  await expect(ledger.getByRole('row')).toHaveCount(unused + 1);

  await krenko.getByRole('link', { name: 'Krenko, Mob Boss' }).click();
  await expect(page).toHaveURL(/mode=card/);
  await expect(page).toHaveURL(/a=Krenko/);
  await expect(page).toHaveURL(/role=commander/);
  await expect(page.getByRole('link', { name: 'Cards', exact: true })).toHaveAttribute('aria-current', 'page');
});

test('partner commanders show both cards: one in front, the partner peeking from behind', async ({ page }) => {
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: partners }));
  await page.goto('/explore');
  const pair = page.getByRole('img', { name: /Frodo, Adventurous Hobbit \/\/ Sam, Loyal Attendant: two partner commanders/ });
  await expect(pair).toBeVisible();
  await expect(pair.locator('img')).toHaveCount(2);
  await page.getByRole('radio', { name: 'List' }).click();
  const row = page.getByRole('row', { name: /Frodo/ });
  await expect(row).toContainText('$0.78');
  await row.getByRole('button', { name: /Inspect Frodo/ }).click();
  const dialog = page.getByRole('dialog');
  await expect(dialog.getByRole('img')).toHaveCount(2);
  await expect(dialog.getByRole('region', { name: 'Frodo, Adventurous Hobbit' })).toBeVisible();
  await expect(dialog.getByRole('region', { name: 'Sam, Loyal Attendant' })).toBeVisible();
  await expect(dialog).toContainText('both cards');
});

test('a ranking never read is fetched as a job with progress, then shown', async ({ page }) => {
  let cached = false;
  let submitted: unknown = null;
  const salt = {
    scope: 'salt', timeframe: 'all', filter: '', title: 'Saltiest cards', fetched_at: '2026-10-06T10:00:00+00:00',
    total: 1, base: 1, pool: 1, owned: 0, unused: 0, offset: 0, local_filters: [],
    rows: [{ rank: 1, name: 'Stasis', slug: 'stasis', num_decks: 18038, salt: 3.0572, trend: null, facts: { ...ranking.rows[1].facts, owned: 0, free: 0 } }],
  };
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: cached ? { ...salt, cached: true } : { ...salt, cached: false, fetched_at: null, rows: [] } }));
  const sse = [
    ['status', { status: 'running' }],
    ['progress', { done: 1, total: 1, message: 'Matching 100 cards to your collection', level: 'info' }],
    ['result', { summary: 'Saltiest cards: 100 entries', artifacts: [] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/jobs/edhrec.rankings', (r) => {
    submitted = r.request().postDataJSON();
    return r.fulfill({ status: 202, json: { id: 'rk1', name: 'edhrec.rankings', title: 'Fetch a ranking', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/rk1/events', async (r) => {
    cached = true;
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse });
  });

  await page.goto('/explore?rank=salt&rview=list');
  await expect(page.getByRole('row', { name: /Stasis/ })).toContainText('3.06');
  expect(submitted).toEqual({ scope: 'salt', timeframe: 'week', refresh: false });
  // salt is all-time: the timeframe stays in place, disabled, and says why
  await expect(page.getByRole('radio', { name: 'Week' })).toBeDisabled();
  await expect(page.getByText('Salt is rated over all time.')).toBeVisible();
});

test('color, tag and set are laid out together, each Any, and combine', async ({ page }) => {
  const asked: URLSearchParams[] = [];
  await page.route('**/api/explore/ranking?*', (r) => {
    const url = new URL(r.request().url());
    asked.push(url.searchParams);
    return r.fulfill({ json: rankingPage(ranking, url) });
  });
  await page.goto('/explore');
  await expect(page.getByRole('button', { name: /Narrow by/ })).toHaveCount(0);
  const color = page.getByRole('button', { name: /^Color identity/ });
  const fam = page.getByRole('button', { name: /^Set family/ });
  await expect(color).toHaveText(/Any/);
  await expect(fam).toHaveText(/Any/);
  await expect(page.getByRole('combobox', { name: 'Tag or creature type' })).toHaveAttribute('placeholder', /^Any/);

  await color.click();
  await page.getByRole('option', { name: /Azorius/ }).click();
  await expect(page).toHaveURL(/color=azorius/);
  const tag = page.getByRole('combobox', { name: 'Tag or creature type' });
  await tag.fill('goblins');
  await tag.press('Enter');
  await expect(page).toHaveURL(/tag=goblins/);
  await expect(page).toHaveURL(/color=azorius/);
  await expect(page.getByRole('radio', { name: 'Week' })).toBeEnabled();
  await expect.poll(() => asked.some((q) => q.get('color') === 'azorius' && q.get('tag') === 'goblins')).toBe(true);

  await fam.click();
  await page.getByRole('option').nth(1).click();
  await expect(page).toHaveURL(/fam=/);
  await expect(page.getByRole('radio', { name: 'Week' })).toBeDisabled();
  await expect(page.getByText('Set and tag lists cover all time.')).toBeVisible();

  await color.click();
  await page.getByRole('option', { name: 'Any', exact: true }).click();
  await expect(page).not.toHaveURL(/color=/);

  // the filters narrow commanders: on top cards they stay in place, disabled, and say so
  await page.getByRole('button', { name: /^List/ }).click();
  await page.getByRole('menuitemradio', { name: 'Top cards' }).click();
  await expect(color).toBeDisabled();
  await expect(page.getByText('Color, tag and set narrow top commanders.')).toBeVisible();
});

test('the first 100 show; Load more adds 50 at a time', async ({ page }) => {
  const template = ranking.rows[1];
  const big = { ...ranking, rows: Array.from({ length: 160 }, (_, i) => ({ ...template, rank: i + 1, name: `Commander ${i + 1}`, slug: `commander-${i + 1}`, facts: { ...template.facts, oracle_id: `o-${i + 1}` } })) };
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: { ...rankingPage(big, new URL(r.request().url())), base: 160, pool: 160 } }));
  await page.goto('/explore?rview=list');
  const ledger = page.getByRole('table');
  await expect(ledger.getByRole('row')).toHaveCount(101);
  await expect(page.getByText('Showing 100 of 160')).toBeVisible();
  await page.getByRole('button', { name: 'Load 50 more' }).click();
  await expect(ledger.getByRole('row')).toHaveCount(151);
  await page.getByRole('button', { name: 'Load 10 more' }).click();
  await expect(ledger.getByRole('row')).toHaveCount(161);
  await expect(page.getByRole('button', { name: /^Load \d+ more/ })).toHaveCount(0);
});

test('a set EDHREC lists nothing for is a calm empty state; a failed read never names an exception', async ({ page }) => {
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: { ...ranking, filter: 'set:acr', timeframe: '', rows: [], total: 0, base: 0, pool: 0, owned: 0, unused: 0, local_filters: ['color'] } }));
  await page.goto('/explore?fam=acr&color=mono-red');
  await expect(page.getByText(/EDHREC lists no commanders from .+ yet\./)).toBeVisible();
  await expect(page.getByRole('alert')).toHaveCount(0);

  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: { ...ranking, cached: false, fetched_at: null, rows: [], total: 0, pool: 0 } }));
  await page.route('**/api/jobs/edhrec.rankings', (r) => r.fulfill({ status: 202, json: { id: 'rk2', name: 'edhrec.rankings', title: 'x', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } }));
  const sse = [['status', { status: 'running' }], ['error', { error: 'EdhrecError: EDHREC has no “gobblinz” tag.', code: 'edhrec_error', trace: null }], ['status', { status: 'failed' }]]
    .map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/jobs/rk2/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.goto('/explore?tag=gobblinz');
  await expect(page.getByText(/EDHREC has no “gobblinz” tag\./)).toBeVisible();
  await expect(page.getByText(/EdhrecError/)).toHaveCount(0);
});

test('the mode tabs move between specific cards and rankings, keeping both', async ({ page }) => {
  await page.goto('/explore?a=Tifa%20Lockhart&role=card');
  await expect(page.getByRole('link', { name: 'Cards', exact: true })).toHaveAttribute('aria-current', 'page');
  await page.getByRole('link', { name: 'Rankings' }).click();
  await expect(page.getByRole('heading', { level: 1, name: ranking.title })).toBeAttached();
  await page.getByRole('link', { name: 'Cards', exact: true }).click();
  await expect(page).toHaveURL(/a=Tifa/);
  await expect(page.getByRole('region', { name: /Tifa Lockhart on EDHREC/ }).or(page.getByText('Nothing matches'))).toBeVisible();
});

test('the set family picker offers families you own nothing from, owned ones first and marked', async ({ page }) => {
  await page.goto('/explore');
  await page.getByRole('button', { name: /^Set family/ }).click();
  const options = page.getByRole('option');
  await expect(options.nth(1)).toContainText('Avatar: The Last Airbender');
  await expect(options.nth(1)).toContainText('owned');
  await page.getByRole('combobox', { name: 'Filter families' }).fill('edge');
  await expect(options).toHaveCount(1);
  await expect(options.first()).not.toContainText('owned');
  await options.first().click();
  await expect(page).toHaveURL(/fam=eoe/);
});

test('a ranking EDHREC cut short says so calmly, with the way out', async ({ page }) => {
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: { ...rankingPage(ranking, new URL(r.request().url())), pool_complete: false, pool_partial_reason: 'rate_limited', base: 200 } }));
  await page.goto('/explore');
  await expect(page.getByRole('status').filter({ hasText: 'Showing the first 200 — EDHREC limited the read. Refresh to fetch the rest.' })).toBeVisible();
  await expect(page.getByText(/429|EdhrecError/)).toHaveCount(0);
});
