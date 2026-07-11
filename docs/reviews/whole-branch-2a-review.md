# Whole-Branch Review — Stage 2a (Cloud Auth, Shell & Library)

**Reviewer:** Claude (controller-level synthesis) · **Date:** 2026-07-11
**Range:** `master 4d5b597..4c933d4` — 40 commits, 86 files, +5339/−943
**Verdict:** **READY for PR** (per-task dual-reviewed; cross-cutting invariants verified; deferred nits + flags below). Formal Codex+Claude whole-branch dual pass recommended before merge (see Process note).

## Process note
Every one of the 16 tasks was individually dual-reviewed (Codex from coordinator + independent Claude), saved to `docs/reviews/task-2a-*`. The security-critical annotation RPC (T7) got the full **§8 iterative** treatment. This whole-branch pass is a **controller-level cross-cutting synthesis** — the formal Codex+Claude whole-branch dual review was deferred because the account hit a session limit (resets 4:20am). Recommend running `/code-review ultra <PR#>` (or the dual pass at reset) before merge as a final net.

## Cross-cutting invariants — VERIFIED
1. **Schema is additive & minimal:** only 2 new migrations — `0015_video_updated_at_trigger.sql` (BEFORE UPDATE trigger) and `0016_update_video_annotations.sql` (the annotation RPC). No existing migration edited.
2. **`merge_video_data` UNCHANGED** (0 diff lines in `0007`) — the shared merge RPC's set-null semantics preserved; annotation writes go through the dedicated `update_video_annotations` RPC only.
3. **Multi-tenant isolation holds:** `update_video_annotations` is `SECURITY INVOKER SET search_path=public` + `owner_id=auth.uid()` guard + in-SQL key allowlist + `revoke public`/`grant authenticated` (T7 §8-cleared; cross-owner denial proven by real-Supabase tests). All cloud read/write routes: `auth.getUser()` 401 → `UUID_RE` 400 → `resolveOwnedPlaylistKey` (owner-asserted) 404 → **session client only**. No new service-role client reaches user-facing stores.
4. **Local app unchanged:** dual-mode via `STORAGE_BACKEND`; `serveLocal` branches byte-preserved (verified per-task); `LocalApp` = old `app/page.tsx` body + only a `ScopeProvider` wrapper (semantic diff confirms no logic change); the shared leaf components' local requests are identical (route-equivalent). Existing local unit + E2E specs stay green.
5. **Auth flow coherent:** middleware local-no-op short-circuit; `/login` public; cloud `/` gated → `/login`; `/api/*` JSON 401 before page-redirect; anon-provision + `/s`/`/try` preserved; callback `/library`→`/`; `/login` OAuth → callback `?next=/`. 401 from any cloud fetch (incl. sidebar) → `router.replace('/login')`.
6. **Green:** `npx tsc --noEmit` 0; `npm test` 174 suites / 1875 tests; `npx supabase db reset && test:integration` 327 passed / 2 pre-existing skips (migrations 0001→0016 apply clean).

## ⚠️ Flags for the user (before merge / launch)
- **`/s/[token]` anonymous share links** are `authenticated`-classified, so a logged-out share recipient is redirected to `/login` — i.e. **shared links may not open for logged-out users**. This is **pre-existing** and the spec explicitly declared `/s` gating out of scope (§2), and 2a does not change its classification — but it touches the already-shipped share feature. **Verify shared links work for anonymous recipients before launch** (likely needs `/s` added to the public/anon route category — a small follow-up).
- **T16 cloud E2E is documented-SKIPPED** (harness gap: needs a 2nd Playwright web server with `STORAGE_BACKEND=supabase` + seeded session-cookie injection). The cloud flow is otherwise covered by real-Supabase integration tests + component tests. Follow-up: build the harness + un-skip.
- **G8 (Stage 1D):** the fail-closed cloud-Gemini transcribe fallback flag is still off (unrelated to 2a; feature-completeness before launch).

## Deferred nits → backlog (none mask a correctness/security gap)
listPlaylists `created_at` secondary-sort test-strength; `/api/playlists` serveCloud try/catch for `{error}` body; cloud quick-view `[id]`-absent test; `UUID_RE` dedup across routes; **T7 RPC value-domain validation** (allowlists keys not value ranges — own-row only, matches codebase posture); getQuickView local `+`/`%20` encoding (route-equivalent); NoteCell/StarRating fallback error wording; AccountMenu signOut error handling + `aria-controls`; VideoMenu "Watch on YouTube" vs spec "Open"; CloudApp unspecified copy + no retry-on-error affordance; midnight-UTC preseed test flake; design-token `--color-*` alias polish.

## Recommendation
**READY for PR to `master`.** Merge is the user's gate. Suggest the formal dual whole-branch review (`/code-review ultra`) on the PR before merge, and closing the `/s` anon-share question.
