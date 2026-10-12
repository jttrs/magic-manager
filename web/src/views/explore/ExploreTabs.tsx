import { getRouteApi, useNavigate } from '@tanstack/react-router';
import { Button } from '../../components/Button';
import { SectionTabs } from '../../components/SectionTabs';
import { SideSection } from '../../components/Sidebar';
import { SurfMark } from '../../components/StoreMarks';
import type { CompareSearch, ExploreMode } from '../../core/search';
import { CardSurfer } from './surf/CardSurfer';

const route = getRouteApi('/explore');

const MODES: { mode: ExploreMode; label: string }[] = [
  { mode: 'rankings', label: 'Rankings' },
  { mode: 'card', label: 'Specific cards' },
];

/** Explore's modes, as tabs across the top of the sheet: EDHREC's rankings, or specific cards. */
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

/** The card surfer — random cards, full-screen, open whenever the URL carries
 *  `surf`. A side trip from either mode, so it sits at the foot of the rail. */
export function SurfSection() {
  const { surf } = route.useSearch();
  const navigate = useNavigate({ from: '/explore' });
  const setSurf = (v: string | undefined) => navigate({ search: (s) => ({ ...s, surf: v }), replace: true });
  return (
    <SideSection title="Random cards">
      <Button className="justify-start" onClick={() => setSurf('on')}>
        <SurfMark className="size-[1.15rem] text-accent" />
        Surf random cards
      </Button>
      <CardSurfer raw={surf} onChange={setSurf} onClose={() => setSurf(undefined)} />
    </SideSection>
  );
}
