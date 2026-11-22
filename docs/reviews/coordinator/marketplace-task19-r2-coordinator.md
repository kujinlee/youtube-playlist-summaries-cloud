# Round 2 — `marketplace-task19` — coordinator — two inputs still reach a traceback: a huge integer cost, and a scan finding whose id is not a string

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-task19
halves:
  codex: ran
  claude: "GAP: alternation"
findings:
  - {id: X1, severity: Major, aim: deliverable, fix_induced: true, component: shape, disposition: fixed}
  - {id: X2, severity: Major, aim: deliverable, fix_induced: false, component: inputs, disposition: fixed}
```

Codex reviewed 63d5b48e, the round 1 fold of plan Task 19 (PR #618): [`codex/marketplace-task19-r2-codex.md`](../codex/marketplace-task19-r2-codex.md). Verdict NOT CONVERGED. Loosening answer: "not a loosening".

REVIEW GAP: claude — alternation

What held in round 2:
- self-test 215/215;
- 8 sampled mutations (6 of them new in the fold), each killed by its named case in a full clone;
- NaN, Infinity and -Infinity are rc 2 in all four input files.

## Is this thrashing?

Not yet. Round 1's findings were all `fix_induced: false`, so this is the first fix-induced round for this subject. If round 3 again finds a defect caused by this fold, in the same component, Phase 6 arms for `check-inventory.py`'s shape pass. Round 3 is the round cap's last full round (`review-method.md` §0 Q4c).

## Dispositions

- **X1 (MAJOR, fix-induced): `10**400` as a cost estimate raises `OverflowError` inside `_finite`. ACCEPT.**
  - Python's `math.isfinite` converts its argument to a float, and an integer too large for a float raises instead of returning False.
  - Fix: `_finite` returns False for such an integer, so the row gets a `[shape]` error. The exception class goes; nothing is caught around the whole pass.
  - Check the same thing against every numeric field in `ROW_SCHEMA`, not only the cost estimates.
- **X2 (MAJOR): a scan finding `{"id": []}` raises `TypeError` in `row_errors`. ACCEPT.**
  - Round 1's input validation checked that each finding is an object, but never checked its `id`.
  - Fix: the scan validation requires every finding's `id` to be a string, else rc 2 CANNOT RUN.
  - The class check: every field of a scan, sidecar or map entry that a rule later reads is validated at load time. List the fields the rules read and confirm each one is.

Each fix gets a case that goes red before the fix, an adjacent negative, and a mutation killed by that case, verified in a full clone with `node_modules` present (Codex's clone lacked `typescript`, so its sweep could not run).
