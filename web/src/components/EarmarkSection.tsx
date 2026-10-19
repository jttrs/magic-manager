import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ToggleGroup } from 'radix-ui';
import { useId, useState } from 'react';
import { cardEarmarksQuery, decksQuery, unwrap } from '../app/queries';
import { cardEarmarkRemove, cardEarmarkSave, type CardEarmarkIn, type CardEarmarkOut } from '../core/api';
import { findEarmark, REASON_LABEL, type EarmarkReason } from '../core/cardEarmarks';
import type { GuideCard } from '../core/guideCard';
import { Button } from './Button';

type Draft = Omit<CardEarmarkIn, 'card'>;
const fromMark = (m: CardEarmarkOut): Draft => ({ printing: m.scryfall_id, finish: m.finish, reason: m.reason, deck: m.deck_slug, note: m.note });

/** The inspector's Earmark section: mark a card you're interested in (owned or not),
 *  and say why — to collect, or a deck idea (optionally for one deck), a preferred
 *  printing, a note. Every change saves at once. */
export function EarmarkSection({ card }: { card: GuideCard }) {
  const qc = useQueryClient();
  const id = useId();
  const list = useQuery(cardEarmarksQuery());
  const hit = findEarmark(list.data, card.name);
  const mark = hit?.earmark;
  const [error, setError] = useState('');
  const done = () => Promise.all(['cardEarmarks', 'collection'].map((k) => qc.invalidateQueries({ queryKey: [k] })));
  const save = useMutation({
    mutationFn: async (d: Draft) => unwrap(await cardEarmarkSave({ body: { card: card.scryfallId ?? card.name, ...d } })),
    onMutate: () => setError(''),
    onError: (e) => setError((e as Error).message),
    onSettled: done,
  });
  const remove = useMutation({
    mutationFn: async (oracleId: string) => unwrap(await cardEarmarkRemove({ path: { oracle_id: oracleId } })),
    onMutate: () => setError(''),
    onError: (e) => setError((e as Error).message),
    onSettled: done,
  });
  const busy = save.isPending || remove.isPending;
  const cur: Draft = mark ? fromMark(mark) : {};
  const change = (patch: Partial<Draft>) => save.mutate({ ...cur, ...patch });
  const here = card.scryfallId && card.setCode ? `${card.setCode.toUpperCase()} #${card.cn}` : null;
  const prefersHere = Boolean(mark?.scryfall_id && mark.scryfall_id === card.scryfallId);

  return (
    <section aria-labelledby={id} className="flex flex-col gap-2">
      <div className="flex items-center gap-3 border-b border-rule pb-1">
        <h3 id={id} className="text-sm voice-semi font-medium text-ink">Earmark</h3>
        <Button
          tone="paper"
          emphasis={mark ? 'primary' : 'quiet'}
          aria-pressed={Boolean(mark)}
          disabled={busy || list.isPending}
          onClick={() => (mark ? remove.mutate(mark.oracle_id) : save.mutate({}))}
          className="ml-auto min-h-8"
        >
          {mark ? 'Earmarked' : 'Earmark'}
        </Button>
      </div>
      {!mark ? (
        <p className="text-sm text-ink-muted">Earmark cards you’re interested in — to collect, or for a deck idea. They show in Explore and in the deck editor.</p>
      ) : (
        <div className="flex flex-col gap-2 text-sm">
          <ToggleGroup.Root
            type="single"
            value={mark.reason ?? ''}
            onValueChange={(v) => change({ reason: (v || null) as EarmarkReason | null, deck: v === 'deck' ? cur.deck : null })}
            aria-label="Why"
            className="inline-grid grid-flow-col self-start rounded-sm border border-rule p-0.5"
          >
            {(Object.keys(REASON_LABEL) as EarmarkReason[]).map((r) => (
              <ToggleGroup.Item key={r} value={r} disabled={busy} className="min-h-8 cursor-pointer rounded-xs px-2.5 text-xs voice-semi text-ink-muted hover:text-ink data-[state=on]:bg-paper-sunk data-[state=on]:text-ink">
                {REASON_LABEL[r]}
              </ToggleGroup.Item>
            ))}
          </ToggleGroup.Root>
          {mark.reason === 'deck' && <DeckPick value={mark.deck_slug} disabled={busy} onChange={(deck) => change({ deck })} />}
          {here && (
            <label className="inline-flex cursor-pointer items-center gap-1.5">
              <input
                type="checkbox"
                checked={prefersHere}
                disabled={busy}
                onChange={(e) => change(e.target.checked ? { printing: card.scryfallId, finish: null } : { printing: null, finish: null })}
                className="accent-[var(--theme-accent)]"
              />
              Prefer this printing ({here})
            </label>
          )}
          {mark.scryfall_id && !prefersHere && <p className="text-xs text-ink-muted">Prefers another printing.</p>}
          {prefersHere && card.prices?.foil != null && card.prices?.nonfoil != null && (
            <label className="inline-flex cursor-pointer items-center gap-1.5">
              <input type="checkbox" checked={mark.finish === 'foil'} disabled={busy} onChange={(e) => change({ finish: e.target.checked ? 'foil' : 'nonfoil' })} className="accent-[var(--theme-accent)]" />
              Foil
            </label>
          )}
          <NoteField key={mark.updated_at} value={mark.note ?? ''} disabled={busy} onSave={(note) => change({ note: note || null })} />
        </div>
      )}
      {error && <p role="alert" className="text-sm text-danger">{error}</p>}
    </section>
  );
}

function DeckPick({ value, disabled, onChange }: { value: string | null; disabled: boolean; onChange: (slug: string | null) => void }) {
  const q = useQuery(decksQuery());
  const decks = (q.data ?? []).filter((d) => d.origin !== 'precon').sort((a, b) => a.name.localeCompare(b.name));
  return (
    <label className="flex flex-col gap-1 text-ink-muted">
      For deck
      <select
        value={value ?? ''}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value || null)}
        className="h-9 cursor-pointer rounded-sm border border-rule bg-paper-raised px-2 text-sm text-ink focus-visible:border-accent"
      >
        <option value="">Any deck</option>
        {decks.map((d) => <option key={d.slug} value={d.slug}>{d.name}</option>)}
      </select>
    </label>
  );
}

function NoteField({ value, disabled, onSave }: { value: string; disabled: boolean; onSave: (v: string) => void }) {
  const [text, setText] = useState(value);
  const commit = () => text.trim() !== value && onSave(text.trim());
  return (
    <label className="flex flex-col gap-1 text-ink-muted">
      Note
      <input
        value={text}
        maxLength={500}
        disabled={disabled}
        placeholder="Why it caught your eye"
        onChange={(e) => setText(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
        className="h-9 rounded-sm border border-rule bg-paper-raised px-2 text-sm text-ink placeholder:text-ink-muted focus-visible:border-accent"
      />
    </label>
  );
}
