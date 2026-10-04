import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';
import { submitJob } from '../core/api';
import { watchJob, type JobEvent } from '../core/jobs';

export type JobLive = {
  status: string;
  done: number;
  total: number | null;
  log: { seq: number; msg: string; level: string }[];
  summary?: string;
  artifacts?: unknown[];
  error?: string;
};

const fresh = (): JobLive => ({ status: 'queued', done: 0, total: null, log: [] });

/** Watch one job's SSE stream; `start` enqueues a registered job and follows it. */
export function useJob() {
  const qc = useQueryClient();
  const [id, setId] = useState<string | null>(null);
  const [live, setLive] = useState<JobLive | null>(null);
  const stop = useRef<() => void>(() => {});

  useEffect(() => {
    if (!id) return;
    stop.current = watchJob(id, (e: JobEvent) => {
      setLive((l) => {
        const cur = l ?? fresh();
        switch (e.type) {
          case 'status':
            if (e.data.status === 'succeeded' || e.data.status === 'failed') qc.invalidateQueries({ queryKey: ['jobs'] });
            return { ...cur, status: e.data.status };
          case 'progress':
            return { ...cur, done: e.data.done, total: e.data.total, log: [...cur.log.slice(-199), { seq: (cur.log.at(-1)?.seq ?? 0) + 1, msg: e.data.message, level: e.data.level }] };
          case 'result':
            return { ...cur, summary: e.data.summary, artifacts: e.data.artifacts };
          case 'error':
            return { ...cur, error: e.data.error };
        }
      });
    });
    return () => stop.current();
  }, [id, qc]);

  /** Follow an existing job (e.g. one picked from the Recent list). */
  const follow = useCallback((jobId: string) => {
    setLive(fresh());
    setId(jobId);
  }, []);

  /** Enqueue `name` with `body`; resolves to an error message, or null when started. */
  const start = useCallback(async (name: string, body: Record<string, unknown>): Promise<string | null> => {
    try {
      const r = await submitJob({ path: { name }, body });
      if (r.error || !r.data) return 'The server rejected the job.';
      follow(r.data.id);
      qc.invalidateQueries({ queryKey: ['jobs'] });
      return null;
    } catch {
      return 'Couldn’t reach the server. Is `uv run mm serve` running?';
    }
  }, [follow, qc]);

  const reset = useCallback(() => {
    stop.current();
    setId(null);
    setLive(null);
  }, []);

  return { live, start, follow, reset };
}
