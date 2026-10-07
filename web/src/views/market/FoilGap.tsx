import { InfoTip } from '../../components/InfoTip';
import { Segmented } from '../../components/Sidebar';
import type { CardPriceOut } from '../../core/api';
import { fmtUsd } from '../../core/format';
import { fmtFoilGap } from '../../core/market';
import type { MarketSearch } from '../../core/search';

const STATUS_NOTE: Record<string, string> = {
  fancy: 'fancy foil',
  foil_only: 'foil only',
  nonfoil_only: 'no foil',
};

/** The foil premium of one printing: "+45%" with the dollar gap beneath. */
export function FoilGapCell({ c, className = '' }: { c: CardPriceOut; className?: string }) {
  const note = STATUS_NOTE[c.foil_gap_status];
  return (
    <td className={`py-1.5 pl-3 text-right ${className}`}>
      {c.foil_gap_status === 'ok' && c.foil_gap_pct != null ? (
        <span className="text-ink" title={`Foil ${fmtUsd(c.price_usd_foil)} vs nonfoil ${fmtUsd(c.price_usd)}`}>
          {fmtFoilGap(c.foil_gap_pct)}
          {c.foil_gap_usd != null && (
            <span className="ml-1.5 text-xs text-ink-muted">
              {c.foil_gap_usd < 0 ? '−' : '+'}
              {fmtUsd(Math.abs(c.foil_gap_usd))}
            </span>
          )}
        </span>
      ) : (
        <span className="text-xs text-ink-muted">{note ?? '—'}</span>
      )}
    </td>
  );
}

export function FoilPremiumFilter({ value, onChange }: { value: MarketSearch['foilMax']; onChange: (v: MarketSearch['foilMax']) => void }) {
  return (
    <Segmented<MarketSearch['foilMax']>
      label="Foil premium"
      showLabel
      wrap
      labelExtra={
        <InfoTip label="What is the foil premium?">
          How much more the plain foil costs than the nonfoil of the same printing. Fancy foils (surge, etched, textured…) are a different product and are left out when a cap is set.
        </InfoTip>
      }
      value={value}
      onChange={onChange}
      options={[
        { value: 'any', label: 'Any' },
        { value: 'cheaper', label: 'Foil cheaper' },
        { value: '25', label: 'Under 25%' },
        { value: '50', label: 'Under 50%' },
        { value: '100', label: 'Under 100%' },
      ]}
    />
  );
}
