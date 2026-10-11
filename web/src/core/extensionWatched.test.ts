import { beforeEach, describe, expect, it } from 'vitest';

// Executes the companion's watched-page reader (extension/src/watched.js) against a stubbed `chrome`
// and fake inject / loaded / alive — the mid-read safety paths that the e2e (companion-watched.spec.ts)
// can't drive. watched.js is plain browser ESM with no types, so it is loaded by path at run time.
type Entry = { url: string; store: string };
type Result = { urls: { url: string; open: boolean }[]; pages: Record<string, unknown>; warnings: { code: string; url: string }[] };
type Deps = { inject: (tabId: number, file: string, fn: unknown) => Promise<unknown>; loaded: (tabId: number, ms: number) => Promise<boolean>; alive: () => Promise<boolean> };
type Watched = { readWatched: (plan: { urls: Entry[] }, deps: Deps) => Promise<Result> };

const MODULE = new URL('../../../extension/src/watched.js', import.meta.url).pathname;
const PAGE = { ld: [1], head: 'price', text: '$5' };   // reads as rendered
const url = (n: number) => `https://www.target.com/p/thing-${n}/-/A-${1000 + n}`;
const entries = (n: number): Entry[] => Array.from({ length: n }, (_, i) => ({ url: url(i), store: 'Target' }));

const tick = () => new Promise((r) => setTimeout(r, 0));

let created: string[];
let removed: number[];
let inFlight: number;
let maxInFlight: number;
let userTabs: { id: number; url: string }[];
let userTabNow: Map<number, string>;

beforeEach(() => {
  created = []; removed = []; inFlight = 0; maxInFlight = 0; userTabs = []; userTabNow = new Map();
  (globalThis as { chrome?: unknown }).chrome = {
    tabs: {
      query: async () => userTabs,
      get: async (id: number) => ({ id, url: userTabNow.get(id) }),
      create: async ({ url: u }: { url: string }) => {
        created.push(u);
        inFlight += 1;
        maxInFlight = Math.max(maxInFlight, inFlight);
        await tick();
        return { id: 100 + created.length };
      },
      remove: async (id: number) => { removed.push(id); inFlight -= 1; },
    },
    permissions: { contains: async () => true },
  };
});

const load = async () => (await import(/* @vite-ignore */ MODULE)) as Watched;
const deps = (over: Partial<Deps> = {}): Deps => ({ inject: async () => { await tick(); return PAGE; }, loaded: async () => true, alive: async () => true, ...over });

describe('readWatched mid-read safety', () => {
  it('stops opening tabs once alive() goes false mid-run', async () => {
    const { readWatched } = await load();
    let alive = true;
    const out = await readWatched({ urls: entries(6) }, deps({ alive: async () => alive, inject: async () => { alive = false; return PAGE; } }));
    expect(created).toHaveLength(3);   // the three already in flight; no create after the flip
    const skipped = out.warnings.filter((w) => w.code === 'tabs.page_unreadable').map((w) => w.url);
    expect(skipped).toEqual([url(3), url(4), url(5)]);
    expect(out.urls.slice(3).every((u) => u.open)).toBe(true);   // opened:false → reported as not opened by us
    expect(Object.keys(out.pages)).toHaveLength(3);
  });

  it('skips a user tab that navigated away, never injecting into it', async () => {
    const { readWatched } = await load();
    userTabs = [{ id: 7, url: url(0) }];
    userTabNow.set(7, 'https://www.target.com/p/elsewhere/-/A-999');
    const injected: number[] = [];
    const out = await readWatched({ urls: entries(1) }, deps({ inject: async (id) => { injected.push(id); return PAGE; } }));
    expect(out.warnings).toEqual([{ code: 'tabs.page_unreadable', url: url(0) }]);
    expect(injected).toEqual([]);
    expect(created).toEqual([]);
    expect(removed).toEqual([]);   // never one of yours to close
  });

  it('reads a user tab still on the page without opening or closing anything', async () => {
    const { readWatched } = await load();
    userTabs = [{ id: 7, url: url(0) }];
    userTabNow.set(7, url(0));
    const out = await readWatched({ urls: entries(1) }, deps());
    expect(out.warnings).toEqual([]);
    expect(out.urls[0].open).toBe(true);
    expect(created).toEqual([]);
    expect(removed).toEqual([]);
  });

  it('reports watched.load_timeout and still closes the tab it opened', async () => {
    const { readWatched } = await load();
    const out = await readWatched({ urls: entries(1) }, deps({ loaded: async () => false }));
    expect(out.warnings).toEqual([{ code: 'watched.load_timeout', url: url(0) }]);
    expect(created).toHaveLength(1);
    expect(removed).toEqual([101]);
    expect(out.urls[0].open).toBe(false);
  });

  it('never has more than 3 tabs open at once, and reads no more than MAX_WATCHED pages', async () => {
    const { readWatched } = await load();
    const out = await readWatched({ urls: entries(60) }, deps());
    expect(maxInFlight).toBe(3);
    expect(created).toHaveLength(50);
    expect(removed).toHaveLength(50);
    expect(out.urls).toHaveLength(50);
    expect(Object.keys(out.pages)).toHaveLength(50);
  });
});
