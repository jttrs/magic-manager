// The many-option picker's rules, framework-free: what an empty selection means,
// what the trigger says, and what the bulk buttons do. `MultiSelect` renders them.

/**
 * What a picker's value means:
 * - `scope`: the things you chose to look at; empty = nothing chosen (Set families).
 * - `include`: a narrowing filter; empty = no filter, every option counts (Stores).
 * - `exclude`: the CHECKED options are shown and unchecking hides one; all checked =
 *   no filter (Rarity, Finish, Treatment — stored as exclusions by their view).
 */
export type PickMode = 'scope' | 'include' | 'exclude';

export type PickOption = { value: string; label: string };

export type BulkAction = { label: string; next: string[] };

/** Options left unchecked in an exclude picker (only listed options count). */
function hiddenOptions(options: readonly PickOption[], value: readonly string[]): PickOption[] {
  const on = new Set(value);
  return options.filter((o) => !on.has(o.value));
}

/** The trigger's text: the one choice by name, otherwise a count with the noun. */
export function pickSummary(mode: PickMode, options: readonly PickOption[], value: readonly string[], noun: string): string {
  if (mode === 'exclude') {
    const hidden = hiddenOptions(options, value);
    if (!hidden.length) return `All ${noun}`;
    if (hidden.length === options.length) return `All ${noun} hidden`;
    return hidden.length === 1 ? `${hidden[0].label} hidden` : `${hidden.length} ${noun} hidden`;
  }
  const chosen = options.filter((o) => value.includes(o.value));
  const n = chosen.length || value.length;
  if (!n) return mode === 'scope' ? `Choose ${noun}…` : `All ${noun}`;
  if (n === 1) return chosen[0]?.label ?? value[0];
  if (mode === 'scope' && options.length > 1 && chosen.length === options.length) return `All ${n} ${noun}`;
  return `${n} ${noun}`;
}

/** The count beside the bulk buttons: `N selected`, or `N hidden` for exclude pickers. */
export function pickCount(mode: PickMode, options: readonly PickOption[], value: readonly string[]): string {
  return mode === 'exclude' ? `${hiddenOptions(options, value).length} hidden` : `${value.length} selected`;
}

/**
 * The bulk buttons. They only ever change the options in `listed` (every option, or
 * the ones a filter box shows), so an option that isn't on screen — a zero-count
 * rarity, say — is never hidden or chosen behind your back.
 */
export function bulkActions(mode: PickMode, listed: readonly PickOption[], value: readonly string[], filtering: boolean): BulkAction[] {
  const keys = new Set(listed.map((o) => o.value));
  const add = (): string[] => [...new Set([...value, ...listed.map((o) => o.value)])];
  const drop = (): string[] => value.filter((v) => !keys.has(v));
  const allOn = listed.every((o) => value.includes(o.value));
  const anyOn = listed.some((o) => value.includes(o.value));
  const out: BulkAction[] = [];
  if (mode === 'exclude') {
    const what = filtering ? 'shown' : 'all';
    if (!allOn) out.push({ label: `Check ${what}`, next: add() });
    if (anyOn) out.push({ label: `Uncheck ${what}`, next: drop() });
    return out;
  }
  if (filtering) {
    if (!allOn) out.push({ label: 'Select shown', next: add() });
    if (anyOn) out.push({ label: 'Clear shown', next: drop() });
    return out;
  }
  if (mode === 'scope') {
    if (!allOn) out.push({ label: 'Select all', next: add() });
    if (value.length) out.push({ label: 'Clear all', next: [] });
    return out;
  }
  // include: an empty selection already shows everything.
  if (value.length) out.push({ label: 'Show all', next: [] });
  return out;
}
