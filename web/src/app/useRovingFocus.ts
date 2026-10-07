import { useRef, useState, type KeyboardEvent } from 'react';

/** One tab stop for a list of rows (roving focus): ↑/↓ move, Home/End jump. Rows carry
 *  `attr` = their key and `tabIndex={key === tabKey ? 0 : -1}`; keys from other elements are ignored. */
export function useRovingFocus(keys: readonly string[], activeKey: string | undefined, attr: string) {
  const navRef = useRef<HTMLElement>(null);
  const [focusKey, setFocusKey] = useState<string | undefined>(undefined);
  const tabKey = (focusKey && keys.includes(focusKey) ? focusKey : undefined) ?? activeKey ?? keys[0];
  const onKeyDown = (e: KeyboardEvent<HTMLElement>) => {
    if (!(e.target as HTMLElement).hasAttribute(attr)) return;
    const i = keys.indexOf(tabKey ?? '');
    const next = e.key === 'ArrowDown' ? i + 1 : e.key === 'ArrowUp' ? i - 1 : e.key === 'Home' ? 0 : e.key === 'End' ? keys.length - 1 : null;
    if (next == null) return;
    e.preventDefault();
    const k = keys[Math.max(0, Math.min(keys.length - 1, next))];
    setFocusKey(k);
    navRef.current?.querySelector<HTMLElement>(`[${attr}="${CSS.escape(k)}"]`)?.focus();
  };
  return { navRef, tabKey, setFocusKey, onKeyDown };
}
