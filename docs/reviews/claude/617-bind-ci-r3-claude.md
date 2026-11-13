Reviewed head: a2c28a43c90eafb90baf07a409b59b2a1ec43e4b

# Round 3 — `617-bind-ci` (backlog #617 part 1) — Claude half

Reviewed SHA: `a2c28a43c90eafb90baf07a409b59b2a1ec43e4b` (branch `617-bind-ci`, clean tree).
Subject: `ci_flaky_contract` in `scripts/sweep-red-alert.py`, against `.github/workflows/ci.yml`.

Run by this reviewer:
- `python3 scripts/sweep-red-alert.py --self-test` → **49/49 passed**.
- `python3 scripts/check-plan-code.py --mutate . --only scripts/sweep-red-alert.py` → **37 mutations, 37 killed, 37
  attributed to the case each names, 0 survivors**, rc 0.
- Drift probes: run against in-memory copies of the real `ci.yml` (a scratch script that imports the module and calls
  `ci_flaky_contract`); no tracked file was edited. Each finding below quotes the probe's result.

Not re-raised (filed in r1): `- if:` before `name:`, `${SHARD_INDEX:-0}`, the contract-before-`read_flaky` order, the
duplicated block walk (Cm5).

## Findings

### M1 — MAJOR — the r2 reassignment check sees only `VAR=`; an arithmetic increment slips through (the class of r2 XM1, only its instance fixed)

`scripts/sweep-red-alert.py:127` — `re.search(rf"(^|[^\w$]){var}=", l)`.

Inserting any of these lines before the `grep` in the writing step leaves the contract **ok** (probe result `ok` for
each):

```
((SHARD_INDEX++))        let SHARD_INDEX++        SHARD_INDEX+=1
read SHARD_INDEX < …     unset SHARD_INDEX
```

Failure scenario (criterion (a)): someone "fixes" the index to 1-based — and `ci.yml` itself invites it, its own
comment at `ci.yml:1127` says *"the shards are 1..job-total"* — with `((SHARD_INDEX++))` before the write. Every shard
writes `shard-1.txt` .. `shard-38.txt`, the PR's self-test stays green (the contract is ok), and on master every run
reports `shard-0.txt` missing: the FLAKY scan is NOT RUN for shard 0 on every master sweep, while `shard-38.txt` is
never read at all. That is exactly the drift r2 XM1 was folded to catch; only the `=` spelling of it is caught.
`+=` matters on its own: `SHARD_INDEX+=1` appends, so shard 0 writes `shard-01.txt`.

Caused by the fold? **Not introduced** by it, but it is the r2 XM1 fold's incompleteness — instance-not-class. A class
fix is to refuse ANY occurrence of the variable's name in the step's script that is not a `$VAR` / `${VAR}`
expansion (which also covers `read`, `unset`, `let`, `declare`, `(( ))`, `for VAR in`); see m2 for the cost of that
rule on a debug `echo`, which the folder must weigh in the same edit.

### m2 — MINOR — false RED: a debug `echo "SHARD_INDEX=$SHARD_INDEX"` in the writing step is read as a reassignment

`scripts/sweep-red-alert.py:127`. Probe: inserting `echo "SHARD_INDEX=$SHARD_INDEX SHARD_TOTAL=$SHARD_TOTAL"` (or
`echo "::notice::shard SHARD_INDEX=$SHARD_INDEX"`) before the `grep` → **RAISED** *"the step that writes the shard file
reassigns `SHARD_INDEX`"*. The `"` before the name is in `[^\w$]`, so the regex matches inside a string.

Failure scenario (criterion (b)): a harmless diagnostic line — the most likely edit anyone makes to a CI step being
debugged — turns the PR red with a message claiming a reassignment that does not exist; and if it reached master, the
contract raises before `read_flaky`, so the FLAKY names present that night are not filed (the filed r1 order point,
now reachable by a harmless edit).

Caused by the fold? **Yes — r2 XM1's fold** introduced the regex.

### m3 — MINOR — false RED: a `- ` line inside the writing step's script becomes the step's start

`scripts/sweep-red-alert.py:122` — `st = max(i < wi where lines[i].lstrip().startswith("- "))`. The scan does not know
it is inside a `run: |` block. Probe: a step-summary heredoc before the write,

```
          cat >> "$GITHUB_STEP_SUMMARY" <<EOF
          ## Shard $SHARD_INDEX
          - seeds: $SEEDS
          EOF
```

→ **RAISED** *"the shard file is named by `$SHARD_INDEX`, which is not `${{ strategy.job-index }}`"*: `st` lands on the
`- seeds:` line, the step "ends" at the next script line (same indent), and the step's real `env:` is outside
`lines[st:end]`. A bash array continuation line starting `- ` does the same. (Side effect of the same scan: the
heredoc's `## Shard` line is dropped by `_uncomment` — harmless here, but `_uncomment` treats shell/heredoc text as
YAML everywhere.)

Failure scenario (b): adding a Markdown job summary to the sweep step — a common, harmless edit — is a false red with a
misleading message. Fix shape: take `st` as the nearest `- ` line whose indent is LESS than the write line's (a step
item is always shallower than its `run:` script body).

Caused by the fold? **Yes — r1 Cm3's fold** (step scoping) introduced `st`; r2's `end` computation inherits it.

### m4 — MINOR (file, not fold) — a second matrix axis or an `include:` entry is a SILENT miss the contract cannot see

`scripts/sweep-red-alert.py:89` (`shard_count`) with `read_flaky` reading `range(shards)`. The contract proves the file
is named by `strategy.job-index`, but the read range is the length of the `shard:` list, not `job-total`. Adding a second
matrix dimension (or one `include:` job) makes job-index run past `len(shard)`: files `shard-38.txt` … are written,
uploaded and downloaded, never read, and nothing is missing — **no red, the FLAKY names in those shards are never
filed**. Pre-existing (backlog #495's `shard_count`), outside the two links the docstring scopes, and low realism today
(`ci.yml:1126` says only the list's length matters). Recommend filing: assert the `matrix:` block has exactly one key
and no `include:`, or read the count the same way the files are named.

Caused by the fold? **No.**

## Criterion (d) — mutants

All 13 `#617` mutants in `scripts/mutations/sweep-red-alert.json` read against the cases they name; each is killed by
the clause in its name, not a second reason:
- `len(writes) < 1` is killed by the second-write element of its tuple case; the `.txt` lookahead mutant by the
  `.txt".bak` element; the two `_uncomment` mutants by the inline-comment and comment-line elements respectively.
- the `<= ind` → `< ind` and `break` → `pass` mutants are both killed by the later-step-with-`with:` case (both make
  `withs` two long). The `end = wi or …` mutant is killed by the synthetic `env:`-below-`run:` workflow.
- the job-index mutant is killed by the `$SHARD_TOTAL` case through the `job-total` value, not through the
  reassignment check (`SHARD_TOTAL=` does not occur in the step).
Unpinned but harmless: `len(withs) != 1` has no case of its own (zero `with:` blocks would IndexError — still a raise
in `main`, but uncaught by the self-test's `_contract`, which catches only `ValueError`).

## Summary

| ID | Severity | Criterion | Fold-induced |
|---|---|---|---|
| M1 | MAJOR | (a) `((SHARD_INDEX++))` / `+=` / `let` / `read` / `unset` pass; master NOT RUN for shard 0 | r2 XM1 incomplete (instance, not class) |
| m2 | MINOR | (b) debug `echo "SHARD_INDEX=$…"` is a false red | yes, r2 XM1 |
| m3 | MINOR | (b) a `- ` line in the run script (heredoc summary) moves the step start → false red | yes, r1 Cm3 |
| m4 | MINOR | (a) second matrix axis → files past `len(shard)` silently unread | no — file |

VERDICT: NOT CONVERGED
