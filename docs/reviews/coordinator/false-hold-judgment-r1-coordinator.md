# Round 1 — `false-hold-judgment` (backlog #508) — coordinator — ⟳ NOT CONVERGED (Codex); folded

Both halves ran on `54667f2c`. Claude: CONVERGED with 2 MAJOR and 5 MINOR findings. Codex: NOT CONVERGED with 3 MAJOR.
Codex 1 and Claude m4 are the same defect, so it is listed once below as `X1`.

```yaml
round: 1
fixes_nontrivial: true
subject: false-hold-judgment
halves:
  codex: ran
  claude: ran
findings:
  - {id: CM1, severity: High, aim: deliverable, fix_induced: false, component: scripts/codex-review.py, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: X1, severity: High, aim: deliverable, fix_induced: false, component: scripts/codex-review.py, disposition: fixed}
  - {id: X2, severity: High, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: X3, severity: High, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: Cm3, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: Cm5, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
  - {id: Cm6, severity: Low, aim: deliverable, fix_induced: false, component: scripts/record-review-verdict.py, disposition: filed}
  - {id: Cm7, severity: Low, aim: deliverable, fix_induced: false, component: scripts/check-merge-ready.py, disposition: fixed}
```

## Each finding: what was done, and which case covers it

Every fix was written test-first. Each new case was run and seen red before the fix, then green after it.

| Finding | Disposition | Case(s) that cover it |
|---|---|---|
| **Claude M1**: a dissent in any non-exact wording was dropped, so the other half's assent cleared the line | **fixed**. Assent stays strict. Dissent is now loose: any line that names `LOOSENING-CHECK`, in any case, and is not the exact assent is a finding for every 12-hex id on it. | codex-review: `#508 r1 M1: a dissent in ANY wording is a finding — bold, ...` (the reviewer's 7 probes, plus a backticked id); `...and it beats the exact assent for the same id in the same review`; the re-pinned `#508: an indented, quoted, prefixed or suffixed assent is a FINDING, a placeholder no answer` |
| **Claude M2**: the round's coordinator document and decision log, committed after the final round, voided its answers | **fixed**. `REVIEW_RECORDS` now also exempts `docs/reviews/coordinator/` and the single file `docs/reviews/decision-scheme/decision-log.jsonl`. The scheme's `baseline.json` is still NOT exempt. | `#508 r1 M2: the round's coordinator document and decision log, added after it, match`; `...but the decision scheme's BASELINE changed after it does not`; real git: `⭐ #508 r1 M2 real git: the coordinator doc and decision log committed AFTER the round keep its answer, rc=0` |
| **Claude M2, second gap**: `--flagged-block` read committed history only | **fixed**, by option (b). `--flagged-block` reads the working tree through `git stash create`, which writes a commit object and leaves the stash list untouched. `gather` and `status_cmd` now take that head. Bound: an untracked file is not included, but a new file removes no lines, so it flags none. | real git: `⭐ #508 r1 M2 real git: --flagged-block asks about a line an UNCOMMITTED fix flags`, run on a gate the branch's commits never touch; `#508 r1 M2: gather reads the head it is GIVEN ...`; `#508 r1 M2: ...and the head it is given` (status_cmd) |
| ⚠ **Claude M2, other files**: `docs/backlog.md`, `docs/dashboard-entries.md` and `docs/goal-threads.md`, edited after the final round | **not exempted**. The owner's rule is the EXACT tree, and the pinned case `...nor does a DOC changed after it` still holds. Those edits must be committed before the final round; otherwise the gate HOLDs, which fails closed. | the existing `⭐ #508 real git: ...and ANY edit after the round (a doc) voids the answer, rc=3` |
| **Codex 1 / Claude m4**: an assent quoted in a fence or comment was read as an answer | **fixed**. An exact assent is ignored inside a ``` or ~~~ fence or an HTML comment. Fences follow CommonMark's closing rule. An unclosed fence or comment runs to the end of the file. A finding inside one still counts. | `#508 r1 Codex 1: an exact assent inside a ``` or ~~~ fence is no answer`; `...nor inside an HTML comment, one line or many`; `...but an assent AFTER the fence or comment closes is the answer`; `...and a FINDING inside a fence still counts` |
| **Codex 2**: an `ignore = all` submodule moved after the round kept the answer | **fixed**. `tree_matches` compares every entry of both trees, gitlinks included. Its `changed` parameter and the `git diff --name-only` call that fed it are deleted. | `#508 r1 Codex 2: a GITLINK changed after the round does not match, though no diff named it`; `...nor a file ADDED after the round that no diff named`; real git: `⭐ #508 r1 Codex 2 real git: an ignored submodule moved after the round voids its answer, rc=3` (Codex's own reproduction, with a rc=0 control before the move) |
| **Codex 3**: a rising count that also dropped a trailing space was exempt | **fixed**. `rising_count` now compares the unstripped added lines. Move detection still uses the stripped list, unchanged. | `#508 r1 Codex 3: a rising count that also DROPS a trailing space is still a failure-path removal`; control `...while the same rise with the trailing space KEPT is exempt` |
| **Claude m3**: a finding on an unchanged line was dropped once the tree moved | **fixed**, with a rule stricter than the suggested note. A finding in ANY verdict the branch adds keeps that id held, on any tree. An id hashes the removed text, so the finding still names the same line. Rewriting the line gives a new id, which goes to the next round. The output names the verdict that holds it. | `#508 r1 m3: a FINDING from a record on ANOTHER tree still beats an assent on this one`; real git: `⭐ #508 r1 m3 real git: a FINDING from an earlier round on an UNCHANGED line beats a later assent, rc=3` (the reviewer's 3-step input) |
| **Claude m5**: a block row had no location | **fixed**. Each row reads `` `file:line` ``, where the line is in the BASE file. Hunks are a `list` subclass that carries `old`, the start line from the `@@ -N` header. The id is unchanged, because it does not include the line number. | `#508 r1 m5: failure_path_removals reports each removal's gate, text and base line, hunk by hunk`; `#508 r1 m5: each block row names its file AND base line`; real git: `#508 r1 m5 real git: ...and names where each line was in the base file` |
| **Claude m6**: a Claude half's overlay is captured when the verdict is recorded, not when the review ran | **filed**, not fixed. The real fix needs the brief's path list to reach `record-review-verdict.py`, or a capture at dispatch. That is a design change, not a cheap clause. For now the bound is stated in `docs/review-method.md` step 4: record before any fold edit. | none (filed) |
| **Claude m7**: the rising-count exemption assumes the count is prose | **fixed** as asked, by stating the bound in the `rising_count` docstring. No line in the repo has that shape. | none (doc-only) |

## Mutations

There are 8 new mutations in `codex-review.json` and 2 re-anchored, for a pin of 76 → 84. There are 15 new mutations in `check-merge-ready.json` and 5 re-anchored, for a pin of 112 → 127. `record-review-verdict.json` is unchanged at 23. Every anchor in the three manifests matches exactly once. Each new or changed entry was applied to a staged COPY (`check-plan-code.stage_tree` → `run_mutations`), and each was killed through the case it names. The results are in the commit message.

Not mutated: `blob_hunks` setting `whole.old = 1` for an added or deleted blob. It is display only: it sets the line number of a whole-file removal and decides nothing.

## This PR's own flagged lines

The Claude half answered `finding` for two ids, and that is owner-sanctioned (card A). Under the m3 rule, those findings now hold on every later tree. This PR therefore HOLDs for the owner, as the Claude half recommended.
