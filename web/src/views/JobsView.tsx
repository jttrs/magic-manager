import { useQuery } from '@tanstack/react-query';
import { useState, type FormEvent } from 'react';
import { jobsQuery } from '../app/queries';
import { useJob } from '../app/useJob';
import { ViewLayout } from '../components/AppShell';
import { Button } from '../components/Button';
import { SideSection, TextField } from '../components/Sidebar';
import { EmptyNote, GuideSheet } from '../components/States';
import { fmtInt } from '../core/format';

/** The job-runner chassis: configure → enqueue → stream progress (SSE) → result. */
export function JobsView() {
  const jobs = useQuery(jobsQuery());
  const [families, setFamilies] = useState('');
  const [cardType, setCardType] = useState('legendary creature');
  const [resume, setResume] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [tagError, setTagError] = useState('');
  const { live, start, follow } = useJob();

  async function onSubmit(ev: FormEvent) {
    ev.preventDefault();
    setFormError('');
    const fam = families.split(',').map((s) => s.trim()).filter(Boolean);
    if (!fam.length) {
      setFormError('Enter at least one set-family code, e.g. fin, msh.');
      return;
    }
    setSubmitting(true);
    const err = await start('edhrec.sync_bulk', { families: fam, card_type: cardType || null, resume });
    setSubmitting(false);
    if (err) setFormError(err === 'The server rejected the job.' ? 'The server rejected the job. Check the family codes and try again.' : err);
  }

  async function onSyncTags() {
    setTagError('');
    setSubmitting(true);
    const err = await start('scryfall.sync_tags', { refresh: false });
    setSubmitting(false);
    if (err) setTagError(err);
  }

  const pct = live?.total ? Math.round((live.done / live.total) * 100) : null;

  const sidebar = (
    <div className="flex flex-col gap-6">
    <form onSubmit={onSubmit} className="flex flex-col gap-6" aria-describedby="job-form-error">
      <SideSection title="Warm EDHREC cache">
        <p className="text-sm leading-relaxed text-on-chrome-muted">Fetch EDHREC pages for every card in the given set families so compares load instantly.</p>
        <TextField name="families" label="Set families" value={families} placeholder="fin, msh, tla…" onChange={setFamilies} />
        <TextField name="card_type" label="Type filter" value={cardType} placeholder="legendary creature…" onChange={setCardType} />
        <label className="flex cursor-pointer items-center gap-2 text-sm text-on-chrome">
          <input type="checkbox" checked={resume} onChange={(e) => setResume(e.target.checked)} className="h-4 w-4 accent-[var(--theme-accent)]" />
          Skip cards already cached
        </label>
        <Button type="submit" emphasis="primary" disabled={submitting}>{submitting ? 'Starting…' : 'Start warm-up'}</Button>
        <p id="job-form-error" role="alert" className="min-h-4 text-sm text-danger">{formError}</p>
      </SideSection>
    </form>
    <SideSection title="Sync Scryfall tags">
      <p className="text-sm leading-relaxed text-on-chrome-muted">Download Scryfall’s daily oracle-tag file so Commanders can group cards by function.</p>
      <Button type="button" disabled={submitting} onClick={onSyncTags}>Sync tags</Button>
      {tagError && <p role="alert" className="text-sm text-danger">{tagError}</p>}
    </SideSection>
    </div>
  );

  return (
    <ViewLayout label="Job controls" sidebar={sidebar} startOpen>
      <GuideSheet title="Jobs" summary="Long-running work runs in the background; progress streams live.">
        <div className="grid h-full min-h-0 gap-6 overflow-y-auto px-5 pb-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
          <section aria-labelledby="live-h" className="min-w-0">
            <h2 id="live-h" className="border-b-2 border-rule-strong pb-1 text-2xl voice-condensed font-bold uppercase">Current run</h2>
            {!live ? (
              <EmptyNote title="No run yet">Start a job from the sidebar to watch it here.</EmptyNote>
            ) : (
              <div className="mt-3 flex flex-col gap-3">
                <p className="flex items-baseline gap-3 text-md">
                  <span className="voice-condensed text-xl font-bold capitalize">{live.status}</span>
                  <span className="tabular text-ink-muted">{fmtInt(live.done)}{live.total != null ? ` / ${fmtInt(live.total)}` : ''}</span>
                  {pct != null && <span className="ml-auto tabular text-ink">{pct}%</span>}
                </p>
                <div className="relative h-1.5 overflow-hidden rounded-pill bg-rule" role="progressbar" aria-label="Job progress" aria-valuemin={0} aria-valuemax={live.total ?? undefined} aria-valuenow={live.done}>
                  <span className="absolute inset-y-0 left-0 bg-highlight-solid transition-[width] ease-guide" style={{ width: `${pct ?? (live.status === 'succeeded' ? 100 : 0)}%` }} />
                </div>
                {live.summary && <p className="highlighter self-start px-1 text-md">{live.summary}</p>}
                {live.error && <p role="alert" className="text-md text-danger">{live.error}</p>}
                <ol className="max-h-[50dvh] overflow-y-auto text-sm tabular" aria-label="Progress log">
                  {live.log.map((l) => (
                    <li key={l.seq} className={`ruled py-1 ${l.level === 'error' ? 'text-danger' : 'text-ink'}`}>{l.msg}</li>
                  ))}
                </ol>
                <p aria-live="polite" className="sr-only">{live.log.at(-1)?.msg}</p>
              </div>
            )}
          </section>
          <section aria-labelledby="recent-h" className="min-w-0">
            <h2 id="recent-h" className="border-b-2 border-rule-strong pb-1 text-2xl voice-condensed font-bold uppercase">Recent</h2>
            {jobs.data?.length ? (
              <ul className="mt-2">
                {jobs.data.map((j) => (
                  <li key={j.id} className="ruled">
                    <button type="button" onClick={() => follow(j.id)} className="flex w-full cursor-pointer flex-col gap-0.5 py-2 text-left hover:bg-paper-sunk">
                      <span className="flex items-baseline gap-2 text-md">
                        <span className="voice-semi font-medium">{j.title}</span>
                        <span className="ml-auto text-xs capitalize text-ink-muted">{j.status}</span>
                      </span>
                      <span className="text-xs tabular text-ink-muted">{j.summary ?? j.error ?? new Date(j.created_at).toLocaleString()}</span>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-3 text-sm text-ink-muted">No jobs since the server started.</p>
            )}
          </section>
        </div>
      </GuideSheet>
    </ViewLayout>
  );
}
