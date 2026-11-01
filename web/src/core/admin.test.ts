import { describe, expect, it } from 'vitest';
import type { AdminUserOut, FlagStateOut, OwnerPathOut } from './api';
import { adminSearch, choiceValue, defaultChoiceLabel, filterUsers, flagChoice, flagTitle, ownerOnlyNote, providersLabel, seenLabel, showCounts, statusLabel, unflaggedPaths } from './admin';

const flag = (over: Partial<FlagStateOut> = {}): FlagStateOut => ({ name: 'deals', about: '', default: false, override: null, effective: false, owner_paths: [], ...over });
const user = (over: Partial<AdminUserOut> = {}): AdminUserOut => ({
  id: 'aaaaaaaaaaaaaaaa', display_name: 'Ana', email: 'ana@example.com', providers: ['discord'], is_admin: false,
  created_at: '2026-10-01T00:00:00+00:00', last_seen_at: null, disabled_at: null, sessions: 0, flags: [], ...over,
});
const PATHS: OwnerPathOut[] = [
  { key: 'deals.mac_tabs', feature: 'deals', title: 'Read tabs in this server’s Chrome' },
  { key: 'decks.moxfield_login', feature: null, title: 'Private Moxfield decks' },
];

describe('admin view-model', () => {
  it('parses URL state defensively', () => {
    expect(adminSearch.parse({})).toEqual({ q: '', show: 'all' });
    expect(adminSearch.parse({ show: 'nope', user: '../etc' })).toEqual({ q: '', show: 'all', user: undefined });
    expect(adminSearch.parse({ user: 'bbbbbbbbbbbbbbbb' }).user).toBe('bbbbbbbbbbbbbbbb');
  });

  it('filters by role, status and name/email', () => {
    const us = [user(), user({ id: 'b', display_name: 'Bo', email: null, is_admin: true }), user({ id: 'c', display_name: 'Cy', disabled_at: '2026-10-02' })];
    expect(filterUsers(us, { q: '', show: 'admins' }).map((u) => u.id)).toEqual(['b']);
    expect(filterUsers(us, { q: '', show: 'members' }).map((u) => u.id)).toEqual(['aaaaaaaaaaaaaaaa', 'c']);
    expect(filterUsers(us, { q: '', show: 'disabled' }).map((u) => u.id)).toEqual(['c']);
    expect(filterUsers(us, { q: 'EXAMPLE', show: 'all' }).map((u) => u.id)).toEqual(['aaaaaaaaaaaaaaaa', 'c']);
    expect(showCounts(us)).toEqual({ all: 3, admins: 1, members: 2, disabled: 1 });
  });

  it('says status, providers and last visit in plain words', () => {
    expect(statusLabel(user())).toBe('Signed out');
    expect(statusLabel(user({ sessions: 2 }))).toBe('Signed in on 2 browsers');
    expect(statusLabel(user({ sessions: 1, disabled_at: 'x' }))).toBe('Turned off');
    expect(providersLabel(user({ providers: ['discord', 'google'] }))).toBe('Discord · Google');
    const now = new Date('2026-11-01T12:00:00Z');
    expect(seenLabel(null, now)).toBe('never');
    expect(seenLabel('2026-11-01T11:59:30Z', now)).toBe('just now');
    expect(seenLabel('2026-11-01T11:30:00Z', now)).toBe('30 min ago');
    expect(seenLabel('2026-10-29T12:00:00Z', now)).toBe('3 days ago');
  });

  it('maps the three-way flag choice', () => {
    expect(flagChoice(flag())).toBe('default');
    expect(flagChoice(flag({ override: false }))).toBe('off');
    expect(choiceValue('on')).toBe(true);
    expect(choiceValue('default')).toBeNull();
    expect(defaultChoiceLabel(flag({ default: true }))).toBe('Default · on');
    expect(flagTitle('cart_check')).toBe('Cart check');
    expect(flagTitle('new_thing')).toBe('New thing');
  });

  it('labels owner-only parts of a flag', () => {
    expect(ownerOnlyNote(flag(), PATHS, false)).toBeNull();
    expect(ownerOnlyNote(flag({ owner_paths: ['deals.mac_tabs'] }), PATHS, false)).toBe('Stays owner-only for members: Read tabs in this server’s Chrome.');
    expect(ownerOnlyNote(flag({ owner_paths: ['deals.mac_tabs'] }), PATHS, true)).toMatch(/^Includes owner-only parts/);
    expect(unflaggedPaths(PATHS).map((p) => p.key)).toEqual(['decks.moxfield_login']);
  });
});
