import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { unwrap } from '../../app/queries';
import { useFeature } from '../../app/features';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { dealsUnwatch, dealsWatch, type ProductCostOut } from '../../core/api';
import type { SldRow } from '../../core/secretLair';
import { CardLines } from './CardLines';
import { H3, Row } from './DealInspector';
import { ProductContents } from './ProductContents';
import type { CostState } from './useDealsData';

/** One Secret Lair drop: its sealed price against the cards inside (bonus card included). */
export function SldInspector({ row: r, cost, costState, watchedUrls }: { row: SldRow; cost?: ProductCostOut; costState?: CostState; watchedUrls?: string[] }) {
  const edition = r.finish === 'foil' ? 'Foil Edition' : 'Regular edition';
  const bonus = cost?.lines?.filter((l) => l.bonus) ?? [];
  return (
    <section aria-labelledby="sld-h" className="flex h-full min-h-0 flex-col gap-5 overflow-y-auto overscroll-contain px-4 pb-8 pt-1 [scrollbar-gutter:stable]">
      <header className="flex flex-wrap items-end gap-x-4 gap-y-2 border-b-2 border-rule-strong pb-1.5">
        <div className="min-w-0 flex-1">
          <h2 id="sld-h" className="text-2xl voice-condensed font-bold leading-tight text-ink">{r.name}</h2>
          <p className="mt-1 text-sm tabular text-ink-muted">
            {['SLD · Secret Lair', edition, r.release_date && `released ${r.release_date}`].filter(Boolean).join(' · ')}
          </p>
        </div>
        <WatchControl r={r} price={cost?.market ?? null} watchedUrls={watchedUrls} />
      </header>

      <section aria-label="What it’s worth" className="flex flex-col gap-1">
        <h3 className={H3}>What it’s worth</h3>
        {!cost ? (
          costState?.error
            ? <p role="alert" className="text-sm text-danger">Couldn’t work out what it’s worth: {costState.error}</p>
            : <p role="status" aria-busy="true" className="text-sm text-ink-muted">Working out what it’s worth…</p>
        ) : (
          <>
            <dl className="flex flex-col">
              <Row strong label="Sealed price" value={cost.market} best={null} note={cost.market_source} />
              <Row label="Cards inside, exact printings" value={cost.exact} best={cost.market ?? null} />
              <Row label="Cards inside, cheapest printings" value={cost.floor} best={cost.market ?? null} />
              {(cost.booster_ev ?? 0) > 0 && <Row label="of which the bonus card, expected value" value={cost.booster_ev} best={null} />}
            </dl>
            <p className="text-sm text-ink-muted">
              The % beside each line is how far the sealed price sits under (−) or over (+) it.
              {bonus.length > 0 && ` Includes the bonus card${bonus.length > 1 ? 's' : ''}: ${bonus.map((l) => l.name).join(', ')}.`}
              {(cost.booster_ev ?? 0) > 0 && ' The bonus card is random, so it counts at its expected value.'}
            </p>
            {cost.market == null && <p className="text-sm text-ink-muted">No sealed market price yet — new drops take a while to list.</p>}
            {(cost.unpriced ?? 0) > 0 && (
              <p className="text-sm text-ink-muted">{cost.unpriced} of {cost.total_cards} cards have no price at their exact printing — totals count only the rest.</p>
            )}
            {cost.notes?.map((n) => <p key={n} className="text-sm text-ink-muted">{n}</p>)}
            {r.tcgplayer_url && (
              <a href={r.tcgplayer_url} target="_blank" rel="noreferrer" className="touch-hit self-start text-sm text-accent-ink underline">
                TCGplayer<span aria-hidden="true"> ↗</span><span className="sr-only"> (opens in a new tab)</span>
              </a>
            )}
          </>
        )}
      </section>

      {r.sealed_name && (cost?.booster_ev ?? 0) > 0 && (
        <section aria-label="Contents" className="flex flex-col gap-1">
          <h3 className={H3}>Contents</h3>
          <ProductContents set="sld" name={r.sealed_name} />
        </section>
      )}

      {cost?.lines?.length ? (
        <CardLines title="Cards" lines={cost.lines} sortable labels={{ need: 'Qty', exact: 'This printing', floor: 'Cheapest' }} />
      ) : null}
    </section>
  );
}

function WatchControl({ r, price, watchedUrls }: { r: SldRow; price: number | null; watchedUrls?: string[] }) {
  const on = useFeature('deals');
  const qc = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const url = r.tcgplayer_url;
  const refresh = () => qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
  const watch = useMutation({
    mutationFn: async () => unwrap(await dealsWatch({ body: { url: url!, choice: { kind: 'sld', set_code: 'sld', name: r.name, finish: r.finish }, price, currency: 'USD' } })),
    onSuccess: refresh,
  });
  if (!on) return null;
  const watchingHere = url != null && watchedUrls?.includes(url);
  return (
    <span className="flex flex-col items-end gap-1">
      {watchingHere ? (
        <Button tone="paper" emphasis="quiet" onClick={() => setConfirm(true)}>Stop watching</Button>
      ) : watchedUrls?.length ? (
        <span className="text-sm text-accent-ink">Watching at another store</span>
      ) : (
        <Button
          tone="paper"
          emphasis="quiet"
          disabled={!url || watch.isPending}
          title={url ? 'Track its TCGplayer market price in Deals → Watching' : 'Not listed on TCGplayer yet'}
          onClick={() => watch.mutate()}
        >
          {watch.isPending ? 'Saving…' : 'Watch'}
        </Button>
      )}
      {watch.isError && <span role="alert" className="text-xs text-danger">{(watch.error as Error).message}</span>}
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={`Stop watching ${r.name}?`}
        confirmLabel="Stop watching"
        onConfirm={async () => { unwrap(await dealsUnwatch({ query: { url: url! } })); await refresh(); }}
      >
        <p>Its TCGplayer price stops being tracked.</p>
      </ConfirmDialog>
    </span>
  );
}
