// Deals view-model: framework-free.

/** One product page's reading (the deals.read_prices job artifact). */
export type PriceRow = {
  url: string;
  vendor: string | null;
  price: number | null;
  currency: string | null;
  available: boolean | null;
  title: string | null;
  signal: string;
  error: string | null;
};

/** The `prices` artifact of a finished read_prices job, keyed by URL. */
export function pricesFrom(artifacts: unknown): Map<string, PriceRow> {
  const art = (artifacts as { label: string; data: PriceRow[] }[] | undefined)?.find((a) => a.label === 'prices');
  return new Map((art?.data ?? []).map((r) => [r.url, r]));
}

/** Errors that apply to the whole read (e.g. Chrome's JavaScript setting), shown once. */
export function sharedErrors(rows: Iterable<PriceRow>): string[] {
  const counts = new Map<string, number>();
  for (const r of rows) if (r.error) counts.set(r.error, (counts.get(r.error) ?? 0) + 1);
  return [...counts].filter(([msg, n]) => n > 1 || /Apple Events/.test(msg)).map(([msg]) => msg);
}

/** "In stock" / "Sold out" / "" (page doesn't say). */
export function stockLabel(r: PriceRow | undefined): string {
  if (!r || r.available == null) return '';
  return r.available ? 'In stock' : 'Sold out';
}
