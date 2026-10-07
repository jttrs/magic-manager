// API errors, specific and traceable: the server's message, its error code and
// the request ref (docs/analytics.md § Errors are specific). Framework-free.

export class ApiError extends Error {
  readonly status: number | null;
  readonly code: string | null;
  readonly requestId: string | null;
  /** The raw `detail` (some routes return structured detail, e.g. stale rows). */
  readonly detail: unknown;

  constructor(message: string, o: { status?: number | null; code?: string | null; requestId?: string | null; detail?: unknown } = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = o.status ?? null;
    this.code = o.code ?? null;
    this.requestId = o.requestId ?? null;
    this.detail = o.detail;
  }

  /** The short ref a user can quote (first 8 of the request id). */
  get ref(): string | null {
    return this.requestId ? this.requestId.slice(0, 8) : null;
  }
}

type Body = { detail?: unknown; code?: unknown; request_id?: unknown } | undefined;

function messageOf(detail: unknown): string | null {
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    const parts = detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? `${Array.isArray((d as { loc?: unknown }).loc) ? `${((d as { loc: unknown[] }).loc).slice(1).join('.')}: ` : ''}${String((d as { msg: unknown }).msg)}` : null))
      .filter(Boolean);
    return parts.length ? parts.join('; ') : null;
  }
  if (detail && typeof detail === 'object' && 'message' in detail) return String((detail as { message: unknown }).message);
  return null;
}

const isAbort = (e: unknown) =>
  (e instanceof Error || (typeof DOMException !== 'undefined' && e instanceof DOMException)) && (e as Error).name === 'AbortError';

let noAnswer: ((code: 'offline' | 'network') => void) | null = null;
/** Called when a request gets no answer at all (analytics reports it; the server can't). */
export function onNoAnswer(fn: ((code: 'offline' | 'network') => void) | null) {
  noAnswer = fn;
}

/** Build an ApiError from a failed call; `response` undefined = no answer at all. */
export function apiErrorFrom(body: unknown, response: Response | undefined): ApiError {
  const b = (body && typeof body === 'object' ? body : undefined) as Body;
  const requestId = typeof b?.request_id === 'string' ? b.request_id : response?.headers.get('x-request-id') ?? null;
  const code = typeof b?.code === 'string' ? b.code : null;
  if (!response && isAbort(body)) {
    // A cancelled request (navigation, a newer query) is not a failure: never reported.
    return new ApiError('The request was cancelled.', { code: 'aborted' });
  }
  if (!response) {
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    noAnswer?.(offline ? 'offline' : 'network');
    return new ApiError(offline ? 'You’re offline — the server can’t be reached.' : 'The server didn’t answer. Is `mm serve` running?', { code: offline ? 'offline' : 'network' });
  }
  const base = messageOf(b?.detail) ?? `The server answered ${response.status}${response.statusText ? ` ${response.statusText}` : ''}.`;
  const ref = requestId ? requestId.slice(0, 8) : null;
  const message = response.status >= 500 && ref ? `${base} (ref ${ref})` : base;
  return new ApiError(message, { status: response.status, code, requestId, detail: b?.detail });
}
