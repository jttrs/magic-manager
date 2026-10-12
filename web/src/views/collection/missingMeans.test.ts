import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

function storage(opts: { failWrites?: boolean; failReads?: boolean } = {}) {
  const m = new Map<string, string>();
  return {
    getItem: (k: string) => { if (opts.failReads) throw new Error('blocked'); return m.get(k) ?? null; },
    setItem: (k: string, v: string) => { if (opts.failWrites) throw new Error('QuotaExceededError'); m.set(k, v); },
    removeItem: (k: string) => { if (opts.failWrites) throw new Error('QuotaExceededError'); m.delete(k); },
  };
}

describe('missingMeans preference', () => {
  beforeEach(() => { vi.resetModules(); });
  afterEach(() => { vi.unstubAllGlobals(); });

  it('defaults to this printing and persists the card choice', async () => {
    vi.stubGlobal('localStorage', storage());
    const m = await import('./missingMeans');
    expect(m.readMissingMeans()).toBe('printing');
    m.setMissingMeans('card');
    expect(localStorage.getItem('mm.collection.missingMeans')).toBe('card');
    expect(m.readMissingMeans()).toBe('card');
    m.setMissingMeans('printing');
    expect(localStorage.getItem('mm.collection.missingMeans')).toBeNull();
  });

  it('keeps the choice in memory when storage refuses writes but allows reads', async () => {
    vi.stubGlobal('localStorage', storage({ failWrites: true }));
    const m = await import('./missingMeans');
    m.setMissingMeans('card');
    expect(m.readMissingMeans()).toBe('card');
  });

  it('keeps the choice in memory when storage is blocked entirely', async () => {
    vi.stubGlobal('localStorage', storage({ failWrites: true, failReads: true }));
    const m = await import('./missingMeans');
    expect(m.readMissingMeans()).toBe('printing');
    m.setMissingMeans('card');
    expect(m.readMissingMeans()).toBe('card');
  });
});
