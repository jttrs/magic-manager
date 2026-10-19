import { SectionTabs } from '../../components/SectionTabs';
import type { CompareSearch, ExploreMode } from '../../core/search';

const MODES: { mode: ExploreMode; label: string }[] = [
  { mode: 'rankings', label: 'Rankings' },
  { mode: 'card', label: 'Cards' },
  { mode: 'surf', label: 'Surfer' },
];

/** Explore's modes, as tabs across the top of the sheet: EDHREC's rankings, specific cards, or the random-card surfer. */
export function ExploreTabs({ mode }: { mode: ExploreMode }) {
  return (
    <SectionTabs
      label="Explore views"
      tabs={MODES.map((m) => ({
        id: m.mode,
        label: m.label,
        active: m.mode === mode,
        link: { to: '/explore', search: ((s: CompareSearch) => ({ ...s, mode: m.mode })) as never },
      }))}
    />
  );
}
