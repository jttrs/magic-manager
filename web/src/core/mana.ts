// Mana symbols: Scryfall's `{2}{U}{R}` cost strings → symbol tokens, their
// spoken names (for screen readers) and Scryfall's official symbol SVGs.
// Framework-free; components/ManaSymbols.tsx renders them.

const COLOR: Record<string, string> = { W: 'white', U: 'blue', B: 'black', R: 'red', G: 'green', C: 'colorless' };
const WORD: Record<string, string> = { ...COLOR, X: 'X', Y: 'Y', Z: 'Z', S: 'snow', T: 'tap', Q: 'untap', E: 'energy' };
const WUBRG = 'WUBRG';

/** `{2}{W/U}{G/P}` → `['2', 'W/U', 'G/P']`; only the front face of a `A // B` cost. */
export function parseMana(cost: string | null | undefined): string[] {
  const front = (cost ?? '').split(' // ')[0];
  return [...front.matchAll(/\{([^}]+)\}/g)].map((m) => m[1].toUpperCase());
}

/** Scryfall's SVG for one symbol (the same files its `/symbology` lists). */
export const symbolUrl = (sym: string): string => `https://svgs.scryfall.io/card-symbols/${encodeURIComponent(sym.replace(/\//g, ''))}.svg`;

/** One symbol in words: `2` → "2", `U` → "blue", `W/U` → "white or blue", `G/P` → "Phyrexian green". */
function spokenSymbol(sym: string): string {
  const parts = sym.split('/');
  if (parts.length === 2 && parts[1] === 'P') return `Phyrexian ${WORD[parts[0]] ?? parts[0]}`;
  if (parts.length > 1) return parts.map((p) => WORD[p] ?? p).join(' or ');
  return WORD[sym] ?? sym;
}

export const spokenMana = (syms: readonly string[]): string => (syms.length ? syms.map(spokenSymbol).join(', ') : 'none');

/** Colour identity letters in WUBRG order as symbols; colourless = `C`. */
export function identitySymbols(colors: readonly string[]): string[] {
  const known = colors.filter((c) => WUBRG.includes(c)).sort((a, b) => WUBRG.indexOf(a) - WUBRG.indexOf(b));
  return known.length ? known : ['C'];
}
