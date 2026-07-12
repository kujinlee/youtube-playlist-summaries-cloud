# Task 6 Review — cloud dig trigger route branch (Approved, converged after 1 fix round)

Dual review of `2455f7f` (base `bffb9c4`); auth fixes `1248273`; focused auth re-review of the fix delta.
Diff: `lib/http/client-ip.ts` (extracted `parseClientIp`), `app/api/jobs/route.ts` (reuse shared helper), `app/api/videos/[id]/dig/[sectionId]/route.ts` (cloud `POST` branch), `scripts/check-service-confinement.ts` (+dig route allowlist), + route/confinement tests.

Auth-sensitive → full dual review (Claude task-reviewer + Codex adversarial).

## Round 1 — both reviewers

### Claude task-reviewer — ✅ Approved (0 Critical)
Verified in-diff: 400-before-401 ordering (all validation before `cookies()`/`createServerSupabase`); two-client split (session client → auth + `profiles.is_anonymous` RLS read; service-role → enqueue RPC only, no tenant read); `parseClientIp` byte-for-byte identical to the deleted copy (ingest import-swap only, unchanged); local branch untouched (`await params` hoisted once; cloud branch reads URL+headers, never `request.json()`); `Retry-After:60` on 429 + `challengeRequired` deliberate omission both present with origin comments; `EnqueueDigDeps` matches the route's call field-for-field.

### Codex adversarial — 0 Blocking, 1 High, 1 Medium, 2 Low
Cleared: two-client split, owner identity, `parseClientIp` fidelity, local-branch body behavior, Retry-After, confinement minimality, and jest discovery (`tests/api/**` matched at `jest.config.ts:13`).

### Two implementer deviations — both verified CORRECT by both reviewers
- **Test path** `tests/api/dig-cloud-route.test.ts` (not the brief's `tests/app/api/videos/…`): `jest.config.ts:13` matches `tests/api/**` with no `tests/app/**` pattern — the brief's path would have **silently never run**. The relocation is necessary.
- **Confinement allowlist**: one entry added to `ALLOWED_SERVICE_IMPORTERS` (dig route uses `createServiceClient` for the enqueue RPC only; `profiles` read stays on the session client) + a parity test. Minimal, well-commented, does not weaken the guard.

## Findings & dispositions

### HIGH (both: Codex High + Claude Important #2 — "the shape the brief calls Critical") — FIXED (`1248273`)
The anon gate failed **open**: `isAnonymous: profile?.is_anonymous === true` meant a null/errored `profiles` read (RLS denial, missing row, transient error → `profile===null`) yielded `false` → an anonymous user treated as **registered**, bypassing the dig=0 → 403 gate. **Fixed fail-CLOSED:** `profile?.is_anonymous !== false` — only an explicit `false` grants registered access; `true`/`null`/`undefined` → anon → 403. Backed by a profile-null test asserting `isAnonymous: true`.

### MEDIUM (Codex — 400-before-401) — FIXED (`1248273`)
`Number('')`/`Number(' ')` are `0`, so a whitespace `sectionId` segment passed validation as section 0 and reached auth. **Fixed:** `!sectionIdParam || sectionIdParam.trim()===''` → 400 before `Number()` (mirrors the local branch); backed by a whitespace test asserting `createServerSupabase` not called.

### Low / test-coverage (both) — FIXED (`1248273`)
Added: anonymous-path delegation test (`isAnonymous:true`), profile-null fail-safe test, whitespace + negative-integer `sectionId` 400 tests, invalid-videoId before-auth test, and the missing `createServerSupabase not called` assertion on invalid-playlist. dig-cloud-route 5→11 tests.

## Re-review (fix delta `2455f7f..1248273`) — Codex, auth path
0 Blocking / High / Medium / Low. Verified the fail-closed mapping is genuine and complete (`true`→403, `false`→registered, `null`→403), the whitespace guard precedes `Number()` and auth, the variable unification broke neither branch, and the 6 new tests genuinely lock in both fixes. Codex re-ran the focused suites to confirm.

## Disposition
Converged after 1 fix round (auth-path re-review clean). Both reviewers Approved; both implementer deviations correct. Tests: dig-cloud-route 11/11, full suite 2122, tsc clean. No deferrals.
