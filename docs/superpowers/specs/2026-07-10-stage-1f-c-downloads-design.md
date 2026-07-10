# Stage 1F-c — Downloads (MD + rendered HTML), owner + share-token (cloud)

**Status:** 🟡 **design DRAFT (v1)** — brainstormed and design-approved by the user 2026-07-10; not yet through dual adversarial review. **Branch:** `feat/stage-1f-c-downloads`.

> **Design in one paragraph:** let a summary doc be **downloaded** as raw markdown (`.md`) or self-contained rendered HTML (`.html`), by the **owner** (session) or a **share-token holder** (1F-b link), by adding `format` + `download` query params to the two existing serve routes. Downloading is a thin layer over 1F-a (owner) and 1F-b (share): the MD path is a pure storage passthrough that never touches the model or money; the HTML path reuses the exact serve render + money path of each caller. No server-side PDF (print → "Save as PDF" in the browser, already shipped), no Obsidian FSA (deferred).

**Predecessors:** Stage 1F-a (authorized summary-HTML serving, PR #7) + Stage 1F-b (share tokens, PR #8, merged `bb71d32`). This slice reuses both serve paths and their money/isolation invariants unchanged; it adds only a raw-MD branch and an attachment disposition.
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 ("Download the file → app route that first verifies ownership/share, then streams"), §1F ("download MD/HTML/zip").
**Sibling slices:** 1F-a = serve; 1F-b = share; 1F-c = downloads (this doc). Closes Stage 1F.

---

## 1. Purpose

Let a summary doc's content leave the app as a file: **raw markdown** (the canonical worker-written source) or **self-contained rendered HTML** (the printable magazine doc). Available to the **owner** and to any **share-token holder** (a share link authorizes saving the file, not only viewing it). "PDF" is the browser's Save-as-PDF from that HTML (the print button already ships in 1F-a/1F-b) — there is no server-side PDF. Obsidian export is served pragmatically by "download the `.md` and drop it in a vault"; a File System Access "connect vault" flow is out of scope.

**In scope (backend):** `format` + `download` query params on `app/api/html/[id]/route.ts` (owner cloud serve) and `app/s/[token]/route.ts` (share serve); a raw-MD response branch on both; RFC 5987 filenames; extension of 1F-b's money guards to the new MD-download branch. **Out of scope:** the download buttons / menu UI (Sub-project 2), server-side PDF, Obsidian FSA, zip/bundle export, cloud dig-deeper downloads.

## 2. Background — downloading is 90% already built

- **Owner HTML serve** (`serveCloud`, `app/api/html/[id]/route.ts`): session + RLS + owner-assert → read `mdKey` blob (`:60`) → parse → `resolveMagazineModel` (materialize + charge once if stale/absent, cached) → render nonce-CSP HTML → `Cache-Control: private, no-store`.
- **Share HTML serve** (`app/s/[token]/route.ts`): token → `getShareServeContext` (confused-deputy guard) → get-only `service_role` read of `mdKey` (`:37`) → parse → `readFreshMagazineModel` (serve-if-fresh, **never charges**) → share-mode render → `no-store` + `Referrer-Policy: no-referrer`.

Both routes read the raw MD bytes **before** any model resolution. A download is therefore: (a) a `format=md` short-circuit *at that point* (return the bytes, skip the model entirely), or (b) `format=html` = the existing render, plus (c) a `Content-Disposition: attachment` header when `download=1`. Nothing about auth, money, or isolation changes.

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Extend the two existing routes with `format` + `download` query params.** No new download routes. | Maximal reuse of auth/money/isolation; a download is a disposition + an early MD branch, not a new surface. |
| D2 | **`format=html` (default) = today's inline view behavior, unchanged.** `format=md` = raw canonical markdown. `format` other than `html`/`md` → **400**. | Back-compat: every current caller omits `format` and gets the exact same response. |
| D3 | **`download=1` adds `Content-Disposition: attachment` + filename; absent = inline** (current behavior). Any other value → treated as absent (inline). | The only difference between "view" and "download" is the disposition header. |
| D4 | **MD download is a pure passthrough — it never resolves the model, never charges, never generates**, on BOTH the owner and share paths. It short-circuits right after the MD blob read. | The raw `.md` is the worker-written canonical file already in storage; rendering/charging is irrelevant to it. |
| D5 | **HTML download reuses each caller's existing money path verbatim:** owner → `resolveMagazineModel` (materialize + charge once, cached, exactly like a view); share → `readFreshMagazineModel` (serve-if-fresh, else "not ready", **never charges**). | Downloading HTML is materially identical to viewing it; the only delta is the disposition header. All 1F-a/1F-b money invariants hold. |
| D6 | **Share-token downloads authorize both formats.** The token grants "read this doc's content"; md and html are two encodings of that content. | The user accepted that a share link is a save-the-file capability; no per-format token distinction. |
| D7 | **Filename = RFC 5987**: `Content-Disposition: attachment; filename="<ascii>.<ext>"; filename*=UTF-8''<pct-encoded>`. ascii fallback = the sanitized base key (`{serial}_{slug}`); `filename*` carries the unicode doc title. Extension `.md` / `.html`. | Unicode titles (e.g. the `건강` playlist) must download with a correct name; ascii fallback for legacy clients. |
| D8 | **Downloaded HTML is byte-identical to the served HTML** for that caller (owner: full render; share: share-mode strip). The HTTP response keeps the caller's CSP + cache headers; the saved file has no CSP but is safe standalone (self-contained, inline CSS, no external requests). | One render path, no divergence; share downloads keep the owner-structure strip (no leak). |
| D9 | **Error behavior matches each caller's existing view path:** owner missing-blob → **409** "repair needed"; share missing-blob / corrupt-MD / bad-token → coarse **404**; bad `format` → **400**. | Downloads inherit, not redefine, each path's error contract. |
| D10 | **The new MD-download branch is added to 1F-b's money guards** (B18 zero-`reserve` proof + B18b import guard + B18c graph): the share MD path must reach no charging code. | The MD branch is a new anonymous code path; the never-charges guarantee must provably extend to it. |

## 4. Architecture

### 4.1 Owner route — `app/api/html/[id]/route.ts` (`serveCloud`)

Add near the top of `serveCloud`, alongside the existing `type` check:
- `const format = searchParams.get('format') ?? 'html';` — reject if not `html`/`md` → **400**.
- `const download = searchParams.get('download') === '1';`

After the existing `mdBytes` read (`:60`, and its `:61` 409-on-missing):
```ts
if (format === 'md') {
  return fileResponse(mdBytes, 'text/markdown; charset=utf-8', {
    download, base, title: video.title, ext: 'md',
    cache: 'private, no-store',
  });
}
```
(`base = mdKey.replace(/\.md$/,'')`, computed before the branch.) The `format === 'html'` path is the existing render, unchanged, except the final `Response` routes through the same helper so `download` can add the disposition (`Content-Type: text/html`, ext `html`, same `private, no-store` + CSP header).

### 4.2 Share route — `app/s/[token]/route.ts`

After the existing `mdBytes` read (`:37-45`, keep the bad-key→404 catch):
```ts
if (format === 'md') {
  return fileResponse(mdBytes, 'text/markdown; charset=utf-8', {
    download, base: ctx.mdKey.replace(/\.md$/,''), ext: 'md',  // no title: MD path stays parse-free (D4)
    cache: 'no-store', referrerPolicy: 'no-referrer',
  });
}
```
`format` + `download` are parsed from the request URL and **`format` is validated first, before the token lookup** — a bad `format` → **400** (token-independent, so it is not a token-existence oracle; matches the owner path C5). The `format === 'html'` path is the existing share render (share-mode strip), plus the disposition when `download=1`. The MD branch **imports and calls nothing new** beyond the already-present get-only read — it must not touch `read-model`/`serve-doc`/`reserve`.

Note: the share MD branch does **not** parse the MD (D4 — pure passthrough), so its `filename*` derives from the **base key** only (no unicode doc title). The owner MD branch (§4.1) already holds `video.title` from the index read, so it passes the unicode title for a friendlier `filename*`. This owner-has-title / share-base-key asymmetry is intentional (the share path must not pay a parse just to name a file).

### 4.3 Shared filename/disposition helper — `lib/html-doc/file-response.ts` (new)

```ts
export function fileResponse(
  body: Buffer | string,
  contentType: string,
  opts: { download: boolean; base: string; title?: string; ext: 'md' | 'html';
          cache: string; csp?: string; referrerPolicy?: string },
): Response
```
Builds the `Response` with `Content-Type`, `Cache-Control`, optional CSP + `Referrer-Policy`, and — when `download` — `Content-Disposition: attachment; filename="<asciiSafe(base)>.<ext>"; filename*=UTF-8''<encodeRFC5987(title ?? base)>.<ext>`. `asciiSafe` strips/replaces non-ASCII and `"`/`;`/path chars; `encodeRFC5987` percent-encodes per RFC 5987. Pure, unit-tested.

## 5. URL Contracts

| Route | Auth | Params | Response |
|---|---|---|---|
| `/api/html/[id]` | session (owner) | `playlist=<uuid>`, `type=summary`, `format=html\|md` (default html), `download=1?` | inline or `attachment`; md=text/markdown (no charge), html=rendered (1F-a money path) |
| `/s/[token]` | none (bearer) | `format=html\|md` (default html), `download=1?` | inline or `attachment`; md=text/markdown (never charge), html=share render (never charge) |

Existing callers (no `format`/`download`) get byte-identical responses to today (D2).

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| C1 | Owner view unchanged | owner GET, no `format`/`download` | identical to 1F-a today (inline HTML, materialize+charge path) |
| C2 | Owner download MD | owner GET `format=md&download=1` | **200** `text/markdown`, `attachment` filename; **no model resolution, no charge** |
| C3 | Owner view MD inline | owner GET `format=md` (no download) | 200 `text/markdown` inline; no charge |
| C4 | Owner download HTML | owner GET `format=html&download=1` | 200 `text/html`, `attachment`; 1F-a materialize+charge-once path; CSP + `private,no-store` present |
| C5 | Bad format (either path) | owner OR share GET `format=pdf` | **400** — validated before token/model work; on the share path this is token-independent (no oracle) |
| C6 | Owner MD missing blob | promoted but `summaryMd` blob lost | **409** "repair needed" (same as 1F-a view) |
| C7 | Share view unchanged | share GET, no `format`/`download` | identical to 1F-b today (share-mode HTML, never charge) |
| C8 | Share download MD | share GET `format=md&download=1`, live token | **200** `text/markdown`, `attachment`; **no charge, no generation, no reserve** |
| C9 | Share download HTML | share GET `format=html&download=1`, live token, fresh model | 200 `text/html`, `attachment`, share-mode strip; **never charges**; `no-store`+`no-referrer` |
| C10 | Share HTML not-ready | share `format=html`, model absent/stale | **503** "not ready" (1F-b path); no charge |
| C11 | Share denied (any format) | expired/revoked/unknown/malformed token, any `format`/`download` | **coarse 404**, no body leak, before blob read |
| C12 | Share MD missing/corrupt blob | live token, blob lost or unparseable | coarse **404** (MD branch: missing→404; MD is not parsed on the md path, so "corrupt" only affects html) |
| C13 | Filename RFC 5987 | any `download=1` | `Content-Disposition: attachment; filename="<ascii>.<ext>"; filename*=UTF-8''<pct>`; unicode title round-trips |
| C14 | Filename ascii fallback | title is non-ASCII (건강) | `filename="<ascii base-key>.<ext>"` present as fallback + `filename*` unicode |
| C15 | MD path never charges (both) | C2/C3/C8 | `spend_ledger`/`serve_model_charge` unchanged; zero `reserve_serve_model`; MD branch reaches no charging import (extends B18/B18b/B18c) |
| C16 | Share download isolation | share `format=md`/`html` for owner A via B's token | coarse 404 (confused-deputy guard unchanged); no cross-owner file |
| C17 | Downloaded HTML self-contained | any html download | opens offline (inline CSS, print button); no external request; share download has no owner-structure leak |
| C18 | Disposition absent = inline | `format=md` without `download` | no `Content-Disposition`; served inline |

## 7. Testing Strategy

- **Unit** — `fileResponse` / filename helper: ascii fallback, RFC 5987 `filename*` for unicode, extension, disposition present iff `download`, content-type, headers.
- **Owner route (integration/route)** — C1–C6: view-unchanged regression; MD download no-charge (spy on `reserve_serve_model`, ledger unchanged); HTML download = charge-once path; bad format 400; missing blob 409.
- **Share route (integration)** — C7–C12, C16: view-unchanged; MD download no-charge (extends the 1F-b B18 money proof to the md branch); HTML download never-charge + share-mode strip; denied-all-formats coarse 404; confused-deputy for both formats.
- **Money guards (C15)** — extend the 1F-b import-guard + B18 zero-`reserve` proof so the new MD branch is covered; assert the share MD path imports no charging module.
- **Mock boundary** — Gemini mocked at `lib/gemini.ts`; MD downloads make zero Gemini calls (asserted).

## 8. Dev-Process Re-Review Triggers

Money-adjacent + anonymous-path + reuses the 1F-b service_role surface → **iterative re-review to convergence** (spec + plan). Implementation applies §8 per-task re-review on: the share MD-download branch (C8/C15 — must provably never charge and stay within the confined get-only read) and the HTML-download money-path reuse (C4/C9). The owner-only + filename-helper tasks are simple (single-pass review).

## 9. Out of Scope / Follow-ups

- **Download UI** (buttons, format menu) — Sub-project 2.
- **Server-side PDF** — explicitly not built; print → browser Save-as-PDF (already shipped). Would reintroduce Chromium the project deliberately removed.
- **Obsidian FSA "connect vault"** — deferred; "download the `.md`" covers the need.
- **Zip / multi-doc bundle export** — deferred.
- **Cloud dig-deeper downloads** — deferred with cloud dig-deeper itself.
- Inherited 1F-a/1F-b 1G follow-ups (rate-limiting the anon route now also covers anon downloads; staleness heal; token-row GC) still stand.

## 10. Success Criteria

1. Owner downloads their summary as `.md` (no charge) or `.html` (charge-once, same as viewing); a share-link holder downloads both formats (never charging the owner).
2. No download path weakens 1F-a/1F-b: MD downloads never touch the model/money on either path; share HTML download reuses the never-charge guard; the new MD branch is covered by the extended B18/B18b/B18c guards.
3. Existing `/api/html/[id]` and `/s/[token]` callers (no `format`/`download`) get byte-identical responses.
4. Filenames are correct for unicode titles (RFC 5987) with an ascii fallback; downloaded HTML is self-contained and (for shares) leaks no owner structure.
5. `tsc` clean; unit + integration suites green; spec cleared dual adversarial review to convergence.
