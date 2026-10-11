// Add cards → Moxfield collection, and Archidekt deck links, through a stand-in
// for the companion's bridge (the readers themselves are pinned in
// companion-import-readers.spec.ts; the real extension in companion-extension.spec.ts).
import type { Page } from '@playwright/test';
import { COLLECTION_URL, expect, test } from './support';

type Answer = { ok: true; data: unknown } | { ok: false; code: string };

async function fakeCompanion(page: Page, answers: Record<string, Answer>, features: Record<string, boolean> = { cart: true, deals: false, moxfield: true, archidekt: true }) {
  await page.addInitScript(({ answers, features }) => {
    const CHANNEL = 'magic-manager/companion';
    const w = window as unknown as { __companionRequests: unknown[] };
    w.__companionRequests = [];
    const post = (m: Record<string, unknown>) => window.postMessage({ ...m, channel: CHANNEL, from: 'companion' }, location.origin);
    window.addEventListener('message', (ev) => {
      const d = ev.data;
      if (ev.source !== window || !d || d.channel !== CHANNEL || d.from !== 'app') return;
      if (d.type === 'ping') post({ type: 'hello', version: '0.4.0', features });
      if (d.type === 'request') {
        w.__companionRequests.push({ kind: d.kind, params: d.params });
        const a = answers[d.kind];
        if (!a) return;
        post({ type: 'ack', id: d.id, ok: true, status: 'awaiting_approval', summary: 'the stuff' });
        setTimeout(() => post({ type: 'result', id: d.id, kind: d.kind, ...a }), 200);
      }
    });
  }, { answers, features });
}

async function flags(page: Page) {
  await page.route('**/api/features', (r) => r.fulfill({ json: { flags: { companion: true } } }));
}

const SID = (n: number) => `00000000-0000-4000-8000-00000000000${n}`;
const LINES = [
  { quantity: 5, finish: 'nonfoil', scryfall_id: SID(1), set: 'tla', cn: '4', name: 'Aang, the Last Airbender' },
  { quantity: 1, finish: 'etched', scryfall_id: SID(2), set: 'tla', cn: '1', name: 'Aang’s Journey' },
  { quantity: 2, finish: 'nonfoil', scryfall_id: SID(3), set: 'tla', cn: '205', name: 'Abandon Attachments', proxy: true },
];
const READ = { collection: { scope: 'binder', id: 'LbwVB1hSiU2THiRQeR2QlQ', name: 'Trade Box 1', signed_in: true, total: 3, entries: 3, lines: LINES }, warnings: [] };
const PREVIEW = {
  label: 'web:moxfield binder · Trade Box 1',
  rows: [
    { scryfall_id: SID(1), finish: 'nonfoil', name: 'Aang, the Last Airbender', set: 'tla', collector_number: '4', current: 7, incoming: 5 },
    { scryfall_id: SID(2), finish: 'foil', name: 'Aang’s Journey', set: 'tla', collector_number: '1', current: 0, incoming: 1 },
  ],
  not_found: [], skipped: { proxy: 2, digital: 0 }, not_in_read: 120, already_imported_at: null, warnings: [],
};

async function openCollectionTab(page: Page) {
  await page.goto(COLLECTION_URL);
  await page.getByRole('button', { name: 'Add cards' }).click();
  await page.getByRole('tab', { name: 'Moxfield collection' }).click();
  return page.getByRole('dialog', { name: 'Add cards' });
}

test.describe('Add cards → Moxfield collection', () => {
  test('the tab is there only with the companion flag', async ({ page }) => {
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await expect(page.getByRole('tab', { name: 'Moxfield collection' })).toHaveCount(0);
  });

  test('a binder: list, read, review a diff, choose add or replace, import once', async ({ page }) => {
    await flags(page);
    await fakeCompanion(page, {
      moxfield_binders: { ok: true, data: { binders: [{ id: 'LbwVB1hSiU2THiRQeR2QlQ', name: 'Trade Box 1', cards: 3 }] } },
      moxfield_collection: { ok: true, data: READ },
    });
    let previewBody: unknown = null;
    let applyBody: Record<string, unknown> | null = null;
    await page.route('**/api/collection/import/preview', (r) => { previewBody = r.request().postDataJSON(); return r.fulfill({ json: PREVIEW }); });
    await page.route('**/api/collection/import/apply', (r) => {
      applyBody = r.request().postDataJSON();
      return r.fulfill({ json: { mode: 'replace', ingest_id: 9, added: 1, updated: 1, not_found: 0, label: PREVIEW.label } });
    });
    const d = await openCollectionTab(page);
    await d.getByRole('radio', { name: /One of your binders/ }).check();
    await d.getByRole('button', { name: 'List my binders' }).click();
    await expect(d.getByRole('combobox', { name: 'Binder' })).toHaveValue('LbwVB1hSiU2THiRQeR2QlQ');
    await d.getByRole('button', { name: 'Read from Moxfield' }).click();

    await expect(d.getByRole('heading', { name: 'Moxfield binder · Trade Box 1' })).toBeVisible();
    expect(previewBody).toEqual({ source: 'moxfield', scope: 'binder', id: 'LbwVB1hSiU2THiRQeR2QlQ', name: 'Trade Box 1', lines: LINES });
    await expect(d).toContainText('Skipped 2 proxies.');
    await expect(d).toContainText('120 printings you own aren’t in this read — left as they are.');
    // Both effects are shown before choosing; nothing imports until you choose.
    await expect(d.getByRole('radio', { name: /Add to what you own/ }).locator('xpath=ancestor::label')).toContainText('+6 copies · 1 new printing');
    await expect(d.getByRole('radio', { name: /Set your counts/ }).locator('xpath=ancestor::label')).toContainText('+1 copy · −2 copies · 1 new printing');
    await expect(d.getByRole('button', { name: /^Import/ })).toBeDisabled();

    await d.getByRole('radio', { name: /Set your counts/ }).check();
    const table = d.getByRole('table', { name: 'Cards that would change' });
    await expect(table.getByRole('row')).toHaveCount(3);
    await expect(table.getByRole('row').nth(1)).toContainText('−2');
    await d.getByRole('button', { name: 'Import · +1 copy · −2 copies · 1 new printing' }).click();
    await expect(d.getByRole('status')).toContainText('Imported: 1 new printing, 1 changed');
    expect(applyBody).toMatchObject({ mode: 'replace', force: false, scope: 'binder', name: 'Trade Box 1' });
    expect(await page.evaluate(() => (window as unknown as { __companionRequests: unknown[] }).__companionRequests)).toEqual([
      { kind: 'moxfield_binders', params: {} },
      { kind: 'moxfield_collection', params: { what: 'binder', binder: 'LbwVB1hSiU2THiRQeR2QlQ' } },
    ]);
  });

  test('adding an identical read again needs a confirmation', async ({ page }) => {
    await flags(page);
    await fakeCompanion(page, { moxfield_collection: { ok: true, data: { ...READ, collection: { ...READ.collection, scope: 'collection', id: null, name: null } } } });
    await page.route('**/api/collection/import/preview', (r) => r.fulfill({ json: { ...PREVIEW, already_imported_at: '2026-10-01 10:00:00' } }));
    const d = await openCollectionTab(page);
    await d.getByRole('button', { name: 'Read from Moxfield' }).click();
    await expect(d.getByRole('heading', { name: 'Your Moxfield collection' })).toBeVisible();
    await d.getByRole('radio', { name: /Add to what you own/ }).check();
    const go = d.getByRole('button', { name: /^Import/ });
    await expect(go).toBeDisabled();
    await d.getByRole('checkbox', { name: /imported this exact read on 2026-10-01/ }).check();
    await expect(go).toBeEnabled();
  });

  test('a shared link is read by its URL; signed out names the fix', async ({ page }) => {
    await flags(page);
    await fakeCompanion(page, { moxfield_collection: { ok: false, code: 'moxfield.signed_out' } });
    const d = await openCollectionTab(page);
    await d.getByRole('button', { name: 'Read from Moxfield' }).click();
    await expect(d.getByRole('alert')).toContainText('You aren’t signed in to Moxfield in this browser');
    await d.getByRole('radio', { name: /A shared link/ }).check();
    const read = d.getByRole('button', { name: 'Read from Moxfield' });
    await d.getByRole('textbox', { name: /collection or binder link/ }).fill('https://moxfield.com/decks/abc');
    await expect(read).toBeDisabled();
    await d.getByRole('textbox', { name: /collection or binder link/ }).fill('https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w');
    await read.click();
    await expect.poll(async () => (await page.evaluate(() => (window as unknown as { __companionRequests: { params: unknown }[] }).__companionRequests)).at(-1)).toEqual(
      { kind: 'moxfield_collection', params: { url: 'https://moxfield.com/collection/hgsItGBwRUybHyN0WZR41w' } });
  });
});

test.describe('Archidekt deck links through the companion', () => {
  const DECK = { url: 'https://archidekt.com/decks/13106730', deck: { id: 13106730, name: 'Revival Trance', owner: { username: 'me' }, cards: [
    { quantity: 1, modifier: 'Normal', categories: ['Commander'], card: { uid: SID(1), collectorNumber: '558', edition: { editioncode: 'fic' }, oracleCard: { name: 'Terra, Herald of Hope' } } },
  ] } };

  test('read in this browser (private decks too) and land in review', async ({ page }) => {
    await flags(page);
    await fakeCompanion(page, { archidekt: { ok: true, data: DECK } });
    let body: unknown = null;
    await page.route('**/api/ingest/deck-from-browser', (r) => {
      body = r.request().postDataJSON();
      return r.fulfill({ json: { format: 'deck', deck_name: 'Revival Trance', warnings: [], deck: { source: 'archidekt', id: '13106730', name: 'Revival Trance', author: 'me', cards: [] }, lines: [] } });
    });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await page.getByRole('tab', { name: 'Deck or precon' }).click();
    await page.getByRole('textbox', { name: /Archidekt/ }).fill(DECK.url);
    await expect(page.getByText('Read in this browser by the companion, so your private decks work too.', { exact: false })).toBeVisible();
    await page.getByRole('button', { name: 'Fetch deck' }).click();
    await expect(page.getByRole('heading', { name: 'Revival Trance' })).toBeVisible();
    expect(body).toEqual({ source: 'archidekt', deck: DECK.deck });
  });

  test('with Archidekt switched off in the companion, the server reads the public deck as before', async ({ page }) => {
    await flags(page);
    await fakeCompanion(page, {}, { cart: true, deals: false, moxfield: true, archidekt: false });
    await page.goto(COLLECTION_URL);
    await page.getByRole('button', { name: 'Add cards' }).click();
    await page.getByRole('tab', { name: 'Deck or precon' }).click();
    await page.getByRole('textbox', { name: /Archidekt/ }).fill(DECK.url);
    await expect(page.getByText('Read in this browser by the companion', { exact: false })).toHaveCount(0);
  });
});
