import { describe, expect, it } from 'vitest';
import { confirmMatches, exportFilename, reauthLinks, signInFresh } from './account';

describe('confirmMatches', () => {
  it('accepts the phrase in any case and spacing, nothing else', () => {
    expect(confirmMatches('delete my account')).toBe(true);
    expect(confirmMatches('  Delete   MY account ')).toBe(true);
    expect(confirmMatches('delete')).toBe(false);
    expect(confirmMatches('delete my accounts')).toBe(false);
    expect(confirmMatches('')).toBe(false);
  });
});

describe('signInFresh', () => {
  const fetched = 1_000_000;
  it('counts down the server seconds from when /me was read', () => {
    expect(signInFresh(300, fetched, fetched + 299_000)).toBe(true);
    expect(signInFresh(300, fetched, fetched + 300_000)).toBe(false);
    expect(signInFresh(0, fetched, fetched)).toBe(false);
    expect(signInFresh(null, fetched, fetched)).toBe(false);
    expect(signInFresh(300, 0, fetched)).toBe(false);
  });
});

describe('reauthLinks', () => {
  const providers = [
    { name: 'discord', title: 'Discord', login_url: '/api/auth/login/discord' },
    { name: 'google', title: 'Google', login_url: '/api/auth/login/google' },
  ];
  it('offers the linked providers and returns to the page', () => {
    expect(reauthLinks(providers, ['google'], '/decks')).toEqual([{ title: 'Google', href: '/api/auth/login/google?next=%2Fdecks' }]);
  });
  it('falls back to every provider', () => {
    expect(reauthLinks(providers, [], '/').map((l) => l.href)).toEqual(['/api/auth/login/discord', '/api/auth/login/google']);
  });
});

describe('exportFilename', () => {
  it('reads the server name, else a dated default', () => {
    expect(exportFilename('attachment; filename="magic-manager-export-2026-11-01.zip"')).toBe('magic-manager-export-2026-11-01.zip');
    expect(exportFilename(null, new Date('2026-01-02T00:00:00Z'))).toBe('magic-manager-export-2026-01-02.zip');
    expect(exportFilename('attachment; filename="../x"', new Date('2026-01-02T00:00:00Z'))).toBe('magic-manager-export-2026-01-02.zip');
  });
});
