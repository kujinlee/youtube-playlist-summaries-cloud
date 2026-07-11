# Dual Review — Stage 2a Task 9 (middleware auth gating + callback fix)

**Date:** 2026-07-11 · **Diff:** `ee4f339..036d560`

## Codex (gpt-5.5) — FAIL/Changes-needed (on sequencing) · 0 High beyond the one item
Verified OK: local no-op before `getSupabaseEnv()`; `/api/*` JSON 401 fires BEFORE the page→`/login` redirect (`middleware.ts:42` before `:51`); no `/login` loop; cloud-only `/` override (classifyRoute `/` stays public); `/try` anon-provision + `/s` classification preserved; callback `/library`→`/` (no caller relied on old default); the `middleware-api-401` test change forces cloud mode without weakening. Ran middleware-2a 14/14, auth-callback 3/3.
- **"Blocking" (reframed → sequencing):** `/login` is middleware-public but `app/login/page.tsx` doesn't exist yet → unauth redirect lands on 404. **This is T11's deliverable, not a T9 defect** (see Claude M1). Resolution: build `/login` next.

## Claude (opus) — Spec PASS · Approved · 0 Critical/Important
Full branch-order trace confirms all 7 edits correct and loop-free; `classifyRoute` has exactly one caller; test integrity verified (no weakened assertions; local-no-op test proves no-throw via `getSupabaseEnv`/`getUser` `not.toHaveBeenCalled` + 200; no existing test asserted the old `/library` default).
- **M1 (Minor, sequencing):** `/login` page doesn't exist until T11 — expected SDD ordering, not a T9 defect. → build T11 next.
- **M2 (awareness → whole-branch/backlog):** `/s/[token]` (anonymous share) is `authenticated`-classified, so logged-out share recipients are redirected (target shifted `/`→`/login`). Pre-existing + spec-declared out-of-scope (design.md:54,333); T9 doesn't change classification. **Verify shared links open for logged-out recipients before launch.**
- **M3 (awareness → T11/whole-branch):** an anon user (via `/try`) counts as `user`, so `/login`→`/` — an anon user can't reach Google sign-in to upgrade. Per-spec (N5 + authed-/login→/). Primary signup (no session) reaches `/login` fine; only the anon-then-upgrade path is gapped.

## Disposition
T9 code is **correct** — both passes agree 0 real Critical/Important/High. The `/login`-missing is task sequencing (T11), not a T9 defect → **T9 complete; T11 (login page) pulled forward as the next task** to close the redirect target. M2/M3 flagged to user + carried to whole-branch. Impl `036d560`: RED 8/14→GREEN 14/14, npm test 1817, integration 327/329, tsc 0.
