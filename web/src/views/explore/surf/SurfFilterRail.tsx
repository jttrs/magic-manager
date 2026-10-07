import { useQuery } from '@tanstack/react-query';
import { ToggleGroup } from 'radix-ui';
import { useState } from 'react';
import { surfOptionsQuery } from '../../../app/queries';
import { MultiSelect } from '../../../components/MultiSelect';
import { Segmented, SideSection } from '../../../components/Sidebar';
import { activeFilters, COLOR_NAME, COLORS, EMPTY_FILTERS, toggleColor, type SurfFilters, type SurfSource, type SurfState } from '../../../core/surf';
import { ArtTagField } from './ArtTagField';

/** The surfer's filter rail (chrome): source, then art, set, colour identity,
 *  flavor text, card type, legendary, rarity, treatment and artist. */
export function SurfFilterRail({ state, onChange }: { state: SurfState; onChange: (s: SurfState) => void }) {
  const f = state.filters;
  const opts = useQuery(surfOptionsQuery());
  const setF = (patch: Partial<SurfFilters>) => onChange({ ...state, filters: { ...f, ...patch } });
  const active = activeFilters(f);
  return (
    <div className="flex flex-col gap-6">
      <SideSection title="Draw from">
        <Segmented<SurfSource>
          label="Draw from"
          value={state.source}
          onChange={(source) => onChange({ ...state, source })}
          options={[{ value: 'scryfall', label: 'All of Magic' }, { value: 'owned', label: 'Your cards' }]}
        />
      </SideSection>

      <SideSection title="Art & printing">
        <ArtTagField value={f.art} onChange={(art) => setF({ art })} />
        <MultiSelect
          label="Set"
          noun="sets"
          summary={f.families.length ? undefined : 'Any set'}
          value={f.families}
          onChange={(families) => setF({ families })}
          options={(opts.data?.families ?? []).map((o) => ({ value: o.value, label: o.year ? `${o.label} · ${o.year}` : o.label }))}
        />
        <MultiSelect
          label="Treatment"
          noun="treatments"
          searchable={false}
          keepOrder
          summary={f.treatments.length ? undefined : 'Any treatment'}
          value={f.treatments}
          onChange={(treatments) => setF({ treatments })}
          options={opts.data?.treatments ?? []}
        />
        <ArtistField key={f.artist} value={f.artist} onChange={(artist) => setF({ artist })} />
      </SideSection>

      <SideSection title="Card">
        <ColorPips value={f.colors} onChange={(colors) => setF({ colors })} />
        {f.colors && f.colors !== 'c' && (
          <Segmented
            label="Colour match"
            value={f.color_match}
            onChange={(color_match) => setF({ color_match })}
            options={[{ value: 'exact', label: 'Exactly these' }, { value: 'within', label: 'Within these' }]}
          />
        )}
        <Segmented
          label="Flavor text"
          showLabel
          value={f.flavor}
          onChange={(flavor) => setF({ flavor })}
          options={[{ value: 'any', label: 'Any' }, { value: 'has', label: 'Has it' }, { value: 'none', label: 'None' }]}
        />
        <MultiSelect
          label="Card type"
          noun="types"
          searchable={false}
          keepOrder
          summary={f.types.length ? undefined : 'Any type'}
          value={f.types}
          onChange={(types) => setF({ types })}
          options={opts.data?.types ?? []}
        />
        <Segmented
          label="Legendary"
          showLabel
          value={f.legendary}
          onChange={(legendary) => setF({ legendary })}
          options={[{ value: 'any', label: 'Any' }, { value: 'only', label: 'Legendary' }, { value: 'not', label: 'Not' }]}
        />
        <MultiSelect
          label="Rarity"
          noun="rarities"
          searchable={false}
          keepOrder
          summary={f.rarity.length ? undefined : 'Any rarity'}
          value={f.rarity}
          onChange={(rarity) => setF({ rarity })}
          options={opts.data?.rarities ?? []}
        />
      </SideSection>

      {active > 0 && (
        <button type="button" onClick={() => setF(EMPTY_FILTERS)} className="self-start cursor-pointer text-sm text-on-chrome-muted underline hover:text-on-chrome">
          Reset filters · {active}
        </button>
      )}
    </div>
  );
}

/** Colour identity as WUBRG + C pips: letters on the chips, full names for
 *  assistive tech. Colourless and colours exclude each other. */
function ColorPips({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex flex-col gap-1.5">
      <span id="surf-ci" className="text-sm voice-semi text-on-chrome-muted">Colour identity</span>
      <ToggleGroup.Root
        type="multiple"
        aria-labelledby="surf-ci"
        value={[...value]}
        onValueChange={(next) => {
          const changed = COLORS.find((c) => next.includes(c) !== value.includes(c));
          if (changed) onChange(toggleColor(value, changed));
        }}
        className="flex gap-1.5"
      >
        {COLORS.map((c) => (
          <ToggleGroup.Item
            key={c}
            value={c}
            aria-label={COLOR_NAME[c]}
            title={COLOR_NAME[c]}
            className="grid size-8 cursor-pointer place-items-center rounded-pill border border-chrome-line text-sm voice-semi uppercase text-on-chrome-muted transition-[color,background-color,border-color] ease-guide hover:border-on-chrome-muted hover:text-on-chrome data-[state=on]:border-accent data-[state=on]:bg-accent data-[state=on]:text-on-accent"
          >
            {c}
          </ToggleGroup.Item>
        ))}
      </ToggleGroup.Root>
    </div>
  );
}

/** Artist name, applied on Enter or when the field loses focus (keyed by the
 *  applied value, so a reset clears the text). */
function ArtistField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [text, setText] = useState(value);
  const commit = () => text.trim() !== value && onChange(text.trim());
  return (
    <label className="flex flex-col gap-1.5 text-sm voice-semi text-on-chrome-muted">
      Artist
      <input
        name="surf-artist"
        type="search"
        autoComplete="off"
        spellCheck={false}
        value={text}
        placeholder="e.g. Rebecca Guay"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && commit()}
        onBlur={commit}
        className="min-h-9 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 text-md text-on-chrome placeholder:text-on-chrome-muted focus-visible:border-accent"
      />
    </label>
  );
}
