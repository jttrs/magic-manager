import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { Dialog, Switch, Tooltip } from 'radix-ui';
import { useId, useState, type ReactNode } from 'react';
import { analyticsCatalogQuery, consentQuery, unwrap } from '../app/queries';
import { analyticsForget, analyticsSetConsent, type ConsentOut } from '../core/api';
import { fmtCount } from '../core/format';
import { Button } from './Button';

function ChromeTip({ label, children }: { label: string; children: ReactNode }) {
  return (
    <Tooltip.Provider delayDuration={200}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>{children}</Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content side="bottom" sideOffset={6} collisionPadding={12} className="z-50 rounded-sm border border-chrome-line bg-chrome-raised px-2.5 py-1.5 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]">
            {label}
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}

const iconButton = 'relative grid size-8 cursor-pointer place-items-center rounded-sm text-on-chrome-muted no-underline transition-colors ease-guide hover:text-on-chrome data-[status=active]:text-on-chrome';

/** Masthead link to the internal Analytics view (flag `analytics`). */
export function AnalyticsLink() {
  return (
    <ChromeTip label="Analytics">
      <Link to="/analytics" aria-label="Analytics" className={`${iconButton} max-sm:hidden`}>
        <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
          <path d="M2.5 13.5h11M4.5 11V8M8 11V4M11.5 11V6.5" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
        </svg>
      </Link>
    </ChromeTip>
  );
}

/** Masthead privacy control: what we record, the two switches, delete-my-data.
 *  Hosted users who haven't chosen yet see it once, on their first visit. */
export function PrivacyButton() {
  const consent = useQuery(consentQuery());
  const [chosen, setOpen] = useState<boolean | null>(null);
  const c = consent.data;
  // Hosted users who haven't chosen yet see it once, until they close it.
  const needsAsk = Boolean(c && c.mode === 'hosted' && !c.asked && !c.disabled);
  const open = chosen ?? needsAsk;
  if (!c) return null;
  const label = c.disabled ? 'Privacy · nothing is recorded on this server' : 'Privacy · what this app records';
  return (
    <Dialog.Root open={open} onOpenChange={setOpen}>
      <ChromeTip label={label}>
        <Dialog.Trigger aria-label={label} className={iconButton}>
          <svg viewBox="0 0 16 16" aria-hidden="true" className="size-4">
            <path d="M8 1.75 3 3.6v4.1c0 3.1 2.1 5.4 5 6.55 2.9-1.15 5-3.45 5-6.55V3.6L8 1.75Z" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
            {c.usage || c.errors ? <path d="m5.6 8 1.7 1.7 3.2-3.4" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" /> : null}
          </svg>
        </Dialog.Trigger>
      </ChromeTip>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-scrim backdrop-blur-[1px]" />
        <Dialog.Content className="paper-grain fixed left-1/2 top-1/2 z-50 flex max-h-[min(44rem,calc(100dvh-1.5rem))] w-[min(32rem,calc(100vw-1.5rem))] -translate-x-1/2 -translate-y-1/2 flex-col rounded-sm bg-paper text-ink shadow-[0_24px_60px_-24px_var(--theme-scrim)] focus:outline-none">
          <header className="flex items-start gap-3 border-b-2 border-rule-strong px-5 pb-2 pt-4">
            <div className="min-w-0 flex-1">
              <Dialog.Title className="text-2xl voice-condensed font-bold leading-none">Privacy</Dialog.Title>
              <Dialog.Description className="mt-1 text-sm text-ink-muted">
                What this app records to improve itself. It never records what you type, which cards you own, prices, or who you are.
              </Dialog.Description>
            </div>
            <Dialog.Close className="touch-hit grid size-9 cursor-pointer place-items-center rounded-sm text-xl text-ink-muted hover:bg-paper-sunk hover:text-ink" aria-label="Close">×</Dialog.Close>
          </header>
          <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-5 pb-5 pt-3">
            <PrivacyBody consent={c} />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

function PrivacyBody({ consent }: { consent: ConsentOut }) {
  const qc = useQueryClient();
  const catalog = useQuery(analyticsCatalogQuery());
  const [deleted, setDeleted] = useState<number | null>(null);
  const save = useMutation({
    mutationFn: async (body: { errors?: boolean; usage?: boolean }) => unwrap(await analyticsSetConsent({ body })),
    onSuccess: (c) => qc.setQueryData(consentQuery().queryKey, c),
  });
  const forget = useMutation({
    mutationFn: async () => unwrap(await analyticsForget()),
    onSuccess: (r) => setDeleted(r.deleted),
  });
  const events = catalog.data ?? [];
  const off = consent.disabled;
  return (
    <div className="flex flex-col gap-4">
      {off && <p className="text-md">Recording is switched off on this server (<code>MM_ANALYTICS=off</code>), so nothing is recorded whatever you choose.</p>}
      <ConsentSwitch
        label="Error reports"
        checked={consent.errors}
        disabled={off || save.isPending}
        onChange={(v) => save.mutate({ errors: v })}
        events={events.filter((e) => e.category === 'error')}
      >
        When something breaks, record which part failed and its error code, so it gets fixed without you having to report it.
      </ConsentSwitch>
      <ConsentSwitch
        label="Usage analytics"
        checked={consent.usage}
        disabled={off || save.isPending}
        onChange={(v) => save.mutate({ usage: v })}
        events={events.filter((e) => e.category === 'usage')}
      >
        Record which views and features get used, as counts, so development follows real use.
      </ConsentSwitch>
      {save.error && <p role="alert" className="text-sm text-danger">{(save.error as Error).message}</p>}
      <p className="text-sm leading-relaxed text-ink-muted">
        Error reports are kept 30 days and usage 90 days. After that only daily totals remain, with no link to you. Events carry a random per-tab session id and a one-way key, never your name, email or address.
      </p>
      <div className="flex flex-wrap items-center gap-3 border-t border-rule pt-3">
        <Button tone="paper" disabled={forget.isPending} onClick={() => forget.mutate()}>
          {forget.isPending ? 'Deleting…' : 'Delete my analytics data'}
        </Button>
        <p aria-live="polite" className="text-sm text-ink-muted">
          {deleted != null ? (deleted ? `Deleted ${fmtCount(deleted, 'event')}.` : 'Nothing to delete.') : ''}
        </p>
        {forget.error && <p role="alert" className="text-sm text-danger">{(forget.error as Error).message}</p>}
      </div>
      {consent.mode === 'hosted' && !consent.asked && (
        <Dialog.Close asChild>
          <Button emphasis="primary" onClick={() => save.mutate({})}>Save my choice</Button>
        </Dialog.Close>
      )}
    </div>
  );
}

function ConsentSwitch({ label, checked, disabled, onChange, events, children }: {
  label: string; checked: boolean; disabled: boolean; onChange: (v: boolean) => void; events: { name: string; purpose: string }[]; children: ReactNode;
}) {
  const id = useId();
  return (
    <section className="ruled flex flex-col gap-1.5 pb-3">
      <div className="flex items-center gap-3">
        <label htmlFor={id} className="flex-1 text-xl voice-condensed font-bold">{label}</label>
        <Switch.Root
          id={id}
          checked={checked}
          disabled={disabled}
          onCheckedChange={onChange}
          aria-describedby={`${id}-d`}
          className="relative h-6 w-11 shrink-0 cursor-pointer rounded-pill border border-rule-strong bg-paper-sunk transition-colors ease-guide disabled:cursor-not-allowed disabled:opacity-45 data-[state=checked]:border-accent data-[state=checked]:bg-accent"
        >
          <Switch.Thumb className="block size-4 translate-x-1 rounded-pill bg-ink transition-transform ease-guide data-[state=checked]:translate-x-[1.375rem] data-[state=checked]:bg-on-accent" />
        </Switch.Root>
      </div>
      <p id={`${id}-d`} className="text-md leading-relaxed">{children}</p>
      {events.length > 0 && (
        <details className="text-sm text-ink-muted">
          <summary className="cursor-pointer voice-semi">What’s recorded ({events.length})</summary>
          <ul className="mt-1.5 flex flex-col gap-1 pl-1">
            {events.map((e) => (
              <li key={e.name}><span className="tabular text-ink">{e.name}</span> — {e.purpose}</li>
            ))}
          </ul>
        </details>
      )}
    </section>
  );
}
