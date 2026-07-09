# Round-3 re-review — Stage 1D spec v3 (dual; verdict: NOT converged — v4)

**Date:** 2026-07-08 · Target: v3 (commit f242534)
**Reviewers:** Codex round-3 (`task-mrcmvol7-ryqn2e`, session `019f43ca`) + Claude round-3 (fresh Opus subagent `a77d3d1d`), independent.
**Note:** the two reviewers **diverged on severity** — Codex ruled the token-ceiling gap a Blocking (v4 required); Claude ruled it an accepted residual risk and declared convergence. Surfaced to the user (non-convergence was the user's stated condition for involvement); user chose **enforce token caps**. So the gap is treated as a Blocking and fixed in v4.

## Blocking (Codex; Claude classified as accepted residual)

- **Cap soundness still false: duration is not a token ceiling.** `max_duration_seconds` bounds wall-clock **seconds**, but Gemini bills **tokens**. The code enforces **no** transcript-input cap and **no** `maxOutputTokens` (verified: no `maxOutputTokens` in any `gemini.ts` `generationConfig`; no truncation in `transcript-timestamps.ts`). A dense-caption / verbose 30-min video sends the full transcript to `generateSummary` (up to 12 model passes) and emits unbounded output → real cost can exceed the assumed 256k-in/4k-out, so `est` (75¢) is not a provable upper bound and the guard test can't prove it (config has no token/output caps). *Fix (chosen): enforce cloud-scoped token caps — `maxOutputTokens` on every cloud call + transcript-input truncation — and derive `est` from those enforced limits.*
  - Claude's counter (recorded): independent recompute ≈ $0.56 at the assumed figures (~29% margin), the three cloud Gemini surfaces are exactly `transcribe`/`generateSummary`/`extractQuickView` (`fixSummary` NOT in cloud path), and abuse is already bounded by auth + monthly quota + velocity + duration — hence "accepted residual, not defect." Valid, but for a money kill-switch the user chose the provable fix.

## High (Codex)

- **The "live" guard test still can't prove `per_run_worst`** while token/output caps aren't enforceable/among the recomputed variables. *Fix: import the enforced code token caps into the test and recompute from them (+ live duration/attempts).*

## Medium (both reviewers concur)

- **PT003 duration backstop is fragile (Codex + Claude M3-1).** `coalesce((p_payload->>'durationSeconds')::int, 0)`: a **fractional** duration (`durationSeconds` is `z.number().finite().positive()` — floats allowed) throws `22P02` (raw cast) instead of a clean `too_long`; a **missing/null** duration coalesces to `0` and is silently admitted (the backstop's threat model is untrusted input). *Fix: `floor((...)::numeric)::int`, and reject (not admit) missing/non-numeric — and move the check into the new-row branch so a JOIN of a live job isn't blocked by a drifted payload (M3-3).*
- **Test-file misidentification (Codex).** The direct jobs-insert / idempotency cases are in `tests/integration/job-queue-schema.test.ts`, **not** `schema.test.ts` (which holds core RLS/schema assertions). v3 conflated them. *Fix: enumerate `job-queue-schema.test.ts` for the enqueue/idempotency rewrites; extend `schema.test.ts` only for the new-table RLS-forced assertion.*
- **Handler duration-constant is a third coupling site (Claude M3-2).** §9's "or a shared 1800 constant" option means a handler hard-coded to 1800 would reject jobs an admin later admits (raised `max_duration_seconds` + `est`). *Fix: handler must **read** `max_duration_seconds` from config; add it to the coupling list.*

## Low

- **SQLSTATE `PT###` collides with PostgREST's `PTxyz`→HTTP-status convention (Codex).** `PT001/2/3` would be reinterpreted as HTTP-status overrides. *Fix: move off the `PT` class (→ `PJ001/2/3`).*
- **Queue-depth / user-ceiling / velocity are advisory-only (Claude M3-4).** Not stated as non-atomic; a burst can overshoot. *Fix: state explicitly that only the daily cap + quota are atomic/race-free.*

## Round-2 → v3 resolution status
- **B-A** (at-most-once billing): **RESOLVED** — Claude traced `max_attempts=1` through `fail_job` AND `sweep_expired_leases`; both dead-letter at `attempts=1`, closing the crash-reclaim re-bill. Verified.
- **H-B** (two-client split): **RESOLVED** — `resolvePlaylistId` session-RLS; service client isolated to a read-less `Enqueuer`; no leak path.
- **H-C** (guard test): **RESOLVED w.r.t. DB drift**, but incomplete for token variables → the round-3 High.
- **M-D** (duration backstop + handler): **PARTIAL** → M3-1 (fragile cast) + M3-2 (handler coupling).
- **M-E** (test enumeration): **RESOLVED count, wrong name** → the test-file Medium.

## v4 fixes (all of the above)
Enforced cloud-scoped token caps (`maxOutputTokens` + transcript truncation, options → local unchanged); `est` re-derived from enforced caps (75¢→$1.00, ~96¢ provable worst case); guard test imports code caps; robust PJ003 cast + reject-missing + new-row-branch placement; handler reads `max_duration_seconds` from config; corrected test-file enumeration; SQLSTATEs `PT`→`PJ`; advisory-gate wording. → spec v4; re-run full dual review (round-4).
