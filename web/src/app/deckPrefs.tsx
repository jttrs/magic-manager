// Decks preferences kept in this browser: how many cards short a recipe may be and still
// count as Buildable (the Decks rail's "Decklist status"). Shared by the list and Settings → Decks.
import { useMemo } from 'react';
import { SettingsRow } from '../components/settings/SettingsControls';
import { DEFAULT_BUILDABLE_SHORT } from '../core/decks';
import { fmtCount } from '../core/format';
import { createLocalPref } from './localPref';
import { useSettingsSection } from './settings';
import { RangeInput } from '../components/controls/Inputs';

const MAX = 10;

/** The stored cards-short threshold; anything missing or out of range is the default. */
export function parseBuildableShort(raw: string | null): number {
  if (raw == null) return DEFAULT_BUILDABLE_SHORT;
  const n = Number(raw);
  return Number.isInteger(n) && n >= 0 && n <= MAX ? n : DEFAULT_BUILDABLE_SHORT;
}

const pref = createLocalPref({ key: 'mm.decks.buildableShort', parse: parseBuildableShort, serialize: String });

/** Cards a recipe may be short of and still count as Buildable (0–10, default 3). */
export const useBuildableShort = pref.use;

/** Settings → Decks, while the Decks view is mounted. */
export function useDecksSettings() {
  const short = useBuildableShort();
  const section = useMemo(() => ({
    id: 'decks',
    title: 'Decks',
    content: (
      <SettingsRow
        label={`Buildable when short at most ${fmtCount(short, 'card')}`}
        description={short === 0 ? 'A recipe is Buildable only when every card is in your unused cards.' : `A recipe you haven’t built counts as Buildable when your unused cards leave it ${fmtCount(short, 'card')} or fewer short.`}
        control={({ labelId, descriptionId }) => (
          <div className="flex items-center gap-3 sm:min-w-[15rem]">
            <RangeInput min={0} max={MAX} value={short} aria-labelledby={labelId} aria-describedby={descriptionId} onChange={pref.set} />
            <span className="w-6 text-right tabular text-sm">{short}</span>
          </div>
        )}
      />
    ),
  }), [short]);
  useSettingsSection(section);
}
