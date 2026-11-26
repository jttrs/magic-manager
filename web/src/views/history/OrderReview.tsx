import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { purchaseReviewQuery, purchaseStoresQuery, unwrap } from '../../app/queries';
import { useFeature } from '../../app/features';
import { Button } from '../../components/Button';
import { Pressable } from '../../components/controls/Pressable';
import { Chevron } from '../../components/icons/Chevron';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { FailureNote } from '../../components/companion/CompanionNotes';
import { GridSkeleton, ErrorNote } from '../../components/States';
import { purchaseApply, purchaseForget, type ReviewLineOut } from '../../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import { addableCopies, addableOwnedLines, STATUS_LABEL, subtotalGap } from '../../core/purchases';
import { Valued } from './OrderRow';
import { VerificationMark } from './StoreVerification';

const FULL = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' });
const orderDate = (at: string) => {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at.slice(0, 10) : FULL.format(d);
};

/** One store order: what you paid and what it is worth, its lines read-only, and one button that adds
 *  every single card of the order to your collection. Nothing changes until you press it. */
export function OrderReview({ purchaseId, onBack, onForgotten, onOpenEntry }: { purchaseId: number; onBack?: () => void; onForgotten: () => void; /** Opens the order's ledger entry (the cards it added so far). */ onOpenEntry?: (ingestId: number) => void }) {
  const on = useFeature('purchases');
  const q = useQuery(purchaseReviewQuery(purchaseId, on));
  const stores = useQuery(purchaseStoresQuery(on));
  const qc = useQueryClient();
  const [confirmForget, setConfirmForget] = useState(false);
  const [saved, setSaved] = useState<{ added: number } | null>(null);

  const refresh = () => Promise.all(['purchases', 'history', 'collection', 'holdings', 'undo'].map((k) => qc.invalidateQueries({ queryKey: [k] })));
  const apply = useMutation({
    mutationFn: async () => unwrap(await purchaseApply({ path: { purchase_id: purchaseId } })),
    onSuccess: async (r) => {
      setSaved({ added: r.added });
      await refresh();
    },
  });

  if (q.isPending) return <GridSkeleton label="Loading order…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { purchase: p, lines } = q.data;
  const store = stores.data?.find((s) => s.key === p.store);
  const addable = addableCopies(lines);
  const alreadyOwned = addableOwnedLines(lines);

  return (
    <section aria-labelledby="order-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <Pressable onClick={onBack} className="inline-flex w-full items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> Purchase history
          </Pressable>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div className="min-w-0">
            <h2 id="order-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{p.store_name} order #{p.order_id}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 text-sm text-ink-muted">
              <span>{orderDate(p.ordered_at)} · {STATUS_LABEL[p.status]} · {fmtCount(p.copies, 'copy', 'copies')}</span>
              <VerificationMark store={store} />
              {onOpenEntry && p.ingest_id != null && (
                <Button tone="paper" emphasis="nav" onClick={() => onOpenEntry(p.ingest_id!)} className="-my-1 py-1">
                  See the cards it added
                </Button>
              )}
            </p>
          </div>
        </div>
        <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm tabular">
          <Fact label="Items paid" value={fmtUsd(p.paid_usd)} />
          {p.subtotal_usd != null && <Fact label="Store subtotal" value={fmtUsd(p.subtotal_usd)} />}
          {p.shipping_usd != null && <Fact label="Shipping" value={fmtUsd(p.shipping_usd)} />}
          {p.tax_usd != null && <Fact label="Tax" value={fmtUsd(p.tax_usd)} />}
          {p.fees_usd != null && <Fact label="Fees" value={fmtUsd(p.fees_usd)} />}
          {p.credit_usd != null && <Fact label="Store credit" value={fmtUsd(p.credit_usd)} />}
          {p.total_usd != null && <Fact label="Order total" value={fmtUsd(p.total_usd)} />}
          <Fact label="Worth today" value={<Valued p={p} field="worth" />} strong />
          <Fact label="Gain" value={<Valued p={p} field="gain" />} strong />
        </dl>
        {subtotalGap(p) != null && (
          <p className="max-w-measure-wide text-sm leading-snug text-ink">
            The store’s item list adds up to {fmtUsd(p.paid_usd)}, but its subtotal is {fmtUsd(p.subtotal_usd)} — replacements or refunds aren’t priced exactly. Per-card prices are as the store lists them.
          </p>
        )}
      </header>

      <div className="@container min-h-0 flex-1 overflow-y-auto overflow-x-hidden px-4 pb-4">
        <div role="table" aria-label={`Lines of ${p.store_name} order ${p.order_id}`} className="tabular text-sm">
          <div role="row" aria-hidden="true" className={`${COLS} sticky top-0 z-10 hidden border-b border-rule-strong bg-paper py-1.5 text-xs voice-semi uppercase tracking-caps text-ink-muted @[42rem]:grid`}>
            <span>Card</span><span className="text-right">Qty</span><span className="text-right">Paid each</span><span className="text-right">Worth today</span>
          </div>
          {lines.map((l) => (
            <LineRow key={l.line_no} l={l} />
          ))}
        </div>
      </div>

      <footer className="mx-4 flex flex-col gap-2 border-t border-rule py-3">
        {alreadyOwned > 0 && addable > 0 && !saved && (
          <p role="note" className="max-w-measure-wide text-sm text-ink">
            You already own copies of {fmtInt(alreadyOwned)} of these cards. Adding counts them again — skip this if you entered them by hand.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-3">
          {addable > 0 ? (
            <Button tone="paper" emphasis="primary" disabled={apply.isPending} onClick={() => apply.mutate()}>
              {apply.isPending ? 'Adding…' : `Add ${fmtCount(addable, 'card', 'cards')} to your collection`}
            </Button>
          ) : null}
          <p role="status" className="text-sm text-ink">
            {saved
              ? `Added ${fmtCount(saved.added, 'card', 'cards')} to your collection.`
              : addable > 0
                ? 'Adds every single card from this order that hasn’t been added yet.'
                : p.assigned > 0
                  ? 'In your collection.'
                  : 'Recorded — sealed products aren’t added as cards.'}
          </p>
          {p.assigned === 0 && (
            <Button tone="paper" emphasis="link" onClick={() => setConfirmForget(true)} className="ml-auto text-sm">
              Forget this order
            </Button>
          )}
        </div>
        {apply.isError && <FailureNote error={apply.error} />}
      </footer>

      <ConfirmDialog
        open={confirmForget}
        onOpenChange={setConfirmForget}
        title="Forget this order?"
        confirmLabel="Forget order"
        onConfirm={async () => {
          unwrap(await purchaseForget({ path: { purchase_id: purchaseId } }));
          await refresh();
          onForgotten();
        }}
      >
        <p>Removes {p.store_name} order #{p.order_id} from your order history. Your collection is not changed. You can read it again later.</p>
      </ConfirmDialog>
    </section>
  );
}

// Wide panes: one row of columns. Narrow panes: the card name, then its numbers beneath.
const COLS = '@[42rem]:grid-cols-[minmax(0,1fr)_2.5rem_4.5rem_5rem] @[42rem]:gap-x-2';
const KIND_NOTE = { single: null, sealed: 'Sealed product', other: 'Other item' } as const;

function Cell({ label, children, className = '' }: { label: string; children: ReactNode; className?: string }) {
  return (
    <span role="cell" className={`flex flex-col @[42rem]:block @[42rem]:text-right ${className}`}>
      <span className="text-2xs voice-semi uppercase tracking-caps text-ink-muted @[42rem]:sr-only">{label}</span>
      {children}
    </span>
  );
}

function LineRow({ l }: { l: ReviewLineOut }) {
  const set = [l.printing ? l.printing.set_name ?? l.printing.set_code.toUpperCase() : l.set_name, l.finish === 'nonfoil' ? null : l.finish, l.condition].filter(Boolean).join(' · ');
  const note = l.kind === 'single' ? (l.printing == null ? 'Single card — exact printing not found, recorded only' : null) : `${KIND_NOTE[l.kind]} — recorded only, not added as a card`;
  const worth = l.today_usd == null ? null : l.today_usd * l.quantity;
  return (
    <div role="row" className={`${COLS} ruled grid grid-cols-3 items-start gap-x-3 gap-y-1.5 border-b border-rule py-2`}>
      <span role="cell" className="col-span-full min-w-0 @[42rem]:col-span-1">
        <span className="block text-md voice-semi font-medium text-ink">{l.name}</span>
        {set && <span className="block text-xs text-ink-muted">{set}</span>}
        {note && <span className="block text-xs text-ink">{note}</span>}
        {l.kind === 'single' && l.printing != null && l.owned > 0 && <span className="block text-xs text-ink-muted">you own {fmtInt(l.owned)}</span>}
      </span>
      <Cell label="Qty" className="text-ink">{fmtInt(l.quantity)}</Cell>
      <Cell label="Paid each" className="text-ink">{fmtUsd(l.unit_usd)}</Cell>
      <Cell label="Worth today" className="text-ink-muted">{fmtUsd(worth)}</Cell>
    </div>
  );
}

function Fact({ label, value, strong = false }: { label: string; value: ReactNode; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs voice-semi uppercase tracking-caps text-ink-muted">{label}</dt>
      <dd className={strong ? 'voice-semi font-medium text-ink' : 'text-ink'}>{value}</dd>
    </div>
  );
}
