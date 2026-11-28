import { useQuery } from '@tanstack/react-query';
import { Popover } from 'radix-ui';
import { useId, useMemo, useState } from 'react';
import { oracleTagsQuery } from '../../app/queries';
import { useDebounced } from '../../app/useDebounced';
import { Button } from '../../components/Button';
import { Check } from '../../components/controls/Check';
import { RailField } from '../../components/controls/RailField';
import { TextInput } from '../../components/controls/TextField';
import { triggerClass } from '../../components/controls/fieldClass';
import { menuPanelClass } from '../../components/controls/surfaces';
import { CaretMark } from '../../components/icons/marks';
import { InfoTip } from '../../components/InfoTip';
import { fmtInt } from '../../core/format';

/** A Function root; `tags` = the Tagger slugs it is built on (Blink = flicker), searched too. */
export type FunctionOption = { value: string; label: string; count: number; tags?: readonly string[] };
export type CardTagValue = { fn: string[]; ot: string[] };

const tagLabel = (slug: string) => slug.replace(/-/g, ' ');

/**
 * One picker for Scryfall Tagger card tags: the curated Function roots are the shortlist
 * shown when the search is empty; typing searches the shortlist AND every other tag
 * (the server's tag cache), each in its own section. Choices are kept as two URL keys,
 * `fn` (function roots) and `ot` (any tag slug), and a card matches ANY of them.
 */
export function CardTagPicker({ functions, value, onChange, loading }: {
  /** The Function roots with counts under the other filters; empty when no card has one. */
  functions: FunctionOption[];
  value: CardTagValue;
  onChange: (v: CardTagValue) => void;
  loading: boolean;
}) {
  const id = useId();
  const [text, setText] = useState('');
  // Tags picked when the popover opened stay listed (unticked) until it closes, so rows never jump.
  const [kept, setKept] = useState<string[]>([]);
  const needle = useDebounced(text.trim(), 200);
  const hits = useQuery({ ...oracleTagsQuery(needle), enabled: needle.length > 0 });

  const fnSet = new Set(value.fn);
  const otSet = new Set(value.ot);
  const fnLabel = useMemo(() => new Map(functions.map((f) => [f.value, f.label])), [functions]);
  const chosen = [...value.fn.map((k) => fnLabel.get(k) ?? tagLabel(k)), ...value.ot.map(tagLabel)];
  const summary = chosen.length === 0 ? 'Any function or tag' : chosen.length === 1 ? chosen[0] : `${chosen[0]} +${chosen.length - 1}`;

  const ql = text.trim().toLowerCase();
  const shownFns = ql
    ? functions.filter((f) => f.label.toLowerCase().includes(ql) || f.tags?.some((t) => tagLabel(t).includes(ql)))
    : functions;
  // The other chosen tags stay listed (checked) while the search is empty, so you can untick them here.
  const tagRows = ql
    ? (hits.data?.tags ?? []).map((t) => ({ slug: t.slug, label: t.label, cards: t.cards as number | null }))
    : [...new Set([...kept, ...value.ot])].map((slug) => ({ slug, label: tagLabel(slug), cards: null }));

  const toggleFn = (k: string) => onChange({ ...value, fn: fnSet.has(k) ? value.fn.filter((x) => x !== k) : [...value.fn, k] });
  const toggleOt = (s: string) => onChange({ ...value, ot: otSet.has(s) ? value.ot.filter((x) => x !== s) : [...value.ot, s] });

  const searching = ql.length > 0;
  const tagsPending = searching && (needle !== text.trim() || hits.isFetching);
  const row = 'flex cursor-pointer items-start gap-2.5 px-3 py-1.5 text-sm hover:bg-chrome-line';
  const head = 'px-3 pb-1 pt-2 text-xs voice-condensed uppercase tracking-caps text-on-chrome-muted';

  // Empty search: the tags you picked, above the shortlist. Searching: every Scryfall tag, below it.
  const tagSection = (
    <fieldset className={`py-0.5 ${searching ? 'border-t border-chrome-line' : 'border-b border-chrome-line'}`}>
      <legend className={`flex w-full ${head}`}>{searching ? 'All Scryfall tags' : 'Tags you picked'}</legend>
      <div aria-live="polite">
        {searching && hits.data?.synced === false && (
          <p className="px-3 py-1.5 text-sm text-on-chrome-muted">No card tags loaded yet: run “Sync card and art tags” in Jobs.</p>
        )}
        {searching && hits.data?.synced !== false && tagRows.length === 0 && (
          <p className="px-3 py-1.5 text-sm text-on-chrome-muted">{tagsPending ? 'Searching…' : `No card tag matches “${text.trim()}”.`}</p>
        )}
      </div>
      {tagRows.map((t) => (
        <label key={t.slug} className={row} title={t.cards != null ? `${fmtInt(t.cards)} cards in all of Magic carry this tag (more specific tags included)` : undefined}>
          <Check checked={otSet.has(t.slug)} onChange={() => toggleOt(t.slug)} />
          <span className="min-w-0 flex-1 truncate">{t.label}</span>
          {t.cards != null && <span className="tabular text-xs text-on-chrome-muted">{fmtInt(t.cards)}</span>}
        </label>
      ))}
    </fieldset>
  );

  return (
    <RailField
      label="Card tags"
      labelId={`${id}-l`}
      extra={
        <InfoTip label="Where do card tags come from?">
          From <b>Scryfall Tagger</b>, where Scryfall’s community tags what each card does. They load from Scryfall’s daily tag file when you run “Sync card and art tags” in Jobs.{' '}
          <b>Functions</b> are a shortlist of common roles; search to pick any other tag. A tag includes its more specific tags, and a card shows when it has <b>any</b> tag you pick.
        </InfoTip>
      }
    >
      <Popover.Root onOpenChange={(o) => { setKept(o ? value.ot : []); if (!o) setText(''); }}>
        <Popover.Trigger
          aria-labelledby={`${id}-l ${id}-s`}
          aria-busy={loading || undefined}
          disabled={loading}
          className={triggerClass('chrome')}
        >
          <span id={`${id}-s`} className={`min-w-0 flex-1 truncate ${loading || !chosen.length ? 'text-on-chrome-muted' : ''}`}>{loading ? 'Loading…' : summary}</span>
          <CaretMark className="size-icon-sm shrink-0 text-on-chrome-muted" />
        </Popover.Trigger>
        <Popover.Portal>
          <Popover.Content
            align="start"
            sideOffset={4}
            collisionPadding={12}
            className={`flex max-h-[min(32rem,75dvh)] w-[max(var(--radix-popover-trigger-width),20rem)] flex-col focus:outline-none ${menuPanelClass}`}
          >
            <div className="flex flex-col gap-2 border-b border-chrome-line p-2">
              <TextInput
                type="search"
                aria-label="Search functions and card tags"
                placeholder="Search tags: flicker, treasure…"
                autoComplete="off"
                spellCheck={false}
                value={text}
                onChange={(e) => setText(e.target.value)}
              />
              <div className="flex gap-3 text-xs">
                {chosen.length > 0 && <Button emphasis="link" onClick={() => onChange({ fn: [], ot: [] })}>Clear</Button>}
                <span className="ml-auto tabular text-on-chrome-muted">{chosen.length ? `${chosen.length} chosen` : 'Any'}</span>
              </div>
            </div>
            <div className="min-h-0 overflow-y-auto overscroll-contain py-1">
              {!searching && tagRows.length > 0 && tagSection}
              {(shownFns.length > 0 || !searching) && (
                <fieldset className="py-0.5">
                  <legend className={`flex w-full ${head}`}>{searching ? 'Functions' : 'Functions · shortlist'}</legend>
                  {shownFns.length === 0 && <p className="px-3 py-1.5 text-sm text-on-chrome-muted">No cards here have a tagged function.</p>}
                  {shownFns.map((f) => (
                    <label key={f.value} className={row}>
                      <Check checked={fnSet.has(f.value)} onChange={() => toggleFn(f.value)} />
                      <span className="min-w-0 flex-1 truncate">{f.label}</span>
                      <span className="tabular text-xs text-on-chrome-muted">{fmtInt(f.count)}</span>
                    </label>
                  ))}
                </fieldset>
              )}
              {searching && tagSection}
            </div>
          </Popover.Content>
        </Popover.Portal>
      </Popover.Root>
    </RailField>
  );
}
