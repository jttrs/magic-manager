// Scraper health (docs/scraper-health.md): which site reads are flagged
// "temporarily down", and how to say so. Pure — the app layer fetches.
import type { ScraperHealthOut } from './api';

export type ScraperHealth = ScraperHealthOut;

export const deckKey = (source: string) => `deck-import/${source}`;
export const CART_KEY = 'companion-cart/manapool';
export const MOXFIELD_READER_KEY = 'companion-deck/moxfield';
export const EDHREC_KEYS = ['edhrec-commander/edhrec', 'edhrec-card/edhrec', 'edhrec-rankings/edhrec'] as const;

/** Companion codes that mean the site's page changed (POST /api/scrapers/report). */
const REPORTABLE_CODES = ['cart.page_changed', 'moxfield.changed'] as const;
export type ReportableCode = (typeof REPORTABLE_CODES)[number];
export const isReportable = (code: string): code is ReportableCode => (REPORTABLE_CODES as readonly string[]).includes(code);

const DECK_HOSTS: [RegExp, string][] = [
  [/(^|\.)moxfield\.com$/i, 'moxfield'],
  [/(^|\.)archidekt\.com$/i, 'archidekt'],
  [/(^|\.)mtggoldfish\.com$/i, 'mtggoldfish'],
  [/(^|\.)manabox\.app$/i, 'manabox'],
  [/(^|\.)scryfall\.com$/i, 'scryfall'],
];

/** The deck builder a pasted link belongs to (mirrors decksource.source_of), or null. */
export function deckSourceOf(url: string): string | null {
  let host: string;
  try {
    host = new URL(url.trim()).hostname;
  } catch {
    return null;
  }
  return DECK_HOSTS.find(([re]) => re.test(host))?.[1] ?? null;
}

/** The down scrapers among `keys`, in the order asked. */
export function downAmong(all: readonly ScraperHealth[] | undefined, keys: readonly string[]): ScraperHealth[] {
  if (!all?.length) return [];
  const byKey = new Map(all.map((h) => [h.key, h]));
  return keys.map((k) => byKey.get(k)).filter((h): h is ScraperHealth => h?.status === 'down');
}

/** A Deals store's health by its vendor key or display name (offers carry the name). */
export function storeHealthLookup(all: readonly ScraperHealth[] | undefined): (keyOrName: string | null | undefined) => ScraperHealth | undefined {
  const m = new Map<string, ScraperHealth>();
  for (const h of all ?? []) {
    if (h.scraper !== 'store-price') continue;
    m.set(h.site, h);
    m.set(h.site_name, h);
  }
  return (k) => (k ? m.get(k) : undefined);
}

const DAY = 86_400_000;

/** "today 6:30 AM", "yesterday 6:30 AM", "Oct 8" — when the flag went up. */
export function sinceText(iso: string | null | undefined, now = new Date()): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const time = d.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' });
  const startOf = (x: Date) => new Date(x.getFullYear(), x.getMonth(), x.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(d)) / DAY);
  if (days <= 0) return `today ${time}`;
  if (days === 1) return `yesterday ${time}`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', ...(d.getFullYear() !== now.getFullYear() ? { year: 'numeric' } : {}) });
}

export type Notice = { title: string; reason: string; meta: string; tip: string };

/** What the notice says for one down scraper. */
export function noticeFor(h: ScraperHealth, now = new Date()): Notice {
  const since = sinceText(h.since, now);
  const found = h.via === 'use' ? 'found while reading' : 'found by the daily check';
  const reason = h.message ?? 'It stopped reading the way it used to.';
  const meta = [since && `Since ${since}`, found, h.code && `Code ${h.code}`].filter(Boolean).join(' · ');
  return {
    title: `${h.label} — temporarily down`,
    reason,
    meta,
    tip: `${h.site_name} is temporarily down: ${reason}${since ? ` Since ${since}.` : ''} You can still try.`,
  };
}
