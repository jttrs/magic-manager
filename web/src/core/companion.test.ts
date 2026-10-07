import { describe, expect, it, vi } from 'vitest';
import { CHANNEL, CompanionError, isOlder, onHello, parseBookmarkletPaste, ping, request, warningLines } from './companion';

type Listener = (ev: { source: unknown; origin: string; data: unknown }) => void;

/** A window stand-in: postMessage goes to `sent`, `deliver` fires message listeners. */
function fakeWindow(origin = 'http://localhost:8765') {
  const listeners = new Set<Listener>();
  const sent: { data: Record<string, unknown>; target: string }[] = [];
  const win = {
    location: { origin },
    addEventListener: (_: string, fn: Listener) => listeners.add(fn),
    removeEventListener: (_: string, fn: Listener) => listeners.delete(fn),
    postMessage: (data: Record<string, unknown>, target: string) => sent.push({ data, target }),
    setTimeout: (fn: () => void, ms: number) => setTimeout(fn, ms),
    clearTimeout: (t: ReturnType<typeof setTimeout>) => clearTimeout(t),
  };
  const deliver = (data: unknown, { source = win as unknown, from = origin } = {}) => listeners.forEach((fn) => fn({ source, origin: from, data }));
  return { win: win as unknown as Window, sent, deliver, listeners };
}

const CART = {
  items: [{ scryfall_id: '8d8432a7-1c8a-4cfb-947c-ecf9791063eb', name: 'Sire of Seven Deaths', set_name: 'Foundations', finish: 'foil', condition: 'NM', treatments: [], quantity: 2, price: 20.5 }],
  warnings: [],
};
const catalog = {
  'companion.not_installed': { message: 'The browser companion didn’t answer.', fix: 'Install it.' },
  'request.denied': { message: 'You chose not to send it.', fix: null },
  'cart.paste_invalid': { message: 'That isn’t what the cart bookmarklet copies.', fix: 'Click the bookmarklet again.' },
  'cart.empty': { message: 'Your cart is empty.', fix: null },
};

describe('request', () => {
  it('posts one request pinned to this origin and resolves with validated data after approval', async () => {
    const { win, sent, deliver } = fakeWindow();
    const onAwait = vi.fn();
    const p = request(win, 'cart', {}, { catalog, onAwaitingApproval: onAwait });
    expect(sent).toHaveLength(1);
    const { data: req, target } = sent[0];
    expect(target).toBe('http://localhost:8765');
    expect(req).toMatchObject({ channel: CHANNEL, from: 'app', type: 'request', kind: 'cart' });
    deliver({ channel: CHANNEL, from: 'companion', type: 'ack', id: req.id, ok: true, summary: '1 cart line' });
    expect(onAwait).toHaveBeenCalledWith('1 cart line');
    deliver({ channel: CHANNEL, from: 'companion', type: 'result', id: req.id, ok: true, data: CART });
    await expect(p).resolves.toEqual(CART);
  });

  it('ignores messages from other windows, other origins, the app itself, and other request ids', async () => {
    const { win, sent, deliver } = fakeWindow();
    const p = request(win, 'cart', {}, { catalog, ackTimeoutMs: 50 });
    const id = sent[0].data.id;
    const forged = { channel: CHANNEL, from: 'companion', type: 'result', id, ok: true, data: CART };
    deliver(forged, { source: {} });                         // an iframe / other window
    deliver(forged, { from: 'https://evil.example' });       // another origin
    deliver({ ...forged, from: 'app' });                     // the page talking to itself
    deliver({ ...forged, id: 'someone-else' });
    await expect(p).rejects.toMatchObject({ code: 'companion.not_installed' });
  });

  it('rejects with the catalogued code, message and fix when the companion refuses', async () => {
    const { win, sent, deliver } = fakeWindow();
    const p = request(win, 'cart', {}, { catalog });
    const id = sent[0].data.id;
    deliver({ channel: CHANNEL, from: 'companion', type: 'ack', id, ok: true });
    deliver({ channel: CHANNEL, from: 'companion', type: 'result', id, ok: false, code: 'request.denied' });
    const e = await p.catch((x: unknown) => x);
    expect(e).toBeInstanceOf(CompanionError);
    expect(e).toMatchObject({ code: 'request.denied', message: 'You chose not to send it.' });
  });

  it('uses the message the companion sent for codes the app has no catalog entry for', async () => {
    const { win, sent, deliver } = fakeWindow();
    const p = request(win, 'moxfield', { url: 'https://moxfield.com/decks/abcd' }, { catalog });
    deliver({ channel: CHANNEL, from: 'companion', type: 'ack', id: sent[0].data.id, ok: false, code: 'moxfield.private', message: 'Private deck.', fix: 'Sign in.' });
    await expect(p).rejects.toMatchObject({ code: 'moxfield.private', message: 'Private deck.', fix: 'Sign in.' });
  });

  it('refuses data that does not match the kind’s shape (e.g. extra secrets are not passed on)', async () => {
    const { win, sent, deliver } = fakeWindow();
    const p = request(win, 'cart', {}, { catalog });
    const id = sent[0].data.id;
    deliver({ channel: CHANNEL, from: 'companion', type: 'result', id, ok: true, data: { items: [{ quantity: 'lots' }], warnings: [] } });
    await expect(p).rejects.toMatchObject({ code: 'request.invalid' });
  });

  it('times out as not installed when nothing answers', async () => {
    const { win } = fakeWindow();
    await expect(request(win, 'tabs', {}, { catalog, ackTimeoutMs: 10 })).rejects.toMatchObject({ code: 'companion.not_installed', fix: 'Install it.' });
  });

  it('cleans up its listener once settled', async () => {
    const { win, sent, deliver, listeners } = fakeWindow();
    const p = request(win, 'cart', {}, { catalog });
    deliver({ channel: CHANNEL, from: 'companion', type: 'result', id: sent[0].data.id, ok: true, data: CART });
    await p;
    expect(listeners.size).toBe(0);
  });
});

describe('hello + ping', () => {
  it('reports a well-formed hello from the bridge only', () => {
    const { win, sent, deliver } = fakeWindow();
    const seen = vi.fn();
    const off = onHello(win, seen);
    ping(win);
    expect(sent[0].data).toMatchObject({ channel: CHANNEL, from: 'app', type: 'ping' });
    deliver({ channel: CHANNEL, from: 'companion', type: 'hello', version: '0.1.0', features: { cart: true, deals: false, moxfield: true } });
    deliver({ channel: CHANNEL, from: 'companion', type: 'hello', version: '0.1.0' }, { from: 'https://evil.example' });
    deliver({ channel: CHANNEL, from: 'companion', type: 'hello', version: 7 });
    expect(seen).toHaveBeenCalledTimes(1);
    expect(seen.mock.calls[0][0].features.moxfield).toBe(true);
    off();
  });
});

describe('parseBookmarkletPaste', () => {
  const paste = (o: unknown) => JSON.stringify(o);
  it('accepts what the bookmarklet copies', () => {
    expect(parseBookmarkletPaste(paste({ source: 'manapool-cart-page', version: '0.1.0', ...CART }), catalog).items).toHaveLength(1);
  });
  it.each([
    ['not JSON', 'hello'],
    ['another shape', paste({ items: CART.items })],
    ['bad lines', paste({ source: 'manapool-cart-page', items: [{ name: 'x' }] })],
  ])('rejects %s with cart.paste_invalid', (_, text) => {
    expect(() => parseBookmarkletPaste(text, catalog)).toThrow(expect.objectContaining({ code: 'cart.paste_invalid', fix: 'Click the bookmarklet again.' }));
  });
  it('says the cart is empty rather than invalid', () => {
    expect(() => parseBookmarkletPaste(paste({ source: 'manapool-cart-page', items: [] }), catalog)).toThrow(expect.objectContaining({ code: 'cart.empty' }));
  });
});

describe('helpers', () => {
  it('compares versions numerically', () => {
    expect(isOlder('0.1.0', '0.2.0')).toBe(true);
    expect(isOlder('0.10.0', '0.9.9')).toBe(false);
    expect(isOlder('1.0', '1.0.0')).toBe(false);
  });
  it('groups warnings into catalogued lines', () => {
    expect(warningLines([{ code: 'cart.row_unreadable' }, { code: 'cart.row_unreadable' }, { code: 'x.y' }], { 'cart.row_unreadable': { message: 'Some rows' } }))
      .toEqual(['Some rows (2)', 'x.y']);
  });
});
