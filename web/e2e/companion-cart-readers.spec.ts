// Pinned behaviour of the companion's TCGplayer and Card Kingdom CART readers
// (extension/src/readers/{tcgplayer,cardkingdom}-cart.js), run in real Chromium against
// guest carts saved from the live sites (tests/fixtures/companion/*-cart*.html).
// The *.expected.json goldens are fed to the server's strict models + cart.audit by
// tests/test_companion_carts.py, so reader → app → engine stays one chain.
//
// Re-pin on purpose:  UPDATE_GOLDEN=1 npm --prefix web run e2e -- companion-cart-readers
// A site changed its page? Follow .claude/skills/scrape-doctor/SKILL.md.
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, test, type Page } from '@playwright/test';

const ROOT = resolve(import.meta.dirname, '../..');
const FIX = resolve(ROOT, 'tests/fixtures/companion');
const reader = (name: string) => readFileSync(resolve(ROOT, 'extension/src/readers', name), 'utf8');
const fixture = (name: string) => readFileSync(resolve(FIX, name), 'utf8');

function golden(name: string, actual: unknown) {
  const path = resolve(FIX, name);
  if (process.env.UPDATE_GOLDEN || !existsSync(path)) writeFileSync(path, JSON.stringify(actual, null, 2) + '\n');
  expect(actual).toEqual(JSON.parse(readFileSync(path, 'utf8')));
}

type Out = { ok: boolean; code?: string; items: Record<string, unknown>[]; warnings: { code: string; row?: number; missing?: string[] }[] };

async function read(page: Page, url: string, html: string, script: string, fn: string): Promise<Out> {
  await page.unrouteAll();
  await page.route('**/*', (r) => (r.request().url() === url
    ? r.fulfill({ status: 200, contentType: 'text/html; charset=utf-8', body: html })
    : r.fulfill({ status: 404, body: '' })));
  await page.goto(url, { waitUntil: 'domcontentloaded' });
  await page.addScriptTag({ content: reader(script) });
  return page.evaluate((f) => (window as unknown as Record<string, (d: Document) => Out>)[f](document), fn);
}

const TCG = ['https://www.tcgplayer.com/cart', 'tcgplayer-cart.js', 'readTcgplayerCart'] as const;
const CK = ['https://www.cardkingdom.com/cart', 'cardkingdom-cart.js', 'readCardKingdomCart'] as const;

test.describe('TCGplayer cart reader', () => {
  test('reads every line: product id, set + number, condition, language, finish, quantity, unit price', async ({ page }) => {
    const html = fixture('tcgplayer-cart.html');
    const out = await read(page, TCG[0], html, TCG[1], TCG[2]);
    expect(out.ok).toBe(true);
    // Pinned facts a human checked against the saved page (the golden carries the rest):
    expect(out.items.map((i) => [i.kind, i.tcgplayer_product_id, i.name, i.number, i.finish, i.condition, i.language, i.quantity, i.price])).toEqual([
      ['single', 563893, 'Vengeful Bloodwitch', '76', 'nonfoil', 'NM', 'English', 2, 0.4],
      ['sealed', null, 'FINAL FANTASY - Play Booster Pack', null, 'nonfoil', null, null, 1, 8.49],
      ['single', 630864, 'Aerith Gainsborough', '4', 'nonfoil', 'NM', 'Japanese', 1, 0.16],
      ['single', 487805, 'The One Ring', '246', 'nonfoil', 'LP', 'English', 1, 108.15],
      ['single', 630864, 'Aerith Gainsborough', '4', 'nonfoil', 'NM', 'English', 1, 1.75],
      ['single', 630958, 'Ardyn, the Usurper', '315', 'foil', 'NM', 'English', 1, 5.49],
      ['single', 577866, 'Sol Ring', '94', 'nonfoil', 'NM', 'English', 1, 1.85],
      // A non-Magic line's "025/165" never leaves the reader (the server's number pattern would 422 the cart).
      ['other', 284472, 'Pikachu', null, 'nonfoil', null, null, 1, 1.85],
    ]);
    // Never the sellers, a seller's own listing title, shipping or totals.
    const sent = JSON.stringify(out);
    for (const s of ['Addicted2packz', 'ComicKungFu', 'Magical Outpost', 'TheNamesOptional', 'minimum order', 'Shipping', '$3.24']) expect(sent).not.toContain(s);
    golden('tcgplayer-cart.expected.json', out);
  });

  test('the real empty guest cart reads as empty (cart.empty), not a changed page', async ({ page }) => {
    expect(await read(page, TCG[0], fixture('tcgplayer-cart-empty.html'), TCG[1], TCG[2]))
      .toMatchObject({ ok: false, code: 'cart.empty', warnings: [{ code: 'cart.signed_out' }] });
  });

  test('a redesigned cart with no recognisable lines is cart.page_changed', async ({ page }) => {
    expect(await read(page, TCG[0], '<!doctype html><main><h1>Cart</h1><div>Sol Ring $1.00</div></main>', TCG[1], TCG[2]))
      .toMatchObject({ ok: false, code: 'cart.page_changed' });
  });

  test('a line it can’t fully read is kept and flagged', async ({ page }) => {
    const html = fixture('tcgplayer-cart.html').replace('href="/product/563893/magic--vengeful-bloodwitch"', 'href="/x"').replace('href="/product/563893/magic--vengeful-bloodwitch"', 'href="/x"');
    const out = await read(page, TCG[0], html, TCG[1], TCG[2]);
    expect(out.items[0].tcgplayer_product_id).toBeNull();
    expect(out.warnings).toContainEqual({ code: 'cart.row_unreadable', row: 1, missing: ['printing'] });
  });
});

test.describe('Card Kingdom cart reader', () => {
  test('reads every line: product id, edition, grade, finish, quantity, unit price', async ({ page }) => {
    const out = await read(page, CK[0], fixture('cardkingdom-cart.html'), CK[1], CK[2]);
    expect(out.ok).toBe(true);
    expect(out.items.map((i) => [i.kind, i.cardkingdom_product_id, i.name, i.set_name, i.number, i.finish, i.condition, i.quantity, i.price])).toEqual([
      ['single', 313555, 'Aerith Gainsborough', 'Final Fantasy', null, 'nonfoil', 'NM', 1, 4.49],
      ['single', 313885, 'Ardyn, the Usurper', 'Final Fantasy Variants Foil', '524', 'foil', 'NM', 1, 16.99],
      ['single', 26242, 'Sol Ring', '3rd Edition', null, 'nonfoil', 'VG', 1, 17.49],
      ['single', 333767, 'Sol Ring', 'Foundations Commander', null, 'nonfoil', 'NM', 2, 2.99],
      ['single', 279381, 'The One Ring', 'Promotional', null, 'foil', 'EX', 1, 125.99],
      ['sealed', null, 'The Hobbit Gift Bundle', null, null, 'nonfoil', null, 1, 119.99],
    ]);
    // Never the request token, line-item ids or the cart total.
    const sent = JSON.stringify(out);
    for (const s of ['_token', 'lineitem', '874623', '170.94', 'Subtotal']) expect(sent).not.toContain(s);
    golden('cardkingdom-cart.expected.json', out);
  });

  test('the real empty guest cart reads as empty (cart.empty)', async ({ page }) => {
    expect(await read(page, CK[0], fixture('cardkingdom-cart-empty.html'), CK[1], CK[2])).toMatchObject({ ok: false, code: 'cart.empty' });
  });

  test('a redesigned cart is cart.page_changed; a sign-in redirect is cart.sign_in', async ({ page }) => {
    expect(await read(page, CK[0], '<!doctype html><main><h1>Cart (2 items)</h1></main>', CK[1], CK[2])).toMatchObject({ ok: false, code: 'cart.page_changed' });
    expect(await read(page, 'https://www.cardkingdom.com/customer_login', '<!doctype html><main>Sign in</main>', CK[1], CK[2]))
      .toMatchObject({ ok: false, code: 'cart.sign_in' });
  });
});
