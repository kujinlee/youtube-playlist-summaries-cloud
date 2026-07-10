# Stage 1F-b — Share Tokens (anonymous read of one summary doc, cloud)

**Status:** 🟡 **design DRAFT (v1)** — brainstormed and design-approved by the user 2026-07-10; not yet through grill-with-docs / dual adversarial review. **Branch:** TBD (`feat/stage-1f-b-share-tokens`).

> **Design in one paragraph:** a doc owner mints an opaque, high-entropy **capability link** to **one** promoted summary doc. Anyone with the link reads the rendered summary HTML — no login, no owner money spent, no access to anything else the owner owns. The share path **only reads** an already-materialized magazine model (never generates, never charges); the sole new privileged surface is a read-only, token-gated `service_role` fetch of exactly the one doc's blobs. **Next: grill-with-docs → dual adversarial review to convergence → user spec-approval → `writing-plans`.**

**Predecessor:** Stage 1F-a (authorized, lazy-materialized summary-HTML serving, PR #7, merged `288f591`). This slice reuses its render/CSP stack, its magazine-model store, and its money-path invariants unchanged.
**North-star:** `docs/superpowers/specs/2026-07-01-cloud-publishing-architecture-design.md` §5 (print & share), §7 (RLS + storage-key isolation).
**Sibling slices:** 1F-b = share tokens (this doc); 1F-c = downloads / PDF / Obsidian export.

---

## 1. Purpose

Let a summary-doc owner grant **read-only, unauthenticated** access to **one** rendered summary HTML doc by handing out a link. The link is a bearer capability: whoever holds it can read that one doc and nothing else. The owner can set an expiry and revoke links at any time. Anonymous share traffic must be **structurally incapable of spending the owner's money**.

**In scope (backend):** the `share_tokens` schema + RLS, the mint/revoke/list definer RPCs, and the anonymous share-serve route. **Out of scope:** the owner-facing "manage my links" UI (Sub-project 2, frontend), and every 1F-c concern (PDF, download, Obsidian).

## 2. Background — why a share viewer hits three walls today

The 1F-a serve path is owner-only end to end, by three independent mechanisms:

1. **Session gate** — `app/api/html/[id]/route.ts` calls `supabase.auth.getUser()` and returns **401** with no session.
2. **RLS + owner assert** — the playlist row, the index, and every blob are gated by `split_part(name,'/',1) = auth.uid()` (storage RLS, `0007`) and an explicit owner-assert (`resolveOwnedPlaylistKey`). A non-owner sees **404**.
3. **Money RPC** — `reserve_serve_model` (`0012`) derives the owner from `auth.uid()` internally and returns `denied` to any non-owner, so generation is impossible for anyone but the owner.

A share viewer is, by definition, **not the owner**, so all three walls block them. 1F-b introduces a *parallel* serve path with a **different trust model** — a bearer capability token instead of a session — and must re-establish the money and isolation guarantees for that path from scratch, because none of the three walls above protect it.

**The consequence that drives the whole design:** the doc's bytes (summary MD + cached magazine model) live in owner-`service_role`-gated storage. There is **no anon-RLS path** to them (confirmed against `0007`: only the owner's own `auth.uid()` segment or `service_role` can read). Serving a shared doc therefore *requires* a `service_role` read — the design's job is to make that read minimal, read-only, and token-gated.

## 3. Decisions

| # | Decision | Rationale |
|---|---|---|
| D1 | **Share unit = one `(playlist, video)` summary doc** per token. | Smallest surface; mirrors 1F-a's per-request serve. Whole-playlist / doc-set sharing is YAGNI for this slice. |
| D2 | **The share path never generates and never charges.** It reads an already-materialized model only. | Anonymous traffic is structurally incapable of spending owner money. No `reserve_serve_model`, no Gemini, no `spend_ledger` touch on this path. |
| D3 | **Serve-if-fresh, else "not ready."** If the model is absent or stale (`isFresh` false), return a coarse not-ready — never generate. | The owner materializes by viewing the doc once (normal 1F-a path, charged to the owner). Keeps a single freshness source of truth (the owner's live model blob). |
| D4 | **Read auth = token-gated, read-only `service_role` fetch on a dedicated share route.** | The only mechanism that can read owner-gated blobs (D2 rules out generation, storage RLS rules out anon). Second privileged surface in the system, tightly bounded: read-only, one doc, only after the token validates. |
| D5 | **Opaque 256-bit random token**, base64url, in the URL. **Not a JWT.** | Revocation needs a DB row regardless, so a self-contained signed token buys nothing. High entropy ⇒ not enumerable. |
| D6 | **Token stored SHA-256-hashed at rest; plaintext generated in the Next route and shown once.** | A DB leak cannot hand out live links. Plaintext never transits or rests in Postgres (the route hashes before calling the mint RPC). |
| D7 | **Expiry: owner-set at mint (default 30 days; `never` allowed).** Enforced in the serve lookup. | Safe-by-default (links auto-die) with flexibility. |
| D8 | **Revocation: multiple live tokens per doc; revoke-one + revoke-all-for-doc.** | Per-recipient links, targeted kill without breaking other recipients. |
| D9 | **All writes go through `SECURITY DEFINER` RPCs; `share_tokens` is `force`-RLS, `service_role`-only grants.** No direct `INSERT/UPDATE` for `authenticated`. | Same discipline as `enqueue_job` / `serve_model_charge`: the owner-and-`promoted` check lives in one place and can't be bypassed. |
| D10 | **Share render is "share-mode": `dig:false`, nav / owner / playlist identity stripped**, nonce CSP, `Cache-Control: no-store`. | A link leaks nothing but the one doc's body; a revoked link can't be served from a CDN/browser cache. |
| D11 | **Oracle-free coarse denial:** invalid / expired / revoked / unpromoted all return the same **404**, *before any blob read*. | No enumeration or existence oracle; invalid tokens cost nothing. |
| D12 | **Rate-limiting the anonymous route is a documented follow-up, not a first-slice blocker.** | Reads are generation-free and cheap; token entropy blocks guessing. Recorded in §9. |

## 4. Architecture

### 4.1 Schema — `share_tokens` (new migration `00NN_share_tokens.sql`)

```sql
create table share_tokens (
  id            uuid primary key default gen_random_uuid(),
  token_hash    bytea not null unique,                 -- sha256(plaintext); plaintext never stored (D6)
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

### 4.2 RPCs (all `SECURITY DEFINER set search_path = public`, owner from `auth.uid()` internally, granted to `authenticated`)

- **`create_share_token(p_playlist_id uuid, p_video_id text, p_ttl_days int, p_token_hash bytea) returns timestamptz`**
  Derive `v_owner := auth.uid()`; raise if null. Verify `(p_playlist_id, p_video_id)` is owned by `v_owner` **and** the summary artifact `status = 'promoted'` (same predicate as `reserve_serve_model`); else `raise exception` → route maps to a coarse **404** (no existence leak; never 403, which would confirm the doc exists). `p_ttl_days`: null/`0` ⇒ `expires_at = null` (never); else `expires_at = now() + make_interval(days => p_ttl_days)`. Insert the row; return `expires_at`. **The plaintext token and its hash are produced in the Next route** — this RPC only ever sees `p_token_hash`.
- **`revoke_share_token(p_id uuid) returns boolean`** — `update share_tokens set revoked_at = now() where id = p_id and owner_id = auth.uid() and revoked_at is null`; return whether a row changed.
- **`revoke_all_share_tokens(p_playlist_id uuid, p_video_id text) returns int`** — revoke every live token for that owned doc; return the count.
- **`list_share_tokens(p_playlist_id uuid, p_video_id text) returns table(id uuid, created_at timestamptz, expires_at timestamptz, revoked_at timestamptz)`** — owner-scoped; **never returns `token_hash`**. Backend RPC now; the UI consumer is Sub-project 2.

### 4.3 Share-serve route — `app/api/share/[token]/route.ts` (anonymous)

Ordered so invalid tokens cost nothing (D11):

1. **Shape-validate** the path token (base64url, expected length). Malformed ⇒ **404** (coarse), before any DB call.
2. `hash = sha256(token)`. Build a **`service_role` client** (the one privileged surface). `SELECT owner_id, playlist_id, video_id FROM share_tokens WHERE token_hash = hash AND revoked_at IS NULL AND (expires_at IS NULL OR expires_at > now())`. No row ⇒ **404 (coarse)**, *before any blob read*.
3. Resolve the doc for the owner (`service_role`): read the playlist key + index, find the video, assert `summaryMd.status = 'promoted'`, get `md_key`. Not promoted / video gone ⇒ **404**.
4. **`service_role` read** MD blob → `parseSummaryMarkdown` → titles. Read the model envelope via `readModelEnvelope(ownerPrincipal, base, serviceRoleBlobStore)`. Absent or **not `isFresh`** ⇒ **"not ready"** (503-class), **no generation** (D2/D3).
5. Render **share-mode**: `renderMagazineHtml(parsed, model, { nonce, dig: false, share: true })` — the `share` flag strips cross-doc nav, owner, and playlist identity (D10). Respond **200** `text/html` with `Content-Security-Policy: buildSummaryCsp(nonce)` and `Cache-Control: no-store`.

The `ownerPrincipal` is constructed for the owner's `owner_id` + resolved playlist key (so `service_role` `objectKey` addresses the owner's storage segment), mirroring how the worker's `resolveServiceBundle` builds a `service_role` principal off-session.

### 4.4 Mint route — `POST /api/share` (authenticated owner)

Session client; `getUser()` → `ownerId` (401 if none). Body: `{ playlistId, videoId, ttlDays? }`. Generate `token = base64url(crypto.randomBytes(32))`; `hash = sha256(token)`. Call `create_share_token(playlistId, videoId, ttlDays ?? 30, hash)`. On success return **201** `{ token, url, expiresAt }` — **the only time the plaintext is exposed**. Ownership/promoted failure ⇒ coarse **404**. (Revoke/list routes are thin authenticated wrappers over their RPCs; their UI lives in Sub-project 2.)

## 5. URL Contracts

| Route | Method | Auth | Params | Success |
|---|---|---|---|---|
| `/api/share` | POST | session (owner) | body `{ playlistId, videoId, ttlDays? }` | 201 `{ token, url: "/s/<token>", expiresAt }` |
| `/s/[token]` (or `/api/share/[token]`) | GET | **none** (bearer token) | path `token` | 200 `text/html` (share-mode render) |
| `/api/share/[id]/revoke` | POST | session (owner) | path `id` | 200 `{ revoked: boolean }` |

(Revoke-all and list route shapes finalized during planning; RPCs are specified in §4.2.)

## 6. Enumerated Behaviors

| # | Behavior | Trigger | Expected |
|---|---|---|---|
| B1 | Mint a link | owner POST, owns `(playlist,video)`, summary `promoted` | 201 `{ token, url, expiresAt }`; row stored with `sha256(token)`; plaintext returned once |
| B2 | Mint on unowned/unpromoted doc | owner POST for a doc not owned, or owned but not `promoted` | coarse **404**; no row written; no existence leak |
| B3 | Mint unauthenticated | POST with no session | **401** |
| B4 | Mint default expiry | `ttlDays` omitted | `expires_at = now()+30d` |
| B5 | Mint never-expiry | `ttlDays` null/0 | `expires_at = null` |
| B6 | Serve a valid link | GET `/s/<token>`, live token, model fresh | **200** `text/html`, share-mode render; **no** reserve/Gemini/ledger touch |
| B7 | Serve when model not materialized | live token, model absent | **"not ready"** (503-class); **no generation** |
| B8 | Serve when model stale (version bump) | live token, `isFresh` false | **"not ready"**; heals after the **owner** next views (owner-charged) |
| B9 | Serve expired token | `expires_at < now()` | **404 (coarse)**, before any blob read |
| B10 | Serve revoked token | `revoked_at` set | **404 (coarse)**, before any blob read |
| B11 | Serve malformed token | wrong shape/length | **404 (coarse)**, before any DB call |
| B12 | Serve unknown token | well-formed but no matching hash | **404 (coarse)**, before any blob read |
| B13 | Serve after summary un-promoted / deleted | live token but summary no longer `promoted` | **404 (coarse)** |
| B14 | Revoke one link | owner POST revoke, owns the token | `revoked_at` set; subsequent serve → B10; returns `true` |
| B15 | Revoke someone else's / unknown token | revoke `id` not owned by caller | no change; returns `false`; no leak |
| B16 | Revoke-all for a doc | owner revoke-all | every live token for that doc revoked; returns count |
| B17 | List links | owner list for own doc | rows `{id, created_at, expires_at, revoked_at}`; **never** `token_hash` |
| B18 | No money on the share path | any share serve (B6–B13) | `spend_ledger` / `serve_model_charge` unchanged; no `reserve_serve_model` call |
| B19 | `service_role` scoped read-only | share serve | only the one doc's MD + model read; no write; no other owner's objects reachable |
| B20 | CSP present + coherent | any 200 share serve | full nonce CSP; header nonce matches every inline nonce; no `unsafe-*` |
| B21 | No-store caching | any 200 share serve | `Cache-Control: no-store` |
| B22 | Share render leaks nothing extra | any 200 share serve | no cross-doc nav, no owner id, no playlist name/id, no dig controls in output |
| B23 | Direct RPC bypass blocked | `authenticated` attempts direct `INSERT`/`UPDATE` on `share_tokens` | denied (no grant/policy); mutation only via definer RPCs |
| B24 | Hash-at-rest | inspect a stored row | `token_hash` present; plaintext token absent anywhere in DB |

## 7. Testing Strategy

- **Unit** — token generation/hashing helper (shape, entropy length, deterministic hash); `isFresh` reuse; share-mode render strips nav/identity (fixtures with and without cross-doc nav data).
- **Integration (real DB, `service_role`)** — each RPC: ownership+promoted gate, expiry math, revoke-one / revoke-all / list (no-hash), direct-INSERT bypass denied (B23). Serve path against real storage: fresh→200, absent/stale→not-ready, expired/revoked/unknown/malformed→coarse-404-before-blob-read, un-promoted→404.
- **Money invariant** — a share-serve test asserts `spend_ledger` and `serve_model_charge` rows are **unchanged** across B6–B13 (B18) — the anti-charge proof, mirroring the 1F-a no-charge seam tests.
- **Isolation** — a `service_role` scoped-read test proving the share route reads only the token's one doc, and an owner-B-can't-be-reached-via-owner-A's-token test.
- **Mock boundary** — Gemini stays mocked at `lib/gemini.ts`; the share path must make **zero** Gemini calls (asserted).

## 8. Dev-Process Re-Review Triggers

This slice is squarely in the **iterative re-review to convergence** category (`dev-process.md` → Adversarial Review): a new **capability grant**, **anonymous access**, a **second `service_role` surface**, and a **money-adjacent** path. The spec and the plan each go through grill-with-docs → dual adversarial review, re-reviewed until a round returns no new Blocking/High. Implementation applies §8 per-task iterative re-review on the money-invariant task (B18) and the `service_role` scoped-read task (B19).

## 9. Out of Scope / Follow-ups

- **Owner-facing "manage links" UI** — Sub-project 2 (frontend), consumes `list/revoke` RPCs + `/api/share`.
- **Anonymous-route rate-limiting** (D12) — reads are generation-free and cheap; recorded as a follow-up.
- **1F-c** — PDF, download, Obsidian export of shared docs.
- **Share of dig-deeper docs** — cloud dig-deeper is deferred; share is summary-only.
- **Analytics / view counts** on shared links — not needed for the capability.

## 10. Success Criteria

1. An owner can mint a link to one promoted summary doc; an anonymous holder reads it; a non-holder cannot.
2. No share-serve request (valid, expired, revoked, unknown, or not-ready) ever charges the owner or calls Gemini (B18 proven by test).
3. The only privileged surface on the share path is a read-only, token-gated `service_role` read of exactly the one doc's blobs (B19).
4. Expiry and revoke (one + all) take effect immediately on the serve path; invalid tokens yield oracle-free coarse 404s before any blob read.
5. Plaintext tokens exist only in the mint response; the DB stores hashes only (B24).
6. `tsc` clean; unit + integration suites green; the spec cleared dual adversarial review to convergence.
