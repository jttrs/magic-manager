import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import type { MouseEvent } from 'react';
import { createPressHold } from './usePressHold';

const click = { shiftKey: false, detail: 1 } as MouseEvent;
const keyClick = { shiftKey: false, detail: 0 } as MouseEvent;

function setup() {
  const onPress = vi.fn();
  const onHold = vi.fn();
  const holding: boolean[] = [];
  const g = createPressHold(() => ({ onPress, onHold }), (v) => holding.push(v), 400);
  return { g, onPress, onHold, holding };
}

describe('press and hold', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('a plain click presses', () => {
    const { g, onPress, onHold } = setup();
    g.click(click);
    expect(onPress).toHaveBeenCalledWith(click);
    expect(onHold).not.toHaveBeenCalled();
  });

  it('holding 400 ms holds and swallows the click', () => {
    const { g, onPress, onHold, holding } = setup();
    g.down({ button: 0 });
    expect(holding.at(-1)).toBe(true);
    vi.advanceTimersByTime(400);
    expect(onHold).toHaveBeenCalledTimes(1);
    expect(holding.at(-1)).toBe(false);
    g.cancel();
    g.click(click);
    expect(onPress).not.toHaveBeenCalled();
    g.click(click); // only the one click is swallowed
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('releasing early presses', () => {
    const { g, onPress, onHold } = setup();
    g.down({ button: 0 });
    vi.advanceTimersByTime(200);
    g.cancel();
    vi.advanceTimersByTime(400);
    g.click(click);
    expect(onHold).not.toHaveBeenCalled();
    expect(onPress).toHaveBeenCalledTimes(1);
  });

  it('leaving cancels the hold', () => {
    const { g, onHold } = setup();
    g.down({ button: 0 });
    g.cancel();
    vi.advanceTimersByTime(1000);
    expect(onHold).not.toHaveBeenCalled();
  });

  it('only the primary button starts a hold', () => {
    const { g, onHold } = setup();
    g.down({ button: 2 });
    vi.advanceTimersByTime(1000);
    expect(onHold).not.toHaveBeenCalled();
  });

  it('Shift+Enter holds; plain Enter is left to the click', () => {
    const { g, onHold } = setup();
    const preventDefault = vi.fn();
    g.keyDown({ key: 'Enter', shiftKey: false, preventDefault });
    expect(onHold).not.toHaveBeenCalled();
    g.keyDown({ key: 'Enter', shiftKey: true, preventDefault });
    expect(onHold).toHaveBeenCalledTimes(1);
    expect(preventDefault).toHaveBeenCalledTimes(1);
  });

  it('the context menu holds and is prevented', () => {
    const { g, onHold } = setup();
    const preventDefault = vi.fn();
    g.contextMenu({ preventDefault });
    expect(preventDefault).toHaveBeenCalled();
    expect(onHold).toHaveBeenCalledTimes(1);
  });

  it('a hold released off the button never swallows the next keyboard press', () => {
    const { g, onPress, onHold } = setup();
    g.down({ button: 0 });
    vi.advanceTimersByTime(400);
    g.cancel();                       // pointer left: no click follows the hold
    expect(onHold).toHaveBeenCalledTimes(1);
    g.click(keyClick);                // Enter later
    expect(onPress).toHaveBeenCalledTimes(1);
  });
});
