// lib/pdf/pdf-render-version.ts
import crypto from 'crypto';
import { assertLogicalKey } from '@/lib/storage/blob-store';

/** Bump when ANY PDF render setting (A4/margins/printBackground/print-media/fonts) OR the pinned
 *  Playwright/Chromium version (package.json "playwright") changes — these alter PDF bytes WITHOUT
 *  changing the HTML, so they must bust the cache. The unit test cannot detect a MISSED bump
 *  (it only checks the current key carries the current constant); treat bumping as a review-time
 *  checklist item whenever generate-doc-pdf.ts or the Playwright dep changes. (Round-1 plan L1.) */
export const PDF_RENDER_VERSION = 1;

export function pdfCacheKey(base: string, htmlNonceFree: string): string {
  // `base` becomes the object NAME in `pdfs/{base}...`, so it must be a single path segment.
  // Callers pass the md key minus `.md`, already validated by assertCloudSummaryMdKey — this is a
  // self-defending check so the single-object contract can't be silently broken by a future caller:
  // a slash in `base` diverges local storage (path.join normalizes `//`) from Supabase (literal key),
  // collapsing cache identities on one backend but not the other. (Task-3 dual review Medium.)
  if (!base || base.includes('/') || base.includes('\\') || base.includes('\0') || base.includes('..')) {
    throw new Error(`invalid pdf cache base (must be a single path segment): ${base}`);
  }
  const hash = crypto.createHash('sha256').update(htmlNonceFree, 'utf8').digest('hex').slice(0, 16);
  const key = `pdfs/${base}.r${PDF_RENDER_VERSION}.${hash}.pdf`;
  assertLogicalKey(key);
  return key;
}
