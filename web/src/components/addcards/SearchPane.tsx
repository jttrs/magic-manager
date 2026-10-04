import { useQuery } from '@tanstack/react-query';
import { useDeferredValue, useState } from 'react';
import { printingSearchQuery } from '../../app/queries';
import type { PrintingOut } from '../../core/api';
import { fmtUsd } from '../../core/format';
import type { Finish } from '../../core/ingest';
import { ownedLabel, printingLabel } from './PrintingPicker';

/** Live printing search: type a name, press a printing to stage one copy. */
export function SearchPane({ onPick }: { onPick: (p: PrintingOut, finish: Finish) => void }) {
  const [q, setQ] = useState('');
  const dq = useDeferredValue(q);
  const res = useQuery(printingSearchQuery(dq));
  const hits = res.data?.printings ?? [];
  return (
    <div className="flex min-h-0 flex-col gap-3">
      <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
        Card name
        <input
          type="search"
          autoFocus
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="e.g. Sol Ring, Cloud…"
          autoComplete="off"
          spellCheck={false}
          className="h-10 rounded-sm border border-rule-strong bg-paper-raised px-3 text-md text-ink placeholder:text-ink-muted focus-visible:border-accent"
        />
      </label>
      <p aria-live="polite" className="min-h-4 text-xs text-ink-muted">
        {q.trim().length < 2
          ? 'Type at least two letters.'
          : res.isError
            ? <span className="text-danger">Search failed: {(res.error as Error).message}</span>
            : res.isFetching && !res.data
              ? 'Searching…'
              : `${hits.length}${hits.length === 60 ? '+' : ''} printings${res.data?.source === 'scryfall' ? ' from Scryfall' : ''}. Press a card to add one copy.`}
      </p>
      <ul aria-label="Printings" className="grid min-h-0 grid-cols-[repeat(auto-fill,minmax(8.5rem,1fr))] gap-3 overflow-y-auto pb-2 pr-1">
        {hits.map((p) => (
          <li key={p.scryfall_id} className="flex flex-col gap-1">
            <button
              type="button"
              onClick={() => onPick(p, 'nonfoil')}
              aria-label={`Add ${p.name}, ${printingLabel(p)}`}
              className="group cursor-pointer rounded-[4.5%/3.2%] transition-transform duration-200 ease-guide hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
            >
              {p.image_uri ? (
                <img src={p.image_uri} alt="" loading="lazy" decoding="async" className="aspect-[488/680] w-full rounded-[4.5%/3.2%] bg-paper-sunk" />
              ) : (
                <span className="grid aspect-[488/680] w-full place-items-center rounded-sm border border-rule bg-paper-sunk p-2 text-center text-xs text-ink-muted">{p.name}</span>
              )}
            </button>
            <span className="truncate text-sm voice-semi font-medium text-ink" title={p.name}>{p.name}</span>
            <span className="truncate text-2xs tabular text-ink-muted" title={p.set_name ?? undefined}>{printingLabel(p)}</span>
            <span className="flex items-center gap-2 text-2xs tabular">
              <span className="text-ink">{fmtUsd(p.price_usd ?? p.price_usd_foil)}</span>
              <span className="text-accent-ink">{ownedLabel(p)}</span>
              {p.finishes.includes('foil') && p.finishes.includes('nonfoil') && (
                <button type="button" onClick={() => onPick(p, 'foil')} aria-label={`Add ${p.name} foil, ${printingLabel(p)}`} className="ml-auto cursor-pointer rounded-xs border border-rule px-1 leading-5 text-ink-muted hover:border-rule-strong hover:text-ink">
                  +✦ Foil
                </button>
              )}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
