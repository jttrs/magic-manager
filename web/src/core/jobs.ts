// Job-event stream client over SSE (EventSource reconnects with Last-Event-ID; the
// server replays history after it). Framework-free; returns an unsubscribe fn.
export type JobEvent =
  | { type: 'status'; data: { status: 'queued' | 'running' | 'succeeded' | 'failed' } }
  | { type: 'progress'; data: { done: number; total: number | null; message: string; level: string } }
  | { type: 'result'; data: { summary: string; artifacts: unknown[] } }
  | { type: 'error'; data: { error: string } };

export function watchJob(id: string, onEvent: (e: JobEvent) => void): () => void {
  const es = new EventSource(`/api/jobs/${encodeURIComponent(id)}/events`);
  for (const type of ['status', 'progress', 'result', 'error'] as const) {
    es.addEventListener(type, (m) => {
      const e = { type, data: JSON.parse((m as MessageEvent).data) } as JobEvent;
      onEvent(e);
      if (e.type === 'status' && (e.data.status === 'succeeded' || e.data.status === 'failed')) es.close();
    });
  }
  return () => es.close();
}
