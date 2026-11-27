import { useQuery } from '@tanstack/react-query';
import { useId, useState } from 'react';
import { artTagsQuery } from '../../../app/queries';
import { useDebounced } from '../../../app/useDebounced';
import { Pressable } from '../../../components/controls/Pressable';
import { RailField } from '../../../components/controls/RailField';
import { TextInput } from '../../../components/controls/TextField';
import { CloseMark } from '../../../components/icons/marks';
import { fmtInt } from '../../../core/format';

const slugify = (s: string) => s.trim().toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
const tagLabel = (slug: string) => slug.replace(/-/g, ' ');

/** Art tags (any of): a search field on chrome with suggestions from the local
 *  Scryfall tag cache; Enter adds the best match, or the typed tag as-is. */
export function ArtTagField({ value, onChange }: { value: string[]; onChange: (v: string[]) => void }) {
  const id = useId();
  const [text, setText] = useState('');
  const needle = useDebounced(text.trim(), 200);
  const res = useQuery({ ...artTagsQuery(needle), enabled: needle.length > 0 });
  const hits = needle ? (res.data?.tags ?? []).filter((t) => !value.includes(t.slug)) : [];
  const add = (slug: string) => {
    if (slug && !value.includes(slug)) onChange([...value, slug]);
    setText('');
  };
  return (
    <RailField label="Art tags" htmlFor={id}>
      {value.length > 0 && (
        <ul aria-label="Art tags" className="flex flex-wrap gap-1.5">
          {value.map((t) => (
            <li key={t}>
              <Pressable
                onClick={() => onChange(value.filter((v) => v !== t))}
                aria-label={`Remove art tag ${tagLabel(t)}`}
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
            add((text.trim() === needle && !res.isPlaceholderData ? hits[0]?.slug : undefined) ?? slugify(text));
          }
        }}
        placeholder="dragon, moon, ocean…"
        autoComplete="off"
        spellCheck={false}
        aria-describedby={`${id}-hits`}
      />
      <div id={`${id}-hits`} aria-live="polite" className="flex flex-wrap gap-1.5 empty:hidden">
        {needle && res.data && !res.data.synced && (
          <span className="text-xs leading-relaxed text-on-chrome-muted">No art tags loaded here yet — press Enter to search Scryfall for “{needle}”.</span>
        )}
        {needle && res.data?.synced && hits.length === 0 && !res.isFetching && (
          <span className="text-xs text-on-chrome-muted">No art tag matches “{needle}”.</span>
        )}
        {hits.map((t) => (
          <Pressable
            key={t.id}
            onClick={() => add(t.slug)}
            title={`${fmtInt(t.illustrations)} artworks tagged ${t.label}`}
            className="inline-flex min-h-7 items-center gap-1.5 rounded-pill border border-chrome-line px-2.5 text-xs voice-semi text-on-chrome-muted transition-colors ease-guide hover:border-on-chrome-muted hover:text-on-chrome"
          >
            {t.label} <span className="tabular opacity-75">{fmtInt(t.illustrations)}</span>
          </Pressable>
        ))}
      </div>
    </RailField>
  );
}
