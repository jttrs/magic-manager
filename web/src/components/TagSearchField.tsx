import { useId, useState, type ReactNode } from 'react';
import { useDebounced } from '../app/useDebounced';
import { fmtInt } from '../core/format';
import { Pressable } from './controls/Pressable';
import { RailField } from './controls/RailField';
import { TextInput } from './controls/TextField';
import { CloseMark } from './icons/marks';

export type TagHit = { id: string; slug: string; label: string; count: number };
export type TagHits = { synced?: boolean; tags: TagHit[]; fetching: boolean; stale: boolean };

const slugify = (s: string) => s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const tagLabel = (slug: string) => slug.replace(/-/g, ' ');

/** A rail field that picks Scryfall Tagger tags (any of): chosen tags as removable
 *  chips, a search box with suggestions from the local tag cache; Enter adds the best
 *  match (or, with `freeText`, the typed tag as-is). Shared by art tags and oracle tags. */
export function TagSearchField({ label, noun, placeholder, value, onChange, useHits, countTitle, unsyncedNote, freeText = false, labelExtra }: {
  label: string;
  /** An ⓘ beside the label. */
  labelExtra?: ReactNode;
  /** Singular, for messages: "art tag", "oracle tag". */
  noun: string;
  placeholder: string;
  value: string[];
  onChange: (v: string[]) => void;
  /** The suggestions for a (debounced) needle; `enabled` only when it's non-empty. */
  useHits: (needle: string) => TagHits;
  /** Tooltip for a suggestion: "3,195 cards tagged burn". */
  countTitle: (t: TagHit) => string;
  /** What to say when the tag cache isn't loaded yet. */
  unsyncedNote: (needle: string) => string;
  freeText?: boolean;
}) {
  const id = useId();
  const [text, setText] = useState('');
  const needle = useDebounced(text.trim(), 200);
  const res = useHits(needle);
  const hits = needle ? res.tags.filter((t) => !value.includes(t.slug)) : [];
  const add = (slug: string | undefined) => {
    if (slug && !value.includes(slug)) onChange([...value, slug]);
    setText('');
  };
  return (
    <RailField label={label} htmlFor={id} extra={labelExtra}>
      {value.length > 0 && (
        <ul aria-label={label} className="flex flex-wrap gap-1.5">
          {value.map((t) => (
            <li key={t}>
              <Pressable
                onClick={() => onChange(value.filter((v) => v !== t))}
                aria-label={`Remove ${noun} ${tagLabel(t)}`}
                className="inline-flex min-h-7 items-center gap-1.5 rounded-pill border border-accent bg-accent px-2.5 text-xs voice-semi text-on-accent"
              >
                {tagLabel(t)} <CloseMark className="size-icon-xs" />
              </Pressable>
            </li>
          ))}
        </ul>
      )}
      <TextInput
        id={id}
        type="search"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            const best = text.trim() === needle && !res.stale ? hits[0]?.slug : undefined;
            add(best ?? (freeText ? slugify(text) : undefined));
          }
        }}
        placeholder={placeholder}
        autoComplete="off"
        spellCheck={false}
        aria-describedby={`${id}-hits`}
      />
      <div id={`${id}-hits`} aria-live="polite" className="flex flex-wrap gap-1.5 empty:hidden">
        {needle && res.synced === false && <span className="text-xs leading-relaxed text-on-chrome-muted">{unsyncedNote(needle)}</span>}
        {needle && res.synced && hits.length === 0 && !res.fetching && <span className="text-xs text-on-chrome-muted">No {noun} matches “{needle}”.</span>}
        {hits.map((t) => (
          <Pressable
            key={t.id}
            onClick={() => add(t.slug)}
            title={countTitle(t)}
            className="inline-flex min-h-7 items-center gap-1.5 rounded-pill border border-chrome-line px-2.5 text-xs voice-semi text-on-chrome-muted transition-colors ease-guide hover:border-on-chrome-muted hover:text-on-chrome"
          >
            {t.label} <span className="tabular opacity-75">{fmtInt(t.count)}</span>
          </Pressable>
        ))}
      </div>
    </RailField>
  );
}
