<!-- codex-review: model=gpt-6.1-sol -->

No new findings after reviewing `264d28ea` and the full `origin/master...HEAD` diff.

1. **(a) Diagnosis holds.** `ok2` contains only ids that record answers. Membership already rejects an unanswered id. The new case pins the remaining distinction: answering “finding” again preserves both verdict names; answering `not a loosening` retires the earlier finding. Checking `standing_findings` catches the diagnostic loss even though the newer finding still HOLDs.
2. **(b) Subject restored.** The appended comment changes the flagged file’s blob without changing the flagged line or id. Round 7’s finding is therefore off-tree again. Round 8’s Codex assent cannot retire Claude’s finding.
3. **No hidden weakening.** This commit weakens no case and widens no `expect`. The full branch’s deliberate assertion flips match the owner-approved bound.

Verification, run sequentially:

- Requested self-test: **365/365 passed**, rc 0.
- Complete scratch baseline: rc 0, `parse_fail_names = []`.
- Mutant (a): rc 1; `parse_fail_names` contains exactly its new `expect`.
- Mutant (b): rc 1; `parse_fail_names` contains its unchanged m3 `expect`, plus the existing repaired-line case. My scratch driver’s stricter “only one failure” assertion failed; the requested mutation-attribution condition passes.

Worktree remains clean. No GitHub actions taken.

## Loosening answers
LOOSENING-CHECK f420a0304250: finding: answers now survive changes to other files when their flagged file's entry matches, as owner-approved
LOOSENING-CHECK 6f2121cd3021: finding: the whole-tree requirement is replaced by per-file binding, preserving answers across changes to other files, as owner-approved
LOOSENING-CHECK 10f587a01725: not a loosening
LOOSENING-CHECK 1d9326b385a7: not a loosening
LOOSENING-CHECK 766bf98f8fce: not a loosening
LOOSENING-CHECK 7895f28f4d34: finding: a merge changing only a doc after review now preserves the answer and passes, as owner-approved
LOOSENING-CHECK 78c781c7b7fc: finding: the doc-only change now expects rc 0 instead of rc 3 and a different-tree refusal, as owner-approved
LOOSENING-CHECK 34cc62ed27bc: not a loosening
VERDICT: CONVERGED
