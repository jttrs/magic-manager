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
      const raw = (m as MessageEvent).data;
      if (raw == null) {
        // The connection's own error (no payload). EventSource retries a dropped
        // stream by itself; a CLOSED one was refused (e.g. 404: the server no
        // longer knows this job after a restart), so report it as failed.
        if (type === 'error' && es.readyState === 2 /* CLOSED */) {
          onEvent({ type: 'error', data: { error: 'the server lost track of this job — it may have restarted' } });
          onEvent({ type: 'status', data: { status: 'failed' } });
        }
        return;
      }
      const e = { type, data: JSON.parse(raw) } as JobEvent;
      onEvent(e);
      if (e.type === 'status' && (e.data.status === 'succeeded' || e.data.status === 'failed')) es.close();
    });
  }
  return () => es.close();
}
