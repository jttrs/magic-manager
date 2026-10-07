// Wires the framework-free tracker into the app: the session header on every API
// call, consent from the server, page views from the router, uncaught errors,
// and a flush on an interval / when the tab is hidden (docs/analytics.md).
import { useQuery } from '@tanstack/react-query';
import { useRouterState } from '@tanstack/react-router';
import { useEffect } from 'react';
import { analyticsEvents } from '../core/api';
import { client } from '../core/api/client.gen';
import { onNoAnswer } from '../core/apiError';
import { createTracker, errorCode, viewOf, type Consent } from '../core/analytics';
import { consentQuery } from './queries';

const FLUSH_MS = 10_000;

const tracker = createTracker({
  async send(events, sessionId) {
    // keepalive: a batch sent while the tab closes still arrives.
    const r = await analyticsEvents({ body: { events }, headers: { 'X-MM-Session': sessionId }, keepalive: true });
    return Boolean(r.response?.ok);
  },
});

// Link server-side events (API errors, jobs) to this tab's session.
client.interceptors.request.use((req) => {
  if (!req.headers.has('X-MM-Session')) req.headers.set('X-MM-Session', tracker.sessionId());
  return req;
});

const currentView = () => viewOf(window.location.pathname);

// An API call that got no answer at all (the server records every answered error).
// Requests the browser kills while leaving the page are not failures.
let leaving = false;
if (typeof window !== 'undefined') window.addEventListener('pagehide', () => { leaving = true; void tracker.flush(); });
onNoAnswer((code) => {
  if (!leaving) tracker.track('client.network_error', { view: currentView(), code });
});

let installed = false;
function installGlobalHandlers() {
  if (installed || typeof window === 'undefined') return;
  installed = true;
  window.addEventListener('error', (e) => tracker.track('client.error', { view: currentView(), kind: 'uncaught', code: errorCode(e.error ?? e.message) }));
  window.addEventListener('unhandledrejection', (e) => tracker.track('client.error', { view: currentView(), kind: 'rejection', code: errorCode(e.reason) }));
  window.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') void tracker.flush();
  });
  window.setInterval(() => void tracker.flush(), FLUSH_MS);
}

/** Mount once (AppShell): consent → tracker, page views per route change. */
export function useAnalytics() {
  const consent = useQuery(consentQuery());
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  useEffect(installGlobalHandlers, []);
  useEffect(() => {
    if (consent.data) tracker.setConsent(consent.data as Consent);
    else if (consent.isError) tracker.setConsent({ errors: false, usage: false });
  }, [consent.data, consent.isError]);
  useEffect(() => {
    const wide = window.matchMedia?.('(min-width: 48rem)').matches ?? true;
    tracker.track('page.viewed', { view: viewOf(pathname), viewport: wide ? 'wide' : 'narrow' });
  }, [pathname]);
}
