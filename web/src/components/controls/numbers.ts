/** A whole number typed into a field, or null while it isn't one yet (empty, "-", "2.5"). */
export function parseWhole(text: string): number | null {
  const t = text.trim();
  return /^-?\d+$/.test(t) ? Number(t) : null;
}

/** The value a whole-number field settles on when you leave it: what you typed, kept
 *  inside [min, max]; the previous value when you left it empty or unreadable. */
export function clampWhole(text: string, min: number, max: number, previous: number): number {
  const n = parseWhole(text);
  return n == null ? previous : Math.max(min, Math.min(max, n));
}
