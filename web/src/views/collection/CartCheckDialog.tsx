import { useMutation, useQuery } from '@tanstack/react-query';
import { Dialog } from 'radix-ui';
import { useState, type ReactNode } from 'react';
import { cartSetupQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { cartCheck, type CartAuditOut } from '../../core/api';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';

/** Internal (cart_check flag): audit a Mana Pool cart against your collection —
 *  bought twice, already owned, priced over market, and family gaps still missing. */
export function CartCheckDialog({ trigger, family }: { trigger: ReactNode; family?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(48rem,calc(100dvh-1.5rem))] w-[min(46rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          {open && <CartCheck family={family} />}
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function CartCheck({ family }: { family?: string }) {
  const setup = useQuery(cartSetupQuery(true));
  const run = useMutation({
    mutationFn: async () => unwrap(await cartCheck({ body: { family: family ?? null } })),
  });
  const r = run.data;
  const ready = setup.data?.account === true;

  return (
    <>
      <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
        <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Check my Mana Pool cart</Dialog.Title>
        <Dialog.Description className="text-md leading-relaxed text-ink-muted">
          Finds cards you’re buying twice, already own, or are paying over market for — and set gaps still missing from the cart.
        </Dialog.Description>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {r ? (
          <Results r={r} />
        ) : setup.isPending ? (
          <p role="status" className="text-md text-ink-muted">Checking this machine’s setup…</p>
        ) : !ready ? (
          <p className="text-md leading-relaxed">
            Reading the cart needs your Mana Pool account in this machine’s <code className="text-sm">.env</code>: <code className="text-sm">MANAPOOL_EMAIL</code>, <code className="text-sm">MANAPOOL_PASSWORD</code> and <code className="text-sm">MANAPOOL_ACCESS_TOKEN</code>. Add them, restart <code className="text-sm">uv run mm serve</code>, and try again.
          </p>
        ) : (
          <p className="text-md leading-relaxed text-ink-muted">Reads your cart with the Mana Pool account in this machine’s .env and checks every line against your collection.</p>
        )}
        {run.isError && <p role="alert" className="mt-3 text-sm text-danger">{(run.error as Error).message}</p>}
      </div>
      <div className="flex justify-end gap-2 border-t border-rule px-5 py-3">
        <Button tone="paper" emphasis={r ? 'quiet' : 'primary'} onClick={() => run.mutate()} disabled={!ready || run.isPending}>
          {run.isPending ? 'Reading your cart…' : r ? 'Check again' : 'Read my cart'}
        </Button>
      </div>
    </>
  );
}

function Results({ r }: { r: CartAuditOut }) {
  const missingCost = r.missing.reduce((s, m) => s + (m.market ?? 0), 0);
  return (
    <div className="flex flex-col gap-5">
      <p className="text-md tabular">
        {fmtCount(r.lines, 'line')} · {fmtCount(r.copies, 'card')} · {fmtUsd(r.total)}
        {r.family ? <span className="text-ink-muted"> · set family {r.family.toUpperCase()}</span> : r.families.length > 1 ? <span className="text-ink-muted"> · spans {r.families.map((f) => f.toUpperCase()).join(', ')}</span> : null}
      </p>
      <Section title="Bought twice" n={r.dupes.length} empty="No printing is in the cart twice.">
        {r.dupes.map((d) => (
          <Line key={d.scryfall_id ?? `${d.set}${d.num}`} card={d} right={<>{d.note}{d.cheaper != null && <> · keep the {fmtUsd(d.cheaper)} one</>}</>} />
        ))}
      </Section>
      <Section title="Already in your collection" n={r.owned.length} empty="Nothing in the cart is already in your collection.">
        {r.owned.map((o) => <Line key={`${o.scryfall_id}${o.fin}`} card={o} right={<>you own {fmtInt(o.owned_qty)} · {fmtUsd(o.your)}</>} />)}
      </Section>
      <Section title="Over market" n={r.overpay.length} empty="Nothing is priced well over market.">
        {r.overpay.map((o) => (
          <Line key={`${o.scryfall_id}${o.fin}`} card={o} right={<><span className="text-ink">{fmtUsd(o.your)}</span> vs {fmtUsd(o.market)} · <span className="font-medium text-danger">+{Math.round(o.pct ?? 0)}%</span></>} />
        ))}
      </Section>
      {r.family && (
        <Section title={`Still missing from ${r.family.toUpperCase()}`} n={r.missing.length} meta={r.missing.length ? `≈ ${fmtUsd(missingCost)}` : undefined} empty="The cart completes the family.">
          {r.missing.slice(0, 60).map((m) => <Line key={`${m.scryfall_id}${m.fin}`} card={m} right={fmtUsd(m.market)} />)}
          {r.missing.length > 60 && <li className="py-1.5 text-sm text-ink-muted">…and {fmtInt(r.missing.length - 60)} more — see Collection, Missing.</li>}
        </Section>
      )}
      {r.unidentified.length > 0 && (
        <Section title="Couldn’t identify" n={r.unidentified.length}>
          {r.unidentified.map((u, i) => <li key={i} className="border-b border-rule py-1.5 text-sm text-ink-muted">{u.name ?? 'Unknown card'} {u.set ? `· ${u.set} ${u.num ?? ''}` : ''}</li>)}
        </Section>
      )}
    </div>
  );
}

function Section({ title, n, meta, empty, children }: { title: string; n: number; meta?: string; empty?: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1" aria-label={title}>
      <h3 className="flex items-baseline gap-2 text-sm voice-condensed font-medium uppercase tracking-[0.06em] text-ink-muted">
        {title} · {fmtInt(n)}
        {meta && <span className="normal-case tracking-normal tabular">{meta}</span>}
      </h3>
      {n === 0 ? <p className="text-sm text-ink-muted">{empty}</p> : <ul className="flex flex-col">{children}</ul>}
    </section>
  );
}

function Line({ card, right }: { card: { name: string; set: string; num: string; fin?: string }; right: ReactNode }) {
  return (
    <li className="flex items-baseline gap-3 border-b border-rule py-1.5 text-sm">
      <span className="min-w-0 flex-1">
        <span className="text-ink">{card.name}</span>
        <span className="ml-2 text-xs text-ink-muted">{card.set.toUpperCase()} {card.num}{card.fin === 'foil' ? ' · foil' : ''}</span>
      </span>
      <span className="shrink-0 text-right tabular text-ink-muted">{right}</span>
    </li>
  );
}
