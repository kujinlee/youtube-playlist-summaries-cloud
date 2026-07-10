# Stage 1F-c — Downloads Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a summary doc be downloaded as raw markdown (`.md`) or self-contained rendered HTML (`.html`), by the owner (session) or a share-token holder (1F-b link), by adding `format` + `download` query params to the two existing serve routes.

**Architecture:** A pure-leaf `file-response.ts` helper builds every download/serve `Response` (content-type by kind, RFC 5987 filename, `nosniff`). The MD path is an early short-circuit after the blob read — before any model resolution — so it never charges. The HTML path reuses each caller's existing money path (owner materialize+charge, share never-charge). No new routes, no new auth/isolation surface.

**Tech Stack:** Next.js route handlers, Supabase (session + service_role), TypeScript strict, jest + ts-jest (unit), real-DB integration (`--runInBand`), the existing 1F-b jest import-guard.

**Spec:** `docs/superpowers/specs/2026-07-10-stage-1f-c-downloads-design.md` (v4 CONVERGED). Behaviors C1–C21 (spec §6) are the test contract.

## Global Constraints

- **MD never charges (D4):** the `format=md` branch short-circuits *after the MD blob read, before any model resolution* on BOTH routes. No `resolveMagazineModel`, `readFreshMagazineModel`, `reserve_serve_model`, or generation on the md path.
- **HTML reuses each caller's money path verbatim (D5):** owner → `resolveMagazineModel` (materialize + charge once, cached); share → `readFreshMagazineModel` (serve-if-fresh, never charges). The only delta from a view is the disposition header.
- **`nosniff` on EVERY response (D11):** `X-Content-Type-Options: nosniff` on md + html, inline + download, both routes. **Inline `format=md` (no download) → `text/plain; charset=utf-8`**; `.md` download → `text/markdown`; html → `text/html`.
- **Filename (D7):** `Content-Disposition: attachment; filename="<asciiSafe(base)>.<ext>"; filename*=UTF-8''<encodeRFC5987(title?.trim()||base)>.<ext>`. The ASCII `filename=` half **always uses the base key** (never the unicode title — a non-Latin-1 `filename=` throws in undici). `asciiSafe` collapses `[\x00-\x1f\x7f]`, `[^\x20-\x7e]`, `" \ / ;` → `_`, trims dots/spaces, empty→`summary`. `encodeRFC5987` = strict allowlist (`A-Za-z0-9` + RFC 5987 attr-char punctuation; `-` at the regex-class edge so `+-.` is not a range).
- **Share MD re-check (D12):** the share `format=md` branch runs the SAME mandatory pre-response `getShareServeContext` re-check (revoked/un-promoted → coarse 404) that the HTML path runs at `s/route.ts:57-59`, before returning bytes.
- **Format validated first (M2/B-L2):** bad `format` (not `html`/`md`) → **400**; on the share route validated *before* the `TOKEN_RE` shape check + token lookup (token-independent, no oracle). Owner validates `format` *after* the existing `type` check (L3).
- **Money guards (D10):** `lib/html-doc/file-response.ts` is a **pure dependency-free leaf** (imports nothing from `@/`); it is added to the 1F-b import-guard `shareSources` scan set AND asserted to have no `@/` import; the B18 zero-`reserve` money proof is extended to the `format=md` share branch.
- **Back-compat (D2):** existing no-`format`/no-`download` callers get an *equivalent* response — same status, same header name/value set **plus new `nosniff`**, same body modulo the per-response nonce, no `Content-Disposition`; the owner path gains **no** `Referrer-Policy`.
- **Next.js:** read the route-handler guide under `node_modules/next/dist/docs/` before editing handlers (per AGENTS.md).
- **`gh` two-remotes footgun:** any `gh` command MUST pass `--repo kujinlee/youtube-playlist-summaries-cloud`.
- **§8 re-review triggers:** Task 3 (owner HTML money-path reuse, C4) and Task 4 (share MD branch + money proof + isolation, C8/C15/C16) get per-task iterative dual review. Tasks 1–2 (filename helper, title field) are single-pass.

---

## File Structure

**Create:**
- `lib/html-doc/file-response.ts` — pure leaf: `fileResponse(body, opts)` + `asciiSafe` + `encodeRFC5987`. Imports nothing from `@/`.
- `tests/lib/html-doc/file-response.test.ts`

**Modify:**
- `lib/share/serve.ts` — `ShareServeContext` gains `title?: string`; `getShareServeContext` reads `vid.data.title`.
- `app/api/html/[id]/route.ts` (`serveCloud`) — `format`/`download` params; `format=md` branch; html final `Response` via `fileResponse`.
- `app/s/[token]/route.ts` — `format`/`download` params (format first); `format=md` branch WITH the re-check; html final `Response` via `fileResponse`.
- `tests/lib/share/import-guard.test.ts` — add `file-response.ts` to `shareSources` + a leaf assertion.
- `tests/lib/share/serve.test.ts` (or the integration `share-serve.test.ts`) — assert `title` returned.
- `tests/integration/share-route.test.ts` — extend the B18 money proof to `format=md`; add C8/C11b/C19–C21.

---

## Task 1: `file-response.ts` pure-leaf helper (+ import-guard extension)

**Files:**
- Create: `lib/html-doc/file-response.ts`, `tests/lib/html-doc/file-response.test.ts`
- Modify: `tests/lib/share/import-guard.test.ts`

**Interfaces:**
- Produces: `export function fileResponse(body: Buffer | string, opts: { kind: 'md' | 'html'; download: boolean; base: string; title?: string; cache: string; csp?: string; referrerPolicy?: string }): Response`

- [ ] **Step 1: Write the failing unit test** (`tests/lib/html-doc/file-response.test.ts`)

```ts
import { fileResponse } from '@/lib/html-doc/file-response';

const get = (r: Response, h: string) => r.headers.get(h);

describe('fileResponse', () => {
  it('inline md is text/plain (non-executable) with nosniff, no disposition', () => {
    const r = fileResponse('# hi', { kind: 'md', download: false, base: '00042_intro', cache: 'no-store' });
    expect(get(r, 'Content-Type')).toBe('text/plain; charset=utf-8');
    expect(get(r, 'X-Content-Type-Options')).toBe('nosniff');
    expect(get(r, 'Content-Disposition')).toBeNull();
  });
  it('download md is text/markdown, attachment, ascii base-key filename + unicode filename*', () => {
    const r = fileResponse('# hi', { kind: 'md', download: true, base: '00042_intro', title: 'Intro to AI', cache: 'no-store' });
    expect(get(r, 'Content-Type')).toBe('text/markdown; charset=utf-8');
    expect(get(r, 'Content-Disposition')).toBe(`attachment; filename="00042_intro.md"; filename*=UTF-8''Intro%20to%20AI.md`);
  });
  it('unicode title → ascii filename= is the base key, unicode rides in filename*', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '00042_geon', title: '건강한 식습관', cache: 'no-store' });
    const cd = get(r, 'Content-Disposition')!;
    expect(cd).toContain('filename="00042_geon.md"');        // ascii half = base key
    expect(cd).toContain("filename*=UTF-8''");
    expect(cd).toMatch(/%ea%b1%b4/i);                        // 건 encoded, never literal in filename=
    expect(cd).not.toContain('건강');                         // never a non-Latin-1 filename= value
  });
  it('CR/LF/quote/semicolon in title cannot inject the header', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '00001_v', title: 'a"\r\nb;c', cache: 'no-store' });
    const cd = get(r, 'Content-Disposition')!;
    expect(cd).not.toMatch(/[\r\n]/);
    expect(cd).toContain('filename="00001_v.md"');
    expect(cd).toContain('%0D%0A');                          // CR/LF percent-encoded in filename*
  });
  it('empty/all-non-ascii base → filename= falls back to summary', () => {
    const r = fileResponse('x', { kind: 'md', download: true, base: '   ', title: '', cache: 'no-store' });
    expect(get(r, 'Content-Disposition')).toContain('filename="summary.md"');
  });
  it('html carries csp + referrerPolicy when given; nosniff always', () => {
    const r = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'no-store', csp: "default-src 'none'", referrerPolicy: 'no-referrer' });
    expect(get(r, 'Content-Type')).toBe('text/html; charset=utf-8');
    expect(get(r, 'Content-Security-Policy')).toBe("default-src 'none'");
    expect(get(r, 'Referrer-Policy')).toBe('no-referrer');
    expect(get(r, 'X-Content-Type-Options')).toBe('nosniff');
  });
  it('owner-style html (no referrerPolicy) emits no Referrer-Policy', () => {
    const r = fileResponse('<html>', { kind: 'html', download: false, base: 'b', cache: 'private, no-store', csp: 'x' });
    expect(get(r, 'Referrer-Policy')).toBeNull();
  });
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npx jest file-response` — Expected FAIL (module missing).

- [ ] **Step 3: Implement `lib/html-doc/file-response.ts`**

```ts
// PURE LEAF (spec D10): imports NOTHING from '@/' so the 1F-b import guard can scan it and the
// share route's use of it cannot smuggle in charging code. Do not add app imports here.

function asciiSafe(base: string): string {
  const cleaned = base
    .replace(/[^\x20-\x7e]/g, '_') // non-printable-ASCII (incl. all >=0x80 and control 0x00-0x1f,0x7f) → _
    .replace(/["\\/;]/g, '_')       // quote, backslash, slash, semicolon → _
    .replace(/^[.\s]+|[.\s]+$/g, ''); // trim leading/trailing dots and spaces
  return cleaned || 'summary';
}

function encodeRFC5987(s: string): string {
  // Strict allowlist: A-Za-z0-9 + RFC 5987 attr-char punctuation. `-` is at the class EDGE so the
  // literal `+.` chars are NOT parsed as a range (which would admit `,`). Everything else → %HH of
  // its UTF-8 bytes (so CR/LF/;/" and all multibyte chars are percent-encoded, never literal).
  const out: string[] = [];
  for (const byte of Buffer.from(s, 'utf-8')) {
    const ch = String.fromCharCode(byte);
    if (/[A-Za-z0-9!#$&+.^_`|~-]/.test(ch)) out.push(ch);
    else out.push('%' + byte.toString(16).toUpperCase().padStart(2, '0'));
  }
  return out.join('');
}

export function fileResponse(
  body: Buffer | string,
  opts: {
    kind: 'md' | 'html'; download: boolean; base: string; title?: string;
    cache: string; csp?: string; referrerPolicy?: string;
  },
): Response {
  const contentType =
    opts.kind === 'html' ? 'text/html; charset=utf-8'
    : opts.download ? 'text/markdown; charset=utf-8'
    : 'text/plain; charset=utf-8';

  const headers: Record<string, string> = {
    'Content-Type': contentType,
    'X-Content-Type-Options': 'nosniff',
    'Cache-Control': opts.cache,
  };
  if (opts.csp) headers['Content-Security-Policy'] = opts.csp;
  if (opts.referrerPolicy) headers['Referrer-Policy'] = opts.referrerPolicy;

  if (opts.download) {
    const ext = opts.kind; // 'md' | 'html'
    const ascii = `${asciiSafe(opts.base)}.${ext}`;
    const uni = `${encodeRFC5987(opts.title?.trim() || opts.base)}.${ext}`;
    headers['Content-Disposition'] = `attachment; filename="${ascii}"; filename*=UTF-8''${uni}`;
  }
  return new Response(body, { status: 200, headers });
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npx jest file-response && npx tsc --noEmit` — Expected PASS + clean.

- [ ] **Step 5: Extend the import guard to scan `file-response.ts` + assert it is a leaf**

In `tests/lib/share/import-guard.test.ts`, add `file-response.ts` to `shareSources`:

```ts
const shareSources = [
  ...walk(join(root, 'app/s')),
  ...walk(join(root, 'lib/share')),
  join(root, 'lib/html-doc/read-model.ts'),
  join(root, 'lib/html-doc/file-response.ts'),   // 1F-c: share md/html downloads route through this
].filter((f) => existsSync(f));
```

And add a leaf assertion (the guard is a flat grep, so scanning the file only catches direct imports — the real protection is that it imports nothing from `@/`). The regex must catch **every** `@/` import form — the `from`-clause form, a bare side-effect `import '@/…'` (which has NO `from`), a dynamic `import('@/…')`, and `require('@/…')` — so match the `'@/` / `"@/` literal directly rather than anchoring on `from`:

```ts
it('file-response.ts is a dependency-free leaf (no @/ imports, any form)', () => {
  const src = readFileSync(join(root, 'lib/html-doc/file-response.ts'), 'utf-8');
  // Any @/ import: `from '@/…'`, bare `import '@/…'`, dynamic `import('@/…')`, `require('@/…')`.
  // The file legitimately imports nothing from '@/', so a bare literal match is both sufficient
  // and precise (it does not appear in any string/comment in this leaf).
  expect(src).not.toMatch(/['"]@\//);
});
```

- [ ] **Step 6: Run to verify the guard passes + planted negative controls**

Run: `npx jest import-guard` — Expected PASS (file-response.ts has no forbidden imports and no `@/` import in any form).

Sanity — plant each `@/` import form in turn in `file-response.ts`, confirm `npx jest import-guard` FAILS, then revert, for **all three**:
1. bare side-effect: `import '@/lib/gemini';` (has no `from` — this is the form the old `from`-anchored regex missed; it must now fail the leaf assertion).
2. dynamic: `void import('@/lib/gemini');`
3. require: `require('@/lib/gemini');`

Each must trip the leaf assertion (the bare/dynamic/require forms may slip past the forbidden-import scan, which is exactly why the literal-match leaf assertion is the load-bearing check).

- [ ] **Step 7: Commit**

```bash
git add lib/html-doc/file-response.ts tests/lib/html-doc/file-response.test.ts tests/lib/share/import-guard.test.ts
git commit -m "feat(1f-c): file-response.ts pure-leaf helper (RFC 5987 filename + nosniff) + guard extension"
```

---

## Task 2: `getShareServeContext` returns `title?`

**Files:**
- Modify: `lib/share/serve.ts` (`ShareServeContext` + the return)
- Test: `tests/integration/share-serve.test.ts` (the existing `getShareServeContext` suite)

**Interfaces:**
- Consumes: nothing new.
- Produces: `ShareServeContext` gains `title?: string`.

- [ ] **Step 1: Write the failing test** (append to `tests/integration/share-serve.test.ts`)

```ts
it('returns the doc title from the video row (for download filenames)', async () => {
  const u = await newUser();
  const { playlistId, playlistKey } = await seedPlaylist(svc, u.user.id);
  // seedPromotedVideo writes data.title? — set it explicitly so the assertion is meaningful:
  const videoId = 'v-titletest';
  await svc.from('videos').insert({
    playlist_id: playlistId, owner_id: u.user.id, video_id: videoId, position: 5,
    data: { id: videoId, title: 'My Doc Title', language: 'en', summaryMd: 'v-titletest.md',
            docVersion: 1, artifacts: { summaryMd: { key: 'v-titletest.md', status: 'promoted' } } },
  });
  const { token, tokenHash } = generateShareToken();
  await svc.from('share_tokens').insert({ token_hash: tokenHash, owner_id: u.user.id,
    playlist_id: playlistId, video_id: videoId, expires_at: new Date(Date.now() + 864e5).toISOString() });
  const ctx = await getShareServeContext(svc, token);
  expect(ctx).toMatchObject({ ownerId: u.user.id, playlistKey, mdKey: 'v-titletest.md', title: 'My Doc Title' });
});
```

(Adjust imports at the top of the file to include `seedPlaylist`, `generateShareToken` if not already present — they are used elsewhere in the suite.)

- [ ] **Step 2: Run to verify it fails**

Run: `npm run test:integration -- --runInBand -t "returns the doc title"` — Expected FAIL (`title` undefined).

- [ ] **Step 3: Implement in `lib/share/serve.ts`**

Add `title?: string` to the type:

```ts
export type ShareServeContext = {
  ownerId: string; playlistKey: string; playlistId: string; videoId: string; mdKey: string;
  title?: string;
};
```

In `getShareServeContext`, after `mdKey` is derived and before the return, read the title defensively (the row is already fetched — no extra query, no parse):

```ts
  const rawTitle = (vid.data as { title?: unknown }).title;
  const title = typeof rawTitle === 'string' && rawTitle.trim() ? rawTitle : undefined;

  return { ownerId: tok.owner_id, playlistKey: pl.playlist_key, playlistId: tok.playlist_id,
           videoId: tok.video_id, mdKey, title };
```

- [ ] **Step 4: Run to verify it passes + no regression**

Run: `npm run test:integration -- --runInBand -t getShareServeContext && npx tsc --noEmit` — Expected PASS (all existing getShareServeContext tests still green; new one passes).

- [ ] **Step 5: Commit**

```bash
git add lib/share/serve.ts tests/integration/share-serve.test.ts
git commit -m "feat(1f-c): getShareServeContext returns doc title for download filenames"
```

---

## Task 3: Owner route — `format`/`download` + MD branch + HTML via `fileResponse`

**§8 re-review trigger — owner HTML money-path reuse (C4).**

**Files:**
- Modify: `app/api/html/[id]/route.ts` (`serveCloud`)
- Test: `tests/integration/` owner route test (create `tests/integration/html-download.test.ts` or extend the existing owner-serve test; mirror its harness)

**Interfaces:**
- Consumes: `fileResponse` (Task 1).

**Test-infra prerequisite (H1 — seed writes a title):** `tests/integration/helpers/seed.ts` `seedPromotedVideo` currently writes a `data` blob with **no `title`**, so any title-derived-filename assertion (C2 owner, C8 share) would silently fall back to the base key and prove nothing. Before writing these tests, extend `seedPromotedVideo` with an **optional** `title?: string` param that, when provided, writes `data.title` (keep the param optional so the ~dozen existing callers compile untouched under `tsc`). Give the download tests a real title (e.g. `'My Doc Title'`). A hostile-title case (C21, quote/CRLF) still needs a custom `svc.from('videos').insert` — the helper is for the happy-path title, not header-injection fixtures.

- [ ] **Step 1: Write the failing tests** (`tests/integration/html-download.test.ts`)

Against a real DB + seeded promoted doc + MD blob (use `seedPlaylist`/`seedPromotedVideo` **with the new `title` arg**/`seedSummaryBlob`; authenticate as the owner with `signInAs`). Cover:

```
- C1  owner GET (no format/download) → 200 text/html, CSP + private,no-store, NOW nosniff, NO Referrer-Policy, no Content-Disposition (view regression).
- C2  owner GET format=md&download=1 → 200 text/markdown, attachment filename="<base>.md"; spy reserve_serve_model NOT called; spend_ledger unchanged.
- C3  owner GET format=md (no download) → 200 text/plain; charset=utf-8, nosniff, no Content-Disposition; no charge.
- C4  owner GET format=html&download=1 → 200 text/html, attachment; goes through the resolveMagazineModel path (charge-once semantics preserved).
- C5  owner GET format=pdf → 400 (validated after type; ?type=bad&format=pdf → the type-400 first).
- C6  owner GET format=md when the MD blob is missing behind promoted → 409 "repair needed".
```

Write concrete assertions in the repo's integration-route harness style (invoke the route's `GET` with a `Request` carrying the query string; `signInAs` gives the owner session). For C2/C3 the money check: `jest.spyOn(SupabaseClient.prototype, 'rpc')` and assert no `'reserve_serve_model'` call + `spend_ledger` unchanged.

- [ ] **Step 2: Run to verify they fail**

Run: `npm run test:integration -- --runInBand -t "html-download"` — Expected FAIL (params ignored).

- [ ] **Step 3: Implement in `serveCloud`**

After the `type` check (`:29-30`), add:

```ts
  const format = searchParams.get('format') ?? 'html';
  if (format !== 'html' && format !== 'md') return json({ error: 'invalid format' }, 400);
  const download = searchParams.get('download') === '1';
```

Compute `base` **before** the model branch (move it up), and insert the MD short-circuit right after the `mdBytes` 409 check (`:60-61`). **Move the existing `// IDENTITY COHERENCE …` comment that sits above the old `base` declaration up with it** (do not leave it orphaned at the old site) so the derivation stays documented at its new location:

```ts
    // IDENTITY COHERENCE: base (filename stem) is the MD key sans .md — the same key the
    // model/blob are addressed by, so download filename and served doc cannot diverge.
    const base = mdKey.replace(/\.md$/, '');
    if (format === 'md') {
      return fileResponse(mdBytes, {
        kind: 'md', download, base, title: video.title,
        cache: 'private, no-store',   // helper adds nosniff; inline md → text/plain, download md → text/markdown
      });
    }
```

Replace the final html `Response` (`:88-96`) with the helper (keeps CSP + cache, adds nosniff, no Referrer-Policy):

```ts
    const nonce = generateNonce();
    const html = renderMagazineHtml(parsed, resolved.model, { nonce, dig: false });
    return fileResponse(html, {
      kind: 'html', download, base, title: video.title,
      cache: 'private, no-store', csp: buildSummaryCsp(nonce),
    });
```

Import `fileResponse` at the top: `import { fileResponse } from '@/lib/html-doc/file-response';`. Add the `import { fileResponse }` line; keep all existing imports. (`base` is now declared once, before both the md branch and the resolve call — delete the later duplicate `const base = …` at the old `:73`.)

- [ ] **Step 4: Run to verify pass + tsc + full owner-serve regression**

Run: `npm run test:integration -- --runInBand -t "html-download" && npx tsc --noEmit && npx jest html`
Expected: PASS; existing owner-serve tests still green (C1 regression: same status + headers + body modulo nonce, plus new nosniff).

- [ ] **Step 5: Commit**

```bash
git add "app/api/html/[id]/route.ts" tests/integration/html-download.test.ts
git commit -m "feat(1f-c): owner route format/download params + MD passthrough branch"
```

---

## Task 4: Share route — `format`/`download` + MD branch (with re-check) + money proof

**§8 re-review trigger — share MD branch (C8/C15) + isolation (C16) + money proof.**

**Files:**
- Modify: `app/s/[token]/route.ts`
- Test: extend `tests/integration/share-route.test.ts`

**Interfaces:**
- Consumes: `fileResponse` (Task 1), `getShareServeContext` w/ `title` (Task 2).

- [ ] **Step 1: Write the failing tests** (extend `tests/integration/share-route.test.ts`)

Cover, inside the existing B18 money-proof block (so the ledger snapshot + `reserve_serve_model` spy assert across these too):

```
- C7  share GET (no format/download), live token → 200 text/html share render, no-store+no-referrer, NOW nosniff, no Content-Disposition (view regression).
- C8  share GET format=md&download=1, live token → 200 text/markdown, attachment filename="<base>.md"+filename*=<title>; NEVER charges, no reserve, no generation.
- C8b share GET format=md (no download) → 200 text/plain; charset=utf-8, nosniff.
- C9  share GET format=html&download=1, live token, fresh model → 200 text/html, attachment, share-mode strip (no MD key in body), never charges.
- C5s share GET format=pdf (valid token) → 400; and /s/<malformed>?format=pdf → 400 (format before TOKEN_RE).
- C11 share GET format=md, expired/revoked/unknown token → coarse 404 before blob read.
- C11b revoke/un-promote BETWEEN the initial resolve and the response on the md path → 404 (the D12 re-check). Use the existing jest.mock('@/lib/share/serve') 2nd-call-hook pattern: on the md branch's re-check call, revoke the token, expect 404.
- C12 share GET format=md when the MD blob is missing behind a promoted artifact → 404 (the md branch does not leak a 5xx/empty body on a missing blob; the bad-key catch at `:37-45` yields the coarse 404 for the md path too).
- C16 cross-owner isolation for BOTH formats: owner B mints a token for B's doc; requesting A's doc key via that token → 404 for `format=md` AND for `format=html`. Proves the md short-circuit inherits the unchanged confused-deputy guard + D12 re-check (it must NOT open an isolation hole the html path lacks).
- C19 every response (md/html, inline/download) has X-Content-Type-Options: nosniff.
- C21 filename edge: a video whose title contains a quote/CRLF → header not injected (filename= is the base key; filename* percent-encoded).
```

For B18: assert across C7/C8/C8b/C9/C11 that `SupabaseClient.prototype.rpc` was never called with `'reserve_serve_model'` and `spend_ledger`/`serve_model_charge` are byte-unchanged, and the `generateMagazineModel` mock has zero calls.

- [ ] **Step 2: Run to verify they fail**

Run: `npm run test:integration -- --runInBand -t "share-route"` — Expected FAIL.

- [ ] **Step 3: Implement in `app/s/[token]/route.ts`**

At the top of `GET`, parse + validate `format` **before** `TOKEN_RE` (D12/B-L2), and `download`:

```ts
  const { searchParams } = new URL(_req.url);
  const format = searchParams.get('format') ?? 'html';
  if (format !== 'html' && format !== 'md') return notFound400();  // bad format → 400, token-independent
  const download = searchParams.get('download') === '1';
```

(Add a small `const notFound400 = () => new Response(JSON.stringify({ error: 'invalid format' }), { status: 400, headers: DENIAL_HEADERS });` next to the existing `notFound`/`notReady`. **Keep the `_req` param name** — a `_`-prefixed param that is now read (`_req.url`) still compiles cleanly; do not rename it, to keep the diff minimal.)

Insert the MD branch after the `mdBytes` read + bad-key catch (`:37-45`), BEFORE the parse/model — and it MUST run the re-check first (D12):

```ts
  if (format === 'md') {
    const recheck = await getShareServeContext(svc, token);   // D12/B10b — revoked/un-promoted mid-request → 404
    if ('status' in recheck) return notFound();
    return fileResponse(mdBytes, {
      kind: 'md', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
      cache: 'no-store', referrerPolicy: 'no-referrer',   // helper adds nosniff; inline md → text/plain
    });
  }
```

Replace the final html `Response` (`:62-71`) with the helper (keeps CSP + no-store + no-referrer, adds nosniff, keeps share-mode strip via the existing `renderMagazineHtml(..., { nonce, dig: false, share: true })`):

```ts
  const nonce = generateNonce();
  const html = renderMagazineHtml(parsed, model.model, { nonce, dig: false, share: true });
  return fileResponse(html, {
    kind: 'html', download, base: ctx.mdKey.replace(/\.md$/, ''), title: ctx.title,
    cache: 'no-store', csp: buildSummaryCsp(nonce), referrerPolicy: 'no-referrer',
  });
```

Import `fileResponse`: `import { fileResponse } from '@/lib/html-doc/file-response';` (this is why file-response.ts must be a pure leaf — the share route imports it; the guard scans it). Do NOT add any other import.

- [ ] **Step 4: Run to verify pass + tsc + import-guard + full share suite**

Run: `npm run test:integration -- --runInBand -t "share-route" && npx jest import-guard && npx tsc --noEmit`
Expected: PASS; the import guard still green (file-response.ts is a leaf, share route imports only it); B18 money proof green across the new md cases.

- [ ] **Step 5: Commit**

```bash
git add "app/s/[token]/route.ts" tests/integration/share-route.test.ts
git commit -m "feat(1f-c): share route format/download + MD branch with re-check + money proof"
```

---

## Verification (end of stage)

1. `npx tsc --noEmit` — 0 errors.
2. `npx jest` — full unit suite green (grows with Task 1 unit tests).
3. `npx supabase db reset && npm run test:integration -- --runInBand` — all green (Tasks 2, 3, 4 integration).
4. `npx jest import-guard` — passes; demonstrably FAILS on a deliberately-bad import in `file-response.ts` (Task 1 Step 6 sanity check).
5. Behaviors C1–C21 each have a covering test.
6. Each of Tasks 3, 4 cleared per-task dual adversarial review (Claude + Codex) with §8 iterative re-review; reviews saved to `docs/reviews/task-1f-c-N-<name>-{review,codex}.md`.
7. Stage-complete: `superpowers:finishing-a-development-branch` → whole-branch holistic review → PR to `master` (`gh … --repo kujinlee/youtube-playlist-summaries-cloud`).

## Self-Review notes (author)

- **Spec coverage:** D1/D2/D3 (T3+T4 params), D4 MD-no-charge (T3 C2/C3 + T4 C8/C8b money proof), D5 HTML money reuse (T3 C4 + T4 C9), D6 both formats (T4), D7 filename (T1), D8 downloaded-HTML (T3/T4 html), D9 errors (T3 C6 409 / T4 C11 404 / C5 400), D10 guards (T1 import-guard + T4 B18), D11 nosniff+text/plain (T1 + C19/C20), D12 re-check (T4 C11b). Behaviors C1–C21 → T1 (C13/C14/C19/C20/C21 helper-level) + T3 (C1–C6) + T4 (C7–C12,C11b,C16,C19,C21).
- **Degraded-but-safe note (round-3 Low):** if a `slug` were ever non-ASCII, `asciiSafe` collapses it to `_`s in the `filename=` half — safe and intended (the real name rides in `filename*`); not a bug. Base keys are `{padSerial}_{slug}` (ASCII today).
- **Confirm during execution:** the exact owner-route integration harness (Task 3) and whether `video.title` is populated in the owner index (`Video.title` is required in schema, so it should be); the `share-route.test.ts` seed for a title (Task 4 C21 needs a video with a hostile title).
