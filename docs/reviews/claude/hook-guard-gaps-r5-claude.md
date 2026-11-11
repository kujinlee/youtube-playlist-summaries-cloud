# hook-guard-gaps — round 5, Claude half (merge confirmation)

**Subject:** merge commit `0adde2ca` (HEAD of `hook-guard-gaps`), parents `0b7471d5` (branch) and
`1b4b74d3` (master, PR #410). Merge base `4aaa6ed7`. Scope: the conflict resolution only, which
`git show --remerge-diff HEAD` puts in four files: `docs/backlog.md`, `docs/dashboard-entries.md`,
`docs/reviews/decision-scheme/decision-log.jsonl`, `scripts/check-plan-code.py`. I did not re-review
the feature.

**Mandate:** refute. Every check below was run in the worktree, read-only. The one experiment ran
in a `mktemp -d` copy. Afterwards `git status --short` in the worktree was empty.

## Checks

| # | Check | How it was executed | Result |
|---|---|---|---|
| 1 | `EXPECTED_MUTATIONS` keeps both keys | `ast` three-way read of the dict literal at the base, both parents and HEAD | Only two keys differ across the four versions. `check-hook-commands.py`: base 12, branch 16, master 12, HEAD **16**. `session-state.py`: absent, absent, master 17, HEAD **17**. The literal has 70 keys and no duplicate key, so a later duplicate cannot silently override an earlier one. **CONFIRMED** |
| 2 | Pinned 2171 equals the real sum | Imported the module and computed `sum(EXPECTED_MUTATIONS.values())` | 2171. Per-version sums: base 2150, branch 2154 (+4), master 2167 (+17), HEAD 2171 = 2150+4+17. The `_self_test` case asserts 2171, and `--self-test` passes. **CONFIRMED** |
| 3 | Each manifest's entry count equals its pin | Counted `file` per entry across every `scripts/mutations/*.json` and compared with the pin map in both directions | No mismatch. The manifests total 2171 entries. **CONFIRMED** |
| 4 | Docs logs keep both sides, nothing lost or duplicated | For each file, a line-set three-way check: expected = (base − lines either side removed) ∪ lines either side added. Compared with HEAD, plus new duplicate lines and conflict markers | All three files: 0 missing, 0 extra, 0 new duplicate lines, 0 conflict markers. Backlog row ids are unique, and 360–369 are all present. Row 365 carries the branch's ✅ version (master never changed it), and 366/367/369 come from master, 368 from the branch. The JSONL parses line by line, with master's 4 `session-state` rows followed by the branch's `hook-guard-gaps` row. The dashboard now has a second `## 2026-10-26` heading for the branch entry, which matches what the file already does (the base already had 9 such headings). `check-dashboard-entry.py` returns rc 0 and `check-docs.py` returns rc 0. **CONFIRMED** |
| 5 | `check-hook-commands.py` accepts master's SessionStart hook and passes 29/29 | Ran the guard (rc 0: 14 hook commands, all canonical and present). Ran `--self-test` with rc read directly, not through a pipe (rc 0, `29/29`). Known positive in a temp copy: appending `\|\| true` to the session-state command gave rc 1, naming SessionStart. Removing `session-state.sh` gave rc 1, "does not exist". The guard therefore reads the new entry and is not passing it by accident. Its extra `"timeout": 60` key is accepted. **CONFIRMED** |
| 6 | The six gates exit 0 | Ran each, capturing rc | `check-plan-code.py --self-test` returned 0 (246/246). `check-fixture-variation.py`, `check-selftest-counts.py` (61 verified by running), `check-ratchet-contract.py`, `check-decision-scheme.py` (2 WARN-only lines, both about other subjects, both pre-existing) and `check-review-rounds.py` (551 parsed, 0 silent gaps) each returned 0. **CONFIRMED** |

## Findings

None. I tried to refute each claim: by duplicate dict keys, by a pin that was hand-added rather than
summed, by manifest drift, by a row lost or doubled in a hunk that has no conflict marker, and by a
guard that passes the new hook without reading it. None of these attempts produced a defect.

⚠ **Limit, stated:** check 4 compares sets of lines, so it cannot detect a line that has been moved to
the wrong place within a file. For these files I read the order by hand: backlog rows ascend, the
dashboard entries are appended, and the JSONL is append-only.

VERDICT: CONVERGED
