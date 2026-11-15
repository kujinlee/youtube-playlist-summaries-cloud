<!-- codex-review: model=gpt-6.1-sol -->

## Findings

- **MINOR — docs/backlog.md:625 (row 646, L1):** The parked filter is in `agenda_digest` (`scripts/goal-tree.py:1556`), not `derive_agenda`. Suggested fix: correct the function name.

- **MINOR — docs/backlog.md:625 (row 646, L2):** “Never reaches the agenda” overstates the exclusion. A `next` thread with a line wait becomes `blocked` at `scripts/goal-tree.py:586` and is excluded from NOW, but `derive_agenda` propagates declared waits into matching agenda steps (`1351–1373`), which remain eligible for Focus. Suggested fix: say “never reaches the agenda’s NOW list.”

- **MINOR — docs/backlog.md:624 (row 645):** “Review r1–r4 converged” contradicts the coordinator reports: rounds 1–3 say **NOT CONVERGED**; round 4 says **CONVERGED**. Suggested fix: “Converged in r4 after folding r1–r3 findings.”

No bare numeric references found in the five rows. Every “Fails if” sentence names an observation, although row 646’s observation concerns the review process.

`python3 scripts/gen-backlog-page.py --self-test`: **247/247 passed**. Both supplied merge commits are ancestors of `origin/master`.

VERDICT: CONVERGED
