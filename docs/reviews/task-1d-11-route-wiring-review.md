# Task 1D-11 Review — POST /api/jobs preflight + two-client wiring

**Commit:** 66cb82a · **Base:** 1c243ea · Dual review (Claude SDD spec+quality + Codex security-focused).

## Spec Compliance: ✅ Approved (SDD reviewer, sonnet)

- Preflight precedence exact: `velocityExceeded`→429+`Retry-After`, `atCapacity`→503, `!admitted`→403, else proceed.
- IP parse: `Fly-Client-IP` else first `X-Forwarded-For` hop else null; flows into both `preflight` and enqueue ctx (tested).
- `challengeRequired` sourced from the preflight **verdict** (not producer result), merged into 200 (tested with true verdict + independent counts).
- Two-client split honored: reads=session client, writes=service `Enqueuer` (no read method by design). GET byte-identical to base; test asserts `createServiceClient` NOT called on GET.
- Existing error mapping intact (422/503/502/500). DECISION-2 migration of `jobs-route.test.ts` done (service/enqueuer mocks + 7-field counts). Only remaining tsc error is `producer-roundtrip.test.ts` (T13).

## Security (confinement narrowing)
- Change is a genuine NARROWING: `findServiceImporters()` still baselines to empty, subtracts exactly one resolved path (`app/api/jobs/route.ts`) via `ALLOWED_SERVICE_IMPORTERS`. New positive test asserts `reachesService('app/api/jobs/route.ts') === true` → allowlist can't rot into protecting a file that no longer uses service.ts. Self-flagged by implementer, correctly scoped.

## Codex Adversarial (frontier) — No Blocking/High
- **Vector 1 (cross-tenant) — SAFE:** `ownerId = user.id` from session `getUser()` (401 gate); body only supplies `playlistUrl`. Service client confined to `SupabaseEnqueuer` (no tenant read/list). GET reads on session client.
- **Vector 2 (allowlist bypass) — SAFE:** single resolved-path allowlist; any new `app/**` transitively reaching service.ts still fails. Caveat: covers transitive (not direct-only) reachability — matches the intended narrowed invariant.
- **Vector 4 (preflight bypass) — SAFE:** awaited before enqueue; all blocking verdicts return immediately.
- **Vector 5 (leak) — SAFE:** fixed public error strings; `challengeRequired` from trusted verdict.
- **Vector 3 — MEDIUM (see below).**

## Findings deferred to whole-branch / USER DECISION
- **MEDIUM (Codex V3) — IP-spoofing velocity bypass, PLAN-MANDATED:** when `Fly-Client-IP` is absent, the route trusts the first `X-Forwarded-For` hop (client-settable); DB velocity check (0011 L164-168) is keyed only by `enqueue_ip`, so an authed caller can rotate XFF to evade `velocityExceeded`. **NOT unlimited spend** — per-owner quota/daily-cap in `enqueue_job` (trusted `ownerId`) is the primary backstop. On Fly, the proxy always sets `Fly-Client-IP` so the fallback never triggers. The IP-parsing rule is exactly what the spec/brief mandated → this is a spec-level decision, not a T11 defect. **Options for user:** (a) accept (rely on Fly always setting Fly-Client-IP + per-owner quota); (b) drop the XFF fallback to null (rotation then shares one null bucket); (c) also key the velocity check by ownerId. Recommend documenting the "must only be reachable via Fly proxy" deploy assumption.
- **MINOR:** `createServiceClient()`/`new SupabaseEnqueuer` constructed before the `try` → a missing `SUPABASE_SERVICE_ROLE_KEY` would escape the clean-500 boundary. Consistent with the pre-existing session-client construction (also outside try) — not a T11 regression; follow-up ticket to wrap all client construction.
- **MINOR:** `RETRY_AFTER_SECONDS = 60` hardcoded placeholder (no per-verdict value), documented inline.

## Verdict: Approved (jobs-route 19/19 + confinement green; full npm test 1698 green).
