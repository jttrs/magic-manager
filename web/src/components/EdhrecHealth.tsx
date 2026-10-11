import { useDownScrapers } from '../app/scraperHealth';
import { EDHREC_KEYS } from '../core/scraperHealth';
import { ScraperNotice } from './ScraperNotice';

/** "Temporarily down" for EDHREC reads, above the Explore sheets (inset like their other notes). */
export function EdhrecHealth({ keys = EDHREC_KEYS }: { keys?: readonly string[] }) {
  const down = useDownScrapers(keys);
  return <ScraperNotice down={down} className="mx-5 mb-2" />;
}
