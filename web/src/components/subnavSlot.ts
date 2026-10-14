import { createContext } from 'react';

/** True inside `ViewLayout`'s `subnav` strip: `SectionTabs` reads it to take the
 *  strip's chrome look instead of the in-sheet paper look. */
export const SubnavSlot = createContext(false);
