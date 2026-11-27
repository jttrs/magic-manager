// The overlay surfaces: dialogs (paper sheets over a scrim) and menus/popovers (chrome
// panels). Radix supplies behaviour; these classes are the one look.

export type DialogSize = 'sm' | 'md' | 'lg';

const WIDTH: Record<DialogSize, string> = {
  sm: 'w-[min(var(--dialog-sm),calc(100vw-1.5rem))]',
  md: 'w-[min(var(--dialog-md),calc(100vw-1.5rem))]',
  lg: 'w-[min(var(--dialog-lg),calc(100vw-1rem))]',
};

/** The scrim behind a dialog: a flat dim, no backdrop blur — a backdrop-filter makes Chrome
 *  recompute the page behind on every repaint (scrolling a dialog, a pulsing job dot), which
 *  flickers the dialog. */
export const dialogOverlayClass = 'fixed inset-0 z-40 bg-scrim';

/** A dialog's paper sheet, centred. `layout` = how its body stacks (`stack`: a padded
 *  column that scrolls as a whole; `frame`: a flex column whose own parts scroll). */
export function dialogContentClass(size: DialogSize = 'sm', layout: 'stack' | 'frame' = 'stack'): string {
  const base = `paper-grain fixed left-1/2 top-1/2 z-50 ${WIDTH[size]} max-h-[min(var(--dialog-max-h),calc(100dvh-1.5rem))] -translate-x-1/2 -translate-y-1/2 rounded-sm bg-paper text-ink shadow-dialog focus:outline-none`;
  return layout === 'stack' ? `${base} flex flex-col gap-4 overflow-y-auto p-5` : `${base} flex flex-col`;
}

/** A dialog's title rule. */
export const dialogTitleClass = 'border-b-2 border-rule-strong pb-2 text-2xl voice-condensed font-bold leading-none';

/** A menu / popover / select-list panel on chrome — above dialogs (z-50), so a picker inside a dialog opens over it. */
export const menuPanelClass = 'z-60 rounded-sm border border-chrome-line bg-chrome-raised text-on-chrome shadow-popover';

/** A menu's small caps heading. */
export const menuLabelClass = 'px-3 pb-1 pt-1.5 text-xs voice-condensed uppercase tracking-caps text-on-chrome-muted';

/** A hairline between a menu's groups. */
export const menuSeparatorClass = 'my-1 h-px bg-chrome-line';

/** One menu item (radio or plain). */
export const menuItemClass = 'flex cursor-pointer items-center gap-2.5 px-3 py-1.5 text-sm outline-none data-[highlighted]:bg-chrome-line data-[state=checked]:text-accent data-[disabled]:cursor-not-allowed data-[disabled]:opacity-45';
