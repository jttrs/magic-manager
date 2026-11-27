import { createContext, type MutableRefObject } from 'react';

/** The strip's slot elements, created by `ViewLayout`; `GuideSheet` portals its
 *  header (arrange, buy, actions) into them. `owner` lets only the first
 *  GuideSheet under a layout claim them. */
export type SheetHeaderSlotsValue = {
  arrange: HTMLElement | null;
  buy: HTMLElement | null;
  actions: HTMLElement | null;
  owner: MutableRefObject<symbol | null>;
};

export const SheetHeaderSlots = createContext<SheetHeaderSlotsValue | null>(null);
