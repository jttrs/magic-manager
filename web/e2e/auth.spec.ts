import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, mockApi, test } from './support';

const INVITE = 'uXzOwwvx9K3YGKPD_qLZ_GK0iABKv9ABsnE31c4X58E';
const PROVIDERS = [
  { name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' },
  { name: 'google', title: 'Google', login_url: '/api/auth/login/google' },
];
const OWNER = { id: 'abcdefgh23456789', display_name: 'The Owner', email: 'owner@example.com', is_admin: true };

async function hosted(page: Page, signedIn: boolean) {
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: {}, mode: 'hosted' } }),
    '/api/auth/me': () => ({ json: { user: signedIn ? OWNER : null, csrf_token: signedIn ? 'csrf-1' : null, providers: PROVIDERS, profiles_open: false } }),
  });
}

test('hosted, signed out: the sign-in sheet carries the invite and hides the app', async ({ page }) => {
  await hosted(page, false);
  await page.goto(`/decks?invite=${INVITE}`);
  await expect(page.getByRole('heading', { name: 'magic-manager', level: 1 })).toBeVisible();
  await expect(page.getByText('You’re invited.')).toBeVisible();
  await expect(page.getByRole('navigation', { name: 'Primary' })).toHaveCount(0);
  await expect(page.getByRole('link', { name: 'Continue with Discord' }))
    .toHaveAttribute('href', `/api/auth/login/discord?invite=${INVITE}&next=%2Fdecks`);
  await expect(page.getByRole('link', { name: 'Continue with Google' })).toBeVisible();
  // the invite leaves the address bar once read
  await expect(page).toHaveURL(/\/decks$/);
});

test('hosted, a refused sign-in says why in plain words', async ({ page }) => {
  await hosted(page, false);
  await page.goto('/?auth_error=profiles_soon');
  await expect(page.getByRole('alert')).toHaveText('Profiles open soon — for now only the admin can sign in.');
  await expect(page.getByText('Invite-only.')).toBeVisible();
});

test('hosted, signed in: account mark, CSRF on writes, sign out', async ({ page }) => {
  await hosted(page, true);
  const writes: Record<string, string | undefined>[] = [];
  await page.route('**/api/auth/logout', (r) => {
    writes.push(r.request().headers());
    return r.fulfill({ status: 204, body: '' });
  });
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await page.getByRole('button', { name: 'Signed in as The Owner' }).click();
  const account = page.getByRole('dialog', { name: 'Your account' });
  await expect(account).toContainText('owner@example.com');
  await expect(account).toContainText('Admin');
  await account.getByRole('button', { name: 'Sign out' }).click();
  await expect.poll(() => writes.length).toBe(1);
  expect(writes[0]['x-csrf-token']).toBe('csrf-1');
});

test('local mode: no account mark, no sign-in', async ({ page }) => {
  await page.goto(COLLECTION_URL);
  await expect(page.getByRole('navigation', { name: 'Primary' })).toBeVisible();
  await expect(page.getByRole('button', { name: /Signed in as/ })).toHaveCount(0);
});
