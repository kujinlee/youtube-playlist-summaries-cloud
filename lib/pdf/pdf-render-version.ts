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
  const hash = crypto.createHash('sha256').update(htmlNonceFree, 'utf8').digest('hex').slice(0, 16);
  const key = `pdfs/${base}.r${PDF_RENDER_VERSION}.${hash}.pdf`;
  assertLogicalKey(key);
  return key;
}
