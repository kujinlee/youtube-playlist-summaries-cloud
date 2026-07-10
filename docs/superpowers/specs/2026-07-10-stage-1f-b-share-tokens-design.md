# Stage 1F-b — Share Tokens (anonymous read of one summary doc, cloud)

**Status:** ✅ **design CONVERGED (v4)** — v1 dual review (1 Blocking / 3 High / 5 Medium) → v2; round-2 re-review (1 new High + 3 Medium) → v3; **round-3 re-review returned 0 new Blocking / 0 new High from both passes (CONVERGED)** → this v4 folds in the round-3 Lows + one Codex type finding (near-free; gate already met at v3). **Next: user spec-approval → `writing-plans`.** **Branch:** `feat/stage-1f-b-share-tokens`.
**Review trail:** `docs/reviews/spec-1f-b-{codex,claude}-v1.md`, `-v2-rereview.md`, `-v3-rereview.md`.

> **Design in one paragraph:** a doc owner mints an opaque, high-entropy **capability link** to **one** promoted summary doc. Anyone with the link reads the rendered summary HTML — no login, no owner money spent, no access to anything else the owner owns. The share path **only reads** an already-materialized magazine model (never generates, never charges); the sole new privileged surface is a read-only, token-gated `service_role` fetch of exactly the one doc's blobs.

**Predecessor:** Stage 1F-a (authorized, lazy-materialized summary-HTML serving, PR #7, merged `288f591`). This slice reuses its render/CSP stack and its magazine-model store, and **extracts** a new generate-free leaf module out of 1F-a's `serve-doc.ts` (see D13).
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 (print & share), §7 (RLS + storage-key isolation).
**Sibling slices:** 1F-b = share tokens (this doc); 1F-c = downloads / PDF / Obsidian export.

---

## 1. Purpose

Let a summary-doc owner grant **read-only, unauthenticated** access to **one** rendered summary HTML doc by handing out a link. The link is a bearer capability: whoever holds it reads that one doc and nothing else. The owner sets an expiry and can revoke links at any time. Anonymous share traffic must be **structurally incapable of spending the owner's money**.

**In scope (backend):** the `share_tokens` schema + RLS, the mint/revoke/list definer RPCs, the anonymous share-serve route, and the extraction of a generate-free `read-model.ts` leaf module (D13) that makes "never charges" structural. **Out of scope:** the owner-facing "manage my links" UI (Sub-project 2, frontend), and every 1F-c concern (PDF, download, Obsidian).

## 2. Background — why a share viewer hits three walls today

The 1F-a serve path is owner-only end to end, by three independent mechanisms:

1. **Session gate** — `app/api/html/[id]/route.ts` calls `supabase.auth.getUser()` → **401** with no session.
2. **RLS + owner assert** — the playlist row, the index, and every blob are gated by `split_part(name,'/',1) = auth.uid()` (storage RLS, `0007`) plus an explicit owner-assert. A non-owner gets **404**.
3. **Money RPC** — `reserve_serve_model` (`0012`) derives owner from `auth.uid()` internally and returns `denied` to any non-owner.

A share viewer is by definition **not the owner**, so all three block them. 1F-b introduces a *parallel* serve path with a **different trust model** — a bearer capability token instead of a session — and must re-establish money and isolation guarantees for that path from scratch.

**The consequence that drives the design:** the doc's bytes (summary MD + cached magazine model) live in owner-`service_role`-gated storage. There is **no anon-RLS path** to them (`0007`: only the owner's own `auth.uid()` segment or `service_role` can read). Serving a shared doc therefore *requires* a `service_role` read — the design's job is to make that read minimal, read-only, token-gated, and generation-free.

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Share unit = one `(playlist, video)` summary doc** per token. | Smallest surface; mirrors 1F-a's per-request serve. |
| D2 | **The share path never generates and never charges** — reads an already-materialized model only. | Anonymous traffic structurally cannot spend owner money. No `reserve_serve_model`, no Gemini, no `spend_ledger`. |
| D3 | **Serve-if-fresh, else "not ready."** Model absent/stale (`isFresh` false) → coarse not-ready, never generate. | The owner materializes by viewing once (normal 1F-a path, owner-charged). Single freshness source of truth. |
| D4 | **Read auth = token-gated, read-only `service_role` fetch on a dedicated share route.** | Only mechanism that can read owner-gated blobs. Bounded: read-only, one doc, only after the token validates. |
| D5 | **Opaque 256-bit random token**, base64url, in the URL. Not a JWT. | Revocation needs a DB row regardless. High entropy ⇒ not enumerable. |
| D6 | **Route-generated tokens are 256-bit random, stored SHA-256-hashed (32 bytes); plaintext shown once.** The DB CHECK enforces *hash shape* (32 bytes), not entropy — a direct-RPC `authenticated` caller can only self-weaken links to **their own** doc (out of threat scope; not cross-tenant). | A DB leak can't hand out live links. Plaintext never rests in Postgres. Entropy is guaranteed by the route's `crypto.randomBytes(32)`, the only sanctioned mint path. |
| D7 | **Expiry: owner-set at mint (default 30 days; explicit `never`; bounded `1..MAX_SHARE_TTL_DAYS=365`), enforced in BOTH the route (UX) and the definer RPC (trust boundary).** | Safe-by-default with flexibility; the RPC bound rejects hostile/degenerate `expires_at` from a direct caller. |
| D8 | **Revocation: multiple live tokens per doc; revoke-one + revoke-all-for-doc.** A serve's **final pre-response re-check** (D14) closes the revoke-before-final-check race; a revoke landing after that check may serve one more time (`no-store`-bounded), so semantics are "effective within one request boundary," not literally instantaneous. | Per-recipient links, targeted kill, honest race semantics. |
| D9 | **All writes go through `SECURITY DEFINER` RPCs; `share_tokens` is `force`-RLS, `service_role`-only grants.** No direct `INSERT/UPDATE` for `authenticated`. | Same discipline as `enqueue_job` / `serve_model_charge`. |
| D10 | **Share render is "share-mode":** `dig:false`, nonce CSP, `Cache-Control: no-store`, **`Referrer-Policy: no-referrer`**, and **strips the owner-structure leak** (the `source-md` MD-key meta + the footer `<code>` holding that key, plus `video-id`/`generator` metas). See §4.5. | A link leaks neither owner library structure nor the token; a revoked link can't be CDN/browser-cached. |
| D11 | **Oracle-free coarse denial:** invalid / expired / revoked / unknown → same **404**, *before any blob read*; malformed → 404 before any DB call. | No enumeration/existence oracle; invalid tokens cost nothing. |
| D12 | **Anonymous-route abuse control is a named pre-launch follow-up.** Generation-free (B18), but each *valid* hit costs real infra (2 blob reads + parse + render, `no-store`). | Honest cost accounting; §9 names per-token/IP rate-limit + optional `(token_hash, generatorVersion)` HTML cache. |
| D13 | **Extract a generate-free leaf module `lib/html-doc/read-model.ts`** exporting `readFreshMagazineModel(...)` (does `readModelEnvelope` + `isFresh`, **no RPC, no generate**) and `isFresh`. It imports **only** `readModelEnvelope` + `GENERATOR_VERSION` — **never** `@/lib/gemini`, `@/lib/gemini-cost`, `serve-doc`, or any `reserve_*`. To keep it a **true leaf**, extract `GENERATOR_VERSION` into a tiny `lib/html-doc/constants.ts` that both `render.ts` and `read-model.ts` import (so the freshness helper does not drag the whole renderer graph). `serve-doc.ts` imports the helper from `read-model.ts` and uses it at **both** its read sites; the share route imports **only** `read-model.ts`. | Puts the helper where its module graph is provably Gemini-free — so importing it into the anonymous route cannot pull in the charging code. This is the structural core of "never charges." Touching merged 1F-a code (`serve-doc.ts`) → re-review trigger (§8). |
| D14 | **Share serve re-checks token liveness AND `promoted` after the blob reads, immediately before returning 200 (mandatory, not conditional).** | Closes the revoke/un-promote-before-final-check race (B10b/B13). |
| D15 | **Confused-deputy guard:** resolve the doc by the **global** `playlist_id AND owner_id` (never `readIndex`, which keys on per-owner-unique `playlist_key`), and **assert the resolved `owner_id` equals the token row's**. | Mirrors `getWorkerStorageBundle` (`resolve.ts:71`). The `videos(playlist_id, owner_id)` composite FK (`0001`) already forbids a video's owner differing from its playlist's — the assert is belt-and-suspenders. |
| D16 | **The share route uses a runtime `get`-only wrapper** `{ get: fullStore.get.bind(fullStore) }` (typed `ReadOnlyBlobStore = Pick<BlobStore,'get'>`), not a full `SupabaseBlobStore` cast — so `put/delete/promote` are unreachable at runtime, not just hidden by the type. **`readModelEnvelope` (and `readFreshMagazineModel`) must accept `blobStore: ReadOnlyBlobStore`** (a widening of the current `BlobStore` param — read-only, safe) so the wrapper type-checks without an unsafe cast; `writeModelEnvelope` keeps the full `BlobStore`. | A `Pick` type alone still points at an object carrying write methods; the wrapper removes them for real. Without widening `readModelEnvelope`, the wrapper wouldn't compile and the "obvious fix" (cast back to `BlobStore`) would defeat D16. |

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
```

`MAX_SHARE_TTL_DAYS = 365` (D7) is inlined in the mint RPC's bound (below) and mirrored as a route constant.

### 4.2 RPCs (all `SECURITY DEFINER set search_path = public`, owner from `auth.uid()` internally, granted to `authenticated`)

- **`create_share_token(p_playlist_id uuid, p_video_id text, p_expiry timestamptz, p_token_hash bytea) returns timestamptz`**
  Derive `v_owner := auth.uid()`; raise if null. **Validate at the trust boundary:** `octet_length(p_token_hash) = 32` (table CHECK is the backstop) **and** `p_expiry IS NULL OR (p_expiry > now() AND p_expiry <= now() + make_interval(days => 365) + interval '1 hour')` — else raise (a direct caller cannot mint a born-dead or effectively-permanent link, closing the round-2 High). The **`+ interval '1 hour'` grace margin** absorbs app↔DB clock skew so a legitimate route-computed `ttlDays: 365` mint is never spuriously rejected (round-3 B-L5); the bound still rejects anything materially over a year. Verify `(p_playlist_id, p_video_id)` is owned by `v_owner` **and** the summary artifact `status = 'promoted'` (same predicate as `reserve_serve_model`); else raise → route maps to coarse **404** (never 403). Insert with `expires_at = p_expiry`; return `expires_at`. The plaintext token and its hash are produced in the Next route (§4.4); this RPC only sees the 32-byte hash.
- **`revoke_share_token(p_id uuid) returns boolean`** — `update … set revoked_at = now() where id = p_id and owner_id = auth.uid() and revoked_at is null`; return whether a row changed.
- **`revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns int`** — revoke every live token for that owned doc; return the count.
- **`list_share_tokens(p_playlist_id uuid, p_video_id text) returns table(id, created_at, expires_at, revoked_at)`** — owner-scoped (`where owner_id = auth.uid()`); **never returns `token_hash`**. Backend RPC now; UI is Sub-project 2.

### 4.3 Share-serve route — `app/s/[token]/route.ts` (anonymous; public URL `/s/<token>`)

1. **Shape-validate** the path token (base64url, expected length). Malformed ⇒ **404 (coarse)**, before any DB call.
2. `hash = sha256(token)`. Build the **`service_role` client**. `SELECT id, owner_id, playlist_id, video_id FROM share_tokens WHERE token_hash = hash AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())`. No row ⇒ **404 (coarse)**, before any blob read.
3. **Confused-deputy-guarded resolve (D15):** select the playlist by `playlist_id AND owner_id = token.owner_id` (copying `getWorkerStorageBundle`, `resolve.ts:71`), assert the resolved `owner_id` equals the token's, read the video **by that playlist UUID**, assert `summaryMd.status = 'promoted'`, and take **`mdKey = artifacts.summaryMd.key ?? video.summaryMd`** (the owner-path H-2 precedence, `route.ts:55-58`). Return `{ principal: {id: owner_id, indexKey: playlist_key}, mdKey }`. Any mismatch / not-promoted / video-gone ⇒ **404 (coarse)**.
4. **Read-only reads (D13/D16):** wrap the service-role blob store as `{ get: store.get.bind(store) }`. Read the MD blob; **if the MD blob is missing behind a `promoted` record ⇒ coarse 404** (the anon analogue of the owner path's `repair needed`, `route.ts:60` — no repair hint leaked). Then `parseSummaryMarkdown` (wrapped: a parse throw on corrupt MD is caught ⇒ coarse **404**, **never a 500 leak**) → titles → `base = mdKey.replace(/\.md$/,'')`. Call **`readFreshMagazineModel({ blobStore: readOnly, principal, base, titles })`** from `read-model.ts` — no RPC, no generate. `not_ready` (absent or stale model) ⇒ **"not ready"** (503-class). The share module imports none of `resolveMagazineModel` / `generateMagazineModel` (and calls no `reserve_serve_model` RPC).
5. **Mandatory re-check before responding (D14):** re-run the step-2 liveness `SELECT` **and** re-assert `promoted` on the video row. If the token is now revoked/expired or the doc un-promoted ⇒ **404**; do not emit the body.
6. **Render share-mode (§4.5):** `renderMagazineHtml(parsed, model, { nonce, dig: false, share: true })`. Respond **200** `text/html` with `Content-Security-Policy: buildSummaryCsp(nonce)`, `Cache-Control: no-store`, `Referrer-Policy: no-referrer`.

### 4.4 Mint route — `POST /api/share` (authenticated owner)

Session client; `getUser()` → `ownerId` (401 if none). Body `{ playlistId, videoId, ttlDays? }` where `ttlDays` is `number` (>0 days), `'never'`, or omitted. **TTL contract:** omitted ⇒ 30 days; `'never'` ⇒ `expires_at = null`; positive integer `1..365` ⇒ `now + ttlDays days`; anything else (0, negative, non-integer, > 365) ⇒ **400**. Compute `expires_at` in the route (the RPC re-validates the bound, D7). Generate `token = base64url(crypto.randomBytes(32))`, `hash = sha256(token)`, call `create_share_token(playlistId, videoId, expires_at, hash)`. Success ⇒ **201** `{ token, url: "/s/<token>", expiresAt }` — the only time plaintext is exposed. Ownership/promoted failure ⇒ coarse **404**. Revoke/list routes are thin authenticated wrappers over their RPCs.

### 4.5 Share-mode render (`share: true` — new additive `renderMagazineHtml` option)

`renderMagazineHtml` gains a `share?: boolean` (today it accepts only `nonce`/`dig`; the new option is additive, so existing render tests are unaffected). `share: true`:
- **Strips** the `<meta name="source-md">` tag **and** the footer `<code>${sourceMd}</code>` element that holds the MD key `NNNNN_slug.md` (the only genuine owner-structure leak — serial number / library size / ordering). The surrounding `<footer>` wrapper prose (which carries no key) may remain; **B22 asserts the MD key string is absent from the output.** Also strips the `<meta name="video-id">` and `<meta name="generator">` tags (low-risk, for cleanliness).
- **Keeps** the doc body — title, channel, source video URL, TL;DR, takeaways, sections, timestamp links — the shared summary's content, not owner-account identity.
- Inherits `dig:false` (no cross-doc nav).

`buildSummaryCsp` is unchanged (referrer control is a response header, not CSP).

## 5. URL Contracts

| Route | Method | Auth | Params | Success |
|---|---|---|---|---|
| `/api/share` | POST | session (owner) | body `{ playlistId, videoId, ttlDays? }` | 201 `{ token, url: "/s/<token>", expiresAt }` |
| `/s/[token]` | GET | **none** (bearer) | path `token` | 200 `text/html` share-mode + `Referrer-Policy: no-referrer`, `Cache-Control: no-store` |
| `/api/share/[id]/revoke` | POST | session (owner) | path `id` | 200 `{ revoked: boolean }` |
| `/api/share/revoke-all` | POST | session (owner) | body `{ playlistId, videoId }` | 200 `{ count }` |

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| B1 | Mint a link | owner POST, owns `(playlist,video)`, summary `promoted` | 201 `{ token, url, expiresAt }`; row stored `sha256(token)` (32 bytes); plaintext once |
| B2 | Mint on unowned/unpromoted doc | doc not owned or not `promoted` | coarse **404**; no row |
| B3 | Mint unauthenticated | POST, no session | **401** |
| B4 | Mint default expiry | `ttlDays` omitted | `expires_at = now()+30d` |
| B5 | Mint never-expiry | `ttlDays: 'never'` | `expires_at = null` |
| B5b | Mint bounded/rejected TTL (route) | `ttlDays` = 0 / negative / non-integer / > 365 | **400**; no row |
| B5c | RPC rejects hostile expiry (trust boundary) | direct RPC `p_expiry` past, or > now()+365d | RPC raises; no row (D7) |
| B6 | Serve a valid link | GET `/s/<token>`, live token, model fresh | **200** share-mode; **no** reserve/Gemini/ledger touch |
| B7 | Serve when model not materialized | live token, model absent | **"not ready"** (503-class); no generation |
| B8 | Serve when model stale (version bump) | live token, `isFresh` false | **"not ready"**; heals after owner next views |
| B9 | Serve expired token | `expires_at < now()` | **404 (coarse)**, before any blob read |
| B10 | Serve revoked token | `revoked_at` set at step 2 | **404 (coarse)**, before any blob read |
| B10b | Revoke/un-promote lands mid-serve | live at step 2, revoked/un-promoted before step 5 | step-5 re-check → **404**; body not emitted (D14) |
| B11 | Serve malformed token | wrong shape/length | **404 (coarse)**, before any DB call |
| B12 | Serve unknown token | well-formed, no matching hash | **404 (coarse)**, before any blob read |
| B13 | Serve after summary un-promoted / deleted | live token, summary no longer `promoted` | **404 (coarse)** (step-3 or step-5) |
| B13b | MD blob lost / corrupt behind promoted | promoted record but MD `get()` null or `parseSummaryMarkdown` throws | **404 (coarse)**; never a 500 leak |
| B14 | Revoke one link | owner POST revoke, owns it | `revoked_at` set; later serve → B10; returns `true` |
| B15 | Revoke someone else's / unknown token | `id` not owned by caller | no change; returns `false` |
| B16 | Revoke-all for a doc | owner revoke-all | every live token revoked; returns count |
| B17 | List links | owner list for own doc | rows `{id, created_at, expires_at, revoked_at}`; **never** `token_hash` |
| B18 | No money on the share path (runtime guarantee) | any share serve (B6–B13) | `spend_ledger` / `serve_model_charge` unchanged; spies assert **zero** `reserve_serve_model` **and** `generateMagazineModel` calls |
| B18b | Static import/RPC guard | share route + `read-model.ts` sources | ESLint `no-restricted-imports` (forbid `serve-doc`/`gemini`/`resolveMagazineModel`/`generateMagazineModel` under `app/s/**` + share helpers) + grep for `reserve_serve_model` / `.rpc(` string → none present |
| B18c | `read-model.ts` graph is generate-free | module graph of `read-model.ts` | never transitively reaches `@/lib/gemini`, `@/lib/gemini-cost`, or `serve-doc` (a static import-graph walk; the `reserve_serve_model` RPC *string* is B18b's grep, not an importable module) |
| B19 | `service_role` scoped read-only | share serve | reads only the one doc's MD + model via a runtime `get`-only wrapper; no write method reachable (D16) |
| B19b | Confused-deputy guard | token owner_id vs resolved owner_id | resolution asserts equality; mismatch → **404** (D15) |
| B20 | CSP present + coherent | any 200 share serve | full nonce CSP; header nonce matches every inline nonce; no `unsafe-*` |
| B21 | No-store + no-referrer | any 200 share serve | `Cache-Control: no-store` **and** `Referrer-Policy: no-referrer` |
| B22 | Share render strips owner-structure | any 200 share serve | MD-key string absent (no `source-md` meta, no footer `<code>` key); no `video-id`/`generator` meta; no cross-doc nav / dig controls; body content retained |
| B23 | Direct RPC bypass blocked | `authenticated` direct `INSERT`/`UPDATE` on `share_tokens` | denied; mutation only via definer RPCs |
| B24 | Hash-at-rest | inspect a stored row | `token_hash` (32 bytes) present; plaintext absent anywhere in DB |

## 7. Testing Strategy

- **Unit** — token gen/hash helper (shape, 32-byte hash, base64url); TTL route contract (omitted→30, `'never'`→null, bounds→400); `readFreshMagazineModel` (ok when fresh, not_ready when absent/stale; spies assert **zero** reserve/generate calls); share-mode render strips the enumerated set (B22 fixtures with `source-md`/`video-id`/`generator` present).
- **Static guards (B18b/B18c)** — ESLint `no-restricted-imports` rule scoped to `app/s/**` + share helper modules; a grep test for the `reserve_serve_model` / `.rpc(` strings in share sources; a module-graph assertion that `read-model.ts` never reaches `@/lib/gemini`.
- **Integration (real DB, `service_role`)** — each RPC: ownership+promoted gate, hash-length CHECK, expiry bound (B5c: past raises; `now()+366d` raises; a route-computed `ttlDays: 365` mint **passes** — the grace-margin boundary, catches TTL-constant drift), revoke-one/all/list (no-hash), direct-INSERT bypass (B23). Serve path on real storage: fresh→200, absent/stale-model→not-ready, **MD blob missing behind promoted→coarse-404**, **corrupt/unparsable MD→coarse-404 (never 500)**, expired/revoked/unknown/malformed→coarse-404-before-blob-read, un-promoted→404, in-flight-revoke/un-promote→404 (B10b).
- **Money invariant (B18)** — share-serve test asserts `spend_ledger` and `serve_model_charge` rows unchanged across B6–B13 **and** runtime spies show zero reserve/Gemini calls, mirroring the 1F-a no-charge seam tests.
- **Isolation (B19/B19b)** — scoped-read test proving reads go through the `get`-only wrapper (no write method callable); owner-B-unreachable-via-owner-A's-token; confused-deputy mismatch → 404.
- **Mock boundary** — Gemini stays mocked at `lib/gemini.ts`; the share path makes zero Gemini calls (asserted).

## 8. Dev-Process Re-Review Triggers

Squarely in the **iterative re-review to convergence** category: a new **capability grant**, **anonymous access**, a **second `service_role` surface**, a **money-adjacent** path, **and** a refactor of already-merged shared 1F-a code (D13, `serve-doc.ts` → new `read-model.ts`). Spec and plan each go through dual adversarial review to convergence. Implementation applies §8 per-task iterative re-review on: the `read-model.ts` extraction (D13), the money-invariant + static-guard task (B18/B18b/B18c), and the `service_role` scoped-read + confused-deputy task (B19/B19b).

## 9. Out of Scope / Follow-ups

- **Owner-facing "manage links" UI** — Sub-project 2 (frontend), consumes `list/revoke` RPCs + `/api/share`.
- **Anonymous-route abuse control (D12):** coarse per-token/IP rate-limit and/or a short `(token_hash, generatorVersion)`-keyed rendered-HTML cache (every hit reaches origin because `no-store`). Generation-free, so not a money hole; an infra-cost/DoS mitigation to land before public launch.
- **`GENERATOR_VERSION`-bump staleness (known limitation):** a version bump makes every live shared link return "not ready" until the **owner** next opens the doc (owner-charged) — D3 forbids share-path generation; recipients get no signal. Follow-up: heal-at-mint or an owner "refresh shares" action.
- **Token-entropy at the DB boundary (accepted residual):** the CHECK enforces 32-byte hash *shape*, not randomness; a direct-RPC `authenticated` caller can hash a weak token, but only self-weakens links to **their own** doc (owner-self-harm, not cross-tenant). Making the RPC generate the token itself is a possible future tightening.
- **Orphaned/stale token rows:** un-promoting/deleting a summary leaves rows (→ 404, harmless); reaping an anon guest-owner cascades their tokens. GC/notification is a follow-up.
- **Path-token log capture (threat-model note):** a token in the URL path is recorded by any reverse proxy / access log — inherent to capability URLs. `Referrer-Policy: no-referrer` blocks cross-origin `Referer` leakage; on-host logs still see it. Accept for this slice.
- **1F-c** — PDF, download, Obsidian export of shared docs.
- **Share of dig-deeper docs** — deferred; share is summary-only.
- **Analytics / view counts** — not needed.

## 10. Success Criteria

1. An owner mints a link to one promoted summary doc; an anonymous holder reads it; a non-holder cannot.
2. No share-serve request (valid, expired, revoked, unknown, not-ready) ever charges the owner, calls `reserve_serve_model`, or calls Gemini — proven by B18 (rows unchanged + zero-call spies), B18b (static import/RPC guard), and B18c (`read-model.ts` graph is Gemini-free).
3. The only privileged surface is a read-only (runtime `get`-only) token-gated `service_role` read of exactly the one doc's blobs, with the confused-deputy owner-match assert (B19/B19b).
4. Expiry, revoke (one + all), and un-promote take effect within one request boundary — including the in-flight re-check (B10b) — and invalid tokens yield oracle-free coarse 404s before any blob read; the RPC bounds `expires_at` at the trust boundary (B5c).
5. Plaintext tokens exist only in the mint response; the DB stores 32-byte hashes only (B24); the share page emits `Referrer-Policy: no-referrer` and strips the owner-structure metadata (B21/B22).
6. `tsc` clean; unit + integration suites green; the spec cleared dual adversarial review to convergence.
