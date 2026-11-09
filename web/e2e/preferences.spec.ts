import { COLLECTION_URL, expect, mockApi, test } from './support';

const variant = (value: string, def = 'hide') => ({
  key: 'variant_prints', title: 'Variant prints', about: 'Alternate printings of the same card.', kind: 'choice',
  choices: [{ value: 'hide', label: 'Leave out' }, { value: 'show', label: 'Include' }], value, default: def, changed: value !== def,
});
const byFamily = (value: string) => ({
  key: 'by_family', title: 'Customize by family', about: "Also set what each family's rules do.", kind: 'choice',
  choices: [{ value: 'off', label: 'Print kinds only' }, { value: 'on', label: 'Also by family' }], value, default: 'off', changed: value !== 'off',
});
const KINDS = [['white_border', 'White border'], ['serialized', 'Serialized']] as const;
const kinds = (states: Record<string, string | null> = {}) => ({
  kinds: KINDS.map(([key, label]) => ({ key, label, state: states[key] ?? null, effective: states[key] ?? 'hide' })),
});
const KINDS_PATH = '/api/preferences/collection/variant-kinds';
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
  await mockApi(page, {
    '/api/preferences/collection': (url) => ({ json: url.pathname === KINDS_PATH ? kinds() : { prefs: [setTypes(value)] } }),
  });
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
    '/api/preferences/collection': (url) => ({
      json: url.pathname === KINDS_PATH ? kinds() : { prefs: [variant(state.variant), rarities(state.rarities)] },
    }),
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

  await settings.getByRole('radiogroup', { name: 'Variant prints' }).getByRole('radio', { name: 'Include' }).click();
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

test('preferences: a kind overrides the group (Group sends null)', async ({ page }) => {
  let states: Record<string, string | null> = {};
  const puts: { url: string; body: unknown }[] = [];
  await mockApi(page, {
    '/api/preferences/collection': (url) => ({
      json: url.pathname === KINDS_PATH ? kinds(states) : { prefs: [variant('hide'), byFamily('off')] },
    }),
  });
  await page.route('**/api/preferences/collection/variant-kinds/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { state: string | null };
    puts.push({ url: new URL(r.request().url()).pathname, body });
    states = { ...states, [new URL(r.request().url()).pathname.split('/').pop()!]: body.state };
    return r.fulfill({ json: kinds(states) });
  });
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Settings' }).click();
  const settings = page.getByRole('dialog', { name: 'Settings' });
  // By-family is off: no family picker.
  await expect(settings.getByRole('button', { name: /Choose a family/ })).toHaveCount(0);
  const row = settings.getByRole('radiogroup', { name: 'Serialized' });
  await expect(row.getByRole('radio', { name: 'Group' })).toBeChecked();
  await row.getByRole('radio', { name: 'Include' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ url: `${KINDS_PATH}/serialized`, body: { state: 'show' } });
  await expect(row.getByRole('radio', { name: 'Include' })).toBeChecked();
  await row.getByRole('radio', { name: 'Group' }).click();
  await expect.poll(() => puts.length).toBe(2);
  expect(puts[1].body).toEqual({ state: null });
});

test('preferences: family rules — All rules, then a rule on its own, Group goes back', async ({ page }) => {
  const rule = (id: string, description: string, def: string, note: string | null, also = 0) => ({
    id, description, note, default: def, prints: 10, owned: 2, also_hidden: also,
    state: pins[id] ?? null,
    effective: pins[id] ?? allRules ?? def,
    source: pins[id] ? 'rule' : allRules ? 'family' : 'shipped',
    changed: Boolean(pins[id]),
  });
  let allRules: string | null = null;
  let pins: Record<string, string | null> = {};
  const rules = () => ({
    code: 'fin', all_rules: allRules, by_family: true,
    rules: [rule('a', 'Active hide rule', 'hide', null), rule('b', 'Proposed count rule', 'count', 'Proposed from the set doc.', 80)],
  });
  const puts: { url: string; body: unknown }[] = [];
  const prefix = '/api/preferences/collection';
  await mockApi(page, {
    [prefix]: (url) => {
      const path = url.pathname.slice(prefix.length);
      if (path === '/families') return { json: { families: [{ code: 'fin', name: 'Final Fantasy', rules: 2, changed: 0 }, { code: 'ltr', name: 'Lord of the Rings', rules: 1, changed: 0 }] } };
      if (path === '/families/fin') return { json: rules() };
      if (path === '/variant-kinds') return { json: kinds() };
      return { json: { prefs: [variant('hide'), byFamily('on')] } };
    },
  });
  await page.route('**/api/preferences/collection/families/fin/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { state: string | null };
    const url = new URL(r.request().url()).pathname;
    puts.push({ url, body });
    if (url.endsWith('/all')) allRules = body.state;
    return r.fulfill({ json: rules() });
  });
  await page.route('**/api/preferences/collection/families/fin/rules/*', (r) => {
    if (r.request().method() !== 'PUT') return r.fallback();
    const body = r.request().postDataJSON() as { state: string | null };
    const url = new URL(r.request().url()).pathname;
    puts.push({ url, body });
    pins = { ...pins, [url.split('/').pop()!]: body.state };
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
  await expect(settings.getByText('Now: Count (shipped) · 80 hidden by Variant prints')).toBeVisible();

  await settings.getByText('Why').click();
  await expect(settings.getByText('Proposed from the set doc.')).toBeVisible();

  // All rules sets the family; Shipped sends null.
  const all = settings.getByRole('radiogroup', { name: 'All rules in this family' });
  await expect(all.getByRole('radio', { name: 'Shipped' })).toBeChecked();
  await all.getByRole('radio', { name: 'Chase' }).click();
  await expect.poll(() => puts.length).toBe(1);
  expect(puts[0]).toEqual({ url: `${prefix}/families/fin/all`, body: { state: 'chase' } });
  await expect(settings.getByText('Now: Chase (from All rules)').first()).toBeVisible();

  // One rule on its own beats All rules; Group goes back to following it.
  const row = settings.getByRole('radiogroup', { name: 'Proposed count rule' });
  await row.getByRole('radio', { name: 'Hide' }).click();
  await expect.poll(() => puts.length).toBe(2);
  expect(puts[1]).toEqual({ url: `${prefix}/families/fin/rules/b`, body: { state: 'hide' } });
  await expect(settings).toContainText('Now: Hide ·');
  await row.getByRole('radio', { name: 'Group' }).click();
  await expect.poll(() => puts.length).toBe(3);
  expect((puts[2] as { body: unknown }).body).toEqual({ state: null });
  await expect(row.getByRole('radio', { name: 'Group' })).toBeChecked();
  await expect(settings.getByRole('button', { name: /Reset Proposed/ })).toHaveCount(0);
});
