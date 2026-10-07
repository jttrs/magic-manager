import { useEffect, useRef } from 'react';
import { errorText } from '../../app/useCompanion';

/** A companion / cart failure: what happened, what to do next, and the code to quote when reporting it. */
export function FailureNote({ error }: { error: unknown }) {
  const { message, fix, code, ref } = errorText(error);
  // Your own "Don't send" is a choice, not a failure.
  const chose = code === 'request.denied';
  return (
    <div role={chose ? 'status' : 'alert'} className="flex flex-col gap-0.5 text-md leading-relaxed">
      <p className={chose ? 'text-ink' : 'text-danger'}>{message}</p>
      {fix && <p className="text-ink">{fix}</p>}
      {(code || ref) && <p className="text-xs tabular text-ink-muted">{[code && `Code ${code}`, ref && `ref ${ref}`].filter(Boolean).join(' · ')}</p>}
    </div>
  );
}

/** While the companion's own approval window is open. */
export function AwaitingNote({ summary }: { summary: string }) {
  return (
    <p role="status" className="text-md leading-relaxed text-ink">
      Waiting for you to approve in the companion window{summary ? ` — ${summary}` : ''}. Nothing is sent until you press Send there.
    </p>
  );
}

/** A draggable ``javascript:`` bookmark. React refuses javascript: hrefs as props, so it is set on the node. */
export function BookmarkletLink({ href, label }: { href: string; label: string }) {
  const ref = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    ref.current?.setAttribute('href', href);
  }, [href]);
  return (
    <a
      ref={ref}
      onClick={(e) => e.preventDefault()}
      className="inline-flex min-h-9 cursor-grab items-center rounded-sm border border-dashed border-accent px-3 text-sm voice-semi font-medium text-ink no-underline"
      title="Drag me to your bookmarks bar"
    >
      {label}
    </a>
  );
}
