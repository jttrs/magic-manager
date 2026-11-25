// A preference kept in this browser (localStorage), readable from React and from plain code, kept in
// step across tabs. Storage is the source of truth on every read; only when a write fails (blocked or
// full) does the value live in memory, for this tab only.
import { useSyncExternalStore } from 'react';

export type LocalPref<T> = { use: () => T; get: () => T; set: (v: T) => void };

export function createLocalPref<T>({ key, parse, serialize }: { key: string; parse: (raw: string | null) => T; serialize: (v: T) => string | null }): LocalPref<T> {
  const listeners = new Set<() => void>();
  let blocked = false; // a write failed: `memory` holds the value
  let memory: T = parse(null);

  const get = (): T => {
    if (blocked) return memory;
    try {
      return parse(localStorage.getItem(key));
    } catch {
      return memory; // storage unreadable
    }
  };

  const set = (v: T): void => {
    memory = v;
    try {
      const raw = serialize(v); // null = the default: store nothing
      if (raw == null) localStorage.removeItem(key);
      else localStorage.setItem(key, raw);
      blocked = false;
    } catch {
      blocked = true;
    }
    for (const l of listeners) l();
  };

  const subscribe = (l: () => void) => {
    listeners.add(l);
    const onStorage = (e: StorageEvent) => {
      if (e.key === key || e.key === null) l();
    };
    window.addEventListener('storage', onStorage);
    return () => {
      listeners.delete(l);
      window.removeEventListener('storage', onStorage);
    };
  };

  const server = parse(null);
  return { get, set, use: () => useSyncExternalStore(subscribe, get, () => server) };
}
