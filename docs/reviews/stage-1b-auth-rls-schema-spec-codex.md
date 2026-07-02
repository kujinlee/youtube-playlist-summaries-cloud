# Codex Adversarial Review — Stage 1B Auth + RLS Schema Spec

**Reviewer:** Codex (frontier), fresh session
**Date:** 2026-07-02
**Target:** `docs/superpowers/specs/2026-07-02-stage-1b-auth-rls-schema-design.md`
**Verdict:** 4 Blocking, 8 High, 4 Medium, 2 Low. All addressed in spec v2.

## BLOCKING
- **B1 — Cross-tenant video injection via mismatched `playlist_id`/`owner_id` (§5).** RLS checks `videos.owner_id` but `playlist_id` FKs independently; attacker inserts `owner_id=self, playlist_id=victim` → FK+RLS pass → cross-tenant PK collision / DoS. → Composite FK `videos(playlist_id, owner_id)` → `playlists(id, owner_id)` (+ `unique(playlists.id, owner_id)`); test spoofed combos.
- **B2 — Profile provisioning hand-waved → first-write race (§4/§5).** `owner_id` FKs `profiles` but no authoritative creation path. → `handle_new_user` trigger `after insert on auth.users` creates the `profiles` row (sets `is_anonymous`); single source, runs before any app write.
- **B3 — Principal contract contradiction (§5 vs principal.ts).** `principal.ts`: "cloud: outputFolder unused"; 1B: `outputFolder → playlist_key`. → Redefine `Principal.outputFolder` as "the index selector" (local: path; cloud: playlist_key); update the JSDoc as a 1B code touch.
- **B4 — 1B defers tables the parent requires before adapter writes (§1 vs parent §7.1/§10).** → Redefine ordering: **1C = `SupabaseMetadataStore` only**; `artifacts`/`jobs`/`usage_counters`/`share_tokens` land in their own stages, each following 1B's RLS convention. Parent's "1C adapter bundle" is decomposed into per-contract stages (matches the sibling-contract plan).

## HIGH
- **H1/H2 — service_role wording overstates FORCE; boundary unenforceable (§3/§7).** → Distinguish `FORCE RLS` (table-owner) from `BYPASSRLS`/service_role; service client lives in a server-only module with a runtime guard + a static test that no route handler / `'use client'` imports it.
- **H3 — `readIndex` absent-row semantics missing (§5).** → Missing playlist ⇒ return an **empty `PlaylistIndex`** matching the local ENOENT-tolerant behavior (videos: []).
- **H4 — Write semantics undefined (§5).** → Specify per method: `writeIndex` upserts the playlist + makes the video set exactly match (upsert present, delete absent) transactionally; `upsertVideo` upserts one; `updateVideoFields` JSONB-merges one. All in a transaction.
- **H5 — JSONB has no identity/shape tie (§5).** → DB `CHECK (data->>'id' = video_id)`; adapter validates `data` against `VideoSchema` before write.
- **H6 — Video ordering undefined (§5).** → Add `position int`; `readIndex … ORDER BY position`; writes set position from the array index (preserves local array order).
- **H7 — RLS tests miss the FK attack (§7).** → Add mixed-tenant (attacker owner_id + victim playlist_id) insert test.
- **H8 — UPDATE/DELETE expectations ambiguous (§7).** → Specify per op: invisible-row UPDATE/DELETE ⇒ 0 rows affected; a visible write that would change `owner_id` ⇒ `WITH CHECK` error. Test visibility and mutation independently.

## MEDIUM
- **M1 — Anonymous lifecycle/cleanup unspecified (§4/§9).** → Document a retention/TTL-cleanup gap as an explicit pre-public gate (not built in 1B).
- **M2 — Middleware/session vague (§3/§4).** → Define route categories (public / anon-allowed / authenticated), callback cookie exchange, and how server components + route handlers get the refreshed session.
- **M3 — `playlist_key` derivation (§9, now decided).** → YouTube list-id; extract `list=`; reject non-playlist/malformed URLs; raw list-id is the key.
- **M4 — Test client role (§7).** → Data ops use the **anon key + the user's JWT**; admin API only for user creation.

## LOW
- **L1 — `is_anonymous` user-writable (§5).** → Trigger-set; a `BEFORE UPDATE` guard prevents client changes; app never trusts a client-set value.
- **L2 — Storage-key convention in 1B success criteria but untested (§6/§8).** → Remove from 1B success criteria; keep as a documented convention for BlobStore.

## Disposition
All Blocking/High addressed in spec v2; Mediums/Lows folded in. User decisions applied: list-id key, anon-upgrade out of scope, plain SQL migrations.
