import { COMPARE_URL, expect, fixtures, test } from './support';

const counts = { a_only: 0, both: 0, b_only: 0 } as Record<string, number>;
for (const c of fixtures.compare.cards) counts[c.bucket]++;

test('pools render as three horizontal columns with counts (F4)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const heads = page.locator('h2[id^="col-"]');
  await expect(heads).toHaveCount(3);
  await expect(heads.nth(0)).toContainText(`Tifa Lockhart only · ${counts.a_only}`);
  await expect(heads.nth(1)).toContainText(`Both · ${counts.both}`);
  await expect(heads.nth(2)).toContainText(`Cloud only · ${counts.b_only}`);
  const boxes = await Promise.all([0, 1, 2].map((i) => heads.nth(i).boundingBox()));
  expect(boxes[0]!.x).toBeLessThan(boxes[1]!.x);
  expect(boxes[1]!.x).toBeLessThan(boxes[2]!.x);
  expect(Math.abs(boxes[0]!.y - boxes[2]!.y)).toBeLessThan(2);
});

test('a column can be hidden and shown again; state lives in the URL', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await page.getByRole('button', { name: 'Hide Cloud only column' }).click();
  await expect(page.locator('#col-b_only')).toHaveCount(0);
  await expect(page).toHaveURL(/show=/);
  await page.reload();
  await expect(page.locator('#col-b_only')).toHaveCount(0);
  await page.getByRole('toolbar', { name: 'Visible columns' }).getByRole('button', { name: /Cloud only/ }).click();
  await expect(page.locator('#col-b_only')).toHaveCount(1);
});

test('dividers resize columns from the keyboard (window splitter)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const col = page.locator('section[aria-labelledby="col-a_only"]');
  const before = (await col.boundingBox())!.width;
  await page.getByRole('separator').first().focus();
  for (let i = 0; i < 3; i++) await page.keyboard.press('ArrowRight');
  const after = (await col.boundingBox())!.width;
  expect(after).toBeGreaterThan(before + 40);
});

test('shared cards carry two labelled inclusion bars', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const shared = page.locator('section[aria-labelledby="col-both"]');
  await expect(shared.getByText('Tifa Lockhart (top)')).toBeVisible();
  const both = fixtures.compare.cards.find((c) => c.bucket === 'both')!;
  await expect(shared.getByLabel(new RegExp(`^Tifa Lockhart ${Math.round(both.a_pct!)}%`)).first()).toBeAttached();
});

test('display printing is the standard one returned by the API (F3)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const tile = page.locator('section[aria-labelledby="col-a_only"]').getByRole('article').first();
  const name = (await tile.getByRole('button', { name: /^Mark / }).getAttribute('aria-label'))!.replace(/^Mark /, '');
  const c = fixtures.compare.cards.find((x) => x.name === name)!;
  await expect(tile).toContainText(`${c.collector_number} · ${c.set_code!.toUpperCase()}`);
  await expect(tile.getByRole('img', { name: c.name })).toHaveAttribute('src', c.image_uri!);
});

test('list view shows a dense checklist and persists in the URL', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await page.getByRole('radio', { name: 'List' }).click();
  await expect(page).toHaveURL(/view=list/);
  await expect(page.getByRole('button', { name: /^Mark / }).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /^Inspect / }).first()).toBeVisible();
  await expect(page.getByRole('article')).toHaveCount(0);
});

test('marking cards highlights them and copies a plain list', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const first = page.getByRole('button', { name: /^Mark / }).first();
  const name = (await first.getAttribute('aria-label'))!.replace(/^Mark /, '');
  await first.click();
  await expect(page.getByRole('button', { name: `Unmark ${name}` })).toHaveAttribute('aria-pressed', 'true');
  await expect(page.getByRole('heading', { name: 'Marked · 1' })).toBeVisible();
  await page.getByRole('button', { name: 'Copy marked as list' }).click();
  await expect(page.getByText('Copied 1 line')).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${name}`);
});

test('sheet is titled Commanders; EDHREC lists live in a multi-select, not a chip wall', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('Explore');
  await page.getByRole('button', { name: /EDHREC lists/ }).click();
  await expect(page.getByRole('searchbox', { name: 'Filter lists' })).toBeVisible();
});

test('sort rules come from the shared builder and land in the URL', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await page.getByRole('button', { name: /^Sort/ }).click();
  await page.getByRole('button', { name: 'Biggest inclusion gap' }).click();
  await expect(page).toHaveURL(/sort=delta%2Cinclusion/);
});

test('name filter and EDHREC list chips narrow every column', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const target = fixtures.compare.cards[0].name;
  await page.getByRole('searchbox', { name: 'Card name' }).fill(target);
  await expect(page.getByRole('article')).toHaveCount(fixtures.compare.cards.filter((c) => c.name.toLowerCase().includes(target.toLowerCase())).length);
});

test('card combobox: suggestions, keyboard choice, URL update', async ({ page }) => {
  await page.goto('/explore');
  await expect(page.getByText('Explore a card')).toBeVisible();
  const box = page.getByRole('combobox', { name: 'Card' });
  await box.fill('tifa');
  await expect(page.getByRole('listbox')).toBeVisible();
  await box.press('ArrowDown');
  await box.press('Enter');
  await expect(page).toHaveURL(/a=Tifa/);
});

test('engine errors surface with a retry, not a blank sheet', async ({ page }) => {
  await page.unrouteAll();
  const { mockApi } = await import('./support');
  await mockApi(page, { '/api/edhrec/compare': () => ({ status: 422, json: { detail: "'Sol Ring' is not commander-eligible" } }) });
  await page.goto('/explore?a=Sol%20Ring&b=Tifa%20Lockhart&role=commander');
  await expect(page.getByRole('alert')).toContainText('not commander-eligible');
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
});

test('explore a card as a card: commanders that run it, played alongside, similar; role follows eligibility', async ({ page }) => {
  const { profile } = await import('./support');
  const e = (name: string, o: Record<string, unknown> = {}) => ({ name, slug: name.toLowerCase(), facts: profile(name).facts, num_decks: 10, potential_decks: 20, share: 50, lift: 1.5, group: null, ...o });
  await page.route('**/api/explore/card?**', (r) => r.fulfill({ json: {
    a: profile('Sol Ring', { commander_eligible: false, commanders: [e('Tifa Lockhart', { group: 'top' })], coplayed: [e('Arcane Signet', { group: 'Mana rocks', lift: 2.25 })], similar: [e('Mana Vault')] }),
    b: null, commanders: [], coplayed: [], tags: {},
  } }));
  await page.goto('/explore?a=Sol%20Ring');
  await expect(page.getByRole('radio', { name: 'As commander' })).toBeDisabled();
  await expect(page.getByRole('radio', { name: 'As a card' })).toHaveAttribute('aria-checked', 'true');
  for (const h of ['Commanders that run it', 'Played alongside', 'Similar cards']) await expect(page.getByRole('heading', { name: new RegExp(`^${h}`) })).toBeVisible();
  await expect(page.getByText('2.25× lift')).toBeVisible();
  await expect(page.getByRole('link', { name: /EDHREC/ })).toHaveAttribute('href', /\/cards\/sol-ring$/);
});

test('old /commanders links land on Explore as commander; the inspector offers Explore this card', async ({ page }) => {
  await page.goto('/commanders?a=Tifa%20Lockhart&b=Cloud%2C%20Ex-SOLDIER');
  await expect(page).toHaveURL(/\/explore\?.*role=commander/);
  const tile = page.getByRole('article').first();
  const name = (await tile.getByRole('button', { name: /^Mark / }).getAttribute('aria-label'))!.replace(/^Mark /, '');
  await tile.getByRole('button', { name: `Inspect ${name}` }).click();
  await page.getByRole('dialog').getByRole('link', { name: 'Explore this card' }).click();
  await expect(page).toHaveURL(/\/explore\?a=/);
  await expect(page.getByRole('combobox', { name: 'Card' })).toHaveValue(name.split(' // ')[0]);
});
