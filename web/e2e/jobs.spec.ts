import { expect, test } from './support';

test('job runner: submit → live progress over SSE → result', async ({ page }) => {
  const sse = [
    ['status', { status: 'queued' }], ['status', { status: 'running' }],
    ['progress', { done: 1, total: 2, message: 'Checking A…', level: 'info' }],
    ['progress', { done: 2, total: 2, message: 'B — cmd+card', level: 'info' }],
    ['result', { summary: '2 cards · 0 already cached · 2 synced (1 commanders) · 0 failed', artifacts: [] }],
    ['status', { status: 'succeeded' }],
  ].map(([e, d], i) => `event: ${e}\ndata: ${JSON.stringify(d)}\nid: ${i + 1}\n\n`).join('');
  await page.route('**/api/jobs/edhrec.sync_bulk', (r) => r.fulfill({ status: 202, json: { id: 'job1', name: 'edhrec.sync_bulk', title: 'Warm EDHREC cache', inputs: {}, status: 'queued', created_at: '2026-01-01T00:00:00+00:00', started_at: null, finished_at: null, progress: null, summary: null, artifacts: [], error: null } }));
  await page.route('**/api/jobs/job1/events', (r) => r.fulfill({ status: 200, contentType: 'text/event-stream', body: sse }));
  await page.goto('/jobs');
  await page.getByRole('searchbox', { name: 'Set families' }).fill('fin');
  await page.getByRole('button', { name: 'Start warm-up' }).click();
  await expect(page.getByText('2 cards · 0 already cached')).toBeVisible();
  await expect(page.getByText('Succeeded')).toBeVisible();
  await expect(page.getByRole('progressbar', { name: 'Job progress' })).toHaveAttribute('aria-valuenow', '2');
});

test('job form validates before submitting', async ({ page }) => {
  await page.goto('/jobs');
  await page.getByRole('button', { name: 'Start warm-up' }).click();
  await expect(page.getByRole('alert')).toContainText('Enter at least one set-family code');
});
