import type { Browser, BrowserContext, Page } from 'playwright';
import { getStorageBundle } from '@/lib/storage/resolve';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import { PdfRendererUnavailable } from './pdf-renderer-error';

const DEFAULT_TIMEOUT_MS = 30_000;

/**
 * Render a self-contained HTML doc to a PDF via headless Chromium and save it via blobStore.
 *
 * - Locked-down context: JS disabled and all non-`data:` requests blocked — a static, self-contained
 *   doc (inline CSS + base64 images) needs neither, and this shrinks the blast radius.
 * - Print media emulated so the doc's `@media print` rules apply (🖨️/theme/zoom controls hidden).
 * - The rendered PDF bytes are written atomically via blobStore (LocalFsBlobStore uses temp+rename;
 *   cloud impls upload directly).
 * - Cooperative timeout: the render is raced against a timer. On timeout the `finally` closes the
 *   browser (canceling any pending op) and a `timedOut` guard blocks a late write, so a hung
 *   Chromium can never resurrect and write after the job already reported failure. The dangling render
 *   promise gets a no-op `.catch` so its post-close rejection is not an unhandled rejection.
 * - Any failure (launch or render/timeout) is wrapped as `PdfRendererUnavailable` (503) so callers
 *   never have to distinguish "browser wouldn't start" from "render didn't finish in time" — both are
 *   the renderer being unavailable right now.
 * - `opts.returnBuffer` returns the written PDF bytes on success (e.g. for direct HTTP responses);
 *   the default preserves the original void/fire-and-forget behavior used by the local job route.
 * - `STORAGE_BACKEND === 'supabase'` launches Chromium with `--no-sandbox --disable-dev-shm-usage`,
 *   required in the container web tier (no local Mac sandbox, small `/dev/shm`); the local dev path
 *   is unchanged.
 */
export async function generateDocPdf(
  html: string,
  principal: Principal,
  key: string,
  opts: { blobStore?: BlobStore; timeoutMs?: number; returnBuffer?: boolean } = {},
): Promise<Buffer | void> {
  const blobStore = opts.blobStore ?? getStorageBundle().blobStore;
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { chromium } = await import('playwright'); // lazy: only load the driver when a PDF is requested

  let browser: Browser | null = null;
  let context: BrowserContext | null = null;
  let page: Page | null = null;
  let timedOut = false;
  let rendered: Buffer | undefined;
  let timer: ReturnType<typeof setTimeout> | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timer = setTimeout(() => {
      timedOut = true;
      reject(new Error(`PDF job timed out after ${timeoutMs}ms`));
    }, timeoutMs);
    (timer as { unref?: () => void }).unref?.();
  });

  const launchOpts = process.env.STORAGE_BACKEND === 'supabase'
    ? { timeout: timeoutMs, args: ['--no-sandbox', '--disable-dev-shm-usage'] } // container web tier
    : { timeout: timeoutMs }; // local Mac dev — unchanged

  try {
    try {
      browser = await chromium.launch(launchOpts);
    } catch (err) {
      throw new PdfRendererUnavailable(
        `Failed to launch Chromium for PDF export. Run: npx playwright install chromium\n${(err as Error).message}`,
        { cause: err },
      );
    }
    context = await browser.newContext({ javaScriptEnabled: false });
    page = await context.newPage();
    page.setDefaultTimeout(timeoutMs);
    await page.route('**/*', (route) => {
      if (route.request().url().startsWith('data:')) route.continue();
      else route.abort();
    });

    const render = (async () => {
      await page!.setContent(html, { waitUntil: 'load' });
      await page!.emulateMedia({ media: 'print' });
      const buf = await page!.pdf({ printBackground: true, format: 'A4' });
      if (timedOut) return; // the timeout path already won — never write after reporting failure
      await blobStore.put(principal, key, buf, 'application/pdf');
      rendered = buf; // only set once the write has actually completed
    })();
    // If the timeout wins the race, `render` will reject later when the browser is closed in finally;
    // this handler keeps that from becoming an unhandled rejection.
    render.catch(() => { /* swallow post-timeout rejection */ });

    await Promise.race([render, timeout]);
  } catch (err) {
    if (err instanceof PdfRendererUnavailable) throw err;
    throw new PdfRendererUnavailable(`PDF render failed: ${(err as Error).message}`, { cause: err });
  } finally {
    if (timer) clearTimeout(timer);
    // Close the browser FIRST so a hung/pending render is actually canceled.
    if (page) { try { await page.close(); } catch { /* ignore */ } }
    if (context) { try { await context.close(); } catch { /* ignore */ } }
    if (browser) { try { await browser.close(); } catch { /* ignore */ } }
  }

  if (opts.returnBuffer) return rendered; // Buffer on success; unreachable on failure (throws above)
}
