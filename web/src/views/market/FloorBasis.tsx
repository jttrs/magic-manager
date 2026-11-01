const clock = (ms: number) => new Date(ms).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

/** Where the "cheapest printing" values came from. The recheck itself is the
 *  sheet header's *Recheck for cheapest* action (A12): once it has run, this
 *  note says so with the time. (The source is never named.) */
export function FloorBasis({ live, liveError, checkedAt }: { live: boolean; liveError?: string | null; checkedAt?: number }) {
  return (<>
    <p className="-mt-3 text-sm text-ink-muted">
      {live
        ? `Cheapest printings rechecked across every printing${checkedAt ? ` · ${clock(checkedAt)}` : ''}.`
        : 'Cheapest printings among the sets synced here.'}
    </p>
    {liveError && (
      <p role="alert" className="-mt-3 text-sm text-danger">
        Couldn’t recheck every printing — showing the cheapest among the sets synced here. {liveError}
      </p>
    )}
  </>);
}
