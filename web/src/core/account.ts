// Account view-model (framework-free): download-my-data naming, and the delete
// flow's rules — the typed phrase, the fresh-sign-in window, the way back in.
import { loginHref } from './auth';

/** Typed to confirm a deletion; the server checks the same phrase. */
export const DELETE_PHRASE = 'delete my account';

/** What deleting does, in plain sentences (shown before the typed confirmation). */
export const DELETE_CONSEQUENCES: readonly string[] = [
  'Your collection, decks, wishlist, watchlist, purchase history and restore point are deleted from this server right away.',
  'Your sign-in is removed and you’re signed out everywhere. Invites you made that nobody used stop working.',
  'Error and usage records tied to you are deleted.',
  'The server’s offsite backups keep a copy until they age out on their own schedule (about 30 days).',
  'This can’t be undone. Download your data first if you want to keep it.',
];

/** Does `text` say the phrase? Case and extra spaces don't matter. */
export function confirmMatches(text: string): boolean {
  return text.trim().split(/\s+/).join(' ').toLowerCase() === DELETE_PHRASE;
}

/** Is the sign-in still fresh enough to delete? `secondsLeft` is the server's answer
 *  (server clock) when /me was read at `fetchedAt`; only the time elapsed since is
 *  measured here, so a wrong browser clock can't lock anyone out. */
export function signInFresh(secondsLeft: number | null | undefined, fetchedAt: number, now: number = Date.now()): boolean {
  if (!secondsLeft || secondsLeft <= 0 || !fetchedAt) return false;
  return now - fetchedAt < secondsLeft * 1000;
}

export type ProviderLink = { name: string; title: string; login_url: string };

/** "Sign in again" links: the providers this user is linked to (all configured ones
 *  if none match), each returning to `next`. */
export function reauthLinks(providers: readonly ProviderLink[], linked: readonly string[], next: string): { title: string; href: string }[] {
  const mine = providers.filter((p) => linked.includes(p.name));
  return (mine.length ? mine : providers).map((p) => ({ title: p.title, href: loginHref(p.login_url, null, next) }));
}

/** The download's file name from Content-Disposition, else a dated default. */
export function exportFilename(disposition: string | null | undefined, today: Date = new Date()): string {
  const m = /filename="?([A-Za-z0-9][A-Za-z0-9._-]*\.zip)"?\s*(?:;|$)/.exec(disposition ?? '');
  return m ? m[1] : `magic-manager-export-${today.toISOString().slice(0, 10)}.zip`;
}
