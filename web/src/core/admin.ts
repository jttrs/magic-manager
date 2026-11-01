// Admin page view-model (framework-free): URL state, the people filter, plain-words
// labels for a user's status and last visit, and the three-way flag choice.
import { z } from 'zod';
import type { AdminUserOut, FlagStateOut, OwnerPathOut } from './api';

export const SHOWS = ['all', 'admins', 'members', 'disabled'] as const;
export type Show = (typeof SHOWS)[number];
export const SHOW_LABEL: Record<Show, string> = { all: 'Everyone', admins: 'Admins', members: 'Members', disabled: 'Turned off' };

export const adminSearch = z.object({
  q: z.string().catch('').default(''),
  show: z.enum(SHOWS).catch('all').default('all'),
  /** The person open in the inspector (auth user id). */
  user: z.string().regex(/^[a-z0-9]{16}$/).optional().catch(undefined),
});
export type AdminSearch = z.infer<typeof adminSearch>;

export function filterUsers(users: readonly AdminUserOut[], f: Pick<AdminSearch, 'q' | 'show'>): AdminUserOut[] {
  const q = f.q.trim().toLowerCase();
  return users.filter((u) => {
    if (f.show === 'admins' && !u.is_admin) return false;
    if (f.show === 'members' && u.is_admin) return false;
    if (f.show === 'disabled' && !u.disabled_at) return false;
    return !q || u.display_name.toLowerCase().includes(q) || (u.email ?? '').toLowerCase().includes(q);
  });
}

export function showCounts(users: readonly AdminUserOut[]): Record<Show, number> {
  return {
    all: users.length,
    admins: users.filter((u) => u.is_admin).length,
    members: users.filter((u) => !u.is_admin).length,
    disabled: users.filter((u) => u.disabled_at).length,
  };
}

export const roleLabel = (u: Pick<AdminUserOut, 'is_admin'>) => (u.is_admin ? 'Admin' : 'Member');

const PROVIDER: Record<string, string> = { discord: 'Discord', google: 'Google' };
export const providersLabel = (u: Pick<AdminUserOut, 'providers'>) => u.providers.map((p) => PROVIDER[p] ?? p).join(' · ') || '—';

/** "just now" / "5 min ago" / "3 h ago" / "4 days ago" / a date — or "never". */
export function seenLabel(at: string | null | undefined, now: Date = new Date()): string {
  if (!at) return 'never';
  const t = new Date(at);
  const s = Math.max(0, (now.getTime() - t.getTime()) / 1000);
  if (s < 90) return 'just now';
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 36 * 3600) return `${Math.round(s / 3600)} h ago`;
  if (s < 30 * 86400) return `${Math.round(s / 86400)} days ago`;
  return new Intl.DateTimeFormat('en-US', { dateStyle: 'medium' }).format(t);
}

export function statusLabel(u: Pick<AdminUserOut, 'disabled_at' | 'sessions'>): string {
  if (u.disabled_at) return 'Turned off';
  if (u.sessions === 0) return 'Signed out';
  return u.sessions === 1 ? 'Signed in' : `Signed in on ${u.sessions} browsers`;
}

/** The flag control: follow the server's default, or force on / off for this person. */
export type FlagChoice = 'default' | 'on' | 'off';
export const flagChoice = (f: Pick<FlagStateOut, 'override'>): FlagChoice => (f.override == null ? 'default' : f.override ? 'on' : 'off');
export const choiceValue = (c: FlagChoice): boolean | null => (c === 'default' ? null : c === 'on');
export const defaultChoiceLabel = (f: Pick<FlagStateOut, 'default'>) => `Default · ${f.default ? 'on' : 'off'}`;

const FLAG_TITLE: Record<string, string> = {
  cart_check: 'Cart check',
  deals: 'Deals',
  analytics: 'Analytics dashboard',
  companion: 'Browser companion',
  purchases: 'Store orders',
};
export const flagTitle = (name: string) => FLAG_TITLE[name] ?? name.replace(/_/g, ' ').replace(/^./, (c) => c.toUpperCase());

/** The owner-machine paths inside a flag's surface, by title — admins only, whatever the flag says. */
export function ownerOnlyNote(f: Pick<FlagStateOut, 'owner_paths'>, paths: readonly OwnerPathOut[], isAdmin: boolean): string | null {
  if (!f.owner_paths.length) return null;
  const titles = f.owner_paths.map((k) => paths.find((p) => p.key === k)?.title ?? k);
  return isAdmin ? `Includes owner-only parts (admins have them): ${titles.join('; ')}.` : `Stays owner-only for members: ${titles.join('; ')}.`;
}

/** Paths that aren't inside any flag (e.g. the deck fetch's Moxfield login). */
export const unflaggedPaths = (paths: readonly OwnerPathOut[]) => paths.filter((p) => p.feature == null);

export const INVITE_DAYS = [1, 7, 30] as const;
export const inviteDaysLabel = (d: number) => (d === 1 ? '1 day' : `${d} days`);
