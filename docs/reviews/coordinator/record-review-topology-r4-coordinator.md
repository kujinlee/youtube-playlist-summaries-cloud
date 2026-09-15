# record-review-topology — round 4, coordinator adjudication

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. All four
rounds are Codex-only and **the Claude half is owed before merge**.

## ⚠ THE REDESIGN FALSIFIER FIRED, AND IT WAS WRITTEN DOWN IN ADVANCE

r3's adjudication overrode the REDESIGN stop condition and recorded the condition that would
overturn the override: *"this fires to REDESIGN if r4 produces a finding that a different shape
would dissolve."* r4's Blocking says, in its own words, *"A full tree-entry comparison, including
entry type or at least non-blob entries, dissolves this."*

**So it fired, and the redesign is what shipped in this round** — not another patch:

| | before | after |
|---|---|---|
| what is compared | blob entries only, `"<mode> <sha>"` | **every** entry, no type filter |
| what absence means | equality with a 40-zero literal | `is_absent` reads the SHAPE, any sha width |
| what carries the type | a `parts[1] == "blob"` filter | the **mode** — `160000` gitlink, `120000` symlink, `100644`/`100755` file |

The filter was mine, added in r2 to stop a commit sha being compared against a blob's. Including the
mode already makes that impossible, so the filter bought nothing and cost a false pass. Removing a
guard that a stronger representation made redundant is the redesign; adding a special case for
submodules would have been the patch.

## Round 4 — Codex, `gpt-5.5`, against the UNCOMMITTED round-3 fixes

`docs/reviews/codex/record-review-topology-r4-codex.md` · verdict
`docs/reviews/verdicts/record-review-topology-r4-codex.verdict.json` (`gate_ran: true`).
**NOT CONVERGED**: 1 Blocking, 1 High, 1 Medium, **no Low**.

| # | Severity | Finding | Disposition |
|---|---|---|---|
| 1 | **Blocking** | Filtering to `blob` entries made a path holding a **submodule** read as absent, so a reviewer who saw that path DELETED credited a merge that puts a gitlink there | **FIXED by redesign** — every entry is kept; the mode carries the type |
| 2 | High | **The finding was against my own adjudication, not the code.** r3 accepted the stacked-parent gap *on condition that the pass names the document* — and the message printed only the reason. The docstring claimed what the code could not do | **FIXED** — `first_codex_gap` returns `"<path> — <who>: <reason>"`; a case asserts the path is in the answer |
| 3 | Medium | `ABSENT_ENTRY` hard-coded SHA-1 width; a SHA-256 repository writes 64 zeros, so a reviewed deletion falsely FAILED there | **FIXED** — `is_absent` reads the shape. Fail-closed either way, but wrong is wrong |

## The one worth keeping

**A review record that over-claims is worse than the gap it excuses.** Finding 2 was not a code
defect at the time it was written — it was *my adjudication asserting a mitigation I had not built*,
and a later reader would have taken the accepted limit as mitigated. r4 caught it by reading the
adjudication against the code, which is the only way that class is ever caught.

## What r4 confirmed rather than found

Stated so the pass is not read as wider than it is. The reviewer swept the tree states — added,
modified, deleted, mode-only, file↔symlink, rename-as-delete+add, unchanged, absent-from-both — and
found no other error; could not produce a zero destination for a non-deletion, duplicate path
records, or a partial-index entry that was *wrong* rather than merely incomplete; found no mutation
whose named case would stay green; and re-derived the prose counts as reconciling (16 findings
across r1–r3, 13 fixed, 3 accepted).
