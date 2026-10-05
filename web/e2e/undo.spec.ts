import { COLLECTION_URL, expect, test } from './support';

const summary = { copies: 100, printings: 80, decks: 5, built: 2, wishlist: 0, earmarks: 1 };
const info = {
  taken_at: new Date().toISOString(), reason: 'before adding cards', restorable: true,
  current: summary, snapshot: { ...summary, copies: 97 }, changes: { copies: -3, printings: 0, decks: 0, built: 0, wishlist: 0, earmarks: 0 },
};

test('no restore point → no undo icon', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('heading', { level: 1, name: 'Collection' })).toBeVisible();
  await expect(page.getByRole('button', { name: /^Restore point/ })).toHaveCount(0);
});

test('restore point: confirm shows what changes, then swaps', async ({ page }) => {
  let restored = false;
  await page.route('**/api/undo', (r) => r.fulfill({ json: info }));
  await page.route('**/api/undo/restore', (r) => { restored = true; return r.fulfill({ json: { ...info, changes: { ...info.changes, copies: 3 } } }); });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: /^Restore point · / }).click();
  const dialog = page.getByRole('alertdialog', { name: /^Restore your collection to / });
  await expect(dialog.getByRole('list', { name: 'What changes' })).toHaveText('3 fewer copies');
  await expect(dialog).toContainText('Taken before adding cards');
  await dialog.getByRole('button', { name: 'Restore' }).click();
  await expect(dialog).toBeHidden();
  expect(restored).toBe(true);
});
