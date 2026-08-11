# Whole-branch review #46 — ROUND 1 ADJUDICATION

Three independent passes over `1a7c076..b9dab35`:

| reviewer | verdict | findings |
|---|---|---|
| Codex (gpt-5.5) | **CONVERGED** | 1 Low |
| Claude (subagent) | **NOT CONVERGED** | 3 High, 3 Medium, 3 Low |
| Coordinator (me, before reading either) | — | 1 Medium |

## The split, and how it was resolved

`docs/review-method.md`: *"Reviewer disagreement is the signal. Never resolve a split by majority or
by trusting a CONVERGED verdict. Adjudicate by reading the code, and record the adjudication."*

**Codex's CONVERGED was wrong, and I established that by measurement rather than by preferring the
other reviewer.** This is the fourth time in this project's history that the finding-reviewer beat a
CONVERGED verdict — the pattern in `dual-review-disagreement-is-the-signal` now has another instance.

Codex was not lazy: it ran `tsc`, the full 2638-test unit suite, four integration files, and its own
mutation of the settle retry. It reported real work. It still missed three Highs, one of which
silently restores the defect the branch exists to fix. **A reviewer that runs the gates inherits the
gates' blind spots** — which is exactly why the round was dual.

## Adjudication of each finding

| id | source | verdict | how established |
|---|---|---|---|
| **H1** budget VALUE unasserted at the call site | Claude | **CONFIRMED — fixed** | I re-ran the mutation myself: `SERVE_BUDGET` → `{attempts:3, attemptTimeoutMs:60_000, …}` at `serve-doc.ts` gave `tsc` exit 0, **1786 unit tests green, 59 integration tests green** |
| **H2** residual traded for a log that does not exist | Claude | **CONFIRMED — fixed** | Spec §3.5.1 verbatim: *"a `put` timeout is logged with elapsed time and the target key"*; `model-store.ts` contained no `console` call |
| **H3** a DB-refused settle read as settled | Claude | **CONFIRMED — fixed** | `settle_serve_model` `returns boolean`; `if not found then return false` (`0020:280`). `callRpcBounded` sets `ok` on transport success, so `{ok:true,data:false}` read as settled |
| **M1/C-1** settle counted once, runs twice | Claude **and** me, independently | **CONFIRMED — fixed** | Same defect found by two passes that could not see each other. Sum now pays for both settles unconditionally |
| **M2** anti-drift pin covers 1 of 3 literals | Claude | **CONFIRMED — fixed** | Claude measured `SERVE_MARGIN_MS` 20_000→21_000 going red *pointing only at the CHECK* |
| **M3** reserve timeout permanently strands 6¢ | Claude | **CONFIRMED — deferred, backlog #28** | I verified the load-bearing word *"permanently"*: a later reserve overwrites `release_token` (`0020:251-254`) while `settle_serve_model` matches only `(owner_id, release_token)` (`:277-280`), so the stranded ledger entries are unreachable forever |
| **L1** migration guards invisible to the ratchet | Claude | **CONFIRMED — deferred, backlog #29** | `check-guard-coverage.py` output is byte-identical with and without 0024 |
| **L2** constraint sweep drops by substring | **Codex and Claude, independently** | **CONFIRMED — fixed** | Sweep now matches `lease_ttl_seconds[[:space:]]*>=`, so an operator's upper bound survives |
| **L3** `fakeRpcBuilder` discards the signal | Claude | **ACCEPTED, recorded** | True, and the premise was verified directly against `postgrest-js` instead. Recorded so the next round knows the fake is not evidence |

## What each reviewer uniquely contributed

- **Codex alone:** L2 (the substring sweep). Claude found it too, independently — the only overlap.
- **Claude alone:** H1, H2, H3, M2, M3, L1, L3. H1 is the finding of the round.
- **Coordinator alone:** nothing the others missed; my C-1 = Claude's M1. Useful as corroboration,
  not as coverage.

**The honest read on my own pass:** re-deriving one inherited assumption found a real Medium, and
found *nothing* of H1's severity. The assumption I chose to re-derive was the arithmetic — which is
the thing the spec had already graded Blocking once, so it is where I was already looking. H1 lived
where nobody had looked, which is the definition of a blind spot and the argument for a reviewer who
did not write the code.

## The lesson H1 carries, stated plainly

Task 3's mutation check **passed**: dropping the budget inside `generateMagazineModelForServe`
turned three tests red. The wrapper was proven load-bearing. But the wrapper is not the call site,
and a `required` positional parameter of type `ServeBudget` defends against **omission**, not against
**a wrong value of the right shape**.

> Mutation testing proves a guard is LOAD-BEARING. It never proves the assertion set is COMPLETE.
> — `docs/review-method.md`, written after a decision that had an assertion *and* a passing mutation
> and broke anyway.

The repo already knew this. It is now the second measured instance, and the fix (assert the value at
the boundary, plus an import guard against the unbounded twin) is the one the **spec had already
ordered in §5** and that no gate noticed was missing.

## Process defect in how I RAN this round

Both reviewers worked in the **same worktree**. Codex's `attempts = 1` mutation was live while
Claude was running the full suite, producing one unattributable red
(`serve-doc-mapping.test.ts` *"retries the settle ONCE"*, `Expected: 2 / Received: 1`) that Claude
correctly declined to charge to the branch. This project has already measured that hazard — *"an
instrument that edits the repo corrupts its peers; two concurrent reviewers got 23/44 vs 44/44 on
the same commit"* — and I reproduced it anyway.

**Round 2 runs each reviewer in its own git worktree.**

## Gate status entering round 2

`tsc --noEmit` clean · unit **263 suites / 2647 tests** · full integration **66 suites / 482 tests,
green twice back-to-back after a `db reset`** · 4 fixes mutation-checked, each turning exactly its
own test red · migration 0024 verified to apply from scratch on a reset database.

One artifact worth recording: the *first* full integration run immediately after a cold `db reset`
showed 3 unrelated failures; that reset had pulled a new `edge-runtime` image and was still
restarting containers. A second clean reset reproduced green, twice. Container readiness, not the
change — recorded rather than waved away.
