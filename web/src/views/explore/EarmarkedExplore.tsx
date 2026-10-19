import { useQuery } from '@tanstack/react-query';
import { useMemo, useState, type ReactNode } from 'react';
import { cardEarmarksQuery } from '../../app/queries';
import { useSelection } from '../../app/selection';
import { ViewLayout } from '../../components/AppShell';
import { CardArt } from '../../components/CardFace';
import { CardInspector } from '../../components/CardInspector';
import { CopyButton } from '../../components/CopyButton';
import { Segmented, SelectField, SideSection, TextField } from '../../components/Sidebar';
import { EmptyNote, ErrorNote, GridSkeleton, GuideSheet } from '../../components/States';
import { VirtualGuide } from '../../components/VirtualGuide';
import type { EarmarkEntryOut } from '../../core/api';
import { earmarkCard, earmarkDecks, earmarkLine, earmarkSections, filterEarmarks } from '../../core/cardEarmarks';
import { fmtInt } from '../../core/format';
import { exportLines, type GuideCard } from '../../core/guideCard';
import { OWN_LABEL } from '../../core/rankings';
import { EARMARK_REASONS, RANK_OWN, type CompareSearch, type EarmarkReasonFilter, type RankOwn } from '../../core/search';
import { SurfSection } from './ExploreTabs';

type Props = { search: CompareSearch; set: (p: Partial<CompareSearch>) => void; tabs: ReactNode };

const REASON_FILTER_LABEL: Record<EarmarkReasonFilter, string> = { all: 'Any', collect: 'To collect', deck: 'Deck idea', none: 'No reason' };

/** Explore → Earmarked: the cards you earmarked (owned or not) — to collect or as
 *  deck ideas — grouped by why, narrowed by reason, deck, ownership and name.
 *  Earmark or change one from any card's inspector. */
export function EarmarkedExplore({ search, set, tabs }: Props) {
  const q = useQuery(cardEarmarksQuery());
  const { selected, toggle, clear } = useSelection('explore-earmarked');
  const [inspecting, setInspecting] = useState<GuideCard | null>(null);
  const all = useMemo(() => q.data ?? [], [q.data]);
  const decks = useMemo(() => earmarkDecks(all), [all]);
  const shown = useMemo(
    () => filterEarmarks(all, { reason: search.er === 'all' ? undefined : search.er, deck: search.ed, own: search.own, q: search.rq }),
    [all, search.er, search.ed, search.own, search.rq],
  );
  const sections = useMemo(() => earmarkSections(shown), [shown]);
  const cards = sections.flatMap((s) => s.items);
  const marked = cards.filter((c) => selected.has(c.key));

  const sidebar = (
    <>
      <SideSection title="Find">
        <TextField name="rq" label="Card name or note" value={search.rq} placeholder="e.g. Sentinel…" onChange={(rq) => set({ rq })} />
      </SideSection>
      <SideSection title="Show">
        <SelectField<EarmarkReasonFilter> label="Why" value={search.er} onChange={(er) => set({ er })} options={EARMARK_REASONS.map((r) => ({ value: r, label: REASON_FILTER_LABEL[r] }))} />
        {decks.length > 0 && (
          <SelectField<string>
            label="For deck"
            value={search.ed ?? ''}
            onChange={(ed) => set({ ed: ed || undefined })}
            options={[{ value: '', label: 'Any deck' }, ...decks.map((d) => ({ value: d.slug, label: d.name }))]}
          />
        )}
        <Segmented<RankOwn> label="Ownership" showLabel value={search.own} onChange={(own) => set({ own })} options={RANK_OWN.map((o) => ({ value: o, label: OWN_LABEL[o] }))} />
      </SideSection>
      <SideSection title="Arrange">
        <Segmented label="View type" showLabel value={search.rview} onChange={(rview) => set({ rview })} options={[{ value: 'grid', label: 'Grid' }, { value: 'list', label: 'List' }]} />
      </SideSection>
      <SideSection title={`Marked · ${marked.length}`}>
        <CopyButton label="Copy marked as list" emphasis="primary" getText={() => exportLines(marked, 'plain')} />
        {selected.size > 0 && (
          <button type="button" onClick={clear} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">Clear marks</button>
        )}
      </SideSection>
      <SurfSection />
    </>
  );

  let body: ReactNode;
  if (q.isPending) body = <GridSkeleton label="Reading your earmarked cards…" />;
  else if (q.isError) body = <ErrorNote error={q.error} onRetry={() => q.refetch()} />;
  else if (!all.length) {
    body = (
      <EmptyNote title="No earmarked cards yet">
        Open any card — in Collection, Explore, a deck or Random cards — and press Earmark. Say whether it’s one to collect or a deck idea; it shows here and in the deck editor.
      </EmptyNote>
    );
  } else if (!shown.length) body = <EmptyNote title="Nothing matches">Loosen the filters in the sidebar.</EmptyNote>;
  else if (search.rview === 'grid') {
    body = <VirtualGuide sections={sections.map((s) => ({ ...s, level: 2, noun: 'group' }))} density="grid" selected={selected} onToggle={toggle} label="Earmarked cards" />;
  } else {
    body = <EarmarkList rows={shown} onInspect={setInspecting} />;
  }

  return (
    <ViewLayout label="Explore controls" summary="Earmarked" sidebar={sidebar}>
      <GuideSheet nav={tabs} title="Earmarked" summary={q.data ? `${fmtInt(shown.length)} of ${fmtInt(all.length)} cards` : undefined}>
        <div className="h-full min-h-0">{body}</div>
      </GuideSheet>
      <CardInspector card={inspecting} onClose={() => setInspecting(null)} />
    </ViewLayout>
  );
}

/** The earmarks as a ruled list: art · name · why · printing · you own. */
function EarmarkList({ rows, onInspect }: { rows: EarmarkEntryOut[]; onInspect: (c: GuideCard) => void }) {
  return (
    <div className="@container h-full overflow-y-auto px-3 pb-6 sm:px-5" role="region" aria-label="Earmarked cards" tabIndex={0}>
      <table className="w-full table-fixed border-collapse text-sm tabular">
        <caption className="sr-only">Earmarked cards: card, why, printing, copies you own</caption>
        <thead className="sticky top-0 z-10 bg-paper">
          <tr className="border-b-2 border-rule-strong text-left text-xs voice-semi text-ink-muted">
            <th scope="col" className="hidden w-[calc(var(--size-thumb)+0.5rem)] @[22rem]:table-cell"><span className="sr-only">Art</span></th>
            <th scope="col" className="py-1.5 pl-1 font-medium">Card</th>
            <th scope="col" className="hidden py-1.5 pl-3 font-medium @[40rem]:table-cell">Why</th>
            <th scope="col" className="hidden w-28 py-1.5 pl-3 font-medium @[30rem]:table-cell">Printing</th>
            <th scope="col" className="w-24 py-1.5 pl-3 text-right font-medium">You own</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((e) => {
            const c = earmarkCard(e);
            const m = e.earmark;
            return (
              <tr key={m.oracle_id} className="border-b border-rule/60">
                <td className="hidden py-1 @[22rem]:table-cell">
                  {c && (
                    <button type="button" onClick={() => onInspect(c)} aria-label={`Inspect ${m.name}`} className="block size-[var(--size-thumb)] cursor-pointer overflow-hidden rounded-xs">
                      <CardArt card={c} crop />
                    </button>
                  )}
                </td>
                <th scope="row" className="py-1 pl-1 text-left font-normal">
                  {c ? (
                    <button type="button" onClick={() => onInspect(c)} className="cursor-pointer text-left voice-semi text-ink hover:underline">{m.name}</button>
                  ) : (
                    <span className="voice-semi text-ink">{m.name}</span>
                  )}
                  <span className="block truncate text-xs text-ink-muted @[40rem]:hidden">{earmarkLine(m)}</span>
                </th>
                <td className="hidden truncate pl-3 text-ink-muted @[40rem]:table-cell" title={earmarkLine(m) || undefined}>{earmarkLine(m) || '—'}</td>
                <td className="hidden pl-3 text-ink-muted @[30rem]:table-cell">{e.printing ? `${e.printing.set_code.toUpperCase()} #${e.printing.collector_number}${m.scryfall_id ? ' · preferred' : ''}` : '—'}</td>
                <td className="whitespace-nowrap pl-3 text-right">
                  {e.owned ? (
                    <>
                      <span className="text-ink">{e.owned}</span>
                      <span className={e.free ? 'text-accent-ink' : 'text-ink-muted'}> · {e.free} free</span>
                    </>
                  ) : <span className="text-ink-muted">—</span>}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
