// Hosted members can't start catalog-wide jobs (JobSpec scope `catalog`, /api/features `jobs`):
// where those buttons would be, the app says an admin fetches it — and never submits.
import { expect, fixtures, test } from './support';

const NOTE = 'Only an admin can fetch this on this server. You see what it has already fetched.';
const DENIED = { 'edhrec.sync_bulk': false, 'scryfall.sync_tags': false, 'edhrec.rankings': false, 'art.lookup': false };

test.beforeEach(async ({ page }) => {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { cart_check: false }, jobs: DENIED } }));
});

test('the Jobs page offers neither catalog job to a member', async ({ page }) => {
  let posted = false;
  await page.route('**/api/jobs/*', (r) => { posted = true; return r.fulfill({ status: 403, json: { detail: 'no', code: 'jobs.admin_only' } }); });
  await page.goto('/jobs');
  await expect(page.getByRole('button', { name: 'Start warm-up' })).toBeDisabled();
  await expect(page.getByRole('button', { name: 'Sync tags' })).toBeDisabled();
  await expect(page.getByText(NOTE)).toHaveCount(2);
  expect(posted).toBe(false);
});

test('an unread ranking says an admin fetches it, and nothing is submitted', async ({ page }) => {
  let posted = false;
  await page.route('**/api/explore/ranking?*', (r) => r.fulfill({ json: { ...fixtures.ranking, cached: false, fetched_at: null, rows: [], total: 0, pool: 0 } }));
  await page.route('**/api/jobs/edhrec.rankings', (r) => { posted = true; return r.fulfill({ status: 403, json: { detail: 'no', code: 'jobs.admin_only' } }); });
  await page.goto('/explore');
  await expect(page.getByText('Not fetched yet')).toBeVisible();
  await expect(page.getByText('No one has fetched this list on this server yet, and only an admin can.')).toBeVisible();
  expect(posted).toBe(false);
});

test('a cached ranking shows without a Refresh action for a member', async ({ page }) => {
  await page.goto('/explore');
  await expect(page.getByRole('heading', { level: 1, name: fixtures.ranking.title })).toBeAttached();
  await expect(page.getByRole('button', { name: 'Open results in EDHREC' }).or(page.getByRole('link', { name: /Open results in EDHREC/ }))).toBeVisible();
  await expect(page.getByRole('button', { name: 'Refresh' })).toHaveCount(0);
});
