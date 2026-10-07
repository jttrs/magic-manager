import { IconAction } from '../../components/IconAction';
import { ScryfallMark } from '../../components/StoreMarks';

/** Where the "cheapest printing" prices came from, with the opt-in live check. */
export function FloorBasis({ live, liveError, onCheckLive }: { live: boolean; liveError?: string | null; onCheckLive: () => void }) {
  return (<>
    <p className="-mt-3 flex min-h-9 items-center gap-2 text-sm text-ink-muted">
      {live ? 'Cheapest printings checked across every set on Scryfall.' : 'Cheapest printings from the sets you’ve synced.'}
      {!live && <IconAction label="Check every set on Scryfall" Icon={ScryfallMark} onClick={onCheckLive} />}
    </p>
    {liveError && (
      <p role="alert" className="-mt-3 text-sm text-danger">
        Couldn’t check every set on Scryfall — showing prices from your synced sets. {liveError}
      </p>
    )}
  </>);
}
