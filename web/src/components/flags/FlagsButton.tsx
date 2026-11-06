import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Popover, Switch } from 'radix-ui';
import { useState, type SVGProps } from 'react';
import { flagAdminQuery, flagsQuery, unwrap } from '../../app/queries';
import { putFlag, type FlagRowOut, type FlagsOut } from '../../core/api';
import { applyRow, changedLabel, choiceValue, everyoneValue, mineChoice } from '../../core/flags';
import type { FlagChoice } from '../../core/admin';
import { FailureNote } from '../companion/CompanionNotes';
import { IconAction } from '../IconAction';
import { SettingsChoice } from '../settings/SettingsControls';

function FlagIcon(props: SVGProps<SVGSVGElement>) {
  return (
    <svg viewBox="0 0 16 16" aria-hidden="true" {...props}>
      <path d="M3.5 14.5V2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      <path d="M3.5 2.8h8.2l-1.9 2.9 1.9 2.9H3.5" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" />
    </svg>
  );
}

type Change = { name: string; scope: 'everyone' | 'me'; value: boolean | null };

/** The predicted row while the server answers (the server's row replaces it). */
function predict(row: FlagRowOut, c: Change): FlagRowOut {
  return c.scope === 'everyone' ? { ...row, everyone: c.value } : { ...row, mine: c.value };
}

/** Masthead feature-flag picker: turn a feature on or off for everyone (and, hosted, just for you). */
export function FlagsButton() {
  const admin = useQuery(flagAdminQuery());
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();
  const flags = useQuery(flagsQuery(open && admin.data === true));
  const key = flagsQuery().queryKey;

  const change = useMutation({
    mutationFn: async (c: Change) => unwrap(await putFlag({ path: { flag: c.name }, body: { scope: c.scope, value: c.value } })),
    onMutate: async (c) => {
      await qc.cancelQueries({ queryKey: key });
      const before = qc.getQueryData<FlagsOut>(key);
      if (before) qc.setQueryData<FlagsOut>(key, { ...before, flags: before.flags.map((r) => (r.name === c.name ? predict(r, c) : r)) });
      return { before };
    },
    onError: (_e, _c, ctx) => { if (ctx?.before) qc.setQueryData(key, ctx.before); },
    onSuccess: (row) => qc.setQueryData<FlagsOut>(key, (d) => d && { ...d, flags: applyRow(d.flags, row) }),
    onSettled: () => qc.invalidateQueries({ queryKey: ['features'] }),
  });

  if (admin.data !== true) return null;
  const rows = flags.data?.flags ?? [];
  const perUser = flags.data?.per_user ?? false;
  return (
    <Popover.Root open={open} onOpenChange={(o) => { setOpen(o); if (!o) change.reset(); }}>
      <Popover.Trigger asChild>
        <IconAction label="Feature flags" Icon={FlagIcon} tone="chrome" />
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={6}
          collisionPadding={12}
          aria-label="Feature flags"
          className="z-50 flex max-h-[min(36rem,calc(100dvh-5rem))] w-[min(24rem,calc(100vw-1.5rem))] flex-col gap-3 overflow-y-auto rounded-sm border border-chrome-line bg-chrome-raised p-3 text-sm text-on-chrome shadow-[0_12px_28px_-12px_var(--theme-scrim)]"
        >
          <h2 className="m-0 text-md voice-semi font-medium">Feature flags</h2>
          {change.error && <FailureNote error={change.error} />}
          {flags.isError && <FailureNote error={flags.error} />}
          {flags.isPending && <p className="m-0 text-on-chrome-muted">Loading…</p>}
          <ul aria-label="Flags" className="m-0 flex list-none flex-col p-0">
            {rows.map((row) => (
              <FlagItem key={row.name} row={row} perUser={perUser} busy={change.isPending} onChange={(c) => change.mutate(c)} />
            ))}
          </ul>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}

function FlagItem({ row, perUser, busy, onChange }: { row: FlagRowOut; perUser: boolean; busy: boolean; onChange: (c: Change) => void }) {
  const checked = everyoneValue(row);
  const labelId = `flag-${row.name}-mine`;
  return (
    <li className="flex flex-col gap-2 border-b border-chrome-line py-3 first:pt-0 last:border-b-0 last:pb-0">
      <div className="flex flex-col gap-0.5">
        <p className="m-0 flex items-baseline gap-2">
          <span className="font-medium">{row.title}</span>
          <span className="text-xs uppercase tracking-[0.06em] text-on-chrome-muted">{row.kind}</span>
        </p>
        <p className="m-0 text-on-chrome-muted">{row.about}</p>
      </div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Switch.Root
          checked={checked}
          disabled={row.pinned_by_env || busy}
          aria-label={`${row.title} for everyone`}
          onCheckedChange={() => onChange({ name: row.name, scope: 'everyone', value: !checked })}
          className="relative inline-flex h-6 w-10 shrink-0 cursor-pointer items-center rounded-pill bg-chrome-line transition-colors ease-guide pointer-coarse:h-11 pointer-coarse:w-14 data-[state=checked]:bg-accent data-[disabled]:cursor-not-allowed data-[disabled]:opacity-60"
        >
          <Switch.Thumb className="block size-4 translate-x-1 rounded-pill bg-on-chrome transition-transform ease-guide pointer-coarse:size-6 data-[state=checked]:translate-x-5 pointer-coarse:data-[state=checked]:translate-x-7" />
        </Switch.Root>
        <span>Everyone</span>
        {row.pinned_by_env && <span className="text-on-chrome-muted">Pinned by environment</span>}
        {row.everyone != null && !row.pinned_by_env && (
          <button
            type="button"
            disabled={busy}
            aria-label={`Reset ${row.title} to its default`}
            onClick={() => onChange({ name: row.name, scope: 'everyone', value: null })}
            className="min-h-6 cursor-pointer text-on-chrome-muted underline hover:text-on-chrome disabled:cursor-not-allowed pointer-coarse:min-h-11"
          >
            Reset
          </button>
        )}
      </div>
      {perUser && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <span id={labelId}>Just me</span>
          <SettingsChoice<FlagChoice>
            labelId={labelId}
            value={mineChoice(row)}
            options={[{ value: 'default', label: 'Follow' }, { value: 'on', label: 'On' }, { value: 'off', label: 'Off' }]}
            onChange={(choice) => { if (!busy) onChange({ name: row.name, scope: 'me', value: choiceValue(choice) }); }}
          />
        </div>
      )}
      <p className="m-0 text-xs text-on-chrome-muted">{changedLabel(row)}</p>
    </li>
  );
}
