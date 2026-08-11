# Whole-branch review #46 — ROUND 2 ADJUDICATION

| reviewer | verdict | findings |
|---|---|---|
| Codex (gpt-5.4, after gpt-5.5 timed out) | **CONVERGED** | 0 |
| Claude (isolated worktree) | **NOT CONVERGED** | 2 High, 1 Medium, 3 Low |

**Both Highs were introduced by round 1's own fixes.** That is the first of the two consecutive
rounds that would trigger `review-method.md`'s FIX → REDESIGN escalation. Round 3 decides.

## The split, again — and the same resolution

Codex returned CONVERGED for the second consecutive round, and was wrong for the second consecutive
round. **I established that by re-running the mutation myself before reading either review**:
replacing `SERVE_PUT_TIMEOUT_MS` with `120_000` at `serve-doc.ts` left **2647 tests green**.

This is not a lazy reviewer. Codex's round-2 work was genuinely strong on the question it answered:
it re-ran the round-1 mutations, probed the **live database** for the settle reply shape
(independently reaching the same `true` / `false` result I measured), and checked the constraint
regex against Postgres's own normalised `pg_get_constraintdef` text rather than the source SQL.

**It answered job 1 — "are the fixes real?" — thoroughly, and did not do job 2 — "what did the fixes
break?"** — although the brief asked for both, in its first section, in bold. That is
`review-method.md`'s *"convergence measures the prompt too"*, and the prompt was not the problem
here: the instruction was explicit and still did not land. Recorded as a property of this reviewer:
**Codex verifies; it does not hunt regressions in its own prior findings' fixes.** Weight its
CONVERGED accordingly — as evidence about the fixes named, never as a gate.

## Adjudication

| id | verdict | how established |
|---|---|---|
| **H-R2-1** the H1 fix covered 1 of 4 bounded call sites | **CONFIRMED — fixed** | I re-measured: `writeModelEnvelopeWithin(120_000, …)` → `tsc` exit 0, **2647/2647 green**, and the round-1 import guard **passed**, because it checked the identifier and never the argument |
| **H-R2-2** `settleBounded`'s `false` carries three meanings | **CONFIRMED — fixed** | Traced: attempt 1 times out client-side but commits server-side → attempt 2 gets the idempotent `false` → round-1 logged `REFUND NOT APPLIED` for a refund that **had applied**. The reserve branch three lines up already reasons correctly about commit-after-timeout; the settle branch did not |
| **M-R2-1** the floor's anti-drift pin was integration-only, i.e. outside CI | **CONFIRMED — fixed** | Moved to `tests/lib/serve-budget.test.ts`; it only reads the `.sql` off disk and never needed a database |
| **L-R2-1** the narrowed sweep still dropped a multi-column CHECK whole | **CONFIRMED — fixed** | Measured against live Postgres on a temp table: `>= 1` → dropped, `<= 3600` → spared, `(>= 1 AND max_serve_attempts >= 1)` → **spared** |
| **L-R2-2** spec and plan still said 156 | **CONFIRMED — fixed** | 13 occurrences updated to 161 across both approved artifacts |
| **L-R2-3** the reserve-timeout mutation went red only via Jest's 5s timeout | **CONFIRMED — dissolved by the H-R2-1 fix** | The new class guard asserts `SERVE_RESERVE_RPC_TIMEOUT_MS` is the argument at that call site, so a mutated value now fails on an assertion rather than on a clock |

## What the H-R2-1 fix does differently from the H1 fix

Round 1 asserted **an instance**. Round 2 asserts **the class**, in
`tests/lib/html-doc/serve-bounded-import-guard.test.ts`:

1. `serve-doc.ts` may contain no numeric literal other than `0` and `1` — it **names** durations and
   counts, it never **spells** them.
2. Each bounded call site receives its **own** designated constant, not merely some constant.
3. The **population** of bounded call sites is pinned, so adding a fifth without extending the table
   fails here.

Mutation-verified against both shapes round 1 would have missed: a literal (`120_000`), and a
**swap** — giving the reserve call the settle's constant, where every argument is still "a constant".

## A guard catching its author, mid-round

The M2 population pin fired while I was writing the L-R2-1 fix: my new comment quotes
`CHECK ((lease_ttl_seconds >= 1) AND …)` as the example of what the sweep must *not* drop, and the
`check` regex matched **the comment**, seeing two floor literals where the SQL has one.

The guard was right and the instrument was reading prose. Fixed by stripping `--` lines before
matching — a pin that reads comments pins the wrong thing. Worth recording because it is the cheap
version of this project's recurring lesson: the instrument found the ambiguity the same minute it
was created, instead of a review round later.

## Process notes

- **Worktree isolation does not isolate the database.** Each reviewer got its own worktree this
  round, and Codex still ran `supabase db reset` on the shared stack mid-review, killing a Claude
  integration run in `globalSetup`. Claude correctly declined to charge any finding to a run made in
  that window. Round 3's brief must say: **do not reset the shared stack.**
- A fresh worktree has no `.env.test.local`, so integration refuses to run until it is copied. Also
  belongs in the brief.
- The Claude worktree was created from `master` rather than the branch head; the agent noticed and
  `git reset --hard`'d to `2098ebf` before reviewing. Verified the Codex worktree was created at
  `HEAD` correctly.

## Gate status entering round 3

`tsc --noEmit` clean · unit **263 suites / 2653 tests** · full integration **67 suites / 484 tests,
green twice back-to-back after a `db reset`** · migration 0024 verified to apply from scratch, and
the live catalog holds exactly one lease-TTL constraint at `>= 161` · every round-2 fix
mutation-checked.
