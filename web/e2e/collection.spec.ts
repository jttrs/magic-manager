import { COLLECTION_ALL_URL, COLLECTION_URL, expect, fixtures, test } from './support';

const cards = fixtures.collectionBlb.cards;
const total = (c: (typeof cards)[number]) => Object.values(c.owned).reduce((s: number, n) => s + (n as number), 0);
const ownedN = cards.filter((c) => total(c) > 0).length;
const missingN = cards.length - ownedN;

test('Collection is the first tab and the default route; /sets redirects to its missing filter', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/collection/);
  await expect(page.getByRole('navigation', { name: 'Primary' }).getByRole('link').first()).toHaveText('Collection');
  await page.goto('/sets?families=%5B%22blb%22%5D');
  await expect(page).toHaveURL(/\/collection\?.*show=missing/);
});

test('no families in the URL means every family you own; picking narrows, picking all goes back to all', async ({ page }) => {
  await page.goto('/collection');
  await expect(page.getByRole('button', { name: /Set families/ })).toContainText('All families');
  await expect(page).not.toHaveURL(/families=/);
  await page.getByRole('button', { name: /Set families/ }).click();
  await page.getByRole('searchbox', { name: 'Filter families' }).fill('bloom');
  await page.getByRole('checkbox', { name: 'Bloomburrow' }).check();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/families=blb/);
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
  await page.goto(COLLECTION_ALL_URL);
  await expect(page.getByRole('article')).toHaveCount(cards.length);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Collection');
  const foil = cards.find((c) => c.owned.foil)!;
  const tile = page.getByRole('article').filter({ hasText: foil.name }).first();
  await expect(tile.getByLabel(/^Owned: /)).toContainText(`✦×${foil.owned.foil}`);
  // nothing ever overlays the art: the mark toggle lives in the caption
  expect(await tile.locator('.absolute').count()).toBe(0);
  const missing = cards.find((c) => total(c) === 0)!;
  await expect(page.getByRole('article').filter({ hasText: missing.name }).first()).toContainText('Missing');
});

test('show owned / missing filters', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const show = page.getByRole('toolbar', { name: 'Ownership' });
  await expect(page.getByRole('article')).toHaveCount(ownedN);
  await show.getByRole('button', { name: /Missing/ }).click();
  await show.getByRole('button', { name: /Owned/ }).click();
  await expect(page.getByRole('article')).toHaveCount(missingN);
});

test('Uncheck all on a card-type picker says what is hidden and offers Check all', async ({ page }) => {
  await page.goto(COLLECTION_ALL_URL);
  await page.getByRole('button', { name: /^Rarity/ }).click();
  await page.getByRole('button', { name: 'Uncheck all' }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByText('Every rarity is hidden')).toBeVisible();
  await page.getByRole('button', { name: 'Check all' }).click();
  await expect(page.getByRole('article')).toHaveCount(cards.length);
});

test('card-type filters: rarity, finish and treatment pickers (with counts), chase include/exclude with an explainer', async ({ page }) => {
  await page.goto(COLLECTION_ALL_URL);
  const rarity = page.getByRole('button', { name: /^Rarity/ });
  await expect(rarity).toContainText('All rarities');
  await rarity.click();
  await expect(page.getByRole('checkbox', { name: /^Mythic/ })).toBeVisible();
  await page.getByRole('checkbox', { name: /^Common/ }).uncheck();
  await page.getByRole('checkbox', { name: /^Uncommon/ }).uncheck();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !['common', 'uncommon'].includes(c.rarity)).length);
  await expect(rarity).toContainText('2 rarities hidden');
  await expect(page).toHaveURL(/exclude=/);
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page.getByRole('toolbar', { name: 'Ownership' }).getByRole('button', { name: /Missing/ }).click(); // reset is owned-only again

  const treat = page.getByRole('button', { name: /^Treatment/ });
  await expect(treat).toContainText('All treatments');
  await treat.click();
  await page.getByRole('button', { name: 'Uncheck all' }).click();
  await page.getByRole('checkbox', { name: /^Standard frame/ }).check();
  await page.keyboard.press('Escape');
  const codes = (c: (typeof cards)[number]) => (c.treatment ? c.treatment.split('|') : []);
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !codes(c).some((t) => t !== 'ff') && (c.standard_frame || codes(c).length > 0)).length);
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await page.getByRole('toolbar', { name: 'Ownership' }).getByRole('button', { name: /Missing/ }).click();

  await page.getByRole('radio', { name: 'Exclude' }).click();
  await expect(page.getByRole('article')).toHaveCount(cards.filter((c) => !c.is_chase).length);
  await page.getByRole('radio', { name: 'Include' }).click();
  await expect(page.getByRole('article')).toHaveCount(cards.length);
  await page.getByRole('button', { name: 'What counts as chase?' }).focus();
  await expect(page.getByRole('tooltip')).toContainText('ultra-premium variants');
  await expect(page.getByRole('tooltip')).not.toContainText('.toml');
  // Showing missing cards is itself a non-default view; back to owned-only, nothing is left to reset.
  await page.getByRole('toolbar', { name: 'Ownership' }).getByRole('button', { name: /Missing/ }).click();
  await expect(page.getByRole('button', { name: 'Reset filters' })).toHaveCount(0);
});

test('finish picker: unchecking Nonfoil judges owned/missing on foils', async ({ page }) => {
  await page.goto(COLLECTION_ALL_URL);
  await page.getByRole('button', { name: /^Finish/ }).click();
  await page.getByRole('checkbox', { name: /^Nonfoil/ }).uncheck();
  await page.keyboard.press('Escape');
  const foilish = cards.filter((c) => c.finishes.includes('foil'));
  await expect(page.getByRole('article')).toHaveCount(foilish.length);
  const show = page.getByRole('toolbar', { name: 'Ownership' });
  await show.getByRole('button', { name: /Owned/ }).click();
  await expect(page.getByRole('article')).toHaveCount(foilish.filter((c) => !(c.owned.foil ?? 0)).length);
});

test('sort builder: presets, keyboard reorder, direction, URL', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /^Sort/ }).click();
  await page.getByRole('button', { name: 'Set name › Rarity › Number' }).click();
  await expect(page.getByRole('list', { name: 'Sort levels' }).getByRole('listitem')).toHaveCount(3);
  await page.getByRole('button', { name: 'Move Rarity up' }).click();
  await expect(page).toHaveURL(/sort=rarity%2Cset%2Ccn/);
  await page.getByRole('button', { name: /^Rarity: .* Reverse$/ }).click();
  await expect(page).toHaveURL(/sort=rarity%3Aasc%2Cset%2Ccn/);
  await page.getByRole('button', { name: 'Remove Set name' }).click();
  await page.getByRole('combobox', { name: /Then by/ }).selectOption({ label: 'Price' });
  await expect(page).toHaveURL(/sort=rarity%3Aasc%2Ccn%2Cprice/);
  await page.keyboard.press('Escape');
  // lead rule drives the section heads
  await expect(page.getByRole('heading', { level: 3, name: /^Common/ })).toBeAttached();
});

test('buy list copies the missing printings shown (or the marked ones)', async ({ page }) => {
  await page.goto(COLLECTION_ALL_URL);
  await page.getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect(page.getByText(`Copied ${missingN} lines`)).toBeVisible();
  const first = cards.find((c) => total(c) === 0)!;
  await page.getByRole('button', { name: `Mark ${first.name}` }).first().click();
  await page.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  await expect(page.getByText(/^Copied 1 cards? · ≈ \$[\d.,]+ at market for TCGplayer/)).toBeVisible();
  await expect(page.getByText('Copied 1 line', { exact: true })).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${first.scryfall_id} [tcgplayer]`);
  await page.getByRole('button', { name: 'Copy Card Kingdom list' }).click();
  await expect(page.getByRole('dialog').filter({ hasText: /Card Kingdom takes names only/ })).toBeVisible();
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

test('pressing the art inspects a card (large art, facts, Scryfall/TCGplayer links); the caption list toggle marks it', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const tile = page.getByRole('article').first();
  const name = (await tile.getByRole('button', { name: /^Mark / }).getAttribute('aria-label'))!.replace(/^Mark /, '');
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

test('the rail reads Find → Show → Buy, with the card-name search first', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  const rail = page.getByRole('complementary').or(page.locator('aside')).first();
  await expect(rail.getByRole('heading', { level: 2 })).toHaveText(['Find', 'Show', 'Buy']);
  await expect(page.getByRole('heading', { level: 1, name: 'Collection' })).toHaveClass(/sr-only/);
});

test('“Missing means” is a Settings preference, not a rail filter, and it sticks', async ({ page }) => {
  await page.goto(COLLECTION_ALL_URL);
  await expect(page.getByText('Missing means')).toHaveCount(0);
  await expect(page.getByText(/missing · \$/)).toBeVisible();
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await settings.getByRole('radiogroup', { name: 'Missing means' }).getByRole('radio', { name: 'The card' }).click();
  await page.keyboard.press('Escape');
  await expect(page.getByText(/cards you own in no printing/)).toBeVisible();
  await expect(page).not.toHaveURL(/gaps/);
  await page.reload();
  await expect(page.getByText(/cards you own in no printing/)).toBeVisible();
});

test('earmarked cards carry a mark, and a filter shows only them', async ({ page }) => {
  const ids = new Set(cards.slice(0, 2).map((c) => c.oracle_id));
  const marked = cards.filter((c) => ids.has(c.oracle_id));
  await page.route((u) => u.pathname === '/api/collection', (r) => r.fulfill({ json: { ...fixtures.collectionBlb, cards: cards.map((c) => ({ ...c, earmarked: ids.has(c.oracle_id) })) } }));
  await page.goto(COLLECTION_ALL_URL);
  await expect(page.getByRole('article')).toHaveCount(cards.length);
  await page.getByRole('radio', { name: 'Only earmarked' }).click();
  await expect(page).toHaveURL(/em=true/);
  await expect(page.getByRole('article')).toHaveCount(marked.length);
  await expect(page.getByRole('article').first()).toContainText('Earmarked');
  await page.getByRole('button', { name: 'Reset filters' }).click();
  await expect(page.getByRole('article')).toHaveCount(ownedN);
});

test('old JSON-style links are rewritten to the short form, and every family spelled out collapses to all', async ({ page }) => {
  await page.goto('/collection?families=%5B%22blb%22%2C%22dft%22%5D&show=%5B%22owned%22%2C%22missing%22%5D');
  await expect(page).toHaveURL(/\/collection\?families=blb%2Cdft&show=owned%2Cmissing$/);
  const all = fixtures.families.map((f) => f.code);
  await page.goto(`/collection?families=${encodeURIComponent(JSON.stringify(all))}`);
  await expect(page).toHaveURL(/\/collection$/);
  await expect(page.getByRole('button', { name: /Set families/ })).toContainText('All families');
});

test('a search with characters the browser re-encodes does not keep rewriting the link', async ({ page }) => {
  await page.goto('/collection?q=Ahoy%20Mateys%27');
  await expect(page.getByRole('searchbox', { name: 'Card name' })).toHaveValue("Ahoy Mateys'");
  const before = await page.evaluate(() => history.length);
  await page.waitForTimeout(500);
  expect(await page.evaluate(() => history.length)).toBe(before);
  await expect(page.getByRole('searchbox', { name: 'Card name' })).toHaveValue("Ahoy Mateys'");
});
