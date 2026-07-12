import { runSingleFlight } from '@/lib/pdf/pdf-concurrency';
const defer = () => { let resolve!: () => void; const p = new Promise<void>(r => (resolve = r)); return { p, resolve }; };

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
});

describe('withPdfSlot cap', () => {
  it('throws PdfBusyError(503) when saturated and does not over-release', async () => {
    process.env.PDF_MAX_CONCURRENCY = '1'; jest.resetModules();
    const { withPdfSlot, PdfBusyError } = await import('@/lib/pdf/pdf-concurrency');
    const d = defer(); const held = withPdfSlot(() => d.p);
    await expect(withPdfSlot(async () => 'x')).rejects.toBeInstanceOf(PdfBusyError);
    d.resolve(); await held;
    await expect(withPdfSlot(async () => 'y')).resolves.toBe('y'); // freed → not over-released
  });
});
