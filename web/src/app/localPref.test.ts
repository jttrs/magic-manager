import { afterEach, describe, expect, it, vi } from 'vitest';
import { createLocalPref } from './localPref';
import { parseBuildableShort } from './deckPrefs';

function stubBrowser(opts: { failWrites?: boolean } = {}) {
  const m = new Map<string, string>();
  vi.stubGlobal('localStorage', {
    getItem: (k: string) => m.get(k) ?? null,
    setItem: (k: string, v: string) => { if (opts.failWrites) throw new Error('blocked'); m.set(k, v); },
    removeItem: (k: string) => { m.delete(k); },
  });
  return m;
}
const make = () => createLocalPref<number>({ key: 'k', parse: (r) => (r == null ? 1 : Number(r)), serialize: String });

describe('parseBuildableShort', () => {
  it('accepts 0–10 and falls back to 3', () => {
    for (const raw of [null, 'abc', '11', '-1', '2.5']) expect(parseBuildableShort(raw)).toBe(3);
    expect(parseBuildableShort('0')).toBe(0);
    expect(parseBuildableShort('10')).toBe(10);
  });
});

describe('createLocalPref', () => {
  afterEach(() => vi.unstubAllGlobals());

  it('reads storage on every get, so a change made elsewhere is seen', () => {
    const m = stubBrowser();
    const p = make();
    expect(p.get()).toBe(1);
    p.set(4);
    expect(m.get('k')).toBe('4');
    m.set('k', '7'); // another tab
    expect(p.get()).toBe(7);
  });

  it('keeps the value in memory only after a write fails', () => {
    stubBrowser({ failWrites: true });
    const p = make();
    p.set(5);
    expect(p.get()).toBe(5);
  });
});
