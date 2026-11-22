# Round 2 — `marketplace-task17` — coordinator — one finding fixed (fix-induced), one half by alternation

Codex reviewed 8d6f913f (the round 1 fold of plan Task 17, PR #616):
`docs/reviews/codex/marketplace-task17-r2-codex.md` (X1 MAJOR; NOT CONVERGED). Severity below uses the header
grammar's words: MAJOR is `High`.

REVIEW GAP: claude — alternation

## X1 — two non-SHIP rows cited nothing (fix-induced)

The round 1 fold removed `coverage-verdict`'s and `mutation-manifests`' unrelated cites and left `cites: []`, so the
fold itself introduced the defect. The rules, quoted and NOT changed (changing either would move the goal):

- Spec §5, rule 1: *"Every non-`SHIP` verdict **cites the dependency-finding ids it rests on**, and the scan
  **refuses to emit a dependency-finding id for a mention candidate.** Then the rule has a falsifier: a non-`SHIP`
  verdict citing no id, or citing a mention candidate's id, is a defect in the inventory."*
- Plan Task 19's refusal list: *"a non-ship verdict with no `cites`, or citing an id the scan did not emit (§5
  rule 1)"*.

Each row was re-judged against C1 to C5 and given exactly one option:

- **`coverage-verdict` — option (a).** Verdict stays DON'T-SHIP, grade argued. Option (b), SHIP, was rejected: its
  only runtime importer is the DON'T-SHIP engine (`check-plan-code.py` line 108; `sweep-red-alert.py` line 442 is in
  its self-test), so no bundle would load it, and spec §4 calls such an orphan library a scope question. The stated
  reason is the consumer's verdict, so it cites what that verdict rests on: **`check-plan-code:2:1`** (line 2494,
  detector 2 `unread`), the one finding `check-plan-code`'s row cites for its C3 fail, labelled *via its only
  runtime consumer*. `check-plan-code:6:3` is not cited, because that row cites it for a C2 **pass**.
- **`mutation-manifests` — option (a).** Verdict stays DON'T-SHIP, grade argued. Option (b) is not available: C3
  fails and C5 is `unanswered`. Its C3 now states a second, spec-named reason (spec §2c: depending on our engine is
  a C3 failure for a CI piece): the manifest format has one executor, `check-plan-code.load_manifests`
  (`MANIFEST_DIR`, line 1476). It cites **`check-plan-code:2:1`** *via that executor*. The cite bears on the second
  reason only. No finding bears on the first (content anchored to this repo's guards), so that reason stays argued.

**Bound, stated in both rows' notes:** `check-plan-code`'s DON'T-SHIP is argued mainly from spec §2c and
`HARNESS_TREE`, neither of which has a scan finding, so both chains are only as strong as one unjudged coupling.
Backlog #696 (b) now records this resolution and keeps the plan question open. The dashboard entry's "cite nothing"
sentence is corrected. The throwaway row checker passes on all six rows.

```yaml
round: 2
fixes_nontrivial: true
subject: marketplace-task17
halves:
  codex: ran
  claude: gap
findings:
  - {id: X1, severity: High, aim: deliverable, fix_induced: true, component: marketplace-inventory-rows, disposition: fixed}
```
