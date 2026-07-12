import { runSingleFlight } from '@/lib/pdf/pdf-concurrency';
const defer = () => { let resolve!: () => void; const p = new Promise<void>(r => (resolve = r)); return { p, resolve }; };

// The cap tests mutate process.env.PDF_MAX_CONCURRENCY + jest.resetModules(); restore both after each
// so this file cannot leak MAX into another test file sharing the same jest worker. (Task-4 review: Claude Important.)
const ORIG_MAX = process.env.PDF_MAX_CONCURRENCY;
afterEach(() => {
  if (ORIG_MAX === undefined) delete process.env.PDF_MAX_CONCURRENCY;
  else process.env.PDF_MAX_CONCURRENCY = ORIG_MAX;
  jest.resetModules();
});

describe('runSingleFlight', () => {
  it('collapses concurrent same-key calls into one fn invocation', async () => {
    let calls = 0; const d = defer();
    const fn = () => { calls++; return d.p.then(() => 'done'); };
    const a = runSingleFlight('K', fn), b = runSingleFlight('K', fn);
    d.resolve(); expect(await a).toBe('done'); expect(await b).toBe('done'); expect(calls).toBe(1);
  });
  it('clears the entry on failure so the next call retries (no poison)', async () => {
    let calls = 0; const bad = () => { calls++; return Promise.reject(new Error('boom')); };
    await expect(runSingleFlight('K', bad)).rejects.toThrow('boom');
    await expect(runSingleFlight('K', bad)).rejects.toThrow('boom');
    expect(calls).toBe(2);
  });
  it('a SYNCHRONOUS throw in fn is converted to a rejection and still clears the entry (no poison)', async () => {
    let calls = 0;
    const boom = (): Promise<string> => { calls++; throw new Error('sync-boom'); };
    await expect(runSingleFlight('S', boom)).rejects.toThrow('sync-boom');
    await expect(runSingleFlight('S', boom)).rejects.toThrow('sync-boom');
    expect(calls).toBe(2); // second call re-invoked → entry was cleared despite the sync throw
  });
});

describe('withPdfSlot cap', () => {
  it('throws PdfBusyError(503) when saturated (MAX=1) and does not over-release', async () => {
    process.env.PDF_MAX_CONCURRENCY = '1'; jest.resetModules();
    const { withPdfSlot, PdfBusyError } = await import('@/lib/pdf/pdf-concurrency');
    const d = defer(); const held = withPdfSlot(() => d.p);
    await expect(withPdfSlot(async () => 'x')).rejects.toBeInstanceOf(PdfBusyError);
    d.resolve(); await held;
    await expect(withPdfSlot(async () => 'y')).resolves.toBe('y'); // freed → not over-released
  });
  it('at MAX=2 admits exactly two concurrent holders and rejects the third (no off-by-one)', async () => {
    process.env.PDF_MAX_CONCURRENCY = '2'; jest.resetModules();
    const { withPdfSlot, PdfBusyError } = await import('@/lib/pdf/pdf-concurrency');
    const d1 = defer(), d2 = defer();
    const h1 = withPdfSlot(() => d1.p), h2 = withPdfSlot(() => d2.p);
    await expect(withPdfSlot(async () => 'x')).rejects.toBeInstanceOf(PdfBusyError); // 3rd over cap
    d1.resolve(); await h1;                                                          // free one slot
    await expect(withPdfSlot(async () => 'y')).resolves.toBe('y');                   // now admitted
    d2.resolve(); await h2;
  });
  it('PDF_MAX_CONCURRENCY=0 clamps to a floor of 1 (does not inflate to the default 3)', async () => {
    process.env.PDF_MAX_CONCURRENCY = '0'; jest.resetModules();
    const { withPdfSlot, PdfBusyError, PDF_MAX_CONCURRENCY } = await import('@/lib/pdf/pdf-concurrency');
    expect(PDF_MAX_CONCURRENCY).toBe(1);
    const d = defer(); const held = withPdfSlot(() => d.p);
    await expect(withPdfSlot(async () => 'x')).rejects.toBeInstanceOf(PdfBusyError); // floor 1 → 2nd rejected
    d.resolve(); await held;
  });
});
