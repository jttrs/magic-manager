import { useRovingFocus } from '../../app/useRovingFocus';
import { EmptyNote } from '../../components/States';
import type { PurchaseOut, PurchasesOut } from '../../core/api';
import { fmtCount, fmtUsd } from '../../core/format';
import { signedParts, STATUS_LABEL, valuation } from '../../core/purchases';

const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: '2-digit', timeZone: 'UTC' });
const orderDay = (at: string) => {
  const d = new Date(at);
  return Number.isNaN(d.getTime()) ? at.slice(0, 10) : DAY.format(d);
};

/** A signed gain or loss; a loss reads in the danger colour, a gain in plain ink. */
function Gain({ usd, tone = 'paper' }: { usd: number; tone?: 'chrome' | 'paper' }) {
  const { sign, abs } = signedParts(usd);
  return <span className={sign === '−' ? 'text-danger' : tone === 'chrome' ? 'text-on-chrome' : 'text-ink'}>{sign}{fmtUsd(abs)}</span>;
}

/** Worth today or the gain: "—" when no line has a price today; marked "cards" with a tip when only some lines are valued. */
export function Valued({ p, field, tone = 'paper' }: { p: Pick<PurchaseOut, 'paid_usd' | 'compared_paid_usd' | 'worth_usd' | 'gain_usd'>; field: 'worth' | 'gain'; tone?: 'chrome' | 'paper' }) {
  const v = valuation(p);
  if (v.kind === 'none') return <span title="No line in this order has a price today (sealed products and unpriced lines aren’t valued).">—</span>;
  const node = field === 'worth' ? fmtUsd(v.worth) : <Gain usd={v.gain} tone={tone} />;
  if (v.kind === 'full') return <>{node}</>;
  return (
    <span title={`Today’s value of the ${fmtUsd(v.comparedPaid)} of cards with a price today. Sealed products and unpriced lines aren’t valued.`}>
      {node} <span className={`text-xs font-normal ${tone === 'chrome' ? 'text-on-chrome-muted' : 'text-ink-muted'}`}>cards</span>
    </span>
  );
}

/** The totals line for every order read so far (`chrome` on the sidebar). */
export function OrdersTotals({ totals, tone = 'paper' }: { totals: Pick<PurchasesOut, 'paid_usd' | 'compared_paid_usd' | 'worth_usd' | 'gain_usd'>; tone?: 'chrome' | 'paper' }) {
  const dt = `text-xs voice-semi uppercase tracking-[0.06em] ${tone === 'chrome' ? 'text-on-chrome-muted' : 'text-ink-muted'}`;
  const dd = tone === 'chrome' ? 'text-on-chrome' : 'text-ink';
  return (
    <dl className="flex flex-wrap gap-x-5 gap-y-1 text-sm tabular">
      <div className="flex items-baseline gap-1.5"><dt className={dt}>Paid</dt><dd className={dd}>{fmtUsd(totals.paid_usd)}</dd></div>
      <div className="flex items-baseline gap-1.5"><dt className={dt}>Worth today</dt><dd className={dd}><Valued p={totals} field="worth" tone={tone} /></dd></div>
      <div className="flex items-baseline gap-1.5"><dt className={dt}>Gain / loss</dt><dd className="voice-semi font-medium"><Valued p={totals} field="gain" tone={tone} /></dd></div>
    </dl>
  );
}

/** Store orders, newest first: ruled rows with Paid, Worth today and the gain. One tab stop (↑/↓, Home/End). */
export function OrdersList({ data, active, onPick }: { data: PurchasesOut; active?: number; onPick: (id: number) => void }) {
  const keys = data.purchases.map((p) => String(p.purchase_id));
  const { navRef, tabKey, setFocusKey, onKeyDown } = useRovingFocus(keys, active == null ? undefined : String(active), 'data-row');
  if (!data.purchases.length) return <EmptyNote title="No store orders yet">Use “Read my orders” to bring them in.</EmptyNote>;
  return (
    <nav ref={navRef} aria-label="Store orders" onKeyDown={onKeyDown} className="flex h-full min-h-0 flex-col">
      <div className="mx-4 border-b-2 border-rule-strong pb-2 pt-1" aria-label="All orders">
        <OrdersTotals totals={data} />
      </div>
      <ul className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-4 pb-6 [scrollbar-gutter:stable]">
        {data.purchases.map((p) => (
          <li key={p.purchase_id}>
            <OrderRow p={p} active={active === p.purchase_id} tabbable={String(p.purchase_id) === tabKey} onFocus={() => setFocusKey(String(p.purchase_id))} onPick={onPick} />
          </li>
        ))}
      </ul>
    </nav>
  );
}

function OrderRow({ p, active, tabbable, onFocus, onPick }: { p: PurchaseOut; active: boolean; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void }) {
  return (
    <button
      type="button"
      data-row={String(p.purchase_id)}
      tabIndex={tabbable ? 0 : -1}
      onFocus={onFocus}
      onClick={() => onPick(p.purchase_id)}
      aria-current={active ? 'true' : undefined}
      className={`ruled flex w-full cursor-pointer items-center gap-3 px-1 py-2 text-left transition-colors ease-guide hover:bg-paper-sunk ${active ? 'highlighter' : ''}`}
    >
      <time dateTime={p.ordered_at} className="w-16 shrink-0 text-xs tabular text-ink-muted">{orderDay(p.ordered_at)}</time>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-md voice-semi font-medium text-ink">{p.store_name} order #{p.order_id}</span>
        <span className="truncate text-xs text-ink-muted">{STATUS_LABEL[p.status]} · {fmtCount(p.copies, 'copy', 'copies')}</span>
      </span>
      <span className="grid shrink-0 grid-cols-[auto_auto] items-baseline gap-x-3 text-xs tabular">
        <span className="text-right text-ink-muted">Paid</span><span className="text-right text-ink">{fmtUsd(p.paid_usd)}</span>
        <span className="text-right text-ink-muted">Worth</span><span className="text-right text-ink"><Valued p={p} field="worth" /></span>
        <span className="text-right text-ink-muted">Gain</span><span className="text-right"><Valued p={p} field="gain" /></span>
      </span>
    </button>
  );
}
