import type { ReactNode } from 'react';

/** One labelled control in a rail (or any stacked form): a fixed-height label row —
 *  the label plus an optional ⓘ (`extra`), which never makes the row taller — then the
 *  control. Every rail control goes through this, so label spacing is set once.
 *  Pass `htmlFor` when the control is a native field, `labelId` when it is labelled by
 *  `aria-labelledby` (a segmented group, a menu trigger). */
export function RailField({ label, htmlFor, labelId, extra, children }: {
  label: ReactNode;
  htmlFor?: string;
  labelId?: string;
  extra?: ReactNode;
  children: ReactNode;
}) {
  const cls = 'text-sm voice-semi text-on-chrome-muted';
  return (
    <div className="flex min-w-0 flex-col gap-1.5">
      <span className="flex h-5 items-center gap-1.5">
        {htmlFor ? <label htmlFor={htmlFor} id={labelId} className={cls}>{label}</label> : <span id={labelId} className={cls}>{label}</span>}
        {extra}
      </span>
      {children}
    </div>
  );
}
