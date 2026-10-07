// Commander Spellbook combos on the guide sheet: a deck's near-misses ("one
// card away") and the combos it contains, and the combos one card is part of.
// Presentational over the API shapes; view-model math lives in core/combos.
import { useQuery } from '@tanstack/react-query';
import { Dialog } from 'radix-ui';
import { useId, useState, type ReactNode } from 'react';
import { cardCombosQuery, deckCombosQuery } from '../app/queries';
import type { CardCombosOut, ComboOut, DeckCombosOut, PieceOut, PrintingOut } from '../core/api';
import { decksLine, deckCombosSummary, nearMisses, ownNote, piecesOwned, producesLine, steps, type NearMiss } from '../core/combos';
import { fmtCount, fmtUsd } from '../core/format';
import { Chevron } from './Chevron';
import { SpellbookMark } from './StoreMarks';

type Inspect = (p: PrintingOut) => void;
const crop = (url: string) => url.replace('/normal/', '/art_crop/');

/** Pieces as a "+"-joined line. `tone` decides each piece's ink. */
function Pieces({ combo, tone }: { combo: ComboOut; tone: (p: PieceOut) => 'add' | 'muted' | 'ink' }) {
  return (
    <>
      {combo.pieces.map((p, i) => {
        const t = tone(p);
        return (
          <span key={`${p.name}-${i}`}>
            {i > 0 && <span className="text-ink-muted"> + </span>}
            <span className={t === 'add' ? 'text-accent-ink' : t === 'muted' ? 'text-ink-muted' : 'text-ink'}>{p.name}</span>
          </span>
        );
      })}
    </>
  );
}

/** How the combo works: extra pieces, setup, mana, steps, and the Spellbook page. */
function ComboHow({ combo }: { combo: ComboOut }) {
  const s = steps(combo);
  return (
    <div className="ml-6 flex flex-col gap-1.5 pb-2 text-sm text-ink">
      {combo.produces.length > 2 && <Row k="Result">{combo.produces.join(' · ')}</Row>}
      {combo.requires.length > 0 && <Row k="Also needs">{combo.requires.join(' · ')}</Row>}
      {combo.prerequisites && <Row k="Setup"><span className="whitespace-pre-line">{combo.prerequisites}</span></Row>}
      {combo.mana_needed && <Row k="Mana">{combo.mana_needed}</Row>}
      {s.length > 0 && (
        <ol className="ml-4 list-decimal text-ink marker:text-ink-muted">
          {s.map((line, i) => <li key={i} className="pl-1">{line}</li>)}
        </ol>
      )}
      <a href={combo.url} target="_blank" rel="noreferrer" title="Open on Commander Spellbook" className="-ml-2 inline-flex min-h-8 items-center gap-1.5 self-start rounded-sm px-2 text-sm voice-semi font-medium text-accent-ink no-underline transition-colors duration-150 ease-guide hover:bg-paper-sunk focus-visible:bg-paper-sunk">
        <SpellbookMark className="size-4" /> Commander Spellbook<span className="sr-only">(opens in a new tab)</span>
      </a>
    </div>
  );
}

function Row({ k, children }: { k: string; children: ReactNode }) {
  return (
    <p className="flex gap-2">
      <span className="w-20 shrink-0 text-ink-muted">{k}</span>
      <span className="min-w-0 flex-1">{children}</span>
    </p>
  );
}

function Disclosure({ head, children, label }: { head: ReactNode; children: ReactNode; label: string }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  return (
    <>
      <button type="button" aria-expanded={open} aria-controls={id} aria-label={label} onClick={() => setOpen(!open)} className="flex w-full min-w-0 cursor-pointer items-start gap-2 rounded-xs py-1.5 text-left hover:bg-paper-sunk focus-visible:bg-paper-sunk">
        <Chevron dir={open ? 'down' : 'right'} className="mt-1 size-3.5 shrink-0 text-ink-muted" />
        <span className="flex min-w-0 flex-1 flex-col">{head}</span>
      </button>
      {open && <div id={id}>{children}</div>}
    </>
  );
}

/** One combo: its pieces, what it does, and (disclosed) how it works. */
function ComboLine({ combo, tone, extra }: { combo: ComboOut; tone: (p: PieceOut) => 'add' | 'muted' | 'ink'; extra?: string }) {
  const meta = [producesLine(combo), decksLine(combo), extra].filter(Boolean).join(' · ');
  return (
    <li className="ruled">
      <Disclosure label={`${combo.pieces.map((p) => p.name).join(' + ')} — how it works`} head={
        <>
          <span className="text-md voice-semi font-medium leading-snug"><Pieces combo={combo} tone={tone} /></span>
          <span className="text-xs tabular text-ink-muted">{meta}</span>
        </>
      }>
        <ComboHow combo={combo} />
      </Disclosure>
    </li>
  );
}

/** A card that would complete near-miss combos, with Add when the editor offers it. */
function NearMissLine({ nm, onAdd, onInspect }: { nm: NearMiss; onAdd?: (p: PrintingOut) => void; onInspect?: Inspect }) {
  const [open, setOpen] = useState(false);
  const id = useId();
  const { piece } = nm.card;
  const pr = piece.printing;
  const own = ownNote(piece);
  const img = pr?.image_uri ? crop(pr.image_uri) : piece.image_uri;
  return (
    <li className="ruled">
      <div className="flex items-center gap-3 py-1.5">
        {img ? <img src={img} alt="" loading="lazy" decoding="async" className="size-10 shrink-0 rounded-xs object-cover" /> : <span aria-hidden="true" className="size-10 shrink-0 rounded-xs border border-rule bg-paper-sunk" />}
        <span className="flex min-w-0 flex-1 flex-col">
          {pr && onInspect ? (
            <button type="button" onClick={() => onInspect(pr)} className="min-w-0 cursor-pointer self-start truncate text-left text-md voice-semi font-medium text-ink underline-offset-4 decoration-rule-strong hover:underline focus-visible:underline">{piece.name}</button>
          ) : <span className="truncate text-md voice-semi font-medium text-ink">{piece.name}</span>}
          <span className="truncate text-xs tabular text-ink-muted">
            <button type="button" aria-expanded={open} aria-controls={id} onClick={() => setOpen(!open)} className="cursor-pointer text-ink underline decoration-rule-strong underline-offset-2 hover:decoration-ink">
              Completes {fmtCount(nm.combos.length, 'combo')}
            </button>
            {' · '}<span className={own.free ? 'text-accent-ink' : ''}>{own.text}</span>
            {' · '}from {fmtUsd(piece.facts.lowest_usd)}
          </span>
        </span>
        {onAdd && pr && (
          <button type="button" aria-label={`Add ${piece.name}`} onClick={() => onAdd(pr)} className="touch-hit grid size-9 shrink-0 cursor-pointer place-items-center rounded-sm text-xl text-accent-ink hover:bg-paper-sunk">+</button>
        )}
      </div>
      {open && (
        <ul id={id} className="mb-1.5 ml-[3.25rem] border-l border-rule pl-3">
          {nm.combos.map((c) => (
            <ComboLine key={c.id} combo={c} tone={(p) => (p.in_deck ? 'ink' : 'add')} />
          ))}
        </ul>
      )}
    </li>
  );
}

function Head({ children, count }: { children: ReactNode; count: string }) {
  return (
    <h3 className="mt-4 flex items-baseline gap-2 border-b-2 border-rule-strong pb-0.5 text-lg voice-condensed font-bold uppercase tracking-[0.04em] text-ink first:mt-0">
      {children}<span className="ml-auto text-sm font-regular normal-case tracking-normal tabular text-ink-muted">{count}</span>
    </h3>
  );
}

function Status({ pending, error, unavailable }: { pending: boolean; error: unknown; unavailable?: string | null }) {
  if (pending) return <p role="status" className="py-4 text-sm text-ink-muted">Asking Commander Spellbook…</p>;
  const msg = unavailable ?? (error ? (error as Error).message : null);
  return msg ? <p role="alert" className="py-4 text-sm text-danger">{msg}</p> : null;
}

/** A deck's combos: near-misses first (what to add), then what's already in it. */
export function DeckCombosBody({ data, pending, error, onAdd, onInspect }: { data?: DeckCombosOut; pending: boolean; error: unknown; onAdd?: (p: PrintingOut) => void; onInspect?: Inspect }) {
  if (!data || !data.available) return <Status pending={pending && !data} error={error} unavailable={data?.error} />;
  const misses = nearMisses(data);
  return (
    <div className="flex flex-col">
      <p className="pb-2 text-sm tabular text-ink-muted" aria-live="polite">{deckCombosSummary(data)}{pending ? ' · updating…' : ''}</p>
      <Head count={fmtCount(misses.length, 'card')}>One card away</Head>
      {misses.length ? (
        <ul>{misses.map((nm) => <NearMissLine key={nm.card.piece.oracle_id ?? nm.card.piece.name} nm={nm} onAdd={onAdd} onInspect={onInspect} />)}</ul>
      ) : <p className="py-2 text-sm text-ink-muted">No combo in this deck’s colours is one card away.</p>}
      <Head count={fmtCount(data.included.length, 'combo')}>In this deck</Head>
      {data.included.length ? (
        <ul>{data.included.map((c) => <ComboLine key={c.id} combo={c} tone={() => 'ink'} />)}</ul>
      ) : <p className="py-2 text-sm text-ink-muted">No known combos yet.</p>}
      <p className="mt-3 text-xs text-ink-muted">Combos from Commander Spellbook, in the deck’s colours. Prices are the cheapest printing; free = copies no built deck has pledged.</p>
    </div>
  );
}

/** Deck Manager: the deck's combos in a dialog, fetched when opened. */
export function DeckCombosDialog({ slug, deckName, trigger }: { slug: string; deckName: string; trigger: ReactNode }) {
  const [open, setOpen] = useState(false);
  const q = useQuery(deckCombosQuery(slug, open));
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <Dialog.Trigger asChild>{trigger}</Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(44rem,calc(100dvh-1.5rem))] w-[min(40rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <header className="flex items-start gap-3 border-b-2 border-rule-strong px-5 pb-2 pt-4">
            <div className="min-w-0 flex-1">
              <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Combos</Dialog.Title>
              <Dialog.Description className="mt-1 truncate text-sm text-ink-muted">{deckName}</Dialog.Description>
            </div>
            <Dialog.Close className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-xl text-ink-muted hover:bg-paper-sunk hover:text-ink" aria-label="Close">×</Dialog.Close>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 pt-3">
            <DeckCombosBody data={q.data} pending={q.isFetching} error={q.error} />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

/** Explore: the most popular combos a card is part of, each piece marked by what you own. */
export function CardCombos({ name }: { name: string }) {
  const q = useQuery(cardCombosQuery(name));
  const d: CardCombosOut | undefined = q.data;
  if (!d || !d.available) return <Status pending={q.isPending} error={q.error} unavailable={d?.error} />;
  if (!d.combos.length) return <p className="py-2 text-sm text-ink-muted">Commander Spellbook knows no combos with {name}.</p>;
  return (
    <ul>
      {d.combos.map((c) => {
        const o = piecesOwned(c);
        return <ComboLine key={c.id} combo={c} tone={(p) => ((p.facts.owned ?? 0) > 0 ? 'ink' : 'muted')} extra={`you own ${o.owned} of ${o.total}`} />;
      })}
    </ul>
  );
}
