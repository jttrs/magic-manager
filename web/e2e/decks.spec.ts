import { expect, fixtures, test } from './support';

const detail = fixtures.deckDetail;
const DECK_URL = `/decks?deck=${encodeURIComponent(detail.deck.slug)}`;

test('deck list shows Commander decks by default, filters built and text; the nav has Decks', async ({ page }) => {
  await page.goto('/decks');
  await expect(page.getByRole('link', { name: 'Decks' })).toHaveAttribute('aria-current', 'page');
  const list = page.getByRole('navigation', { name: 'Decks' });
  const commander = fixtures.decks.filter((d) => d.deck_type === 'Commander');
  await expect(list.getByRole('button')).toHaveCount(commander.length);
  await page.getByRole('radio', { name: /^Built/ }).click();
  await expect(list.getByRole('button')).toHaveCount(commander.filter((d) => d.built > 0).length);
  await page.getByRole('searchbox', { name: 'Deck, set or author' }).fill('avengers');
  await expect(list.getByRole('button')).toHaveCount(1);
  await page.getByRole('searchbox', { name: 'Deck, set or author' }).fill('');
  await page.getByRole('button', { name: /^Group decks by/ }).click();
  await page.getByRole('menuitemradio', { name: 'Deck type' }).click();
  await expect(page).toHaveURL(/group=type/);
  await expect(list.getByRole('heading', { name: /^Commander/ })).toBeVisible();
  await page.getByRole('button', { name: /^Deck type/ }).click();
  await page.getByRole('checkbox', { name: /^Commander/ }).uncheck();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/types=/);
  await expect(list.getByRole('button')).toHaveCount(fixtures.decks.filter((d) => d.built > 0).length);
});

test('inspector: sections by board then type, card facts, deep link', async ({ page }) => {
  await page.goto(DECK_URL);
  await expect(page.getByRole('heading', { level: 2, name: detail.deck.name })).toBeVisible();
  await expect(page.getByRole('heading', { level: 3 }).first()).toContainText('Commander');
  const commander = detail.cards.find((c) => c.board === 'commander')!;
  const tile = page.getByRole('article').filter({ hasText: commander.printing.name }).first();
  await expect(tile).toContainText('in deck');
  await tile.getByRole('button', { name: `Inspect ${commander.printing.name}` }).click();
  await expect(page.getByRole('dialog', { name: commander.printing.name })).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('radio', { name: 'List' }).click();
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(page.getByRole('button', { name: /^Mark / }).first()).toBeVisible();
});

test('add the whole deck, or only marked cards, through the add-cards review', async ({ page }) => {
  const bodies: { items: { scryfall_id: string; qty: number }[]; label: string | null }[] = [];
  await page.route('**/api/ingest/commit', (r) => {
    const b = r.request().postDataJSON();
    bodies.push(b);
    const copies = b.items.reduce((s: number, i: { qty: number }) => s + i.qty, 0);
    return r.fulfill({ json: { ingest_id: 1, copies, printings: b.items.length, summary: `+${copies} copies · ${b.items.length} printings` } });
  });
  await page.goto(DECK_URL);
  await page.getByRole('button', { name: 'Add deck cards to collection' }).click();
  const dialog = page.getByRole('dialog', { name: 'Add cards' });
  await expect(dialog.getByRole('heading', { name: detail.deck.name })).toBeVisible();
  const total = detail.cards.filter((c) => c.board !== 'token').reduce((s, c) => s + c.count, 0);
  await dialog.getByRole('button', { name: `Add ${total} copies` }).click();
  await expect(dialog.getByRole('status')).toContainText(`Added ${total} copies`);
  expect(bodies[0].label).toBe(detail.deck.name);
  await page.keyboard.press('Escape');

  const names: string[] = [];
  for (const i of [0, 1]) {
    const mark = page.getByRole('article').nth(i).getByRole('button', { name: /^Mark / });
    names.push((await mark.getAttribute('aria-label'))!.replace(/^Mark /, ''));
    await mark.click();
  }
  await page.getByRole('button', { name: 'Add 2 marked cards to collection' }).click();
  const two = names.map((nm) => detail.cards.find((c) => c.printing.name === nm)!);
  const n = two.reduce((s, c) => s + c.count, 0);
  await page.getByRole('dialog', { name: 'Add cards' }).getByRole('button', { name: new RegExp(`^Add ${n} cop`) }).click();
  expect(bodies[1].items.map((i) => i.scryfall_id).sort()).toEqual(two.map((c) => c.printing.scryfall_id).sort());
});

test('unknown deck in the URL shows the error with a retry', async ({ page }) => {
  await page.goto('/decks?deck=nope');
  await expect(page.getByText(/not found/)).toBeVisible();
});

test('deck list is one tab stop with arrow-key navigation', async ({ page }) => {
  await page.goto('/decks');
  const rows = page.getByRole('navigation', { name: 'Decks' }).getByRole('button');
  await expect(rows.first()).toHaveAttribute('tabindex', '0');
  await expect(rows.nth(1)).toHaveAttribute('tabindex', '-1');
  await rows.first().focus();
  await page.keyboard.press('ArrowDown');
  await expect(rows.nth(1)).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page).toHaveURL(/deck=/);
});

test('one row per recipe with a built-copy counter (no loose tracking)', async ({ page }) => {
  await page.goto('/decks?types=%5B%5D');
  const d = fixtures.decks.find((x) => x.built > 0)!;
  const row = page.getByRole('navigation', { name: 'Decks' }).getByRole('button', { name: new RegExp(d.name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')) }).first();
  await expect(row.getByLabel(`${d.built} built`)).toBeVisible();
  await expect(page.getByText(/loose/i)).toHaveCount(0);
});

const editable = { ...detail, version_id: 7, editable: true, deck: { ...detail.deck, built: 1, slugs: [detail.deck.slug], pledged_pct: 100 } };

test('deck actions are icons with tooltips; precons offer Copy to edit; building confirms first', async ({ page }) => {
  let built: unknown = null;
  await page.route('**/api/decks/*/build-plan', (r) => r.fulfill({ json: { target: detail.deck.slug, need: 3, covered: 2, short: [{ printing: detail.cards[0].printing, finish: 'nonfoil', qty: 1 }] } }));
  await page.route('**/api/decks/*/build', (r) => { built = r.request().postDataJSON(); return r.fulfill({ json: { slug: detail.deck.slug, summary: 'Built — 2 cards pledged, 1 still missing' } }); });
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: { ...detail, version_id: 1, editable: false, deck: { ...detail.deck, built: 0, slugs: [detail.deck.slug], pledged_pct: 0 } } }));
  await page.goto(DECK_URL);
  const bar = page.getByRole('toolbar', { name: 'Deck actions' });
  await expect(bar.getByRole('button', { name: 'Copy to edit' })).toBeVisible();
  await expect(bar.getByRole('button', { name: 'Break down' })).toHaveAttribute('aria-disabled', 'true');
  await bar.getByRole('button', { name: 'Add deck cards to collection' }).hover();
  await expect(page.getByRole('tooltip')).toHaveText('Add deck cards to collection');
  await bar.getByRole('button', { name: 'Build from your cards' }).click();
  const dialog = page.getByRole('alertdialog', { name: /Build/ });
  await expect(dialog).toContainText('2 of the 3 cards free');
  await expect(dialog.getByRole('list', { name: 'Missing cards' })).toContainText(detail.cards[0].printing.name);
  await dialog.getByRole('button', { name: 'Build with 1 missing' }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Built —' })).toBeVisible();
  expect(built).toEqual({ allow_shortfall: true });
});

test('editor: add a card from search, see the diff, save a new version (built decks review the swap)', async ({ page }) => {
  let saved: { cards: { scryfall_id: string; count: number }[]; expected_version_id: number } | null = null;
  const extra = { ...detail.cards[0].printing, scryfall_id: 'new-card', oracle_id: 'o-new', name: 'Sol Ring', type_line: 'Artifact', owned: { nonfoil: 2 }, free: 2 };
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => {
    if (r.request().method() === 'PUT') {
      saved = r.request().postDataJSON();
      return r.fulfill({ json: { built: true, changes: [], swap: null, version_number: 8, pulled: 0, sleeved: 1 } });
    }
    return r.fulfill({ json: editable });
  });
  await page.route('**/api/ingest/search**', (r) => r.fulfill({ json: { query: 'sol', source: 'local', printings: [{ ...extra, scryfall_id: 'unowned', name: 'Sol Talisman', owned: {}, free: 0 }, extra] } }));
  await page.route('**/api/decks/*/preview', (r) => r.fulfill({ json: { built: true, changes: [], swap: { pull: [], sleeve: [{ printing: extra, finish: 'nonfoil', qty: 1 }], short: [] } } }));
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);
  await expect(page.getByRole('button', { name: 'Save deck' })).toBeDisabled();
  await page.getByRole('tab', { name: 'Search' }).click();
  await page.getByRole('searchbox').fill('sol');
  const results = page.getByRole('button', { name: /^Add Sol/ });
  await expect(results.first()).toHaveAccessibleName('Add Sol Ring');      // free copies rank first
  await results.first().click();
  await expect(page.getByText('New', { exact: true })).toBeVisible();
  await expect(page.getByText('+1')).toBeVisible();
  await page.getByRole('button', { name: 'Save deck' }).click();
  const review = page.getByRole('alertdialog', { name: 'Update your built deck' });
  await expect(review).toContainText('Put in · 1');
  await review.getByRole('button', { name: 'Save and update' }).click();
  await expect(page).toHaveURL(/\/decks\?deck=/);
  expect(saved!.expected_version_id).toBe(7);
  expect(saved!.cards.find((c) => c.scryfall_id === 'new-card')?.count).toBe(1);
});
