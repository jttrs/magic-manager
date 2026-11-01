import { SectionTabs, type SectionTab } from '../../components/SectionTabs';

/** Collection's modes, in the sub-nav strip: the cards you own, and where they came from
 *  (Purchase history — ledger entries and store orders in one list). */
export function CollectionTabs() {
  const tabs: SectionTab[] = [
    { id: 'cards', label: 'Cards', link: { to: '/collection', activeOptions: { exact: true, includeSearch: false } } },
    { id: 'history', label: 'Purchase history', link: { to: '/collection/history', activeOptions: { includeSearch: false } } },
  ];
  return <SectionTabs label="Collection views" tabs={tabs} />;
}
