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
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Collection');
  const foil = cards.find((c) => c.owned.foil)!;
  const tile = page.getByRole('article').filter({ hasText: foil.name }).first();
  await expect(tile.getByLabel(/^Owned: /)).toContainText(`✦×${foil.owned.foil}`);
  // facts never overlay the art; the only overlay is the inspect affordance, invisible until hover/focus
  const overlays = tile.locator('.absolute');
  await expect(overlays).toHaveCount(1);
  await expect(overlays).toHaveAttribute('aria-label', /^Inspect /);
  await page.mouse.move(0, 0);
  await expect(overlays).toHaveCSS('opacity', '0');
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
  for (const g of ['Finish', 'Rarity', 'Treatment', 'Chase']) await expect(page.getByRole('group', { name: new RegExp(g) })).toBeVisible();
  await page.getByRole('checkbox', { name: /^Common/ }).uncheck();
  await page.getByRole('checkbox', { name: /^Uncommon/ }).uncheck();
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !['common', 'uncommon'].includes(c.rarity)).length);
  await expect(page).toHaveURL(/exclude=/);
  await page.getByRole('button', { name: 'Check all' }).click();
  await page.getByRole('button', { name: 'Clear all Treatment' }).click();
  await page.getByRole('checkbox', { name: /^Standard frame/ }).check();
  const codes = (c: (typeof cards)[number]) => (c.treatment ? c.treatment.split('|') : []);
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !codes(c).some((t) => t !== 'ff') && (c.standard_frame || codes(c).length > 0)).length);
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

test('finish lives in card types: unchecking Nonfoil judges owned/missing on foils', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /Card types/ }).click();
  await page.getByRole('checkbox', { name: /^Nonfoil/ }).uncheck();
  await page.keyboard.press('Escape');
  const foilish = cards.filter((c) => c.finishes.includes('foil'));
  await expect(page.getByRole('article')).toHaveCount(foilish.length);
  const show = page.getByRole('toolbar', { name: 'Show cards' });
  await show.getByRole('button', { name: /Owned/ }).click();
  await expect(page.getByRole('article')).toHaveCount(foilish.filter((c) => !(c.owned.foil ?? 0)).length);
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
  await expect(page.getByText('Copy bulk lists · 1 marked', { exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  await expect(page.getByText('Copied 1 line', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${first.scryfall_id} [tcgplayer]`);
  await page.getByRole('button', { name: 'Copy Card Kingdom list' }).click();
  await expect(page.getByText(/Card Kingdom takes names only/)).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${first.scryfall_id} [cardkingdom]`);
});

test('outline: h1 sheet, h2 family, h3 groups (no skipped levels)', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('heading', { level: 2, name: /Bloomburrow/ })).toBeVisible();
  await expect(page.getByRole('heading', { level: 3 }).first()).toBeAttached();
  await expect(page.locator('h4')).toHaveCount(0);
});

test('family head names itself; sections collapse and jump', async ({ page }) => {
  await page.goto(COLLECTION_URL + '&sort=rarity');
  await expect(page.getByText('Set family', { exact: false }).first()).toBeVisible();
  const fam = page.getByRole('heading', { level: 2 }).getByRole('button', { name: 'Bloomburrow' });
  await fam.click();
  await expect(fam).toHaveAttribute('aria-expanded', 'false');
  await expect(page.getByRole('article')).toHaveCount(0);
  await expect(page.getByRole('heading', { level: 3 })).toHaveCount(0);
  await fam.click();
  const first = page.getByRole('heading', { level: 3 }).first().getByRole('button');
  await expect(first).toHaveAttribute('aria-expanded', 'true');
  const firstName = (await first.textContent())!;
  await expect(page.getByRole('button', { name: 'Previous group' }).first()).toBeDisabled();
  await page.getByRole('button', { name: 'Next group' }).first().click();
  await expect(page.locator(':focus')).not.toHaveText(firstName);
  await expect(page.locator(':focus')).toHaveAttribute('aria-expanded', 'true');
  await page.locator(':focus').click();
  await expect(page.locator(':focus')).toHaveAttribute('aria-expanded', 'false');
});

test('magnifier inspects a card (large art, facts, Scryfall/TCGplayer links); the rest of the card still marks', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const tile = page.getByRole('article').first();
  const name = (await tile.getByRole('button').first().getAttribute('aria-label'))!.replace(/^Mark /, '');
  await tile.getByRole('button', { name: `Inspect ${name}` }).click();
  const dialog = page.getByRole('dialog', { name });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('img', { name })).toHaveAttribute('src', /\/large\//);
  await expect(dialog.getByRole('link', { name: /TCGplayer/ })).toHaveAttribute('href', /tcgplayer\.com\/search\/magic/);
  await expect(dialog.getByText('Printing')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
  await expect(page.getByRole('button', { name: `Unmark ${name}` })).toHaveCount(0);
  await tile.getByRole('button', { name: `Mark ${name}` }).click();
  await expect(page.getByRole('button', { name: `Unmark ${name}` }).first()).toBeVisible();
});
