# Whole-Branch Review — Stage 2a (Cloud Auth, Shell & Library)

**Reviewers:** Codex (gpt-5.5) + Claude (opus), independent · **Date:** 2026-07-11
**Range:** `master 4d5b597..HEAD`
**Verdict:** **READY after fixes** — formal dual whole-branch review run; 1 High (Codex) + 1 Medium (Claude) found and FIXED; all money/RLS/local invariants hold.

## Process note
Every one of the 16 tasks was individually dual-reviewed (Codex + Claude), saved to `docs/reviews/task-2a-*`; the annotation RPC (T7) got the full **§8 iterative** pass. The **formal Codex + Claude whole-branch dual review** then ran (after the session limit reset), scoped to cross-cutting invariants + the `/s` fix.

## Formal whole-branch dual-review findings
- **Codex → NOT-READY, 1 High:** the branch-level invariant "any cloud `UnauthorizedError` → `/login`" (spec §11) was incomplete — `CloudApp`/`PlaylistSidebar` redirect, but the retargeted leaf components **swallowed** it (`StarRating` silent rollback, `NoteCell` inline error, `VideoQuickView` "not yet generated"). Verified real. **→ FIXED:** the 3 leaves now `router.replace('/login')` on `UnauthorizedError` before generic handling + tests.
- **Claude → READY, 0 Blocking/0 High; 1 Medium:** anonymous (`/try`) users are locked out of `/login` — the `/login`→`/` redirect fires for any user incl. anon, so an anon can't upgrade to a real account (open-signup product gap). **→ FIXED:** gate the redirect on `user && !user.is_anonymous` + test. (Claude missed the leaf-401 gap Codex caught — reconciled: Codex's finding governs, controller-verified.)
- **Claude Low (accepted):** L1 cloud E2E documented-skip (accepted, backlog); L2 `types/index.ts` `updatedAt` comment imprecise (cosmetic); L3 no CI config for the integration runner (pre-existing).

## Both passes independently VERIFIED (invariants hold)
- Money/RLS: all 5 cloud routes = session client + getUser 401 + UUID guard + `resolveOwnedPlaylistKey` owner-assert 404; `0007`/`merge_video_data` diff **empty**; `0016` RPC INVOKER + `auth.uid()` + SQL allowlist + grant-authenticated; **no service-role into user-facing stores**; no cross-owner path.
- Local app: `LocalApp` == old `app/page.tsx` body + only the `ScopeProvider` wrapper (byte-identical logic); shared leaves' local requests unchanged.
- Auth flow + the new `/s` fix boundary-safe (`/settings` stays authenticated; `/s/<token>` public; route self-authorizes via token).
- Cross-task: memoized scope (no VideoQuickView refetch loop), single Suspense boundary, `updated_at` trigger + RPC + `readIndex` surfacing + `stripComputed` interact correctly, migration 0015→0016 order correct.

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
**READY to merge.** Formal Codex + Claude whole-branch dual review complete; the one High (leaf-401) + one Medium (anon-`/login`) were fixed (commit `2ed1b2a`), and the `/s` anon-share bug fixed (commit `2957e24`). All money/RLS/isolation/local-preservation invariants verified across the 16 tasks by both passes. Post-fix: `tsc` 0, `npm test` 174 suites / 1879 tests. Remaining items are accepted backlog (cloud E2E harness; minor nits) — none block merge.
