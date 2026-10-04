import { COLLECTION_URL, expect, fixtures, test } from './support';

const cards = fixtures.collectionBlb.cards;
const total = (c: (typeof cards)[number]) => Object.values(c.owned).reduce((s: number, n) => s + (n as number), 0);
const ownedN = cards.filter((c) => total(c) > 0).length;
const missingN = cards.length - ownedN;

test('Collection is the first tab and the default route; /sets redirects to its missing filter', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/collection/);
  await expect(page.getByRole('navigation', { name: 'Primary' }).getByRole('link').first()).toHaveText('Collection');
  await page.goto('/sets?families=%5B%22blb%22%5D');
  await expect(page).toHaveURL(/\/collection\?.*show=%5B%22missing%22%5D/);
});

test('first visit opens the family picker; later visits reopen the last families', async ({ page }) => {
  await page.goto('/collection');
  await expect(page.getByText('Choose the sets you collect')).toBeVisible();
  await page.getByRole('button', { name: /Set families/ }).click();
  await page.getByRole('searchbox', { name: 'Filter families' }).fill('bloom');
  await page.getByRole('checkbox', { name: 'Bloomburrow' }).check();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/families=/);
  await page.goto('/collection');
  await expect(page).toHaveURL(/families=%5B%22blb%22%5D/);
});

test('families are a searchable checkbox list, never a chip wall', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('toolbar', { name: 'Set families' })).toHaveCount(0);
  await page.getByRole('button', { name: /Set families/ }).click();
  await expect(page.getByRole('checkbox')).toHaveCount(fixtures.families.length);
  await page.getByRole('searchbox', { name: 'Filter families' }).fill('zzzz');
  await expect(page.getByText(/No families match/)).toBeVisible();
});

test('every printing shows; owned counts and missing marks sit under the art', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('article')).toHaveCount(cards.length);
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Bloomburrow');
  const foil = cards.find((c) => c.owned.foil)!;
  const tile = page.getByRole('article').filter({ hasText: foil.name }).first();
  await expect(tile.getByLabel(/^Owned: /)).toContainText(`✦×${foil.owned.foil}`);
  // facts never overlay the art: nothing is absolutely positioned over the image button
  expect(await tile.locator('.absolute').count()).toBe(0);
  const missing = cards.find((c) => total(c) === 0)!;
  await expect(page.getByRole('article').filter({ hasText: missing.name }).first()).toContainText('Missing');
});

test('show owned / missing filters', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const show = page.getByRole('toolbar', { name: 'Show cards' });
  await show.getByRole('button', { name: /Missing/ }).click();
  await expect(page.getByRole('article')).toHaveCount(ownedN);
  await show.getByRole('button', { name: /Missing/ }).click();
  await show.getByRole('button', { name: /Owned/ }).click();
  await expect(page.getByRole('article')).toHaveCount(missingN);
});

test('card types: one grouped picker; unchecking a trait hides every card carrying it', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const trigger = page.getByRole('button', { name: /Card types/ });
  await expect(trigger).toContainText('All card types');
  await trigger.click();
  for (const g of ['Rarity', 'Treatment', 'Chase']) await expect(page.getByRole('group', { name: new RegExp(g) })).toBeVisible();
  await page.getByRole('checkbox', { name: /^Common/ }).uncheck();
  await page.getByRole('checkbox', { name: /^Uncommon/ }).uncheck();
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !['common', 'uncommon'].includes(c.rarity)).length);
  await expect(page).toHaveURL(/exclude=/);
  await page.getByRole('button', { name: 'Check all' }).click();
  await page.getByRole('button', { name: 'Clear all Treatment' }).click();
  await page.getByRole('checkbox', { name: /^Standard frame/ }).check();
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => c.standard_frame && !c.treatment).length);
  await page.getByRole('button', { name: 'Check all' }).click();
  await page.getByRole('checkbox', { name: /^Not chase/ }).uncheck();
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => c.is_chase).length);
  await page.keyboard.press('Escape');
  await expect(trigger).toContainText('Hiding Not chase');
  await trigger.click();
  await expect(page.getByText('1 unchecked')).toBeVisible();
  await page.keyboard.press('Escape');
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page.getByRole('article')).toHaveCount(cards.length);
});

test('sort builder: presets, keyboard reorder, direction, URL', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /^Sort/ }).click();
  await page.getByRole('button', { name: 'Set › Rarity › Number' }).click();
  await expect(page.getByRole('list', { name: 'Sort levels' }).getByRole('listitem')).toHaveCount(3);
  await page.getByRole('button', { name: 'Move Rarity up' }).click();
  await expect(page).toHaveURL(/sort=rarity%2Cset%2Ccn/);
  await page.getByRole('button', { name: /^Rarity: .* Reverse$/ }).click();
  await expect(page).toHaveURL(/sort=rarity%3Aasc%2Cset%2Ccn/);
  await page.getByRole('button', { name: 'Remove Set' }).click();
  await page.getByRole('combobox', { name: /Then by/ }).selectOption({ label: 'Price' });
  await expect(page).toHaveURL(/sort=rarity%3Aasc%2Ccn%2Cprice/);
  await page.keyboard.press('Escape');
  // lead rule drives the section heads
  await expect(page.getByRole('heading', { level: 3, name: /^Common/ })).toBeAttached();
});

test('buy list copies the missing printings shown (or the marked ones)', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect(page.getByText(`Copied ${missingN} lines`)).toBeVisible();
  const first = cards.find((c) => total(c) === 0)!;
  await page.getByRole('button', { name: `Mark ${first.name}` }).first().click();
  await expect(page.getByRole('heading', { name: /Buy list · 1 marked/ })).toBeVisible();
  await page.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  await expect(page.getByText('Copied 1 line', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${first.scryfall_id} [tcgplayer]`);
});

test('outline: h1 sheet, h2 family, h3 groups (no skipped levels)', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('heading', { level: 2, name: /Bloomburrow/ })).toBeVisible();
  await expect(page.getByRole('heading', { level: 3 }).first()).toBeAttached();
  await expect(page.locator('h4')).toHaveCount(0);
});
