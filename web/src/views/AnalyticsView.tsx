import { useQuery } from '@tanstack/react-query';
import { getRouteApi, Link } from '@tanstack/react-router';
import { useState, type FormEvent, type ReactNode } from 'react';
import { analyticsSummaryQuery, unwrap } from '../app/queries';
import { useFeature } from '../app/features';
import { ViewLayout } from '../components/AppShell';
import { Button } from '../components/Button';
import { CopyButton } from '../components/CopyButton';
import { Segmented, SideSection, TextField } from '../components/Sidebar';
import { EmptyNote, ErrorNote, GuideSheet } from '../components/States';
import { analyticsTrace, type AnalyticsSummaryResponses } from '../core/api';
import { ageLabel, eventTitle, featureLabel, fmtDuration, funnelRate, groupTitle, PERIODS, shortRef, viewRows, type Period } from '../core/analyticsDashboard';
import { fmtCount, fmtInt } from '../core/format';

type Summary = AnalyticsSummaryResponses[200];
const route = getRouteApi('/analytics');

/** Internal (flag `analytics`): error trends first, then how the app is used. */
export function AnalyticsView() {
  const on = useFeature('analytics');
  const { days, ref } = route.useSearch();
  const navigate = route.useNavigate();
  const q = useQuery({ ...analyticsSummaryQuery(days), enabled: on });
  const s = q.data;

  const sidebar = (
    <div className="flex flex-col gap-6">
      <SideSection title="Period">
        <Segmented<`${Period}`>
          label="Period"
          value={`${days as Period}`}
          options={PERIODS.map((p) => ({ value: `${p}` as `${Period}`, label: `${p} days` }))}
          onChange={(v) => void navigate({ search: (prev) => ({ ...prev, days: Number(v) as Period }) })}
        />
      </SideSection>
      <RefLookup current={ref} onLookup={(r) => void navigate({ search: (prev) => ({ ...prev, ref: r }) })} />
      {s && <StoreFacts s={s} />}
    </div>
  );

  return (
    <ViewLayout label="Analytics controls" sidebar={sidebar} summary={`Last ${days} days`}>
      <GuideSheet
        title="Analytics"
        summary={s ? `${s.since} → ${s.until} · errors first, then how the app is used` : 'Errors and usage, from this server’s own event store'}
      >
        {!on ? (
          <EmptyNote title="Analytics is off on this machine">
            Turn on the internal <code>analytics</code> flag (<code>MM_FEATURES=analytics</code> or <code>config/features.local.toml</code>) and restart <code>mm serve</code>.
          </EmptyNote>
        ) : q.error ? (
          <ErrorNote error={q.error} onRetry={() => void q.refetch()} />
        ) : !s ? (
          <p role="status" className="px-5 py-6 text-md text-ink-muted">Reading the event store…</p>
        ) : (
          <div className="h-full min-h-0 overflow-y-auto px-5 pb-8">
            {ref && <Trace refId={ref} onClose={() => void navigate({ search: (prev) => ({ ...prev, ref: undefined }) })} />}
            <Figures s={s} />
            <div className="mt-6 grid gap-x-8 gap-y-8 xl:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)]">
              <div className="flex min-w-0 flex-col gap-8">
                <ErrorTrend s={s} />
                <TopErrors s={s} />
                <RecentErrors s={s} />
              </div>
              <div className="flex min-w-0 flex-col gap-8">
                <Views s={s} />
                <Features s={s} />
                <Funnel s={s} />
                <Jobs s={s} />
              </div>
            </div>
          </div>
        )}
      </GuideSheet>
    </ViewLayout>
  );
}

function Section({ id, title, aside, children }: { id: string; title: string; aside?: ReactNode; children: ReactNode }) {
  return (
    <section aria-labelledby={id} className="min-w-0">
      <h2 id={id} className="flex items-baseline gap-3 border-b-2 border-rule-strong pb-1 text-2xl voice-condensed font-bold uppercase">
        {title}
        {aside && <span className="ml-auto text-sm normal-case voice-semi font-normal tabular text-ink-muted">{aside}</span>}
      </h2>
      {children}
    </section>
  );
}

/** One ruled ledger line of the period's totals — figures, not cards. */
function Figures({ s }: { s: Summary }) {
  const t = s.totals;
  const items: [string, number, boolean][] = [
    ['errors', t.errors, t.errors > 0],
    ['sessions', t.sessions, false],
    ['sessions hit an error', t.sessions_with_errors, t.sessions_with_errors > 0],
    ['usage events', t.usage, false],
  ];
  return (
    <dl className="mt-1 flex flex-wrap gap-x-8 gap-y-2 border-b border-rule pb-3" aria-label="Totals">
      {items.map(([label, n, bad]) => (
        <div key={label} className="flex items-baseline gap-2">
          <dt className="order-2 text-sm voice-semi text-ink-muted">{label}</dt>
          <dd className={`order-1 text-2xl voice-condensed font-bold tabular ${bad ? 'text-danger' : 'text-ink'}`}>{fmtInt(n)}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Errors per day as a ruled tally: one column per day, the busiest day full height. */
function ErrorTrend({ s }: { s: Summary }) {
  const max = Math.max(1, ...s.error_trend.map((d) => d.n));
  const peak = s.error_trend.reduce((a, d) => (d.n > a.n ? d : a), s.error_trend[0] ?? { day: '', n: 0 });
  return (
    <Section id="trend-h" title="Errors per day" aside={peak.n ? `peak ${fmtInt(peak.n)} on ${peak.day}` : 'none recorded'}>
      <figure className="mt-3">
        <ol className="flex h-24 items-end gap-px border-b border-rule-strong" aria-label="Errors per day">
          {s.error_trend.map((d) => (
            <li key={d.day} className="flex h-full min-w-0 flex-1 items-end" title={`${d.day}: ${fmtCount(d.n, 'error')}`}>
              <span className="sr-only">{d.day}: {fmtCount(d.n, 'error')}</span>
              <span aria-hidden="true" className={`block w-full rounded-t-xs ${d.n ? 'bg-danger' : 'bg-rule'}`} style={{ height: d.n ? `${Math.max(6, (d.n / max) * 100)}%` : '1px' }} />
            </li>
          ))}
        </ol>
        <figcaption className="mt-1 flex justify-between text-xs tabular text-ink-muted">
          <span>{s.since}</span>
          <span>{s.until}</span>
        </figcaption>
      </figure>
    </Section>
  );
}

function TopErrors({ s }: { s: Summary }) {
  return (
    <Section id="top-h" title="Top errors" aside={s.top_errors.length ? `${s.top_errors.length} kinds` : undefined}>
      {s.top_errors.length ? (
        <ol className="mt-1">
          {s.top_errors.map((g) => {
            const t = groupTitle(g);
            return (
              <li key={`${g.name}|${JSON.stringify(g.dims)}`} className="ruled grid grid-cols-[3.5rem_minmax(0,1fr)_auto] items-baseline gap-x-3 py-1.5">
                <span className="text-right text-xl voice-condensed font-bold tabular text-danger">{fmtInt(g.n)}</span>
                <span className="min-w-0">
                  <span className="block truncate voice-semi font-medium">{t.what}</span>
                  <span className="block truncate text-sm tabular text-ink-muted">{t.how}</span>
                </span>
                <span className="text-xs tabular text-ink-muted" title={`first seen ${g.first_seen}`}>{ageLabel(g.last_seen, s.until)}</span>
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="mt-3 text-md text-ink-muted">No errors recorded in this period.</p>
      )}
    </Section>
  );
}

function RecentErrors({ s }: { s: Summary }) {
  return (
    <Section id="recent-h" title="Recent errors">
      {s.recent_errors.length ? (
        <ol className="mt-1">
          {s.recent_errors.map((e) => {
            const t = eventTitle(e);
            return (
              <li key={e.event_id} className="ruled grid grid-cols-[minmax(0,1fr)_auto] items-baseline gap-x-3 py-1.5">
                <span className="min-w-0">
                  <span className="block truncate voice-semi font-medium">{t.what} <span className="font-normal text-ink-muted">· {t.how}</span></span>
                  <span className="block text-xs tabular text-ink-muted">{new Date(e.ts).toLocaleString()}</span>
                </span>
                {e.request_id ? (
                  <Link to="/analytics" search={(prev) => ({ ...prev, ref: shortRef(e.request_id) })} className="text-sm tabular text-accent-ink underline-offset-2 hover:underline" aria-label={`Trace ref ${shortRef(e.request_id)}`}>
                    {shortRef(e.request_id)}
                  </Link>
                ) : (
                  <span className="text-xs text-ink-muted">client</span>
                )}
              </li>
            );
          })}
        </ol>
      ) : (
        <p className="mt-3 text-md text-ink-muted">Nothing in the last 30 days of raw error events.</p>
      )}
    </Section>
  );
}

function Views({ s }: { s: Summary }) {
  const rows = viewRows(s.views);
  return (
    <Section id="views-h" title="Views" aside={rows.length ? 'bar = visits · dark part = phone' : undefined}>
      {rows.length ? (
        <ol className="mt-1">
          {rows.map((v) => (
            <li key={v.view} className="ruled grid grid-cols-[8rem_minmax(0,1fr)_3.5rem] items-center gap-x-3 py-1.5">
              <span className="truncate voice-semi">{v.label}</span>
              <span className="h-2 overflow-hidden rounded-pill bg-rule" aria-hidden="true">
                <span className="flex h-full" style={{ width: `${v.share * 100}%` }}>
                  <span className="h-full bg-ink-muted" style={{ width: `${(1 - v.narrowShare) * 100}%` }} />
                  <span className="h-full bg-ink" style={{ width: `${v.narrowShare * 100}%` }} />
                </span>
              </span>
              <span className="text-right tabular" aria-label={`${fmtCount(v.n, 'visit')}, ${fmtInt(v.narrow)} on a phone`}>{fmtInt(v.n)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-md text-ink-muted">No page views recorded (usage analytics may be off).</p>
      )}
    </Section>
  );
}

function Features({ s }: { s: Summary }) {
  const rows = s.features.filter((f) => f.name !== 'job.started' && f.name !== 'job.succeeded');
  return (
    <Section id="features-h" title="Features">
      {rows.length ? (
        <ol className="mt-1">
          {rows.map((f) => (
            <li key={`${f.name}|${JSON.stringify(f.dims)}`} className="ruled flex items-baseline gap-3 py-1.5">
              <span className="min-w-0 flex-1 truncate">{featureLabel(f.name, f.dims)}</span>
              <span className="text-xs tabular text-ink-muted">{ageLabel(f.last_seen, s.until)}</span>
              <span className="w-12 text-right tabular">{fmtInt(f.n)}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="mt-3 text-md text-ink-muted">No feature use recorded yet.</p>
      )}
    </Section>
  );
}

function Funnel({ s }: { s: Summary }) {
  const [first, last] = [s.funnel[0]?.sessions ?? 0, s.funnel.at(-1)?.sessions ?? 0];
  const rate = funnelRate(first, last);
  return (
    <Section id="funnel-h" title="Collection → buy-list" aside={rate != null ? `${rate}% of sessions` : undefined}>
      <ol className="mt-1">
        {s.funnel.map((f) => (
          <li key={f.step} className="ruled flex items-baseline gap-3 py-1.5">
            <span className="flex-1">{f.step}</span>
            <span className="tabular">{fmtCount(f.sessions, 'session')}</span>
          </li>
        ))}
      </ol>
      <p className="mt-2 text-sm text-ink-muted">
        Sessions: median {s.sessions.median_minutes != null ? `${s.sessions.median_minutes} min` : '—'}, {s.sessions.median_events ?? '—'} events.
      </p>
    </Section>
  );
}

function Jobs({ s }: { s: Summary }) {
  return (
    <Section id="jobs-h" title="Jobs">
      {s.jobs.length ? (
        <table className="mt-1 w-full text-left text-md">
          <thead>
            <tr className="ruled text-xs voice-semi uppercase tracking-[0.06em] text-ink-muted">
              <th className="py-1 font-normal">Job</th>
              <th className="py-1 text-right font-normal">Runs</th>
              <th className="py-1 text-right font-normal">Failed</th>
              <th className="py-1 text-right font-normal">Typical</th>
            </tr>
          </thead>
          <tbody>
            {s.jobs.map((j) => (
              <tr key={j.job} className="ruled">
                <td className="max-w-0 truncate py-1.5 tabular">{j.job}</td>
                <td className="py-1.5 text-right tabular">{fmtInt(j.runs)}</td>
                <td className={`py-1.5 text-right tabular ${j.failures ? 'text-danger' : ''}`}>{fmtInt(j.failures)}</td>
                <td className="py-1.5 text-right tabular text-ink-muted">{fmtDuration(j.mean_ms)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="mt-3 text-md text-ink-muted">No background jobs recorded.</p>
      )}
    </Section>
  );
}

function RefLookup({ current, onLookup }: { current?: string; onLookup: (ref: string) => void }) {
  const [value, setValue] = useState(current ?? '');
  const [error, setError] = useState('');
  const submit = (ev: FormEvent) => {
    ev.preventDefault();
    const r = value.trim().toLowerCase();
    if (!/^[0-9a-f]{6,32}$/.test(r)) {
      setError('A ref is 6–32 letters a–f and digits, as shown beside an error.');
      return;
    }
    setError('');
    onLookup(r);
  };
  return (
    <form onSubmit={submit}>
      <SideSection title="Trace an error">
        <p className="text-sm leading-relaxed text-on-chrome-muted">Paste the ref someone saw beside an error to find what happened.</p>
        <TextField name="ref" label="Ref" value={value} placeholder="e.g. 3f9a12c0" onChange={setValue} />
        <Button type="submit">Find</Button>
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
      </SideSection>
    </form>
  );
}

function Trace({ refId, onClose }: { refId: string; onClose: () => void }) {
  const q = useQuery({
    queryKey: ['analytics', 'trace', refId],
    queryFn: async ({ signal }) => unwrap(await analyticsTrace({ path: { ref: refId }, signal })),
  });
  return (
    <section aria-labelledby="trace-h" className="mb-6 rounded-sm bg-paper-sunk px-4 py-3">
      <div className="flex items-baseline gap-3">
        <h2 id="trace-h" className="text-xl voice-condensed font-bold">Ref <span className="tabular">{refId}</span></h2>
        <button type="button" onClick={onClose} className="ml-auto cursor-pointer text-sm voice-semi text-ink-muted hover:text-ink">Close trace</button>
      </div>
      {q.error ? (
        <p role="alert" className="mt-1 text-md text-danger">{(q.error as Error).message}</p>
      ) : !q.data ? (
        <p role="status" className="mt-1 text-md text-ink-muted">Looking up…</p>
      ) : !q.data.length ? (
        <p className="mt-1 text-md text-ink-muted">No events for this ref. Errors are kept 30 days, and nothing is recorded for people who opted out.</p>
      ) : (
        <ol className="mt-1">
          {q.data.map((e) => (
            <li key={e.event_id} className="ruled flex flex-wrap items-baseline gap-x-3 py-1.5">
              <span className="voice-semi font-medium">{e.name}</span>
              <span className="text-sm tabular text-ink-muted">{Object.entries(e.props).map(([k, v]) => `${k}=${v}`).join(' · ')}</span>
              <span className="ml-auto text-xs tabular text-ink-muted">{new Date(e.ts).toLocaleString()}</span>
              {e.request_id && <CopyButton label="Copy request id" getText={() => e.request_id ?? ''} />}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

function StoreFacts({ s }: { s: Summary }) {
  const ev = s.store.events;
  const p = s.retention_policy;
  return (
    <SideSection title="Store">
      <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm text-on-chrome">
        <dt className="text-on-chrome-muted">Raw events</dt>
        <dd className="tabular">{fmtInt(ev.error ?? 0)} errors · {fmtInt(ev.usage ?? 0)} usage</dd>
        <dt className="text-on-chrome-muted">Kept</dt>
        <dd className="tabular">errors {p.error_days} d · usage {p.usage_days} d · totals {p.aggregate_days} d</dd>
        <dt className="text-on-chrome-muted">Pruned</dt>
        <dd className="tabular">{s.store.last_pruned ?? 'not yet'}</dd>
        <dt className="text-on-chrome-muted">Recording</dt>
        <dd>{s.consent.disabled ? 'off on this server' : `errors ${s.consent.errors ? 'on' : 'off'} · usage ${s.consent.usage ? 'on' : 'off'}`}</dd>
        <dt className="text-on-chrome-muted">File</dt>
        <dd className="truncate tabular" title={s.store.path}>{s.store.path.split('/').pop()}</dd>
      </dl>
      <p className="text-xs leading-relaxed text-on-chrome-muted">Run any panel as SQL: <code>uv run mm analytics sql top_errors</code></p>
    </SideSection>
  );
}
