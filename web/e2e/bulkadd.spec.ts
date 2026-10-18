import { expect, fixtures, test } from './support';

const detail = fixtures.deckDetail;
const editable = { ...detail, version_id: 7, editable: true };
const base = detail.cards.find((c) => c.board === 'main')!.printing;
const pr = (id: string, name: string, type_line: string, o: Record<string, unknown> = {}) => ({ ...base, scryfall_id: id, oracle_id: `o-${id}`, name, type_line, ...o });
const LEADER = pr('bulk-leader', 'Bulk Leader', 'Legendary Creature — Human Mercenary');
const RUNES = pr('bulk-runes', 'Bulk Runes', 'Creature — Human Cleric', { finishes: ['nonfoil', 'foil'] });
const BRIDGE = pr('bulk-bridge', 'Bulk Bridge', 'Artifact');
const line = (n: number, raw: string, p: typeof LEADER, section: string, board: string, finish = 'nonfoil') => ({
  line: n, raw, qty: 1, name: p.name, finish, section, board, status: 'exact', candidates: [p], chosen: p.scryfall_id, note: null,
});
const RESOLVED = {
  format: 'moxfield', warnings: [], deck_name: null, deck: null,
  lines: [
    line(1, '1 Bulk Leader (TST) 1 *CMDR*', LEADER, 'commander', 'commander'),
    line(2, '1 Bulk Runes (TST) 2 *F*', RUNES, 'mainboard', 'main', 'foil'),
    line(4, '1 Bulk Bridge (TST) 3', BRIDGE, 'sideboard', 'side'),
    { line: 5, raw: '1 Nonesuch', qty: 1, name: 'Nonesuch', finish: 'nonfoil', section: 'sideboard', board: 'side', status: 'unresolved', candidates: [], chosen: null, note: "No card named 'Nonesuch'" },
  ],
};

test('editor: Bulk Add reads a pasted list, groups it by board, keeps it across tabs, and adds it to the draft', async ({ page }) => {
  const asked: { text: string }[] = [];
  let saved = 0;
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: editable }));
  await page.route('**/api/decks/*/check', (r) => r.fulfill({ json: { format: 'commander', legality: { format: 'commander', legal: true, checked_count: 1, violations: [] }, bracket: null } }));
  await page.route('**/api/ingest/resolve', (r) => {
    asked.push(r.request().postDataJSON() as { text: string });
    return r.fulfill({ json: RESOLVED });
  });
  await page.route('**/api/ingest/commit', () => { saved += 1; });
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);

  const tabs = page.getByRole('tablist', { name: 'Find cards' });
  await expect(tabs.getByRole('tab')).toHaveText(['Search', 'Bulk Add', 'Suggestions', 'Combos', 'Art']);
  await tabs.getByRole('tab', { name: 'Bulk Add' }).click();
  await page.getByLabel('Card list').fill('1 Bulk Leader (TST) 1 *CMDR*\n1 Bulk Runes (TST) 2 *F*\nSideboard\n1 Bulk Bridge (TST) 3\n1 Nonesuch');
  await page.getByRole('button', { name: 'Read list' }).click();

  await expect(page.getByRole('heading', { name: '3 of 4 lines matched' })).toBeVisible();
  for (const board of ['Commander', 'Main deck', 'Sideboard']) await expect(page.getByRole('region', { name: board, exact: true })).toBeVisible();
  await expect(page.getByText('3 copies')).toBeVisible();
  expect(asked[0].text).toContain('*CMDR*');

  // The reviewed list survives a trip to another tab.
  await tabs.getByRole('tab', { name: 'Search' }).click();
  await tabs.getByRole('tab', { name: 'Bulk Add' }).click();
  await expect(page.getByRole('heading', { name: '3 of 4 lines matched' })).toBeVisible();

  await page.getByRole('button', { name: 'Add 3 cards to deck' }).click();
  await expect(page.getByRole('status')).toContainText('Added 3 cards to the deck. Save deck to keep them.');
  await expect(page.getByLabel('Card list')).toHaveValue('');
  const deck = page.getByRole('main');
  for (const name of ['Bulk Leader', 'Bulk Runes', 'Bulk Bridge']) await expect(deck.getByRole('button', { name, exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Save deck' })).toBeEnabled();
  expect(saved).toBe(0);   // a deck draft never touches the collection
});
