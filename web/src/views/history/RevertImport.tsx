import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { useState } from 'react';
import { revertPlanQuery, unwrap } from '../../app/queries';
import { Button } from '../../components/Button';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { historyRevert, type RevertPlanOut } from '../../core/api';
import { ApiError } from '../../core/apiError';
import { fmtInt } from '../../core/format';
import { planFromError, revertActionLabel, revertBlockNote, revertLead } from '../../core/history';

/** "Revert this import": a quiet inspector action → a confirm that lists exactly
 *  what leaves (and the decklist it saved), or what blocks it and the way out. */
export function RevertImport({ ingestId, onDone }: { ingestId: number; onDone: (summary: string) => void }) {
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [refused, setRefused] = useState<RevertPlanOut | null>(null);
  const q = useQuery(revertPlanQuery(ingestId, open));
  const plan = refused ?? q.data;

  return (
    <>
      <Button tone="paper" onClick={() => { setRefused(null); setOpen(true); }}>Revert this import</Button>
      <ConfirmDialog
        open={open}
        onOpenChange={setOpen}
        title={!plan || plan.ok ? 'Revert this import?' : 'Can’t revert this import yet'}
        confirmLabel={plan ? revertActionLabel(plan) : 'Revert'}
        confirmDisabled={!plan?.ok}
        onConfirm={async () => {
          try {
            const r = unwrap(await historyRevert({ path: { ingest_id: ingestId } }));
            onDone(r.summary);
            await qc.invalidateQueries();
          } catch (e) {
            const p = e instanceof ApiError ? planFromError(e.detail) : null;
            if (p) setRefused(p);
            throw e;
          }
        }}
      >
        {q.isPending && !refused ? (
          <p className="text-ink-muted">Checking what this import added…</p>
        ) : q.isError && !refused ? (
          <p role="alert" className="text-danger">{(q.error as Error).message}</p>
        ) : plan ? (
          <PlanBody plan={plan} />
        ) : null}
      </ConfirmDialog>
    </>
  );
}

function PlanBody({ plan }: { plan: RevertPlanOut }) {
  const busy = plan.reason === 'deck_in_use' ? plan.decks.find((d) => d.built || d.pledged > 0) : undefined;
  return (
    <>
      {plan.ok ? <p>{revertLead(plan)}</p> : <p>{plan.message}</p>}
      {busy && (
        <p>
          <Link to="/decks" search={{ deck: busy.slug }} className="voice-semi text-accent-ink underline underline-offset-2">Open {busy.name}</Link>
        </p>
      )}
      {plan.lines.length > 0 && (
        <ul aria-label="Cards" className="max-h-[min(18rem,40dvh)] overflow-y-auto overscroll-contain border-t border-rule pr-1 text-sm [scrollbar-gutter:stable]">
          {plan.lines.map((l) => {
            const note = revertBlockNote(l);
            const p = l.printing;
            return (
              <li key={`${p.scryfall_id}|${l.finish}`} className="ruled flex flex-col gap-0.5 py-1.5">
                <span className="flex items-baseline gap-3">
                  <span className="min-w-0 flex-1 truncate">
                    <span className="voice-semi text-ink">{p.name}</span>
                    <span className="text-ink-muted"> · {p.set_code.toUpperCase()} {p.collector_number}{l.finish === 'foil' ? ' · foil' : ''}</span>
                  </span>
                  <span className="shrink-0 tabular text-ink">{l.remove ? `−${fmtInt(l.remove)}` : `+${fmtInt(l.restore)}`}</span>
                </span>
                {note && <span className="text-xs text-danger">{note}</span>}
              </li>
            );
          })}
        </ul>
      )}
      <p className="text-sm text-ink-muted">
        {plan.ok
          ? 'The entry stays in your history, marked reverted. Undo in the header can still roll back this session.'
          : 'Nothing has been changed.'}
      </p>
    </>
  );
}

