import { ListRow } from '../../components/controls/ListRow';
import type { PurchaseOut } from '../../core/api';
import { fmtCount, fmtUsd } from '../../core/format';
import { orderTitle, type KindMeta } from '../../core/history';
import { signedParts, STATUS_LABEL, valuation } from '../../core/purchases';

const DAY = new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' });
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

type RowProps = { p: PurchaseOut; meta: KindMeta; rowKey: string; active: boolean; tabbable: boolean; onFocus: () => void; onPick: (id: number) => void };

/** A store order in the timeline or under Needs review: store + order number, status, Paid / Worth / gain. */
export function OrderRow({ p, meta, rowKey, active, tabbable, onFocus, onPick }: RowProps) {
  return (
    <ListRow
      data-row={rowKey}
      tabIndex={tabbable ? 0 : -1}
      onFocus={onFocus}
      onClick={() => onPick(p.purchase_id)}
      active={active}
      className="py-2"
    >
      <time dateTime={p.ordered_at} className="w-12 shrink-0 text-xs tabular text-ink-muted">{orderDay(p.ordered_at)}</time>
      <span className="flex min-w-0 flex-1 flex-col">
        <span className="truncate text-md voice-semi font-medium text-ink">{orderTitle(p)}</span>
        <span className="truncate text-xs text-ink-muted">{meta.label('purchase')} · {STATUS_LABEL[p.status]} · {fmtCount(p.copies, 'copy', 'copies')}</span>
      </span>
      <span className="grid shrink-0 grid-cols-[auto_auto] items-baseline gap-x-2 text-xs tabular">
        <span className="text-right text-ink-muted">Paid</span><span className="text-right text-ink">{fmtUsd(p.paid_usd)}</span>
        <span className="text-right text-ink-muted">Worth</span><span className="text-right text-ink"><Valued p={p} field="worth" /></span>
        <span className="text-right text-ink-muted">Gain</span><span className="text-right"><Valued p={p} field="gain" /></span>
      </span>
    </ListRow>
  );
}
