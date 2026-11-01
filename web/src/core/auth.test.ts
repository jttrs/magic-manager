import { describe, expect, it } from 'vitest';
import { ApiError } from './apiError';
import { authErrorMessage, isSignedOut, loginHref, readSignInParams } from './auth';

const CODE = 'uXzOwwvx9K3YGKPD_qLZ_GK0iABKv9ABsnE31c4X58E';

describe('readSignInParams', () => {
  it('takes the invite and error out of the query and keeps the rest', () => {
    expect(readSignInParams(`?invite=${CODE}&auth_error=not_invited&x=1`)).toEqual({ invite: CODE, error: 'not_invited', rest: '?x=1' });
    expect(readSignInParams('')).toEqual({ invite: null, error: null, rest: '' });
  });
  it('drops malformed values', () => {
    expect(readSignInParams('?invite=short&auth_error=<script>').invite).toBeNull();
    expect(readSignInParams('?auth_error=<script>').error).toBe('unknown');
  });
});

describe('authErrorMessage', () => {
  it('names the problem and the way out', () => {
    expect(authErrorMessage('profiles_soon')).toMatch(/Profiles open soon/);
    expect(authErrorMessage('profile_unavailable')).toMatch(/collection couldn’t be opened/);
    expect(authErrorMessage('unknown')).toMatch(/Start again/);
    expect(authErrorMessage(null)).toBeNull();
  });
});

describe('loginHref', () => {
  it('carries the invite and a same-origin return path only', () => {
    expect(loginHref('/api/auth/login/discord', CODE, '/decks')).toBe(`/api/auth/login/discord?invite=${CODE}&next=%2Fdecks`);
    expect(loginHref('/api/auth/login/google', null, '/')).toBe('/api/auth/login/google');
    expect(loginHref('/api/auth/login/google', null, '//evil.example')).toBe('/api/auth/login/google');
  });
});

describe('isSignedOut', () => {
  it('recognizes the gate’s auth.required', () => {
    expect(isSignedOut(new ApiError('x', { status: 401, code: 'auth.required' }))).toBe(true);
    expect(isSignedOut(new ApiError('x', { status: 403, code: 'auth.csrf' }))).toBe(false);
    expect(isSignedOut(null)).toBe(false);
  });
});
