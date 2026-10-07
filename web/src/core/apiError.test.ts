import { describe, expect, it } from 'vitest';
import { ApiError, apiErrorFrom, onNoAnswer } from './apiError';

const res = (status: number, headers: Record<string, string> = {}) => new Response(null, { status, headers });

describe('apiErrorFrom', () => {
  it('keeps the server message, code and request ref', () => {
    const e = apiErrorFrom({ detail: 'deck changed since you opened it', code: 'stale_draft', request_id: 'abcdef0123456789abcdef0123456789' }, res(409));
    expect(e).toBeInstanceOf(ApiError);
    expect([e.message, e.code, e.status, e.ref]).toEqual(['deck changed since you opened it', 'stale_draft', 409, 'abcdef01']);
  });

  it('puts the ref in a 5xx message so it can be quoted', () => {
    const e = apiErrorFrom({ detail: 'Unexpected server error — KeyError: x', code: 'key_error', request_id: '1234567890abcdef' }, res(500));
    expect(e.message).toBe('Unexpected server error — KeyError: x (ref 12345678)');
  });

  it('explains validation errors field by field, and falls back to the header id', () => {
    const e = apiErrorFrom({ detail: [{ loc: ['query', 'q'], msg: 'String should have at least 2 characters' }] }, res(422, { 'x-request-id': 'feedfacefeedface' }));
    expect(e.message).toBe('q: String should have at least 2 characters');
    expect(e.requestId).toBe('feedfacefeedface');
  });

  it('says plainly when the server never answered, and reports it', () => {
    const seen: string[] = [];
    onNoAnswer((c) => seen.push(c));
    const e = apiErrorFrom(undefined, undefined);
    onNoAnswer(null);
    expect(e.message).toContain('didn’t answer');
    expect(seen).toEqual(['network']);
  });

  it('treats a cancelled request as cancelled, not a network failure', () => {
    const seen: string[] = [];
    onNoAnswer((c) => seen.push(c));
    const e = apiErrorFrom(new DOMException('aborted', 'AbortError'), undefined);
    onNoAnswer(null);
    expect(e.code).toBe('aborted');
    expect(seen).toEqual([]);
  });
});
