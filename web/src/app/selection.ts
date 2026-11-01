// Highlighter selection: the user's marked cards (to buy, or to pull for a deck).
// Kept per view in sessionStorage so it survives reloads but not new sessions.
// The marked cards are copied from the sheet header: `GuideSheet marked={{ count, getText, onClear: clear }}` (CopyMarked).
import { useCallback, useEffect, useState } from 'react';

const read = (key: string) => new Set<string>(JSON.parse(sessionStorage.getItem(key) ?? '[]'));

/** A scope change (e.g. another history entry opened) switches to that scope's own marks. */
export function useSelection(scope: string) {
  const key = `mm.sel.${scope}`;
  const [state, setState] = useState(() => ({ key, sel: read(key) }));
  if (state.key !== key) setState({ key, sel: read(key) });
  const sel = state.key === key ? state.sel : read(key);
  useEffect(() => sessionStorage.setItem(state.key, JSON.stringify([...state.sel])), [state]);
  const toggle = useCallback((k: string) => {
    setState((s) => {
      const n = new Set(s.sel);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return { key: s.key, sel: n };
    });
  }, []);
  const clear = useCallback(() => setState((s) => ({ key: s.key, sel: new Set<string>() })), []);
  return { selected: sel, toggle, clear };
}
