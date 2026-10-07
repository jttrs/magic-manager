import summary from './fixtures/analytics-summary.json' with { type: 'json' };
import { expect, mockApi, test } from './support';

const catalog = [
  { name: 'client.error', version: 1, category: 'error', source: 'client', owner: 'web', purpose: 'Uncaught browser errors by view and error type (never the message).', props: [] },
  { name: 'page.viewed', version: 1, category: 'usage', source: 'client', owner: 'web', purpose: 'Which views are used, on a narrow (phone) or wide (desktop) screen.', props: [] },
];

test('dashboard: errors first, usage beside, trace a ref', async ({ page }) => {
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { analytics: true } } }),
    '/api/analytics/summary': () => ({ json: summary }),
    '/api/analytics/trace/': () => ({ json: [{ event_id: 'e1', name: 'job.failed', ts: '2026-10-07T18:02:00.000+00:00', request_id: '3f9a12c0aa11bb22cc33dd44ee55ff66', session_id: null, category: 'error', props: { job: 'edhrec.sync_bulk', code: 'edhrec_error' } }] }),
  });
  await page.goto('/analytics?days=7');
  await expect(page.getByRole('heading', { name: 'Analytics', level: 1 })).toBeVisible();
  await expect(page.getByLabel('Totals').getByRole('definition').first()).toHaveText('9');
  await expect(page.getByRole('list', { name: 'Errors per day' }).getByRole('listitem')).toHaveCount(7);
  const top = page.getByRole('region', { name: /Top errors/ });
  await expect(top.getByText('PUT deck_save')).toBeVisible();
  await expect(top.getByText('409 · stale_draft')).toBeVisible();
  await expect(page.getByRole('region', { name: /Views/ }).getByText('Collection')).toBeVisible();
  await expect(page.getByRole('region', { name: /Collection → buy-list/ })).toContainText('25% of sessions');

  await page.getByRole('link', { name: 'Trace ref 3f9a12c0' }).click();
  await expect(page).toHaveURL(/ref=3f9a12c0/);
  await expect(page.getByRole('region', { name: /Ref 3f9a12c0/ })).toContainText('code=edhrec_error');

  await page.getByRole('searchbox', { name: 'Ref' }).fill('nope');
  await page.getByRole('button', { name: 'Find' }).click();
  await expect(page.getByRole('alert')).toContainText('A ref is 6–32');
});

test('dashboard is off without the flag', async ({ page }) => {
  await page.goto('/analytics');
  await expect(page.getByText('Analytics is off on this machine')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Analytics' })).toHaveCount(0);
});

test('privacy: switches save, delete my data, catalog listed', async ({ page }) => {
  const puts: unknown[] = [];
  await mockApi(page, {
    '/api/analytics/catalog': () => ({ json: catalog }),
    '/api/analytics/my-data': () => ({ json: { deleted: 12 } }),
  });
  await page.route('**/api/analytics/consent', async (r) => {
    if (r.request().method() === 'PUT') {
      puts.push(r.request().postDataJSON());
      return r.fulfill({ json: { errors: true, usage: false, asked: true, mode: 'local', disabled: false } });
    }
    return r.fulfill({ json: { errors: true, usage: true, asked: true, mode: 'local', disabled: false } });
  });
  await page.goto('/collection');
  await page.getByRole('button', { name: /^Privacy/ }).click();
  const dialog = page.getByRole('dialog', { name: 'Privacy' });
  await expect(dialog.getByRole('switch', { name: 'Usage analytics' })).toBeChecked();
  await dialog.getByRole('switch', { name: 'Usage analytics' }).click();
  await expect(dialog.getByRole('switch', { name: 'Usage analytics' })).not.toBeChecked();
  expect(puts).toEqual([{ usage: false }]);
  await dialog.getByText('What’s recorded (1)').first().click();
  await expect(dialog.getByText('Uncaught browser errors by view')).toBeVisible();
  await dialog.getByRole('button', { name: 'Delete my analytics data' }).click();
  await expect(dialog.getByText('Deleted 12 events.')).toBeVisible();
});

test('hosted: asks once before any usage is recorded', async ({ page }) => {
  await mockApi(page, {
    '/api/analytics/consent': () => ({ json: { errors: true, usage: false, asked: false, mode: 'hosted', disabled: false } }),
    '/api/analytics/catalog': () => ({ json: catalog }),
  });
  await page.goto('/collection');
  const dialog = page.getByRole('dialog', { name: 'Privacy' });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole('switch', { name: 'Usage analytics' })).not.toBeChecked();
  await expect(dialog.getByRole('switch', { name: 'Error reports' })).toBeChecked();
  await expect(dialog.getByRole('button', { name: 'Save my choice' })).toBeVisible();
});

test('tracker batches page views with the session id, never paths', async ({ page }) => {
  const batches: { body: { events: { name: string; props: Record<string, unknown> }[] }; sid: string | undefined }[] = [];
  await page.clock.install();
  await mockApi(page, {
    '/api/analytics/events': () => ({ json: { accepted: 1, rejected: [], dropped_props: 0, skipped_by_consent: 0 } }),
  });
  page.on('request', (req) => {
    if (req.url().endsWith('/api/analytics/events')) batches.push({ body: req.postDataJSON(), sid: req.headers()['x-mm-session'] });
  });
  await page.goto('/decks');
  await expect(page.getByRole('link', { name: 'Decks' })).toBeVisible();
  await page.clock.fastForward(11_000);
  await expect.poll(() => batches.length).toBeGreaterThan(0);
  const ev = batches[0].body.events[0];
  expect(ev).toMatchObject({ name: 'page.viewed', props: { view: 'decks', viewport: 'wide' } });
  expect(batches[0].sid).toMatch(/^[0-9a-f-]{36}$/);
  expect(JSON.stringify(batches)).not.toContain('/decks');
});
