import { expect, fixtures, test } from './support';

const detail = fixtures.deckDetail;
const editable = { ...detail, version_id: 7, editable: true };
const base = detail.cards.find((c) => c.board === 'main')!.printing;
const pr = (id: string, name: string, o: Record<string, unknown> = {}) => ({ ...base, scryfall_id: id, oracle_id: `o-${id}`, name, ...o });
const mark = (id: string, name: string, o: Record<string, unknown> = {}) => ({
  oracle_id: `o-${id}`, name, scryfall_id: null, finish: null, reason: null, deck_slug: null, deck_name: null, note: null,
  earmarked_at: '2026-10-19T00:00:00+00:00', updated_at: '2026-10-19T00:00:00+00:00', ...o,
});
const entry = (id: string, name: string, o: Record<string, unknown> = {}, owned = 0) => ({ earmark: mark(id, name, o), printing: pr(id, name), owned, free: owned });

test('Explore → Earmarked lists your earmarks, filters them, and the inspector edits or removes one', async ({ page }) => {
  let list = [
    entry('sentinel', 'Esper Sentinel', { reason: 'collect', note: 'MH2 foil' }, 2),
    entry('runes', 'Mother of Runes', { reason: 'deck', deck_slug: 'squall', deck_name: 'Squall' }),
  ];
  const puts: Record<string, unknown>[] = [];
  const deletes: string[] = [];
  await page.route('**/api/earmarks/cards**', (r) => {
    const req = r.request();
    if (req.method() === 'PUT') {
      const body = req.postDataJSON() as Record<string, unknown>;
      puts.push(body);
      list = list.map((e) => (e.earmark.name === 'Esper Sentinel' ? { ...e, earmark: { ...e.earmark, reason: body.reason as string, note: body.note as string } } : e));
      return r.fulfill({ json: list[0].earmark });
    }
    if (req.method() === 'DELETE') {
      deletes.push(new URL(req.url()).pathname.split('/').pop()!);
      list = list.filter((e) => e.earmark.oracle_id !== deletes.at(-1));
      return r.fulfill({ json: { removed: true } });
    }
    return r.fulfill({ json: list });
  });
  await page.goto('/explore?mode=earmarked&rview=list');

  await expect(page.getByRole('navigation', { name: 'Explore views' }).getByRole('link', { name: 'Earmarked' })).toHaveAttribute('aria-current', 'page');
  const table = page.getByRole('region', { name: 'Earmarked cards' });
  await expect(table.getByRole('row')).toHaveCount(3);
  await expect(table).toContainText('To collect · MH2 foil');
  await expect(table).toContainText('Deck idea · for Squall');
  await page.getByRole('button', { name: /^Why/ }).click();
  await page.getByRole('menuitemradio', { name: 'Deck idea' }).click();
  await expect(table.getByRole('row')).toHaveCount(2);
  await expect(page).toHaveURL(/er=deck/);
  await page.getByRole('button', { name: /^Why/ }).click();
  await page.getByRole('menuitemradio', { name: 'Any' }).click();

  await table.getByRole('button', { name: 'Esper Sentinel', exact: true }).click();
  const dlg = page.getByRole('dialog');
  await expect(dlg.getByRole('button', { name: 'Earmarked' })).toHaveAttribute('aria-pressed', 'true');
  await dlg.getByRole('radio', { name: 'Deck idea' }).click();
  await expect.poll(() => puts.at(-1)?.reason).toBe('deck');
  expect(puts.at(-1)).toMatchObject({ card: 'sentinel', note: 'MH2 foil' });   // the other fields ride along unchanged
  await dlg.getByRole('button', { name: 'Earmarked' }).click();
  await expect.poll(() => deletes).toEqual(['o-sentinel']);
  await expect(dlg.getByRole('button', { name: 'Earmark', exact: true })).toHaveAttribute('aria-pressed', 'false');
});

test('Explore → Earmarked says how to start when nothing is earmarked', async ({ page }) => {
  await page.goto('/explore?mode=earmarked');
  await expect(page.getByText('No earmarked cards yet')).toBeVisible();
});

test('editor: the Earmarked tab lists cards for this deck first, then those that fit, and says why others are hidden', async ({ page }) => {
  const asked: unknown[] = [];
  const fits = pr('fits', 'Fitting Card');
  await page.route((u) => u.pathname === `/api/decks/${detail.deck.slug}`, (r) => r.fulfill({ json: editable }));
  await page.route('**/api/decks/*/check', (r) => r.fulfill({ json: { format: 'commander', legality: { format: 'commander', legal: true, checked_count: 1, violations: [] }, bracket: null } }));
  await page.route('**/api/decks/*/earmarked', (r) => {
    asked.push(r.request().postDataJSON());
    return r.fulfill({
      json: {
        format: 'commander', commander_colors: ['W', 'B'],
        for_deck: [{ ...entry('pinned', 'Pinned Card', { reason: 'deck', deck_slug: detail.deck.slug, deck_name: detail.deck.name }), in_deck: false, reasons: [] }],
        legal: [{ earmark: mark('fits', 'Fitting Card', { reason: 'collect' }), printing: fits, owned: 1, free: 1, in_deck: false, reasons: [] }],
        hidden: [
          { ...entry('bolt', 'Lightning Bolt'), in_deck: false, reasons: ['Outside the commander’s colours (white, black)'] },
          { ...entry('bad', 'Bad Card'), in_deck: false, reasons: ['Banned in Commander'] },
        ],
      },
    });
  });
  await page.goto(`/decks/${encodeURIComponent(detail.deck.slug)}/edit`);
  const tabs = page.getByRole('tablist', { name: 'Find cards' });
  await expect(tabs.getByRole('tab')).toHaveText(['Search', 'Bulk Add', 'Suggestions', 'Earmarked', 'Combos', 'Art']);
  await tabs.getByRole('tab', { name: 'Earmarked' }).click();

  await expect(page.getByText('Legal in Commander · within white, black')).toBeVisible();
  await expect(page.getByRole('region', { name: 'For this deck' })).toContainText('Pinned Card');
  await expect(page.getByRole('region', { name: 'Earmarked cards that fit' })).toContainText('Fitting Card');
  const summary = page.getByText('2 hidden · 1 banned in Commander · 1 outside the commander’s colours');
  await expect(summary).toBeVisible();
  await expect(page.getByRole('list', { name: 'Hidden earmarked cards' })).toBeHidden();
  await summary.click();
  await expect(page.getByRole('list', { name: 'Hidden earmarked cards' })).toContainText('Lightning Bolt');
  expect((asked[0] as { cards: unknown[] }).cards.length).toBeGreaterThan(0);   // judged on the draft

  await page.getByRole('button', { name: 'Add Fitting Card' }).click();
  await expect(page.getByRole('button', { name: 'Save deck' })).toBeEnabled();
});
