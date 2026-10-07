import { useMemo } from 'react';
import type { ProductCostOut } from '../../core/api';
import { targetPriceOf, type DealProduct } from '../../core/deals';
import { fmtUsd } from '../../core/format';
import { DASHES, historyChart, type Series } from '../../core/priceHistory';
import { H3 } from './inspectorStyles';

const day = (iso: string) => new Date(iso).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
const stamp = (iso: string) => new Date(iso).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' });

/** Every price seen at each store: one step line per store (the cheapest today solid, the rest dashed),
 *  your target as a highlighter stroke, first / low / high / now per store, and every reading as a table. */
export function PriceHistory({ product: p, cost }: { product: DealProduct; cost?: ProductCostOut }) {
  const target = targetPriceOf(p, cost);
  const chart = useMemo(() => historyChart(p.offers, target), [p.offers, target]);
  return (
    <section aria-labelledby="history-h" className="flex flex-col gap-2">
      <h3 id="history-h" className={H3}>Price history</h3>
      {!chart ? (
        <p className="text-sm text-ink-muted">One price so far. Each time you read watched prices, the new prices are added here.</p>
      ) : (
        <>
          <figure className="m-0 grid grid-cols-[auto_minmax(0,1fr)] gap-x-2 gap-y-1">
            <div aria-hidden="true" className="flex flex-col justify-between text-2xs tabular text-ink-muted">
              <span>{fmtUsd(chart.hi)}</span>
              <span>{fmtUsd(chart.lo)}</span>
            </div>
            <div className="relative h-36 border-b border-l border-rule-strong">
              <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={chart.summary} className="absolute inset-0 size-full overflow-visible">
                {chart.targetY != null && (
                  <line x1="0" x2="100" y1={chart.targetY} y2={chart.targetY} className="stroke-highlight" strokeWidth="7" vectorEffect="non-scaling-stroke" />
                )}
                {[...chart.series].reverse().map((s) => <Line key={s.url} s={s} />)}
              </svg>
              {chart.targetY != null && target != null && (
                <span aria-hidden="true" className="absolute right-1 -translate-y-[115%] text-2xs tabular voice-semi text-accent-ink" style={{ top: `${chart.targetY}%` }}>
                  target {fmtUsd(target)}
                </span>
              )}
            </div>
            <span />
            <div aria-hidden="true" className="flex justify-between text-2xs tabular text-ink-muted">
              <span>{day(chart.from)}</span>
              <span>{day(chart.to)}</span>
            </div>
          </figure>

          <table className="w-full border-collapse text-sm tabular">
            <caption className="sr-only">First, lowest, highest and latest price at each store</caption>
            <thead>
              <tr className="border-b border-rule-strong text-left text-xs voice-semi text-ink-muted">
                <th scope="col" className="py-1 pr-2 font-medium">Store</th>
                <th scope="col" className="py-1 pl-2 text-right font-medium">First</th>
                <th scope="col" className="py-1 pl-2 text-right font-medium">Low</th>
                <th scope="col" className="py-1 pl-2 text-right font-medium">High</th>
                <th scope="col" className="py-1 pl-2 text-right font-medium">Now</th>
              </tr>
            </thead>
            <tbody>
              {chart.series.map((s) => (
                <tr key={s.url} className="border-b border-rule/60">
                  <th scope="row" className="py-1.5 pr-2 text-left font-normal text-ink">
                    <span className="inline-flex items-center gap-2">
                      <Swatch s={s} />
                      <span>{s.store}</span>
                    </span>
                  </th>
                  <td className="py-1.5 pl-2 text-right text-ink-muted">{money(s.first)}</td>
                  <td className="py-1.5 pl-2 text-right text-ink">{money(s.low)}</td>
                  <td className="py-1.5 pl-2 text-right text-ink-muted">{money(s.high)}</td>
                  <td className="py-1.5 pl-2 text-right voice-semi font-medium text-ink">{money(s.now)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <details className="group text-sm">
            <summary className="touch-hit inline-flex min-h-9 cursor-pointer items-center text-accent-ink">All {chart.rows.length} readings</summary>
            <table className="mt-1 w-full border-collapse tabular">
              <caption className="sr-only">Every price read, newest first</caption>
              <thead>
                <tr className="border-b border-rule-strong text-left text-xs voice-semi text-ink-muted">
                  <th scope="col" className="py-1 pr-2 font-medium">When</th>
                  <th scope="col" className="py-1 pr-2 font-medium">Store</th>
                  <th scope="col" className="py-1 pl-2 text-right font-medium">Price</th>
                </tr>
              </thead>
              <tbody>
                {chart.rows.map((r) => (
                  <tr key={`${r.at}|${r.store}`} className="border-b border-rule/60">
                    <td className="py-1 pr-2 text-ink-muted">{stamp(r.at)}</td>
                    <td className="py-1 pr-2 text-ink">{r.store}</td>
                    <td className="py-1 pl-2 text-right text-ink">{fmtUsd(r.price)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}
    </section>
  );
}

const money = (v: number | null) => (v == null ? <span className="text-ink-muted">—</span> : fmtUsd(v));

const stroke = (s: Series) => (s.style === 0 ? 'stroke-ink' : 'stroke-ink-muted');

function Line({ s }: { s: Series }) {
  return (
    <g className={stroke(s)}>
      <path d={s.path} fill="none" strokeWidth={s.style === 0 ? 2 : 1.5} strokeDasharray={DASHES[s.style] || undefined} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
      {s.points.map((pt, i) => (
        <path key={i} d={`M${pt.x} ${pt.y}h0`} strokeWidth={s.style === 0 ? 6 : 5} strokeLinecap="round" vectorEffect="non-scaling-stroke" />
      ))}
    </g>
  );
}

function Swatch({ s }: { s: Series }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 8" className={`h-2 w-6 shrink-0 ${stroke(s)}`}>
      <path d="M0 4H24" fill="none" strokeWidth={s.style === 0 ? 2 : 1.5} strokeDasharray={DASHES[s.style] || undefined} />
    </svg>
  );
}
