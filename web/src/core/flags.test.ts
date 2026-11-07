import { describe, expect, it } from 'vitest';
import type { FlagRowOut } from './api';
import { applyRow, changedLabel, choiceValue, everyoneValue, mineChoice, sourceLabel } from './flags';

const row = (over: Partial<FlagRowOut> = {}): FlagRowOut => ({
  name: 'deals', title: 'Deals', about: 'x', kind: 'release', default: false, everyone: null, pinned_by_env: false,
  mine: null, effective: false, source: 'default', changed_at: null, changed_by: null, ...over,
});

describe('flags view-model', () => {
  it('labels the source', () => {
    expect(sourceLabel(row())).toBe('Default');
    expect(sourceLabel(row({ source: 'local_file' }))).toBe('This machine’s file');
    expect(sourceLabel(row({ source: 'everyone' }))).toBe('Set for everyone');
    expect(sourceLabel(row({ source: 'env' }))).toBe('Pinned by environment');
    expect(sourceLabel(row({ source: 'user' }))).toBe('Just you');
  });

  it('describes the last change', () => {
    const now = new Date('2026-11-01T12:00:00Z');
    expect(changedLabel(row(), now)).toBe('Off · Default');
    expect(changedLabel(row({ effective: true, source: 'everyone', changed_at: '2026-11-01T09:00:00Z' }), now)).toBe('On · Set for everyone · 3 h ago');
    expect(changedLabel(row({ effective: true, source: 'everyone', changed_at: '2026-11-01T11:59:50Z', changed_by: 'Jared' }), now)).toBe('On · Set for everyone by Jared · just now');
  });

  it('reads the switch and the just-me choice', () => {
    expect(everyoneValue(row({ default: true }))).toBe(true);
    expect(everyoneValue(row({ default: true, everyone: false }))).toBe(false);
    expect(mineChoice(row())).toBe('default');
    expect(mineChoice(row({ mine: true }))).toBe('on');
    expect(mineChoice(row({ mine: false }))).toBe('off');
    expect(choiceValue('off')).toBe(false);
  });

  it('replaces a row by name', () => {
    const a = row({ name: 'a' });
    const b = row({ name: 'b' });
    const b2 = row({ name: 'b', effective: true });
    expect(applyRow([a, b], b2)).toEqual([a, b2]);
  });
});
