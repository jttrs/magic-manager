import { useFeature } from '../../app/features';
import { useCompanion } from '../../app/useCompanion';
import { SetUpCompanionButton } from './CompanionSetup';

/** Something this app reads only in YOUR browser here (hosted members: Moxfield decks, open
 *  tabs, carts) while the companion isn't connected: say so, and offer its setup — never a
 *  server option that would be refused. */
export function CompanionRequired({ what }: { what: string }) {
  const on = useFeature('companion');
  const c = useCompanion();
  if (on && c.status === 'checking') return <p role="status" className="text-sm text-ink-muted">Looking for the browser companion…</p>;
  return (
    <div role="status" className="flex flex-col gap-2 text-sm leading-relaxed">
      <p className="text-ink">
        {what} are read in your own browser by the browser companion — this app doesn’t open a browser on its server for you.
        {' '}<span className="text-ink-muted">{on ? 'Set it up and pair it with this address, then try again.' : 'Ask the app’s admin to turn on the browser companion for you.'}</span>
      </p>
      {on && <SetUpCompanionButton />}
    </div>
  );
}
