import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { Button } from '../../components/Button';
import { Segmented, SideSection } from '../../components/Sidebar';
import { SurfMark } from '../../components/StoreMarks';
import type { ExploreMode } from '../../core/search';
import { CardSurfer } from './surf/CardSurfer';

const route = getRouteApi('/explore');

/** The first Explore control: one card, or EDHREC's rankings — plus the card
 *  surfer (random cards, full-screen), open whenever the URL carries `surf`. */
export function ExploreModeSwitch({ value, onChange }: { value: ExploreMode; onChange: (m: ExploreMode) => void }) {
  const { surf } = route.useSearch();
  const navigate = useNavigate({ from: '/explore' });
  const setSurf = (v: string | undefined) => navigate({ search: (s) => ({ ...s, surf: v }), replace: true });
  return (
    <SideSection title="Explore">
      <Segmented<ExploreMode>
        label="Explore"
        value={value}
        onChange={onChange}
        options={[{ value: 'card', label: 'A card' }, { value: 'rankings', label: 'Rankings' }]}
      />
      <Button className="justify-start" onClick={() => setSurf('on')}>
        <SurfMark className="size-[1.15rem] text-accent" />
        Surf random cards
      </Button>
      <CardSurfer raw={surf} onChange={setSurf} onClose={() => setSurf(undefined)} />
    </SideSection>
  );
}
