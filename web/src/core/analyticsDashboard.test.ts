import { describe, expect, it } from 'vitest';
import { ageLabel, analyticsSearch, errorTitle, featureLabel, fmtDuration, funnelRate, shortRef, viewRows } from './analyticsDashboard';

describe('analytics dashboard view-model', () => {
  it('parses URL state with safe defaults', () => {
    expect(analyticsSearch.parse({})).toEqual({ days: 30 });
    expect(analyticsSearch.parse({ days: '7', ref: 'ABCDEF12' }).days).toBe(7);
    expect(analyticsSearch.parse({ days: '12', ref: 'nope!' })).toEqual({ days: 30, ref: undefined });
  });

  it('names each error group by what failed and how', () => {
    expect(errorTitle('api.error', { route: 'deck_save', method: 'PUT', status: '409', code: 'stale_draft' })).toEqual({ what: 'PUT deck_save', how: '409 · stale_draft' });
    expect(errorTitle('job.failed', { job: 'edhrec.sync_bulk', code: 'runtime_error' }).what).toBe('Job edhrec.sync_bulk');
    expect(errorTitle('client.error', { view: 'deck_editor', kind: 'uncaught', code: 'type_error' }).what).toBe('Deck editor · uncaught error');
    expect(errorTitle('companion.error', { code: 'cart.no_tab' })).toEqual({ what: 'Browser companion', how: 'cart.no_tab' });
  });

  it('formats ages, refs, durations, funnels and features', () => {
    expect(ageLabel('2026-10-07', '2026-10-07')).toBe('today');
    expect(ageLabel('2026-10-06', '2026-10-07')).toBe('yesterday');
    expect(ageLabel('2026-10-01', '2026-10-07')).toBe('6 days ago');
    expect(shortRef('abcdef0123456789')).toBe('abcdef01');
    expect(fmtDuration(850)).toBe('850 ms');
    expect(fmtDuration(12_400)).toBe('12.4 s');
    expect(fmtDuration(null)).toBe('—');
    expect(funnelRate(4, 1)).toBe(25);
    expect(funnelRate(0, 0)).toBeNull();
    expect(featureLabel('deck.changed', { action: 'break_down' })).toBe('Deck · break down');
  });

  it('scales view bars to the busiest view and splits phone use', () => {
    const rows = viewRows([{ view: 'collection', narrow: 1, wide: 3, n: 4 }, { view: 'decks', narrow: 0, wide: 2, n: 2 }]);
    expect(rows.map((r) => [r.label, r.share, r.narrowShare])).toEqual([['Collection', 1, 0.25], ['Decks', 0.5, 0]]);
  });
});
