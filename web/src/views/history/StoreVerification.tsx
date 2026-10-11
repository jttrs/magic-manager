import { InfoTip } from '../../components/InfoTip';
import type { MagicManagerApiPurchasesStoreOut as StoreOut } from '../../core/api';

const LABEL: Record<StoreOut['verification'], string> = {
  verified: 'Verified',
  partial: 'Partly verified',
  unverified: 'Not verified',
};

/** How far a store's reader can be trusted, with the reason in an InfoTip. Never shows a store as verified unless it is. */
export function VerificationMark({ store }: { store: StoreOut | undefined }) {
  if (!store) return null;
  return (
    <span className="inline-flex items-center gap-1 text-xs text-ink-muted">
      <span className={store.verification === 'verified' ? 'voice-semi text-ink' : 'voice-semi'}>{LABEL[store.verification]}</span>
      <InfoTip label={`About the ${store.name} reader`} tone="paper">{store.note}</InfoTip>
    </span>
  );
}
