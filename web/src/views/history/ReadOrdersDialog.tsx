import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Dialog } from 'radix-ui';
import { useState, type ReactNode } from 'react';
import { purchaseStoresQuery, purchasesQuery, unwrap } from '../../app/queries';
import { useCompanion } from '../../app/useCompanion';
import { Button } from '../../components/Button';
import { AwaitingNote, FailureNote } from '../../components/companion/CompanionNotes';
import { reportScraperFailure, useDownScrapers } from '../../app/scraperHealth';
import { ordersKey } from '../../core/scraperHealth';
import { purchaseSave, type MagicManagerApiPurchasesSaveOut as SaveOut } from '../../core/api';
import { ALLOW_ACCESS_HINT, CompanionError, warningLines, type OrderListData, type OrdersData } from '../../core/companion';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import { chunk, listStatus, STATUS_LABEL, type Store } from '../../core/purchases';
import { VerificationMark } from './StoreVerification';

const STORE_NAME: Record<Store, string> = { manapool: 'Mana Pool', tcgplayer: 'TCGplayer', cardkingdom: 'Card Kingdom' };
const STORE_ORDER: Store[] = ['manapool', 'tcgplayer', 'cardkingdom'];
const BATCH = 100;
const H3 = 'border-b border-rule-strong pb-1 text-md voice-condensed font-bold uppercase tracking-[0.04em] text-ink';
const DAY = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' });
const orderDay = (at: string) => {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at.slice(0, 10) : DAY.format(d);
};

type Saved = { saved: number; skipped: string[]; unresolved: number; purchaseIds: number[]; warnings: string[] };

/** Read your store order history in YOUR browser (companion), choose which orders to bring in,
 *  and save what you paid. Only the orders' lines and prices reach the app. */
export function ReadOrdersDialog({ trigger, onReview }: { trigger: ReactNode; onReview: (purchaseId: number) => void }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(48rem,calc(100dvh-1.5rem))] w-[min(46rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          {open && <ReadOrders onClose={() => setOpen(false)} onReview={(id) => { setOpen(false); onReview(id); }} />}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function ReadOrders({ onClose, onReview }: { onClose: () => void; onReview: (purchaseId: number) => void }) {
  const c = useCompanion();
  const qc = useQueryClient();
  const stores = useQuery(purchaseStoresQuery(true));
  const purchases = useQuery(purchasesQuery(true));
  const [store, setStore] = useState<Store>('manapool');
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [progress, setProgress] = useState<string | null>(null);
  const [list, setList] = useState<OrderListData | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [result, setResult] = useState<Saved | null>(null);

  const info = (s: Store) => stores.data?.find((x) => x.key === s);
  const allowed = (s: Store) => {
    const needs = info(s)?.needs_permission ?? s !== 'manapool';
    if (!needs) return true;
    return c.hello?.features[s === 'tcgplayer' ? 'orders_tcgplayer' : 'orders_cardkingdom'] === true;
  };
  const known = purchases.data?.purchases ?? [];
  const statusOf = (id: string) => listStatus(id, store, known);

  const down = useDownScrapers([ordersKey(store)])[0];
  // A changed store page flags its reader "temporarily down" (docs/scraper-health.md).
  const flagIfChanged = (e: unknown) => { if (e instanceof CompanionError) void reportScraperFailure(e.code, qc, store); };

  const readList = useMutation({
    mutationFn: async () => c.read('order_list', { store }, (s) => setAwaiting(s)),
    onError: flagIfChanged,
    onSuccess: (d) => { setList(d); setPicked(new Set(d.orders.filter((o) => statusOf(o.order_id) === 'unread').map((o) => o.order_id))); },
    onSettled: () => setAwaiting(null),
  });

  const readOrders = useMutation({
    mutationFn: async (ids: string[]) => {
      const batches = chunk(ids, BATCH);
      const total: Saved = { saved: 0, skipped: [], unresolved: 0, purchaseIds: [], warnings: [] };
      for (const [i, batch] of batches.entries()) {
        setProgress(batches.length > 1 ? `Reading orders ${i * BATCH + 1}–${i * BATCH + batch.length} of ${ids.length}…` : `Reading ${fmtCount(batch.length, 'order')}…`);
        const d: OrdersData = await c.read('orders', { store, ids: batch }, (s) => setAwaiting(s));
        setAwaiting(null);
        setProgress('Saving what you paid…');
        const r: SaveOut = unwrap(await purchaseSave({ body: { store, orders: d.orders, warnings: d.warnings } }));
        total.saved += r.saved;
        total.skipped.push(...r.skipped);
        total.unresolved += r.unresolved;
        total.purchaseIds.push(...r.purchase_ids);
        total.warnings.push(...warningLines(d.warnings, c.catalog));
      }
      return total;
    },
    onSuccess: async (r) => {
      setResult({ ...r, warnings: [...new Set(r.warnings)] });
      await Promise.all([qc.invalidateQueries({ queryKey: ['purchases'] }), qc.invalidateQueries({ queryKey: ['history'] })]);
    },
    onError: flagIfChanged,
    onSettled: () => { setAwaiting(null); setProgress(null); },
  });
  const busy = readList.isPending || readOrders.isPending;

  const header = (
    <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
      <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Read my orders</Dialog.Title>
      <Dialog.Description className="text-md leading-relaxed text-ink-muted">
        The companion reads your order history in this browser, signed in as you, and shows you what it will send before anything is saved.
      </Dialog.Description>
    </div>
  );

  if (result) {
    return (
      <>
        {header}
        <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-y-auto px-5 py-4">
          <h3 className={H3}>Done</h3>
          <p role="status" className="text-md text-ink">Saved {fmtCount(result.saved, 'order')}.</p>
          {result.skipped.length > 0 && (
            <p className="text-md text-ink-muted">{fmtCount(result.skipped.length, 'order')} skipped — already in your collection ({result.skipped.join(', ')}).</p>
          )}
          {result.unresolved > 0 && (
            <p className="text-md text-ink-muted">{fmtCount(result.unresolved, 'line')} with no exact printing — recorded only, not added to your collection.</p>
          )}
          {result.warnings.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
        </div>
        <div className="flex justify-end gap-2 border-t border-rule px-5 py-3">
          <Button tone="paper" onClick={onClose}>Close</Button>
          {result.purchaseIds.length > 0 && <Button tone="paper" emphasis="primary" onClick={() => onReview(result.purchaseIds[0])}>Review orders</Button>}
        </div>
      </>
    );
  }

  const toggle = (id: string) => setPicked((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const orders = list?.orders ?? [];
  const unread = orders.filter((o) => statusOf(o.order_id) === 'unread').map((o) => o.order_id);

  return (
    <>
      {header}
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {!list ? (
          <div className="flex flex-col gap-4">
            <fieldset className="flex flex-col gap-1" disabled={busy}>
              <legend className={`${H3} w-full`}>1. Choose a store</legend>
              {STORE_ORDER.map((s) => {
                const ok = allowed(s);
                return (
                  <label key={s} className={`ruled flex cursor-pointer items-start gap-3 px-1 py-2 ${ok ? '' : 'opacity-70'}`}>
                    <input type="radio" name="store" value={s} checked={store === s} onChange={() => setStore(s)} className="mt-1 accent-accent" />
                    <span className="flex min-w-0 flex-1 flex-col gap-0.5">
                      <span className="flex flex-wrap items-center gap-x-3">
                        <span className="text-md voice-semi font-medium text-ink">{STORE_NAME[s]}</span>
                        <VerificationMark store={info(s)} />
                      </span>
                      {info(s) && <span className="max-w-[62ch] text-xs leading-snug text-ink-muted">{info(s)!.note}</span>}
                      {!ok && c.status === 'ready' && <span className="text-xs text-ink">To read {STORE_NAME[s]} orders: {ALLOW_ACCESS_HINT}</span>}
                    </span>
                  </label>
                );
              })}
            </fieldset>
            <section aria-labelledby="ro-read" className="flex flex-col gap-2">
              <h3 id="ro-read" className={H3}>2. Read the order list</h3>
              <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
                {c.status === 'ready'
                  ? `Reads the list of your ${STORE_NAME[store]} orders — dates and totals only. You then choose which orders to read in full.`
                  : c.status === 'checking'
                    ? 'Looking for the browser companion…'
                    : 'Set up the browser companion first — the plug icon at the top of the app.'}
              </p>
              <Button tone="paper" emphasis="primary" className="self-start" disabled={c.status !== 'ready' || !allowed(store) || busy} onClick={() => readList.mutate()}>
                {readList.isPending ? (awaiting != null ? 'Waiting for approval…' : 'Reading your orders…') : 'Read order list'}
              </Button>
              {down && (
                <p role="status" className="max-w-[62ch] text-md leading-relaxed text-ink">
                  Reading {STORE_NAME[store]} orders is temporarily down{down.message ? `: ${down.message}` : '.'}
                </p>
              )}
              {awaiting != null && <AwaitingNote summary={awaiting} />}
              {readList.isError && <FailureNote error={readList.error} />}
            </section>
          </div>
        ) : (
          <div className="flex flex-col gap-3">
            <h3 className={`${H3} flex flex-wrap items-baseline gap-x-3`}>
              3. {STORE_NAME[store]} orders · {fmtInt(orders.length)}
              <span className="normal-case tracking-normal"><VerificationMark store={info(store)} /></span>
            </h3>
            {list.store === 'tcgplayer' && list.range && (
              <p className="text-sm text-ink-muted">Date range on TCGplayer: {list.range}. Pick another year on TCGplayer’s page to read it.</p>
            )}
            {!orders.length ? (
              <p className="text-md text-ink-muted">No orders were found in this list.</p>
            ) : (
              <>
                <div className="flex flex-wrap gap-3 text-sm">
                  <button type="button" disabled={busy} onClick={() => setPicked(new Set(unread))} className="cursor-pointer text-accent-ink underline underline-offset-2 disabled:opacity-45">Select unread</button>
                  <button type="button" disabled={busy} onClick={() => setPicked(new Set(orders.map((o) => o.order_id)))} className="cursor-pointer text-accent-ink underline underline-offset-2 disabled:opacity-45">Select all</button>
                  <button type="button" disabled={busy} onClick={() => setPicked(new Set())} className="cursor-pointer text-ink-muted underline underline-offset-2 disabled:opacity-45">Select none</button>
                </div>
                <ul className="flex flex-col">
                  {orders.map((o) => {
                    const st = statusOf(o.order_id);
                    return (
                      <li key={o.order_id}>
                        <label className="ruled flex cursor-pointer items-center gap-3 px-1 py-1.5 text-sm">
                          <input type="checkbox" checked={picked.has(o.order_id)} onChange={() => toggle(o.order_id)} disabled={busy} className="accent-accent" />
                          <span className="w-28 shrink-0 text-xs tabular text-ink-muted">{orderDay(o.ordered_at)}</span>
                          <span className="min-w-0 flex-1 truncate text-ink">Order #{o.order_id}</span>
                          <span className={`shrink-0 text-xs ${st === 'unread' ? 'text-ink-muted' : 'voice-semi text-ink'}`}>{st === 'unread' ? 'Not read yet' : `Read · ${STATUS_LABEL[st]}`}</span>
                          <span className="w-20 shrink-0 text-right tabular text-ink">{fmtUsd(o.total)}</span>
                        </label>
                      </li>
                    );
                  })}
                </ul>
              </>
            )}
            {awaiting != null && <AwaitingNote summary={awaiting} />}
            {/* Always mounted so screen readers announce each batch as it changes. */}
            <p role="status" aria-live="polite" className={progress ? 'text-sm text-ink-muted' : 'sr-only'}>{progress}</p>
            {readOrders.isError && <FailureNote error={readOrders.error} />}
          </div>
        )}
      </div>
      {list && (
        <div className="flex flex-wrap justify-end gap-2 border-t border-rule px-5 py-3">
          <Button tone="paper" disabled={busy} onClick={() => { setList(null); readOrders.reset(); readList.reset(); }}>Back</Button>
          <Button tone="paper" disabled={busy || !orders.length} onClick={() => readOrders.mutate(orders.map((o) => o.order_id))}>Read all</Button>
          <Button tone="paper" emphasis="primary" disabled={busy || picked.size === 0} onClick={() => readOrders.mutate(orders.map((o) => o.order_id).filter((id) => picked.has(id)))}>
            {readOrders.isPending ? 'Reading…' : `Read ${fmtCount(picked.size, 'order')}`}
          </Button>
        </div>
      )}
    </>
  );
}
