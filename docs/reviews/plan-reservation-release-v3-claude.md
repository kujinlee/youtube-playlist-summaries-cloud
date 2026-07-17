# Reservation Release Plan v3 — Claude Round-3 Adversarial Re-Review (independent)

**Reviewer:** Claude, independent, full repo access.
**Artifact:** plan v3 + spec v7.
**Verdict:** **NOT CONVERGED** — 0 Blocking, 1 new High, 1 Medium, 2 Low. All five round-2 fixes verified genuine. Holistic money pass: no under-count / over-release / SQL defect.

---

## Part A — Round-2 fixes all GENUINE
- R2-H1 (JobQueue interface widening) — genuine, correct locations + default.
- R2-H2 (cap headroom) — `ensureGuardrailHeadroom` exported (`clients.ts:45`, pins `daily_cap_cents:1_000_000`); `beforeAll` present.
- Claude-R2-M — lines 84/124/169 are the ONLY three `fail).toHaveBeenCalledWith` sites; enumeration airtight; all KEEP paths.
- R2-M1 — threading test uses `summaryCore(input, deps, {caps,billing})`; input matches `SummaryCoreInput`.
- L2/L3 — corrected.
- **Interface-widening blast radius — CLEAN.** Sole `implements JobQueue` is `SupabaseJobQueue`; all mock queues are `jest.fn()` cast `as unknown as jest.Mocked<JobQueue>` → an optional field breaks no cast.

## High

### R3-H1 — Task 5 return-type change breaks `serve-doc.ts` scalar read, but the fix is only in Task 11 → Task 5 commits a RED serve path
`Task 5` + `lib/html-doc/serve-doc.ts:52-73` + `tests/integration/pdf-cloud.test.ts:355`. After Task 5, `reserve_serve_model` `.rpc()` returns an array, but `resolveMagazineModel` still does `const { data: reserveStatus } = rpc(...); switch(reserveStatus)` → `switch(array)` → `default: throw` before `generateMagazineModel`. Task 5's runlist includes `pdf-cloud`, whose money-mutation test (`:355`) drives the real `resolveMagazineModel` on an absent model → the throw → asserts `status===200` + `generateMagazineModel` called once, both fail. "Expected: new suite PASS" is wrong; under SDD, Task 5 commits red until Task 11.
**Fix:** fold the minimal `const reserveStatus = data?.[0]?.status` read into Task 5 (defer only token/settle to Task 11), OR drop `pdf-cloud`/serve-materialization from Task 5's runlist with a transient-red note. Option (a) keeps every commit green.

## Medium

### R3-M1 — plan test bodies use the wrong helper API (Tasks 1–5, 12)
`newUser()` → owner id is `u.user.id` (not `u.id`); `signInAs(email, password)` (not `signInAs(u)`) → `{ client, userId }` (not a bare client). Self-correcting at TDD RED; not design-affecting. (Same as Codex-R3-H1; fixed in v4.)

## Low
- **R3-L1** — Task 10 Step 1 references `makeStubQueue({ fail: failSpy })`; real harness is a full `jest.Mocked<JobQueue>` (no fail-injection option). Adapt naming at impl.
- **R3-L2** — behaviors 13b (per-day underflow audit) and 16 (cap re-opens) are claimed but lack a written test body. §9 mandates 13b; 16 needs a locally-lowered cap. Spell both out.

## Part B — Holistic money pass: CLEAN
Walked all of `0020` (`fail_job`, both cancel RPCs, `reserve_serve_model` PJ004/PJ005 subtransaction rollback, `settle_serve_model` guarded double-decrement + idempotent). Prod gate const-false; latch at the primitive before parse. All 26 §7 behaviors assigned to tasks (only 13b/16 lack a written body). No SQL compile/semantic defect; no over-release; only the documented §2.4 residuals. Consistent with spec rounds 4–7 "SQL closed."

**VERDICT: NOT CONVERGED** — 1 new High (Task 5↔11 sequencing; one-edit fix, no SQL/design change). Money design sound and unchanged.
