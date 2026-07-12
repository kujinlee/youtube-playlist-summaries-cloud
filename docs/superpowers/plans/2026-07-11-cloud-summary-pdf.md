# Cloud Summary PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cloud-only `GET /api/pdf/[id]` route that lazily renders a video's summary
(rendered HTML doc) to a print-ready A4 PDF via headless Chromium, caches it at a
content-addressed key, and streams it inline — surfaced as a **View PDF** item on the cloud
`VideoMenu`.

**Architecture:** Serve-side materialization of a *stored derived-cache blob* (not a durable
Job). The route reuses `serveCloud`'s gate→read→resolve→render core (extracted into two helpers
so the html route's `format=md` no-charge short-circuit survives), renders the summary HTML
**nonce-free/deterministic**, hashes it into a content-addressed key salted with
`PDF_RENDER_VERSION`, checks the blob cache with one `get`, and on a miss renders with Chromium
under a concurrency cap + per-key single-flight. No new charging surface; no new table/RPC/migration.

**Tech Stack:** Next.js (App Router, this repo's vendored version — read
`node_modules/next/dist/docs/` before touching routes), TypeScript, Playwright/Chromium
(`lib/pdf/generate-doc-pdf.ts`), Supabase Storage (`SupabaseBlobStore`), Jest + ts-jest (unit),
@testing-library/react (component), real-Supabase integration (`signInAs`).

**Design spec:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md`
**ADR:** `docs/adr/0003-cloud-pdf-serve-side-not-a-job.md`
**Glossary:** `CONTEXT.md` (derived-cache blob, promoted, magazine model)

## Global Constraints

- **Cloud-only.** The new `GET /api/pdf/[id]` handles `STORAGE_BACKEND==='supabase'` only; local
  backend → **400**. The existing local `POST /api/videos/[id]/pdf` export and the local menu are
  **untouched and must stay green**.
- **Session-client only** for all user-facing reads/writes; **service role never** from this route.
- **No new charging surface.** The PDF never charges itself; it rides the pre-existing on-view
  `resolveMagazineModel` materialization (per-owner serve budget + daily cap). At most one
  materialization per view, the same an HTML view triggers, never more.
- **`merge_video_data` left unchanged.** The PDF cache is a pure blob existence check — no artifact
  record, no metadata write.
- **Nonce-free hash input.** The PDF is rendered with `renderMagazineHtml(parsed, model, { nonce:
  undefined, dig: false })`; the hash is taken over that deterministic string. Never hash a
  nonce'd render.
- **Cache key:** `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf`.
- **`type` is `summary`-only** this slice (dig deferred); stray `format`/`download` params are ignored.
- **Type check + full suite before every commit:** `npx tsc --noEmit` and `npm test` must pass.

---

## Preflight gate (do FIRST, before Task 2): Supabase Storage put-atomicity

The bare-put/no-promotion cache (ADR 0003) assumes `SupabaseBlobStore.put`
(`upload(..., { upsert: true })`) is **visibility-atomic** on both new and existing objects — a
concurrent `get` sees either the old object or the complete new one, never a partial. Verify this
empirically before building the cache on it.

- [ ] **Step 1: Write the atomicity integration test** (real Supabase, `signInAs`).

`tests/integration/pdf-put-atomicity.test.ts`:

```ts
import { signInAs, makePrincipal } from '../helpers/supabase'; // existing integration helpers
import { getStorageBundle } from '@/lib/storage/resolve';

test('put(upsert) is visibility-atomic: concurrent overwrite+read never yields a partial object', async () => {
  const { supabase, userId } = await signInAs('atomicity-user');
  const { blobStore } = getStorageBundle({ supabaseClient: supabase });
  const principal = makePrincipal(userId, 'atomicity-plist');
  const key = 'pdfs/atomicity-probe.bin';
  const A = Buffer.alloc(2_000_000, 0xaa); // 2 MB distinct fills so a torn read is detectable
  const B = Buffer.alloc(2_000_000, 0xbb);

  await blobStore.put(principal, key, A, 'application/octet-stream');
  // Interleave overwrites with reads; every read must equal a WHOLE A or a WHOLE B.
  const reads: Promise<Buffer | null>[] = [];
  const writes: Promise<void>[] = [];
  for (let i = 0; i < 20; i++) {
    writes.push(blobStore.put(principal, key, i % 2 ? A : B, 'application/octet-stream'));
    reads.push(blobStore.get(principal, key));
  }
  await Promise.all(writes);
  const results = await Promise.all(reads);
  for (const buf of results) {
    if (buf === null) continue; // absent is fine (before first put lands); never partial
    const first = buf[0];
    expect(buf.every((byte) => byte === first)).toBe(true); // homogeneous → whole A or whole B, never torn
    expect(first === 0xaa || first === 0xbb).toBe(true);
    expect(buf.length).toBe(2_000_000);
  }
  await blobStore.delete(principal, key);
});
```

- [ ] **Step 2: Run it against a real Supabase project.**

Run: `STORAGE_BACKEND=supabase npx jest pdf-put-atomicity --runInBand`
Expected: **PASS** — no torn reads.

- [ ] **Step 3: Record the result and branch.**

- **PASS** → the bare-put cache (Task 8) proceeds as written. Note the confirmation in
  `docs/reviews/spec-cloud-pdf-atomicity.md`.
- **FAIL** → **STOP and escalate.** The fallback is a staging-key + atomic manifest pointer
  (spec §10 / ADR 0003): `putStaged` to a unique key, then flip a single-row DB pointer
  (`pdf_cache(owner_id, cache_key) → object_key`) whose update is atomic; the route reads the
  pointer then `get`s the pointed object. Do **not** use `promote` (copy+delete, non-atomic). This
  changes Task 8's write/read and adds a migration — re-plan that task before continuing.

- [ ] **Step 4: Commit the verification.**

```bash
git add tests/integration/pdf-put-atomicity.test.ts docs/reviews/spec-cloud-pdf-atomicity.md
git commit -m "test(cloud-pdf): verify Supabase put visibility-atomicity (bare-put cache gate)"
```

---

## Task 2: `assertCloudSummaryMdKey` — reject nested/foreign summary keys

**Files:**
- Create: `lib/html-doc/assert-cloud-summary-md-key.ts`
- Test: `tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`

**Interfaces:**
- Produces: `assertCloudSummaryMdKey(mdKey: string): void` — throws `Object.assign(new Error(...),
  { statusCode: 409 })` on a bad key. Called by Task 6's `loadSummaryForServe` **before** any
  storage op.

- [ ] **Step 1: Write the failing test**

```ts
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';

describe('assertCloudSummaryMdKey', () => {
  it('accepts a single-component .md basename', () => {
    expect(() => assertCloudSummaryMdKey('0007_intro-to-transformers.md')).not.toThrow();
  });
  it.each([
    ['nested key', 'nested/foo.md'],
    ['backslash', 'nested\\foo.md'],
    ['parent ref', '../foo.md'],
    ['NUL', 'foo\0.md'],
    ['non-md suffix', 'foo.pdf'],
    ['no suffix', 'foo'],
    ['empty base', '.md'],
    ['empty', ''],
  ])('rejects %s with statusCode 409', (_label, key) => {
    try { assertCloudSummaryMdKey(key); throw new Error('did not throw'); }
    catch (e: any) { expect(e.statusCode).toBe(409); }
  });
});
```

- [ ] **Step 2: Run it — expect FAIL** (module not found).

Run: `npx jest assert-cloud-summary-md-key`
Expected: FAIL — cannot find module.

- [ ] **Step 3: Implement**

```ts
// lib/html-doc/assert-cloud-summary-md-key.ts
/**
 * A cloud summary md key must be a SINGLE path component ending in `.md`, with a non-empty base.
 * `assertLogicalKey` (blob-store) alone permits embedded slashes, so a corrupt
 * `summaryMd.key = "nested/foo.md"` would otherwise build nested `models/…`/`pdfs/…` keys.
 * Reject before any blob/model/PDF storage op. (Spec round-2 Medium.)
 */
export function assertCloudSummaryMdKey(mdKey: string): void {
  const bad =
    typeof mdKey !== 'string' ||
    mdKey.length === 0 ||
    mdKey.includes('/') ||
    mdKey.includes('\\') ||
    mdKey.includes('\0') ||
    mdKey.includes('..') ||
    !mdKey.endsWith('.md') ||
    mdKey.slice(0, -3).length === 0;
  if (bad) throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
}
```

- [ ] **Step 4: Run it — expect PASS.**

Run: `npx jest assert-cloud-summary-md-key`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/assert-cloud-summary-md-key.ts tests/lib/html-doc/assert-cloud-summary-md-key.test.ts
git commit -m "feat(cloud-pdf): assertCloudSummaryMdKey — single-component .md key guard"
```

---

## Task 3: `PDF_RENDER_VERSION` + `pdfCacheKey` — content-addressed key builder

**Files:**
- Create: `lib/pdf/pdf-render-version.ts`
- Test: `tests/lib/pdf/pdf-render-version.test.ts`

**Interfaces:**
- Produces:
  - `PDF_RENDER_VERSION: number` — bump when any PDF render setting or the pinned Chromium changes.
  - `pdfCacheKey(base: string, htmlNonceFree: string): string` → `pdfs/{base}.r{V}.{hash16}.pdf`,
    asserted via `assertLogicalKey`.

- [ ] **Step 1: Write the failing test**

```ts
import { pdfCacheKey, PDF_RENDER_VERSION } from '@/lib/pdf/pdf-render-version';

describe('pdfCacheKey', () => {
  const base = '0007_intro';
  it('is deterministic for identical HTML (nonce-free determinism → cache hit)', () => {
    expect(pdfCacheKey(base, '<html>same</html>')).toBe(pdfCacheKey(base, '<html>same</html>'));
  });
  it('differs when HTML differs', () => {
    expect(pdfCacheKey(base, '<html>a</html>')).not.toBe(pdfCacheKey(base, '<html>b</html>'));
  });
  it('embeds the render version so a bump busts the cache', () => {
    expect(pdfCacheKey(base, '<html>x</html>')).toContain(`.r${PDF_RENDER_VERSION}.`);
  });
  it('shape: pdfs/{base}.r{V}.{16 hex}.pdf', () => {
    expect(pdfCacheKey(base, '<html>x</html>')).toMatch(new RegExp(`^pdfs/${base}\\.r\\d+\\.[0-9a-f]{16}\\.pdf$`));
  });
});
```

- [ ] **Step 2: Run it — expect FAIL.**

Run: `npx jest pdf-render-version`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```ts
// lib/pdf/pdf-render-version.ts
import crypto from 'crypto';
import { assertLogicalKey } from '@/lib/storage/blob-store';

/** Bump when any PDF render setting (A4/margins/printBackground/print-media/fonts) or the pinned
 *  Chromium changes — these alter PDF bytes without changing the HTML, so they must bust the cache. */
export const PDF_RENDER_VERSION = 1;

/** Content-addressed cache key over the DETERMINISTIC nonce-free HTML, salted with the render version. */
export function pdfCacheKey(base: string, htmlNonceFree: string): string {
  const hash = crypto.createHash('sha256').update(htmlNonceFree, 'utf8').digest('hex').slice(0, 16);
  const key = `pdfs/${base}.r${PDF_RENDER_VERSION}.${hash}.pdf`;
  assertLogicalKey(key);
  return key;
}
```

- [ ] **Step 4: Run it — expect PASS.**

Run: `npx jest pdf-render-version`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/pdf/pdf-render-version.ts tests/lib/pdf/pdf-render-version.test.ts
git commit -m "feat(cloud-pdf): PDF_RENDER_VERSION + content-addressed pdfCacheKey"
```

---

## Task 4: `pdf-concurrency` — global semaphore + per-key single-flight

**Files:**
- Create: `lib/pdf/pdf-concurrency.ts`
- Test: `tests/lib/pdf/pdf-concurrency.test.ts`

**Interfaces:**
- Produces:
  - `PDF_MAX_CONCURRENCY: number` (default 3; overridable via `PDF_MAX_CONCURRENCY` env).
  - `class PdfBusyError extends Error` (`statusCode = 503`).
  - `runSingleFlight<T>(key: string, fn: () => Promise<T>): Promise<T>` — collapses concurrent
    same-key calls into one `fn`; deletes the map entry in `finally` (success OR error).
  - `withPdfSlot<T>(fn: () => Promise<T>): Promise<T>` — acquires a semaphore slot or throws
    `PdfBusyError`; releases **only if acquired**, in `finally`.

- [ ] **Step 1: Write the failing tests**

```ts
import { runSingleFlight, withPdfSlot, PdfBusyError } from '@/lib/pdf/pdf-concurrency';

const defer = () => { let resolve!: () => void, reject!: (e: any) => void;
  const p = new Promise<void>((res, rej) => { resolve = res; reject = rej; }); return { p, resolve, reject }; };

describe('runSingleFlight', () => {
  it('collapses concurrent same-key calls into one fn invocation', async () => {
    let calls = 0; const d = defer();
    const fn = () => { calls++; return d.p.then(() => 'done'); };
    const a = runSingleFlight('K', fn), b = runSingleFlight('K', fn);
    d.resolve(); expect(await a).toBe('done'); expect(await b).toBe('done');
    expect(calls).toBe(1);
  });
  it('clears the entry on failure so the next call retries (no poison)', async () => {
    let calls = 0;
    const bad = () => { calls++; return Promise.reject(new Error('boom')); };
    await expect(runSingleFlight('K', bad)).rejects.toThrow('boom');
    await expect(runSingleFlight('K', bad)).rejects.toThrow('boom');
    expect(calls).toBe(2); // second call re-ran → entry was cleared
  });
});

describe('withPdfSlot', () => {
  it('throws PdfBusyError (503) when saturated, and does not over-release', async () => {
    process.env.PDF_MAX_CONCURRENCY = '1';
    jest.resetModules();
    const { withPdfSlot, PdfBusyError } = await import('@/lib/pdf/pdf-concurrency');
    const d = defer();
    const held = withPdfSlot(() => d.p);                       // holds the only slot
    await expect(withPdfSlot(async () => 'x')).rejects.toBeInstanceOf(PdfBusyError); // saturated
    d.resolve(); await held;
    await expect(withPdfSlot(async () => 'y')).resolves.toBe('y'); // slot freed → not over-released
  });
});
```

- [ ] **Step 2: Run — expect FAIL.**

Run: `npx jest pdf-concurrency`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement**

```ts
// lib/pdf/pdf-concurrency.ts
export const PDF_MAX_CONCURRENCY = Math.max(1, parseInt(process.env.PDF_MAX_CONCURRENCY ?? '3', 10) || 3);

export class PdfBusyError extends Error {
  statusCode = 503;
  constructor() { super('PDF renderer busy'); this.name = 'PdfBusyError'; }
}

const inFlight = new Map<string, Promise<unknown>>();

/** Collapse concurrent same-key work into one call; ALWAYS delete the entry on settle (round-2 High). */
export function runSingleFlight<T>(key: string, fn: () => Promise<T>): Promise<T> {
  const existing = inFlight.get(key) as Promise<T> | undefined;
  if (existing) return existing;
  const p = (async () => fn())();
  inFlight.set(key, p);
  return p.finally(() => { inFlight.delete(key); }) as Promise<T>;
}

let active = 0;

/** Acquire a slot or throw PdfBusyError; release ONLY IF acquired, in finally (round-3 Low). */
export async function withPdfSlot<T>(fn: () => Promise<T>): Promise<T> {
  if (active >= PDF_MAX_CONCURRENCY) throw new PdfBusyError();
  active++;                       // acquired
  try { return await fn(); }
  finally { active--; }           // reached only after a successful acquire
}
```

- [ ] **Step 4: Run — expect PASS.**

Run: `npx jest pdf-concurrency`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/pdf/pdf-concurrency.ts tests/lib/pdf/pdf-concurrency.test.ts
git commit -m "feat(cloud-pdf): pdf concurrency cap + per-key single-flight with finally cleanup"
```

---

## Task 5: extend `generateDocPdf` — `returnBuffer`, typed 503 error, container launch args

**Files:**
- Modify: `lib/pdf/generate-doc-pdf.ts`
- Create: `lib/pdf/pdf-renderer-error.ts`
- Test: `tests/lib/pdf/generate-doc-pdf.test.ts` (extend if present)

**Interfaces:**
- Produces:
  - `class PdfRendererUnavailable extends Error` (`statusCode = 503`) in `pdf-renderer-error.ts`.
  - `generateDocPdf(html, principal, key, opts?)` — `opts.returnBuffer?: boolean`; return type
    `Promise<Buffer | void>`. On success with `returnBuffer` → the written bytes; on timeout →
    **writes nothing, returns nothing**; launch failure/timeout → throws `PdfRendererUnavailable`.
    Launch uses container-safe args behind the cloud check.
- Consumes: existing `blobStore.put`, the cooperative-timeout shape already in the file.

- [ ] **Step 1: Write the failing tests** (mock `playwright`).

```ts
jest.mock('playwright', () => {
  const pdf = jest.fn(async () => Buffer.from('PDFBYTES'));
  const page = { setContent: jest.fn(), emulateMedia: jest.fn(), pdf, route: jest.fn(), setDefaultTimeout: jest.fn(), close: jest.fn() };
  const context = { newPage: async () => page, close: jest.fn() };
  const browser = { newContext: async () => context, close: jest.fn() };
  return { chromium: { launch: jest.fn(async () => browser) } };
});
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';

const principal = { id: 'u', indexKey: 'p' } as any;
const put = jest.fn();
const blobStore = { put } as any;

beforeEach(() => { put.mockReset(); });

it('returnBuffer returns the same bytes it writes', async () => {
  const buf = await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', { blobStore, returnBuffer: true });
  expect(Buffer.isBuffer(buf)).toBe(true);
  expect(put).toHaveBeenCalledWith(principal, 'pdfs/x.pdf', buf, 'application/pdf');
});

it('default (no returnBuffer) preserves void behavior', async () => {
  const r = await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', { blobStore });
  expect(r).toBeUndefined();
  expect(put).toHaveBeenCalledTimes(1);
});

it('launch failure throws PdfRendererUnavailable (503), not a plain Error', async () => {
  const { chromium } = require('playwright');
  chromium.launch.mockRejectedValueOnce(new Error('no binary'));
  await expect(generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', { blobStore }))
    .rejects.toBeInstanceOf(PdfRendererUnavailable);
});
```

- [ ] **Step 2: Run — expect FAIL.**

Run: `npx jest generate-doc-pdf`
Expected: FAIL — `PdfRendererUnavailable` undefined / `returnBuffer` not honored.

- [ ] **Step 3: Implement the typed error**

```ts
// lib/pdf/pdf-renderer-error.ts
export class PdfRendererUnavailable extends Error {
  statusCode = 503;
  constructor(message: string, options?: { cause?: unknown }) {
    super(message, options as ErrorOptions);
    this.name = 'PdfRendererUnavailable';
  }
}
```

- [ ] **Step 4: Modify `generate-doc-pdf.ts`** — signature, buffer return, typed error, launch args.

Change the signature and the render/launch bodies (keep the existing cooperative-timeout structure):

```ts
import { PdfRendererUnavailable } from './pdf-renderer-error';

export async function generateDocPdf(
  html: string,
  principal: Principal,
  key: string,
  opts: { blobStore?: BlobStore; timeoutMs?: number; returnBuffer?: boolean } = {},
): Promise<Buffer | void> {
  // ...existing setup...
  const launchArgs = (process.env.STORAGE_BACKEND === 'supabase')
    ? { timeout: timeoutMs, args: ['--no-sandbox', '--disable-dev-shm-usage'] } // container web tier
    : { timeout: timeoutMs };                                                    // local Mac unchanged
  let rendered: Buffer | undefined;
  try {
    try { browser = await chromium.launch(launchArgs); }
    catch (err) {
      throw new PdfRendererUnavailable(
        `Failed to launch Chromium for PDF export. Run: npx playwright install chromium`,
        { cause: err },
      );
    }
    // ...existing context/page/route setup...
    const render = (async () => {
      await page!.setContent(html, { waitUntil: 'load' });
      await page!.emulateMedia({ media: 'print' });
      const buf = await page!.pdf({ printBackground: true, format: 'A4' });
      if (timedOut) return;                 // timeout won → write nothing, return nothing
      await blobStore.put(principal, key, buf, 'application/pdf');
      rendered = buf;                        // only set on a completed, written render
    })();
    render.catch(() => { /* swallow post-timeout rejection */ });
    await Promise.race([render, timeout]);
  } catch (err) {
    if (err instanceof PdfRendererUnavailable) throw err;
    throw new PdfRendererUnavailable(`PDF render failed: ${(err as Error).message}`, { cause: err });
  } finally {
    // ...existing browser/page/context close...
  }
  if (opts.returnBuffer) return rendered;   // undefined on timeout (nothing written)
}
```

- [ ] **Step 5: Run tests + type check — expect PASS.**

Run: `npx jest generate-doc-pdf && npx tsc --noEmit`
Expected: PASS; existing local-PDF callers still compile (they ignore the return + new error).

- [ ] **Step 6: Commit**

```bash
git add lib/pdf/generate-doc-pdf.ts lib/pdf/pdf-renderer-error.ts tests/lib/pdf/generate-doc-pdf.test.ts
git commit -m "feat(cloud-pdf): generateDocPdf returnBuffer + PdfRendererUnavailable(503) + container args"
```

---

## Task 6: `serve-summary-core` — two-stage helper (`loadSummaryForServe` + `resolveAndParse`)

**Files:**
- Create: `lib/html-doc/serve-summary-core.ts`
- Test: `tests/lib/html-doc/serve-summary-core.test.ts`

**Interfaces:**
- Consumes: `resolveOwnedPlaylistKey`, `getPrincipalFromSession`, `getStorageBundle`,
  `assertVideoId`, `assertCloudSummaryMdKey` (Task 2), `parseSummaryMarkdown`,
  `resolveMagazineModel` (returns `ResolveResult` — see `lib/html-doc/serve-doc.ts`).
- Produces:
  - `type LoadResult = { ok: true; mdBytes: Buffer; mdKey: string; base: string; title?: string;
    principal: Principal; playlistId: string; video: Video } | { ok: false; status: number; error: string }`
  - `loadSummaryForServe(supabase, { videoId, playlistId, userId }): Promise<LoadResult>` — auth is
    done by the caller; this does owner-playlist → readIndex → gate `summaryMd.status` → select +
    **`assertCloudSummaryMdKey`** → read md blob. **Does NOT resolve the model.**
  - `resolveAndParse(supabase, load): Promise<{ ok: true; parsed: ParsedSummary; model: MagazineModel;
    stale: boolean } | { ok: false; status: number; error: string }>` — parse + `resolveMagazineModel`,
    mapping its statuses to HTTP codes.

- [ ] **Step 1: Write the failing tests** (mock the storage bundle + `resolveMagazineModel`).

```ts
import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
// Arrange a fake supabase + storage bundle whose readIndex returns a video with a promoted summaryMd.

it('gates committed summary → 503', async () => {
  // video.artifacts.summaryMd.status = 'committed'
  const r = await loadSummaryForServe(fakeSupabaseCommitted, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r).toMatchObject({ ok: false, status: 503 });
});

it('rejects a nested mdKey with 409 before reading the blob', async () => {
  // video.artifacts.summaryMd.key = 'nested/foo.md'; blobStore.get is a spy
  const r = await loadSummaryForServe(fakeSupabaseNestedKey, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r).toMatchObject({ ok: false, status: 409 });
  expect(blobGetSpy).not.toHaveBeenCalled();
});

it('promoted summary → ok with mdBytes/base/title, WITHOUT resolving the model', async () => {
  const r = await loadSummaryForServe(fakeSupabasePromoted, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r.ok).toBe(true);
  expect(resolveMagazineModelSpy).not.toHaveBeenCalled(); // Stage 1 never resolves
});

it('resolveAndParse maps model statuses to HTTP codes', async () => {
  resolveMagazineModelSpy.mockResolvedValueOnce({ status: 'over_budget' });
  const r = await resolveAndParse(fakeSupabasePromoted, okLoad);
  expect(r).toMatchObject({ ok: false, status: 503 });
});
```

- [ ] **Step 2: Run — expect FAIL.**

Run: `npx jest serve-summary-core`
Expected: FAIL — module not found.

- [ ] **Step 3: Implement** (mirror `serveCloud` lines 45–107, split at the resolve boundary).

```ts
// lib/html-doc/serve-summary-core.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import { assertVideoId } from '@/lib/index-store';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import type { Video } from '@/types';
// ...types LoadResult / ResolvedResult per the Interfaces block...

export async function loadSummaryForServe(supabase: SupabaseClient, a: { videoId: string; playlistId: string; userId: string }): Promise<LoadResult> {
  try { assertVideoId(a.videoId); } catch { return { ok: false, status: 400, error: 'invalid videoId' }; }
  const playlistKey = await resolveOwnedPlaylistKey(supabase, a.playlistId, a.userId);
  if (!playlistKey) return { ok: false, status: 404, error: 'not found' };
  const principal = getPrincipalFromSession({ userId: a.userId }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase });
  const index = await bundle.metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === a.videoId) as Video | undefined;
  if (!video) return { ok: false, status: 404, error: 'not found' };
  const artifact = (video as any).artifacts?.summaryMd;
  const status = artifact?.status;
  if (status === 'committed') return { ok: false, status: 503, error: 'not ready, retry' };
  if (status !== 'promoted') return { ok: false, status: 404, error: 'not found' };
  const mdKey = artifact?.key ?? (video as any).summaryMd;
  if (!mdKey) return { ok: false, status: 404, error: 'not found' };
  try { assertCloudSummaryMdKey(mdKey); } catch { return { ok: false, status: 409, error: 'corrupt summary key' }; }
  const mdBytes = await bundle.blobStore.get(principal, mdKey);
  if (!mdBytes) return { ok: false, status: 409, error: 'repair needed' };
  const rawTitle: unknown = (video as any).title;
  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;
  return { ok: true, mdBytes, mdKey, base: mdKey.replace(/\.md$/, ''), title, principal, playlistId: a.playlistId, video };
}

export async function resolveAndParse(supabase: SupabaseClient, load: Extract<LoadResult, { ok: true }>, signal?: AbortSignal) {
  const parsed = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  parsed.sourceMd = load.mdKey;
  const bundle = getStorageBundle({ supabaseClient: supabase });
  const resolved = await resolveMagazineModel({
    supabaseClient: supabase, blobStore: bundle.blobStore, principal: load.principal,
    playlistId: load.playlistId, videoId: load.video.id, base: load.base, parsed,
    language: (load.video as any).language, signal,
  });
  switch (resolved.status) {
    case 'denied': return { ok: false as const, status: 404, error: 'not found' };
    case 'busy': return { ok: false as const, status: 503, error: 'generating, retry shortly' };
    case 'attempts_exhausted': return { ok: false as const, status: 503, error: 'temporarily unavailable' };
    case 'at_capacity': return { ok: false as const, status: 503, error: 'at capacity' };
    case 'over_budget': return { ok: false as const, status: 503, error: 'daily refresh budget reached' };
    case 'ok': return { ok: true as const, parsed, model: resolved.model, stale: resolved.stale === true };
  }
}
```

- [ ] **Step 4: Run tests + `tsc` — expect PASS.**

Run: `npx jest serve-summary-core && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/html-doc/serve-summary-core.ts tests/lib/html-doc/serve-summary-core.test.ts
git commit -m "feat(cloud-pdf): two-stage serve-summary-core (load gate+read; resolve+parse)"
```

---

## Task 7: refactor `serveCloud` (html route) through the helpers — behavior-preserving

**Files:**
- Modify: `app/api/html/[id]/route.ts` (`serveCloud`, lines ~27–121)
- Test: `tests/integration/html-route-cloud.test.ts` (extend the existing cloud html tests)

**Interfaces:**
- Consumes: `loadSummaryForServe`, `resolveAndParse` (Task 6).
- **Behavior contract (must not change):** md/html byte output, all status codes, all 6
  `resolveMagazineModel` mappings, the CSP nonce + `X-Magazine-Stale`, and — critically — the
  **`format=md` short-circuit must NOT resolve the model / call `reserve_serve_model`.**

- [ ] **Step 1: Write the failing parity test** (the money guard).

```ts
it('format=md does NOT resolve the magazine model or charge (no reserve_serve_model)', async () => {
  const rpc = jest.spyOn(supabase, 'rpc');
  const res = await GET(reqFor(`/api/html/${VIDEO}?playlist=${PID}&type=summary&format=md&download=1`), ctx);
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toContain('text/markdown');
  expect(rpc).not.toHaveBeenCalledWith('reserve_serve_model', expect.anything());
});

it('html path is byte-identical to pre-refactor for a promoted summary', async () => {
  const res = await GET(reqFor(`/api/html/${VIDEO}?playlist=${PID}&type=summary`), ctx);
  expect(res.status).toBe(200);
  expect(await res.text()).toBe(GOLDEN_HTML); // captured from the pre-refactor route
});
```

- [ ] **Step 2: Run — expect FAIL** (md still routed through the old inline body / golden mismatch until refactor).

Run: `npx jest html-route-cloud`
Expected: FAIL until the refactor lands (write the golden by capturing current output first).

- [ ] **Step 3: Refactor `serveCloud`** to call `loadSummaryForServe`, short-circuit `md` **before**
  `resolveAndParse`, then render html with the fresh CSP nonce (unchanged) for the html path.

```ts
async function serveCloud(request, videoId, searchParams) {
  // ...param validation (outputFolder/type/format/download/playlist) unchanged...
  const supabase = createServerSupabase((await cookies()) as any);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  try {
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);

    if (format === 'md') { // D4 money invariant — STOP before Stage 2, no resolve, no charge
      return fileResponse(load.mdBytes, { kind: 'md', download, base: load.base, title: load.title, cache: 'private, no-store' });
    }
    const r = await resolveAndParse(supabase, load, request.signal);
    if (!r.ok) return json({ error: r.error }, r.status);

    const nonce = generateNonce();
    const html = renderMagazineHtml(r.parsed, r.model, { nonce, dig: false });
    return fileResponse(html, { kind: 'html', download, base: load.base, title: load.title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce), staleMarker: r.stale });
  } catch (err) { /* ...unchanged 400/500 mapping... */ }
}
```

- [ ] **Step 4: Run the full cloud html suite — expect PASS** (all prior tests green + the 2 new).

Run: `npx jest html-route-cloud && npx tsc --noEmit`
Expected: PASS — no regression.

- [ ] **Step 5: Commit**

```bash
git add app/api/html/[id]/route.ts tests/integration/html-route-cloud.test.ts
git commit -m "refactor(cloud-pdf): serveCloud via two-stage helpers; md short-circuit preserved"
```

---

## Task 8: `GET /api/pdf/[id]` — the route

**Files:**
- Create: `app/api/pdf/[id]/route.ts`
- Test: `tests/integration/pdf-route-cloud.test.ts`

**Interfaces:**
- Consumes: `loadSummaryForServe`, `resolveAndParse` (Task 6), `renderMagazineHtml`,
  `pdfCacheKey` (Task 3), `runSingleFlight`/`withPdfSlot`/`PdfBusyError` (Task 4),
  `generateDocPdf` + `PdfRendererUnavailable` (Task 5), `getStorageBundle`.

- [ ] **Step 1: Write the failing tests** (mock `generateDocPdf`, `resolveMagazineModel`, storage).

```ts
// Key behaviors (one test each):
it('local backend → 400', ...);                                   // STORAGE_BACKEND !== supabase
it('no user → 401', ...);
it('type != summary → 400', ...);
it('committed summary → 503; absent → 404; lost blob → 409', ...);
it('cache HIT streams bytes and does NOT call generateDocPdf', async () => {
  blobGet.mockResolvedValueOnce(Buffer.from('CACHED'));         // key present
  const res = await GET(req, ctx);
  expect(res.status).toBe(200);
  expect(res.headers.get('content-disposition')).toBe('inline');
  expect(res.headers.get('content-type')).toBe('application/pdf');
  expect(generateDocPdf).not.toHaveBeenCalled();
});
it('cache MISS calls generateDocPdf exactly once, streams result', async () => {
  blobGet.mockResolvedValueOnce(null).mockResolvedValueOnce(null); // key absent both checks
  (generateDocPdf as jest.Mock).mockResolvedValueOnce(Buffer.from('NEW'));
  const res = await GET(req, ctx);
  expect(res.status).toBe(200);
  expect(generateDocPdf).toHaveBeenCalledTimes(1);
});
it('nonce-free determinism: two renders of same (parsed,model) hit the same key → 2nd is cache hit', ...);
it('typed PdfRendererUnavailable → 503 (not 500)', async () => {
  (generateDocPdf as jest.Mock).mockRejectedValueOnce(new PdfRendererUnavailable('no binary'));
  expect((await GET(req, ctx)).status).toBe(503);
});
it('PdfBusyError (saturated) → 503', ...);
it('propagates X-Magazine-Stale: 1 when resolveAndParse is stale', ...);
it('stray format/download params are ignored (still inline summary pdf)', ...);
```

- [ ] **Step 2: Run — expect FAIL.**

Run: `npx jest pdf-route-cloud`
Expected: FAIL — route not found.

- [ ] **Step 3: Implement the route.**

```ts
// app/api/pdf/[id]/route.ts
import { cookies } from 'next/headers';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
import { getStorageBundle } from '@/lib/storage/resolve';
import { loadSummaryForServe, resolveAndParse } from '@/lib/html-doc/serve-summary-core';
import { renderMagazineHtml } from '@/lib/html-doc/render';
import { pdfCacheKey } from '@/lib/pdf/pdf-render-version';
import { generateDocPdf } from '@/lib/pdf/generate-doc-pdf';
import { PdfRendererUnavailable } from '@/lib/pdf/pdf-renderer-error';
import { runSingleFlight, withPdfSlot, PdfBusyError } from '@/lib/pdf/pdf-concurrency';

type Params = { params: Promise<{ id: string }> };
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
const json = (b: unknown, s: number) => new Response(JSON.stringify(b), { status: s });

export async function GET(request: Request, { params }: Params) {
  if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase')
    return json({ error: 'use the export action' }, 400);
  const { id: videoId } = await params;
  const { searchParams } = new URL(request.url);
  if (searchParams.get('outputFolder')) return json({ error: 'outputFolder not valid' }, 400);
  if (searchParams.get('type') !== 'summary') return json({ error: 'unsupported or missing type' }, 400);
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
  // stray format/download ignored intentionally.

  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);

  try {
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);
    const r = await resolveAndParse(supabase, load, request.signal);
    if (!r.ok) return json({ error: r.error }, r.status);

    const html = renderMagazineHtml(r.parsed, r.model, { nonce: undefined, dig: false }); // nonce-free
    const key = pdfCacheKey(load.base, html);
    const { blobStore } = getStorageBundle({ supabaseClient: supabase });

    let bytes = await blobStore.get(load.principal, key);            // single get = hit detection
    if (!bytes) {
      bytes = await runSingleFlight(key, () => withPdfSlot(async () => {
        const cached = await blobStore.get(load.principal, key);     // re-check inside the slot
        if (cached) return cached;
        const buf = await generateDocPdf(html, load.principal, key, { blobStore, returnBuffer: true });
        if (!buf) throw new PdfRendererUnavailable('render produced no output (timeout)');
        return buf;
      }));
    }
    const headers: Record<string, string> = {
      'Content-Type': 'application/pdf', 'Content-Disposition': 'inline',
      'Cache-Control': 'private, no-store',
    };
    if (r.stale) headers['X-Magazine-Stale'] = '1';
    return new Response(bytes, { status: 200, headers });
  } catch (err) {
    const e = err as { statusCode?: number; message?: string };
    if (e instanceof PdfBusyError || e instanceof PdfRendererUnavailable || e.statusCode === 503)
      return json({ error: 'PDF renderer unavailable, retry' }, 503);
    if (e.statusCode === 400) return json({ error: e.message }, 400);
    return json({ error: 'internal error' }, 500);
  }
}
```

- [ ] **Step 4: Run tests + `tsc` — expect PASS.**

Run: `npx jest pdf-route-cloud && npx tsc --noEmit`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/api/pdf/[id]/route.ts tests/integration/pdf-route-cloud.test.ts
git commit -m "feat(cloud-pdf): GET /api/pdf/[id] serve+cache route (nonce-free, single-flight, 503s)"
```

---

## Task 9: `pdfHref` client URL builder

**Files:**
- Modify: `lib/client/api.ts`
- Test: `tests/lib/client/pdf-href.test.ts`

**Interfaces:**
- Produces: `pdfHref(playlistId: string, videoId: string): string`
  → `/api/pdf/${videoId}?playlist=${playlistId}&type=summary`.

- [ ] **Step 1: Write the failing test** (assert EVERY param — E2E link rule).

```ts
import { pdfHref } from '@/lib/client/api';
it('builds the exact pdf href with all params', () => {
  const href = pdfHref('11111111-1111-1111-1111-111111111111', 'vid123');
  const u = new URL(href, 'https://app.test');
  expect(u.pathname).toBe('/api/pdf/vid123');
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('summary');
});
```

- [ ] **Step 2: Run — expect FAIL.** `npx jest pdf-href` → FAIL.

- [ ] **Step 3: Implement** (mirror `summaryHref` in the same file).

```ts
export function pdfHref(playlistId: string, videoId: string): string {
  const p = new URLSearchParams({ playlist: playlistId, type: 'summary' });
  return `/api/pdf/${encodeURIComponent(videoId)}?${p.toString()}`;
}
```

- [ ] **Step 4: Run — expect PASS.** `npx jest pdf-href` → PASS.

- [ ] **Step 5: Commit**

```bash
git add lib/client/api.ts tests/lib/client/pdf-href.test.ts
git commit -m "feat(cloud-pdf): pdfHref client URL builder"
```

---

## Task 10: `VideoMenu` — cloud **View PDF** item

**Files:**
- Modify: `components/VideoMenu.tsx` (extend the `cloudMode` allowlist — round-1 L1: this is the
  existing component; do NOT create `components/cloud/VideoMenu`)
- Test: `tests/components/VideoMenu.test.tsx` (extend)

**Interfaces:**
- Consumes: `pdfHref` (Task 9), the existing `summaryReady` prop/derivation and `cloudMode` gating.

- [ ] **Step 1: Write the failing component tests.**

```tsx
it('cloud: shows View PDF with the exact href when summaryReady', () => {
  render(<VideoMenu {...cloudProps} summaryReady playlistId={PID} video={{ id: 'v' }} />);
  fireEvent.click(screen.getByRole('button', { name: /more/i }));
  const link = screen.getByRole('menuitem', { name: /view pdf/i });
  expect(link).toHaveAttribute('href', `/api/pdf/v?playlist=${PID}&type=summary`);
  expect(link).toHaveAttribute('target', '_blank');
});
it('cloud: View PDF disabled with Finalizing… when not summaryReady', () => {
  render(<VideoMenu {...cloudProps} summaryReady={false} ... />);
  fireEvent.click(screen.getByRole('button', { name: /more/i }));
  const item = screen.getByText(/view pdf/i);
  expect(item).toHaveAttribute('aria-disabled', 'true');
  expect(item).toHaveAttribute('title', expect.stringMatching(/finalizing/i));
});
it('local mode: View PDF absent (summaryReady ignored)', () => {
  render(<VideoMenu {...localProps} />);
  fireEvent.click(screen.getByRole('button', { name: /more/i }));
  expect(screen.queryByText(/view pdf/i)).toBeNull();
});
```

- [ ] **Step 2: Run — expect FAIL.** `npx jest VideoMenu` → FAIL.

- [ ] **Step 3: Implement** — add the item to the cloud allowlist, mirroring **View summary**
  (`<a target="_blank" href={pdfHref(playlistId, video.id)}>`), placed after View summary; gate on
  `summaryReady` with the disabled `title`/`aria-disabled` "Finalizing…" pattern already used by the
  2c cloud items.

- [ ] **Step 4: Run + full suite — expect PASS.** `npx jest VideoMenu && npm test` → PASS.

- [ ] **Step 5: Commit**

```bash
git add components/VideoMenu.tsx tests/components/VideoMenu.test.tsx
git commit -m "feat(cloud-pdf): cloud VideoMenu View PDF item, summaryReady-gated"
```

---

## Task 11: Integration suite (real Supabase, `signInAs`)

**Files:**
- Create: `tests/integration/pdf-cloud-e2e.test.ts` (real Supabase; mock `lib/gemini`/`lib/youtube`
  at the lib boundary per `docs/dev-process.md`; `generateDocPdf` may run real Chromium or be
  stubbed to a small buffer — prefer stub in CI, real in the Phase-4 check).

- [ ] **Step 1: Write the integration tests.**

```ts
it('round-trip: first request generates+caches the pdf blob; second serves from cache (Chromium once)', ...);
it('owner isolation: a second owner PDFing the first owner’s video → 404, no blob read', ...);
it('money: PDF of a summary whose model is already cached+fresh triggers NO reserve_serve_model', ...);
it('put-atomicity gate: concurrent overwrite+read of the cache key never yields a partial (from Preflight)', ...);
```

- [ ] **Step 2: Run — expect FAIL then implement fixtures → PASS.**

Run: `STORAGE_BACKEND=supabase npx jest pdf-cloud-e2e --runInBand`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/pdf-cloud-e2e.test.ts
git commit -m "test(cloud-pdf): integration — round-trip, owner isolation, no-extra-charge"
```

---

## Task 12: Phase-4 deploy verification (Chromium-in-cloud) — NOT code

Documented verification (dev-process Phase 4), run against the containerized web tier:

- [ ] Confirm Chromium launches in the web container with `--no-sandbox --disable-dev-shm-usage`
  (or a seccomp profile that allows the sandbox).
- [ ] Measure cold-start + per-render peak RSS; set `PDF_MAX_CONCURRENCY` from RSS vs. container
  memory limit (leave headroom for normal request traffic).
- [ ] Confirm a concurrent burst degrades to **503** (PdfBusyError), not OOM.
- [ ] Confirm the Preflight atomicity result still holds in the deploy environment.
- [ ] Record findings in `docs/reviews/spec-cloud-pdf-deploy-verification.md`.

---

## Self-Review (completed by plan author)

**Spec coverage:** every spec section maps to a task — route+flow (T8), two-stage seam (T6/T7),
nonce-free+version key (T3/T8), concurrency+single-flight+finally (T4/T8), typed 503 (T5/T8),
key validation (T2/T6), menu+href (T9/T10), atomicity gate (Preflight/T11), deploy (T12), money
invariant (T7/T11 assertions). ✔
**Placeholder scan:** every code step carries real code; test steps carry real assertions. ✔
**Type consistency:** `LoadResult`/`resolveAndParse` shapes, `pdfCacheKey`, `PdfBusyError`,
`PdfRendererUnavailable`, `runSingleFlight`/`withPdfSlot`, `generateDocPdf` return type are named
identically across producing and consuming tasks. ✔
