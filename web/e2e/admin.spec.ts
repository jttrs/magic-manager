import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, mockApi, test } from './support';

const PROVIDERS = [{ name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' }];
const OWNER = { id: 'abcdefgh23456789', display_name: 'The Owner', email: 'owner@example.com', is_admin: true };
const MEMBER_ID = 'mmmmmmmmmmmmmmmm';
const PATHS = [
  { key: 'manapool.server_login', feature: 'cart_check', title: 'Read the Mana Pool cart with this server’s login' },
  { key: 'deals.mac_tabs', feature: 'deals', title: 'Read open tabs and store pages in this server’s Chrome' },
  { key: 'analytics.dashboard', feature: 'analytics', title: 'The Analytics dashboard (everyone’s activity)' },
  { key: 'decks.moxfield_server', feature: null, title: 'Read Moxfield decks with this server’s browser and Moxfield login' },
];
const flag = (name: string, about: string, owner_paths: string[] = [], override: boolean | null = null) =>
  ({ name, about, default: false, override, effective: override ?? false, owner_paths });
const flags = (deals: boolean | null = null) => [
  flag('cart_check', 'Check a store cart against the collection.', ['manapool.server_login']),
  flag('deals', 'Deals: watch store prices and read store tabs.', ['deals.mac_tabs'], deals),
  flag('companion', 'The browser companion.'),
];
const user = (over: Record<string, unknown>) => ({
  providers: ['discord'], created_at: '2026-10-01T00:00:00+00:00', last_seen_at: '2026-11-01T10:00:00+00:00',
  disabled_at: null, sessions: 1, flags: flags(), ...over,
});
const OWNER_ROW = user({ ...OWNER });
const MEMBER_ROW = user({ id: MEMBER_ID, display_name: 'Friend', email: 'friend@example.com', is_admin: false, sessions: 0 });

async function hosted(page: Page, me = OWNER, ownerPaths = true) {
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: { analytics: true, cart_check: true }, owner_paths: Object.fromEntries(PATHS.map((p) => [p.key, ownerPaths])), mode: 'hosted' } }),
    '/api/auth/me': () => ({ json: { user: me, csrf_token: 'csrf-1', providers: PROVIDERS, profiles_open: true } }),
    '/api/admin/users': () => ({ json: { users: [OWNER_ROW, MEMBER_ROW], owner_paths: PATHS } }),
  });
}

test('admin: the account mark leads to people; a flag override is sent with CSRF', async ({ page }) => {
  await hosted(page);
  const puts: { url: string; body: unknown; csrf?: string }[] = [];
  await page.route(`**/api/admin/users/${MEMBER_ID}/flags/*`, (r) => {
    puts.push({ url: r.request().url(), body: r.request().postDataJSON(), csrf: r.request().headers()['x-csrf-token'] });
    return r.fulfill({ json: { ...MEMBER_ROW, flags: flags(true) } });
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Signed in as The Owner' }).click();
  await page.getByRole('link', { name: 'People and features' }).click();
  await expect(page).toHaveURL(/\/admin$/);
  await expect(page.getByText('2 people can sign in · 1 admin')).toBeVisible();
  await page.getByRole('list', { name: 'People' }).getByRole('button', { name: /Friend/ }).click();
  const person = page.getByRole('article', { name: 'Friend' });
  await expect(person).toContainText('Signed out');
  await expect(person).toContainText('Stays owner-only for members: Read open tabs and store pages in this server’s Chrome.');
  await expect(person).toContainText('No — admins only');
  await person.getByRole('radiogroup', { name: /^Deals/ }).getByRole('radio', { name: 'On' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0].url).toMatch(/\/flags\/deals$/);
  expect(puts[0].body).toEqual({ value: true });
  expect(puts[0].csrf).toBe('csrf-1');
  await expect(person.getByText('Deals: turned on for Friend.')).toBeVisible();
  await expect(person.getByText('Deals — on')).toBeVisible();
  // the admin can't turn themselves off
  await page.getByRole('list', { name: 'People' }).getByRole('button', { name: /The Owner/ }).click();
  await expect(page.getByRole('button', { name: 'Turn off sign-in' })).toBeDisabled();
});

test('admin: an invite link is shown once and can be copied', async ({ page }) => {
  await hosted(page);
  const sent: unknown[] = [];
  await page.route('**/api/admin/invites', (r) => {
    sent.push(r.request().postDataJSON());
    return r.fulfill({ status: 201, json: { code: 'c0de-c0de-c0de-c0de', url: 'https://cards.example.com/?invite=c0de-c0de-c0de-c0de', admin: false, expires_at: '2026-11-08T12:00:00+00:00' } });
  });
  await page.goto('/admin');
  await page.getByRole('button', { name: 'Invite someone' }).click();
  const dialog = page.getByRole('dialog', { name: 'Invite someone' });
  await dialog.getByRole('radio', { name: '30 days' }).click();
  await dialog.getByRole('button', { name: 'Make invite link' }).click();
  await expect(dialog.getByText('Shown once — copy it now.')).toBeVisible();
  await expect(dialog.getByLabel('Invite link')).toHaveValue('https://cards.example.com/?invite=c0de-c0de-c0de-c0de');
  expect(sent).toEqual([{ admin: false, expires_days: 30 }]);
});

test('a member: no admin link, no admin page, owner-only parts stay hidden', async ({ page }) => {
  await hosted(page, { ...OWNER, id: MEMBER_ID, display_name: 'Friend', is_admin: false }, false);
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Signed in as Friend' }).click();
  await expect(page.getByRole('link', { name: 'People and features' })).toHaveCount(0);
  await page.goto('/admin');
  await expect(page.getByText('Only an admin can see this page')).toBeVisible();
  await page.goto('/analytics');
  await expect(page.getByText('Analytics is for admins here')).toBeVisible();
});

test('admin page: desktop and phone', async ({ page }) => {
  await hosted(page);
  await page.goto(`/admin?user=${MEMBER_ID}`);
  await expect(page.getByRole('article', { name: 'Friend' })).toBeVisible();
  await page.screenshot({ path: 'test-results/admin-desktop.png', fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(page.getByRole('article', { name: 'Friend' })).toBeVisible();
  await page.screenshot({ path: 'test-results/admin-phone.png', fullPage: true });
});
