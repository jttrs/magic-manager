import { expect, fixtures, test } from './support';

const detail = fixtures.deckDetail;
const editable = { ...detail, version_id: 7, editable: true };
const card = detail.cards.find((c) => c.board === 'main')!;
const cur = card.printing;
const pick = { ...cur, scryfall_id: 'cat-free', set_code: 'sld', collector_number: '42', owned: { nonfoil: 2 }, free: 2 };
const alt = { ...cur, scryfall_id: 'cat-cheap', set_code: 'plst', collector_number: '7', owned: {}, free: 0, price_usd: 0.25 };
const TAGS = { synced: true, tags: [{ id: 'tag-cat', label: 'cat', slug: 'cat', illustrations: 156 }, { id: 'tag-house', label: 'housecat', slug: 'housecat', illustrations: 128 }] };
const swaps = (sids: string[]) => ({
  tag: { id: 'tag-cat', label: 'cat' },
  rows: sids.map((sid) => (sid === cur.scryfall_id
    ? { scryfall_id: sid, status: 'swap', pick: 'cat-free', candidates: ['cat-free', 'cat-cheap'] }
    : sid === 'cat-free' || sid === 'cat-cheap'
      ? { scryfall_id: sid, status: 'on_theme', pick: sid, candidates: ['cat-free', 'cat-cheap'] }
      : { scryfall_id: sid, status: 'none', pick: null, candidates: [] })),
  printings: { [cur.scryfall_id]: cur, 'cat-free': pick, 'cat-cheap': alt },
  matched: { 'cat-free': ['cat'], 'cat-cheap': ['housecat'] },
  free_by_finish: { 'cat-free': { nonfoil: 2, foil: 0 } },
});

test('editor: the Art tab swaps a card onto an on-theme printing you have free, and undoes it', async ({ page }) => {
  const asked: string[][] = [];
  let looked = 0;
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: editable }));
  await page.route('**/api/decks/*/check', (r) => r.fulfill({ json: { format: 'commander', legality: { format: 'commander', legal: true, checked_count: 1, violations: [] }, bracket: null } }));
  await page.route('**/api/art/tags**', (r) => r.fulfill({ json: TAGS }));
  await page.route('**/api/art/swaps', (r) => {
    const sids = (r.request().postDataJSON() as { cards: { scryfall_id: string }[] }).cards.map((c) => c.scryfall_id);
    asked.push(sids);
    return r.fulfill({ json: swaps(sids) });
  });
  await page.route('**/api/art/lookup', (r) => { looked += 1; return r.fulfill({ json: { searched: 3, added: 0 } }); });
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);
  await page.getByRole('tab', { name: 'Art' }).click();

  await page.getByLabel('Art theme').fill('ca');
  await page.getByRole('button', { name: /^cat/ }).click();
  await expect(page.getByRole('heading', { name: /Can swap/ })).toContainText('1');
  await expect(page.getByText('SLD #42 · 2 free')).toBeVisible();

  await page.getByRole('button', { name: '1 other printing' }).click();
  await expect(page.getByRole('button', { name: 'Use PLST #7, $0.25' })).toBeVisible();

  await page.getByRole('button', { name: /Swap all free · 1/ }).click();
  await expect(page.getByText('1 swapped')).toBeVisible();
  await expect.poll(() => asked.some((s) => s.includes('cat-free'))).toBe(true);   // re-asked with the new printing
  await expect(page.getByText(/was /)).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save deck' })).toBeEnabled();

  await page.getByRole('button', { name: `Undo swap of ${cur.name}` }).click();
  await expect(page.getByText('1 swapped')).toHaveCount(0);

  await page.getByRole('button', { name: 'Look on Scryfall for more' }).click();
  await expect(page.getByText('Scryfall has nothing new for these cards.')).toBeVisible();
  expect(looked).toBe(1);
});

test('editor: the Art tab offers to load art themes when the tag cache is empty', async ({ page }) => {
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: editable }));
  await page.route('**/api/decks/*/check', (r) => r.fulfill({ json: { format: 'commander', legality: { format: 'commander', legal: true, checked_count: 1, violations: [] }, bracket: null } }));
  await page.route('**/api/art/tags**', (r) => r.fulfill({ json: { synced: false, tags: [] } }));
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);
  await page.getByRole('tab', { name: 'Art' }).click();
  await expect(page.getByText('Art themes aren’t loaded yet')).toBeVisible();
  await expect(page.getByRole('button', { name: 'Load art themes' })).toBeEnabled();
});
