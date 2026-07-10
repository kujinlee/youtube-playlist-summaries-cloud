# Stage 1F-b — Share Tokens (anonymous read of one summary doc, cloud)

**Status:** 🟡 **design DRAFT (v2)** — brainstormed and design-approved by the user 2026-07-10; v1 dual adversarial review (Codex `gpt-5.5` + Claude, independent) returned **1 Blocking / 3 High / 5 Medium**; this v2 addresses all of them. **Next: re-review to convergence → user spec-approval → `writing-plans`.** **Branch:** `feat/stage-1f-b-share-tokens`.
**Review trail:** `docs/reviews/spec-1f-b-codex-v1.md`, `docs/reviews/spec-1f-b-claude-v1.md`.

> **Design in one paragraph:** a doc owner mints an opaque, high-entropy **capability link** to **one** promoted summary doc. Anyone with the link reads the rendered summary HTML — no login, no owner money spent, no access to anything else the owner owns. The share path **only reads** an already-materialized magazine model (never generates, never charges); the sole new privileged surface is a read-only, token-gated `service_role` fetch of exactly the one doc's blobs.

**Predecessor:** Stage 1F-a (authorized, lazy-materialized summary-HTML serving, PR #7, merged `288f591`). This slice reuses its render/CSP stack and its magazine-model store, and **refactors** one 1F-a helper (`serve-doc.ts`) to expose a shared read-only path (see D13).
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 (print & share), §7 (RLS + storage-key isolation).
**Sibling slices:** 1F-b = share tokens (this doc); 1F-c = downloads / PDF / Obsidian export.

---

## 1. Purpose

Let a summary-doc owner grant **read-only, unauthenticated** access to **one** rendered summary HTML doc by handing out a link. The link is a bearer capability: whoever holds it reads that one doc and nothing else. The owner sets an expiry and can revoke links at any time. Anonymous share traffic must be **structurally incapable of spending the owner's money**.

**In scope (backend):** the `share_tokens` schema + RLS, the mint/revoke/list definer RPCs, the anonymous share-serve route, and the read-only-helper refactor of `serve-doc.ts` that makes "never charges" structural. **Out of scope:** the owner-facing "manage my links" UI (Sub-project 2, frontend), and every 1F-c concern (PDF, download, Obsidian).

## 2. Background — why a share viewer hits three walls today

The 1F-a serve path is owner-only end to end, by three independent mechanisms:

1. **Session gate** — `app/api/html/[id]/route.ts` calls `supabase.auth.getUser()` → **401** with no session.
2. **RLS + owner assert** — the playlist row, the index, and every blob are gated by `split_part(name,'/',1) = auth.uid()` (storage RLS, `0007`) plus an explicit owner-assert. A non-owner gets **404**.
3. **Money RPC** — `reserve_serve_model` (`0012`) derives owner from `auth.uid()` internally and returns `denied` to any non-owner, so generation is impossible for anyone but the owner.

A share viewer is by definition **not the owner**, so all three block them. 1F-b introduces a *parallel* serve path with a **different trust model** — a bearer capability token instead of a session — and must re-establish money and isolation guarantees for that path from scratch.

**The consequence that drives the design:** the doc's bytes (summary MD + cached magazine model) live in owner-`service_role`-gated storage. There is **no anon-RLS path** to them (`0007`: only the owner's own `auth.uid()` segment or `service_role` can read). Serving a shared doc therefore *requires* a `service_role` read — the design's job is to make that read minimal, read-only, token-gated, and generation-free.

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Share unit = one `(playlist, video)` summary doc** per token. | Smallest surface; mirrors 1F-a's per-request serve. Whole-playlist / doc-set is YAGNI here. |
| D2 | **The share path never generates and never charges** — reads an already-materialized model only. | Anonymous traffic is structurally incapable of spending owner money. No `reserve_serve_model`, no Gemini, no `spend_ledger`. |
| D3 | **Serve-if-fresh, else "not ready."** Model absent/stale (`isFresh` false) → coarse not-ready, never generate. | The owner materializes by viewing once (normal 1F-a path, charged to the owner). Single freshness source of truth. |
| D4 | **Read auth = token-gated, read-only `service_role` fetch on a dedicated share route.** | Only mechanism that can read owner-gated blobs. Bounded: read-only, one doc, only after the token validates. |
| D5 | **Opaque 256-bit random token**, base64url, in the URL. Not a JWT. | Revocation needs a DB row regardless; a signed token buys nothing. High entropy ⇒ not enumerable. |
| D6 | **Token stored SHA-256-hashed (32 bytes) at rest; plaintext generated in the Next route, shown once.** | A DB leak cannot hand out live links. Plaintext never transits or rests in Postgres. |
| D7 | **Expiry: owner-set at mint (default 30 days; explicit `never`; bounded `1..MAX_SHARE_TTL_DAYS`).** | Safe-by-default with flexibility; bounds reject hostile/degenerate TTLs. |
| D8 | **Revocation: multiple live tokens per doc; revoke-one + revoke-all-for-doc; effective immediately, including in-flight requests.** | Per-recipient links, targeted kill. "Immediately" is enforced by a post-read re-check (D14). |
| D9 | **All writes go through `SECURITY DEFINER` RPCs; `share_tokens` is `force`-RLS, `service_role`-only grants.** No direct `INSERT/UPDATE` for `authenticated`. | Same discipline as `enqueue_job` / `serve_model_charge`. |
| D10 | **Share render is "share-mode":** `dig:false`, nonce CSP, `Cache-Control: no-store`, **`Referrer-Policy: no-referrer`**, and **strips the owner-structure leak** (the `source-md` MD-key meta + footer, plus `video-id`/`generator` metas). See §4.5 for the exact strip-set. | A link leaks neither owner library structure nor the token itself; a revoked link can't be CDN/browser-cached. |
| D11 | **Oracle-free coarse denial:** invalid / expired / revoked / unknown all return the same **404**, *before any blob read*; malformed 404s before any DB call. | No enumeration or existence oracle; invalid tokens cost nothing. |
| D12 | **Anonymous-route abuse control is a named pre-launch follow-up, not first-slice code.** The route is generation-free (B18 holds), but each *valid* hit costs real infra (2 blob reads + parse + render, `no-store`). | Honest cost accounting: it is infra-$, not zero. §9 records per-token/IP rate-limit (and an optional `(token_hash, generatorVersion)` HTML cache) as the pre-launch hardening. |
| D13 | **Extract an exported read-only resolver** `readFreshMagazineModel(...)` (does `readModelEnvelope` + `isFresh`, **no RPC, no generate**); refactor `resolveMagazineModel` to call it on its read branch; **export `isFresh`**. The share module **must not import** `resolveMagazineModel`, `reserve_serve_model`, or `generateMagazineModel`. | Turns "never charges" from prose into structure. Touching merged 1F-a code → re-review trigger (§8). |
| D14 | **Share serve re-checks token liveness (and `promoted`) after the blob reads, immediately before returning 200.** | Makes revocation/un-promote effective for in-flight requests (D8), closing the read-committed serve-once-more race. |
| D15 | **Confused-deputy guard:** the share route resolves the doc by the **global** `playlist_id AND owner_id` (never `readIndex`, which keys on per-owner-unique `playlist_key`) and **asserts the resolved `owner_id` equals the token row's `owner_id`** before assembling the principal. | Mirrors `getWorkerStorageBundle` (`resolve.ts:71`); prevents any A-owner/B-playlist_key confusion class (the bug the 1F-a re-review caught). |

## 4. Architecture

### 4.1 Schema — `share_tokens` (new migration `00NN_share_tokens.sql`)

```sql
create table share_tokens (
  id            uuid primary key default gen_random_uuid(),
  token_hash    bytea not null unique check (octet_length(token_hash) = 32),  -- sha256; plaintext never stored (D6)
  owner_id      uuid not null references profiles(id) on delete cascade,
  playlist_id   uuid not null,
  video_id      text not null,
  created_at    timestamptz not null default now(),
  expires_at    timestamptz,                           -- null = never (D7)
  revoked_at    timestamptz
);
alter table share_tokens enable row level security;
alter table share_tokens force row level security;      -- only BYPASSRLS roles read/write
grant select, insert, update, delete on share_tokens to service_role;  -- no anon/authenticated policy (D9)
create index share_tokens_owner_idx on share_tokens (owner_id);
-- token_hash already unique-indexed by the constraint.
```

`MAX_SHARE_TTL_DAYS` (D7) is a constant used by the mint RPC (below); default value **365** (revisit in planning).

### 4.2 RPCs (all `SECURITY DEFINER set search_path = public`, owner from `auth.uid()` internally, granted to `authenticated`)

- **`create_share_token(p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash bytea) returns timestamptz`**
  Derive `v_owner := auth.uid()`; raise if null. Validate `octet_length(p_token_hash) = 32` (else raise — the table CHECK is the backstop). Verify `(p_playlist_id, p_video_id)` is owned by `v_owner` **and** the summary artifact `status = 'promoted'` (same predicate as `reserve_serve_model`); else `raise exception` → route maps to a coarse **404** (never 403, which would confirm existence). Insert with `expires_at = p_expiry`; return `expires_at`. **The plaintext token, its hash, the default-30-day and `never` decisions, and the `1..MAX_SHARE_TTL_DAYS` bound are all resolved in the Next route (§4.4)** — this RPC receives a concrete `expires_at` (or null for never) and a validated hash length, keeping TTL policy in one testable place.
- **`revoke_share_token(p_id uuid) returns boolean`** — `update share_tokens set revoked_at = now() where id = p_id and owner_id = auth.uid() and revoked_at is null`; return whether a row changed.
- **`revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns int`** — revoke every live token for that owned doc; return the count.
- **`list_share_tokens(p_playlist_id uuid, p_video_id text) returns table(id uuid, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz)`** — owner-scoped (`where owner_id = auth.uid()`); **never returns `token_hash`**. Backend RPC now; UI consumer is Sub-project 2.

### 4.3 Share-serve route — `app/s/[token]/route.ts` (anonymous; public URL `/s/<token>`)

Ordered so invalid tokens cost nothing (D11), generation-free (D2/D13), confused-deputy-guarded (D15), revocation-immediate (D14):

1. **Shape-validate** the path token (base64url, expected length). Malformed ⇒ **404 (coarse)**, before any DB call.
2. `hash = sha256(token)`. Build the **`service_role` client** (the one privileged surface). `SELECT id, owner_id, playlist_id, video_id FROM share_tokens WHERE token_hash = hash AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())`. No row ⇒ **404 (coarse)**, *before any blob read*.
3. **Confused-deputy-guarded resolve (D15):** resolve the doc via a service-role helper that selects the playlist by `playlist_id AND owner_id = token.owner_id` (copying `getWorkerStorageBundle`, `resolve.ts:71`), asserts the resolved `owner_id` equals the token's, then reads the video row **by that playlist UUID** and asserts `summaryMd.status = 'promoted'`, returning `{ principal: {id: owner_id, indexKey: playlist_key}, mdKey }`. Any mismatch / not-promoted / video-gone ⇒ **404 (coarse)**.
4. **Read-only `service_role` reads (D13):** using a **`get`-only** blob view (`ReadOnlyBlobStore = Pick<BlobStore,'get'>` — no `put/delete/promote` reachable), read the MD blob → `parseSummaryMarkdown` → titles → `base = mdKey.replace(/\.md$/,'')`. Call **`readFreshMagazineModel({ blobStore, principal, base, titles })`** — `readModelEnvelope + isFresh`, **no RPC, no generate**. `not_ready` (absent or stale) ⇒ **"not ready"** (503-class). The share module imports **none** of `resolveMagazineModel` / `reserve_serve_model` / `generateMagazineModel`.
5. **Re-check before responding (D14):** re-run the step-2 liveness `SELECT` (and, if required, re-assert `promoted`). If the token is now revoked/expired ⇒ **404**; do not emit the body.
6. **Render share-mode (§4.5):** `renderMagazineHtml(parsed, model, { nonce, dig: false, share: true })`. Respond **200** `text/html` with `Content-Security-Policy: buildSummaryCsp(nonce)`, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`.

### 4.4 Mint route — `POST /api/share` (authenticated owner)

Session client; `getUser()` → `ownerId` (401 if none). Body `{ playlistId, videoId, ttlDays? }` where `ttlDays` is `number` (>0 days), the string `'never'`, or omitted. **TTL contract (fixes the `?? 30` null-swallow):** omitted ⇒ 30 days; `'never'` ⇒ `p_expiry = null`; a positive integer `1..MAX_SHARE_TTL_DAYS` ⇒ `now + ttlDays days`; anything else (0, negative, non-integer, over max) ⇒ **400**. Compute `expires_at` in the route, then generate `token = base64url(crypto.randomBytes(32))`, `hash = sha256(token)`, and call `create_share_token(playlistId, videoId, expires_at, hash)`. On success return **201** `{ token, url: "/s/<token>", expiresAt }` — **the only time the plaintext is exposed**. Ownership/promoted failure ⇒ coarse **404**. Revoke/list routes are thin authenticated wrappers over their RPCs; their UI lives in Sub-project 2.

### 4.5 Share-mode render (`share: true` — new `renderMagazineHtml` option)

`renderMagazineHtml` gains a real `share?: boolean` option (today it accepts only `nonce`/`dig`). `share: true`:
- **Strips** the `<meta name="source-md">` tag **and** the footer `<code>${sourceMd}</code>` (the MD key `NNNNN_slug.md`, which leaks the owner's serial number / library size / ordering — the only genuine owner-structure leak), plus the `<meta name="video-id">` and `<meta name="generator">` tags (low-risk, stripped for cleanliness).
- **Keeps** the doc body proper — title, channel, source video URL, TL;DR, takeaways, sections, timestamp links — these are the shared summary's content, not owner-account identity, and a viewer seeing the underlying YouTube video is expected.
- Inherits `dig:false` (no cross-doc nav) from 1F-a.

`buildSummaryCsp` is unchanged (the referrer control is a response header, not CSP).

## 5. URL Contracts

| Route | Method | Auth | Params | Success |
|---|---|---|---|---|
| `/api/share` | POST | session (owner) | body `{ playlistId, videoId, ttlDays? }` | 201 `{ token, url: "/s/<token>", expiresAt }` |
| `/s/[token]` | GET | **none** (bearer token) | path `token` | 200 `text/html` (share-mode render) + `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| `/api/share/[id]/revoke` | POST | session (owner) | path `id` | 200 `{ revoked: boolean }` |
| `/api/share/revoke-all` | POST | session (owner) | body `{ playlistId, videoId }` | 200 `{ count }` |

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| B1 | Mint a link | owner POST, owns `(playlist,video)`, summary `promoted` | 201 `{ token, url, expiresAt }`; row stored with `sha256(token)` (32 bytes); plaintext returned once |
| B2 | Mint on unowned/unpromoted doc | owner POST, doc not owned or not `promoted` | coarse **404**; no row; no existence leak |
| B3 | Mint unauthenticated | POST, no session | **401** |
| B4 | Mint default expiry | `ttlDays` omitted | `expires_at = now()+30d` |
| B5 | Mint never-expiry | `ttlDays: 'never'` | `expires_at = null` |
| B5b | Mint bounded/rejected TTL | `ttlDays` = 0 / negative / non-integer / > `MAX_SHARE_TTL_DAYS` | **400**; no row |
| B6 | Serve a valid link | GET `/s/<token>`, live token, model fresh | **200** share-mode render; **no** reserve/Gemini/ledger touch |
| B7 | Serve when model not materialized | live token, model absent | **"not ready"** (503-class); **no generation** |
| B8 | Serve when model stale (version bump) | live token, `isFresh` false | **"not ready"**; heals after the **owner** next views (owner-charged) |
| B9 | Serve expired token | `expires_at < now()` | **404 (coarse)**, before any blob read |
| B10 | Serve revoked token | `revoked_at` set at step 2 | **404 (coarse)**, before any blob read |
| B10b | Revoke lands mid-serve (in-flight) | token live at step 2, revoked before step 5 | step-5 re-check → **404**; body not emitted (D14) |
| B11 | Serve malformed token | wrong shape/length | **404 (coarse)**, before any DB call |
| B12 | Serve unknown token | well-formed, no matching hash | **404 (coarse)**, before any blob read |
| B13 | Serve after summary un-promoted / deleted | live token, summary no longer `promoted` | **404 (coarse)** |
| B14 | Revoke one link | owner POST revoke, owns the token | `revoked_at` set; later serve → B10; returns `true` |
| B15 | Revoke someone else's / unknown token | revoke `id` not owned by caller | no change; returns `false`; no leak |
| B16 | Revoke-all for a doc | owner revoke-all | every live token for that doc revoked; returns count |
| B17 | List links | owner list for own doc | rows `{id, created_at, expires_at, revoked_at}`; **never** `token_hash` |
| B18 | No money on the share path | any share serve (B6–B13) | `spend_ledger` / `serve_model_charge` unchanged; **zero** `reserve_serve_model` **and** `generateMagazineModel` calls |
| B18b | Share module import ban | source of the share route + helper | does not import `resolveMagazineModel` / `reserve_serve_model` / `generateMagazineModel` (grep/lint guard) |
| B19 | `service_role` scoped read-only | share serve | only the one doc's MD + model read via a `get`-only view; no write method reachable |
| B19b | Confused-deputy guard | token owner_id vs resolved playlist owner_id | resolution asserts equality; mismatch → **404**; never addresses another owner's segment (D15) |
| B20 | CSP present + coherent | any 200 share serve | full nonce CSP; header nonce matches every inline nonce; no `unsafe-*` |
| B21 | No-store + no-referrer | any 200 share serve | `Cache-Control: no-store` **and** `Referrer-Policy: no-referrer` |
| B22 | Share render strips owner-structure | any 200 share serve | no `source-md` meta/footer, no `video-id`/`generator` meta, no cross-doc nav, no dig controls; body content retained |
| B23 | Direct RPC bypass blocked | `authenticated` direct `INSERT`/`UPDATE` on `share_tokens` | denied (no grant/policy); mutation only via definer RPCs |
| B24 | Hash-at-rest | inspect a stored row | `token_hash` (32 bytes) present; plaintext absent anywhere in DB |

## 7. Testing Strategy

- **Unit** — token gen/hash helper (shape, 32-byte hash, base64url); TTL contract (omitted→30, `'never'`→null, bounds→400); `readFreshMagazineModel` (ok when fresh, not_ready when absent/stale, **never** calls reserve/generate — spy asserts zero calls); share-mode render strips the enumerated set (B22 fixtures with `source-md`/`video-id`/`generator` present).
- **Import guard (B18b)** — a grep/lint test asserting the share route + helper modules import none of the three charging symbols.
- **Integration (real DB, `service_role`)** — each RPC: ownership+promoted gate, hash-length CHECK, expiry math, revoke-one / revoke-all / list (no-hash), direct-INSERT bypass denied (B23). Serve path against real storage: fresh→200, absent/stale→not-ready, expired/revoked/unknown/malformed→coarse-404-before-blob-read, un-promoted→404, in-flight-revoke→404 (B10b).
- **Money invariant (B18)** — a share-serve test asserts `spend_ledger` and `serve_model_charge` rows are **unchanged** across B6–B13, mirroring the 1F-a no-charge seam tests.
- **Isolation (B19/B19b)** — a scoped-read test proving the share route reads only the token's one doc via a `get`-only view; an owner-B-unreachable-via-owner-A's-token test; a confused-deputy test forcing an owner_id/playlist mismatch → 404.
- **Mock boundary** — Gemini stays mocked at `lib/gemini.ts`; the share path makes **zero** Gemini calls (asserted).

## 8. Dev-Process Re-Review Triggers

Squarely in the **iterative re-review to convergence** category (`dev-process.md`): a new **capability grant**, **anonymous access**, a **second `service_role` surface**, a **money-adjacent** path, **and** a refactor of already-merged shared 1F-a code (D13, `serve-doc.ts`). Spec and plan each go through dual adversarial review, re-reviewed until a round returns no new Blocking/High. Implementation applies §8 per-task iterative re-review on: the `readFreshMagazineModel` refactor (D13), the money-invariant task (B18/B18b), and the `service_role` scoped-read + confused-deputy task (B19/B19b).

## 9. Out of Scope / Follow-ups

- **Owner-facing "manage links" UI** — Sub-project 2 (frontend), consumes `list/revoke` RPCs + `/api/share`.
- **Anonymous-route abuse control (D12) — named pre-launch hardening:** coarse per-token/IP rate-limit and/or a short `(token_hash, generatorVersion)`-keyed rendered-HTML cache (every hit currently reaches origin because `no-store`). Generation-free, so not a money hole; it is an infra-cost/DoS mitigation to land before public launch.
- **`GENERATOR_VERSION`-bump staleness (known limitation):** a version bump makes every live shared link return "not ready" until the **owner** next opens the doc (owner-charged re-materialize) — D3 forbids share-path generation. Recipients get no signal. Acceptable for this slice; a future **heal-at-mint** (mint verifies freshness and queues an owner-charged re-materialize) or an owner "refresh shares" action is the follow-up.
- **Orphaned/stale token rows:** un-promoting or deleting a summary leaves token rows (→ 404 at serve, harmless); reaping an anon guest-owner cascades their tokens away, silently killing their links. GC/notification is a follow-up, not correctness.
- **Path-token log capture (threat-model note):** a token in the URL path is recorded by any reverse proxy / access log — inherent to capability URLs. `Referrer-Policy: no-referrer` (D10) blocks cross-origin `Referer` leakage, but on-host access logs still see it; accept for this slice, or move to a non-logged transport later.
- **1F-c** — PDF, download, Obsidian export of shared docs.
- **Share of dig-deeper docs** — cloud dig-deeper is deferred; share is summary-only.
- **Analytics / view counts** — not needed for the capability.

## 10. Success Criteria

1. An owner mints a link to one promoted summary doc; an anonymous holder reads it; a non-holder cannot.
2. No share-serve request (valid, expired, revoked, unknown, or not-ready) ever charges the owner, calls `reserve_serve_model`, or calls Gemini — proven by B18 (row-unchanged) **and** B18b (import guard).
3. The only privileged surface on the share path is a read-only (`get`-only), token-gated `service_role` read of exactly the one doc's blobs, with the confused-deputy owner-match assert (B19/B19b).
4. Expiry, revoke (one + all), and un-promote take effect on the serve path — including in-flight requests (B10b) — and invalid tokens yield oracle-free coarse 404s before any blob read.
5. Plaintext tokens exist only in the mint response; the DB stores 32-byte hashes only (B24); the share page emits `Referrer-Policy: no-referrer` and strips the owner-structure metadata (B21/B22).
6. `tsc` clean; unit + integration suites green; the spec cleared dual adversarial review to convergence.
