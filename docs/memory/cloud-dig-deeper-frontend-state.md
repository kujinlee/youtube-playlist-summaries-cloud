---
name: cloud-dig-deeper-frontend-state
description: "FIRES-WHEN: changing the cloud 'Dig deeper' trigger, the dig serve CSP, the anonymous gate, or cloud dig progress — MERGED PR #20 (a4c251c, 2026-07-15); rules: isAnonymous fail-closed, poll not SSE, off-path byte-identical"
metadata:
  type: project
  originSessionId: 7746a733-7051-4952-85dd-526eb71dd21b
---

**STATE:** MERGED to master — PR #20, merge commit `a4c251c` (2026-07-15), whole-branch dual review
CONVERGED 0B/0H. Makes the cloud dig serving slice ([[cloud-dig-serving-branch-state]], PR #19) reachable,
implementing §14.3 of the dig-generation spec. ⚠ **Residual gap both reviewers flagged:** no browser-level
Playwright cloud e2e (load the dig doc under the real CSP, click the trigger). `tests/e2e/dig-deeper.spec.ts`
was last changed 2026-07-01, before this slice — not verified to cover it (checked 2026-11-14).

**RULES — don't regress (verified in code 2026-11-14):**
- **isAnonymous reads `profiles.is_anonymous` FAIL-CLOSED** — `profile?.is_anonymous !== false`
  (`app/api/html/[id]/route.ts`), never `user.is_anonymous`; a profiles read error → disabled, not 500.
- **The interactive dig doc needs its own CSP** — `buildDigCsp` (`lib/html-doc/csp.ts`) with `connect-src
  'self'`; without it the doc's fetches are browser-blocked and the feature is inert (whole-branch v1 Blocking).
- **Zero-dug returns ok `dug:[]`, not 404** — else the "open to start digging" entry path is dead (v1 Blocking).
- **Progress is POLL-based, by force:** the local SSE stream (`dig/[sectionId]/stream`) is an in-memory
  single-process registry with no supabase branch → 404 for cloud jobs. Cloud polls `dig-state` via
  `pollUntilTerminal` (`lib/job-queue/poll-client.ts`, 2s→10s backoff, 180000ms ceiling).
- **Separate `digCloudScript`, not a branch in NAV_SCRIPT** — the off path must stay byte-identical (PR #19
  invariant); commit the pre-change render golden BEFORE editing the renderer. dig-refresh gated off in cloud.
- **Money invariant:** opening/serving never charges; only the already-built POST spends.
- Test asserts `class="dig-expand-all"`, not the bare token (it also lives in kept CSS); `swapDugSection`
  throws unless the section exists AND `data-dug==="true"`; the shipped script is EXECUTED in jsdom.

**Settled forks (spec §3):** D1 interactive dig doc mirroring local — triggers live INSIDE the server-rendered
doc, React only adds a menu doorway · D2 no cost confirm (backend 429/503 caps are the guardrail) · D3
anonymous: pre-disable (aria-disabled + "Create an account to dig deeper") AND keep the 403 fallback · D4
expand-all EXCLUDED (one click = N sections × ~23¢).

**Contracts:** menu `Dig deeper ↗` = `GET /api/html/<vid>?playlist=<uuid>&type=dig-deeper` (new tab, helper
`digHref` in `lib/client/api.ts`); trigger `POST /api/videos/<id>/dig/<sectionId>?playlist=<uuid>` (no body) →
`202 {jobId}` → poll `dig-state?playlist=` → re-fetch `location.href`, swap the section. 429/503 → "busy — try
later", 403 → account message. Out of scope (§12): expand-all, `?dig=N` deep-links, force-refresh, a precise
job-failure signal.

## History
Spec `a6fca5b`; plan `044212d`, post-plan dual review v1 `e53ae0f` (1B+3H) → v2 `8c4b316` converged; SDD T1–T6
`ff666d2` … `be18af6`; whole-branch v1 found 2 Blocking (one from EACH reviewer, both emergent), fixed
`e2ffc8f`, v2 `205ee05` CONVERGED. Suite 2298/2298 at merge. Reviews:
`docs/reviews/whole-branch-cloud-dig-deeper-frontend-v1-review.md` + `-v2-rereview.md`.
See [[frontend-subproject-design-state]].
