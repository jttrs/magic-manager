// The app side of the browser-companion protocol (extension/src/bridge.js).
// Framework-free: talks to the page's own window via postMessage, pinned to
// this page's origin, and validates every answer before anything uses it —
// the companion reads third-party pages, so its data is treated as untrusted.
// Error codes come from extension/errors.json (the one catalog).

import { z } from 'zod';

export const CHANNEL = 'magic-manager/companion';
export type CompanionKind = 'cart' | 'tabs' | 'moxfield';

const helloSchema = z.object({
  version: z.string().max(20),
  features: z.object({ cart: z.boolean(), deals: z.boolean(), moxfield: z.boolean() }),
});
export type CompanionHello = z.infer<typeof helloSchema>;

const cartLine = z.object({
  scryfall_id: z.string().regex(/^[0-9a-f-]{36}$/).nullable(),
  name: z.string().max(300).nullable(),
  set_name: z.string().max(200).nullable(),
  finish: z.enum(['nonfoil', 'foil', 'etched']),
  condition: z.string().max(8).nullable(),
  treatments: z.array(z.string().max(40)).max(10),
  quantity: z.number().int().min(1).max(999),
  price: z.number().min(0).nullable(),
});
const warning = z.object({ code: z.string().max(60) }).passthrough();
const cartDataSchema = z.object({ items: z.array(cartLine).max(2000), warnings: z.array(warning).max(2000) });
export type CartData = z.infer<typeof cartDataSchema>;
export type CartLine = z.infer<typeof cartLine>;

const page = z.object({ title: z.string().max(500), head: z.string().max(20_000), ld: z.array(z.string().max(100_000)).max(8), text: z.string().max(8_000) });
const tabsDataSchema = z.object({
  tabs: z.array(z.object({ url: z.string().max(2000).regex(/^https:\/\//), title: z.string().max(500), window: z.number().int().min(1) })).max(500),
  pages: z.record(z.string(), page),
  warnings: z.array(warning).max(500),
});
export type RenderedPage = z.infer<typeof page>;

const moxCard = z.object({
  quantity: z.number().int().min(1).max(999),
  isFoil: z.boolean(),
  finish: z.string().max(20).nullable(),
  card: z.object({ scryfall_id: z.string().max(40).nullable(), set: z.string().max(10).nullable(), cn: z.string().max(12).nullable(), name: z.string().max(200).nullable(), finish: z.string().max(20).nullable() }),
});
const moxDataSchema = z.object({
  url: z.string().max(200),
  deck: z.object({
    publicId: z.string().regex(/^[A-Za-z0-9_-]{4,64}$/),
    name: z.string().max(200).nullable(),
    createdByUser: z.object({ userName: z.string().max(100).nullable() }),
    boards: z.record(z.string().max(40), z.object({ cards: z.record(z.string(), moxCard) })),
  }),
});

const SCHEMAS = { cart: cartDataSchema, tabs: tabsDataSchema, moxfield: moxDataSchema } as const;
type DataOf<K extends CompanionKind> = z.infer<(typeof SCHEMAS)[K]>;

export type ErrorCatalog = Record<string, { message: string; fix?: string | null }>;

/** A companion failure, always with a catalogued code + a plain message and fix. */
export class CompanionError extends Error {
  code: string;
  fix: string | null;
  constructor(code: string, message: string, fix: string | null = null) {
    super(message);
    this.code = code;
    this.fix = fix;
  }
}

function companionError(code: string, catalog: ErrorCatalog = {}, fallback?: { message?: string; fix?: string | null }): CompanionError {
  const c = catalog[code];
  return new CompanionError(code, c?.message ?? fallback?.message ?? code, c?.fix ?? fallback?.fix ?? null);
}

type Envelope = { channel?: unknown; from?: unknown; type?: unknown; id?: unknown; ok?: unknown; code?: unknown; message?: unknown; fix?: unknown; data?: unknown; kind?: unknown };

/** Only messages this page posted to itself from the companion bridge. */
function fromCompanion(ev: MessageEvent, win: Window): Envelope | null {
  if (ev.source !== win || ev.origin !== win.location.origin) return null;
  const d = ev.data as Envelope | null;
  if (!d || typeof d !== 'object' || d.channel !== CHANNEL || d.from !== 'companion') return null;
  return d;
}

/** Calls ``onHello`` whenever the companion announces itself; returns an unsubscribe. */
export function onHello(win: Window, onHelloCb: (h: CompanionHello) => void): () => void {
  const fn = (ev: MessageEvent) => {
    const d = fromCompanion(ev, win);
    if (d?.type !== 'hello') return;
    const h = helloSchema.safeParse(d);
    if (h.success) onHelloCb(h.data);
  };
  win.addEventListener('message', fn);
  return () => win.removeEventListener('message', fn);
}

export function ping(win: Window): void {
  win.postMessage({ channel: CHANNEL, from: 'app', type: 'ping' }, win.location.origin);
}

const newId = () => (globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`).replace(/[^A-Za-z0-9_-]/g, '');

export type RequestOptions = {
  catalog?: ErrorCatalog;
  /** The extension reads before it asks you (opening a cart tab can take ~30 s). */
  ackTimeoutMs?: number;
  /** How long the approval window may stay open (the extension's own limit is 5 min). */
  resultTimeoutMs?: number;
  onAwaitingApproval?: (summary: string) => void;
};

/**
 * Ask the companion to read something; resolves with the validated data once
 * you press Send in its approval window, or rejects with a CompanionError.
 */
export function request<K extends CompanionKind>(win: Window, kind: K, params: { url?: string } = {}, opts: RequestOptions = {}): Promise<DataOf<K>> {
  const { catalog = {}, ackTimeoutMs = 45_000, resultTimeoutMs = 5 * 60_000 + 15_000 } = opts;
  const id = newId();
  return new Promise((resolve, reject) => {
    let timer = win.setTimeout(() => done(companionError('companion.not_installed', catalog)), ackTimeoutMs);
    const done = (err: CompanionError | null, data?: DataOf<K>) => {
      win.clearTimeout(timer);
      win.removeEventListener('message', fn);
      if (err) reject(err);
      else resolve(data as DataOf<K>);
    };
    const failWith = (d: Envelope) => done(companionError(typeof d.code === 'string' ? d.code : 'companion.timeout', catalog, {
      message: typeof d.message === 'string' ? d.message : undefined, fix: typeof d.fix === 'string' ? d.fix : null,
    }));
    const fn = (ev: MessageEvent) => {
      const d = fromCompanion(ev, win);
      if (!d || d.id !== id) return;
      if (d.type === 'ack') {
        if (d.ok !== true) return failWith(d);
        win.clearTimeout(timer);
        timer = win.setTimeout(() => done(companionError('companion.timeout', catalog)), resultTimeoutMs);
        opts.onAwaitingApproval?.(typeof (d as { summary?: unknown }).summary === 'string' ? (d as { summary: string }).summary : '');
      } else if (d.type === 'result') {
        if (d.ok !== true) return failWith(d);
        const parsed = SCHEMAS[kind].safeParse(d.data);
        if (!parsed.success) return done(companionError('request.invalid', catalog, { message: 'The companion sent data the app doesn’t recognise.' }));
        done(null, parsed.data as DataOf<K>);
      }
    };
    win.addEventListener('message', fn);
    win.postMessage({ channel: CHANNEL, from: 'app', type: 'request', id, kind, params }, win.location.origin);
  });
}

/** "0.1.0" < "0.2.0" — dotted numeric compare. */
export function isOlder(a: string, b: string): boolean {
  const pa = a.split('.').map((n) => Number.parseInt(n, 10) || 0);
  const pb = b.split('.').map((n) => Number.parseInt(n, 10) || 0);
  for (let i = 0; i < Math.max(pa.length, pb.length); i++) {
    if ((pa[i] ?? 0) !== (pb[i] ?? 0)) return (pa[i] ?? 0) < (pb[i] ?? 0);
  }
  return false;
}

/** The bookmarklet's clipboard payload → validated cart lines, or a CompanionError. */
export function parseBookmarkletPaste(text: string, catalog: ErrorCatalog = {}): CartData {
  let raw: unknown;
  try {
    raw = JSON.parse(text.trim());
  } catch {
    throw companionError('cart.paste_invalid', catalog);
  }
  const env = z.object({ source: z.literal('manapool-cart-page'), items: z.array(z.unknown()), warnings: z.array(z.unknown()).optional() }).safeParse(raw);
  if (!env.success) throw companionError('cart.paste_invalid', catalog);
  const parsed = cartDataSchema.safeParse({ items: env.data.items, warnings: env.data.warnings ?? [] });
  if (!parsed.success) throw companionError('cart.paste_invalid', catalog);
  if (!parsed.data.items.length) throw companionError('cart.empty', catalog);
  return parsed.data;
}

/** Plain-language lines for the warnings a read carried (beside the result). */
export function warningLines(warnings: { code: string; [k: string]: unknown }[], catalog: ErrorCatalog = {}): string[] {
  const out: string[] = [];
  const byCode = new Map<string, number>();
  for (const w of warnings) byCode.set(w.code, (byCode.get(w.code) ?? 0) + 1);
  for (const [code, n] of byCode) {
    const msg = catalog[code]?.message ?? code;
    out.push(n > 1 ? `${msg} (${n})` : msg);
  }
  return out;
}
