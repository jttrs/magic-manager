import { expect, fixtures, test } from './support';
import partners from './fixtures/ranking-top-partners.json' with { type: 'json' };

const ranking = fixtures.ranking;

test('Explore opens on rankings, as a grid; Rankings is the first tab', async ({ page }) => {
  await page.goto('/explore');
  const tabs = page.getByRole('navigation', { name: 'Explore views' }).getByRole('link');
  await expect(tabs).toHaveText(['Rankings', 'Specific cards']);
  await expect(tabs.first()).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('radio', { name: 'Grid' })).toHaveAttribute('aria-checked', 'true');
  await expect(page.getByRole('table')).toHaveCount(0);
  await expect(page.getByRole('button', { name: 'Inspect Krenko, Mob Boss' })).toBeVisible();
  // the rail: find first, the card surfer last
  const rail = page.getByRole('heading', { level: 2 });
  await expect(rail.first()).toHaveText('Find');
  await expect(rail.last()).toHaveText('Random cards');
});

test('the rankings list joins what you own, with type, colour and cost columns; names open the profile in the right role', async ({ page }) => {
  await page.setViewportSize({ width: 1600, height: 900 });
  await page.goto('/explore?rview=list');
  await expect(page.getByRole('heading', { level: 1, name: ranking.title })).toBeVisible();
  const ledger = page.getByRole('table', { name: new RegExp(ranking.title) });
  await expect(ledger.getByRole('row')).toHaveCount(ranking.rows.length + 1);
  const krenko = ledger.getByRole('row', { name: /Krenko, Mob Boss/ });
  await expect(krenko).toContainText('2 · 1 free');
  await expect(krenko.getByRole('cell', { name: 'Creature', exact: true })).toBeVisible();
  await expect(krenko.getByRole('cell', { name: 'Goblin Warrior' })).toBeVisible();
  await expect(krenko.getByRole('img', { name: 'Colour identity: red' })).toBeVisible();
  await expect(krenko.getByRole('img', { name: 'Mana cost: 2, red, red' })).toBeVisible();
  await expect(page.getByText(/read from EDHREC/)).toBeVisible();
  await expect(page.getByRole('link', { name: /Open on EDHREC/ })).toHaveAttribute('href', 'https://edhrec.com/commanders/mono-red/week');

  await page.getByRole('radio', { name: 'Free' }).click();
  await expect(page).toHaveURL(/own=free/);
  const free = ranking.rows.filter((r) => (r.facts.free ?? 0) > 0).length;
  await expect(ledger.getByRole('row')).toHaveCount(free + 1);

  await krenko.getByRole('link', { name: 'Krenko, Mob Boss' }).click();
  await expect(page).toHaveURL(/mode=card/);
  await expect(page).toHaveURL(/a=Krenko/);
  await expect(page).toHaveURL(/role=commander/);
  await expect(page.getByRole('link', { name: 'Specific cards' })).toHaveAttribute('aria-current', 'page');
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
    return r.fulfill({ status: 202, json: { id: 'rk1', name: 'edhrec.rankings', title: 'Fetch an EDHREC ranking', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } });
  });
  await page.route('**/api/jobs/rk1/events', async (r) => {
    cached = true;
    await r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse });
  });

  await page.goto('/explore?rank=salt&rview=list');
  await expect(page.getByRole('row', { name: /Stasis/ })).toContainText('3.06');
  expect(submitted).toEqual({ scope: 'salt', timeframe: 'week', refresh: false });
  await expect(page.getByRole('group', { name: 'Timeframe' })).toHaveCount(0);
});

test('narrowing commanders takes one axis and waits for its value', async ({ page }) => {
  await page.goto('/explore');
  await page.getByRole('button', { name: /Narrow by/ }).click();
  await page.getByRole('menuitemradio', { name: 'Colour identity' }).click();
  await expect(page.getByText('Pick a colour identity')).toBeVisible();
  await page.getByRole('button', { name: /^Colour identity/ }).click();
  await page.getByRole('option', { name: /Azorius/ }).click();
  await expect(page).toHaveURL(/by=color/);
  await expect(page).toHaveURL(/color=azorius/);

  await page.getByRole('button', { name: /Narrow by/ }).click();
  await page.getByRole('menuitemradio', { name: 'Tag or creature type' }).click();
  await expect(page.getByRole('group', { name: 'Timeframe' })).toHaveCount(0);
  const tag = page.getByRole('combobox', { name: 'Tag or creature type' });
  await tag.fill('goblins');
  await tag.press('Enter');
  await expect(page).toHaveURL(/tag=goblins/);
});

test('the mode tabs move between specific cards and rankings, keeping both', async ({ page }) => {
  await page.goto('/explore?a=Tifa%20Lockhart&role=card');
  await expect(page.getByRole('link', { name: 'Specific cards' })).toHaveAttribute('aria-current', 'page');
  await page.getByRole('link', { name: 'Rankings' }).click();
  await expect(page.getByRole('heading', { level: 1, name: ranking.title })).toBeVisible();
  await page.getByRole('link', { name: 'Specific cards' }).click();
  await expect(page).toHaveURL(/a=Tifa/);
  await expect(page.getByRole('region', { name: /Tifa Lockhart on EDHREC/ }).or(page.getByText('Nothing matches'))).toBeVisible();
});
