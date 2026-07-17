# Reservation Release Plan v4 — Claude Round-4 Convergence Review (independent)

**Reviewer:** Claude, independent, full repo access.
**Artifact:** plan v4 + spec v7.
**Verdict:** **CONVERGED** — 0 Blocking, 0 High, 0 Medium, 2 Low (pre-existing, optional). *"This is the gate round — proceed to implementation."*

---

## (A) Round-3 fixes — each verified genuinely applied in v4
1. **R3-H1 serve-doc split read — GENUINE.** Task 5 Step 4 = minimal `data[0].status` only (no token/settle); matches real `serve-doc.ts:52`. Task 11 Step 3 supersedes the same read to add `release_token` + settle — edit of the same lines, no double-declaration, compiles.
2. **Helper-API global fix — GENUINE.** Whole-plan grep: `signInAs(u)`/bare `u.id` appear only in the review-log description line. All 12 live calls `signInAs(u.email, u.password)` + `{ client: session }`; owner id `u.user.id` (41 uses, 0 bare). Matches real `helpers/clients.ts`.
3. **behavior-26 low-cap try/finally — GENUINE** (`daily_cap_cents=450` … `finally { ensureGuardrailHeadroom }`).
4. **Task 10 `makeQueue` — GENUINE** (`makeQueue(job); queue.fail = failSpy`; `makeQueue` exists at `worker-runner-runtime.test.ts:22`).
5. **behavior-13b body — GENUINE** (seeds yday at 10¢ < 150¢ group sum → audit row, today credited, yday not negative).

## (B) Holistic money sweep — CLEAN
- Task 5 + Task 11 both edit serve-doc.ts — sequential edits to the same read block, no conflict; `error` handling preserved.
- `u.id`→`u.user.id` breaks nothing (every site is a `newUser()` result; `userId` from `signInAs` correctly unused).
- Money SQL: `fail_job` (guarded, day from created_at, terminal + not-billable + reserved>0, inside active fence); cancel RPCs (pre-read OLD, queued-only, per-day audit); `reserve_serve_model` (token only on 'reserved'); `settle_serve_model` (idempotent, double-settle + post-KEEP un-charge both return false, released path guarded double-decrement + audit). Reclaim SETs new token → old can't settle (behavior 24, K-bounded leak not double-refund).
- Spec §7 behaviors 1–26 all have covering bodies (16 via the behavior-26 re-admit).

## Findings
**Blocking/High/Medium:** none.
**Low (pre-existing, non-blocking, optional):**
- **L1** — Task 12 names behaviors 5/10/22/23 but Step-1 inlines only 7/25/26/24; their semantics are covered elsewhere and Task 12 says "add the not-yet-covered rows" — accepted placeholder posture, not a red commit. *(Fold-in bodies added v4→v5.)*
- **L2** — the `serve-model-charge.test.ts:125` note is imprecise (that test targets `release_serve_model`, a name this plan doesn't create → stays green). *(Note softened v4→v5.)*

## Verdict
**CONVERGED.** All five round-3 fixes genuinely applied, grounded against real `serve-doc.ts`/`helpers/clients.ts`/`worker-runner-runtime.test.ts`. Holistic money pass: zero new Blocking/High — no under-count, no over-release, no SQL compile error, no red-commit sequence. Three-plus rounds found nothing but test-scaffolding/interface mechanics; the money SQL/design is stable. **The gate round — proceed to implementation.**
