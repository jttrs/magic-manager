import { expect, test } from './support';

const card = (id: string, name: string, o: Record<string, unknown> = {}) => ({
  scryfall_id: id, oracle_id: `o-${id}`, name, type_line: 'Creature — Dragon', oracle_text: 'Flying', flavor_text: `The flavor of ${name}.`, artist: 'Jane Doe',
  set_code: 'dtk', set_name: 'Dragons of Tarkir', collector_number: '161', rarity: 'rare', released_at: '2015-03-27',
  image: 'https://cards.scryfall.io/large/front/x.jpg', faces: [], scryfall_uri: 'https://scryfall.com/card/dtk/161', color_identity: ['R'],
  prices: { nonfoil: 0.14, foil: 0.38 }, owned: 0, owned_any: 0, art_tags: [{ slug: 'moon', label: 'moon' }], ...o,
});

test('surf random cards: an endless feed with filters, art tags that narrow it, and the URL as state', async ({ page }) => {
  const bodies: { filters: { art: string[]; flavor: string }; with_total: boolean }[] = [];
  let n = 0;
  await page.route('**/api/surf/options', (r) => r.fulfill({ json: {
    families: [{ value: 'dtk', label: 'Dragons of Tarkir', year: '2015' }],
    treatments: [{ value: 'borderless', label: 'Borderless' }], types: [{ value: 'creature', label: 'Creature' }], rarities: [{ value: 'rare', label: 'Rare' }],
  } }));
  await page.route('**/api/surf/draw', (r) => {
    const body = r.request().postDataJSON();
    bodies.push(body);
    const cards = [0, 1, 2].map(() => { n += 1; return card(`c${n}`, `Dragon ${n}`, n === 1 ? { owned: 2, owned_any: 3 } : {}); });
    return r.fulfill({ json: { source: 'scryfall', query: 'game:paper', cards, total: body.with_total ? 120 : null, next_offset: null, exhausted: false } });
  });

  await page.goto('/explore');
  await page.getByRole('button', { name: 'Surf random cards' }).click();
  const dialog = page.getByRole('dialog', { name: 'Card surfer' });
  await expect(dialog).toBeVisible();
  await expect(page).toHaveURL(/surf=on/);
  const feed = dialog.getByRole('feed', { name: 'Random cards' });
  const first = feed.getByRole('article', { name: 'Dragon 1' });
  await expect(first).toContainText('The flavor of Dragon 1.');
  await expect(first).toContainText('Jane Doe');
  await expect(first).toContainText('Dragons of Tarkir · DTK #161 · Rare · 2015');
  await expect(first).toContainText('You own 2 of this printing · 3 in every printing');
  await expect(dialog.getByText('120 match')).toBeVisible();
  expect(bodies[0]).toMatchObject({ with_total: true, filters: { art: [], flavor: 'any' } });

  // Endless: scrolling to the end draws more.
  await feed.getByRole('article').last().scrollIntoViewIfNeeded();
  await expect(feed.getByRole('article', { name: 'Dragon 6' })).toBeAttached();

  // An art tag under a card narrows the feed and is shown in the rail.
  await first.getByRole('button', { name: 'moon' }).click();
  await expect(page).toHaveURL(/surf=art%3Dmoon/);
  await expect(dialog.getByRole('button', { name: 'Remove art tag moon' })).toBeVisible();
  await expect.poll(() => bodies.at(-1)?.filters.art).toEqual(['moon']);

  await dialog.getByRole('radio', { name: 'Has it' }).click();
  await expect.poll(() => bodies.at(-1)?.filters.flavor).toBe('has');
  await expect(dialog.getByRole('button', { name: 'Reset filters · 2' })).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(dialog).toHaveCount(0);
  await expect(page).not.toHaveURL(/surf=/);
});

test('surf: nothing matches offers a reset', async ({ page }) => {
  await page.route('**/api/surf/options', (r) => r.fulfill({ json: { families: [], treatments: [], types: [], rarities: [] } }));
  await page.route('**/api/surf/draw', (r) => r.fulfill({ json: { source: 'scryfall', query: 'q', cards: [], total: 0, next_offset: null, exhausted: true } }));
  await page.goto('/explore?surf=' + encodeURIComponent('ar=Nobody'));
  const dialog = page.getByRole('dialog', { name: 'Card surfer' });
  await expect(dialog.getByRole('heading', { name: 'No cards match' })).toBeVisible();
  await dialog.getByRole('button', { name: 'Reset filters', exact: true }).click();
  await expect(page).toHaveURL(/surf=on/);
});
