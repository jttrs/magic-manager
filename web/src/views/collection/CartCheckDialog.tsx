import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Dialog, ToggleGroup } from 'radix-ui';
import { useState, type ReactNode } from 'react';
import { useFeature, useOwnerPath } from '../../app/features';
import { cartSetupQuery, unwrap } from '../../app/queries';
import { useCompanion } from '../../app/useCompanion';
import { Button } from '../../components/Button';
import { AwaitingNote, BookmarkletLink, FailureNote } from '../../components/companion/CompanionNotes';
import { cartCheck, cartLines, companionBookmarklet, type CartAuditOut } from '../../core/api';
import { CART_STORE_NAME, CompanionError, parseBookmarkletPaste, warningLines, type CartLine, type CartStore } from '../../core/companion';
import { CART_STORES, cartAllowed, cartSwitchHint, lineQualifier } from '../../core/cartCheck';
import { trackCompanionError } from '../../app/analytics';
import { reportScraperFailure, useDownScrapers } from '../../app/scraperHealth';
import { ScraperNotice } from '../../components/ScraperNotice';
import { cartKey } from '../../core/scraperHealth';
import { fmtCount, fmtInt, fmtUsd } from '../../core/format';

/** Internal (cart_check flag): audit a Mana Pool, TCGplayer or Card Kingdom cart against
 *  your collection — bought twice, already owned, priced over market, and family gaps still
 *  missing. The cart is read in YOUR browser (companion, or the Mana Pool bookmarklet) —
 *  only its lines reach the app — or, for Mana Pool on the owner's own Mac, with the Mana Pool login in this computer’s .env. */
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

type Source = 'extension' | 'bookmarklet' | 'account';
const SOURCE_LABEL: Record<Source, string> = {
  extension: 'read in this browser by the companion',
  bookmarklet: 'pasted from the bookmarklet',
  account: 'read with your Mana Pool login on this computer',
};
const READS: Record<CartStore, string> = {
  manapool: 'The companion reads your cart page on manapool.com — signed in as you, in this browser — and shows you the lines before anything is sent.',
  tcgplayer: 'The companion reads your cart page on tcgplayer.com — cards, conditions, quantities and prices, never the sellers — and shows you the lines before anything is sent.',
  cardkingdom: 'The companion reads your cart page on cardkingdom.com — cards, grades, quantities and prices — and shows you the lines before anything is sent.',
};
const H3 = 'border-b border-rule-strong pb-1 text-md voice-condensed font-bold uppercase tracking-[0.04em] text-ink';

function CartCheck({ family }: { family?: string }) {
  const companionOn = useFeature('companion');
  const c = useCompanion();
  // The server's own Mana Pool login: the owner's machine — admins only when hosted.
  const serverLogin = useOwnerPath('manapool.server_login');
  const setup = useQuery(cartSetupQuery(serverLogin));
  const bookmarklet = useQuery({ queryKey: ['companion', 'bookmarklet'], queryFn: async () => unwrap(await companionBookmarklet()), staleTime: Infinity });
  const [awaiting, setAwaiting] = useState<string | null>(null);
  const [paste, setPaste] = useState('');
  const [store, setStore] = useState<CartStore>('manapool');
  const [result, setResult] = useState<{ r: CartAuditOut; source: Source; store: CartStore; warnings: string[] } | null>(null);

  const audit = async (items: CartLine[], source: 'extension' | 'bookmarklet', from: CartStore) =>
    unwrap(await cartLines({ body: { items, source, store: from, family: family ?? null } }));
  const qc = useQueryClient();
  const cartDown = useDownScrapers([cartKey(store)]);
  const allowed = cartAllowed(store, c.hello);
  const viaCompanion = useMutation({
    mutationFn: async () => {
      const from = store;
      const d = await c.read('cart', { store: from }, (summary) => setAwaiting(summary));
      setAwaiting(null);
      return { r: await audit(d.items, 'extension', from), source: 'extension' as const, store: from, warnings: warningLines(d.warnings, c.catalog) };
    },
    onSuccess: (r) => { setResult(r); void qc.invalidateQueries({ queryKey: ['scrapers', 'health'] }); },
    onSettled: () => setAwaiting(null),
  });
  const viaPaste = useMutation({
    mutationFn: async () => {
      const d = parseBookmarkletPaste(paste, c.catalog);
      return { r: await audit(d.items, 'bookmarklet', 'manapool'), source: 'bookmarklet' as const, store: 'manapool' as const, warnings: warningLines(d.warnings, c.catalog) };
    },
    onSuccess: (r) => { setResult(r); void qc.invalidateQueries({ queryKey: ['scrapers', 'health'] }); },
    onError: (e) => {
      if (!(e instanceof CompanionError)) return;
      trackCompanionError(e.code);
      void reportScraperFailure(e.code, qc);
    },
  });
  const viaAccount = useMutation({
    mutationFn: async () => ({ r: unwrap(await cartCheck({ body: { family: family ?? null } })), source: 'account' as const, store: 'manapool' as const, warnings: [] }),
    onSuccess: setResult,
  });
  const busy = viaCompanion.isPending || viaPaste.isPending || viaAccount.isPending;

  return (
    <>
      <div className="flex flex-col gap-2 border-b-2 border-rule-strong px-5 pb-3 pt-5">
        <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Check my cart</Dialog.Title>
        <Dialog.Description className="text-md leading-relaxed text-ink-muted">
          Finds cards you’re buying twice, already own, or are paying over market for — and set gaps still missing from the cart.
        </Dialog.Description>
        {!result && <StoreSwitch value={store} onChange={(s) => { setStore(s); viaCompanion.reset(); }} disabled={busy} />}
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
        {result ? (
          <div className="flex flex-col gap-3">
            <p className="text-sm text-ink-muted">{CART_STORE_NAME[result.store]} cart · {SOURCE_LABEL[result.source]}.</p>
            {result.warnings.map((w) => <p key={w} role="status" className="text-md leading-relaxed text-ink">{w}</p>)}
            <Results r={result.r} />
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            <ScraperNotice down={cartDown} />
            {companionOn && (
              <section aria-labelledby="cart-companion" className="flex flex-col gap-2">
                <h3 id="cart-companion" className={H3}>In this browser</h3>
                {c.status === 'ready' ? (
                  <>
                    <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">{READS[store]}</p>
                    {!allowed && <p role="status" className="max-w-[62ch] text-md leading-relaxed text-ink">{cartSwitchHint(store)}</p>}
                  </>
                ) : (
                  <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
                    {c.status === 'checking' ? 'Looking for the browser companion…' : 'Set up the browser companion first — the plug icon at the top of the app.'}
                  </p>
                )}
                <Button tone="paper" emphasis="primary" className="self-start" onClick={() => viaCompanion.mutate()} disabled={c.status !== 'ready' || !allowed || busy}>
                  {viaCompanion.isPending ? (awaiting != null ? 'Waiting for approval…' : 'Reading your cart…') : 'Read my cart'}
                </Button>
                {awaiting != null && <AwaitingNote summary={awaiting} />}
                {viaCompanion.isError && <FailureNote error={viaCompanion.error} />}
              </section>
            )}
            {store === 'manapool' && <section aria-labelledby="cart-bookmarklet" className="flex flex-col gap-2">
              <h3 id="cart-bookmarklet" className={H3}>With the bookmarklet</h3>
              <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">
                No install: drag this to your bookmarks bar, click it on your Mana Pool cart page, then paste here. It copies only the cart’s cards, quantities, finishes and prices.
              </p>
              {bookmarklet.data && <BookmarkletLink href={bookmarklet.data.href} label="mm · Mana Pool cart" />}
              <label className="flex flex-col gap-1.5 text-sm voice-semi text-ink-muted">
                Paste what it copied
                <textarea
                  value={paste}
                  onChange={(e) => setPaste(e.target.value)}
                  rows={3}
                  spellCheck={false}
                  className="rounded-sm border border-rule-strong bg-paper-raised px-3 py-2 font-mono text-sm text-ink placeholder:text-ink-muted focus-visible:border-accent"
                  placeholder='{"source":"manapool-cart-page", …}'
                />
              </label>
              <Button tone="paper" className="self-start" onClick={() => viaPaste.mutate()} disabled={!paste.trim() || busy}>
                {viaPaste.isPending ? 'Checking…' : 'Check pasted cart'}
              </Button>
              {viaPaste.isError && <FailureNote error={viaPaste.error} />}
            </section>}
            {store === 'manapool' && serverLogin && setup.data?.account && (
              <section aria-labelledby="cart-account" className="flex flex-col gap-2">
                <h3 id="cart-account" className={H3}>With your login on this computer</h3>
                <p className="max-w-[62ch] text-md leading-relaxed text-ink-muted">Uses the Mana Pool login in this computer’s .env file. Only works where the app runs on your own computer.</p>
                <Button tone="paper" className="self-start" onClick={() => viaAccount.mutate()} disabled={busy}>
                  {viaAccount.isPending ? 'Reading your cart…' : 'Read with my login'}
                </Button>
                {viaAccount.isError && <FailureNote error={viaAccount.error} />}
              </section>
            )}
          </div>
        )}
      </div>
      {result && (
        <div className="flex justify-end gap-2 border-t border-rule px-5 py-3">
          <Button tone="paper" onClick={() => { setResult(null); viaCompanion.reset(); viaPaste.reset(); viaAccount.reset(); }}>Check again</Button>
        </div>
      )}
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
        {r.owned.map((o, i) => <Line key={`${o.scryfall_id}${o.fin}${i}`} card={o} right={<>you own {fmtInt(o.owned_qty)} · {fmtUsd(o.your)}</>} />)}
      </Section>
      <Section title="Over market" n={r.overpay.length} empty="Nothing is priced well over market.">
        {r.overpay.map((o, i) => (
          <Line key={`${o.scryfall_id}${o.fin}${i}`} card={o} right={<><span className="text-ink">{fmtUsd(o.your)}</span> vs {fmtUsd(o.market)} · <span className="font-medium text-danger">+{Math.round(o.pct ?? 0)}%</span></>} />
        ))}
      </Section>
      {(r.not_compared ?? 0) > 0 && (
        <p className="-mt-3 max-w-[62ch] text-sm text-ink-muted">
          {fmtCount(r.not_compared ?? 0, 'played or non-English line')} left out — market prices are Near Mint English.
        </p>
      )}
      {r.family && (
        <Section title={`Still missing from ${r.family.toUpperCase()}`} n={r.missing.length} meta={r.missing.length ? `≈ ${fmtUsd(missingCost)}` : undefined} empty="The cart completes the family.">
          {r.missing.slice(0, 60).map((m) => <Line key={`${m.scryfall_id}${m.fin}`} card={m} right={fmtUsd(m.market)} />)}
          {r.missing.length > 60 && <li className="py-1.5 text-sm text-ink-muted">…and {fmtInt(r.missing.length - 60)} more — see Collection, Missing.</li>}
        </Section>
      )}
      {(r.not_cards ?? []).length > 0 && (
        <Section title="Not single cards" n={(r.not_cards ?? []).length}>
          {(r.not_cards ?? []).map((n, i) => (
            <li key={i} className="flex items-baseline gap-3 border-b border-rule py-1.5 text-sm">
              <span className="min-w-0 flex-1 text-ink">{n.name ?? 'Unnamed item'} <span className="ml-2 text-xs text-ink-muted">{n.kind === 'sealed' ? 'sealed · not checked' : 'not checked'}</span></span>
              <span className="shrink-0 tabular text-ink-muted">{n.qty > 1 ? `${fmtInt(n.qty)} × ` : ''}{fmtUsd(n.price)}</span>
            </li>
          ))}
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

function Line({ card, right }: { card: { name: string; set: string; num: string; fin?: string; condition?: string | null; language?: string | null }; right: ReactNode }) {
  const q = lineQualifier(card);
  return (
    <li className="flex items-baseline gap-3 border-b border-rule py-1.5 text-sm">
      <span className="min-w-0 flex-1">
        <span className="text-ink">{card.name}</span>
        <span className="ml-2 text-xs text-ink-muted">{card.set.toUpperCase()} {card.num}{card.fin === 'foil' ? ' · foil' : ''}{q ? ` · ${q}` : ''}</span>
      </span>
      <span className="shrink-0 text-right tabular text-ink-muted">{right}</span>
    </li>
  );
}

/** Which cart to check — Mana Pool, TCGplayer or Card Kingdom (the paper twin of the sidebar's Segmented). */
function StoreSwitch({ value, onChange, disabled }: { value: CartStore; onChange: (s: CartStore) => void; disabled: boolean }) {
  return (
    <ToggleGroup.Root
      type="single"
      value={value}
      onValueChange={(v) => v && onChange(v as CartStore)}
      aria-label="Store"
      disabled={disabled}
      className="mt-1 grid max-w-md auto-cols-fr grid-flow-col rounded-sm border border-rule-strong p-0.5"
    >
      {CART_STORES.map((s) => (
        <ToggleGroup.Item
          key={s}
          value={s}
          className="min-h-9 min-w-0 truncate rounded-xs px-2 text-sm voice-semi text-ink-muted cursor-pointer transition-colors ease-guide hover:text-ink disabled:cursor-not-allowed disabled:opacity-45 data-[state=on]:bg-accent data-[state=on]:text-on-accent data-[state=on]:hover:text-on-accent"
        >
          {CART_STORE_NAME[s]}
        </ToggleGroup.Item>
      ))}
    </ToggleGroup.Root>
  );
}
