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

test('a pre-ledger checklist explains where its cards are counted and links there', async ({ page }) => {
  await mockHistory(page);
  await page.goto('/collection/history?entry=247');
  await expect(page.getByText('Recorded before the ledger')).toBeVisible();
  await page.getByRole('button', { name: 'Checklists before the ledger', exact: true }).click();
  await expect(page).toHaveURL(/entry=249/);
});
