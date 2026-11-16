import type { ReactNode } from 'react';
import { InfoTip } from '../../components/InfoTip';
import { fmtInt, fmtUsd } from '../../core/format';
import { basisColumn } from '../../core/secretLair';

export type CardValues = { exact?: number | null; floor?: number | null; unpriced?: number; floorUnpriced?: number; total?: number };

const TH = 'py-1.5 pl-3 text-right font-medium';
const EXACT_CLS = 'hidden @md:table-cell';
const FLOOR_CLS = 'hidden @lg:table-cell';

function Head({ text, marked, tip, cls }: { text: string; marked: boolean; tip?: ReactNode; cls: string }) {
  return (
    <th scope="col" className={`${TH} ${cls}`}>
      <span className="inline-flex items-center gap-0.5">
        {tip && <InfoTip tone="paper" label={`About ${text}`}>{tip}</InfoTip>}
        <span className={marked ? 'text-accent-ink underline decoration-2 underline-offset-4' : ''} title={marked ? 'The Gap is measured against this column' : undefined}>
          {text}{marked && <span className="sr-only"> (the Gap is measured against this)</span>}
        </span>
      </span>
    </th>
  );
}

/** The two value column headers — Exact, Cheapest — the Gap's compared column marked. */
export function CardValueHeads({ basis, exactTip, floorTip }: { basis: string; exactTip?: ReactNode; floorTip?: ReactNode }) {
  const marked = basisColumn(basis);
  return (
    <>
      <Head text="Exact" marked={marked === 'exact'} tip={exactTip} cls={EXACT_CLS} />
      <Head text="Cheapest" marked={marked === 'floor'} tip={floorTip} cls={FLOOR_CLS} />
    </>
  );
}

function Value({ v, unpriced, total, empty }: { v: number | null | undefined; unpriced?: number; total?: number; empty: ReactNode }) {
  if (v == null) return <>{empty}</>;
  const n = unpriced ?? 0;
  return (
    <>
      <span className="text-ink">{fmtUsd(v)}{n > 0 && <span aria-hidden="true" className="text-ink-muted">+</span>}</span>
      {n > 0 && <span className="block text-xs text-danger">{fmtInt(n)} of {fmtInt(total)} unpriced</span>}
    </>
  );
}

/** The two value cells for one row. `empty` stands in for a missing value; `note` sits under the Exact total. */
export function CardValueCells({ values, empty, note }: { values?: CardValues; empty: ReactNode; note?: ReactNode }) {
  return (
    <>
      <td className={`py-2 pl-3 text-right ${EXACT_CLS}`}>
        <Value v={values?.exact} unpriced={values?.unpriced} total={values?.total} empty={empty} />
        {values?.exact != null && note}
      </td>
      <td className={`py-2 pl-3 text-right ${FLOOR_CLS}`}>
        <Value v={values?.floor} unpriced={values?.floorUnpriced} total={values?.total} empty={empty} />
      </td>
    </>
  );
}
