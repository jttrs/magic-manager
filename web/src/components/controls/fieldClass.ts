export type FieldTone = 'chrome' | 'paper';

/** The one text-field box (search, text, number, date): the shared control height, a
 *  ruled border that turns amber on focus. Chrome sits in rails and the masthead; paper
 *  in sheets and dialogs. */
export function fieldClass(tone: FieldTone = 'chrome'): string {
  const base = 'min-h-control pointer-coarse:min-h-control-coarse min-w-0 rounded-sm border px-2.5 text-md focus-visible:border-accent disabled:cursor-not-allowed disabled:opacity-60';
  return tone === 'chrome'
    ? `${base} border-chrome-line bg-chrome-raised text-on-chrome placeholder:text-on-chrome-muted [color-scheme:dark]`
    : `${base} border-rule bg-paper-raised text-ink placeholder:text-ink-muted`;
}

/** The trigger box of a select / multi-select / menu button: the field box laid out
 *  as a row (value, then a caret). */
export function triggerClass(tone: FieldTone = 'chrome'): string {
  const hover = tone === 'chrome' ? 'hover:border-on-chrome-muted' : 'hover:border-rule-strong';
  return `${fieldClass(tone)} flex w-full cursor-pointer items-center gap-2 text-left transition-colors ease-guide ${hover} data-[state=open]:border-accent`;
}
