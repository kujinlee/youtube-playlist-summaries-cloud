---
name: frontend-subproject-design-state
description: "FIRES-WHEN: resuming sub-project 2 (frontend) design — Sub-project 2 (frontend) brainstorming state — corrected local+cloud+sync vision, 2a scope, settled decisions, open questions for resume"
metadata:
  node_type: memory
  type: project
  originSessionId: cf75153b-dcc5-4c52-94eb-ed2c1ce13895
---

**CURRENT STATUS (2026-07-11): Stage 2a ✅ (PR #11, 4c0109b) + 2b ✅ (PR #12, 76e0590) + 2c ✅ (PR #13, db5cbfc) ALL MERGED to master.** 2c absorbed the old "2d share+downloads." The 2b/2c auto-merge grant is now SPENT (see [[stage-2-batch-autonomy-plan]]). **Remaining Sub-project 2 work, each its own spec + merge gate in a FRESH session:** (1) cloud doc GENERATION (cloud PDF + deep-dive — a BACKEND slice: Supabase blob storage, durable serverless jobs, deep-dive Gemini charging+guardrails); (2) Stage 3 Sync (local↔cloud newer-wins). Neither is in any standing grant. The detailed 2a narrative below is historical record.

Sub-project 2 (frontend) brainstorming, started 2026-07-10 after Stage 1G merged (PR #10). **Phase: spec USER-APPROVED → automating gates per [[process-conventions]].** Branch `feat/stage-2a-cloud-auth-shell-library` (off master). Spec `docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md`.
**Spec CONVERGED (ee33563), user-approved — dual adversarial review to convergence DONE (4 rounds):** R1 (Codex+Claude) 6 Blocking + 10 High (all codebase-verified: existing middleware.ts not "new"; OAuth callback defaults /library no-route; videos.updated_at column already exists+RPC-maintained so add-data.updatedAt was wrong; field-partitioned merge unsound w/ 1 clock) → v2 (482ac20). R2 all fixed + NEW High N1 (A6/A7 must NOT overload shared merge_video_data — callers write JSON null as set-null; use dedicated update_video_annotations RPC) → v3 (f6b15f4). R3 NEW High I1 (RPC security: v3 sig took client p_owner + playlist_key lookup + floated SECURITY DEFINER = cross-tenant write risk) → v4 pins SECURITY INVOKER + auth.uid() owner + UUID p_playlist_id + SQL allowlist, matches 0007 RPCs (1b1ebb2). R4 spot re-review 0 Blk/0 High both passes → CONVERGED. Reviews: docs/reviews/spec-2a-{codex,claude}-v1.md + spec-2a-v{2,3,4}-rereview.md. **Phase 2 DONE:** plan `docs/superpowers/plans/2026-07-10-stage-2a-cloud-auth-shell-library.md` (v2). Post-Plan Gate dual review (Codex+Claude): 0 Blocking; both confirmed core SOUND (update_video_annotations SQL valid, trigger idempotent, ordering, auth model); 5H+5M all plan-precision, all addressed in v2 (H1 local listPlaylists cloud-only; H2 test path→tests/components; H3 add VideoRow; H4 cloud Playwright project; H5 401→/login; M1 RPC revoke/grant; M2 UUID-format guard 400-not-500; M3 updatedAt test-churn audit; M4 no-videos empty state). Reviews docs/reviews/plan-2a-{codex,claude}.md. Plan v2 commit 3231894.
**Phase 3 SDD IN PROGRESS.** Ledger `.superpowers/sdd/progress.md` (16 tasks; §8 on T1+T7 — both CONVERGED clean). Per-task loop: implementer(sonnet)→dual review(Codex coord + Claude agent)→fix if needed→commit; review docs in docs/reviews/task-2a-N-*.md. **PHASE A COMPLETE (T1–T8, cloud read/write backend): T1 updatedAt trigger 0015; T2 local stamp; T3 listPlaylists; T4 GET /api/playlists; T5 /api/videos cloud; T6 quick-view cloud; T7 update_video_annotations RPC 0016 (§8, SECURITY INVOKER); T8 archive cloud (+ fix: non-object-body 500→400 in both archive & review serveCloud).** HEAD ee4f339. **PHASE B (frontend) NEARLY COMPLETE — T9–T15 ALL DONE, T16 (cloud E2E) IN FLIGHT:** T9 middleware gating+callback fix; T10 scope client (lib/client/api.ts+scope.tsx); T11 /login (pulled forward before T10); T12 page dispatch+LocalApp extraction (byte-identical, proven via diff)+page-session+tokens; T13 PlaylistSidebar; T14 AccountMenu; T15 = T15a (retarget StarRating/NoteCell/VideoQuickView to useScope()+apiClient + LocalApp ScopeProvider, local byte-identical) + T15b (CloudApp full wiring: Suspense+memoized cloud scope+listVideos+empty states+401→/login; VideoMenu cloud allowlist; sidebar-401 fix). HEAD ad02be2. full suite 1875/1875, tsc 0. All per-task dual-reviewed clean (2 severity disagreements adjudicated: T15a Codex Blk/High vs Claude — both functionally non-regressions [route decodes +/%20 identically; error-text fallback-only]; T15b Codex High sidebar-401 gap REAL → fixed). **✅ STAGE 2a COMPLETE & MERGED — PR #11 merged to master (merge commit 4c0109b, 2026-07-11T14:33). Local+remote branch deleted; migrations 0015/0016 on master; master tsc 0.**
All 16 tasks TDD + per-task dual-reviewed. Then the 3 before-merge issues were revisited one-by-one:
(1) ✅ /s anon share — REAL pre-existing bug (middleware redirected logged-out share recipients to /login; route-level tests bypassed middleware). Fixed: /s→PUBLIC_PREFIX (route self-authorizes via share token) + tests. Commit 2957e24.
(2) ✅ T16 cloud E2E — user chose ACCEPT documented-skip (tests/e2e/cloud-library.spec.ts describe.skip; harness = 2nd Playwright webServer STORAGE_BACKEND=supabase + session-cookie injection). BACKLOG: build harness + un-skip.
(3) ✅ Formal Codex+Claude whole-branch dual review RAN (session limit cleared): Codex NOT-READY 1 High (retargeted leaves StarRating/NoteCell/VideoQuickView swallowed UnauthorizedError instead of →/login — cross-task gap per-task reviews missed) + Claude READY 0 Blk/High, 1 Medium (anon /try user couldn't reach /login to upgrade). BOTH FIXED (commit 2ed1b2a: leaves router.replace('/login') on UnauthorizedError; middleware /login redirect gated on !user.is_anonymous) + tests. All money/RLS/isolation/local-preservation invariants verified by both passes. Final: tsc 0, jest 1879. docs/reviews/whole-branch-2a-review.md.
**BACKLOG (post-2a):** cloud E2E harness; minor deferred nits (T7 RPC value-domain validation; /api/playlists try/catch; various test-strength + a11y + copy nits — see whole-branch review doc); Stage 1D G8 live-Gemini gate. **NEXT sub-project slices: 2b cloud ingest (/api/jobs queue+SSE), 2c doc lifecycle (view/generate HTML/PDF/deep-dive), 2d share+downloads UI, Stage 3 Sync (local↔cloud, docVersion-primary+updatedAt comparator).**
**Whole-branch deferred nits (record for final review):** listPlaylists created_at sort test-strength; /api/playlists serveCloud try/catch; quickview [id]-absent cloud test; UUID_RE dedup across routes; T7 RPC value-domain validation (keys allowlisted not value ranges — own-row only); getQuickView local +/%20 encoding (route-equiv); NoteCell/StarRating fallback error wording; AccountMenu signOut error handling + aria; VideoMenu "Watch on YouTube" vs spec "Open"; CloudApp unspecified copy + no retry-on-error; midnight-UTC preseed flake. **PRE-EXISTING/OUT-OF-SCOPE FLAG (surface to user at PR): /s/[token] anon share links are authenticated-classified → logged-out share recipients redirect to /login; verify shared links work for anon before launch (spec declared /s out of scope §2).** Also 1D fail-closed Gemini fallback still off (G8). Tasks #40,41,43 done; #42 in progress.
Key resolved design (v3): updatedAt = surface existing videos.updated_at column via ON UPDATE trigger (whole-record newer-wins, docVersion primary); dedicated annotation RPC (annotation-keys allowlist) leaves merge_video_data untouched; middleware = EXTEND existing (local no-op short-circuit, /login public, cloud / gated→/login, keep anon-provision + /api 401); page.tsx thin server dispatch reads session read-only.

## Corrected product vision (user clarified 2026-07-10 — I had it wrong first)
NOT "cloud replaces/retires local." Instead: **one codebase, two coexisting apps switched by `STORAGE_BACKEND`:**
- **Local app** — single user, filesystem (outputFolder, folder picker, Obsidian vault). KEEP, do not retire.
- **Cloud app** — multi-tenant, Supabase, auth-gated per owner. TO BUILD.
- **Sync bridge:** user can DOWNLOAD cloud→local and UPLOAD local→cloud — files (summary/deep-dive MD+HTML), video metadata (ratings/notes/archived/scores), and configs (settings). Conflict rule: **newer version overrides older** per video.
So `serveLocal`/`serveCloud` dual-branch pattern is a first-class feature, not legacy.

## Key finding: current frontend is a STALE LOCAL-desktop app
Complete + well-tested (~20 component tests, 10 Playwright specs, 5 SSE streams) but built on the OLD local model: filesystem outputFolder, native Mac folder picker (/api/pick-folder), obsidian:// links from disk paths, `create-next-app` layout metadata. **No auth UI at all** (auth/callback route orphaned), no share-token UI, never calls cloud `/api/jobs`.

## Key finding: Sub-project 1 (backend) NOT complete for the READ/LIST surface
Cloud migration built write/generate/serve/share paths but left library reads on the local path. Missing for cloud "sign in → list playlists → open one → see videos+ratings":
1. `MetadataStore.listPlaylists(ownerId)` + SupabaseMetadataStore impl (no owner-scoped playlist listing exists anywhere) — small (~20 lines; RLS auto-scopes).
2. `GET /api/playlists` cloud route (current is filesystem `?root=`) — small.
3. `/api/videos` cloud branch — today 100% local (`getPrincipal(outputFolder)`, fs `recoverOrphanedVideos`, `getStorageBundle()` w/ no client → THROWS in supabase mode). Refactor to serveLocal/serveCloud like html/[id]; `?playlist=<UUID>` → resolveOwnedPlaylistKey → readIndex → reuse sortVideos. Biggest read piece — medium.
4. `/api/videos/[id]/quick-view` cloud branch — small.
5. `/api/videos/[id]/review` cloud branch (rating/note writes; store `merge_video_data` already works) — small.
6. `/api/videos/[id]/archive` — NO cloud impl; use **archived flag** via updateVideoFields({archived}) (cloud analog of local file-move) — medium + schema/design section.
Cloud session plumbing (lib/supabase/server.ts createServerSupabase, client.ts createClient, service.ts) + RLS already exist. Video jsonb carries ratings/personalScore/archived → detail reads ride along in readIndex.

## Data-model for versioning (newer-wins) — RESOLVED comparator (user-confirmed 2026-07-10)
Sync comparator = **lexicographic (docVersion primary, updatedAt tiebreak)**:
- `docVersion{major,minor}` — ALREADY EXISTS; stamped on (re)generation + HTML render (pipeline.ts:266, summary-handler.ts:162, html-doc/ensure.ts:66); NOT touched by rating/note/archive edits. Higher = newer doc.
- `updatedAt` ISO datetime — NEW; bump on EVERY write, both stores; cloud stamps DB-clock server-side in merge_video_data/_bulk/upsert RPCs.
Rule: higher docVersion wins; if equal, newer updatedAt wins. So a doc regenerated with an OLDER generator is still "older" even if more recently generated (lower docVersion loses despite newer updatedAt). **2a adds updatedAt now** → Stage 3 gets both keys, no backfill. Schema/idempotency change → §8 iterative dual review.
Deferred to Stage 3: whole-record replacement vs field-partitioned merge (doc fields by docVersion, annotations personalScore/personalNote/archived by updatedAt — avoids dropping a newer annotation on the lower-docVersion side). 2a stores docVersion+processedAt+updatedAt → either works, no backfill.

## Reshaped roadmap
- **2a** — Cloud auth + shell + library (Phase A backend read-layer items 1–6 + updatedAt field; Phase B frontend). Local app untouched. ← FIRST.
- **2b** — Cloud ingest (playlist URL → /api/jobs queue → SSE progress).
- **2c** — Cloud doc lifecycle (view/generate magazine HTML, PDF, deep-dive; serve-budget/stale UX).
- **2d** — Cloud share tokens + downloads (+ decide Obsidian's fate).
- **Stage 3 (new)** — Sync: local↔cloud upload/download of files+metadata+config, newer-version-wins. Depends on cloud populated (2a–2c).

## Settled decisions (user-confirmed via AskUserQuestion)
- Decompose sub-project; spec **2a first**.
- Audience = **multi-user / open signup** (needs signup flow, first-run empty states, basic account mgmt).
- Auth = **Google OAuth only** (signInWithOAuth → existing /auth/callback).
- **Fold backend read-layer into 2a** (Phase A backend-first, then Phase B UI — one spec).
- Library nav = **playlist sidebar + video list** (maps to per-playlist readIndex).
- Build approach = **C hybrid REVISED**: reuse presentational components (VideoRow, Badge, StarRating, FilterBar, VideoList render, VideoQuickView) + their tests; build cloud shell/auth ALONGSIDE local; do NOT delete local UI.
- Ordering = **cloud first, sync later**; introduce updatedAt/revision field early.

## OPEN QUESTIONS awaiting user (resume here)
Judgment calls I proposed but user pivoted to the vision clarification before answering — reconfirm:
1. Archive = `data.archived` flag (not membership)? [recommended]
2. Keep dual-backend serveLocal/serveCloud (vs cloud-only)? [yes — now confirmed by vision]
3. URL model `/?playlist=<uuid>` query param vs route segment `/p/<uuid>`? [lean query param]
4. "+ New playlist" a stub in 2a (real ingest = 2b)? [yes]
5. Confirm add updatedAt/revision field in 2a.
Then: draft `## UI Design` (wireframe + token table — formalize existing zinc dark theme into semantic tokens), `## URL Contracts`, `## Overlay Dismissal` (account menu dropdown, VideoQuickView, any archive confirm) tables directly into spec doc (dev-process gates). Then writing-plans.

## Key files
Frontend: app/page.tsx (680-line local page), app/layout.tsx (stale metadata), components/* (~19). Auth: lib/supabase/{server,client,service}.ts. Storage: lib/storage/resolve.ts (getStorageBundle/getPrincipalFromSession/getWorkerStorageBundle), lib/storage/supabase/supabase-metadata-store.ts (readIndex by playlist_key; no listPlaylists). Types: types/index.ts:47 VideoSchema. playlists table: migrations/0001 (id UUID pk, owner_id, playlist_key unique-per-owner, unique(id,owner_id)); RLS owner_id=auth.uid() (0002). Cloud route exemplar: app/api/html/[id]/route.ts (serveLocal/serveCloud + resolveOwnedPlaylistKey).

Spec target path when written: docs/superpowers/specs/2026-07-10-stage-2a-cloud-auth-shell-library-design.md
