import fs from 'fs';
import os from 'os';
import path from 'path';
import { localPrincipal } from '@/lib/storage/principal';
import { localBlobStore } from '@/lib/storage/local/local-blob-store';

// Mock the chromium driver so no real browser launches in unit tests.
jest.mock('playwright', () => {
  const pdf = jest.fn(async () => Buffer.from('%PDF-1.7 fake pdf body'));
  const page = {
    setContent: jest.fn(async () => {}),
    emulateMedia: jest.fn(async () => {}),
    pdf,
    close: jest.fn(async () => {}),
    setDefaultTimeout: jest.fn(),
    route: jest.fn(async () => {}),
  };
  const context = { newPage: jest.fn(async () => page), close: jest.fn(async () => {}) };
  const browser = { newContext: jest.fn(async () => context), close: jest.fn(async () => {}) };
  const chromium = { launch: jest.fn(async () => browser) };
  return { chromium, __mock: { page, context, browser, pdf, chromium } };
});

import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';

interface PwMock {
  page: { setContent: jest.Mock; emulateMedia: jest.Mock; pdf: jest.Mock; close: jest.Mock; setDefaultTimeout: jest.Mock; route: jest.Mock };
  context: { newPage: jest.Mock; close: jest.Mock };
  browser: { newContext: jest.Mock; close: jest.Mock };
  pdf: jest.Mock;
  chromium: { launch: jest.Mock };
}
const { __mock } = jest.requireMock('playwright') as { __mock: PwMock };

let dir: string;
beforeEach(() => {
  dir = fs.mkdtempSync(path.join(os.tmpdir(), 'pdf-'));
  __mock.pdf.mockClear();
  __mock.page.setContent.mockClear();
  __mock.page.emulateMedia.mockClear();
  __mock.page.close.mockClear();
  __mock.context.close.mockClear();
  __mock.browser.close.mockClear();
});
afterEach(() => { fs.rmSync(dir, { recursive: true, force: true }); });

describe('generateDocPdf', () => {
  it('writes a %PDF- file at the logical key path (via LocalFsBlobStore)', async () => {
    const principal = localPrincipal(dir);
    await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf');
    const out = path.join(dir, 'pdfs', 'x.pdf');
    expect(fs.existsSync(out)).toBe(true);
    expect(fs.readFileSync(out).subarray(0, 5).toString('latin1')).toBe('%PDF-');
  });

  it('calls blobStore.put with the exact key and pdf bytes', async () => {
    const fakePut = jest.fn(async (_p: unknown, _k: unknown, _b: unknown, _c: unknown) => {});
    const fakeBlobStore = { put: fakePut } as unknown as typeof localBlobStore;
    const principal = localPrincipal(dir);
    await generateDocPdf('<html></html>', principal, 'pdfs/y.pdf', { blobStore: fakeBlobStore });
    expect(fakePut).toHaveBeenCalledWith(
      principal,
      'pdfs/y.pdf',
      expect.any(Buffer),
      'application/pdf',
    );
    const buf = fakePut.mock.calls[0]?.[2] as Buffer | undefined;
    expect(buf?.subarray(0, 5).toString('latin1')).toBe('%PDF-');
  });

  it('emulates print media, prints background, and closes page+context+browser', async () => {
    const principal = localPrincipal(dir);
    await generateDocPdf('<html></html>', principal, 'pdfs/y.pdf');
    expect(__mock.page.emulateMedia).toHaveBeenCalledWith({ media: 'print' });
    expect(__mock.pdf).toHaveBeenCalledWith(expect.objectContaining({ printBackground: true }));
    expect(__mock.page.close).toHaveBeenCalled();
    expect(__mock.context.close).toHaveBeenCalled();
    expect(__mock.browser.close).toHaveBeenCalled();
  });

  it('rejects and leaves no orphan when render hangs (overall timeout)', async () => {
    __mock.pdf.mockImplementationOnce(() => new Promise(() => {})); // never resolves
    const principal = localPrincipal(dir);
    const err = await generateDocPdf('<html></html>', principal, 'pdfs/hang.pdf', { timeoutMs: 50 }).catch((e) => e);
    expect(err).toBeInstanceOf(PdfRendererUnavailable);
    expect((err as PdfRendererUnavailable).statusCode).toBe(503);
    expect((err as Error).message).toMatch(/timed out/);
    expect(fs.existsSync(path.join(dir, 'pdfs', 'hang.pdf'))).toBe(false);
  });

  describe('returnBuffer / typed error / container args (Task 5)', () => {
    const principal = localPrincipal('/tmp/unused-for-blobstore-tests');
    const put = jest.fn(async () => {});
    const blobStore = { put } as unknown as { put: jest.Mock };

    beforeEach(() => { put.mockReset(); delete process.env.STORAGE_BACKEND; });

    it('returnBuffer returns the same bytes it writes', async () => {
      const buf = await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
        returnBuffer: true,
      });
      expect(Buffer.isBuffer(buf)).toBe(true);
      expect(put).toHaveBeenCalledWith(principal, 'pdfs/x.pdf', buf, 'application/pdf');
    });

    it('default (no returnBuffer) preserves void behavior', async () => {
      const result = await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
      });
      expect(result).toBeUndefined();
      expect(put).toHaveBeenCalledTimes(1);
    });

    it('launch failure throws PdfRendererUnavailable(503), not a plain Error', async () => {
      __mock.chromium.launch.mockRejectedValueOnce(new Error('no binary'));
      const err = await generateDocPdf('<h></h>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
      }).catch((e) => e);
      expect(err).toBeInstanceOf(PdfRendererUnavailable);
      expect((err as PdfRendererUnavailable).statusCode).toBe(503);
      expect(put).not.toHaveBeenCalled();
    });

    it('timeout throws PdfRendererUnavailable and writes nothing', async () => {
      __mock.chromium.launch.mockImplementationOnce(async () => ({
        newContext: async () => ({
          newPage: async () => ({
            setContent: () => new Promise(() => {}), // hang forever
            emulateMedia: jest.fn(),
            pdf: jest.fn(),
            route: jest.fn(),
            setDefaultTimeout: jest.fn(),
            close: jest.fn(),
          }),
          close: jest.fn(),
        }),
        close: jest.fn(),
      }));
      const err = await generateDocPdf('<h></h>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
        timeoutMs: 20,
      }).catch((e) => e);
      expect(err).toBeInstanceOf(PdfRendererUnavailable);
      expect(put).not.toHaveBeenCalled();
    });

    it('launches without container sandbox args when STORAGE_BACKEND is not supabase', async () => {
      await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
      });
      const [opts] = __mock.chromium.launch.mock.calls.at(-1) as [{ args?: string[] }];
      expect(opts.args).toBeUndefined();
    });

    it('launches with --no-sandbox/--disable-dev-shm-usage args when STORAGE_BACKEND=supabase', async () => {
      process.env.STORAGE_BACKEND = 'supabase';
      await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', {
        blobStore: blobStore as unknown as typeof localBlobStore,
      });
      const [opts] = __mock.chromium.launch.mock.calls.at(-1) as [{ args?: string[] }];
      expect(opts.args).toEqual(['--no-sandbox', '--disable-dev-shm-usage']);
    });
  });
});
