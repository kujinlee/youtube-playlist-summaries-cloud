import { pdfCacheKey, PDF_RENDER_VERSION } from '@/lib/pdf/pdf-render-version';
const base = '0007_intro';
it('is deterministic for identical HTML (→ cache hit)', () =>
  expect(pdfCacheKey(base, '<h>x</h>')).toBe(pdfCacheKey(base, '<h>x</h>')));
it('differs when HTML differs', () =>
  expect(pdfCacheKey(base, '<h>a</h>')).not.toBe(pdfCacheKey(base, '<h>b</h>')));
it('a PDF_RENDER_VERSION bump busts the cache (version is in the key)', () =>
  expect(pdfCacheKey(base, '<h>x</h>')).toContain(`.r${PDF_RENDER_VERSION}.`));
it('shape: pdfs/{base}.r{V}.{16 hex}.pdf', () =>
  expect(pdfCacheKey(base, '<h>x</h>')).toMatch(new RegExp(`^pdfs/${base}\\.r\\d+\\.[0-9a-f]{16}\\.pdf$`)));
