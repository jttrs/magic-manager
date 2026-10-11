// magic-manager companion — Moxfield's API from a moxfield.com tab.
//
// Shared by the Moxfield deck and collection readers (injected before them).
// Asks anonymously first: public and link-only decks, collections and binders
// need no sign-in. Only when Moxfield answers that a page is private (or the
// read is your own collection, which is always signed-in) does it ask Moxfield
// for a short-lived sign-in token — exactly as moxfield.com does when it loads
// (POST /v1/account/token/refresh; the browser attaches your Moxfield sign-in
// cookie itself, the companion never reads it). That token lives only in this
// function's memory for this one read, is sent only to api2.moxfield.com as
// Moxfield's own page sends it, and is never stored, logged or returned.
// (Owner-approved exception to "no tokens", 2026-10-11 — see
// docs/browser-companion-security.md.)
//
// A classic script: one global function.

function moxfieldSession() {
  'use strict';
  var API = 'https://api2.moxfield.com';
  var token = null;
  var tried = false;

  async function signIn() {
    if (tried) return token;
    tried = true;
    try {
      var r = await fetch(API + '/v1/account/token/refresh', {
        method: 'POST', credentials: 'include',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ isAppLogin: false })
      });
      if (!r.ok) return null;
      var j = await r.json();
      var t = j && j.access_token;
      token = typeof t === 'string' && t.length > 0 && t.length < 8192 ? t : null;
    } catch (e) {
      token = null;
    }
    return token;
  }

  async function once(path, withToken) {
    var headers = { Accept: 'application/json' };
    if (withToken) headers.Authorization = 'Bearer ' + token;
    return fetch(API + path, { credentials: 'include', headers: headers });
  }

  /**
   * GET an api2 path. auth: 'if_private' (anonymous, then signed in if Moxfield
   * says private) or 'always' (signed in — your own collection / binder list).
   * → {ok:true, data} | {ok:false, code: 'private'|'signed_out'|'blocked'|'not_found'|'http'|'changed', status}
   */
  async function get(path, auth) {
    var res;
    try {
      if (auth === 'always') {
        if (!await signIn()) return { ok: false, code: 'signed_out' };
        res = await once(path, true);
      } else {
        res = await once(path, token != null);
        if ((res.status === 401 || res.status === 403) && /json/.test(res.headers.get('content-type') || '') && token == null && await signIn()) {
          res = await once(path, true);
        }
      }
    } catch (e) {
      return { ok: false, code: 'blocked' };
    }
    if (res.status === 401 || res.status === 403) {
      // Cloudflare's challenge is also a 403 — tell them apart by the body type.
      var ct = res.headers.get('content-type') || '';
      if (!/json/.test(ct)) return { ok: false, code: 'blocked', status: res.status };
      return { ok: false, code: auth === 'always' ? 'signed_out' : 'private', status: res.status };
    }
    if (res.status === 404) return { ok: false, code: 'not_found', status: 404 };
    if (!res.ok) return { ok: false, code: 'http', status: res.status };
    try {
      return { ok: true, data: await res.json() };
    } catch (e) {
      return { ok: false, code: 'changed' };
    }
  }

  return { get: get, signedIn: function () { return token != null; } };
}
