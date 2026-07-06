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
    await expect(
      generateDocPdf('<html></html>', principal, 'pdfs/hang.pdf', { timeoutMs: 50 }),
    ).rejects.toThrow(/timed out/);
    expect(fs.existsSync(path.join(dir, 'pdfs', 'hang.pdf'))).toBe(false);
  });
});
