import { identitySymbols, parseMana, spokenMana, symbolUrl } from '../core/mana';

/** Mana symbols inline with text (Scryfall's official symbol art), one accessible
 *  name for the run: "Mana cost: 2, blue, red". Sized by `size` (a Tailwind size class). */
function ManaSymbols({ symbols, label, size = 'size-[1.1em]' }: { symbols: readonly string[]; label: string; size?: string }) {
  if (!symbols.length) return <span className="text-ink-muted" aria-label={`${label}: none`}>—</span>;
  return (
    <span role="img" aria-label={`${label}: ${spokenMana(symbols)}`} title={`${label}: ${spokenMana(symbols)}`} className="inline-flex shrink-0 items-center gap-0.5 align-[-0.15em]">
      {symbols.map((s, i) => (
        <img key={`${s}-${i}`} src={symbolUrl(s)} alt="" width={16} height={16} loading="lazy" decoding="async" draggable={false} className={`${size} rounded-pill shadow-[-1px_1px_0_var(--theme-scrim)]`} />
      ))}
    </span>
  );
}

export const ManaCost = ({ cost, size }: { cost: string | null | undefined; size?: string }) => <ManaSymbols symbols={parseMana(cost)} label="Mana cost" size={size} />;

export const ColorIdentity = ({ colors, size }: { colors: readonly string[]; size?: string }) => <ManaSymbols symbols={identitySymbols(colors)} label="Colour identity" size={size} />;
