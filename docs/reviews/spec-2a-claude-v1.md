# Claude (opus) Adversarial Review — Stage 2a spec (round 1)

**Reviewer:** Claude opus (independent) · **Date:** 2026-07-10 · **Target:** spec `8d77978`

## Blocking
- **B1 — `middleware.ts` already exists (Stage 1F-b), spec says "New".** Real file auto-provisions anon sessions for anon-allowed routes (`middleware.ts:18-22`), redirects unauth `authenticated` routes to `/` not `/login` (`:33-35`), returns JSON 401 for `/api/*` (`:25-31`), matcher not env-guarded (`:40`), unconditionally calls `getSupabaseEnv()` which throws on missing vars (`env.ts`). Spec's "no-op in local mode" is false → local 500s. A naive "redirect app routes to /login" would convert `/api` 401s to 302s and break every fetch. **Fix:** treat middleware as existing-to-extend; enumerate `route-categories.ts` model; add local-mode short-circuit on `STORAGE_BACKEND !== 'supabase'`; preserve anon-provision branch.
- **B2 — `updatedAt` doesn't surface into `Video`.** RPCs bump the relational `videos.updated_at` **column** (`0001:29`; `0007:94,117,61,68`; `0009:152`), but `readIndex` selects only `data` jsonb (`supabase-metadata-store.ts:22-33`) → new `data.updatedAt` absent on every cloud read. `upsertVideo` does `.update({data})` without bumping the column (`:83-91`); no ON UPDATE trigger. **Fix:** one mechanism — either every write RPC injects `data || jsonb_build_object('updatedAt', now())`, OR `readIndex` surfaces the `updated_at` column into the returned `Video`. (Recommended below: column + ON UPDATE trigger, surfaced on read.)

## High
- **H1 — cloud cannot CLEAR a rating/note.** Local maps `null`/`""`→`undefined` to delete (`review route:54-61`); cloud A6 sends that to `merge_video_data`, which is jsonb `||` only (`0007:88-95`) and can't delete a key, and `undefined` strips on `JSON.stringify` → `{}` → no-op. §9 advertises `personalScore:…|null` (null=clear). **Fix:** delete path — JSON-null sentinel + RPC `data - 'personalScore'`; enumerated-behaviors row + test.
- **H2 — post-login `/library` 404.** Callback defaults `next ?? '/library'` (`callback:19`); no `app/library` route. §9 login sets `redirectTo` with no `next`. **Fix:** callback default `/` or login passes `?next=/`; pin one destination.
- **H3 — `/login` unreachable/loops.** `classifyRoute` returns `authenticated` for anything outside `PUBLIC_EXACT=['/','/about']`, `/auth/*`, `/try` (`route-categories.ts:5-13`); spec never adds `/login`. Unauth `/login` → redirected away. **Fix:** add `/login` to `PUBLIC_EXACT`; spec the two middleware rules; redirect-loop test.
- **H4 — `/` is `public`, so the described gate can't work.** `PUBLIC_EXACT` includes `/` (`route-categories.ts:3`); cloud shell is at `/` (§3.1) → unauth cloud user renders `CloudApp` then 401s on `/api/playlists` (auth-shell flash; not a leak). Local must keep `/` public. **Fix:** mode-aware `classifyRoute` (cloud `/`=authenticated, local `/`=public) OR drop the "middleware redirects `/`→`/login`" claim and accept client-redirect-on-401.
- **H5 — "stamp updatedAt on every write" foils the field-partitioned merge it claims to preserve.** `reconcile_membership` writes `archived` + bumps time (`0007:61,68`); `persist_summary` bumps it (`0009:152`) → a machine write makes a user's earlier manual archive look older. Single clock can't be both doc-recency and annotation-recency. **Fix:** commit to whole-record, OR annotations need own per-field clock; record as known limitation.

## Medium
- **M1 — archive divergence (Sync hazard).** Local archive moves files + clears cached HTML (`archive.ts:99-108`); cloud flips flag. Sync setting `archived:false` on local wouldn't move files back → inconsistent local state. Flag as Stage-3 hazard.
- **M2 — cloud quick-view drops availability gate.** Local 404s unless `summaryMd && tldr` (`quick-view route:27`); A5 would 200 with empty fields. **Fix:** match guard or state cloud behavior.
- **M3 — terminology:** `updated_at` (column) vs `updatedAt` (Video field); `scope`/`principal`/`indexKey`/`playlist_key`/UUID used interchangeably. Pin each to one layer.
- **M4 — `listPlaylists` orders by nullable `playlist_title`** (`0001:15`; untitled from `resolvePlaylistId` `:164-167`) → blank rows, unstable order. **Fix:** empty-title display + stable secondary sort (`created_at`).

## Low
- **L1** — `app/page.tsx` is `'use client'` (`:1`); §3.1 dispatch is a real client-boundary refactor. Call out the `'use client'` relocation.
- **L2** — §12 must require a cross-owner-denial test per route (owner B, valid UUID they don't own), not just "unknown UUID".
- **L3** — `/s/*` (share, anon) falls through to `authenticated` in `classifyRoute`; any route-categories edit must not break it.

**Clean (explicitly fine):** `service_role` server-only (`service.ts:8-9`); `getWorkerStorageBundle` UUID-bound ownership assert; the `serveLocal`/`serveCloud` exemplar; A4 skipping `recoverOrphanedVideos`.

**Assessment:** 2 Blocking + 5 High, all codebase-verified; converges with Codex on middleware/callback/updatedAt/merge. Round 1; re-review after fixes.
