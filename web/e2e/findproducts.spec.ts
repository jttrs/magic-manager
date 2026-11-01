import { expect, test } from './support';

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

  await page.goto('/collection/history');
  await page.getByRole('toolbar', { name: 'Purchase history actions' }).getByRole('button', { name: 'Find products in your cards' }).click();
  const dialog = page.getByRole('dialog', { name: 'Find products in your cards' });
  await expect(dialog.getByText('Your cards complete · 2')).toBeVisible();
  await expect(dialog).toContainText('its shared cards went to Crack the Plates');
  await dialog.getByRole('checkbox', { name: /Treasures of Smaug/ }).uncheck();
  await dialog.getByRole('button', { name: 'Record 1 product' }).click();
  await expect(dialog).toContainText('Recorded 1 product. 6 cards now show where they came from');
  expect(applied).toEqual({ expect: ['A_HOB'], picks: [] });
  expect(await page.evaluate(() => localStorage.getItem('mm.trueup.notMine'))).toBe('["B_HOB"]');
});

const open = async (page: import('@playwright/test').Page) => {
  await page.goto('/collection/history');
  await page.getByRole('toolbar', { name: 'Purchase history actions' }).getByRole('button', { name: 'Find products in your cards' }).click();
  return page.getByRole('dialog', { name: 'Find products in your cards' });
};

test('find products: unreadable lists are named, not reported as "no products"', async ({ page }) => {
  await page.route('**/api/jobs/trueup.scan', (r) => r.fulfill({ status: 202, json: job('s1', 'trueup.scan') }));
  await page.route('**/api/jobs/s1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [], conflicts: [], unread: [{ ref: 'set:hob', name: 'HOB products', error: 'offline' }], applied: false, registered: 0, reattributed: 0 }) }));
  const dialog = await open(page);
  await expect(dialog.getByRole('alert')).toContainText('1 product list couldn’t be read, so its products weren’t checked: HOB products.');
  await expect(dialog).not.toContainText('No products found');
});

test('find products: unchecking then cancelling still remembers not-mine', async ({ page }) => {
  await page.route('**/api/jobs/trueup.scan', (r) => r.fulfill({ status: 202, json: job('s1', 'trueup.scan') }));
  await page.route('**/api/jobs/s1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [product('A_HOB', 'Crack the Plates')], conflicts: [], applied: false, registered: 0, reattributed: 0 }) }));
  const dialog = await open(page);
  await dialog.getByRole('checkbox', { name: /Crack the Plates/ }).uncheck();
  await expect(dialog.getByRole('button', { name: 'Record products' })).toBeDisabled();
  await dialog.getByRole('button', { name: 'Cancel' }).click();
  await expect(dialog).toBeHidden();
  expect(await page.evaluate(() => localStorage.getItem('mm.trueup.notMine'))).toBe('["A_HOB"]');
});

test('find products: the latest "I opened this one" is sent last', async ({ page }) => {
  const scans: { picks: string[] }[] = [];
  await page.route('**/api/jobs/trueup.scan', (r) => { scans.push(r.request().postDataJSON()); return r.fulfill({ status: 202, json: job(`s${scans.length}`, 'trueup.scan') }); });
  await page.route('**/api/jobs/s*/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [], conflicts: [{ ...product('A_HOB', 'Alpha'), lost_to: ['Zed'] }, { ...product('B_HOB', 'Beta'), lost_to: ['Zed'] }], applied: false, registered: 0, reattributed: 0 }) }));
  const dialog = await open(page);
  const pick = (name: string) => dialog.getByRole('listitem').filter({ hasText: name }).getByRole('button', { name: 'I opened this one' }).click();
  await pick('Beta');
  await expect.poll(() => scans.length).toBe(2);
  await pick('Alpha');
  await expect.poll(() => scans.length).toBe(3);
  await pick('Beta');
  await expect.poll(() => scans.at(-1)?.picks).toEqual(['A_HOB', 'B_HOB']);
});

test('find products: one record per click, Escape waits, a failed record can be cancelled', async ({ page }) => {
  let applies = 0;
  let release: () => void = () => {};
  const held = new Promise<void>((res) => { release = res; });
  await page.route('**/api/jobs/trueup.scan', (r) => r.fulfill({ status: 202, json: job('s1', 'trueup.scan') }));
  await page.route('**/api/jobs/s1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse({ ready: [product('A_HOB', 'Crack the Plates')], conflicts: [], applied: false, registered: 0, reattributed: 0 }) }));
  await page.route('**/api/jobs/trueup.apply', async (r) => { applies += 1; await held; return r.fulfill({ status: 202, json: job('a1', 'trueup.apply') }); });
  await page.route('**/api/jobs/a1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: [
    ['status', { status: 'running' }], ['error', { error: 'Your cards changed since the scan — scan again and review the list.' }], ['status', { status: 'failed' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('') }));
  const dialog = await open(page);
  const record = dialog.getByRole('button', { name: 'Record 1 product' });
  await record.dblclick();
  await expect(record).toBeDisabled();
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeDisabled();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeVisible();
  release();
  await expect(dialog.getByRole('alert')).toContainText('Your cards changed since the scan');
  expect(applies).toBe(1);
  await expect(dialog.getByRole('button', { name: 'Cancel' })).toBeEnabled();
  await page.keyboard.press('Escape');
  await expect(dialog).toBeHidden();
});
