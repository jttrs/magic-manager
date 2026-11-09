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

const SET_TYPES = ['expansion', 'commander', 'masterpiece', 'promo', 'eternal', 'masters'];
const setTypes = (value: string[]) => ({
  key: 'set_types', title: 'Set types in a family', about: 'Which kinds of related sets count.', kind: 'multi',
  choices: SET_TYPES.map((v) => ({ value: v, label: v[0].toUpperCase() + v.slice(1) })),
  value, default: SET_TYPES.slice(0, 5), changed: value.join() !== SET_TYPES.slice(0, 5).join(),
});

test('preferences: more than 5 options render as checkboxes, saved in choices order', async ({ page }) => {
  let value = SET_TYPES.slice(0, 5);
  const puts: unknown[] = [];
  await mockApi(page, { '/api/preferences/collection': () => ({ json: { prefs: [setTypes(value)] } }) });
  await page.route('**/api/preferences/collection/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { value: string[] | null };
    puts.push(body);
    value = body.value ?? SET_TYPES.slice(0, 5);
    return r.fulfill({ json: { prefs: [setTypes(value)] } });
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await expect(settings.getByRole('button', { name: 'Masters' })).toHaveCount(0);
  await settings.getByRole('checkbox', { name: 'Masters' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ value: [...SET_TYPES.slice(0, 5), 'masters'] });
  await expect(settings.getByRole('checkbox', { name: 'Masters' })).toBeChecked();
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

test('preferences: family rules — pick a family, set a proposed rule, reset it', async ({ page }) => {
  const rule = (id: string, description: string, def: string, state: string, note: string | null) => ({
    id, description, note, default: def, state, changed: state !== def, prints: 10, owned: 2,
  });
  let proposed = 'count';
  const rules = () => ({
    code: 'fin',
    rules: [rule('a', 'Active hide rule', 'hide', 'hide', null), rule('b', 'Proposed count rule', 'count', proposed, 'Proposed from the set doc.')],
  });
  const puts: unknown[] = [];
  const prefix = '/api/preferences/collection';
  await mockApi(page, {
    [prefix]: (url) => {
      const path = url.pathname.slice(prefix.length);
      if (path === '/families') return { json: { families: [{ code: 'fin', name: 'Final Fantasy', rules: 2, changed: 0 }, { code: 'ltr', name: 'Lord of the Rings', rules: 1, changed: 0 }] } };
      if (path === '/families/fin') return { json: rules() };
      return { json: { prefs: [variant('hide')] } };
    },
  });
  await page.route('**/api/preferences/collection/families/fin/rules/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { state: string | null };
    puts.push({ url: new URL(r.request().url()).pathname, body });
    proposed = body.state ?? 'count';
    return r.fulfill({ json: rules() });
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  await settings.getByRole('button', { name: /Choose a family/ }).click();
  await page.getByRole('combobox', { name: 'Filter families' }).fill('final');
  await page.getByRole('option', { name: /Final Fantasy/ }).click();
  await expect(settings.getByText('Proposed count rule')).toBeVisible();
  await expect(settings.getByText('10 prints · 2 you own').first()).toBeVisible();

  await settings.getByText('Why').click();
  await expect(settings.getByText('Proposed from the set doc.')).toBeVisible();

  const row = settings.getByRole('radiogroup', { name: 'Proposed count rule' });
  await row.getByRole('radio', { name: 'Hide' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ url: '/api/preferences/collection/families/fin/rules/b', body: { state: 'hide' } });
  const reset = settings.getByRole('button', { name: 'Reset Proposed count rule to its default' });
  await expect(reset).toBeVisible();
  await reset.click();
  await expect.poll(() => puts.length).toBe(2);
  expect((puts[1] as { body: unknown }).body).toEqual({ state: null });
  await expect(reset).toHaveCount(0);
});
