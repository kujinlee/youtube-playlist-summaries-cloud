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
under a per-key single-flight + a global concurrency cap. No new charging surface; no new
table/RPC/migration.

**Tech Stack:** Next.js (App Router, this repo's vendored version — read
`node_modules/next/dist/docs/` before touching routes), TypeScript, Playwright/Chromium
(`lib/pdf/generate-doc-pdf.ts`), Supabase Storage (`SupabaseBlobStore`), Jest + ts-jest (unit),
@testing-library/react (component), real-Supabase integration (`tests/integration/helpers`).

**Design spec:** `docs/superpowers/specs/2026-07-11-cloud-summary-pdf-design.md`
**ADR:** `docs/adr/0003-cloud-pdf-serve-side-not-a-job.md` · **Glossary:** `CONTEXT.md`
**Plan review round 1 (addressed in this v2):** `docs/reviews/plan-cloud-pdf-{codex,claude}.md`

## Global Constraints

- **Cloud-only.** The new `GET /api/pdf/[id]` handles `STORAGE_BACKEND==='supabase'` only; local
  backend → **400**. The existing local `POST /api/videos/[id]/pdf` export and the local menu are
  **untouched and must stay green**.
- **Session-client only** for all user-facing reads/writes; **service role never** from this route.
- **No new charging surface.** The PDF never charges itself; it rides the pre-existing on-view
  `resolveMagazineModel` materialization. At most one materialization per view, never more.
- **`merge_video_data` left unchanged.** The PDF cache is a pure blob existence check.
- **Nonce-free hash input.** Render with `renderMagazineHtml(parsed, model, { nonce: undefined,
  dig: false })`; hash that deterministic string. Never hash a nonce'd render.
- **Cache key:** `pdfs/{base}.r{PDF_RENDER_VERSION}.{sha256(htmlNonceFree).slice(0,16)}.pdf`.
- **Single-flight key is OWNER-SCOPED:** `${principal.id}/${principal.indexKey}/${cacheKey}`
  (round-1 plan review H1 — a bare cache key collapses two owners' identical-HTML renders).
- **`type` is `summary`-only** this slice; stray `format`/`download` params are ignored.
- **`generateDocPdf` timeout THROWS** `PdfRendererUnavailable` (round-1 plan review B4) — it does
  **not** "return nothing." `returnBuffer` yields the `Buffer` on success only.
- **`new Response(bytes)` must cast:** `new Response(bytes as BodyInit, …)` (round-1 plan review
  B2; the repo already does this in `lib/html-doc/file-response.ts:55`).
- **Type check + full suite before every commit:** `npx tsc --noEmit` and `npm test` must pass.

## Test harness references (copy these real patterns — do NOT invent helpers)

- **Route handler tests (mocked):** copy the mock header from `tests/api/html-serve-cloud.test.ts:1-45`
  verbatim — `jest.mock('next/headers')`, `jest.mock('@/lib/supabase/server')` (drives `mockUser`),
  `jest.mock('@/lib/storage/resolve')` (returns `{ metadataStore:{readIndex}, blobStore:{get:
  mockBlobGet}, getPrincipalFromSession }`, throwing if `getStorageBundle` is called without a
  session client), `jest.mock('@/lib/html-doc/serve-doc')` (→ `mockResolve`),
  `jest.mock('@/lib/storage/serve-playlist')` (→ `mockPlaylistKey`), and `function req(qs)`.
- **Component tests:** `tests/components/video-menu-cloud-2c.test.tsx:1-30` — `ScopeProvider`,
  `renderCloud`/`renderLocal`, readiness via `video.summaryReady`, assert `getByRole('link', {name})`.
- **Integration (real Supabase):** `tests/integration/helpers/clients.ts` — `newUser()` →
  `{ user:{id}, email, password }`, `signInAs(email, password)` → `{ client, userId }`,
  `adminClient()`, `ensureGuardrailHeadroom(svc)`; `tests/integration/helpers/seed.ts` —
  `seedPlaylist(svc, ownerId)` → `{ playlistId, playlistKey }`, `seedPromotedVideo(svc, {ownerId,
  playlistId, videoId?, base?, status?})` → `{ videoId, base }`, `seedSummaryBlob(svc, ownerId,
  playlistKey, base, md)`. **There is no `makePrincipal`** — construct `{ id: userId, indexKey:
  playlistKey }` or use `getPrincipalFromSession({ userId }, playlistKey)`.

---

## Task 1 (Preflight gate — do FIRST, blocks Task 8): Supabase Storage put-atomicity

The bare-put/no-promotion cache (ADR 0003) assumes `SupabaseBlobStore.put`
(`upload(..., { upsert: true })`) is **visibility-atomic** on new and existing objects. Verify it.

**Files:** Create `tests/integration/pdf-put-atomicity.test.ts`; create/append
`docs/reviews/spec-cloud-pdf-atomicity.md` (the `docs/reviews/` dir already exists).

- [ ] **Step 1: Write the atomicity integration test** (real helpers; modest size to avoid CI flake).

```ts
import { adminClient, newUser, signInAs } from './helpers/clients';
import { seedPlaylist } from './helpers/seed';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';

test('put(upsert) is visibility-atomic: concurrent overwrite+read never yields a partial object', async () => {
  const svc = adminClient();
  const u = await newUser();
  const { client } = await signInAs(u.email, u.password);
  const { playlistKey } = await seedPlaylist(svc, u.user.id);
  const { blobStore } = getStorageBundle({ supabaseClient: client });
  const principal = getPrincipalFromSession({ userId: u.user.id }, playlistKey);
  const key = 'pdfs/atomicity-probe.bin';
  const SIZE = 512_000;                       // 512 KB — big enough to tear, small enough for CI
  const A = Buffer.alloc(SIZE, 0xaa), B = Buffer.alloc(SIZE, 0xbb);

  await blobStore.put(principal, key, A, 'application/octet-stream');
  const reads: Promise<Buffer | null>[] = [], writes: Promise<void>[] = [];
  for (let i = 0; i < 8; i++) {
    writes.push(blobStore.put(principal, key, i % 2 ? A : B, 'application/octet-stream'));
    reads.push(blobStore.get(principal, key));
  }
  await Promise.all(writes);
  for (const buf of await Promise.all(reads)) {
    if (buf === null) continue;                       // absent is fine; never partial
    expect(buf.length).toBe(SIZE);
    expect(buf.every((byte) => byte === buf[0])).toBe(true);   // homogeneous → whole A or whole B
    expect(buf[0] === 0xaa || buf[0] === 0xbb).toBe(true);
  }
  await blobStore.delete(principal, key);
});
```

- [ ] **Step 2: Run against a real Supabase project.**

Run: `STORAGE_BACKEND=supabase npx jest pdf-put-atomicity --runInBand`
Expected: **PASS** — no torn reads. *(This is a gated integration test — it needs live Supabase
env vars; it is not part of the default unit run.)*

- [ ] **Step 3: Record the result and branch.**

- **PASS** → the bare-put cache (Task 8) proceeds as written. Note it in
  `docs/reviews/spec-cloud-pdf-atomicity.md`.
- **FAIL** → **STOP and escalate.** Fallback: staging-key + atomic manifest pointer (spec §10 /
  ADR 0003) — `putStaged` to a unique key, then flip a single-row DB pointer whose update is
  atomic; the route reads the pointer then `get`s. **Never** `promote` (copy+delete, non-atomic).
  This changes Task 8 and adds a migration — re-plan before continuing.

- [ ] **Step 4: Commit.**

```bash
git add tests/integration/pdf-put-atomicity.test.ts docs/reviews/spec-cloud-pdf-atomicity.md
git commit -m "test(cloud-pdf): verify Supabase put visibility-atomicity (bare-put cache gate)"
```

---

## Task 2: `assertCloudSummaryMdKey` — reject nested/foreign summary keys

**Files:** Create `lib/html-doc/assert-cloud-summary-md-key.ts`; Test
`tests/lib/html-doc/assert-cloud-summary-md-key.test.ts`.

**Interfaces — Produces:** `assertCloudSummaryMdKey(mdKey: string): void` — throws
`Object.assign(new Error(...), { statusCode: 409 })` on a bad key.

- [ ] **Step 1: Write the failing test**

```ts
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
describe('assertCloudSummaryMdKey', () => {
  it('accepts a single-component .md basename', () => {
    expect(() => assertCloudSummaryMdKey('0007_intro.md')).not.toThrow();
  });
  it.each([['nested','nested/foo.md'],['backslash','a\\b.md'],['parent','../foo.md'],
    ['NUL','foo\0.md'],['non-md','foo.pdf'],['no-suffix','foo'],['empty-base','.md'],['empty','']])(
    'rejects %s with statusCode 409', (_l, key) => {
    try { assertCloudSummaryMdKey(key); throw new Error('did not throw'); }
    catch (e: any) { expect(e.statusCode).toBe(409); }
  });
});
```

- [ ] **Step 2: Run — expect FAIL** (`npx jest assert-cloud-summary-md-key` → module not found).

- [ ] **Step 3: Implement**

```ts
// lib/html-doc/assert-cloud-summary-md-key.ts
/** A cloud summary md key must be a SINGLE path component ending in `.md` with a non-empty base.
 *  `assertLogicalKey` alone permits embedded slashes, so a corrupt `nested/foo.md` would build
 *  nested `models/…`/`pdfs/…` keys. Reject before any storage op. (Spec round-2 Medium.) */
export function assertCloudSummaryMdKey(mdKey: string): void {
  const bad = typeof mdKey !== 'string' || mdKey.length === 0 ||
    mdKey.includes('/') || mdKey.includes('\\') || mdKey.includes('\0') || mdKey.includes('..') ||
    !mdKey.endsWith('.md') || mdKey.slice(0, -3).length === 0;
  if (bad) throw Object.assign(new Error(`invalid cloud summary md key: ${mdKey}`), { statusCode: 409 });
}
```

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): assertCloudSummaryMdKey guard"`

---

## Task 3: `PDF_RENDER_VERSION` + `pdfCacheKey`

**Files:** Create `lib/pdf/pdf-render-version.ts`; Test `tests/lib/pdf/pdf-render-version.test.ts`.

**Interfaces — Produces:** `PDF_RENDER_VERSION: number`; `pdfCacheKey(base, htmlNonceFree): string`.

- [ ] **Step 1: Write the failing test**

```ts
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
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```ts
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
```

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): PDF_RENDER_VERSION + content-addressed pdfCacheKey"`

---

## Task 4: `pdf-concurrency` — per-key single-flight + global semaphore

**Files:** Create `lib/pdf/pdf-concurrency.ts`; Test `tests/lib/pdf/pdf-concurrency.test.ts`.

**Interfaces — Produces:** `PDF_MAX_CONCURRENCY: number`; `class PdfBusyError extends Error`
(`statusCode=503`); `runSingleFlight<T>(key, fn): Promise<T>`; `withPdfSlot<T>(fn): Promise<T>`.

- [ ] **Step 1: Write the failing tests**

```ts
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
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement**

```ts
// lib/pdf/pdf-concurrency.ts
export const PDF_MAX_CONCURRENCY = Math.max(1, parseInt(process.env.PDF_MAX_CONCURRENCY ?? '3', 10) || 3);
export class PdfBusyError extends Error { statusCode = 503; constructor() { super('PDF renderer busy'); this.name = 'PdfBusyError'; } }

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
  active++;
  try { return await fn(); } finally { active--; }
}
```

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): pdf single-flight + concurrency cap with finally cleanup"`

---

## Task 5: extend `generateDocPdf` — `returnBuffer`, typed 503 error, container args

**Files:** Modify `lib/pdf/generate-doc-pdf.ts`; Create `lib/pdf/pdf-renderer-error.ts`; **update the
EXISTING** `tests/lib/pdf/generate-doc-pdf.test.ts` (round-1 plan review H4 — it exists and asserts
the old timeout-reject; the error-type change breaks it, so it must be updated + re-run).

**Interfaces — Produces:** `class PdfRendererUnavailable extends Error` (`statusCode=503`);
`generateDocPdf(html, principal, key, opts?)` → `Promise<Buffer | void>`. **On timeout OR launch
failure it THROWS `PdfRendererUnavailable`** (never returns undefined). `returnBuffer` returns the
written `Buffer` on success. The existing local caller (`app/api/videos/[id]/pdf/route.ts`) already
`.catch`es errors, so a subclassed Error is backward-compatible.

- [ ] **Step 1: Add the failing/updated tests.** **`tests/lib/pdf/generate-doc-pdf.test.ts` already
  exists with its own `jest.mock('playwright')`** (round-2 plan review Low-1) — do NOT append a second
  `jest.mock('playwright')`; **merge** these cases into the existing mock/handles (reuse its `chromium.launch`
  mock; add per-test `mockRejectedValueOnce`/`mockImplementationOnce` overrides). The block below shows
  the mock *shape* to reconcile with the existing one:

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
const put = jest.fn(); const blobStore = { put } as any;
beforeEach(() => { put.mockReset(); });

it('returnBuffer returns the same bytes it writes', async () => {
  const buf = await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', { blobStore, returnBuffer: true });
  expect(Buffer.isBuffer(buf)).toBe(true);
  expect(put).toHaveBeenCalledWith(principal, 'pdfs/x.pdf', buf, 'application/pdf');
});
it('default (no returnBuffer) preserves void behavior', async () => {
  expect(await generateDocPdf('<html></html>', principal, 'pdfs/x.pdf', { blobStore })).toBeUndefined();
  expect(put).toHaveBeenCalledTimes(1);
});
it('launch failure throws PdfRendererUnavailable(503), not a plain Error', async () => {
  require('playwright').chromium.launch.mockRejectedValueOnce(new Error('no binary'));
  await expect(generateDocPdf('<h></h>', principal, 'pdfs/x.pdf', { blobStore })).rejects.toBeInstanceOf(PdfRendererUnavailable);
});
it('timeout throws PdfRendererUnavailable and writes nothing (M3)', async () => {
  require('playwright').chromium.launch.mockImplementationOnce(async () => ({
    newContext: async () => ({ newPage: async () => ({ setContent: () => new Promise(() => {}), emulateMedia: jest.fn(), pdf: jest.fn(), route: jest.fn(), setDefaultTimeout: jest.fn(), close: jest.fn() }), close: jest.fn() }), close: jest.fn(),
  }));
  await expect(generateDocPdf('<h></h>', principal, 'pdfs/x.pdf', { blobStore, timeoutMs: 20 })).rejects.toBeInstanceOf(PdfRendererUnavailable);
  expect(put).not.toHaveBeenCalled();
});
```
**Also update any pre-existing test in this file** that asserted a plain `Error` on timeout/launch —
change the expectation to `PdfRendererUnavailable`.

- [ ] **Step 2: Run — expect FAIL** (`npx jest generate-doc-pdf`).

- [ ] **Step 3: Create the typed error**

```ts
// lib/pdf/pdf-renderer-error.ts
export class PdfRendererUnavailable extends Error {
  statusCode = 503;
  constructor(message: string, options?: { cause?: unknown }) { super(message, options as ErrorOptions); this.name = 'PdfRendererUnavailable'; }
}
```

- [ ] **Step 4: Modify `generate-doc-pdf.ts`** — signature + buffer + typed error + container args,
  keeping the existing `timedOut`/`Promise.race`/`finally` structure. The timeout promise already
  **rejects**; wrap all thrown errors as `PdfRendererUnavailable` so timeout AND launch failure map
  to 503.

```ts
import { PdfRendererUnavailable } from './pdf-renderer-error';

export async function generateDocPdf(
  html: string, principal: Principal, key: string,
  opts: { blobStore?: BlobStore; timeoutMs?: number; returnBuffer?: boolean } = {},
): Promise<Buffer | void> {
  const blobStore = opts.blobStore ?? getStorageBundle().blobStore;
  const timeoutMs = opts.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const { chromium } = await import('playwright');
  // ...existing browser/context/page/timedOut/timer/timeout declarations unchanged...
  let rendered: Buffer | undefined;
  const launchOpts = (process.env.STORAGE_BACKEND === 'supabase')
    ? { timeout: timeoutMs, args: ['--no-sandbox', '--disable-dev-shm-usage'] } // container web tier
    : { timeout: timeoutMs };                                                    // local Mac unchanged
  try {
    try { browser = await chromium.launch(launchOpts); }
    catch (err) { throw new PdfRendererUnavailable('Failed to launch Chromium for PDF export. Run: npx playwright install chromium', { cause: err }); }
    // ...existing context/page/route setup unchanged...
    const render = (async () => {
      await page!.setContent(html, { waitUntil: 'load' });
      await page!.emulateMedia({ media: 'print' });
      const buf = await page!.pdf({ printBackground: true, format: 'A4' });
      if (timedOut) return;                                  // timeout won → never write late
      await blobStore.put(principal, key, buf, 'application/pdf');
      rendered = buf;                                        // only after a completed write
    })();
    render.catch(() => { /* swallow post-timeout rejection */ });
    await Promise.race([render, timeout]);                   // timeout promise REJECTS → throws
  } catch (err) {
    if (err instanceof PdfRendererUnavailable) throw err;
    throw new PdfRendererUnavailable(`PDF render failed: ${(err as Error).message}`, { cause: err });
  } finally {
    // ...existing timer clear + page/context/browser close unchanged...
  }
  if (opts.returnBuffer) return rendered;                    // Buffer on success (throws otherwise)
}
```

- [ ] **Step 5: Run tests + `tsc` + the local PDF suite — expect PASS.**

Run: `npx jest generate-doc-pdf && npx jest pdf && npx tsc --noEmit`
Expected: PASS; the local `POST /api/videos/[id]/pdf` tests still green (Error subclass is
backward-compatible with its `.catch(logError)`).

- [ ] **Step 6: Commit** `git commit -m "feat(cloud-pdf): generateDocPdf returnBuffer + PdfRendererUnavailable(503) + container args"`

---

## Task 6: `serve-summary-core` — two-stage helper

**Files:** Create `lib/html-doc/serve-summary-core.ts`; Test
`tests/api/serve-summary-core.test.ts` (use the mock header from `tests/api/html-serve-cloud.test.ts:1-45`).

**Interfaces — Produces:** *(If you materialize these named types explicitly rather than relying on
inferred return types, `import type { StorageBundle } from '@/lib/storage/resolve'` — it is exported
there — and `import type { Principal } from '@/lib/storage/principal'`, `Video` from `@/types`.)*
- `type LoadResult = { ok: true; mdBytes: Buffer; mdKey: string; base: string; title?: string;
  principal: Principal; playlistId: string; video: Video; bundle: StorageBundle } | { ok: false;
  status: number; error: string }`
- `loadSummaryForServe(supabase, { videoId, playlistId, userId }): Promise<LoadResult>` — owner
  playlist → readIndex → gate `summaryMd.status` → select mdKey → **`assertCloudSummaryMdKey`** →
  read md blob. **Does NOT resolve the model.** Builds the storage bundle ONCE and returns it (so
  the route/Stage-2 reuse it — round-1 plan review Low: avoid 3× `getStorageBundle`).
- `resolveAndParse(supabase, load, signal?): Promise<{ ok: true; parsed; model; stale: boolean } |
  { ok: false; status; error }>` — parse + `resolveMagazineModel`, mapping its `ResolveResult`
  (see `lib/html-doc/serve-doc.ts:26`) to HTTP codes.

**Note (round-1 plan review Medium):** `assertVideoId` is done by the CALLER route in param
validation (before auth) to preserve the existing 400-before-401 ordering; `loadSummaryForServe`
does not repeat it.

- [ ] **Step 1: Write failing tests** (copy the `html-serve-cloud.test.ts` mock header; drive
  `mockUser`, `mockIndexVideos`, `mockBlobGet`, `mockResolve`, `mockPlaylistKey`).

```ts
// mockBlobGet returns md bytes for a '.md' key; a nested key must be rejected BEFORE get is called.
it('gates committed → 503', async () => { /* mockIndexVideos = [{ id:'v', artifacts:{summaryMd:{status:'committed'}} }] */
  const r = await loadSummaryForServe(sessionClient, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r).toMatchObject({ ok: false, status: 503 });
});
it('rejects a nested mdKey with 409 BEFORE reading the blob', async () => {
  // artifacts.summaryMd = { key: 'nested/foo.md', status: 'promoted' }; mockBlobGet is a spy
  const r = await loadSummaryForServe(sessionClient, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r).toMatchObject({ ok: false, status: 409 });
  expect(mockBlobGet).not.toHaveBeenCalled();
});
it('promoted → ok WITHOUT resolving the model', async () => {
  const r = await loadSummaryForServe(sessionClient, { videoId: 'v', playlistId: PID, userId: 'u' });
  expect(r.ok).toBe(true);
  expect(require('@/lib/html-doc/serve-doc').resolveMagazineModel).not.toHaveBeenCalled();
});
it('resolveAndParse maps over_budget → 503', async () => {
  (require('@/lib/html-doc/serve-doc').resolveMagazineModel as jest.Mock).mockResolvedValueOnce({ status: 'over_budget' });
  expect(await resolveAndParse(sessionClient, okLoad)).toMatchObject({ ok: false, status: 503 });
});
```

- [ ] **Step 2: Run — expect FAIL.**

- [ ] **Step 3: Implement** (mirror `serveCloud` lines 45–107, split at the resolve boundary).

```ts
// lib/html-doc/serve-summary-core.ts
import type { SupabaseClient } from '@supabase/supabase-js';
import { getStorageBundle, getPrincipalFromSession } from '@/lib/storage/resolve';
import { resolveOwnedPlaylistKey } from '@/lib/storage/serve-playlist';
import { assertCloudSummaryMdKey } from '@/lib/html-doc/assert-cloud-summary-md-key';
import { parseSummaryMarkdown } from '@/lib/html-doc/parse';
import { resolveMagazineModel } from '@/lib/html-doc/serve-doc';
import type { Video } from '@/types';

export async function loadSummaryForServe(supabase: SupabaseClient, a: { videoId: string; playlistId: string; userId: string }) {
  const playlistKey = await resolveOwnedPlaylistKey(supabase, a.playlistId, a.userId);
  if (!playlistKey) return { ok: false as const, status: 404, error: 'not found' };
  const principal = getPrincipalFromSession({ userId: a.userId }, playlistKey);
  const bundle = getStorageBundle({ supabaseClient: supabase });
  const index = await bundle.metadataStore.readIndex(principal);
  const video = index.videos.find((v) => v.id === a.videoId) as Video | undefined;
  if (!video) return { ok: false as const, status: 404, error: 'not found' };
  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } }).artifacts?.summaryMd;
  if (artifact?.status === 'committed') return { ok: false as const, status: 503, error: 'not ready, retry' };
  if (artifact?.status !== 'promoted') return { ok: false as const, status: 404, error: 'not found' };
  const mdKey = artifact.key ?? (video as unknown as { summaryMd?: string }).summaryMd;
  if (!mdKey) return { ok: false as const, status: 404, error: 'not found' };
  try { assertCloudSummaryMdKey(mdKey); } catch { return { ok: false as const, status: 409, error: 'corrupt summary key' }; }
  const mdBytes = await bundle.blobStore.get(principal, mdKey);
  if (!mdBytes) return { ok: false as const, status: 409, error: 'repair needed' };
  const rawTitle: unknown = (video as unknown as { title?: unknown }).title;
  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;
  return { ok: true as const, mdBytes, mdKey, base: mdKey.replace(/\.md$/, ''), title, principal, playlistId: a.playlistId, video, bundle };
}

type OkLoad = Extract<Awaited<ReturnType<typeof loadSummaryForServe>>, { ok: true }>;

export async function resolveAndParse(supabase: SupabaseClient, load: OkLoad, signal?: AbortSignal) {
  const parsed = parseSummaryMarkdown(load.mdBytes.toString('utf-8'));
  parsed.sourceMd = load.mdKey;
  const language = ((load.video as unknown as { language?: string }).language === 'ko' ? 'ko' : 'en') as 'en' | 'ko';
  const resolved = await resolveMagazineModel({
    supabaseClient: supabase, blobStore: load.bundle.blobStore, principal: load.principal,
    playlistId: load.playlistId, videoId: load.video.id, base: load.base, parsed, language, signal,
  });
  // Error strings copied VERBATIM from serveCloud (app/api/html/[id]/route.ts:101-105) — the html
  // route's existing tests (html-download.test.ts:241 P6) assert the EXACT strings, and Task 7
  // requires them green before+after the refactor. Do NOT paraphrase. (Round-2 plan review High-1.)
  switch (resolved.status) {
    case 'denied': return { ok: false as const, status: 404, error: 'not found' };
    case 'busy': return { ok: false as const, status: 503, error: 'generating, retry shortly' };
    case 'attempts_exhausted': return { ok: false as const, status: 503, error: 'temporarily unavailable, try later' };
    case 'at_capacity': return { ok: false as const, status: 503, error: 'at capacity' };
    case 'over_budget': return { ok: false as const, status: 503, error: 'daily refresh budget reached, try tomorrow' };
    case 'ok': return { ok: true as const, parsed, model: resolved.model, stale: resolved.stale === true };
  }
}
```

- [ ] **Step 4: Run tests + `tsc` — expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): two-stage serve-summary-core (load; resolve+parse)"`

---

## Task 7: refactor `serveCloud` through the helpers — behavior-preserving (characterization)

**This is a REFACTOR, not RED-GREEN** (round-1 plan review B2/H3): the html route already
short-circuits `format=md` before resolve (`app/api/html/[id]/route.ts:84`) and the existing suites
already assert the behavior, so the tests are **green before and after**. A byte-identical golden is
**impossible** (per-request CSP nonce) — the existing tests pattern-match the nonce; keep them green.

**Files:** Modify `app/api/html/[id]/route.ts` (`serveCloud`); existing tests
`tests/api/html-serve-cloud.test.ts` + `tests/integration/html-download.test.ts` (already assert the
md-no-charge invariant at `html-download.test.ts:122`) must **stay green**.

- [ ] **Step 1: Baseline — run the existing suites green.**

Run: `npx jest html-serve-cloud && STORAGE_BACKEND=supabase npx jest html-download --runInBand`
Expected: PASS (this is the pre-refactor characterization baseline).

- [ ] **Step 2: Refactor `serveCloud`** to call `loadSummaryForServe`, short-circuit `md` **before**
  `resolveAndParse`, render html with a fresh CSP nonce (unchanged). Keep the pre-auth `assertVideoId`
  + param validation exactly as-is.

```ts
async function serveCloud(request, videoId, searchParams) {
  // ...unchanged: outputFolder/type/format/download/playlist validation + assertVideoId (400) BEFORE auth...
  const supabase = createServerSupabase((await cookies()) as unknown as CookieStore);
  const { data: { user } } = await supabase.auth.getUser();
  if (!user) return json({ error: 'authentication required' }, 401);
  try {
    const load = await loadSummaryForServe(supabase, { videoId, playlistId, userId: user.id });
    if (!load.ok) return json({ error: load.error }, load.status);
    if (format === 'md') // D4 money invariant — STOP before Stage 2, no resolve, no charge
      return fileResponse(load.mdBytes, { kind: 'md', download, base: load.base, title: load.title, cache: 'private, no-store' });
    const r = await resolveAndParse(supabase, load, request.signal);
    if (!r.ok) return json({ error: r.error }, r.status);
    const nonce = generateNonce();
    const html = renderMagazineHtml(r.parsed, r.model, { nonce, dig: false });
    return fileResponse(html, { kind: 'html', download, base: load.base, title: load.title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce), staleMarker: r.stale });
  } catch (err) { /* ...unchanged 400/500 mapping... */ }
}
```

- [ ] **Step 3: Re-run both suites — expect PASS (no regression).**

Run: `npx jest html-serve-cloud && STORAGE_BACKEND=supabase npx jest html-download --runInBand && npx tsc --noEmit`
Expected: PASS — identical behavior; md path still calls no `reserve_serve_model`.

- [ ] **Step 4: Commit** `git commit -m "refactor(cloud-pdf): serveCloud via two-stage helpers; md short-circuit preserved"`

---

## Task 8: `GET /api/pdf/[id]` — the route

**Files:** Create `app/api/pdf/[id]/route.ts`; Test `tests/api/pdf-serve-cloud.test.ts` (copy the
mock header from `tests/api/html-serve-cloud.test.ts:1-45`; add `STORAGE_BACKEND` set to
`'supabase'` in the test env; **mock `blobStore.get` BY KEY** — round-1 plan review B3).

**Interfaces — Consumes:** `loadSummaryForServe`/`resolveAndParse` (T6), `renderMagazineHtml`,
`pdfCacheKey` (T3), `runSingleFlight`/`withPdfSlot`/`PdfBusyError` (T4), `generateDocPdf` +
`PdfRendererUnavailable` (T5).

- [ ] **Step 1: Write failing tests.** `mockBlobGet` returns markdown for the `.md` key and the PDF
  cache bytes/null for the `pdfs/…` key:

```ts
mockBlobGet.mockImplementation(async (_p: any, key: string) =>
  key.endsWith('.md') ? Buffer.from(promotedSummaryMd) : pdfCacheBytes /* Buffer | null */);
// mock generateDocPdf + resolveMagazineModel (via the resolve mock → mockResolve = { status:'ok', model })

it('local backend → 400', ...);                                     // STORAGE_BACKEND !== supabase
it('no user → 401', ...);  it('type != summary → 400', ...);  it('bad playlist → 400', ...);
it('committed → 503; absent → 404; lost md blob → 409', ...);
it('cache HIT (pdfs key present) streams inline application/pdf, generateDocPdf NOT called', async () => {
  pdfCacheBytes = Buffer.from('CACHED');
  const res = await GET(req(`type=summary&playlist=${validPlaylist}`), ctx());
  expect(res.status).toBe(200);
  expect(res.headers.get('content-type')).toBe('application/pdf');
  expect(res.headers.get('content-disposition')).toBe('inline');
  expect(generateDocPdf).not.toHaveBeenCalled();
});
it('cache MISS calls generateDocPdf once and streams the result', async () => {
  pdfCacheBytes = null; (generateDocPdf as jest.Mock).mockResolvedValueOnce(Buffer.from('NEW'));
  expect((await GET(req(...), ctx())).status).toBe(200);
  expect(generateDocPdf).toHaveBeenCalledTimes(1);
});
it('typed PdfRendererUnavailable → 503, not 500', async () => {
  pdfCacheBytes = null; (generateDocPdf as jest.Mock).mockRejectedValueOnce(new PdfRendererUnavailable('no binary'));
  expect((await GET(req(...), ctx())).status).toBe(503);
});
it('propagates X-Magazine-Stale: 1 when resolve is stale', async () => { mockResolve = { status: 'ok', model, stale: true }; ... });
it('stray format/download params are ignored (still inline pdf)', ...);
```

- [ ] **Step 2: Run — expect FAIL** (route not found).

- [ ] **Step 3: Implement the route.**

```ts
// app/api/pdf/[id]/route.ts
import { cookies } from 'next/headers';
import { assertVideoId } from '@/lib/index-store';
import { createServerSupabase, type CookieStore } from '@/lib/supabase/server';
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
  if ((process.env.STORAGE_BACKEND ?? 'local') !== 'supabase') return json({ error: 'use the export action' }, 400);
  const { id: videoId } = await params;
  const { searchParams } = new URL(request.url);
  if (searchParams.get('outputFolder')) return json({ error: 'outputFolder not valid' }, 400);
  if (searchParams.get('type') !== 'summary') return json({ error: 'unsupported or missing type' }, 400);
  const playlistId = searchParams.get('playlist');
  if (!playlistId || !UUID_RE.test(playlistId)) return json({ error: 'invalid playlist' }, 400);
  try { assertVideoId(videoId); } catch { return json({ error: 'invalid videoId' }, 400); } // 400 BEFORE auth
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
    const flightKey = `${load.principal.id}/${load.principal.indexKey}/${key}`;             // owner-scoped (H1)

    let bytes = await load.bundle.blobStore.get(load.principal, key);      // single get = hit detection
    if (!bytes) {
      bytes = await runSingleFlight(flightKey, () => withPdfSlot(async () => {
        const cached = await load.bundle.blobStore.get(load.principal, key); // recheck inside the slot
        if (cached) return cached;
        return generateDocPdf(html, load.principal, key, { blobStore: load.bundle.blobStore, returnBuffer: true }) as Promise<Buffer>;
      }));
    }
    const headers: Record<string, string> = {
      'Content-Type': 'application/pdf', 'Content-Disposition': 'inline', 'Cache-Control': 'private, no-store',
    };
    if (r.stale) headers['X-Magazine-Stale'] = '1';
    return new Response(bytes as BodyInit, { status: 200, headers });  // cast per file-response.ts:55
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
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): GET /api/pdf/[id] serve+cache route (nonce-free, owner-scoped single-flight, 503s)"`

---

## Task 9: `pdfHref` client URL builder

**Files:** Modify `lib/client/api.ts`; Test `tests/lib/client/pdf-href.test.ts`.

**Interfaces — Produces:** `pdfHref(playlistId, videoId): string` →
`/api/pdf/${encodeURIComponent(videoId)}?playlist=…&type=summary` (mirror `summaryHref` at
`lib/client/api.ts:194`).

- [ ] **Step 1: Write failing test** (assert every param AND that the video id is encoded).

```ts
import { pdfHref } from '@/lib/client/api';
it('builds the exact pdf href with all params', () => {
  const u = new URL(pdfHref('11111111-1111-1111-1111-111111111111', 'vid 123'), 'https://a.test');
  expect(u.pathname).toBe('/api/pdf/vid%20123');   // encoded
  expect(u.searchParams.get('playlist')).toBe('11111111-1111-1111-1111-111111111111');
  expect(u.searchParams.get('type')).toBe('summary');
});
```

- [ ] **Step 2: Run — expect FAIL.**
- [ ] **Step 3: Implement**

```ts
export function pdfHref(playlistId: string, videoId: string): string {
  const p = new URLSearchParams({ playlist: playlistId, type: 'summary' });
  return `/api/pdf/${encodeURIComponent(videoId)}?${p.toString()}`;
}
```

- [ ] **Step 4: Run — expect PASS.**
- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): pdfHref client URL builder"`

---

## Task 10: `VideoMenu` — cloud **View PDF** item

**Files:** Modify `components/VideoMenu.tsx` (add to the existing `cloudMode` block, after **View
summary**); Test `tests/components/video-menu-cloud-2c.test.tsx` (extend; use the existing
`renderCloud`/`ScopeProvider`, `video.summaryReady`, `getByRole('link')`).

- [ ] **Step 1: Write failing component tests** (mirror the real harness — NO "more" button; the
  menu renders open; readiness is `video.summaryReady`).

```ts
test('cloud + summaryReady: View PDF renders with exact href, target _blank', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: true } as any} onShare={onShare} onClose={onClose} />);
  const pdf = screen.getByRole('link', { name: /view pdf/i });
  expect(pdf).toHaveAttribute('target', '_blank');
  expect(pdf).toHaveAttribute('href', `/api/pdf/${video.id}?playlist=${PID}&type=summary`);
});
test('cloud + NOT ready: View PDF is a disabled span, not a link', () => {
  renderCloud(<VideoMenu {...cloudProps} video={{ ...video, summaryReady: false } as any} onShare={onShare} onClose={onClose} />);
  expect(screen.queryByRole('link', { name: /view pdf/i })).toBeNull();
  expect(screen.getByText(/view pdf/i)).toHaveAttribute('aria-disabled', 'true');
});
test('local mode: View PDF absent', () => {
  renderLocal(<VideoMenu {...localProps} video={{ ...video, summaryReady: true } as any} onShare={onShare} onClose={onClose} />);
  expect(screen.queryByText(/view pdf/i)).toBeNull();
});
```

- [ ] **Step 2: Run — expect FAIL** (`npx jest video-menu-cloud-2c`).

- [ ] **Step 3: Implement** — in `components/VideoMenu.tsx`, import `pdfHref` and add a `<li>` right
  after the **View summary** `<li>` in the cloud block (same `ready`/disabled-`<span>` pattern as the
  existing 2c items):

```tsx
import { summaryHref, pdfHref } from '@/lib/client/api';
// ...after the "View summary ↗" <li>, inside the cloudMode fragment:
<li role="none">
  {ready ? (
    <a href={pdfHref(pid, video.id)} onClick={onClose} target="_blank" rel="noopener noreferrer" className={itemClass}>
      View PDF ↗
    </a>
  ) : (
    <span aria-disabled="true" title="Finalizing…" className={mutedItemClass}>View PDF ↗</span>
  )}
</li>
```

- [ ] **Step 4: Run component test + full suite — expect PASS.**

Run: `npx jest video-menu-cloud-2c && npm test`
Expected: PASS — existing 2c menu assertions unaffected; local menu unchanged.

- [ ] **Step 5: Commit** `git commit -m "feat(cloud-pdf): cloud VideoMenu View PDF item, summaryReady-gated"`

---

## Task 11: Integration suite (real Supabase)

**Files:** Create `tests/integration/pdf-cloud.test.ts` (real helpers; stub `generateDocPdf` to a
small buffer in CI via `jest.mock('@/lib/pdf/generate-doc-pdf')`, or run real Chromium in the
Phase-4 check; mock `lib/gemini`/`lib/youtube` at the lib boundary per `docs/dev-process.md`).

- [ ] **Step 1: Write the integration tests** (use `newUser`/`signInAs`/`seedPlaylist`/
  `seedPromotedVideo`/`seedSummaryBlob`/`ensureGuardrailHeadroom`).

```ts
// Round-trip: first request generates+caches the pdf blob (pdfs/{base}.r…pdf present after),
//   second request serves from cache with generateDocPdf invoked ONCE total.
// Owner isolation: a second user PDFing the first user's video → 404 (resolveOwnedPlaylistKey null).
// Money: with the magazine model pre-seeded/cached+fresh, the PDF request does NOT call
//   reserve_serve_model (spy on the RPC or assert spend_ledger unchanged).
```

- [ ] **Step 2: Run — implement fixtures → PASS.**

Run: `STORAGE_BACKEND=supabase npx jest pdf-cloud --runInBand`
Expected: PASS.

- [ ] **Step 3: Commit** `git commit -m "test(cloud-pdf): integration — round-trip, owner isolation, no-extra-charge"`

---

## Task 12: Phase-4 deploy verification (Chromium-in-cloud) — NOT code

- [ ] Confirm Chromium launches in the web container with `--no-sandbox --disable-dev-shm-usage`
  (or a seccomp profile that allows the sandbox).
- [ ] Measure cold-start + per-render peak RSS; set `PDF_MAX_CONCURRENCY` from RSS vs. container memory.
- [ ] Confirm a concurrent burst degrades to **503** (PdfBusyError), not OOM.
- [ ] Confirm the Preflight atomicity result holds in the deploy environment.
- [ ] Record findings in `docs/reviews/spec-cloud-pdf-deploy-verification.md`.

---

## Self-Review (v2, post round-1 plan review)

**Round-1 plan-review fixes folded in:** integration helpers corrected to real
`newUser`/`signInAs(email,password)`/`seedPlaylist`/`seedPromotedVideo`/`seedSummaryBlob` (no
`makePrincipal`) — Preflight + T11; `new Response(bytes as BodyInit)` — T8; mock `blobStore.get`
by key — T8; `generateDocPdf` timeout **throws** `PdfRendererUnavailable`, existing test updated,
M3 timeout test added — T5; Task 7 reframed as a **refactor/characterization** task (no impossible
golden; existing nonce-pattern-matching suites stay green; correct file paths); owner-scoped
single-flight key — T8; route-test mock plumbing copied from `html-serve-cloud.test.ts` — T6/T8;
VideoMenu tests use `renderCloud`/`video.summaryReady`/`getByRole('link')` — T10; `assertVideoId`
kept in route param validation (400-before-401) — T6/T8; `language` narrowed to `'en'|'ko'` — T6;
storage bundle built once and threaded — T6/T8; `pdfHref` encoded-id assertion — T9;
`PDF_RENDER_VERSION` discipline comment — T3.
**Spec coverage / placeholder / type-consistency:** all pass (see prior self-review; names
`LoadResult`/`resolveAndParse`/`pdfCacheKey`/`PdfBusyError`/`PdfRendererUnavailable`/
`runSingleFlight`/`withPdfSlot` consistent across producing + consuming tasks).
