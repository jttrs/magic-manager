import { useFeature } from '../../app/features';
import { SectionTabs } from '../../components/SectionTabs';
import type { MarketSearch } from '../../core/search';

type Subject = MarketSearch['subject'];

const SUBJECTS: { id: Subject; label: string }[] = [
  { id: 'family', label: 'Set family' },
  { id: 'deck', label: 'Deck' },
  { id: 'sld', label: 'Secret Lair' },
  { id: 'deals', label: 'Deals' },
];

/** Market's modes, in the sub-nav strip: a set family's sealed products and
 *  singles, a deck's cost, the newest Secret Lair drops, and (with the `deals`
 *  feature) store pages compared to what they're worth. One route, so the
 *  caller says which is current. Switching mode closes the open item. */
export function MarketTabs({ subject }: { subject: Subject }) {
  const deals = useFeature('deals');
  return (
    <SectionTabs
      label="Market views"
      tabs={SUBJECTS.filter((s) => s.id !== 'deals' || deals).map((s) => ({
        id: s.id,
        label: s.label,
        active: s.id === subject,
        link: { to: '/market', search: ((p: MarketSearch) => ({ ...p, subject: s.id, item: undefined })) as never },
      }))}
    />
  );
}
