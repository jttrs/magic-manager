import { COLLECTION_URL, expect, mockApi, test } from './support';

const variant = (value: string, def = 'hide') => ({
  key: 'variant_prints', title: 'Variant prints', about: 'Alternate printings of the same card.', kind: 'choice',
  choices: [{ value: 'hide', label: 'Leave out' }, { value: 'show', label: 'Include' }], value, default: def, changed: value !== def,
});
const rarities = (value: string[]) => ({
  key: 'missing_rarities', title: 'Missing rarities', about: 'Which rarities a missing list asks for.', kind: 'multi',
  choices: [{ value: 'rare', label: 'Rares' }, { value: 'mythic', label: 'Mythics' }, { value: 'common', label: 'Commons' }],
  value, default: ['rare', 'mythic'], changed: value.length !== 2 || value.join() !== 'rare,mythic',
});

test('preferences: change, reset, and toggle a multi in choices order', async ({ page }) => {
  let state = { variant: 'hide', rarities: ['rare', 'mythic'] };
  const puts: { key: string; body: unknown }[] = [];
  await mockApi(page, {
    '/api/preferences/collection': () => ({ json: { prefs: [variant(state.variant), rarities(state.rarities)] } }),
  });
  await page.route('**/api/preferences/collection/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const key = r.request().url().split('/').pop()!;
    const body = r.request().postDataJSON() as { value: string | string[] | null };
    puts.push({ key, body });
    if (key === 'variant_prints') state = { ...state, variant: (body.value as string | null) ?? 'hide' };
    else state = { ...state, rarities: (body.value as string[] | null) ?? ['rare', 'mythic'] };
    return r.fulfill({ json: { prefs: [variant(state.variant), rarities(state.rarities)] } });
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await expect(settings.getByRole('heading', { name: 'What counts' })).toBeVisible();
  await expect(settings.getByText('Variant prints')).toBeVisible();

  await settings.getByRole('radio', { name: 'Include' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ key: 'variant_prints', body: { value: 'show' } });
  const reset = settings.getByRole('button', { name: 'Reset Variant prints to its default' });
  await expect(reset).toBeVisible();
  await reset.click();
  await expect.poll(() => puts.length).toBe(2);
  expect(puts[1].body).toEqual({ value: null });
  await expect(reset).toHaveCount(0);

  await settings.getByRole('button', { name: 'Commons' }).click();
  await expect.poll(() => puts.length).toBe(3);
  expect(puts[2]).toEqual({ key: 'missing_rarities', body: { value: ['rare', 'mythic', 'common'] } });
});
