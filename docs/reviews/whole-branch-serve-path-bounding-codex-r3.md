<!-- codex-review: model=gpt-5.5 -->

**Blocking**
None.

**High**
H-R3-1: the round-2 “class” guard still accepts a larger bounded-call expression, so it is another instance-shaped assertion.

`tests/lib/html-doc/serve-bounded-import-guard.test.ts:113`  
`const seen = args.filter((a) => a.includes(constant)).length;`  
`tests/lib/html-doc/serve-bounded-import-guard.test.ts:114`  
`expect({ fn, constant, seen }).toEqual({ fn, constant, seen: 1 });`

Failure scenario: `resolveMagazineModel` reaches the paid lease path and calls the put bound at `serve-doc.ts:133`:

`lib/html-doc/serve-doc.ts:133`  
`await writeModelEnvelopeWithin(SERVE_PUT_TIMEOUT_MS, principal, base, {`

Temporary mutation tested this round: `SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS` plus importing `SERVE_MARGIN_MS`. The guard suite still passed: 8/8 green. That spends the margin as enforced wait while the database still permits the 161s floor. The caller is the reserved serve path: `generateMagazineModelForServe` then `writeModelEnvelopeWithin` at `lib/html-doc/serve-doc.ts:127-133`. Money consequence at the legal minimum: the 20s unmodelled-work margin can be silently consumed, reopening lease-expiry admission of a second paid producer.

Proposed fix: stop scanning call text with `includes`. Parse `serve-doc.ts` with the TypeScript compiler and assert each bounded argument expression is exactly the expected identifier, or invert the design so bounded APIs accept an opaque per-site budget token exported only from `serve-budget.ts`.

**Medium**
None.

**Low**
L-R3-1: migration prose points to the wrong anti-drift gate.

`supabase/migrations/0024_lease_covers_serve.sql:8`  
`-- Pinned by tests/integration/serve-config-invariant.test.ts, which asserts EVERY floor literal in`

But the gate now lives in unit tests:

`tests/lib/serve-budget.test.ts:90`  
`// IT LIVES IN THE UNIT SUITE ON PURPOSE (round-2 review M-R2-1).`

Failure scenario: a reviewer follows the migration comment and looks in the integration suite for the literal population pin, then concludes the pin is outside CI. Caller: humans maintaining the migration/gate. Proposed fix: update the comment to `tests/lib/serve-budget.test.ts`.

**Round-2 fixes: genuinely fixed, or reworded?**
H-R2-1: reworded, not closed. It catches literal replacement and missing per-site constants, but not expression drift. The temporary `SERVE_PUT_TIMEOUT_MS + SERVE_MARGIN_MS` mutation passed the guard.

H-R2-2: genuinely fixed. `settleBounded` now returns `applied | refused | indeterminate`; timeout/error before a later `false` no longer emits `REFUND NOT APPLIED`. The focused mapping tests cover the timeout-then-false path.

M-R2-1: genuinely fixed. The migration literal pin is in `tests/lib/serve-budget.test.ts`; the stale migration comment is Low documentation residue.

L-R2-1: genuinely fixed in SQL behavior. I verified with a temp table against live Postgres: simple `lease_ttl_seconds >= 1` matched drop, upper bound did not, `AND`/`OR` compound constraints were spared.

L-R2-2: fixed for the load-bearing 156 to 161 values I checked in the spec/code/migration. I did not find a stale 156 that matters to this branch gate.

L-R2-3: only partly dissolved. The exact reserve-timeout literal mutation is covered, but the same call-site guard still accepts arithmetic expressions containing the right constant.

**Escalation Verdict**
Wrong shape being patched.

This is not just a defect stream converging. Round 1 asserted one call site. Round 2 asserted a population, but still by substring over raw call text. Round 3 found the same class again: the assertion proves “the expected token appears somewhere,” not “the bounded operation receives exactly the budget the lease sum counted.”

That is a High caused by the round-2 fix, after round 2 already had Highs caused by round-1 fixes. Per `docs/review-method.md:45-46`, the escalation rule fires. The redesign I would require is not a new timeout scheme; it is a different validation shape for the boundary: AST-level exact-expression assertions, or opaque/branded per-site budget values that make arithmetic/alias drift unrepresentable at the call site.

Verification run: `npx tsc --noEmit` passed; focused unit tests passed, 35/35. `git status --short` was clean after restoring the mutation.

NOT CONVERGED
