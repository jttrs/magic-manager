import { COLLECTION_URL, expect, test } from './support';

const product = (fileName: string, name: string) => ({ fileName, name, type: 'Box Set', code: 'HOB', release_date: '2026-08-14', recipe_qty: 6, usd: 37.37 });
const job = (id: string, name: string) => ({ id, name, title: name, inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null });
const sse = (data: unknown) => [
  ['status', { status: 'running' }],
  ['result', { summary: 'ok', artifacts: [{ kind: 'json', label: 'scan', data }] }],
  ['status', { status: 'succeeded' }],
].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');

test('find products: scan, uncheck one, record the rest', async ({ page }) => {
  let applied: { expect: string[] } | null = null;
  await page.route('**/api/jobs/trueup.scan', (r) => r.fulfill({ status: 202, json: job('s1', 'trueup.scan') }));
  await page.route('**/api/jobs/s1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [product('A_HOB', 'Crack the Plates'), product('B_HOB', 'Treasures of Smaug')], conflicts: [{ ...product('C_HOB', 'Lost One'), lost_to: ['Crack the Plates'] }], applied: false, registered: 0, reattributed: 0 }) }));
  await page.route('**/api/jobs/trueup.apply', (r) => { applied = r.request().postDataJSON(); return r.fulfill({ status: 202, json: job('a1', 'trueup.apply') }); });
  await page.route('**/api/jobs/a1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [product('A_HOB', 'Crack the Plates')], conflicts: [], applied: true, registered: 1, reattributed: 6 }) }));

  await page.goto(COLLECTION_URL);
  await page.getByRole('toolbar', { name: 'Collection actions' }).getByRole('button', { name: 'Find products in your cards' }).click();
  const dialog = page.getByRole('dialog', { name: 'Find products in your cards' });
  await expect(dialog.getByText('Your cards complete · 2')).toBeVisible();
  await expect(dialog).toContainText('its shared cards went to Crack the Plates');
  await dialog.getByRole('checkbox', { name: /Treasures of Smaug/ }).uncheck();
  await dialog.getByRole('button', { name: 'Record 1 product' }).click();
  await expect(dialog).toContainText('Recorded 1 product. 6 cards now show where they came from');
  expect(applied).toEqual({ expect: ['A_HOB'], picks: [] });
  expect(await page.evaluate(() => localStorage.getItem('mm.trueup.notMine'))).toBe('["B_HOB"]');
});
