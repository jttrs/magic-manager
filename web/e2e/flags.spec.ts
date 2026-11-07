import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, mockApi, test } from './support';

const row = (over: Record<string, unknown> = {}) => ({
  name: 'deals', title: 'Deals', about: 'Watch store prices and read store tabs.', kind: 'release', default: false,
  everyone: null, pinned_by_env: false, mine: null, effective: false, source: 'default', changed_at: null, changed_by: null, ...over,
});
const OWNER = { id: 'abcdefgh23456789', display_name: 'The Owner', email: 'owner@example.com', is_admin: true };
const MEMBER = { ...OWNER, id: 'mmmmmmmmmmmmmmmm', display_name: 'Friend', is_admin: false };
const PROVIDERS = [{ name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' }];

async function setup(page: Page, opts: { rows?: unknown[]; perUser?: boolean; hosted?: boolean; admin?: boolean } = {}) {
  const { rows = [row()], perUser = false, hosted = false, admin = true } = opts;
  const counts = { features: 0 };
  const puts: { url: string; body: unknown; csrf?: string }[] = [];
  await mockApi(page, {
    '/api/features': () => {
      counts.features += 1;
      return { json: { flags: {}, mode: hosted ? 'hosted' : 'local', flag_admin: admin, owner_paths: {} } };
    },
    '/api/auth/me': () => ({ json: { user: admin ? OWNER : MEMBER, csrf_token: 'csrf-1', providers: PROVIDERS, profiles_open: true } }),
    '/api/flags': () => ({ json: { flags: rows, per_user: perUser } }),
  });
  // Registered after mockApi, so it wins for PUTs.
  await page.route('**/api/flags/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { scope: string; value: boolean | null };
    puts.push({ url: r.request().url(), body, csrf: r.request().headers()['x-csrf-token'] });
    const next = body.scope === 'everyone' ? row({ everyone: body.value, effective: body.value ?? false, source: 'everyone', changed_at: new Date().toISOString(), changed_by: 'The Owner' }) : row({ mine: body.value, effective: body.value ?? false, source: 'user' });
    return r.fulfill({ json: next });
  });
  return { counts, puts };
}

test('flags: toggle a feature for everyone, and the features are re-read', async ({ page }) => {
  const { counts, puts } = await setup(page);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Feature flags' }).click();
  const list = page.getByRole('list', { name: 'Flags' });
  await expect(list).toContainText('Deals');
  await expect(list).toContainText('Watch store prices and read store tabs.');
  await expect(page.getByText('Just me')).toHaveCount(0);
  const before = counts.features;
  await list.getByRole('switch', { name: 'Deals for everyone' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].url).toMatch(/\/api\/flags\/deals$/);
  expect(puts[0].body).toEqual({ scope: 'everyone', value: true });
  await expect.poll(() => counts.features).toBeGreaterThan(before);
  await expect(list).toContainText('On · Set for everyone by The Owner');
  await expect(list.getByRole('button', { name: 'Reset Deals to its default' })).toBeVisible();
});

test('flags: a value pinned by the environment cannot be changed', async ({ page }) => {
  await setup(page, { rows: [row({ pinned_by_env: true, effective: true, source: 'env' })] });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Feature flags' }).click();
  await expect(page.getByRole('switch', { name: 'Deals for everyone' })).toBeDisabled();
  await expect(page.getByText('Pinned by environment').first()).toBeVisible();
});

test('flags: a hosted member has no picker', async ({ page }) => {
  await setup(page, { hosted: true, admin: false });
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('button', { name: 'Signed in as Friend' })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Feature flags' })).toHaveCount(0);
});

test('flags: a hosted admin can set a flag just for themselves', async ({ page }) => {
  const { puts } = await setup(page, { hosted: true, perUser: true });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Feature flags' }).click();
  const list = page.getByRole('list', { name: 'Flags' });
  await expect(list.getByText('Just me')).toBeVisible();
  await list.getByRole('radio', { name: 'On' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].body).toEqual({ scope: 'me', value: true });
  expect(puts[0].csrf).toBe('csrf-1');
});
