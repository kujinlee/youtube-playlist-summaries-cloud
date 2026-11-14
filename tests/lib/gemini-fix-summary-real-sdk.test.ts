// Backlog #62, round 3. fixSummary's metering driven through the REAL `@google/generative-ai` SDK
// (0.24.1) against a local HTTP server — NOT a mocked SDK.
//
// WHY THIS FILE EXISTS. Round 2 metered an in-flight attempt only when the rejection looked like a
// cancel (`GoogleGenerativeAIAbortError` or an aborted signal), and its tests threw that class by
// hand. Both round-3 reviewers then measured the real SDK: a timeout during the response-BODY read
// (`response.json()` runs outside the SDK's abort wrapper) rejects with a plain DOMException
// `AbortError`, signal NOT aborted — matching neither condition, so a served, presumably billed
// attempt was metered as nothing. The repair removes the classification (each attempt is metered at
// DISPATCH); these cases hold it to the shapes the SDK really produces.
//
// The SDK's 60 s request timer is shortened by intercepting setTimeout for exactly that delay; the
// server is real, and so is every byte of the SDK's fetch, parse and abort handling.
import http from 'node:http';
import type { AddressInfo } from 'node:net';
import { fixSummary, type UsageMeter } from '@/lib/gemini';

const SDK_TIMEOUT_MS = 60_000;      // lib/gemini.ts REQUEST_TIMEOUT_MS, as the SDK receives it
const SHORTENED_MS = 150;

type Mode = 'ok' | 'stall-body' | 'stall-headers';
let mode: Mode = 'ok';
let hits = 0;
let server: http.Server;
let port = 0;

const OK_BODY = JSON.stringify({
  candidates: [{ content: { parts: [{ text: '---\ncorrected\n' }], role: 'model' }, finishReason: 'STOP' }],
  usageMetadata: { promptTokenCount: 10_000, candidatesTokenCount: 4_000 },
});

// A FRESH SERVER PER CASE, on a fresh port. With one shared server, a socket left over from a
// stalled or aborted case made the next case's first request fail as "fetch failed" (measured: the
// last case passed alone and failed after the others).
beforeEach(async () => {
  server = http.createServer((req, res) => {
    hits++;
    req.resume();
    if (mode === 'stall-headers') return;                         // never answers at all
    res.writeHead(200, { 'Content-Type': 'application/json' });
    if (mode === 'stall-body') { res.write(OK_BODY.slice(0, 40)); return; }   // headers + half a body, then silence
    res.end(OK_BODY);
  });
  await new Promise<void>((r) => server.listen(0, '127.0.0.1', r));
  port = (server.address() as AddressInfo).port;
});
afterEach(async () => {
  server.closeAllConnections();
  await new Promise<void>((r) => server.close(() => r()));
});

const realFetch = global.fetch;
const realSetTimeout = global.setTimeout;
beforeEach(() => {
  hits = 0;
  mode = 'ok';
  process.env.GEMINI_API_KEY = 'test-key';
  // Redirect the SDK's request to the local server, keeping its init (signal included) untouched.
  jest.spyOn(global, 'fetch').mockImplementation(((input: RequestInfo | URL, init?: RequestInit) => {
    const u = new URL(String(input));
    return realFetch(`http://127.0.0.1:${port}${u.pathname}${u.search}`, init);
  }) as typeof fetch);
  jest.spyOn(global, 'setTimeout').mockImplementation(((fn: (...a: unknown[]) => void, ms?: number, ...a: unknown[]) =>
    realSetTimeout(fn, ms === SDK_TIMEOUT_MS ? SHORTENED_MS : ms, ...a)) as typeof setTimeout);
});
afterEach(() => {
  jest.restoreAllMocks();
});

const UNKNOWN = { promptTokens: null, outputTokens: null };

describe('fixSummary meters at dispatch — through the real SDK (backlog #62, round 3)', () => {
  it('a served attempt REPLACES its provisional entry with the measured usage', async () => {
    const meter: UsageMeter = { attempts: [] };
    const r = await fixSummary('md', 'c', { signal: new AbortController().signal, meter }, 0, 0);
    expect(r.text).toBe('---\ncorrected');
    expect(meter.attempts).toEqual([{ promptTokens: 10_000, outputTokens: 4_000 }]);
  });

  it('an SDK timeout during the BODY read is metered — the shape both reviewers measured', async () => {
    mode = 'stall-body';
    const meter: UsageMeter = { attempts: [] };
    const err = await fixSummary('md', 'c', { signal: new AbortController().signal, meter }, 0, 0)
      .then(() => null, (e: unknown) => e);
    expect(meter.attempts).toEqual([UNKNOWN]);
    // Our timer, not the caller's cancel: a retryable failure, never re-labelled AbortError.
    expect((err as Error).name).not.toBe('AbortError');
    expect((err as Error).message).toMatch(/summary fix failed/);
  });

  it('a body-read timeout is RETRIED and every attempt is metered', async () => {
    mode = 'stall-body';
    const meter: UsageMeter = { attempts: [] };
    await expect(fixSummary('md', 'c', { signal: new AbortController().signal, meter }, 1, 0))
      .rejects.toThrow(/summary fix failed/);
    expect(hits).toBe(2);
    expect(meter.attempts).toEqual([UNKNOWN, UNKNOWN]);
  });

  it('an SDK timeout before any header arrives is metered and retryable too', async () => {
    mode = 'stall-headers';
    const meter: UsageMeter = { attempts: [] };
    await expect(fixSummary('md', 'c', { signal: new AbortController().signal, meter }, 0, 0))
      .rejects.toThrow(/summary fix failed/);
    expect(meter.attempts).toEqual([UNKNOWN]);
  });

  it('a CALLER abort in flight is metered, surfaces as AbortError, and is not retried', async () => {
    mode = 'stall-body';
    const ac = new AbortController();
    const meter: UsageMeter = { attempts: [] };
    const p = fixSummary('md', 'c', { signal: ac.signal, meter }, 2, 0);
    realSetTimeout(() => ac.abort(), 40);
    await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(hits).toBe(1);
    expect(meter.attempts).toEqual([UNKNOWN]);
  });

  it('a CALLER abort on the LAST attempt still surfaces as AbortError (round 2 L2, now via the signal)', async () => {
    mode = 'stall-headers';
    const ac = new AbortController();
    const meter: UsageMeter = { attempts: [] };
    const p = fixSummary('md', 'c', { signal: ac.signal, meter }, 0, 0);
    realSetTimeout(() => ac.abort(), 40);
    await expect(p).rejects.toThrow(expect.objectContaining({ name: 'AbortError' }));
    expect(meter.attempts).toEqual([UNKNOWN]);
  });
});
