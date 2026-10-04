// Highlighter selection: the user's marked cards (to buy, or to pull for a deck).
// Kept per view in sessionStorage so it survives reloads but not new sessions.
import { useCallback, useEffect, useState } from 'react';

export function useSelection(scope: string) {
  const key = `mm.sel.${scope}`;
  const [sel, setSel] = useState<Set<string>>(() => new Set(JSON.parse(sessionStorage.getItem(key) ?? '[]')));
  useEffect(() => sessionStorage.setItem(key, JSON.stringify([...sel])), [key, sel]);
  const toggle = useCallback((k: string) => {
    setSel((s) => {
      const n = new Set(s);
      if (n.has(k)) n.delete(k);
      else n.add(k);
      return n;
    });
  }, []);
  const clear = useCallback(() => setSel(new Set()), []);
  return { selected: sel, toggle, clear };
}
