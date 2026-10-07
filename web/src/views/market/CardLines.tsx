import { useMemo, useState } from 'react';
import type { DeckLineOut } from '../../core/api';
import { fmtInt, fmtUsd } from '../../core/format';

type Unit = 'exact' | 'floor';
type Props = {
  title: string;
  lines: DeckLineOut[];
  /** Which price the caption total uses; leave unset for no total. */
  unitBasis?: Unit;
  /** Caption shows "worth $x" instead of a plain total. */
  worth?: boolean;
  /** Column headers; defaults read as a deck's buy list. */
  labels?: { need: string; exact: string; floor: string };
  /** Price column headers become sort buttons (default: exact, highest first). */
  sortable?: boolean;
};

const DECK_LABELS = { need: 'Need', exact: 'Deck’s printing', floor: 'Cheapest' };
const exactOf = (l: DeckLineOut) => l.unit_usd;
const floorOf = (l: DeckLineOut) => l.floor_usd;

/** A card list with the price of the listed printing beside the cheapest printing anywhere. */
export function CardLines({ title, lines, unitBasis, worth = false, labels = DECK_LABELS, sortable = false }: Props) {
  const [sort, setSort] = useState<{ key: Unit; dir: 1 | -1 }>({ key: 'exact', dir: -1 });
  const rows = useMemo(() => {
    if (!sortable) return lines;
    const pick = sort.key === 'exact' ? exactOf : floorOf;
    return [...lines].sort((a, b) => {
      const x = pick(a), y = pick(b);
      if (x == null || y == null) return x == null ? (y == null ? 0 : 1) : -1;
      return (x - y) * sort.dir || a.name.localeCompare(b.name);
    });
  }, [lines, sortable, sort]);
  if (!lines.length) return null;
  const unit = unitBasis === 'floor' ? floorOf : exactOf;
  const total = lines.reduce((s, l) => s + (unit(l) ?? 0) * (l.buy || l.need), 0);
  const count = lines.reduce((n, l) => n + (unitBasis ? l.buy || l.need : l.need), 0);
  const toggle = (key: Unit) => setSort((s) => (s.key === key ? { key, dir: (s.dir * -1) as 1 | -1 } : { key, dir: -1 }));
  const th = (key: Unit, text: string, cls: string) => (
    <th scope="col" aria-sort={sortable && sort.key === key ? (sort.dir === 1 ? 'ascending' : 'descending') : undefined} className={`${cls} py-1.5 pl-3 text-right font-medium`}>
      {sortable ? (
        <button type="button" onClick={() => toggle(key)} className="cursor-pointer voice-semi hover:text-ink">
          {text}{sort.key === key ? (sort.dir === 1 ? ' ↑' : ' ↓') : ''}
        </button>
      ) : text}
    </th>
  );
  return (
    <table className="w-full border-collapse text-sm tabular">
      <caption className="pb-1 text-left text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
        {title} · {fmtInt(count)}
        {unitBasis && <span className="normal-case tracking-normal"> · {worth ? `worth ${fmtUsd(total)}` : fmtUsd(total)}</span>}
      </caption>
      <thead>
        <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
          <th scope="col" className="py-1.5 pr-3 font-medium">Card</th>
          <th scope="col" className="py-1.5 pl-3 text-right font-medium">{labels.need}</th>
          <th scope="col" className="hidden py-1.5 pl-3 text-right font-medium sm:table-cell">Free</th>
          {th('exact', labels.exact, 'hidden sm:table-cell')}
          {th('floor', labels.floor, '')}
        </tr>
      </thead>
      <tbody>
        {rows.map((l) => (
          <tr key={`${l.scryfall_id}|${l.finish}`} className="border-b border-rule/60">
            <th scope="row" className="py-1.5 pr-3 text-left font-normal">
              <span className="text-ink">{l.name}</span>
              {l.bonus && <span className="ml-2 text-xs voice-semi text-accent-ink" title="Shipped with the drop as its bonus card">bonus</span>}
              <span className="ml-2 text-xs text-ink-muted">{l.set_code.toUpperCase()} {l.collector_number}{l.finish !== 'nonfoil' ? ` · ${l.finish}` : ''}</span>
            </th>
            <td className="py-1.5 pl-3 text-right text-ink">{l.need}</td>
            <td className="hidden py-1.5 pl-3 text-right text-ink-muted sm:table-cell">{l.free || '—'}</td>
            <td className="hidden py-1.5 pl-3 text-right text-ink sm:table-cell">{fmtUsd(l.unit_usd)}</td>
            <td className="py-1.5 pl-3 text-right">
              <span className="text-ink">{fmtUsd(l.floor_usd)}</span>
              {l.floor_set_code && (l.floor_set_code !== l.set_code || l.floor_collector_number !== l.collector_number) && (
                <span className="ml-1.5 hidden text-xs text-ink-muted md:inline">{l.floor_set_code.toUpperCase()} {l.floor_collector_number}</span>
              )}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
