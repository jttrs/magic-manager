import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { purchaseReviewQuery, purchaseStoresQuery, unwrap } from '../../app/queries';
import { useFeature } from '../../app/features';
import { Button } from '../../components/Button';
import { Chevron } from '../../components/Chevron';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { FailureNote } from '../../components/companion/CompanionNotes';
import { GridSkeleton, ErrorNote } from '../../components/States';
import { purchaseApply, purchaseForget, type ReviewLineOut } from '../../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import { clampDecision, decisionsBody, decisionTotals, defaultDecisions, isAssignable, STATUS_LABEL, subtotalGap, type Decision, type Decisions } from '../../core/purchases';
import { Gain } from './OrdersList';
import { VerificationMark } from './StoreVerification';

const FULL = new Intl.DateTimeFormat('en-US', { dateStyle: 'medium', timeZone: 'UTC' });
const orderDate = (at: string) => {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at.slice(0, 10) : FULL.format(d);
};

/** One store order: what you paid, what it is worth, and — line by line — which copies you already own
 *  (match) and which are new (add). Nothing changes until "Save to collection". */
export function OrderReview({ purchaseId, onBack, onForgotten }: { purchaseId: number; onBack?: () => void; onForgotten: () => void }) {
  const on = useFeature('purchases');
  const q = useQuery(purchaseReviewQuery(purchaseId, on));
  const stores = useQuery(purchaseStoresQuery(on));
  const qc = useQueryClient();
  const [decisions, setDecisions] = useState<Decisions>({});
  const [confirmForget, setConfirmForget] = useState(false);
  const [saved, setSaved] = useState<{ matched: number; added: number } | null>(null);

  const refresh = () => Promise.all([qc.invalidateQueries({ queryKey: ['purchases'] }), qc.invalidateQueries({ queryKey: ['history'] }), qc.invalidateQueries({ queryKey: ['collection'] })]);
  const apply = useMutation({
    mutationFn: async (body: ReturnType<typeof decisionsBody>) => unwrap(await purchaseApply({ path: { purchase_id: purchaseId }, body: { lines: body } })),
    onSuccess: async (r) => {
      setSaved({ matched: r.matched, added: r.added });
      setDecisions({});
      await refresh();
    },
  });

  if (q.isPending) return <GridSkeleton label="Loading order…" />;
  if (q.isError) return <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  const { purchase: p, lines } = q.data;
  const store = stores.data?.find((s) => s.key === p.store);
  const totals = decisionTotals(lines, decisions);
  const nothingChosen = totals.matched + totals.added === 0;
  const setLine = (l: ReviewLineOut, patch: Partial<Decision>) => {
    setSaved(null);
    setDecisions((d) => ({ ...d, [l.line_no]: clampDecision(l, { ...(d[l.line_no] ?? { match: 0, add: 0 }), ...patch }) }));
  };
  const fill = (mode: 'match' | 'add') => { setSaved(null); apply.reset(); setDecisions(defaultDecisions(lines, mode)); };

  return (
    <section aria-labelledby="order-h" className="flex h-full min-h-0 flex-col">
      <header className="mx-4 flex flex-col gap-2 border-b-2 border-rule-strong pb-2 pt-1">
        {onBack && (
          <button type="button" onClick={onBack} className="inline-flex w-full cursor-pointer items-center gap-0.5 text-sm voice-semi text-accent-ink">
            <Chevron dir="left" className="size-3.5" /> All orders
          </button>
        )}
        <div className="flex flex-wrap items-end gap-x-4 gap-y-1">
          <div className="min-w-0">
            <h2 id="order-h" className="text-2xl voice-condensed font-bold uppercase leading-none text-ink">{p.store_name} order #{p.order_id}</h2>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 text-sm text-ink-muted">
              <span>{orderDate(p.ordered_at)} · {STATUS_LABEL[p.status]} · {fmtCount(p.copies, 'copy', 'copies')}</span>
              <VerificationMark store={store} />
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
          <Fact label="Worth today" value={fmtUsd(p.worth_usd)} strong />
          <Fact label="Gain" value={<Gain usd={p.gain_usd} />} strong />
        </dl>
        {subtotalGap(p) != null && (
          <p className="max-w-[70ch] text-sm leading-snug text-ink">
            The store’s item list adds up to {fmtUsd(p.paid_usd)}, but its subtotal is {fmtUsd(p.subtotal_usd)} — replacements or refunds aren’t priced exactly. Per-card prices are as the store lists them.
          </p>
        )}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <Button tone="paper" onClick={() => fill('match')}>Match to cards I own</Button>
          <Button tone="paper" onClick={() => fill('add')}>Add all as new</Button>
          <span className="text-xs text-ink-muted">Fills the boxes below; change any line, then save.</span>
        </div>
      </header>

      <div className="min-h-0 flex-1 overflow-auto px-4 pb-4">
        <table className="w-full min-w-[44rem] border-collapse text-sm">
          <caption className="sr-only">Lines of {p.store_name} order {p.order_id}</caption>
          <thead>
            <tr className="border-b border-rule-strong text-left text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">
              <th scope="col" className="sticky top-0 bg-paper py-1.5 pr-2 font-medium">Card</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Qty</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Paid each</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Today each</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Owned</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Can match</th>
              <th scope="col" className="sticky top-0 bg-paper px-2 py-1.5 text-right font-medium">Match</th>
              <th scope="col" className="sticky top-0 bg-paper py-1.5 pl-2 text-right font-medium">Add</th>
            </tr>
          </thead>
          <tbody className="tabular">
            {lines.map((l) => (
              <LineRow key={l.line_no} l={l} d={decisions[l.line_no]} onChange={(patch) => setLine(l, patch)} />
            ))}
          </tbody>
        </table>
      </div>

      <footer className="mx-4 flex flex-col gap-2 border-t border-rule py-3">
        <div className="flex flex-wrap items-center gap-3">
          <Button tone="paper" emphasis="primary" disabled={nothingChosen || apply.isPending} onClick={() => apply.mutate(decisionsBody(decisions))}>
            {apply.isPending ? 'Saving…' : 'Save to collection'}
          </Button>
          <p role="status" className="text-sm text-ink">
            {saved
              ? `Saved: matched ${fmtCount(saved.matched, 'copy', 'copies')}, added ${fmtInt(saved.added)} new.`
              : nothingChosen
                ? 'Nothing chosen yet.'
                : `Matches ${fmtCount(totals.matched, 'copy', 'copies')} you own, adds ${fmtInt(totals.added)} new · ${fmtUsd(totals.paid)} paid for them.`}
          </p>
          {p.assigned === 0 && (
            <button type="button" onClick={() => setConfirmForget(true)} className="ml-auto cursor-pointer text-sm text-ink-muted underline hover:text-ink">
              Forget this order
            </button>
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

function LineRow({ l, d, onChange }: { l: ReviewLineOut; d: Decision | undefined; onChange: (patch: Partial<Decision>) => void }) {
  const assignable = isAssignable(l);
  const set = [l.printing ? l.printing.set_name ?? l.printing.set_code.toUpperCase() : l.set_name, l.finish === 'nonfoil' ? null : l.finish, l.condition].filter(Boolean).join(' · ');
  const done = l.matched + l.added;
  const recordedOnly = l.kind !== 'single' || l.printing == null;
  return (
    <tr className="ruled border-b border-rule align-top">
      <th scope="row" className="py-1.5 pr-2 text-left font-normal">
        <span className="block text-md voice-semi font-medium text-ink">{l.name}</span>
        <span className="block text-xs text-ink-muted">{set}</span>
        {done > 0 && <span className="block text-xs text-ink-muted">Already assigned: {fmtInt(l.matched)} matched, {fmtInt(l.added)} added</span>}
        {recordedOnly && <span className="block text-xs text-ink">Recorded only — not added to your collection</span>}
      </th>
      <td className="px-2 py-1.5 text-right text-ink">{fmtInt(l.quantity)}</td>
      <td className="px-2 py-1.5 text-right text-ink">{fmtUsd(l.unit_usd)}</td>
      <td className="px-2 py-1.5 text-right text-ink-muted">{fmtUsd(l.today_usd)}</td>
      <td className="px-2 py-1.5 text-right text-ink-muted">{assignable ? fmtInt(l.owned) : '—'}</td>
      <td className="px-2 py-1.5 text-right text-ink-muted">{assignable ? fmtInt(l.matchable) : '—'}</td>
      <td className="px-2 py-1">{assignable ? <Count label={`Match ${l.name}`} value={d?.match ?? 0} max={Math.min(l.remaining, l.matchable)} onChange={(match) => onChange({ match })} /> : null}</td>
      <td className="py-1 pl-2">{assignable ? <Count label={`Add ${l.name}`} value={d?.add ?? 0} max={l.remaining - (d?.match ?? 0)} onChange={(add) => onChange({ add })} /> : null}</td>
    </tr>
  );
}

function Count({ label, value, max, onChange }: { label: string; value: number; max: number; onChange: (n: number) => void }) {
  return (
    <input
      type="number"
      inputMode="numeric"
      aria-label={label}
      min={0}
      max={Math.max(0, max)}
      value={value}
      onChange={(e) => onChange(e.target.valueAsNumber)}
      className="ml-auto block h-8 w-14 rounded-sm border border-rule-strong bg-paper-raised px-2 text-right text-sm tabular text-ink focus-visible:border-accent"
    />
  );
}

function Fact({ label, value, strong = false }: { label: string; value: ReactNode; strong?: boolean }) {
  return (
    <div className="flex items-baseline gap-1.5">
      <dt className="text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">{label}</dt>
      <dd className={strong ? 'voice-semi font-medium text-ink' : 'text-ink'}>{value}</dd>
    </div>
  );
}
