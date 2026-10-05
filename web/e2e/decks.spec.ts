import { expect, fixtures, test } from './support';

const detail = fixtures.deckDetail;
const DECK_URL = `/decks?deck=${encodeURIComponent(detail.deck.slug)}`;

test('deck list groups by set, filters by state and text; the nav has Decks', async ({ page }) => {
  await page.goto('/decks');
  await expect(page.getByRole('link', { name: 'Decks' })).toHaveAttribute('aria-current', 'page');
  const list = page.getByRole('navigation', { name: 'Decks' });
  await expect(list.getByRole('button')).toHaveCount(fixtures.decks.length);
  await page.getByRole('toolbar', { name: 'Decks' }).getByRole('button', { name: /^Loose/ }).click();
  await expect(list.getByRole('button')).toHaveCount(fixtures.decks.filter((d) => d.state === 'built').length);
  await page.getByRole('searchbox', { name: 'Deck, set or author' }).fill('avengers');
  await expect(list.getByRole('button')).toHaveCount(1);
  await page.getByRole('combobox', { name: 'Group decks by' }).selectOption('year');
  await expect(page).toHaveURL(/group=year/);
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
  await page.getByRole('button', { name: 'Add deck to collection' }).click();
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
  await page.getByRole('button', { name: 'Add 2 marked' }).click();
  const two = names.map((nm) => detail.cards.find((c) => c.printing.name === nm)!);
  const n = two.reduce((s, c) => s + c.count, 0);
  await page.getByRole('dialog', { name: 'Add cards' }).getByRole('button', { name: new RegExp(`^Add ${n} cop`) }).click();
  expect(bodies[1].items.map((i) => i.scryfall_id).sort()).toEqual(two.map((c) => c.printing.scryfall_id).sort());
});

test('unknown deck in the URL shows the error with a retry', async ({ page }) => {
  await page.goto('/decks?deck=nope');
  await expect(page.getByText(/not found/)).toBeVisible();
});
