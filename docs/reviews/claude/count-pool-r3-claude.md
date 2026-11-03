Reviewed head: dc6a390997111db7bf4ed742cd5cba0de666a4f4

# count-pool — round 3, Claude half (PR #487, branch `build-count-pool`)

Scope: the two commits no round has seen — `6b5d8b6b` (merge of origin/master `bbefd7a8`) and `dc6a3909`
(`scripts/check-selftest-counts.py` removed from `MAIN_DEBT`). Adversarial mandate: try to refute that the merge
is faithful and that the pin removal is earned.

## Checks run

| Check | Result |
|---|---|
| `git diff 7a44034f 6b5d8b6b -- <PR paths>` vs `git diff $(merge-base) bbefd7a8 -- <same>` | Identical apart from blob ids and hunk offsets: the merge brought in exactly master's ci.yml (24 -> 18 shards + note) and check-plan-code.py (`sweep_needed` shard note) changes; nothing in `check-selftest-counts.py` or `scripts/mutations/` changed |
| `git merge-tree --write-tree c8f339e8 bbefd7a8` then `git diff <tree> 6b5d8b6b` | Only `docs/dashboard-entries.md` differs: the conflict region resolved by keeping BOTH 2026-11-03 entries under two headings. Neither entry lost a line. Duplicate date headings are normal in that file (`grep '^## ' \| sort \| uniq -d` lists dozens) |
| `grep -n check-selftest-counts .github/workflows/ci.yml` | `:714 run: python3 scripts/check-selftest-counts.py --jobs 4`, `:717 ... --self-test` |
| `grep -n 'shard: \[' .github/workflows/ci.yml` | `:1132 shard: [1, ..., 18]` — master's 18-shard matrix survived |
| `python3 scripts/check-main-drivable.py --report` | rc 0; `scripts/check-selftest-counts.py  rebind`; 54 in population, 29 driven, 25 pinned |
| `python3 scripts/check-main-drivable.py` (live) | rc 0, `D2 OK — every guard with a main() either drives it over a constructed world or is pinned.` |
| `python3 scripts/check-main-drivable.py --self-test` (background, polled) | `455/455 passed`, rc 0 |
| `python3 scripts/check-selftest-counts.py --self-test` (background, polled) | `59/59 self-test cases passed`, rc 0, 0 `[FAIL]` lines |
| `grep -rn MAIN_DEBT scripts/` outside check-main-drivable.py | Only prose in `check-decision-scheme.py` and anchors in `scripts/mutations/check-main-drivable.json` (`assess(texts, MAIN_DEBT, ...)`, `live_reconcile(live, MAIN_DEBT)`) — none counts its size; the "25 pinned" figure is computed at runtime |
| Mutation probes of `main`'s wiring, on a scratch copy outside the repo | 3 of 3 survive — see M1 |
| `git merge-tree --write-tree HEAD origin/master` (master now `4c279a2d`) | CONFLICT in `docs/backlog.md` and `docs/dashboard-entries.md` — see L2 |

## Findings

### M1 (Medium, pre-existing, FILE not fix) — the case that earned the pin removal drives only `--jobs`; `main`'s scope wiring is undefended, including a false green

`scripts/check-selftest-counts.py:1062-1085`: the only `main()` calls in the suite replace `audit` with
`fake_audit`, which records only `jobs`. So D2 credits the script with the `rebind` route (correct per that
detector's rule — the case does rebind a global `main` reads) and `dc6a3909` had to remove the pin. But the
residue D2 exists to cover is mostly not covered. Each of these mutants of `main` leaves the suite at
`59/59 self-test cases passed`, rc 0:

- `:731` `audit(ROOT, POPULATION, pc.count_drift, pc.child_env, only, jobs)` -> `... None, jobs)` (`--only`/`--changed` silently run everything);
- `:719` `only = only_names(args.only, POPULATION)` -> `only = None`;
- `:721` `only = changed_scope(ROOT, POPULATION, args.base)` -> `only = set()` — **`--changed` then always prints "nothing to check" and exits 0: a false green.**

Not introduced by this PR: on the merge base `main()` took no argument and sat in `MAIN_DEBT`, so this wiring
was undefended before too. CI runs the full set (`--jobs 4`, no `--changed`), so CI is unaffected; `--changed`
is a local path. What changed is the claim: the debt list no longer says this `main` is undriven. The commit
subject also says "drives main(argv)" where the detector reports `rebind`, not `argv`. Suggested fix direction
(a backlog row): let `fake_audit` record `(root, pinned, only)` too, and add one `main(["--changed", ...])` and
one `main(["--only", ...])` case asserting the `only` the audit received.

### L1 (Low) — the dashboard entry and backlog #487's closing cell carry the pre-fold counts

`docs/dashboard-entries.md:18682`: "Self-test 40 → 51 cases; mutation manifest 23 → 29, scoped sweep 29/29
killed". The suite is 59 cases (`scripts/check-selftest-counts.py:94`, and the run above) and the manifest has 36
entries (`scripts/mutations/check-selftest-counts.json`); the round-1 coordinator record states "51 → 59" and
"29 → 36". Backlog #487's DONE cell (`docs/backlog.md:468`) likewise says "scoped sweep 29/29". Present at
`7a44034f` already, so not a merge defect — prose that the fold did not update.

### L2 (Low, readiness, not code) — master moved again and the branch no longer merges cleanly

origin/master is now `4c279a2d` (#488, docs). `git merge-tree` reports conflicts in `docs/backlog.md` (master
adds row 489 where the branch adds its own row) and `docs/dashboard-entries.md` — both append-at-end conflicts of the
same shape as `6b5d8b6b`'s. None of the PR's code paths are touched by master's new commits.

## Conclusion

The merge is faithful: re-doing it mechanically gives the same tree except for the dashboard conflict, which kept
both entries intact; ci.yml keeps `--jobs 4` and the 18-shard matrix. The `MAIN_DEBT` removal is earned per the
detector (`rebind`), the live check and its 455-case self-test are green, and nothing else depends on the list's
size. No BLOCKER. M1 is a pre-existing coverage gap to file; L1 and L2 are prose and a re-merge.

VERDICT: CONVERGED
