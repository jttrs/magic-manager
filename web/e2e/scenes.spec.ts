import { COLLECTION_URL, expect, fixtures, test } from './support';

// Bloomburrow with its first five printings re-cast as two scenes, so the Scene
// group, its per-finish heads and the per-scene buy lists run against a real payload.
const base = fixtures.collectionBlb;
const [a, b, c, d] = base.cards;
const fin = (finish: 'nonfoil' | 'foil', printings: number, owned: number, usd: number, ids: string[], unpriced = 0) => ({ finish, printings, owned, missing_usd: usd, unpriced, missing_ids: ids });
const SCENES = [
  {
    key: 'blb:1-3', family: 'blb', rank: 0, name: 'Harbor at Dusk', artist: 'A. Painter', kind: 'scene', set_code: 'blb', cn_lo: 1, cn_hi: 3,
    printings: 2, owned_printings: 1, finishes: [fin('nonfoil', 2, 1, 4.5, [b.scryfall_id]), fin('foil', 2, 0, 9.25, [a.scryfall_id, b.scryfall_id])],
  },
  {
    key: 'blb:7-8', family: 'blb', rank: 1, name: 'Poster A · Meadow', artist: 'Various artists', kind: 'poster', set_code: 'blb', cn_lo: 7, cn_hi: 8,
    printings: 2, owned_printings: 2, finishes: [fin('nonfoil', 2, 2, 0, []), fin('foil', 1, 0, 0, [d.scryfall_id], 1)],
  },
];
const scenes = { [a.scryfall_id]: 'blb:1-3', [b.scryfall_id]: 'blb:1-3', [c.scryfall_id]: 'blb:7-8', [d.scryfall_id]: 'blb:7-8' };
const WITH_SCENES = { ...base, scenes: SCENES, cards: base.cards.map((x) => ({ ...x, scene: scenes[x.scryfall_id] ?? null })) };

test.beforeEach(async ({ page }) => {
  await page.route((u) => u.pathname === '/api/collection', (r) => r.fulfill({ json: WITH_SCENES }));
});

test('Scene group: one section per scene in config order, the rest last, each head with per-finish completion', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /^Sort/ }).click();
  await page.getByRole('button', { name: 'Scene › Number' }).click();
  await expect(page).toHaveURL(/sort=scene%2Ccn/);
  const heads = page.getByRole('heading', { level: 3 });
  await expect(heads.nth(0)).toHaveText('Harbor at Dusk');
  await expect(heads.nth(1)).toHaveText('Poster A · Meadow');
  await expect(heads.nth(2)).toHaveText('Not in a scene');
  const harbor = page.locator('[data-head="h:blb:blb:1-3"]');
  await expect(harbor).toContainText('A. Painter · BLB 1–3');
  await expect(harbor.getByRole('img', { name: '50% of this scene owned in some finish' })).toBeVisible();
  await expect(harbor).toContainText(/Nonfoil\s*1\/2 · \$4\.50 to finish/);
  await expect(harbor).toContainText(/Foil\s*0\/2 · \$9\.25 to finish/);
  const poster = page.locator('[data-head="h:blb:blb:7-8"]');
  await expect(poster).toContainText(/Nonfoil\s*2\/2 · complete/);
  await expect(poster).toContainText(/Foil\s*0\/1 · 1 unpriced to finish/);
});

test('a scene’s buy lists copy its missing printings in one finish', async ({ page }) => {
  await page.goto(COLLECTION_URL + '&sort=scene,cn');
  await page.getByRole('button', { name: 'Buy lists for Harbor at Dusk' }).click();
  const pop = page.getByRole('dialog', { name: 'Buy lists for Harbor at Dusk' });
  const foil = pop.getByRole('region', { name: 'Foil', exact: true });
  await expect(foil).toContainText(/2 missing printings · \$9\.25/);
  await foil.getByRole('button', { name: 'Copy TCGplayer list' }).click();
  await expect(foil.getByText('Copied 2 lines')).toBeVisible();
  expect(await page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${a.scryfall_id} [tcgplayer]\n1 ${b.scryfall_id} [tcgplayer]`);
  await pop.getByRole('region', { name: 'Nonfoil' }).getByRole('button', { name: 'Copy ManaPool list' }).click();
  await expect.poll(() => page.evaluate(() => navigator.clipboard.readText())).toBe(`1 ${b.scryfall_id} [manapool]`);
});

test('families without scenes never offer the Scene group', async ({ page }) => {
  await page.route((u) => u.pathname === '/api/collection', (r) => r.fulfill({ json: base }));
  await page.goto(COLLECTION_URL + '&sort=scene,cn');
  await expect(page.getByRole('heading', { name: 'Not in a scene' })).toHaveCount(0);
  await expect(page.getByRole('article')).toHaveCount(base.cards.length);
});
