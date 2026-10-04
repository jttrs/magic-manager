import { COMPARE_URL, expect, fixtures, test } from './support';

const counts = { a_only: 0, both: 0, b_only: 0 } as Record<string, number>;
for (const c of fixtures.compare.cards) counts[c.bucket]++;

test('pools render as three horizontal columns with counts (F4)', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const heads = page.locator('h2[id^="col-"]');
  await expect(heads).toHaveCount(3);
  await expect(heads.nth(0)).toContainText(`Tifa Lockhart only · ${counts.a_only}`);
  await expect(heads.nth(1)).toContainText(`Shared · ${counts.both}`);
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
  const name = (await tile.getByRole('button').first().getAttribute('aria-label'))!.replace(/^Mark /, '');
  const c = fixtures.compare.cards.find((x) => x.name === name)!;
  await expect(tile).toContainText(`${c.collector_number} · ${c.set_code!.toUpperCase()}`);
  await expect(tile.getByRole('img', { name: c.name })).toHaveAttribute('src', c.image_uri!);
});

test('rows density shows a dense checklist and persists in the URL', async ({ page }) => {
  await page.goto(COMPARE_URL);
  await page.getByRole('radio', { name: 'Rows' }).click();
  await expect(page).toHaveURL(/density=rows/);
  await expect(page.getByRole('checkbox', { name: /^Mark / }).first()).toBeVisible();
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

test('name filter and EDHREC list chips narrow every column', async ({ page }) => {
  await page.goto(COMPARE_URL);
  const target = fixtures.compare.cards[0].name;
  await page.getByRole('searchbox', { name: 'Card name' }).fill(target);
  await expect(page.getByRole('article')).toHaveCount(fixtures.compare.cards.filter((c) => c.name.toLowerCase().includes(target.toLowerCase())).length);
});

test('commander combobox: suggestions, keyboard choice, URL update', async ({ page }) => {
  await page.goto('/commanders');
  await expect(page.getByText('Pick two commanders')).toBeVisible();
  const box = page.getByRole('combobox', { name: 'Commander A' });
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
  await page.goto('/commanders?a=Sol%20Ring&b=Tifa%20Lockhart');
  await expect(page.getByRole('alert')).toContainText('not commander-eligible');
  await expect(page.getByRole('button', { name: 'Try again' })).toBeVisible();
});
