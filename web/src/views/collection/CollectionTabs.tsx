import { useFeature } from '../../app/features';
import { SectionTabs, type SectionTab } from '../../components/SectionTabs';
import type { HistorySearch } from '../../core/history';

/** Collection's modes: the cards you own, how they came in, and (with the
 *  `purchases` feature) the store orders behind them. Purchase history and
 *  Store orders share one route, so the history view says which is current. */
export function CollectionTabs({ orders }: { orders?: boolean }) {
  const purchases = useFeature('purchases');
  const onHistory = orders !== undefined;
  const tabs: SectionTab[] = [
    { id: 'cards', label: 'Cards', link: { to: '/collection', activeOptions: { exact: true, includeSearch: false } } },
    {
      id: 'history',
      label: 'Purchase history',
      link: { to: '/collection/history', search: onHistory ? (s: HistorySearch) => ({ ...s, orders: false, order: undefined }) : {} } as SectionTab['link'],
      active: onHistory && !orders,
    },
  ];
  if (purchases) {
    tabs.push({
      id: 'orders',
      label: 'Store orders',
      link: { to: '/collection/history', search: onHistory ? (s: HistorySearch) => ({ ...s, orders: true, entry: undefined }) : { orders: true } } as SectionTab['link'],
      active: onHistory && orders,
    });
  }
  return <SectionTabs label="Collection views" tabs={tabs} />;
}
