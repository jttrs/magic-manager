import { useEffect, useMemo, useRef, useState, type KeyboardEvent, type MouseEvent, type PointerEvent } from 'react';

const HOLD_DELAY_MS = 400;

type Press = { onPress: (e: MouseEvent) => void; onHold: () => void };

/** The press-vs-hold state machine, free of React so it can be tested with fake timers.
 *  A press is a click; a hold is the pointer staying down for `delay`, a context menu
 *  (long-press on touch, the ContextMenu key) or Shift+Enter. A hold swallows the click that follows it. */
export function createPressHold(get: () => Press, setHolding: (v: boolean) => void, delay = HOLD_DELAY_MS) {
  let timer: ReturnType<typeof setTimeout> | undefined;
  let consumed = false;
  const clear = () => {
    if (timer !== undefined) clearTimeout(timer);
    timer = undefined;
    setHolding(false);
  };
  return {
    down(e: { button: number }) {
      if (e.button !== 0) return;
      consumed = false;
      clear();
      setHolding(true);
      timer = setTimeout(() => {
        timer = undefined;
        consumed = true;
        setHolding(false);
        get().onHold();
      }, delay);
    },
    cancel: clear,
    contextMenu(e: { preventDefault: () => void }) {
      e.preventDefault();
      if (consumed) return; // a touch long-press already held before the menu fired
      clear();
      get().onHold();
    },
    keyDown(e: { key: string; shiftKey: boolean; preventDefault: () => void }) {
      if (e.key === 'Enter' && e.shiftKey) {
        e.preventDefault();
        get().onHold();
      }
    },
    click(e: MouseEvent) {
      if (consumed) {
        consumed = false;
        return;
      }
      get().onPress(e);
    },
  };
}

/** Props to spread on a button that acts on click and on a hold (see `createPressHold`). */
export function usePressHold({ onPress, onHold, delay = HOLD_DELAY_MS }: Press & { delay?: number }) {
  const [holding, setHolding] = useState(false);
  const latest = useRef<Press>({ onPress, onHold });
  useEffect(() => {
    latest.current = { onPress, onHold };
  });
  const gesture = useMemo(() => createPressHold(() => latest.current, setHolding, delay), [delay]);
  useEffect(() => gesture.cancel, [gesture]);
  return {
    onPointerDown: (e: PointerEvent) => gesture.down(e),
    onPointerUp: gesture.cancel,
    onPointerLeave: gesture.cancel,
    onPointerCancel: gesture.cancel,
    onContextMenu: (e: MouseEvent) => gesture.contextMenu(e),
    onKeyDown: (e: KeyboardEvent) => gesture.keyDown(e),
    onClick: (e: MouseEvent) => gesture.click(e),
    holding,
  };
}
