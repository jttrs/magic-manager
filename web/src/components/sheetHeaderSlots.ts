import { createContext, type MutableRefObject } from 'react';

/** The strip's slot elements, created by `ViewLayout`; `GuideSheet` portals its
 *  header (summary, arrange, actions) into them. `owner` lets only the first
 *  GuideSheet under a layout claim them. */
export type SheetHeaderSlotsValue = {
  stats: HTMLElement | null;
  arrange: HTMLElement | null;
  actions: HTMLElement | null;
  owner: MutableRefObject<symbol | null>;
};

export const SheetHeaderSlots = createContext<SheetHeaderSlotsValue | null>(null);
