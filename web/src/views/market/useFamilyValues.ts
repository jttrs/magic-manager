import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { enqueueJob, useJob } from '../../app/useJob';
import type { ProductValueOut } from '../../core/api';
import { hasPricingErrors } from '../../core/market';

// Product valuations are slow to compute and prices move about daily: keep each
// family's for 12 hours across reloads — unless a product failed to price, so a
// passing outage doesn't stick for the day.
const VALUES_TTL = 12 * 3600_000;
const storageKey = (code: string) => `mm.market.values.v3.${code}`;

function readValues(code: string): ProductValueOut[] | null {
  try {
    const hit = JSON.parse(localStorage.getItem(storageKey(code)) ?? 'null') as { at: number; rows: ProductValueOut[] } | null;
    return hit && Date.now() - hit.at < VALUES_TTL ? hit.rows : null;
  } catch {
    return null;
  }
}

function storeValues(code: string, rows: ProductValueOut[]) {
  try {
    if (hasPricingErrors(rows)) localStorage.removeItem(storageKey(code));
    else localStorage.setItem(storageKey(code), JSON.stringify({ at: Date.now(), rows }));
  } catch {
    // Storage full or blocked: the values still show for this visit.
  }
}

type Submitted = { id: string } | { error: string };

// A family's pricing job outlives the panel that started it: switching to the
// Cards tab unmounts the panel, and coming back must pick up the same job (its
// event history replays) instead of queueing a second full valuation.
const pending = new Map<string, Promise<Submitted>>();

function submit(code: string): Promise<Submitted> {
  let p = pending.get(code);
  if (!p) {
    p = enqueueJob('market.value_family', { code });
    pending.set(code, p);
    void p.then((r) => {
      if ('error' in r && pending.get(code) === p) pending.delete(code);
    });
  }
  return p;
}

type Artifact = { label: string; data: unknown };

/** A family's sealed-product valuations: cached (memory + 12 h storage), else
 *  priced by the `market.value_family` job, shared across remounts. */
export function useFamilyValues(code: string, hasProducts: boolean) {
  const qc = useQueryClient();
  const key = useMemo(() => ['market', 'values', code], [code]);
  const values = useQuery({ queryKey: key, queryFn: () => qc.getQueryData<ProductValueOut[]>(key) ?? readValues(code), staleTime: Infinity, gcTime: 30 * 60_000 });
  const { live, follow, reset } = useJob();
  const [jobCode, setJobCode] = useState<string | null>(null);
  const [startError, setStartError] = useState<string | null>(null);
  // Bumped by reprice: re-runs the start effect even when nothing was cached.
  const [attempt, setAttempt] = useState(0);

  const run = useCallback(() => {
    let alive = true;
    reset();
    setStartError(null);
    setJobCode(code);
    void submit(code).then((r) => {
      if (!alive) return;
      if ('id' in r) {
        follow(r.id);
        void qc.invalidateQueries({ queryKey: ['jobs'] });
      } else setStartError(r.error);
    });
    return () => {
      alive = false;
    };
  }, [code, follow, reset, qc]);

  // Price the family once per visit, or follow the job already pricing it.
  useEffect(() => {
    if (!hasProducts || values.isPending || values.data) return;
    return run();
  }, [hasProducts, values.isPending, values.data, run, attempt]);

  useEffect(() => {
    if (jobCode !== code || !live) return;
    if (live.status === 'succeeded') {
      const art = (live.artifacts as Artifact[] | undefined)?.find((a) => a.label === 'values');
      if (art) {
        qc.setQueryData(key, art.data as ProductValueOut[]);
        storeValues(code, art.data as ProductValueOut[]);
      } else setStartError('the job finished without prices');
      pending.delete(code);
    } else if (live.status === 'failed') pending.delete(code);
  }, [live, jobCode, code, qc, key]);

  /** Price again from scratch (after a failed job or products that failed to price). */
  const reprice = useCallback(() => {
    pending.delete(code);
    try {
      localStorage.removeItem(storageKey(code));
    } catch {
      // Storage blocked: nothing to clear.
    }
    qc.setQueryData(key, null);
    setAttempt((n) => n + 1);
  }, [code, qc, key]);

  const data = values.data ?? null;
  const running = !data && !startError && live != null && live.status !== 'succeeded' && live.status !== 'failed';
  const failure = data ? null : startError ?? (live?.status === 'failed' ? live.error ?? 'the job failed' : null);
  return { values: data, live, running, failure, reprice };
}
