---
name: cloud-dig-deeper-frontend-state
description: "FIRES-WHEN: resuming or citing the cloud dig-deeper frontend slice (PR #20) — Cloud dig-deeper FRONTEND slice — ✅ MERGED to master (PR #20, merge commit a4c251c, 2026-07-15); dual-reviewed CLEAN (0B/0H); branch deleted"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**Cloud "Dig deeper" FRONTEND affordance** — makes the merged cloud dig serving slice ([[cloud-dig-serving-branch-state]], PR #19) reachable + the cloud-aware POST trigger usable. Implements §14.3 of the dig-generation spec.

**STATUS (2026-07-15): ✅ MERGED to master — PR #20, merge commit `a4c251c` (merge-commit strategy, preserves review-convergence trail). Branch `feat/cloud-dig-deeper-frontend` deleted (local + remote). Full suite 2298/2298 + golden + tsc 0 + integration green at merge.** Slice done. Residual follow-up (not a blocker): browser-level Playwright cloud e2e (load dig doc under real CSP, click trigger — the one gap both reviewers flagged).

**Full gate trail (all committed on branch):** Spec `a6fca5b` (approved). Plan `044212d`; Post-Plan dual review v1 `e53ae0f` (1B+3H fixed), v2 `8c4b316` (0B/0H converge). SDD T1-T6: digHref `ff666d2` · VideoMenu `c7dd12b` · nav cloud engine `37d6b8f` (NAV_SCRIPT untouched) · render cloud mode `ba231af` (byte-identity proven via worktree-regenerated golden) · route interactive+profiles-isAnon `03e161e` · integration `be18af6`. **Whole-branch dual review: v1 `be18af6` found 2 Blocking (one from EACH reviewer, both emergent): CSP `buildSummaryCsp` had no connect-src → interactive doc's fetches browser-blocked → feature inert; loadDigForServe zero-dug→404 → "open to start digging" entry path dead. Both fixed `e2ffc8f` (new buildDigCsp + connect-src 'self'; zero-dug returns ok dug:[]). v2 re-review CONVERGED 0B/0H `205ee05` — both fixes verified genuine.** Reviews: `docs/reviews/whole-branch-cloud-dig-deeper-frontend-v1-review.md` + `-v2-rereview.md`.

**NEXT (human gate):** merge decision. Recommended: push → PR → merge via `gh --repo kujinlee/youtube-playlist-summaries-cloud`; per `superpowers:finishing-a-development-branch`. Local-only working-tree files to NOT commit: `supabase/config.toml`, `docs/local-validation-findings.md`. Residual follow-up (not a blocker): browser-level Playwright cloud e2e (load dig doc under real CSP, click trigger — the one gap both reviewers flagged). Local Supabase stack is currently UP (used for the integration test).

**Key plan-review fixes baked in (don't regress):** B1 isAnonymous MUST read `profiles.is_anonymous` fail-closed (`profile?.is_anonymous !== false`) NOT `user.is_anonymous` (unreliable per POST route comment dig/[sectionId]/route.ts:47-53); serve route has `supabase`+`user` in scope (html/[id]/route.ts:42-43), profiles read inside try, `.single()` returns {data:null} on error (no 500, fail-closed→disabled). H1 assert `class="dig-expand-all"` not bare token (token in kept CSS). H2 swapDugSection throws unless section exists AND data-dug==="true". H3 test EXECUTES shipped DIG_CLOUD_SCRIPT via new Function in jsdom. M3 commit pre-change render golden BEFORE editing renderer. M4 gate dig-refresh off in cloud (`&& !cloud`). Separate `digCloudScript` (NOT a branch in NAV_SCRIPT — would break byte-identity). Loading copy `⏳ generating…`. Poll ceiling 180000ms, backoff 2s→10s.

**Four forks settled (spec §3):**
- **D1 Interactive dig doc, mirroring local** — per-section `dig deeper ▶` triggers live INSIDE the served doc (server-rendered HTML + inlined navScript), NOT React. React only adds a menu doorway. Reuses existing `dig-trigger` markup (gated today by `readOnly`).
- **D2 No cost confirm** — one click enqueues; backend quota/daily caps (429/503) are the guardrail. Frictionless like local.
- **D3 Anonymous: pre-disable trigger** (aria-disabled + "Create an account to dig deeper" tooltip) AND keep 403 handler as server-enforced fallback. Matches existing cloud-menu disabled pattern.
- **D4 Expand-all EXCLUDED** (cost cliff: one click = N sections × ~23¢).

**Two FORCED constraints (code dictates, not choices):**
- Progress MUST be poll-based. Local SSE stream (`dig/[sectionId]/stream`) = in-memory single-process job-registry, NO supabase branch → returns 404 for cloud worker jobs. Cloud polls `dig-state` via `pollUntilTerminal` (`lib/job-queue/poll-client.ts`, 2s→10s; same idiom as `IngestProgressBanner`).
- Cloud dig UX is server-rendered HTML (nav.ts NAV_SCRIPT + render-dig-deeper.ts), not React. Cloud serve renders `readOnly:true` today (strips triggers + JS).

**Interaction (spec §7):** click `dig deeper ▶` → `⏳ generating…` → `POST /api/videos/<id>/dig/<sectionId>?playlist=<uuid>` (NO body) → `202 {jobId}` → poll `dig-state?playlist=` until sectionId appears → re-fetch `location.href` + swap `[data-start]` section in place (reuse local DOM-swap). `200 ready`→swap now. Errors→`⚠ retry` (429/503→"busy — try later", 403→account msg). Poll timeout ~3 min ceiling.

**URL contracts (spec §5):** menu `Dig deeper ↗` = `GET /api/html/<vid>?playlist=<uuid>&type=dig-deeper` (new tab); trigger POST no body; poll `dig-state?playlist=`; re-fetch `location.href`. New helper `digHref(playlistId, videoId)` in `lib/client/api.ts` mirrors `summaryHref`.

**Files (spec §11):** `lib/client/api.ts` (digHref), `components/VideoMenu.tsx` (cloud menu item, gated summaryReady), `app/api/html/[id]/route.ts` (interactive render not readOnly + inject playlist/cloud-flag + isAnonymous). SHARED (mandatory dual re-review): `lib/html-doc/render-dig-deeper.ts` (cloud-interactive mode, additive/off=byte-identical, anon pre-disable) + `lib/html-doc/nav.ts` (poll branch on trigger handler, reuse swap). Off-path MUST stay byte-identical (PR #19 invariant). Money invariant intact: opening/serving never charges; only the already-built POST spends.

**15 enumerated behaviors in spec §9** = the test contract. Integration test finally gives the serve path a committed integration test (PR #19 gap).

**Out of scope (§12):** expand-all; summary-doc dig deep-links (`?dig=N`); force-refresh of current-version dug section; precise job-failure signal (uses timeout ceiling). See [[frontend-subproject-design-state]], [[cloud-dig-serving-branch-state]].
