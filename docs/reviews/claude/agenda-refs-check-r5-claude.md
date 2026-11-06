Reviewed head: 04fd6a6ae679d0d4f81e4c7c83d0f258d40fca31

# Round 5 — `agenda-refs-check` (backlog #504, PR #525) — Claude half (adversarial), the merge resolution only

**Scope.** Only the merge `04fd6a6a` of origin/master `319bd152` into the branch tip `0a5ba00c`, in the three files
`check-review-recorded` says no round saw merged: `scripts/check-plan-code.py`, `scripts/goal-tree.py` and
`scripts/mutations/goal-tree.json`. The merge base is `1d618a6f`. This is a capped round (§0 Q4c), so only a BLOCKER
would be folded. I tried to refute the merger's account rather than confirm it.

## 1. Lost or duplicated changes — not refuted

**Text files.** I re-ran the merge for each file with `git merge-file -p ours base theirs` and diffed the result against
the committed merge.
- `goal-tree.py`: the only difference is the one conflict hunk, the docstring self-test count. The branch had 412 and
  master had 397; the merge sets 416. Every other line equals the clean three-way union. This includes master's #518
  move of `opened`/`resolved` above `if prs:`, master's `agenda_digest` `or t.get("open_prs")` clause, and master's four
  new cases, beside the branch's `REF_KINDS`, `_EOL`, `_blank`, `_ref_ok` and byte-mode `_locked` changes.
- `check-plan-code.py`: the only difference is the conflict hunk on the `scripts/goal-tree.py` pin. The branch had 314
  and master had 300; the merge keeps the branch's r3-fold comment, adds a merge comment and sets 316.

**Manifest, compared structurally** (each entry as canonical JSON, not as text). Base 298, ours 314, theirs 300, merged
316.
- Ours removed 3 entries and added 19. Theirs removed 4 and added 6.
- The expected union is `(base − ours-removed − theirs-removed) ∪ ours-added ∪ theirs-added`. It has 316 entries, and
  it equals the merged set exactly: 0 entries missing and 0 extra.
- No entry name is duplicated. No base entry was changed on both sides.

The textual `merge-file` run does conflict here, because both sides appended at the same point. The merger resolved it
by keeping both appended blocks, and the structural check confirms that.

## 2. Anchors — not refuted

All 316 entries target `scripts/goal-tree.py`. I applied each entry's edits in order to the merged source, under the
same rule as `check-plan-code.py:anchor_problems`, and every find-string occurs exactly once. Problems: 0.

## 3. Mutations killed by a different case — not refuted

I ran 9 entries through `check-plan-code.py:run_mutations` itself, imported as a module. They ran on a `git archive`
copy of `scripts/` in the scratchpad, with `HOME` redirected to an empty scratch directory. The 9 entries sit near the
changes from both sides:
- master's side: entries 137 (r1 X1 title-resolved PR), 230 (#509 NOW), 271 (named open PRs, whose expect master
  re-named), 298 and 299 (the two #518 entries);
- the code master moved (`resolved`): entries 278 and 279 (r3 Codex M1);
- the branch's side: entries 302 (unknown ref kind) and 310 (lone CR, r3 N1).

Result: 9 of 9 were caught AND attributed. In each one, the named case went red, by `run_mutations`' own equality
rule. `ok True`, with an empty report. The worktree was untouched afterwards (`git status` showed only the pre-existing
untracked log).

## 4. Self-test and pin counts — not refuted

- `python3 scripts/goal-tree.py --self-test` printed **416/416** passed, which equals the docstring's `# 416 cases`.
- `python3 scripts/check-plan-code.py --self-test` printed **310/310** passed, which equals its docstring's `# 310 cases`.
- The `EXPECTED_MUTATIONS["scripts/goal-tree.py"]` pin is 316, which equals `len(goal-tree.json)` = 316.

## Bound

I did not run the full 316-entry sweep locally; CI's sweep is the full measure. The sample covers every entry master
added or changed that touches the moved `resolved` code, plus two of the branch's entries.

**Findings: 0 BLOCKER, 0 MAJOR, 0 MINOR.**

VERDICT: CONVERGED
