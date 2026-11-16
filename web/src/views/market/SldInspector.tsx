import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { unwrap } from '../../app/queries';
import { useFeature } from '../../app/features';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { dealsUnwatch, dealsWatch, type ProductCostOut } from '../../core/api';
import { splitBonus, type SldRow } from '../../core/secretLair';
import { CardLines } from './CardLines';
import { H3, Row } from './DealInspector';
import { ProductContents } from './ProductContents';
import type { CostState } from './useDealsData';

/** One Secret Lair drop: its sealed value against the cards inside (its guaranteed cards; any bonus is shown apart). */
export function SldInspector({ row: r, cost, costState, watchedUrls }: { row: SldRow; cost?: ProductCostOut; costState?: CostState; watchedUrls?: string[] }) {
  const edition = r.finish === 'foil' ? 'Foil Edition' : 'Regular edition';
  const { cards, named, possible } = splitBonus(cost?.lines);
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
              <Row strong label="Sealed value" value={cost.market} best={null} note={cost.market_source} />
              <Row label="Guaranteed cards, exact printings" value={cost.exact} best={cost.market ?? null} />
              <Row label="Guaranteed cards, cheapest printings" value={cost.floor} best={cost.market ?? null} />
            </dl>
            <p className="text-sm text-ink-muted">
              The % beside each line is how far the sealed value sits under (−) or over (+) it.
              {cost.has_bonus && ' Bonus cards aren’t counted.'}
            </p>
            {cost.market == null && <p className="text-sm text-ink-muted">No sealed market value yet — new drops take a while to list.</p>}
            {(cost.unpriced ?? 0) > 0 && (
              <p className="text-sm text-ink-muted">{cost.unpriced} of {cost.total_cards} cards have no value at their exact printing — totals count only the rest.</p>
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

      {cards.length > 0 && (
        <CardLines title="Guaranteed cards" lines={cards} sortable labels={{ need: 'Qty', exact: 'This printing', floor: 'Cheapest' }} />
      )}
      {named.length > 0 && (
        <section aria-label="Bonus" className="flex flex-col gap-1">
          <CardLines title="Bonus" lines={named} labels={{ need: 'Qty', exact: 'This printing', floor: 'Cheapest' }} />
          <p className="text-sm text-ink-muted">Prices are for reference — the bonus isn’t in any total.</p>
        </section>
      )}
      {possible.length > 0 && (
        <section aria-label="Possible bonus" className="flex flex-col gap-1">
          <CardLines title="Possible bonus" lines={possible} labels={{ need: 'Qty', exact: 'This printing', floor: 'Cheapest' }} />
          <p className="text-sm text-ink-muted">One of these ships with the drop — odds unknown, so not counted.</p>
        </section>
      )}
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
          title={url ? 'Track its market value in Deals → Watching' : 'Not listed for sale yet'}
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
        <p>Its market value stops being tracked.</p>
      </ConfirmDialog>
    </span>
  );
}
