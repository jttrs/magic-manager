import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { cardFloorsQuery } from '../app/queries';
import type { FloorOut } from '../core/api';
import { fmtUsd } from '../core/format';
import { IconAction } from './IconAction';
import { RefreshMark } from './StoreMarks';

const clock = (ms: number) => new Date(ms).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

/** Inspector row: the cheapest nonfoil and foil printing of this card. First
 *  among the sets synced here; the refresh icon (*Recheck for cheapest*) checks
 *  every printing once, and the row then says so with the time (a second check
 *  would only re-serve the same day's cached answer, so the icon goes away). Renders a dt/dd pair
 *  for the inspector's fact grid. (The source is never named: users who know
 *  where prices come from don't need it, and the rest don't care.) */
export function CheapestPrinting({ scryfallId, setCode, cn }: { scryfallId: string; setCode: string | null; cn: string | null }) {
  const [live, setLive] = useState(false);
  const q = useQuery(cardFloorsQuery([scryfallId], live));
  const f = q.data?.floors[0];
  const where = (fl: FloorOut) => {
    const same = fl.set_code?.toLowerCase() === setCode?.toLowerCase() && fl.collector_number === cn;
    return same ? 'this printing' : `${(fl.set_code ?? '').toUpperCase()} #${fl.collector_number}`;
  };
  return (
    <>
      <dt className="text-ink-muted">Cheapest</dt>
      <dd className="flex items-start gap-2 tabular">
        <span className="flex min-w-0 flex-wrap gap-x-4 gap-y-0.5">
        {q.isPending ? (
          <span role="status" className="text-ink-muted">{live ? 'Checking all printings…' : 'Checking…'}</span>
        ) : q.isError ? (
          <span className="text-danger">Couldn’t check: {(q.error as Error).message}</span>
        ) : !f || (!f.nonfoil && !f.foil) ? (
          <span className="text-ink-muted">No price {live ? 'in any printing' : 'among synced sets'}</span>
        ) : (
          <>
            {f.nonfoil && (
              <span>
                {fmtUsd(f.nonfoil.usd)} <span className="text-ink-muted">nonfoil · {where(f.nonfoil)}</span>
              </span>
            )}
            {f.foil && (
              <span>
                {fmtUsd(f.foil.usd)} <span className="text-ink-muted">✦ foil · {where(f.foil)}</span>
              </span>
            )}
          </>
        )}
        {!q.isPending && !q.isError && f && (f.nonfoil || f.foil) && (
          <span className="text-xs text-ink-muted">
            {live ? `checked all printings · ${clock(q.dataUpdatedAt)}` : 'among synced sets'}
          </span>
        )}
        </span>
        {!live && (
          <span className="-my-2 shrink-0">
            <IconAction label="Recheck for cheapest" Icon={RefreshMark} disabled={q.isPending} disabledReason="Checking…" onClick={() => setLive(true)} />
          </span>
        )}
      </dd>
    </>
  );
}
