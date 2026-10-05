import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { unwrap } from '../../app/queries';
import { ConfirmDialog } from '../../components/ConfirmDialog';
import { IconAction } from '../../components/IconAction';
import { AddCardMark, BreakDownMark, BuildDeckMark, CopyDeckMark, EditDeckMark } from '../../components/StoreMarks';
import { deckBreakDown, deckBuild, deckBuildPlan, deckCopy, type BuildPlanOut, type DeckDetailOut } from '../../core/api';
import { fmtInt } from '../../core/format';

type Dialog = { kind: 'build'; plan: BuildPlanOut } | { kind: 'break' } | { kind: 'copy' } | null;

/** The deck's actions as one calm row of icons (tooltips carry the words):
 *  add its cards to your collection · edit (or copy-to-edit a precon) · build from
 *  your free cards · break down. Physical changes confirm first. */
export function DeckActions({ detail, slug, onAddToCollection }: { detail: DeckDetailOut; slug: string; onAddToCollection: () => void }) {
  const { deck } = detail;
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [dialog, setDialog] = useState<Dialog>(null);
  const [planError, setPlanError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const refresh = async () => {
    await qc.invalidateQueries({ queryKey: ['decks'] });
    await qc.invalidateQueries({ queryKey: ['collection'] });
    await qc.invalidateQueries({ queryKey: ['holdings'] });
  };
  const openBuild = async () => {
    setPlanError(null);
    try {
      setDialog({ kind: 'build', plan: unwrap(await deckBuildPlan({ path: { slug } })) });
    } catch (e) {
      setPlanError((e as Error).message);
    }
  };
  const build = (allow: boolean) => async () => {
    const r = unwrap(await deckBuild({ path: { slug }, body: { allow_shortfall: allow } }));
    setToast(r.summary);
    await refresh();
  };
  const breakDown = async () => {
    const r = unwrap(await deckBreakDown({ path: { slug } }));
    setToast(r.summary);
    await refresh();
  };
  const copy = async () => {
    const r = unwrap(await deckCopy({ path: { slug }, body: {} }));
    await qc.invalidateQueries({ queryKey: ['decks'] });
    navigate({ to: '/decks/$slug/edit', params: { slug: r.slug } });
  };

  const allBuilt = deck.built >= deck.slugs.length && deck.pledged_pct >= 100;
  const plan = dialog?.kind === 'build' ? dialog.plan : null;
  const short = plan ? plan.need - plan.covered : 0;

  return (
    <>
      <span role="toolbar" aria-label="Deck actions" className="flex items-center gap-0.5">
        <IconAction label="Add deck cards to collection" Icon={AddCardMark} onClick={onAddToCollection} />
        {detail.editable ? (
          <IconAction label="Edit deck" Icon={EditDeckMark} onClick={() => navigate({ to: '/decks/$slug/edit', params: { slug } })} />
        ) : (
          <IconAction label="Copy to edit" Icon={CopyDeckMark} onClick={() => setDialog({ kind: 'copy' })} />
        )}
        <IconAction label="Build from your cards" Icon={BuildDeckMark} onClick={openBuild} disabled={allBuilt} disabledReason="Every copy of this deck is built" />
        <IconAction label="Break down" Icon={BreakDownMark} onClick={() => setDialog({ kind: 'break' })} disabled={deck.built === 0} disabledReason="This deck isn’t built" />
      </span>
      {(toast || planError) && (
        <p role="status" className={`w-full text-right text-sm ${planError ? 'text-danger' : 'text-ink-muted'}`}>{planError ?? toast}</p>
      )}

      <ConfirmDialog
        open={dialog?.kind === 'build'}
        onOpenChange={(o) => !o && setDialog(null)}
        title={`Build ${deck.name}?`}
        confirmLabel={short ? `Build with ${fmtInt(short)} missing` : 'Build deck'}
        onConfirm={build(short > 0)}
      >
        {plan && (
          <>
            <p>
              {short
                ? <>You have <b>{fmtInt(plan.covered)}</b> of the <b>{fmtInt(plan.need)}</b> cards free. Building pledges those to the deck; the rest stay listed as missing.</>
                : <>{plan.need === 1 ? 'Its card is' : <>All <b>{fmtInt(plan.need)}</b> cards are</>} free in your collection. Building pledges {plan.need === 1 ? 'it' : 'them'} to this deck, so {plan.need === 1 ? 'it stops' : 'they stop'} counting as free.</>}
            </p>
            {short > 0 && (
              <ul aria-label="Missing cards" className="max-h-48 overflow-y-auto border-t border-rule pt-2 text-sm">
                {plan.short.map((s) => (
                  <li key={`${s.printing.scryfall_id}|${s.finish}`} className="flex gap-2 py-0.5">
                    <span className="min-w-0 flex-1 truncate">{s.printing.name}</span>
                    <span className="tabular text-ink-muted">{s.printing.set_code.toUpperCase()} · ×{s.qty}{s.finish === 'foil' ? ' ✦' : ''}</span>
                  </li>
                ))}
              </ul>
            )}
          </>
        )}
      </ConfirmDialog>

      <ConfirmDialog open={dialog?.kind === 'break'} onOpenChange={(o) => !o && setDialog(null)} title={`Break down ${deck.name}?`} confirmLabel="Break down" onConfirm={breakDown}>
        <p>Its cards go back to your collection as free copies. The decklist stays, so you can build it again later.</p>
      </ConfirmDialog>

      <ConfirmDialog open={dialog?.kind === 'copy'} onOpenChange={(o) => !o && setDialog(null)} title="Copy to edit" confirmLabel="Copy and edit" onConfirm={copy}>
        <p>Precon decklists stay as released, because they’re how the app knows which products your cards came from. Copy it to make your own version you can change freely.</p>
      </ConfirmDialog>
    </>
  );
}
