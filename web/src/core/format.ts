// Locale-aware formatting (Intl, never hand-rolled). Framework-free.
const usd = new Intl.NumberFormat(undefined, { style: 'currency', currency: 'USD' });
const pct = new Intl.NumberFormat(undefined, { maximumFractionDigits: 0 });
const int = new Intl.NumberFormat(undefined);

export const fmtUsd = (v: number | null | undefined): string => (v == null ? '—' : usd.format(v));
export const fmtPct = (v: number | null | undefined): string => (v == null ? '—' : `${pct.format(v)}%`);
export const fmtInt = (v: number | null | undefined): string => (v == null ? '—' : int.format(v));
/** "1 card" / "3 cards" (count formatted). */
export const fmtCount = (n: number, one: string, many = `${one}s`): string => `${int.format(n)} ${n === 1 ? one : many}`;

const day = new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', timeZone: 'UTC' });
/** "Nov 12" from an ISO date or timestamp, read as the date it was stamped (UTC). */
export const fmtDay = (iso: string | null | undefined): string => (iso ? day.format(new Date(`${iso.slice(0, 10)}T00:00:00Z`)) : '—');

/** A Scryfall Tagger slug as words (`gives-evasion` → `gives evasion`); shared by every tag picker. */
export const tagLabel = (slug: string) => slug.replace(/-/g, ' ');
