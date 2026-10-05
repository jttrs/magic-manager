import { useMutation } from '@tanstack/react-query';
import { unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { EmptyNote } from '../../components/States';
import { dealsTabs, type OpenTabsOut, type StoreTabsOut } from '../../core/api';
import { fmtCount, fmtInt } from '../../core/format';

const MODE_NOTE: Record<StoreTabsOut['mode'], string> = {
  shopify: 'price read from the store',
  meta: 'price read from the store',
  rendered: 'price read from your open tab',
};

/** Internal (deals flag): the product pages open in your browser, by store.
 *  Read on demand only — the open-tab set changes under us, so nothing is cached. */
export function DealsPanel() {
  const read = useMutation({ mutationFn: async () => unwrap(await dealsTabs({ query: { browser: 'chrome' } })) });
  const r = read.data;
  return (
    <div className="flex flex-col gap-4 px-5 pt-2">
      <div className="flex flex-wrap items-center gap-3">
        <Button tone="paper" emphasis={r ? 'quiet' : 'primary'} onClick={() => read.mutate()} disabled={read.isPending}>
          {read.isPending ? 'Reading your tabs…' : r ? 'Read again' : 'Read my open tabs'}
        </Button>
        {r && <span className="text-sm tabular text-ink-muted">{fmtInt(r.windows_read)} of {fmtCount(r.windows, 'window')} read</span>}
      </div>
      {read.isError && <p role="alert" className="text-md text-danger">{(read.error as Error).message}</p>}
      {r?.warnings.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
      {!r && !read.isPending && !read.isError && (
        <p className="max-w-[60ch] text-md leading-relaxed text-ink-muted">
          Reads the tabs open in Chrome on this computer and keeps the store product pages. Nothing is opened, closed or changed.
        </p>
      )}
      {r && <Results r={r} />}
    </div>
  );
}

function Results({ r }: { r: OpenTabsOut }) {
  const products = r.stores.reduce((n, s) => n + s.tabs.length, 0);
  if (!products && !r.uncatalogued.length) {
    return r.warnings.length
      ? <EmptyNote title="Couldn’t see your store tabs">Follow the note above, then read again.</EmptyNote>
      : <EmptyNote title="No store pages open">Open product pages from a store, then read again.</EmptyNote>;
  }
  return (
    <div className="flex flex-col gap-5">
      {r.stores.map((s) => (
        <section key={s.key} aria-label={s.name} className="flex flex-col">
          <h2 className="flex items-baseline gap-2 border-b-2 border-rule-strong pb-1 text-lg voice-condensed font-bold text-ink">
            {s.name}
            <span className="text-sm font-normal tabular text-ink-muted">{fmtInt(s.tabs.length)}</span>
            <span className="ml-auto text-xs font-normal text-ink-muted">{MODE_NOTE[s.mode]}{s.no_sales_tax ? ' · no sales tax' : ''}</span>
          </h2>
          <ul>
            {s.tabs.map((t) => (
              <li key={t.url} className="flex items-baseline gap-3 border-b border-rule py-1.5 text-sm">
                <a href={t.url} target="_blank" rel="noreferrer" className="min-w-0 flex-1 truncate text-ink no-underline hover:text-accent-ink">
                  {t.title || t.url}<span className="sr-only"> (opens in a new tab)</span>
                </a>
                <span className="shrink-0 tabular text-ink-muted" title="Prices arrive with each store's recipe">—</span>
              </li>
            ))}
          </ul>
        </section>
      ))}
      {r.uncatalogued.length > 0 && (
        <section aria-label="Stores without a recipe yet" className="flex flex-col gap-1">
          <h2 className="text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">Stores without a recipe yet</h2>
          <ul className="text-sm text-ink">
            {r.uncatalogued.map((u) => <li key={u.host} className="border-b border-rule py-1.5">{u.host} <span className="tabular text-ink-muted">· {fmtCount(u.tabs.length, 'product page')}</span></li>)}
          </ul>
        </section>
      )}
      <p className="text-xs text-ink-muted">
        Also open: {fmtCount(r.store_pages, 'other store page')} (carts, collections) · {fmtCount(r.other, 'other tab')}
        {r.dropped_local ? ` · ${fmtCount(r.dropped_local, 'local tab')} skipped` : ''}
        {r.duplicates ? ` · ${fmtCount(r.duplicates, 'duplicate')}` : ''}
      </p>
    </div>
  );
}
