import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useId, useState, type FormEvent } from 'react';
import { unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { dealsClearTarget, dealsSetTarget, type ProductCostOut, type TargetOut } from '../../core/api';
import { inStockBest, targetMet, targetPriceOf, targetText, type DealProduct } from '../../core/deals';
import { fmtUsd } from '../../core/format';
import { H3 } from './inspectorStyles';

type Mode = TargetOut['mode'];

/** A watched product's price target: what it is, whether today's best in-stock price meets it, and a
 *  small form to set, change or remove it. Reading watched prices reports targets newly met. */
export function PriceTarget({ product: p, cost }: { product: DealProduct; cost?: ProductCostOut }) {
  const qc = useQueryClient();
  const id = useId();
  const t = p.target ?? null;
  const [mode, setMode] = useState<Mode>(t?.mode ?? 'price');
  const [text, setText] = useState(t ? String(t.value) : '');
  const value = Number(text);
  const stored = Math.round(value * 100) / 100; // the engine rounds to cents, then validates
  const valid = text.trim() !== '' && Number.isFinite(value) && stored > 0 && (mode === 'price' || stored < 100);
  const changed = !t || t.mode !== mode || t.value !== value;
  const refresh = () => qc.invalidateQueries({ queryKey: ['deals', 'watched'] });
  const save = useMutation({
    mutationFn: async () => unwrap(await dealsSetTarget({ body: { product_id: p.productId!, mode, value } })),
    onSuccess: refresh,
  });
  const clear = useMutation({
    mutationFn: async () => unwrap(await dealsClearTarget({ query: { product_id: p.productId! } })),
    onSuccess: () => { setText(''); return refresh(); },
  });
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (valid && changed) save.mutate();
  };
  const busy = save.isPending || clear.isPending;
  const error = (save.error ?? clear.error) as Error | null;
  return (
    <section aria-labelledby={`${id}-h`} className="flex flex-col gap-2">
      <h3 id={`${id}-h`} className={H3}>Target price</h3>
      <Status p={p} cost={cost} />
      <form onSubmit={submit} className="flex flex-wrap items-end gap-x-3 gap-y-2">
        <fieldset className="flex flex-col gap-1">
          <legend className="text-xs voice-semi text-ink-muted">Target as</legend>
          <span className="inline-flex gap-3 text-sm text-ink">
            <label className="inline-flex min-h-9 cursor-pointer items-center gap-1.5">
              <input type="radio" name={`${id}-mode`} checked={mode === 'price'} onChange={() => setMode('price')} className="accent-[var(--theme-accent)]" /> A price
            </label>
            <label className="inline-flex min-h-9 cursor-pointer items-center gap-1.5">
              <input type="radio" name={`${id}-mode`} checked={mode === 'pct_under'} onChange={() => setMode('pct_under')} className="accent-[var(--theme-accent)]" />
              % under {p.kind === 'single' ? 'its price' : 'sealed price'}
            </label>
          </span>
        </fieldset>
        <label className="flex flex-col gap-1 text-xs voice-semi text-ink-muted">
          {mode === 'price' ? 'Price (USD)' : 'Percent under'}
          <span className="inline-flex h-9 items-center rounded-sm border border-rule-strong bg-paper-raised px-2 text-md text-ink focus-within:border-accent">
            {mode === 'price' && <span aria-hidden="true" className="text-ink-muted">$</span>}
            <input
              type="text"
              inputMode="decimal"
              autoComplete="off"
              value={text}
              onChange={(e) => setText(e.target.value.replace(/[^0-9.]/g, ''))}
              aria-invalid={(text !== '' && !valid) || undefined}
              placeholder={mode === 'price' ? '0.00' : '15'}
              className="w-20 bg-transparent px-1 tabular outline-none placeholder:text-ink-muted"
            />
            {mode === 'pct_under' && <span aria-hidden="true" className="text-ink-muted">%</span>}
          </span>
        </label>
        <Button type="submit" tone="paper" emphasis="primary" disabled={!valid || !changed || busy}>
          {save.isPending ? 'Saving…' : t ? 'Update target' : 'Set target'}
        </Button>
        {t && (
          <Button tone="paper" emphasis="quiet" disabled={busy} onClick={() => clear.mutate()}>
            {clear.isPending ? 'Removing…' : 'Remove target'}
          </Button>
        )}
      </form>
      {text !== '' && !valid && <p className="text-xs text-danger">{mode === 'price' ? 'Enter a price above $0.' : 'Enter a percentage between 0 and 100.'}</p>}
      {error && <p role="alert" className="text-sm text-danger">Couldn’t save the target: {error.message}</p>}
    </section>
  );
}

function Status({ p, cost }: { p: DealProduct; cost?: ProductCostOut }) {
  const t = p.target;
  if (!t) return <p className="text-sm text-ink-muted">No target yet. Set one and reading watched prices tells you when the best in-stock price reaches it.</p>;
  const at = targetPriceOf(p, cost);
  const met = targetMet(p, cost);
  const best = inStockBest(p);
  const how = t.mode === 'price' ? fmtUsd(t.value) : `${fmtUsd(at ?? 0)} (${targetText(t, p.kind)})`;
  if (at == null) return <p role="status" className="text-sm text-ink-muted">Target {targetText(t, p.kind)} — waiting for the sealed price to work out the price.</p>;
  if (met && best?.price != null) {
    return (
      <p role="status" className="text-sm text-ink">
        <span className="highlighter voice-semi font-medium">Target met</span> — {best.store ?? 'a store'} has it at {fmtUsd(best.price)}. Your target is {how}.
      </p>
    );
  }
  return (
    <p role="status" className="text-sm text-ink">
      Target {how}.{' '}
      <span className="text-ink-muted">
        {best?.price != null ? `Best in stock is ${fmtUsd(best.price)} — ${fmtUsd(best.price - at)} to go.` : 'No store has it in stock right now.'}
      </span>
    </p>
  );
}
