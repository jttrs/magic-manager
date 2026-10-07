import { useQueries, useQuery } from '@tanstack/react-query';
import { useMemo, useRef, type KeyboardEvent } from 'react';
import { productCostQuery, secretLairQuery, watchedQuery } from '../../app/queries';
import { useFeature } from '../../app/features';
import { Button } from '../../components/Button';
import { InfoTip } from '../../components/InfoTip';
import { Segmented, SelectField, SideSection, TextField } from '../../components/Sidebar';
import { EmptyNote, ErrorNote } from '../../components/States';
import type { ProductCostOut } from '../../core/api';
import { fmtInt, fmtUsd } from '../../core/format';
import type { MarketSearch } from '../../core/search';
import { filterSortDrops, SLD_BASIS_LABEL, SLD_LIMITS, sldGap, sldKey, sldRows, type SldBasis, type SldEdition, type SldRow, type SldSort } from '../../core/secretLair';
import { MasterDetail } from './DealsWorkspace';
import type { CostState } from './useDealsData';
import { SldInspector } from './SldInspector';

type Set = (patch: Partial<MarketSearch>) => void;
type SldCosts = { data: Map<string, ProductCostOut | undefined>; state: Map<string, CostState> };

const filtersOf = (s: MarketSearch) => ({ q: s.dq, minOff: s.minOff, basis: s.sbasis, sort: s.ssort });

/** The newest drops at the chosen edition, each drop's worth fetched on its own (rows fill in). */
function useSecretLair(search: MarketSearch) {
  const list = useQuery(secretLairQuery(search.sldN));
  const rows = useMemo(() => sldRows(list.data?.drops ?? [], search.edition), [list.data, search.edition]);
  const results = useQueries({ queries: rows.map((r) => productCostQuery('sld', 'sld', r.name, r.finish)) });
  const costs: SldCosts = { data: new Map(), state: new Map() };
  rows.forEach((r, i) => {
    const q = results[i];
    costs.data.set(r.key, q?.data);
    costs.state.set(r.key, { loading: q?.isPending ?? true, error: q?.isError ? (q.error as Error).message : undefined });
  });
  return { list, rows, costs };
}

/** Keys (`sld|name|finish`) of watched drops → their store links. */
function useWatchedDrops(): Map<string, string[]> {
  const on = useFeature('deals');
  const watched = useQuery({ ...watchedQuery(), enabled: on });
  return useMemo(() => new Map((watched.data ?? []).filter((w) => w.kind === 'sld').map((w) => [sldKey(w.name, w.finish ?? 'nonfoil'), w.stores.map((s) => s.url)])), [watched.data]);
}

/** Sidebar controls for the Secret Lair subject. */
export function SecretLairFind({ search, set }: { search: MarketSearch; set: Set }) {
  const { rows, costs } = useSecretLair(search);
  // A filter change keeps the open drop only while it's still listed (a new edition is a new row).
  const setFilter = (patch: Partial<MarketSearch>) => {
    const kept = !patch.edition && filterSortDrops(rows, costs.data, filtersOf({ ...search, ...patch })).some((r) => r.key === search.item);
    set(search.item && !kept ? { ...patch, item: undefined } : patch);
  };
  return (
    <SideSection title="Find">
      <TextField name="dq" label="Search" value={search.dq} placeholder="Drop name" onChange={(dq) => setFilter({ dq })} />
      <Segmented<SldEdition>
        label="Edition"
        showLabel
        labelExtra={<InfoTip label="Which edition?">Most drops sell as a regular and a foil edition — separate products with their own prices. A drop sold in one edition only shows that one.</InfoTip>}
        value={search.edition}
        onChange={(edition) => setFilter({ edition })}
        options={[{ value: 'nonfoil', label: 'Regular' }, { value: 'foil', label: 'Foil' }]}
      />
      <SelectField<`${(typeof SLD_LIMITS)[number]}`>
        label="Show"
        value={String(search.sldN) as '30'}
        onChange={(v) => setFilter({ sldN: Number(v) })}
        options={SLD_LIMITS.map((n) => ({ value: `${n}` as '30', label: `${n} newest drops` }))}
      />
      <Segmented<'0' | '10' | '20' | '30'>
        label="Discount"
        showLabel
        labelExtra={<InfoTip label="Under what?">How far the sealed price sits under the price chosen in <b>Compare to</b>.</InfoTip>}
        value={String(search.minOff) as '0'}
        onChange={(v) => setFilter({ minOff: Number(v) as 0 })}
        options={[{ value: '0', label: 'Any' }, { value: '10', label: '10%+' }, { value: '20', label: '20%+' }, { value: '30', label: '30%+' }]}
      />
      <Segmented<SldBasis>
        label="Compare to"
        showLabel
        labelExtra={<InfoTip label="What is the sealed price compared to?"><b>Exact</b> is the drop’s cards and its bonus card at their Secret Lair printings. <b>Cheapest</b> is each of those cards at its cheapest printing anywhere — what the cards cost for a deck.</InfoTip>}
        value={search.sbasis}
        onChange={(sbasis) => setFilter({ sbasis })}
        options={[{ value: 'exact', label: 'Exact' }, { value: 'floor', label: 'Cheapest' }]}
      />
      <SelectField<SldSort>
        label="Sort"
        value={search.ssort}
        onChange={(ssort) => setFilter({ ssort })}
        options={[
          { value: 'gap_pct', label: 'Biggest discount %' }, { value: 'gap_usd', label: 'Biggest discount $' },
          { value: 'price', label: 'Lowest sealed price' }, { value: 'release', label: 'Newest' }, { value: 'name', label: 'Name' },
        ]}
      />
    </SideSection>
  );
}

/** Market → Secret Lair: the newest drops, sealed price beside the cards inside, with an inspector. */
export function SecretLairPanel({ search, set }: { search: MarketSearch; set: Set }) {
  const { list, rows, costs } = useSecretLair(search);
  const watched = useWatchedDrops();
  const shown = useMemo(() => filterSortDrops(rows, costs.data, filtersOf(search)), [rows, costs.data, search]);
  const selected = rows.find((r) => r.key === search.item);
  const pricing = rows.filter((r) => costs.state.get(r.key)?.loading).length;
  const body = list.isPending ? (
    <p role="status" className="text-md text-ink-muted">Listing the newest drops…</p>
  ) : list.isError ? (
    <ErrorNote error={list.error} onRetry={() => list.refetch()} />
  ) : rows.length === 0 ? (
    <EmptyNote title="No Secret Lair drops">The drop catalogue came back empty.</EmptyNote>
  ) : shown.length === 0 ? (
    <EmptyNote title="Nothing matches these filters">
      <Button tone="paper" onClick={() => set({ dq: '', minOff: 0 })}>Clear filters</Button>
    </EmptyNote>
  ) : (
    <>
      <p role="status" className="text-sm tabular text-ink-muted">
        {fmtInt(shown.length)} of the {fmtInt(rows.length)} newest drops · compared to {SLD_BASIS_LABEL[search.sbasis]}
        {pricing > 0 && ` · pricing ${fmtInt(pricing)}…`}
      </p>
      <DropTable shown={shown} costs={costs} basis={search.sbasis} watched={watched} item={selected?.key} onPick={(item) => set({ item })} />
      {list.data && list.data.total > rows.length && search.sldN < SLD_LIMITS[SLD_LIMITS.length - 1] && (
        <Button tone="paper" className="self-start" onClick={() => set({ sldN: SLD_LIMITS.find((n) => n > search.sldN) })}>
          Show more drops
        </Button>
      )}
    </>
  );
  const listPane = (
    <div className="flex h-full min-h-0 flex-col gap-3 overflow-y-auto overscroll-contain px-4 pb-8 pt-2 [scrollbar-gutter:stable]">{body}</div>
  );
  const inspector = selected
    ? <SldInspector key={selected.key} row={selected} cost={costs.data.get(selected.key)} costState={costs.state.get(selected.key)} watchedUrls={watched.get(selected.key)} />
    : <EmptyNote title="Pick a drop">Choose a row to see what it’s worth, its bonus card and every card inside.</EmptyNote>;
  return <MasterDetail list={listPane} inspector={inspector} open={selected != null} onBack={() => set({ item: undefined })} backLabel="All drops" splitId="mm.sld.split" />;
}

const TH = 'py-1.5 pl-3 text-right font-medium';

function DropTable({ shown, costs, basis, watched, item, onPick }: { shown: SldRow[]; costs: SldCosts; basis: SldBasis; watched: Map<string, string[]>; item?: string; onPick: (key: string) => void }) {
  const ref = useRef<HTMLTableSectionElement>(null);
  const move = (e: KeyboardEvent<HTMLElement>) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const btns = [...(ref.current?.querySelectorAll<HTMLButtonElement>('button[data-drop]') ?? [])];
    const i = btns.indexOf(document.activeElement as HTMLButtonElement);
    if (i < 0) return;
    e.preventDefault();
    btns[Math.max(0, Math.min(btns.length - 1, i + (e.key === 'ArrowDown' ? 1 : -1)))]?.focus();
  };
  return (
    <div className="@container">
      <table className="w-full border-collapse text-sm tabular">
        <caption className="sr-only">Secret Lair drops</caption>
        <thead>
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="py-1.5 pr-3 font-medium">Drop</th>
            <th scope="col" className={TH}>Sealed</th>
            <th scope="col" className={TH}>Gap</th>
            <th scope="col" className={`${TH} hidden @md:table-cell`}>Cards inside</th>
          </tr>
        </thead>
        <tbody ref={ref} onKeyDown={move}>
          {shown.map((r) => (
            <DropRow key={r.key} r={r} cost={costs.data.get(r.key)} state={costs.state.get(r.key)} basis={basis} watching={watched.has(r.key)} selected={r.key === item} onPick={() => onPick(r.key)} />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function DropRow({ r, cost, state, basis, watching, selected, onPick }: { r: SldRow; cost?: ProductCostOut; state?: CostState; basis: SldBasis; watching: boolean; selected: boolean; onPick: () => void }) {
  const loading = state?.loading === true;
  const dash = <span className="text-ink-muted" title={state?.error}>{loading ? '…' : '—'}</span>;
  const gap = sldGap(cost, basis);
  const pct = gap == null ? null : Math.abs(gap.pct) < 1 ? 'even' : `${gap.pct < 0 ? '−' : '+'}${Math.abs(Math.round(gap.pct))}%`;
  const tone = gap == null || Math.abs(gap.pct) < 1 ? 'text-ink-muted' : gap.pct < 0 ? 'text-accent-ink' : 'text-danger';
  const cards = cost?.[basis];
  const other = basis === 'exact' ? cost?.floor : cost?.exact;
  return (
    <tr
      aria-busy={loading || undefined}
      onClick={(e) => { if (!(e.target as HTMLElement).closest('a')) onPick(); }}
      className="cursor-pointer border-b border-rule/60 align-top transition-colors ease-guide hover:bg-paper-sunk"
    >
      <th scope="row" className="py-2 pr-3 text-left font-normal">
        <button type="button" data-drop onClick={onPick} aria-current={selected ? 'true' : undefined} className="touch-hit min-h-11 cursor-pointer text-left text-md voice-semi font-medium text-ink md:min-h-0">
          <span className={selected ? 'highlighter' : ''}>{r.name}</span>
        </button>
        <span className="block text-xs text-ink-muted">
          {[r.release_date, r.otherEdition && (r.finish === 'foil' ? 'foil only' : 'regular only')].filter(Boolean).join(' · ')}
          {watching && <span className="ml-1.5 text-accent-ink">· watching</span>}
        </span>
      </th>
      <td className="py-2 pl-3 text-right">
        {cost?.market != null ? <span className="text-ink">{fmtUsd(cost.market)}</span> : dash}
      </td>
      <td className="py-2 pl-3 text-right" title={gap ? `Sealed is ${fmtUsd(Math.abs(gap.usd))} ${gap.usd < 0 ? 'under' : 'over'} the ${SLD_BASIS_LABEL[basis]}` : undefined}>
        {gap && pct ? (
          <>
            <span className={`text-md voice-semi font-medium ${tone}`}>{pct}</span>
            <span className="block text-xs text-ink-muted">{fmtUsd(Math.abs(gap.usd))}</span>
          </>
        ) : dash}
      </td>
      <td className="hidden py-2 pl-3 text-right @md:table-cell">
        {cards == null ? dash : (
          <>
            <span className="text-ink">{fmtUsd(cards)}{(cost?.unpriced ?? 0) > 0 && <span aria-hidden="true" className="text-ink-muted">+</span>}</span>
            {(cost?.unpriced ?? 0) > 0 && <span className="block text-xs text-danger">{fmtInt(cost!.unpriced)} of {fmtInt(cost!.total_cards)} unpriced</span>}
            {other != null && <span className="block text-xs text-ink-muted">{basis === 'exact' ? 'cheapest' : 'exact'} {fmtUsd(other)}</span>}
          </>
        )}
      </td>
    </tr>
  );
}
