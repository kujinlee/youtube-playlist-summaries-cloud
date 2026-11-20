Reviewed head: 760b7092045e0374633fbcd33a91e60095655369

# PR #606 (running-now-worktree, backlog #672) — round 3, Claude half

Scope: `git diff af7e905f..760b7092` (the round 2 fold) plus every mode of `main()` in `scripts/goal-tree.py`,
because the fold moved the clock read. Mandate: try to refute that the fold is correct.

## What was measured

| Check | Result |
|---|---|
| `python3 scripts/goal-tree.py --self-test` at 760b7092 (worktree) | rc=0, `553/553 self-test cases passed` |
| Same, on a full `git archive HEAD` copy outside the repo (baseline) | rc=0, 553/553 |
| The new mutation ("PR #606 r2 Codex: --owed-idle reads its clock outside the CANNOT RUN handler"), applied to a second copy | rc=1, 552/553; the ONLY failure is the case it names: `got ('RAISED OSError: clock failed', [])`, `want (3, [True])` |
| Reverting the fold = the mutation's two edits (it restores the af7e905f placement exactly) | so the new case is measured to fail without the fold |
| All 467 manifests in `scripts/mutations/goal-tree.json` anchor once in the file | 467 manifests, 0 unresolved; `EXPECTED_MUTATIONS["scripts/goal-tree.py"] == 467` |
| Docstring case count | `# 553 cases` matches the run |

The mutation harness sweep (`check-plan-code.py --mutate . --only scripts/goal-tree.py`) was NOT run (467
manifests would exceed the per-call bound); the kill was checked by applying the manifest's edits by hand and
running the self-test, which is what the harness does for one manifest.

## main(), mode by mode (`scripts/goal-tree.py:2961-3087`)

- `--self-test` returns at `:2978`, before any clock read — unchanged.
- `--owed-idle` (`:2989-3001`): `read_clock()` is now the first statement of the `try` (`:2993`). If it raises,
  `except Exception` builds the bounded CANNOT RUN line; nothing after the handler reads `now` or `judge`, so no
  UnboundLocalError path (`judge` is unbound on that path but never read; `now` is a parameter, always bound).
  It still reads its clock with no collect in this mode, as before.
- Every other mode: `now, judge = read_clock()` at `:3002` is the first statement after the `--owed-idle`
  block — the same position relative to all following code as in af7e905f (where it sat immediately before
  `if a.owed_idle:`, which returns). Behaviour of `--record-agenda` (re-read after `collect` at `:3035`),
  `--tick-agenda` (uses `now` from `:3002`, or from `:3035` when combined with `--record-agenda` — as before),
  `--snapshot` (re-read after collect at `:3046`, r1 XM2 intact), `--page` and `--print` (use the latest `now` /
  `judge`) is unchanged. `judge` is bound at `:3002` before every use at `:3075`.

## Findings

None at BLOCKER or MAJOR. One MINOR observation, not fix-induced, recorded for completeness:

1. **MINOR — `scripts/goal-tree.py:2993`, inferred, fix-induced: no.** `--owed-idle` reads its clock BEFORE
   `main_checkout` (a git subprocess) and before it reads the log's last line. A snapshot appended between the
   two would be stamped after `judge`. Input: a snapshot logged in the sub-second window between `:2993` and the
   `_last_line` read; output: an age of a few seconds the wrong side of zero at most. Same order as af7e905f and
   as the pre-PR code, so not caused by this round; not worth a fold. Not filed by me.

Pre-existing, out of scope: a FAILING clock in any mode other than `--owed-idle` still raises a traceback
(`:3002`). Only `--owed-idle` has a hook contract (exit 3 = "I printed my own CANNOT line",
`.claude/hooks/session-state.sh:22-23`), and the other modes are run by hand or by `regen-pages.py`, where a
traceback is loud. Not a finding.

## Loosening answers

- **Does the fold loosen any gate?** No. Before it, a failing clock under `--owed-idle` raised: python exit 1,
  so the hook printed its own CANNOT RUN line. After it, the script prints a bounded CANNOT RUN line naming the
  exception and exits 3, and the hook stays silent. Either way exactly one CANNOT RUN reaches the session; the
  fold improves the message (it names the cause), it does not turn a failure into a pass.
- **Does the broad `except Exception` swallow anything new?** It now also covers the clock; every exception it
  catches still produces a line beginning `OWED_IDLE_CANNOT` and "treat as NOT RUN", and exit 3 — never 0.
- **Was a case or mutation weakened or retired?** No. 466 -> 467, none retired; the r1 mutation "r1 Claude F4:
  --owed-idle ignores the clock it is given" still anchors.
- **Can the new case pass for an ambient reason?** No: it requires exactly one output line that starts with the
  CANNOT prefix, names "clock failed" and fits the width, and rc 3; the mutant gives a raise and no stdout.

VERDICT: CONVERGED
