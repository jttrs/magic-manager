// Client analytics tracker (docs/analytics.md). Framework-free: batched,
// offline-tolerant, consent-aware, no third-party scripts and nothing stored on
// the device — the session id lives in memory only and rotates after 30 idle
// minutes. The server re-validates everything against the event catalog.

export type Category = 'error' | 'usage';
type PropValue = string | number | boolean;
type Props = Record<string, PropValue>;
export type Queued = { name: string; props: Props; ts: number };
export type Consent = { errors: boolean; usage: boolean; disabled?: boolean };
type Send = (events: Queued[], sessionId: string) => Promise<boolean>;

/** The events the browser may send, by consent category (mirrors config/analytics_events.toml). */
export const CLIENT_EVENTS = {
  'page.viewed': 'usage',
  'client.error': 'error',
  'client.network_error': 'error',
  'companion.error': 'error',
} as const satisfies Record<string, Category>;
type ClientEvent = keyof typeof CLIENT_EVENTS;

/** Page names the catalog allows — never a path (paths can carry slugs and names). */
export const VIEWS = ['collection', 'history', 'jumpstart', 'decks', 'deck_editor', 'explore', 'market', 'jobs', 'analytics', 'other'] as const;
export type View = (typeof VIEWS)[number];

export function viewOf(pathname: string): View {
  const p = pathname.replace(/\/+$/, '') || '/';
  if (p === '/collection/history') return 'history';
  if (p === '/collection/jumpstart') return 'jumpstart';
  if (p === '/collection' || p === '/' || p === '/sets') return 'collection';
  if (/^\/decks\/[^/]+\/edit$/.test(p)) return 'deck_editor';
  if (p === '/decks') return 'decks';
  if (p === '/explore' || p === '/commanders') return 'explore';
  if (p === '/market') return 'market';
  if (p === '/jobs') return 'jobs';
  if (p === '/analytics') return 'analytics';
  return 'other';
}

/** An error's TYPE as a catalog code (`TypeError` → `type_error`); never its message. */
export function errorCode(err: unknown): string {
  const raw = err instanceof Error ? err.name : typeof err === 'string' ? 'string_rejection' : 'unknown';
  const snake = raw
    .replace(/([a-z0-9])([A-Z])/g, '$1_$2')
    .replace(/([A-Z])([A-Z][a-z])/g, '$1_$2')
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, '_')
    .replace(/\d{5,}/g, '')
    .replace(/^_+|_+$/g, '');
  const code = /^[a-z]/.test(snake) ? snake : `e_${snake || 'unknown'}`;
  return code.slice(0, 64);
}

export type TrackerOptions = {
  send: Send;
  now?: () => number;
  uuid?: () => string;
  maxQueue?: number;
  batch?: number;
  idleMs?: number;
};

export type Tracker = {
  track: (name: ClientEvent, props?: Props) => void;
  setConsent: (c: Consent | null) => void;
  flush: () => Promise<void>;
  sessionId: () => string;
  pending: () => Queued[];
};

/**
 * Until consent is known, events wait in memory (bounded); once known, events
 * the user hasn't allowed are discarded, never sent. A failed send keeps the
 * batch for the next flush (oldest dropped past `maxQueue`).
 */
export function createTracker({ send, now = Date.now, uuid = () => crypto.randomUUID(), maxQueue = 200, batch = 50, idleMs = 30 * 60_000 }: TrackerOptions): Tracker {
  let queue: Queued[] = [];
  let consent: Consent | null = null;
  let sid = uuid();
  let lastActive = now();
  let flushing: Promise<void> | null = null;

  const allowed = (name: string) => {
    if (!consent || consent.disabled) return false;
    return CLIENT_EVENTS[name as ClientEvent] === 'error' ? consent.errors : consent.usage;
  };

  const sessionId = () => {
    const t = now();
    if (t - lastActive > idleMs) sid = uuid();
    lastActive = t;
    return sid;
  };

  return {
    track(name, props = {}) {
      if (!(name in CLIENT_EVENTS)) return;
      if (consent && !allowed(name)) return;
      sessionId();
      queue.push({ name, props, ts: now() });
      if (queue.length > maxQueue) queue = queue.slice(queue.length - maxQueue);
    },
    setConsent(c) {
      consent = c;
      if (c) queue = queue.filter((e) => allowed(e.name));
    },
    async flush() {
      if (flushing) return flushing;
      if (!consent || !queue.length) return;
      flushing = (async () => {
        while (queue.length) {
          const chunk = queue.slice(0, batch);
          let ok = false;
          try {
            ok = await send(chunk, sid);
          } catch {
            ok = false;
          }
          if (!ok) break;
          queue = queue.slice(chunk.length);
        }
      })();
      try {
        await flushing;
      } finally {
        flushing = null;
      }
    },
    sessionId,
    pending: () => [...queue],
  };
}
