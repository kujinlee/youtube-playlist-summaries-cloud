# Stage 1F-c — Downloads (MD + rendered HTML), owner + share-token (cloud)

**Status:** 🟡 **design DRAFT (v3)** — design-approved 2026-07-10. v1 dual review: 1 Blocking + 2 High + 2 Med + 3 Low → v2. v2 re-review (round 2): 0 new Blocking, 2 new High (both reconciliation defects — the v2 `text/plain` + ASCII-filename fixes didn't propagate to C3/§5/§4.3) + 1 Med + 3 Low → this v3. **Next: re-review round 3 to convergence → user spec-approval → `writing-plans`.** **Branch:** `feat/stage-1f-c-downloads`.
**Review trail:** `docs/reviews/spec-1f-c-{codex,claude}-v1.md`, `-v2-rereview.md`.

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
| D7 | **Filename = RFC 5987**: `Content-Disposition: attachment; filename="<ascii>.<ext>"; filename*=UTF-8''<pct-encoded>`. ascii fallback = the sanitized base key (`{serial}_{slug}`); `filename*` carries the unicode doc title. Extension `.md` / `.html`. **Both paths use the title** — the owner route has `video.title` from the index; the share route gets it for free from the `videos.data` row `getShareServeContext` already reads (add `title` to `ShareServeContext`). No MD parse needed on either MD path. | Unicode titles (e.g. the `건강` playlist) download with a correct human name on owner AND share; ascii base-key fallback for legacy clients. |
| D8 | **Downloaded HTML uses the same render as the served HTML** for that caller (owner: full render; share: share-mode strip) — same body modulo the per-response nonce. The HTTP response keeps the caller's CSP + cache headers (+ `nosniff`); the saved file has no CSP but is safe standalone: self-contained, inline CSS, no external requests, and the only inline script is the nonce'd `window.print()` print handler (no network / no exfiltration, harmless from `file://`, L2). | One render path, no divergence; share downloads keep the owner-structure strip (no leak). |
| D9 | **Error behavior matches each caller's existing view path:** owner missing-blob → **409** "repair needed"; share missing-blob / corrupt-MD / bad-token → coarse **404**; bad `format` → **400**. | Downloads inherit, not redefine, each path's error contract. |
| D10 | **The new MD-download branch is added to 1F-b's money guards** (B18 zero-`reserve` proof + B18b import guard + B18c graph). **The new `lib/html-doc/file-response.ts` helper is added to the B18b guard's scan set** (`shareSources`) and kept a **pure, dependency-free leaf** (no imports beyond Node/web `Response`), so the share route's import of it cannot smuggle in charging code. | The MD branch is a new anonymous code path; the never-charges guarantee must provably extend to it AND to any helper it pulls in (round-1 High: the guard scanned `app/s`/`lib/share`/`read-model.ts` only — a new helper would be unscanned). |
| D11 | **`X-Content-Type-Options: nosniff` on EVERY download/serve response** (md + html, inline + attachment). **Inline `format=md` (no `download`) is served as `text/plain; charset=utf-8`**, not `text/markdown`; the `.md` *download* uses `text/markdown` + attachment. | Raw MD is unescaped AI/worker-authored content that can contain `<script>`/`<html>`; `nosniff` blocks content-sniffing, and `text/plain` inline guarantees a sniffing UA cannot execute it on the app origin (round-1 High: worst case = owner content executing in a share recipient's authenticated origin). |
| D12 | **The share MD branch performs the SAME mandatory pre-response `getShareServeContext` re-check** (revoked/un-promoted → coarse 404) immediately before returning bytes, exactly as the share HTML path does today (`s/route.ts:57-59`). | Round-1 **Blocking**: the MD branch returned right after the blob read, *before* the existing re-check, reopening the D14/B10b revoke-mid-request window that 1F-b closed. |

## 4. Architecture

### 4.1 Owner route — `app/api/html/[id]/route.ts` (`serveCloud`)

After the existing `type` check (`:29-30`, which stays first), add:
- `const format = searchParams.get('format') ?? 'html';` — if not `html`/`md` → **400** (validated after `type`, so `?format=pdf&type=bad` returns the type-400 first; L3).
- `const download = searchParams.get('download') === '1';` (any other value → inline).

After the existing `mdBytes` read (`:60`, and its `:61` 409-on-missing), with `base = mdKey.replace(/\.md$/,'')`:
```ts
if (format === 'md') {
  return fileResponse(mdBytes, {
    kind: 'md', download, base, title: video.title,
    cache: 'private, no-store',  // helper adds nosniff; inline md → text/plain, download md → text/markdown
  });
}
```
The `format === 'html'` path is the existing render, unchanged, except the final `Response` routes through the same helper (`kind: 'html'`) so `download` can add the disposition — same `private, no-store` + CSP header + the new `nosniff`.

### 4.2 Share route — `app/s/[token]/route.ts`

`getShareServeContext` is extended to also return the doc title (`ShareServeContext` gains **`title?: string`** — read from `vid.data.title` on the row it already fetches, validated `typeof === 'string' && .trim()`, else omitted; no extra query, no MD parse; legacy/unvalidated rows without a title fall back to the base key, L1). `format` + `download` are parsed at the top and **`format` is validated first — before both the `TOKEN_RE` shape check (`:25`) and the token lookup** — a bad `format` → **400** (token-independent → not a token-existence oracle; so `/s/<malformed>?format=pdf` → 400, not 404. C11 covers only a *valid/absent* format with a bad token → 404; M2 / B-L2).

After the existing `mdBytes` read (`:37-45`, keep the bad-key→404 catch), the MD branch **must run the same mandatory re-check the HTML path runs at `:57-59` before returning** (D12):
```ts
if (format === 'md') {
  const recheck = await getShareServeContext(svc, token);   // D12/B10b: revoked/un-promoted mid-request → 404
  if ('status' in recheck) return notFound();
  return fileResponse(mdBytes, {
    kind: 'md', download, base: ctx.mdKey.replace(/\.md$/,''), title: ctx.title,
    cache: 'no-store', referrerPolicy: 'no-referrer',   // helper adds nosniff; inline md → text/plain
  });
}
```
The `format === 'html'` path is the existing share render (share-mode strip) + disposition when `download=1`. The MD branch **imports and calls nothing new** beyond the already-present get-only read and `fileResponse` (a pure leaf) — it must not touch `read-model`/`serve-doc`/`reserve`. (Title comes from the DB row, D4 parse-free intact.)

### 4.3 Shared filename/disposition helper — `lib/html-doc/file-response.ts` (new, pure leaf)

**Pure and dependency-free** (imports nothing but the web `Response`; no app imports) so adding it to the B18b guard's `shareSources` scan set (D10) keeps the share money-graph provably clean.

```ts
export function fileResponse(
  body: Buffer | string,
  opts: { kind: 'md' | 'html'; download: boolean; base: string; title?: string;
          cache: string; csp?: string; referrerPolicy?: string },
): Response
```
- **Content-Type:** `html` → `text/html; charset=utf-8`. `md` **inline** (no download) → **`text/plain; charset=utf-8`** (a sniffing UA cannot execute embedded HTML); `md` **download** → `text/markdown; charset=utf-8`. (D11)
- **Always** sets **`X-Content-Type-Options: nosniff`**, plus `Cache-Control` (from `cache`), optional CSP (`csp`) + `Referrer-Policy` (`referrerPolicy`).
- **When `download`:** `Content-Disposition: attachment; filename="<asciiSafe(base)>.<ext>"; filename*=UTF-8''<encodeRFC5987(title?.trim() || base)>.<ext>`, `ext` = `kind`. **The ASCII `filename=` half ALWAYS uses the base key** (`{serial}_{slug}`, already ASCII), **never the unicode title** (per D7) — a non-Latin-1 `filename=` value throws when constructing the header in undici/Fetch and violates RFC 6266; the unicode title rides only in `filename*`.
- **`asciiSafe(s)`** — replace every byte in `[\x00-\x1f\x7f]` (incl. CR/LF) **and every non-printable-ASCII byte `[^\x20-\x7e]`** (guaranteeing a printable-ASCII, header-safe result even if `base` ever held one), plus `"` `\` `/` `;`, with `_`; strip leading/trailing dots and spaces; empty → literal `summary`. The ASCII half thus never carries control/quote/path chars → no header injection or filename breakout.
- **`encodeRFC5987(s)`** — a strict allowlist percent-encoder: pass only `A-Za-z0-9` and the RFC 5987 `attr-char` punctuation `! # $ & + - . ^ _ \` | ~` (in a regex class, place `-` at an edge so `+-.` is not parsed as a **range** that would silently admit `,`); percent-encode (`%HH`, UTF-8 bytes) everything else, so CR/LF/`;`/`"`/quotes become `%0D`/`%0A`/… — never literal in the header.
- Pure, unit-tested (ascii fallback, unicode round-trip, empty/all-non-ASCII/CRLF-in-title, disposition present iff `download`, content-type per kind+download, `nosniff` always present).

## 5. URL Contracts

| Route | Auth | Params | Response |
|---|---|---|---|
| `/api/html/[id]` | session (owner) | `playlist=<uuid>`, `type=summary`, `format=html\|md` (default html), `download=1?` | inline or `attachment` (+`nosniff`); **md inline=`text/plain`, md download=`text/markdown`** (no charge); html=rendered (1F-a money path) |
| `/s/[token]` | none (bearer) | `format=html\|md` (default html), `download=1?` | inline or `attachment` (+`nosniff`); **md inline=`text/plain`, md download=`text/markdown`** (never charge); html=share render (never charge) |

Existing callers (no `format`/`download`) get an **equivalent** response to today (D2): same status, same header name/value set (owner: CSP + `private,no-store`, **no** `Referrer-Policy`; share: CSP + `no-store` + `no-referrer`) **plus the new `nosniff`**, same rendered body modulo the per-response nonce, and no `Content-Disposition`. A regression test pins these (esp. that the owner path gains no `Referrer-Policy`).

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| C1 | Owner view unchanged | owner GET, no `format`/`download` | identical to 1F-a today (inline HTML, materialize+charge path) |
| C2 | Owner download MD | owner GET `format=md&download=1` | **200** `text/markdown`, `attachment` filename; **no model resolution, no charge** |
| C3 | Owner view MD inline | owner GET `format=md` (no download) | 200 **`text/plain; charset=utf-8`** inline (D11 — not `text/markdown`, so embedded HTML can't execute) + `nosniff`; no charge |
| C4 | Owner download HTML | owner GET `format=html&download=1` | 200 `text/html`, `attachment`; 1F-a materialize+charge-once path; CSP + `private,no-store` present |
| C5 | Bad format (either path) | owner OR share GET `format=pdf` | **400** — validated before token/model work; on the share path this is token-independent (no oracle) |
| C6 | Owner MD missing blob | promoted but `summaryMd` blob lost | **409** "repair needed" (same as 1F-a view) |
| C7 | Share view unchanged | share GET, no `format`/`download` | identical to 1F-b today (share-mode HTML, never charge) |
| C8 | Share download MD | share GET `format=md&download=1`, live token | **200** `text/markdown`, `attachment`; **no charge, no generation, no reserve** |
| C9 | Share download HTML | share GET `format=html&download=1`, live token, fresh model | 200 `text/html`, `attachment`, share-mode strip; **never charges**; `no-store`+`no-referrer` |
| C10 | Share HTML not-ready | share `format=html`, model absent/stale | **503** "not ready" (1F-b path); no charge |
| C11 | Share denied (valid/absent format) | expired/revoked/unknown/malformed token, `format` valid or absent | **coarse 404**, no body leak, before blob read |
| C11b | Revoke/un-promote mid-MD-download | token live at initial resolve, revoked/un-promoted before the MD response | **coarse 404** — the MD branch re-runs `getShareServeContext` before returning (D12/B10b) |
| C12 | Share MD missing/corrupt blob | live token, blob lost or unparseable | coarse **404** (MD branch: missing→404; MD is not parsed on the md path, so "corrupt" only affects html) |
| C13 | Filename RFC 5987 | any `download=1` | `Content-Disposition: attachment; filename="<ascii>.<ext>"; filename*=UTF-8''<pct>`; unicode title round-trips |
| C14 | Filename ascii fallback | title is non-ASCII (건강) | `filename="<ascii base-key>.<ext>"` present as fallback + `filename*` unicode |
| C15 | MD path never charges (both) | C2/C3/C8 | `spend_ledger`/`serve_model_charge` unchanged; zero `reserve_serve_model`; MD branch + `file-response.ts` (now in the B18b `shareSources` scan set) reach no charging import (extends B18/B18b/B18c) |
| C16 | Share download isolation | share `format=md`/`html` for owner A via B's token | coarse 404 (confused-deputy guard unchanged); no cross-owner file |
| C17 | Downloaded HTML self-contained | any html download | opens offline (inline CSS, print button); no external request; share download has no owner-structure leak |
| C18 | Disposition absent = inline | `format=md` without `download` | no `Content-Disposition`; served inline |
| C19 | Anti-sniffing header always | any md or html response (inline or download, both paths) | `X-Content-Type-Options: nosniff` present (D11) |
| C20 | Inline MD is non-executable | `format=md` without `download` | `Content-Type: text/plain; charset=utf-8` (not `text/markdown`) — a sniffing UA cannot execute embedded `<script>` on the app origin (D11) |
| C21 | Filename edge cases | title empty / all-non-ASCII / contains CR-LF-quote-`;` | ASCII `filename` = sanitized base (or literal `summary` if empty), never containing control/quote/path chars; `filename*` strict-percent-encoded (CR/LF → `%0D%0A`); no header injection |

## 7. Testing Strategy

- **Unit (`fileResponse` / filename helper)** — ascii fallback; RFC 5987 `filename*` unicode round-trip; **CR/LF/quote/`;`-in-title → percent-encoded, no header injection** (C21); **empty / all-non-ASCII title → `summary`/base fallback**; disposition present iff `download`; content-type per kind+download (**inline md = `text/plain`**, C20); **`nosniff` always present** (C19).
- **Owner route (integration/route)** — C1–C6: view-unchanged regression (**same header set incl. new `nosniff`, no `Referrer-Policy`, no `Content-Disposition`**, M3); MD download no-charge (spy on `reserve_serve_model`, ledger unchanged); HTML download = charge-once path; bad format 400 (after type); missing blob 409.
- **Share route (integration)** — C7–C12, C11b, C16: view-unchanged; MD download no-charge; **revoke/un-promote-mid-MD-download → 404 (the D12 re-check, a B10b test for `format=md`)**; HTML download never-charge + share-mode strip; denied coarse 404; confused-deputy for both formats.
- **Money guards (C15)** — the 1F-b import-guard is a **flat, non-recursive grep** over an explicit file set, so adding `lib/html-doc/file-response.ts` to `shareSources` catches only imports written *in that file*; the real protection is an explicit **leaf assertion** the plan MUST add — `file-response.ts` contains **no `import … from '@/…'`** (a dependency-free leaf), so it cannot transitively reach charging code. (`shareSources` uses `.filter(existsSync)` → the file must exist when the guard runs; TDD ordering.) Extend the B18 zero-`reserve` proof so the `format=md` share branch is covered.
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
3. Existing `/api/html/[id]` and `/s/[token]` callers (no `format`/`download`) get an equivalent response: same status + same header set/values (plus new `nosniff`) + same body modulo nonce + no `Content-Disposition` (the owner path gains no `Referrer-Policy`) — pinned by a regression test.
4. Filenames are correct for unicode titles (RFC 5987) with an ascii fallback; downloaded HTML is self-contained and (for shares) leaks no owner structure.
5. `tsc` clean; unit + integration suites green; spec cleared dual adversarial review to convergence.
