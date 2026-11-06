# Round 2 — `seed-varied-sweep` (backlog #506, its last part) — coordinator — NOT CONVERGED (Codex), folded

```yaml
round: 2
fixes_nontrivial: true
subject: seed-varied-sweep
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: instrument, fix_induced: true, component: seed-outcome, disposition: fixed}
```

REVIEW GAP: claude — alternation, per `review-method.md` -> Round topology: the coordinator authored the round-1 fold,
so round 2 goes to the half that did not write it (Codex). Not a failure to run.

Codex reviewed `f25ab1aa` and reported one MAJOR, with a runnable reproduction (`/tmp/svs-r2-adversarial.py`). It also
re-ran every round-1 reproduction against the fold: all fail closed.

## The finding

**XM1 (Codex MAJOR) — FIXED. `fix_induced: true`:** the clause is round 1's own fold (r1 Codex M2 added the
"completed under some seeds, not others" rule) and it decided completion with `"passed" in out` — a substring of
everything the child printed. A case NAMED `value passed validation` therefore read as a completion summary, and a
mutant whose suite crashed before its summary under seed 7 was credited `1 killed, 1 attributed, 0 survivor(s)`.

**Fix — one definition of the summary LINE.** `check-plan-code.py` now has `SUMMARY_LINE` and `summary_total(out)`:
the denominator of the LAST line that WHOLLY matches a summary shape, else None. The shapes are enumerated from the
scripts' own `print` calls and then CHECKED by running all 88 suites that a manifest mutates or
`check-selftest-counts.py` pins: `N/M passed`, `N/M cases passed`, `N/M self-test cases passed`, `N/M cannot-run cases
passed`, `N of M self-test cases passed`, each optionally led by `self-test: `, and one the grep of f-strings MISSED and
the run found — `check-storage-independence.py`'s `self-test: N cases, N passed, N failed`. Without that arm its control
(rc 0) would have read NOT green, so the nightly sweep would have called that whole manifest CANNOT RUN. The other 87
suites read green under the new rule (four first read red only under concurrent load and were re-run alone: all green,
whole-line summary present).

Three consumers now share it:

- `seed_outcome`'s completion test (the finding);
- `control_is_green` — the same substring, the class (below);
- `check-selftest-counts.py`'s `printed_total`, which kept its OWN copy (`RATIO` + the word `passed` anywhere on a line).
  It now borrows `summary_total` (added to `BORROWED`, so a rename upstream is a loud ImportError, not a crash), and
  `RATIO` is deleted. Its 60 cases are unchanged and still green, now exercising the borrowed rule.

**Cases (red first, then green).** Codex's fixture verbatim, through `run_mutations` with seeds `(3, 7)`:
`⛔ r2 Codex M1 END TO END: a seed that crashed before its summary is never credited as a kill` — red before the fix
with `(True, [True], False)`, i.e. ok and caught. Unit: `⛔ r2 Codex M1: a case NAME containing `passed` is not a summary
— the stopped seed is still a cannot-run` and the shape-inside-a-case-name case `...nor is a case name that CONTAINS the
whole summary shape: only a summary LINE completes a suite` (`[FAIL] 3/4 passed is the shape`) — both red before.
Then `⛔ r2 Codex M1: a control that exits 0 printing only a case name with `passed` in it is NOT green`, and four
`summary_total` cases: every shape, a ratio line without `passed`, last-wins, and `[FAIL]`/backticked labels -> None.

## The class — every other place `check-plan-code.py` infers completion or a kill from the child's output

Searched every non-self-test read of a child's output (`in out`/`in so`/`in se`, `startswith`, `parse_fail_names`,
`control_is_green`, `rc ==`):

| Site | Reads | Verdict |
|---|---|---|
| `seed_outcome` completion | was `"passed" in out` | **the finding — fixed** |
| `control_is_green` (`control_parts`, the before-control and the re-control in `mutate_delivered`) | was `rc == 0 and "passed" in out` | **same defect — fixed**: an rc-0 suite that printed a case name containing `passed` but no summary read GREEN. The file's own comment had already noted it ("two of the 434 live manifest names contain `passed`… held by a naming coincidence"); updated |
| `parse_fail_names` (attribution) | a line that STARTS with `[FAIL] ` | already line-anchored, not a substring — sound |
| kill / survive / cannot-run | the EXIT CODE (`rc == 1`, `rc == 2`) | not output — sound |
| `ev_files[...]["tail"]` | the last line | display only, decides nothing |

⚠ **A related, pre-existing exposure, not a substring and not fixed here:** a suite that prints its named `[FAIL]` and
then CRASHES exits 1, which the harness reads as a kill — in the unseeded run, and in a seeded run when every seed
crashes at the same place (pinned as `...ADJACENT: a suite that stops at the same place under EVERY seed is judged as the
unseeded run judges it`). `summary_total` would now let a later change require a summary for a kill too; that is a
change to the unseeded harness's verdict and is out of this round's scope.

## Mutations

`scripts/mutations/check-plan-code.json` 215 -> 224 (pin updated, with its reason): seed completion back to the
substring; control greenness back to the substring; whole-line `fullmatch` -> `search`; last -> first; and one per
`SUMMARY_LINE` arm (`passed`, `N of M`, `self-test: `, the `cases` words, `N cases, N passed, N failed`). The r4 M1
entry ("a control is called green on its EXIT CODE alone") was RE-BOUND to the new line — its old anchor was gone.
`scripts/mutations/check-selftest-counts.json` 36 -> 34: its three `printed_total`/`RATIO` entries left with the rule;
one new entry pins that `printed_total` still reads the borrowed rule.

**All 11 new or re-bound entries killed, each by the case it names** — measured on a fresh APFS clone of the worktree
per mutant with `HOME` redirected into the temp directory (never in place), running the mutated file's own
`--self-test`: every one exits 1 with every `expect` case among its red cases (the ten in check-plan-code.py at
357–359/360; the check-selftest-counts entry at 52/60).

Every anchor in every manifest (3,821 entries) binds exactly once, applied sequentially.

## Gates

| Check | Result |
|---|---|
| `check-plan-code.py --self-test` | 360/360 passed (352 + 8 new cases; docstring count updated) |
| `check-selftest-counts.py --self-test` | 60/60 passed |
| `check-selftest-counts.py` (full) | rc 0 — 79 scripts declare a count, every one verified by running it |
| `check-ratchet-contract.py` | rc 0 |
| `check-docs.py` | rc 0 |
| `check-fixture-variation.py` | rc 0 (first run caught `control_is_green(rc=…)` never varied; a case at rc 1 added) |
| `check-guard-coverage.py` | rc 0 |
| summary rule over the 88 real suites | 88/88 green, each with a whole-line summary |
