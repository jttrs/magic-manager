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
  await page.getByRole('navigation', { name: 'Explore views' }).getByRole('link', { name: 'Surfer' }).click();
  await expect(page).toHaveURL(/mode=surf/);
  const view = page;
  const feed = view.getByRole('feed', { name: 'Random cards' });
  const first = feed.getByRole('article', { name: 'Dragon 1' });
  await expect(first).toContainText('The flavor of Dragon 1.');
  await expect(first).toContainText('Jane Doe');
  await expect(first).toContainText('Dragons of Tarkir · DTK #161 · Rare · 2015');
  await expect(first).toContainText('You own 2 of this printing · 3 in every printing');
  await expect(view.getByText('120 match')).toBeVisible();
  expect(bodies[0]).toMatchObject({ with_total: true, filters: { art: [], flavor: 'any' } });

  // Endless: scrolling to the end draws more.
  await feed.getByRole('article').last().scrollIntoViewIfNeeded();
  await expect(feed.getByRole('article', { name: 'Dragon 6' })).toBeAttached();

  // An art tag under a card narrows the feed and is shown in the rail.
  await first.getByRole('button', { name: 'moon' }).click();
  await expect(page).toHaveURL(/surf=art%3Dmoon/);
  await expect(view.getByRole('button', { name: 'Remove art tag moon' })).toBeVisible();
  await expect.poll(() => bodies.at(-1)?.filters.art).toEqual(['moon']);

  await view.getByRole('radio', { name: 'Has it' }).click();
  await expect.poll(() => bodies.at(-1)?.filters.flavor).toBe('has');
  await expect(view.getByRole('button', { name: 'Reset filters · 2' })).toBeVisible();

  await page.getByRole('link', { name: 'Rankings' }).click();
  await expect(page.getByRole('feed', { name: 'Random cards' })).toHaveCount(0);
  await page.getByRole('link', { name: 'Surfer' }).click();
  await expect(page).toHaveURL(/surf=art%3Dmoon/);
});

test('surf: nothing matches offers a reset', async ({ page }) => {
  await page.route('**/api/surf/options', (r) => r.fulfill({ json: { families: [], treatments: [], types: [], rarities: [] } }));
  await page.route('**/api/surf/draw', (r) => r.fulfill({ json: { source: 'scryfall', query: 'q', cards: [], total: 0, next_offset: null, exhausted: true } }));
  await page.goto('/explore?surf=' + encodeURIComponent('ar=Nobody'));
  const view = page;
  await expect(view.getByRole('heading', { name: 'No cards match' })).toBeVisible();
  await view.getByRole('button', { name: 'Reset filters', exact: true }).click();
  await expect(page).not.toHaveURL(/surf=/);
});

test('surf: your cards keeps searching through empty pages before giving up', async ({ page }) => {
  const offsets: number[] = [];
  await page.route('**/api/surf/options', (r) => r.fulfill({ json: { families: [], treatments: [], types: [], rarities: [] } }));
  await page.route('**/api/surf/draw', (r) => {
    const { offset } = r.request().postDataJSON();
    offsets.push(offset);
    const last = offset >= 240;
    return r.fulfill({ json: { source: 'owned', query: 'q', cards: last ? [card('o1', 'Owned Dragon', { owned: 1, owned_any: 1 })] : [], total: 300, next_offset: offset + 120, exhausted: false } });
  });
  await page.goto('/explore?surf=' + encodeURIComponent('src=owned'));
  const view = page;
  await expect(view.getByRole('article', { name: 'Owned Dragon' })).toBeAttached();
  expect(offsets.slice(0, 3)).toEqual([0, 120, 240]);
});

/** A finished feed of `n` cards (no more pages). */
async function feedOf(page: import('@playwright/test').Page, n: number) {
  await page.route('**/api/surf/options', (r) => r.fulfill({ json: { families: [], treatments: [], types: [{ value: 'creature', label: 'Creature' }], rarities: [] } }));
  await page.route('**/api/surf/draw', (r) => r.fulfill({ json: {
    source: 'scryfall', query: 'q', cards: Array.from({ length: n }, (_, i) => card(`k${i + 1}`, `Dragon ${i + 1}`)), total: n, next_offset: null, exhausted: true,
  } }));
}

test('surf: j and k step through the feed, which has focus when the tab opens', async ({ page }) => {
  await feedOf(page, 3);
  await page.goto('/explore?mode=surf');
  const feed = page.getByRole('feed', { name: 'Random cards' });
  const second = feed.getByRole('article', { name: 'Dragon 2' });
  await expect(feed.getByRole('article', { name: 'Dragon 1' })).toBeInViewport();
  await expect(feed).toBeFocused();
  await expect(second).not.toBeInViewport();

  await page.keyboard.press('j');
  await expect(second).toBeInViewport({ ratio: 0.9 });
  // Only the feed scrolls: the Explore tabs stay on screen.
  await expect(page.getByRole('navigation', { name: 'Explore views' })).toBeInViewport();
  await page.keyboard.press('j');
  await expect(feed.getByRole('article', { name: 'Dragon 3' })).toBeInViewport({ ratio: 0.9 });
  await page.keyboard.press('k');
  await expect(second).toBeInViewport({ ratio: 0.9 });
});

test('surf: Explore this card leaves the surfer for the card, in the Cards tab', async ({ page }) => {
  await feedOf(page, 1);
  await page.goto('/explore?surf=' + encodeURIComponent('art=moon'));
  await page.getByRole('article', { name: 'Dragon 1' }).getByRole('link', { name: 'Explore this card' }).click();
  await expect(page).toHaveURL(/mode=card/);
  await expect(page).toHaveURL(/a=Dragon(\+|%20)1/);
  await expect(page).not.toHaveURL(/surf=/);
  await expect(page.getByRole('navigation', { name: 'Explore views' }).getByRole('link', { name: 'Cards', exact: true })).toHaveAttribute('aria-current', 'page');
  await expect(page.getByRole('feed', { name: 'Random cards' })).toHaveCount(0);
});

test('surf on a phone: filters fold behind the rail disclosure, the feed stays first', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await feedOf(page, 1);
  await page.goto('/explore?mode=surf');
  await expect(page.getByRole('article', { name: 'Dragon 1' })).toBeVisible();
  const toggle = page.getByRole('button', { name: /Card surfer filters/ });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('radio', { name: 'Has it' })).toBeHidden();

  await toggle.click();
  await expect(toggle).toHaveAttribute('aria-expanded', 'true');
  await page.getByRole('radio', { name: 'Has it' }).click();
  await expect(page).toHaveURL(/surf=fl%3Dhas/);

  // Collapsed again, the rail summarises the active filters.
  await toggle.click();
  await expect(toggle).toContainText('1 filter');
});
