# Task 8 review — serve-side config-invariant soundness test

**Commits:** `ce59ce7` (impl) → `83840c1` (fix: drift-proof quota read + order-safe beforeAll) → comment-accuracy fix
**Gate:** Claude + Codex, plus a Codex RE-CHECK (round 1 found 2 Critical → fixed → re-adjudicated). Execution: SDD.

## Round 1 — reviewers diverged
**Claude — Approved.** Verified spec-compliant verbatim: reads live cost config, hard anon bound, tested registered-deferral, correct real columns, correct `SAFETY_FRACTION` direction. Flagged the cross-file `guardrail_config` mutation hazard as real-but-fix-belongs-elsewhere (warned a naive self-reset would be tautological).

**Codex — needs fixes (2 Critical + 2 Important, all on the TEST).** (C1) hard-codes doc counts `2`/`20` instead of reading `quota_allowance` → misses quota drift; (C2) reads a dirty shared `guardrail_config` singleton under `--runInBand` → flake/false-green + would break Task 9's full-suite run; (I) query errors unguarded (NaN risk); (I) optional tuned-tuple test can pass wrong + leaks dirty state.

**Adjudication (checked migrations):** `guardrail_config` is seeded by `insert ... default values` using column DEFAULT clauses → `SET = DEFAULT` / reading `information_schema` defaults is **drift-proof AND order-safe, NOT tautological** (Claude's objection applies only to hard-coded restores). `quota_allowance` is seeded with EXPLICIT values (no column default). → Codex's Criticals are valid; the fix is well-defined.

## Fix (`83840c1`, test-only; proven)
1. **C1:** doc counts read from `quota_allowance.monthly` (anon/registered), positive-integer-guarded.
2. **C2:** `beforeAll` restores `guardrail_config` from live `information_schema.columns` DEFAULTs (drift-proof) — order-safety **proven** against simulated dirty rows (`6/8/4`); RED **proven** (raising the true column default to 30 → anon test fails 300>100, revert → green). (`exec_sql` is read-only, so the restore reads catalog defaults + applies via UPDATE.)
3. **I:** result-guards (`error===null`, row present, `Number.isInteger && >0`) before arithmetic.
4. **I:** optional tuned-tuple test removed (was the false-green + dirty-leak source).
5. **Empirical correction:** the fixer found `quota_allowance` is ALSO mutated elsewhere (`cost-guardrails.test.ts`, `clients.ts ensureGuardrailHeadroom`) — added a `beforeAll` restore to the seed literals `2/20` for order-safety.

## Codex RE-CHECK — CONVERGES for shipping
All 4 round-1 findings CONFIRMED closed; order-safe; cost defaults genuinely drift-proof; optional test gone. **Tradeoff verdict: SHIP-WITH-FOLLOWUP.** The `quota_allowance` literal-restore makes quota **order-safe but NOT quota-drift-proof** (a future quota-seed change is masked by the restore) — a known, narrower limitation from shared mutable DB state, **not a remaining Critical** (test is order-safe; cost-drift caught). An overclaiming in-file comment ("a future quota bump is caught") was **corrected** to state the limitation accurately.

## Follow-up recorded → Task 9 triage / future hardening
Make quota fully drift-proof by having the mutating files (`cost-guardrails.test.ts`, `helpers/clients.ts`, `serve-model-charge.test.ts`) RESTORE `guardrail_config`/`quota_allowance` after mutating (or add a canonical seed source), so Task 8 can read LIVE quota with no self-reset. This also fixes the broader integration-suite config-singleton hygiene.

## Result
Full `test:integration --runInBand` = 182 passed, 2 pre-existing skips, 0 failed; `tsc` clean; order-safe. Anon money bound (`2·5·6=60 ≤ 100`) asserted HARD against live defaults; registered residual (`600 > 100`) a tested deferral-to-1G. **Task 8 COMPLETE (ship-with-follow-up).**
