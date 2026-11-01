import { useEffect } from 'react';
import type { MarkedCopy } from '../../components/CopyMarked';
import { exportLines, type GuideGroup } from '../../core/guideCard';

/** An inspector's marked cards, reported up so the Decks sheet header can copy them
 *  (`GuideSheet marked=`). Reports null when the inspector closes. */
export function useReportMarked(sections: readonly GuideGroup[], selected: ReadonlySet<string>, clear: () => void, onMarked?: (m: MarkedCopy | null) => void) {
  useEffect(() => {
    if (!onMarked) return;
    const cards = sections.flatMap((g) => g.items).filter((c) => selected.has(c.key));
    onMarked({ count: cards.length, getText: () => exportLines(cards, 'plain'), onClear: clear });
  }, [sections, selected, clear, onMarked]);
  useEffect(() => (onMarked ? () => onMarked(null) : undefined), [onMarked]);
}
