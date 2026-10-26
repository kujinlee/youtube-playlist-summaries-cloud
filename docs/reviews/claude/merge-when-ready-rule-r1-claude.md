# merge-when-ready-rule — round 1, Claude adversarial review

Subject: branch `merge-when-ready-rule` at `ca4498a0`, `git diff origin/master...HEAD` (7 files).
Mandate: refute. Every finding below was produced by running code, not by reading it alone.

Baseline executed: `python3 scripts/check-merge-ready.py --self-test` → `114/114 self-test cases passed`.
`check-fixture-variation.py`, `check-selftest-counts.py`, `check-main-drivable.py`,
`check-ratchet-contract.py`, `check-docs.py` (215/215) all rc=0 on the branch. `check-rc-contract.py`
rc=0, but `grep merge-ready` in it finds nothing, so it says nothing about the new rc 3. NOT RUN: the `--mutate .` sweep
over the 14 new manifest entries.

## What the code claims about its own bound

`scripts/check-merge-ready.py:473-475`: *"A weakening that lowers no pin or count, edits no baseline,
and removes no line on a failure path merges as READY."* The bound is stated honestly. Findings 1-3
are not that bound. In each one a line on a failure path IS removed, or the file holding it is
deleted, and the PR still gets no HOLD.

## Findings

### H1 — High — a comment explaining the removal pushes it out of the window (`scripts/check-merge-ready.py:546-554`)

`code` drops comment lines from the list, but each kept entry still holds its ORIGINAL `enumerate`
index. So comment lines and blank added lines still count toward the `abs(j - i) <= k`
distance, even though they can never anchor. I took PR #398's own fixture (the case the window was
tuned on) and added six `+    # trigger 4 retired: reason N` lines between the removed entry and
`fails.append`:

```
A0 control #398: ['loosens a gate: scripts/check-x.py removes or rewrites 1 line(s) on a failure path, ...']
A1 +6 comment lines explaining removal: []
A1b +6 blank added lines: []
```

An honest author will usually leave a comment saying why a check was removed. That comment is enough
to defeat the detector, so the evasion is the common case, not a contrived one. Fix: measure distance
over the filtered list, or over removed and context lines only (positions in the old file), so added
lines cannot dilute the window.

### H2 — High — deleting a whole gate file is never held (`scripts/check-merge-ready.py:497`, `:534-536`)

For a deleted file, `--- a/X` sets `cur`, then `+++ /dev/null` sets `cur = None`. That discards every
removed line in `diff_lines`, and `failure_path_removals` keys its hunks on `path=None`. Nothing
applies `GATE_CODE` to the `files` list either. Executed result:

```
A2 delete whole gate file (print('FAIL') / sys.exit(1) removed, +++ /dev/null): []
```

Deleting `scripts/check-foo.py` together with its `ci.yml` step leaves CI green and prints READY.
This is the strongest loosening there is, and the detector is blind to it by construction. Fix: if a
`GATE_CODE` path appears with `+++ /dev/null` (or under `git diff --diff-filter=D --name-only`), hold.

### H3 — High — `FAIL_PATH` misses how this repo's hooks actually block (`scripts/check-merge-ready.py:484`)

The hooks block through `deny "..."`, which emits a `permissionDecision` (`block-default-branch-push.sh:98-108`),
or through `exit 2` (`enforce-handoff-path.sh:82`, `enforce-selection-card.sh:102`, `block-idle-stop.sh` ×5).
`FAIL_PATH` matches neither of these. It also misses `failures += 1` and `raise SystemExit(1)`. I ran
real `git diff -U5` over copies of the two hooks (kept in a scratch repo, not the worktree):
the `--no-verify` `deny` became `:`, and `enforce-handoff-path.sh`'s `exit 2` became `exit 0`:

```
['.claude/hooks/block-default-branch-push.sh', '.claude/hooks/enforce-handoff-path.sh']
[]          # hold_reasons → no HOLD; both blocks neutered
```

The same run on synthetic diffs: `-    exit 2` in a hook → `[]`; `-        failures += 1` → `[]`;
`-        raise SystemExit(1)` → `[]`. `GATE_CODE` includes `.claude/hooks/*` in its scope, but for
hooks the anchor vocabulary covers almost none of their failure paths. Fix: add `exit 2`, `\bdeny\b`,
`permissionDecision`, `failures\s*\+=`, `SystemExit\(` and `return 2` (CANNOT RUN paths) to `FAIL_PATH`.

### M1 — Medium — gates outside `GATE_CODE` (`scripts/check-merge-ready.py:485`); scope question for the owner

Each of these, with `-  exit 1` and a removed `run: python3 scripts/check-docs.py` line, got `[]`:
`scripts/check-schema-gates.sh` (the "one command for all thirteen schema gates"),
`scripts/ci/start-schema-db.sh`, `.github/workflows/ci.yml`, `.claude/settings.json` (unregistering a
hook), `scripts/codex-review.py`, and `.claude/hooks/lib/x.sh` (the regex has no subdirectories). A
removed CI step is the most direct way to loosen a gate. Out of scope by the owner's card? The card
said "loosening only", not "loosening in `check-*.py`". `GATE_CODE` is the implementer's reading,
and neither the code comment nor `dev-process.md` says those files are excluded. At a minimum,
`.github/workflows/*.yml` and `scripts/check-*.sh` belong in it, or the exclusion should be stated
in the bound at `:473-475`.

### M2 — Medium — a deleted or renamed pin is not a lowered pin (`scripts/check-merge-ready.py:576`)

`if path in new and new[path] < old[path]` gives:

```
A7  pin line deleted ('-    "scripts/check-x.py": 12,')            : []
A7b pin key renamed and lowered (check-x 12 -> check-y 3)           : []
```

Removing a script's entry from `EXPECTED_MUTATIONS` deletes all twelve of its mutations from the
gate. That is a larger loosening than 12 → 11, and it is the case that passes. Lowering the
`PIN_TOTAL` alongside it does trigger, but only when the total line is edited too. Fix: treat
`path in old and path not in new` as a drop to 0.

### M3 — Medium — the "NO-ENTRY does not hold" case passes for an ambient reason (`scripts/check-merge-ready.py:1129`, `:799`)

`H(body="NO-ENTRY: docs only", nr=False)` passes a `body` that `hold_reasons` never receives (`H`
drops it), so the case asserts only `nr=False → []`. The real discrimination happens in `main()` at
`:799`, and no `main()` case uses a NO-ENTRY body. I mutated a /scratch copy of `:799` to
`nr = any(v is not None for v in granted_escapes(...).values())`, so that ANY granted escape holds:

```
rc=0
114/114 self-test cases passed
```

The owner chose the "NO-REVIEW only" reading, and this mutation reverses it with the suite still
green. Fix: a `_main([...], body="NO-ENTRY: docs only\n")` case that expects rc=0, plus a mutation
entry for it.

### M4 — Medium — "a move" is any identical line anywhere in the file (`scripts/check-merge-ready.py:551`)

`readded` is file-wide and matches on stripped text, so the common failure lines repeat throughout a
gate (`return 1`, `sys.exit(1)`). Removing one from a live branch and adding `return 1` inside an
unused function was treated as a move:

```
A3 return 1 'moved' into dead code: []
```

It also happens without intent. A PR that deletes one guard branch's `return 1` and, elsewhere in the
same diff, adds a new function that ends in `return 1` gets no HOLD. Fix: count a removal as moved only
when the re-added line keeps a neighbouring line of context, or only for lines that are not on
`FAIL_PATH`.

### L1 — Low — stale prose still says merge is always a human gate

- `docs/process-checklists.md:26`: *"(push/merge/deploy — always a human gate)"*. This contradicts the
  new rule and the 2026-09-30 push removal.
- `docs/process-rationale.md:1059`: *"merging is still the human gate"*. As history this is
  acceptable, but nothing marks it as superseded.

`dev-process.md` is updated, but the checklists doc is the one its spine says to read "when you are
working a gate".

### L2 — Low — `--app-tests-passed` wording implies a record exists (`scripts/check-merge-ready.py:601-602`)

The HOLD text says *"no local test:integration + test:e2e run is recorded at this head"*. Nothing
records anything. The flag is the merger's own assertion and the script compares two strings. The
`--help` text and the docstring (*"after a local … run at that head"*) are accurate, and no prose I
found claims the script verifies the run. But nowhere does the text say that it is self-attested.
Suggested wording: "…and no `--app-tests-passed <head>` was given (self-attested; the script does not
run or verify the tests)".

## Directions checked and NOT found broken

- **Exit-code contract.** `grep -rn check-merge-ready` over `.github/ .claude/ scripts/` and the process
  docs finds no programmatic caller. The only consumers are humans or agents reading
  `dev-process.md:36-41`, the hook message at `block-default-branch-push.sh:223` and
  `docs/CLAUDE.md:18`. All three say READY ⇒ merge, so rc 3 is never misread as a CANNOT RUN by a
  machine. `main()` returns 3 before printing the "local sweep" warning, which keeps a HOLD from being
  dressed up as NOT READY.
- **Wrong subject.** The house-rule diff uses local `HEAD`, but `:394` already refuses when PR
  `headRefOid` ≠ local HEAD, so the diff cannot describe a different tree.
- **False-hold rate.** I replayed `hold_reasons` over the last 39 first-parent squash commits on
  `origin/master` with `git diff -U5 SHA^ SHA`, with app tests assumed passed and no waiver. It held
  5: #398, #387, #382, #381 (the decision-scheme work, which genuinely loosens) and #360, where the
  four lines flagged in `check-ratchet-contract.py` look like a refactor
  (`def main(...)`, `ci_path = ...`), so probably a false hold. 1 in 39 does not set off backlog #56.
  This branch itself, replayed, gets no HOLD.
- Migration and app-code regexes: `supabase/schema.sql`, `seed.sql`, `functions/…` and `config.toml`
  are all held as app code. Over-broad but safe in direction.

## Summary

High 3 (H1 comment-padding evasion, H2 gate-file deletion, H3 hook block vocabulary), Medium 4,
Low 2. H1-H3 each show a diff that loosens a gate and prints READY, and each falls outside the bound
the code states for itself. None is the owner's chosen exclusion.

VERDICT: NOT CONVERGED
