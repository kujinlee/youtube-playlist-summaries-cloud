# Adversarial Plan RE-REVIEW (round 2) — Stage 1F-a — Codex (gpt-5.5)

**Artifact:** `docs/superpowers/plans/2026-07-09-stage-1f-a-authorized-doc-serving.md` (revised v2, 2175 lines)
**Contract:** `docs/superpowers/specs/2026-07-09-stage-1f-a-authorized-doc-serving-design.md`
**Reviewer:** real Codex (gpt-5.5) via coordinator Bash (sandbox-disabled remedy)
**Date:** 2026-07-09
**Verdict:** **NOT READY TO EXECUTE** — 1 Blocking, 2 High. Needs another revision (one Blocking compile defect + High test-validity gaps in money-path/RLS coverage).

This is the round-2 re-review after the revision subagent closed the round-1 17 findings. It VERIFIES each round-1 fix (see Round-1 Fix Status) and hunts NEW defects the fixes introduced. Per dev-process §"Iterative Re-Review", a round that surfaces a NEW Blocking/High means the loop is still earning its cost — another revision round is mandatory.

---

## BLOCKING

### B-1 — Task 2 Step 4: optional `CloudGeminiCaps` magazine fields used as required. CORRECTNESS
`CloudGeminiCaps.magazineInputTokens?` / `magazineOutputTokens?` were made optional (to preserve the 4 existing caps literals), but `assertMagazineInputWithinCap` compares `totalTokens > caps.magazineInputTokens`. Under `strict`, that is "possibly undefined" → **Task 2's own `npx tsc --noEmit` fails at its commit**. Worse, a caller can pass `caps` without magazine fields → `maxOutputTokens: 0` / broken preflight.
**Fix:** after `if (caps)`, require both fields with a type guard (or throw `NonRetryableError`) before use; use a narrowed local type for the preflight and `withCaps`.

---

## HIGH

### H-1 — Task 1 grant/RLS tests do not prove UPDATE/DELETE lockdown. CORRECTNESS
The revised plan adds a direct CRUD test, but the update/delete assertions are **vacuous**: Supabase `.update()` / `.delete()` return `data: null` unless chained with `.select()`, so `expect(upd.data ?? []).toEqual([])` passes even if the operation succeeded. The final service-role check only asserts row count is still `1` — it would not catch `attempt_count` being mutated.
**Fix:** assert `upd.error` / `del.error` when permission is denied, OR chain `.select()` and verify zero affected rows; then service-read the marker and assert the exact original fields (`attempt_count`, `lease_expires_at`) are unchanged. Also assert `pg_class.relforcerowsecurity = true` for `serve_model_charge`.

### H-2 — Task 1 concurrency fix only partially tested (K-boundary reclaim is sequential). CORRECTNESS
The plan claims three `Promise.all` concurrency tests, but the K-boundary reclaim test is **sequential**. It misses the exact prior M-1 race: a loser at the K-boundary seeing `attempt_count = K` while the winner's K-th lease is live. The SQL now checks `lease_expires_at > now()` so it appears sound, but the regression test does not exercise the concurrent boundary.
**Fix:** make the K-1 expired-lease case a real two-racer `Promise.all` (after expiring attempt 4); assert one `reserved`, one `in_flight`, `attempt_count = 5`, `reserved_cents = 30`.

---

## MEDIUM

### M-1 — Task 4 promote-hardening test can pass without the hardening. CORRECTNESS
Covers "final already exists before move" and "move fails and final absent," but NOT the real over-TTL race: final absent on precheck, `move()` fails (concurrent promoter won), final present on recheck. A buggy impl with only the precheck and no post-error recheck would pass the current tests.
**Fix:** add a test where `download` returns absent-then-present and `move` returns a destination/source race error; expect `promote()` to resolve.

### M-2 — Task 6 generatorVersion invalidation lacks a direct test. CORRECTNESS
The snippet checks `envelope.generatorVersion === GENERATOR_VERSION`, but tests only cover title drift and "generatorVersion is defined" on write. A future edit could drop version invalidation with those tests still green.
**Fix:** seed/write an envelope with matching `sourceSections` but stale `generatorVersion`, then assert `resolveMagazineModel` calls Gemini and rewrites the envelope.

### M-3 — Task 7 B9/B10 isolation test overclaims "200". CORRECTNESS
The revised integration test drives real `resolveOwnedPlaylistKey` / `readIndex` RLS points for registered/anon/foreign users (useful, no longer prose). But it does not actually call `GET` or assert HTTP 200/404; it asserts "route would proceed."
**Fix:** either reword the name/comment to "RLS points for the 200 path," or add a thin real route call with Gemini mocked at the lib boundary.

---

## LOW / NITS

### L-1 — expected-count drift. CORRECTNESS
Task 2 says "PASS (4 tests)" while showing 6; Task 8 says "PASS (2 tests)" while showing 3. Fresh subagents use these as checklists.
**Fix:** correct the expected counts.

---

## Round-1 Fix Status (verification of the revision)

- **Seed helper fidelity:** CONFIRMED-FIXED — `owner_id`, top-level `summaryMd`/`language`/`serialNumber`, `artifacts.summaryMd.{key,status}`.
- **SQL no-claim status race:** CONFIRMED-FIXED in SQL, but boundary **concurrency test STILL-BROKEN** (H-2).
- **Grant/RLS tests:** STILL-BROKEN for update/delete proof (H-1).
- **Task 1 concurrency tests:** PARTIALLY FIXED — two real `Promise.all`, missing K-boundary concurrent race (H-2).
- **Task 2 shared-schema regression:** CONFIRMED-FIXED conceptually, but **new optional-field compile blocker introduced** (B-1).
- **Task 5 render-dig-deeper / print / nonce:** CONFIRMED-FIXED — `navScript().replace('<script>', ...)` is mechanically correct against current `NAV_SCRIPT`.
- **Task 7 confinement / B20:** CONFIRMED-FIXED — no allowlist, route scanned, session client asserted.
- **Task 8 invariant tautology:** CONFIRMED-FIXED — reset defaults read without mutation.

**Verdict:** NOT READY TO EXECUTE. Needs another revision — one Blocking compile defect and High test-validity gaps in the money-path/RLS coverage. (Task 5, the §8 shared-code re-review trigger, is CONFIRMED-FIXED.)
