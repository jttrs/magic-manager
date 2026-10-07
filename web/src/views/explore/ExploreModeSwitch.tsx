import { Segmented, SideSection } from '../../components/Sidebar';
import type { ExploreMode } from '../../core/search';

/** The first Explore control: one card in a role, or EDHREC's rankings. */
export function ExploreModeSwitch({ value, onChange }: { value: ExploreMode; onChange: (m: ExploreMode) => void }) {
  return (
    <SideSection title="Explore">
      <Segmented<ExploreMode>
        label="Explore"
        value={value}
        onChange={onChange}
        options={[{ value: 'card', label: 'A card' }, { value: 'rankings', label: 'Rankings' }]}
      />
    </SideSection>
  );
}
