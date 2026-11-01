import { expect, mockApi, test } from './support';
import history from './fixtures/history.json' with { type: 'json' };
import event from './fixtures/history-event.json' with { type: 'json' };

const mockHistory = (page: Parameters<typeof mockApi>[0]) =>
  mockApi(page, {
    '/api/history/': (url) => {
      const id = Number(url.pathname.split('/').pop());
      return id === event.entry.ingest_id
        ? { json: event }
        : { json: { entry: history.entries.find((e) => e.ingest_id === id), lines: [] } };
    },
    '/api/history': () => ({ json: history }),
  });

test('purchase history is a Collection sheet: timeline by month, deck moves gathered, filters', async ({ page }) => {
  await mockHistory(page);
  await page.goto('/collection');
  await page.getByRole('navigation', { name: 'Collection views' }).getByRole('link', { name: 'Purchase history' }).click();
  await expect(page).toHaveURL(/\/collection\/history/);
  await expect(page.getByRole('link', { name: 'Collection', exact: true })).toHaveAttribute('aria-current', 'page');
  const list = page.getByRole('navigation', { name: 'Purchase history' });
  await expect(list.getByRole('heading', { name: /October 2026/ })).toBeVisible();
  // Two same-day deck moves collapse into one quiet run that expands.
  const run = list.getByRole('button', { name: /Built 2 decks/ });
  await expect(run).toHaveAttribute('aria-expanded', 'false');
  await run.click();
  await expect(list.getByRole('button', { name: /Built Party Time/ })).toBeVisible();
  // Kind filter + search.
  await page.getByRole('button', { name: /^Kind of entry/ }).click();
  await page.getByRole('checkbox', { name: /^Card pool/ }).check();
  await page.keyboard.press('Escape');
  await expect(page).toHaveURL(/kinds=/);
  await expect(list.getByRole('button')).toHaveCount(1);
  await page.getByRole('button', { name: 'Clear filters' }).click();
  await page.getByRole('searchbox', { name: 'Product, set or file' }).fill('hobbit');
  await expect(list.getByRole('button')).toHaveCount(1);
  await expect(list.getByRole('button')).toContainText('350 rows');
});

test('drill into an entry: what came in, worth today, exact printings, open deck', async ({ page }) => {
  await mockHistory(page);
  await page.goto(`/collection/history?entry=${event.entry.ingest_id}`);
  await expect(page.getByRole('heading', { level: 2, name: event.entry.title })).toBeVisible();
  await expect(page.getByText('Worth today')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Open deck' })).toHaveAttribute('href', new RegExp(`deck=${event.entry.deck_slug}`));
  const first = event.lines[0].printing.name;
  await page.getByRole('button', { name: `Inspect ${first}` }).first().click();
  await expect(page.getByRole('dialog', { name: first })).toBeVisible();
});

test('marks belong to the open entry; the sheet header copies them; an order has none', async ({ page }) => {
  await mockHistory(page);
  const other = history.entries.find((x) => x.ingest_id === 538)!;
  await page.route('**/api/history/538', (r) => r.fulfill({ json: { entry: { ...other, ledgered: true }, lines: event.lines } }));
  await page.goto(`/collection/history?entry=${event.entry.ingest_id}`);
  const first = event.lines[0].printing.name;
  await expect(page.getByRole('button', { name: 'Mark cards to copy them as a list' })).toBeVisible();
  await page.getByRole('button', { name: `Mark ${first}` }).first().click();
  await expect(page.getByRole('button', { name: 'Copy 1 marked card as a list' })).toBeVisible();
  await page.goto('/collection/history?entry=538');
  await expect(page.getByRole('button', { name: 'Mark cards to copy them as a list' })).toBeVisible();
  await page.goto(`/collection/history?entry=${event.entry.ingest_id}`);
  await expect(page.getByRole('button', { name: 'Copy 1 marked card as a list' })).toBeVisible();
  await page.goto('/collection/history?entry=247');
  await expect(page.getByText('Recorded before the ledger')).toBeVisible();
  await expect(page.getByRole('button', { name: /marked card|Mark cards to copy/ })).toHaveCount(0);
});

test('a pre-ledger checklist explains where its cards are counted and links there', async ({ page }) => {
  await mockHistory(page);
  await page.goto('/collection/history?entry=247');
  await expect(page.getByText('Recorded before the ledger')).toBeVisible();
  await page.getByRole('button', { name: 'Checklists before the ledger', exact: true }).click();
  await expect(page).toHaveURL(/entry=249/);
});

test('Purchase history: the tab is the title, the rail reads Find → Show, no Store orders tab without the flag', async ({ page }) => {
  await page.goto('/collection/history');
  const tabs = page.getByRole('navigation', { name: 'Collection views' });
  await expect(tabs.getByRole('link', { name: 'Purchase history' })).toHaveAttribute('aria-current', 'page');
  await expect(tabs.getByRole('link', { name: 'Store orders' })).toHaveCount(0);
  await expect(page.getByRole('heading', { level: 1, name: 'Purchase history' })).toHaveClass(/sr-only/);
  await expect(page.getByRole('heading', { level: 2 }).first()).toHaveText('Find');
});

test.describe('revert this import', () => {
  const line = event.lines[0];
  const entry = { ...event.entry, ingest_id: 900, method: 'import-block', kind: 'singles', title: 'Added a deck’s cards', detail: 'Goblins', product: null, set_code: null, deck_slug: null, copies_in: 2, held: 2, printings: 1, revertible: true, reverted_by: null, reverts: null };
  const plan = (over: Record<string, unknown> = {}) => ({
    ingest_id: 900, ok: true, reason: null, message: null, copies_removed: 2, copies_restored: 0, reverted_by: null,
    lines: [{ printing: line.printing, finish: 'nonfoil', remove: 2, restore: 0, held: 2, owned: 3, pledged: 0, blocker: null, pledged_to: [] }],
    decks: [{ slug: 'goblins', name: 'Goblins', built: false, pledged: 0 }],
    ...over,
  });

  async function setup(page: Parameters<typeof mockApi>[0], revertPlan: ReturnType<typeof plan>) {
    let reverted = false;
    const current = () => (reverted ? { ...entry, revertible: false, reverted_by: 901, held: 0 } : entry);
    await mockApi(page, {
      '/api/history/900/revert': () => ({ json: revertPlan }),
      '/api/history/900': () => ({ json: { entry: current(), lines: [{ ...line, copies_in: 2, held: reverted ? 0 : 2 }] } }),
      '/api/history/': (url) => ({ json: { entry: history.entries.find((e) => e.ingest_id === Number(url.pathname.split('/').pop())) ?? event.entry, lines: [] } }),
      '/api/history': () => ({ json: { ...history, entries: [current(), ...history.entries] } }),
    });
    await page.route('**/api/history/900/revert', (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      reverted = true;
      return route.fulfill({ json: { revert_ingest_id: 901, summary: 'Reverted: removed 2 copies, deleted 1 decklist', plan: revertPlan } });
    });
  }

  test('confirm lists exactly what leaves, then the entry reads reverted', async ({ page }) => {
    await setup(page, plan());
    await page.goto('/collection/history?entry=900');
    await page.getByRole('button', { name: 'Revert this import' }).click();
    const dialog = page.getByRole('alertdialog', { name: 'Revert this import?' });
    await expect(dialog.getByText('This removes 2 copies (1 printing) from your collection and deletes the decklist Goblins it saved.')).toBeVisible();
    await expect(dialog.getByRole('list', { name: 'Cards' }).getByRole('listitem')).toContainText([`${line.printing.name}`]);
    await dialog.getByRole('button', { name: 'Remove 2 copies' }).click();
    await expect(dialog).toBeHidden();
    await expect(page.getByRole('status').filter({ hasText: 'Reverted: removed 2 copies, deleted 1 decklist' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'See the revert' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Revert this import' })).toHaveCount(0);
  });

  test('blocked: says why, names the deck holding the copies, nothing to confirm', async ({ page }) => {
    await setup(page, plan({
      ok: false, reason: 'lines_blocked', message: '1 of its cards can’t be taken back out: copies were removed since or are in a built deck. Free them first, then revert.',
      lines: [{ printing: line.printing, finish: 'nonfoil', remove: 2, restore: 0, held: 2, owned: 2, pledged: 1, blocker: 'pledged', pledged_to: ['Party Time'] }],
    }));
    await page.goto('/collection/history?entry=900');
    await page.getByRole('button', { name: 'Revert this import' }).click();
    const dialog = page.getByRole('alertdialog', { name: 'Can’t revert this import yet' });
    await expect(dialog.getByText('1 copy is in Party Time — break that deck down first.')).toBeVisible();
    await expect(dialog.getByRole('button', { name: 'Remove 2 copies' })).toBeDisabled();
  });

  test('entries that can’t be reverted offer no revert', async ({ page }) => {
    await mockHistory(page);
    await page.goto(`/collection/history?entry=${event.entry.ingest_id}`);
    await expect(page.getByRole('heading', { level: 2, name: event.entry.title })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Revert this import' })).toHaveCount(0);
  });
});
