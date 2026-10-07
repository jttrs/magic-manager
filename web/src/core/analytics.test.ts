import { describe, expect, it } from 'vitest';
import toml from '../../../config/analytics_events.toml?raw';
import { CLIENT_EVENTS, createTracker, errorCode, viewOf, VIEWS, type Queued } from './analytics';

function setup(ok = true) {
  const sent: { events: Queued[]; sid: string }[] = [];
  let t = 1_000;
  let n = 0;
  const tracker = createTracker({
    send: async (events, sid) => { sent.push({ events, sid }); return ok; },
    now: () => t,
    uuid: () => `sid-${++n}`,
    maxQueue: 5,
    batch: 2,
  });
  return { tracker, sent, advance: (ms: number) => { t += ms; } };
}

describe('tracker', () => {
  it('holds events until consent is known, then sends only what is allowed', async () => {
    const { tracker, sent } = setup();
    tracker.track('page.viewed', { view: 'decks', viewport: 'wide' });
    tracker.track('client.error', { view: 'decks', kind: 'uncaught', code: 'type_error' });
    await tracker.flush();
    expect(sent).toEqual([]);
    tracker.setConsent({ errors: true, usage: false });
    expect(tracker.pending().map((e) => e.name)).toEqual(['client.error']);
    tracker.track('page.viewed', { view: 'decks', viewport: 'wide' });
    await tracker.flush();
    expect(sent.flatMap((b) => b.events.map((e) => e.name))).toEqual(['client.error']);
  });

  it('sends nothing when opted out or disabled', async () => {
    const { tracker, sent } = setup();
    tracker.setConsent({ errors: true, usage: true, disabled: true });
    tracker.track('client.error', { view: 'decks', kind: 'uncaught', code: 'x' });
    await tracker.flush();
    expect(sent).toEqual([]);
  });

  it('batches, keeps a failed batch for later, and bounds the queue', async () => {
    const bad = setup(false);
    bad.tracker.setConsent({ errors: true, usage: true });
    for (let i = 0; i < 7; i++) bad.tracker.track('page.viewed', { view: 'decks', viewport: 'wide' });
    expect(bad.tracker.pending()).toHaveLength(5);
    await bad.tracker.flush();
    expect(bad.sent).toHaveLength(1);
    expect(bad.tracker.pending()).toHaveLength(5);

    const good = setup(true);
    good.tracker.setConsent({ errors: true, usage: true });
    for (let i = 0; i < 3; i++) good.tracker.track('page.viewed', { view: 'decks', viewport: 'wide' });
    await good.tracker.flush();
    expect(good.sent.map((b) => b.events.length)).toEqual([2, 1]);
    expect(good.tracker.pending()).toEqual([]);
  });

  it('rotates the in-memory session after 30 idle minutes', () => {
    const { tracker, advance } = setup();
    const first = tracker.sessionId();
    advance(29 * 60_000);
    expect(tracker.sessionId()).toBe(first);
    advance(31 * 60_000);
    expect(tracker.sessionId()).not.toBe(first);
  });
});

describe('helpers', () => {
  it('maps paths to page names, never paths', () => {
    expect(viewOf('/decks/my-secret-deck/edit')).toBe('deck_editor');
    expect(viewOf('/collection/history')).toBe('history');
    expect(viewOf('/explore')).toBe('explore');
    expect(viewOf('/whatever/else')).toBe('other');
  });

  it('turns an error into its type code, never its message', () => {
    expect(errorCode(new TypeError('cards.map is not a function for Sol Ring'))).toBe('type_error');
    expect(errorCode('boom')).toBe('string_rejection');
    expect(errorCode({})).toBe('unknown');
  });

  it('mirrors the catalog: client events, categories and views', () => {
    for (const [name, category] of Object.entries(CLIENT_EVENTS)) {
      const block = toml.split(`[events."${name}"]`)[1]?.split('[events.')[0] ?? '';
      expect(block, name).toContain(`category = "${category}"`);
      expect(block, name).toContain('source = "client"');
    }
    for (const v of VIEWS) expect(toml).toContain(`"${v}"`);
  });
});
