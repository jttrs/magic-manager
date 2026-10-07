import { useQueryClient } from '@tanstack/react-query';
import { Dialog } from 'radix-ui';
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { useJob, type JobLive } from '../../app/useJob';
import { Button } from '../../components/Button';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';
import { confirmed, productMeta, readNotMine, rememberNotMine, scanFrom, type CoverageScan } from '../../core/trueup';

type Phase = 'scan' | 'review' | 'record' | 'done';

/** Find which products your loose cards came from — scene boxes, precon and
 *  jumpstart decks, land packs, complete Secret Lair drops — review the matches,
 *  and record the ones you bought, so Acquired from can trace their cards. */
export function FindProductsDialog({ trigger }: { trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content
          onInteractOutside={(e) => e.preventDefault()}
          className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(44rem,calc(100dvh-1.5rem))] w-[min(40rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none"
        >
          {open && <Review onClose={() => setOpen(false)} />}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function Review({ onClose }: { onClose: () => void }) {
  const qc = useQueryClient();
  const scanJob = useJob();
  const recordJob = useJob();
  const [picks, setPicks] = useState<string[]>([]);
  const [notMine, setNotMine] = useState<Set<string>>(new Set());
  const [error, setError] = useState('');

  const scan = (p: string[]) => {
    setError('');
    scanJob.reset();
    void scanJob.start('trueup.scan', { refute: readNotMine(), picks: p }).then((e) => e && setError(e));
  };
  // Scan once as soon as the dialog opens.
  const started = useRef(false);
  useEffect(() => {
    if (started.current) return;
    started.current = true;
    scan([]);
  });

  const result: CoverageScan | null = scanJob.live?.status === 'succeeded' ? scanFrom(scanJob.live.artifacts) : null;
  const recorded: CoverageScan | null = recordJob.live?.status === 'succeeded' ? scanFrom(recordJob.live.artifacts) : null;
  const phase: Phase = recorded ? 'done' : recordJob.live ? 'record' : result ? 'review' : 'scan';
  const keep = result ? confirmed(result, notMine) : [];

  useEffect(() => {
    if (!recorded) return;
    void qc.invalidateQueries({ queryKey: ['collection'] });
    void qc.invalidateQueries({ queryKey: ['decks'] });
    void qc.invalidateQueries({ queryKey: ['holdings'] });
    void qc.invalidateQueries({ queryKey: ['history'] });
  }, [recorded, qc]);

  const record = async () => {
    rememberNotMine([...notMine]);
    const err = await recordJob.start('trueup.apply', { expect: keep.map((p) => p.fileName), picks });
    if (err) setError(err);
  };
  const failure = scanJob.live?.status === 'failed' ? scanJob.live.error : recordJob.live?.status === 'failed' ? recordJob.live.error : null;

  return (
    <>
      <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
        <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Find products in your cards</Dialog.Title>
        <Dialog.Description className="text-md leading-relaxed text-ink-muted">
          Cards with no known source are matched against every product’s card list — scene boxes, precon and Jumpstart decks, land packs, Secret Lair drops. A product shows only when you have all of its cards.
        </Dialog.Description>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {phase === 'scan' && !failure && <Progress live={scanJob.live} label="Checking products" />}
        {phase === 'record' && !failure && <Progress live={recordJob.live} label="Recording products" />}
        {failure && (
          <p role="alert" className="text-md text-danger">
            {failure}{' '}
            <button type="button" className="cursor-pointer underline" onClick={() => { recordJob.reset(); scan(picks); }}>Scan again</button>
          </p>
        )}
        {phase === 'review' && result && (
          result.ready.length === 0 && result.conflicts.length === 0 ? (
            <p className="text-md leading-relaxed text-ink-muted">No products found. Your cards with no known source don’t complete any product’s list.</p>
          ) : (
            <div className="flex flex-col gap-5">
              {result.ready.length > 0 && (
                <section aria-labelledby="fp-ready" className="flex flex-col gap-1">
                  <h3 id="fp-ready" className="text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">Your cards complete · {fmtInt(result.ready.length)}</h3>
                  <ul className="flex flex-col">
                    {result.ready.map((p) => {
                      const mine = !notMine.has(p.fileName);
                      return (
                        <li key={p.fileName} className="flex items-center gap-3 border-b border-rule py-2">
                          <label className="flex min-w-0 flex-1 cursor-pointer items-start gap-2.5">
                            <input
                              type="checkbox"
                              checked={mine}
                              onChange={() => setNotMine((s) => { const n = new Set(s); if (mine) n.add(p.fileName); else n.delete(p.fileName); return n; })}
                              className="mt-1 accent-[var(--theme-accent)]"
                            />
                            <span className="min-w-0">
                              <span className={`block ${mine ? 'text-ink' : 'text-ink-muted line-through'}`}>{p.name}</span>
                              <span className="block text-xs text-ink-muted">{productMeta(p)}</span>
                            </span>
                          </label>
                          <span className="shrink-0 text-right text-sm tabular text-ink-muted">{fmtCount(p.recipe_qty, 'card')} · <span className="text-ink">{fmtUsd(p.usd)}</span></span>
                        </li>
                      );
                    })}
                  </ul>
                  <p className="text-xs text-ink-muted">Uncheck any you didn’t buy — they won’t be suggested again.</p>
                </section>
              )}
              {result.conflicts.length > 0 && (
                <section aria-labelledby="fp-lost" className="flex flex-col gap-1">
                  <h3 id="fp-lost" className="text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">Shared a card with another product · {fmtInt(result.conflicts.length)}</h3>
                  <ul className="flex flex-col">
                    {result.conflicts.map((p) => (
                      <li key={p.fileName} className="flex items-center gap-3 border-b border-rule py-2">
                        <span className="min-w-0 flex-1">
                          <span className="block text-ink">{p.name}</span>
                          <span className="block text-xs text-ink-muted">{productMeta(p)}{p.lost_to.length ? ` · its shared cards went to ${p.lost_to.slice(0, 2).join(', ')}` : ''}</span>
                        </span>
                        <button
                          type="button"
                          onClick={() => { const next = [...picks, p.fileName]; setPicks(next); scan(next); }}
                          className="shrink-0 cursor-pointer rounded-sm border border-rule px-2.5 py-1 text-sm voice-semi text-ink hover:border-rule-strong"
                        >
                          I opened this one
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </div>
          )
        )}
        {phase === 'done' && recorded && (
          <p role="status" className="text-md leading-relaxed">
            Recorded {fmtCount(recorded.registered, 'product')}. {fmtCount(recorded.reattributed, 'card')} now show where they came from under <b>Acquired from</b>.
          </p>
        )}
      </div>

      {error && <p role="alert" className="px-5 pb-2 text-sm text-danger">{error}</p>}
      <div className="flex justify-end gap-2 border-t border-rule px-5 py-3">
        {phase === 'done' ? (
          <Button emphasis="primary" onClick={onClose}>Done</Button>
        ) : (
          <>
            <Dialog.Close asChild>
              <Button tone="paper" disabled={phase === 'record'}>Cancel</Button>
            </Dialog.Close>
            <Button emphasis="primary" onClick={record} disabled={phase !== 'review' || keep.length === 0}>
              {keep.length ? `Record ${fmtCount(keep.length, 'product')}` : 'Record products'}
            </Button>
          </>
        )}
      </div>
    </>
  );
}

function Progress({ live, label }: { live: JobLive | null; label: string }) {
  const done = live?.done ?? 0;
  const total = live?.total ?? null;
  return (
    <div role="status" aria-live="polite" className="flex flex-col gap-1.5">
      <p className="flex items-baseline gap-2 text-sm text-ink-muted">
        {total ? (
          <>
            <span className="tabular">{label} · {fmtInt(done)} of {fmtInt(total)}</span>
            {live?.log.at(-1)?.msg && <span className="min-w-0 truncate">· {live.log.at(-1)!.msg}</span>}
          </>
        ) : (
          <span>{live?.log.at(-1)?.msg ?? `${label}…`}</span>
        )}
      </p>
      <div className="h-[3px] overflow-hidden rounded-pill bg-paper-sunk" role="progressbar" aria-label={label} aria-valuemin={0} aria-valuemax={total ?? 0} aria-valuenow={done}>
        <div className="h-full rounded-pill bg-accent transition-[width] duration-300 ease-guide" style={{ width: total ? `${(done / total) * 100}%` : '4%' }} />
      </div>
      <p className="text-xs text-ink-muted">The first scan reads every product’s list and can take a few minutes; later scans take under a minute.</p>
    </div>
  );
}
