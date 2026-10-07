import { expect, fixtures, profile, test } from './support';

const detail = fixtures.deckDetail;
const editable = { ...detail, version_id: 7, editable: true };
const printing = { ...detail.cards[0].printing, scryfall_id: 'lattice', oracle_id: 'o-lattice', name: 'Mycosynth Lattice', type_line: 'Artifact', owned: { nonfoil: 1 }, free: 1 };
const facts = (owned: number, free: number, usd = 35.54) => ({ oracle_id: null, type_line: 'Artifact', cmc: 6, color_identity: [], lowest_usd: usd, scryfall_id: null, image_uri: null, set_code: null, collector_number: null, scryfall_url: null, owned, free });
const inDeck = detail.cards.find((c) => c.board !== 'commander' && c.board !== 'token')!.printing.name;
const piece = (name: string, in_deck: boolean, o: Record<string, unknown> = {}) => ({ name, oracle_id: `o-${name}`, in_deck, facts: facts(in_deck ? 1 : 0, 0), image_uri: null, printing: null, ...o });
const lattice = piece('Mycosynth Lattice', false, { oracle_id: 'o-lattice', facts: facts(1, 1), printing });
const combo = (id: string, pieces: unknown[], o: Record<string, unknown> = {}) => ({
  id, url: `https://commanderspellbook.com/combo/${id}/`, pieces, produces: ['Destroy all permanents opponents control', 'Mass Land Denial'], requires: [],
  description: 'Cast Vandalblast with overload.\nAll permanents are artifacts.', prerequisites: 'Mycosynth Lattice on the battlefield.', mana_needed: '{4}{R}', popularity: 5200, identity: 'R', missing: null, ...o,
});
const COMBOS = {
  available: true, error: null, identity: 'RW', off_color: 2,
  included: [combo('in-1', [piece(inDeck, true), piece('Basalt Monolith', true)], { produces: ['Infinite colorless mana'] })],
  almost: [combo('near-1', [piece(inDeck, true), lattice], { missing: lattice })],
  missing_cards: [{ piece: lattice, combos: ['near-1'], popularity: 5200 }],
};

test('editor: the Combos tab lists what one card would complete and adds it', async ({ page }) => {
  const bodies: { cards: { scryfall_id: string }[] }[] = [];
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: editable }));
  await page.route('**/api/decks/*/check', (r) => r.fulfill({ json: { format: 'commander', legality: { format: 'commander', legal: true, checked_count: 1, violations: [] }, bracket: null } }));
  await page.route('**/api/combos/draft', (r) => { bodies.push(r.request().postDataJSON()); return r.fulfill({ json: COMBOS }); });
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);
  await page.getByRole('tab', { name: 'Combos' }).click();
  await expect(page.getByText('1 in this deck · 1 one card away · 2 more need another colour')).toBeVisible();
  await expect(page.getByRole('heading', { name: /One card away/ })).toContainText('1 card');
  await expect(page.getByText('1 free', { exact: true })).toBeVisible();

  await page.getByRole('button', { name: 'Completes 1 combo' }).click();
  const how = page.getByRole('button', { name: new RegExp(`${inDeck} \\+ Mycosynth Lattice — how it works`) });
  await how.click();
  await expect(page.getByText('All permanents are artifacts.')).toBeVisible();
  await expect(page.getByRole('link', { name: /Commander Spellbook/ }).first()).toHaveAttribute('href', 'https://commanderspellbook.com/combo/near-1/');

  await page.getByRole('button', { name: 'Add Mycosynth Lattice' }).click();
  await expect(page.getByText('+1')).toBeVisible();
  await expect.poll(() => bodies.some((b) => b.cards.some((c) => c.scryfall_id === 'lattice'))).toBe(true);   // re-asked with the new card
});

test('deck manager: the Combos action opens the deck’s combos; Spellbook outages say so', async ({ page }) => {
  let fail = false;
  await page.route('**/api/decks/*/combos', (r) => r.fulfill({ json: fail ? { available: false, error: 'Couldn’t reach Commander Spellbook: HTTP 503', identity: null, included: [], almost: [], missing_cards: [], off_color: 0 } : COMBOS }));
  await page.goto(`/decks?deck=${encodeURIComponent(detail.deck.slug)}`);
  await page.getByRole('toolbar', { name: 'Deck actions' }).getByRole('button', { name: 'Combos' }).click();
  const dialog = page.getByRole('dialog', { name: 'Combos' });
  await expect(dialog.getByRole('heading', { name: /In this deck/ })).toContainText('1 combo');
  await expect(dialog.getByText('Infinite colorless mana')).toBeVisible();
  await expect(dialog.getByRole('button', { name: /^Add / })).toHaveCount(0);     // read-only here
  await page.keyboard.press('Escape');
  fail = true;
  await page.reload();
  await page.getByRole('toolbar', { name: 'Deck actions' }).getByRole('button', { name: 'Combos' }).click();
  await expect(page.getByRole('dialog', { name: 'Combos' }).getByRole('alert')).toContainText('HTTP 503');
});

test('explore: a card plate shows the combos the card is part of, on demand', async ({ page }) => {
  let asked = 0;
  await page.route('**/api/explore/card**', (r) => r.fulfill({ json: { a: profile('Isochron Scepter', { commander_eligible: false }), b: null, commanders: [], coplayed: [], tags: {} } }));
  await page.route('**/api/combos/card**', (r) => {
    asked++;
    return r.fulfill({ json: { available: true, name: 'Isochron Scepter', error: null, combos: [combo('c1', [piece('Dramatic Reversal', false, { facts: facts(2, 1) }), piece('Isochron Scepter', false)], { produces: ['Infinite magecraft triggers'] })] } });
  });
  await page.goto('/explore?a=Isochron%20Scepter&role=card');
  const toggle = page.getByRole('button', { name: 'Combos', exact: true });
  await expect(toggle).toHaveAttribute('aria-expanded', 'false');
  expect(asked).toBe(0);
  await toggle.click();
  const section = page.getByRole('region', { name: /Combos with Isochron Scepter/ });
  await expect(section).toContainText('you own 1 of 2');
  await expect(section).toContainText('Infinite magecraft triggers');
  await page.getByRole('button', { name: 'Hide combos' }).click();
  await expect(section).toHaveCount(0);
});
