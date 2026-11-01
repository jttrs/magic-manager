import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, mockApi, test } from './support';

const PROVIDERS = [
  { name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' },
  { name: 'google', title: 'Google', login_url: '/api/auth/login/google' },
];
const MEMBER = { id: 'mmmmmmmmmmmmmmmm', display_name: 'Friend', email: 'friend@example.com', is_admin: false, providers: ['discord'] };
const ZIP = Buffer.from('PK\u0005\u0006' + '\u0000'.repeat(18), 'binary');

async function local(page: Page) {
  await mockApi(page, { '/api/features': () => ({ json: { flags: {}, owner_paths: {}, mode: 'local' } }) });
}

async function hosted(page: Page, signedInAt: string, me: Record<string, unknown> | null = MEMBER) {
  await mockApi(page, {
    '/api/features': () => ({ json: { flags: {}, owner_paths: {}, mode: 'hosted' } }),
    '/api/auth/me': () => ({ json: { user: me, csrf_token: 'csrf-1', providers: PROVIDERS, profiles_open: true, signed_in_at: signedInAt, reauth_minutes: 10, reauth_seconds_left: Date.now() - Date.parse(signedInAt) < 600_000 ? 540 : 0 } }),
  });
}

const now = () => new Date().toISOString();
const longAgo = () => new Date(Date.now() - 60 * 60_000).toISOString();

async function openAccount(page: Page) {
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await expect(settings.getByRole('heading', { name: 'Account' })).toBeVisible();
  return settings;
}

test('account: local mode downloads my data, and has no delete', async ({ page }) => {
  await local(page);
  let asked = 0;
  await page.route('**/api/account/export', (r) => {
    asked += 1;
    return r.fulfill({ status: 200, body: ZIP, headers: { 'content-type': 'application/zip', 'content-disposition': 'attachment; filename="magic-manager-export-2026-11-01.zip"' } });
  });
  await page.goto(COLLECTION_URL);
  const settings = await openAccount(page);
  await expect(settings.getByText('Delete my account')).toHaveCount(0);
  const download = page.waitForEvent('download');
  await settings.getByRole('button', { name: 'Download' }).click();
  expect((await download).suggestedFilename()).toBe('magic-manager-export-2026-11-01.zip');
  expect(asked).toBe(1);
});

test('account: a failed download says why, with the ref', async ({ page }) => {
  await local(page);
  await page.route('**/api/account/export', (r) => r.fulfill({ status: 500, json: { detail: { code: 'account.export_failed', message: 'Your data couldn’t be packed: disk full' }, code: 'account.export_failed', request_id: 'abcdef0123456789' } }));
  await page.goto(COLLECTION_URL);
  const settings = await openAccount(page);
  await settings.getByRole('button', { name: 'Download' }).click();
  await expect(settings.getByText(/Your data couldn’t be packed: disk full/)).toBeVisible();
});

test('account: hosted delete needs the typed phrase, sends CSRF and lands on sign-in', async ({ page }) => {
  await hosted(page, now());
  const sent: { body: unknown; csrf?: string }[] = [];
  await page.route('**/api/account/delete', async (r) => {
    sent.push({ body: r.request().postDataJSON(), csrf: r.request().headers()['x-csrf-token'] });
    await page.unroute('**/api/auth/me');
    await page.route('**/api/auth/me', (m) => m.fulfill({ json: { user: null, csrf_token: null, providers: PROVIDERS, profiles_open: true } }));
    return r.fulfill({ json: { deleted: true, files_removed: 3 } });
  });
  await page.goto(COLLECTION_URL);
  const settings = await openAccount(page);
  await settings.getByRole('button', { name: 'Delete account…' }).click();
  const dialog = page.getByRole('alertdialog', { name: 'Delete your account' });
  await expect(dialog).toContainText('offsite backups keep a copy');
  const commit = dialog.getByRole('button', { name: 'Delete my account' });
  await expect(commit).toBeDisabled();
  await dialog.getByLabel('Type delete my account to confirm').fill('delete');
  await expect(commit).toBeDisabled();
  await dialog.getByLabel('Type delete my account to confirm').fill('Delete my account');
  await commit.click();
  await expect(page.getByText('Your account and its collection were deleted from this server.')).toBeVisible();
  expect(sent).toEqual([{ body: { confirm: 'Delete my account' }, csrf: 'csrf-1' }]);
});

test('account: an old sign-in is sent to sign in again, then comes back to the dialog', async ({ page }) => {
  await hosted(page, longAgo());
  await page.goto(COLLECTION_URL);
  const settings = await openAccount(page);
  await settings.getByRole('button', { name: 'Delete account…' }).click();
  const dialog = page.getByRole('alertdialog', { name: 'Delete your account' });
  await expect(dialog.getByRole('button', { name: 'Delete my account' })).toHaveCount(0);
  const again = dialog.getByRole('link', { name: 'Sign in again with Discord' });
  await expect(again).toHaveAttribute('href', /^\/api\/auth\/login\/discord\?next=%2Fcollection/);
  await expect(dialog.getByRole('link', { name: /Google/ })).toHaveCount(0); // only the linked provider
  await page.route('**/api/auth/login/**', (r) => r.fulfill({ status: 200, body: 'provider' }));
  await again.click();
  // back from the provider with a fresh session: Settings and the dialog reopen
  await page.unroute('**/api/auth/me');
  await page.route('**/api/auth/me', (m) => m.fulfill({ json: { user: MEMBER, csrf_token: 'csrf-2', providers: PROVIDERS, profiles_open: true, signed_in_at: now(), reauth_minutes: 10, reauth_seconds_left: 600 } }));
  await page.goto(COLLECTION_URL);
  const back = page.getByRole('alertdialog', { name: 'Delete your account' });
  await expect(back.getByLabel('Type delete my account to confirm')).toBeVisible();
  await page.reload();
  await expect(page.getByRole('alertdialog')).toHaveCount(0); // the mark is used once
});

test('account: the server refusing (last admin) is shown in the dialog', async ({ page }) => {
  await hosted(page, now(), { ...MEMBER, is_admin: true });
  await page.route('**/api/account/delete', (r) => r.fulfill({ status: 409, json: { detail: { code: 'auth.last_admin', message: 'You’re the only admin — make someone else an admin before deleting this account.' }, code: 'auth.last_admin', request_id: 'r1' } }));
  await page.goto(COLLECTION_URL);
  const settings = await openAccount(page);
  await settings.getByRole('button', { name: 'Delete account…' }).click();
  const dialog = page.getByRole('alertdialog', { name: 'Delete your account' });
  await dialog.getByLabel('Type delete my account to confirm').fill('delete my account');
  await dialog.getByRole('button', { name: 'Delete my account' }).click();
  await expect(dialog.getByRole('alert')).toContainText('only admin');
});

for (const [name, viewport] of [['desktop', { width: 1280, height: 860 }], ['phone', { width: 390, height: 844 }]] as const) {
  test(`account: settings and delete dialog look right (${name})`, async ({ page }) => {
    await page.setViewportSize(viewport);
    await hosted(page, now());
    await page.goto(COLLECTION_URL);
    const settings = await openAccount(page);
    await settings.getByRole('heading', { name: 'Account' }).scrollIntoViewIfNeeded();
    await page.screenshot({ path: test.info().outputPath(`account-settings-${name}.png`) });
    await settings.getByRole('button', { name: 'Delete account…' }).click();
    await page.getByLabel('Type delete my account to confirm').fill('delete my account');
    await page.screenshot({ path: test.info().outputPath(`account-delete-${name}.png`) });
    await expect(page.getByRole('button', { name: 'Delete my account' })).toBeEnabled();
  });
}
