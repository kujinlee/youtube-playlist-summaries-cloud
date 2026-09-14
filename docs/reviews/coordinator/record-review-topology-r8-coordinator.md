# record-review-topology — rounds 5–8, coordinator adjudication and STOP

**REVIEW GAP:** claude — not invoked; built by a worker fork that cannot spawn subagents. All eight
rounds are Codex-only and **the Claude half is owed before merge**. On this branch's own evidence
(three rounds, zero overlapping findings between halves) that is a materially weaker gate, not a
formality.

## Where it landed

| round | verdict | B / H / M / L |
|---|---|---|
| r1 | NOT CONVERGED | 1 / 3 / 3 / 1 |
| r2 | NOT CONVERGED | 1 / 1 / 1 / 0 |
| r3 | NOT CONVERGED | 0 / 1 / 3 / 1 |
| r4 | NOT CONVERGED | 1 / 1 / 1 / 0 |
| r5 (design review) | **CONVERGED** — *"the SHAPE is now right"* | 0 / 0 / 0 / 1 |
| r6 | CONVERGED | 0 / 0 / 0 / 1 |
| r7 | NOT CONVERGED | 0 / 0 / 0 / 1 |
| r8 | NOT CONVERGED | 0 / 0 / 0 / 1 |

**Four consecutive rounds at zero Blocking/High/Medium.** r7 and r8 say NOT CONVERGED on a Low
alone; the project's bar is Blocking/High.

## ⛔ STOPPING, and why that is a decision rather than fatigue

r5, r6, r7 and r8 each found exactly one Low of the **same editorial class**: generic prose calling
the recorded unit a blob or content, when after r4 it is a git tree entry — mode plus object id.
Each fix touched guarded code, which made the previous round stale, which forced another round.
r8's remaining Low is **one comment**, `check-review-recorded.py:665` — *"no final blob to equal"*.

Fixing it would invalidate r8 and buy r9. So it is **left in place and recorded here**, and the
branch ships exactly the tree r8 reviewed. That is this branch's own rule being obeyed rather than
escaped, and the alternative — an exemption for "editorial" changes — is the loosening every one of
r1–r4's Blockings was made of.

**OPEN, one line, for the next branch that touches this file:**
`scripts/check-review-recorded.py:665` — *"no final blob to equal"* → *"no final entry to equal"*.

## Rounds 5–8 in one line each

- **r5 — the design review the stop condition demanded.** Asked whether the SHAPE is right, not for
  more edge cases. Answer: the representation is complete for tracked paths; what it omits (xattrs,
  smudge bytes, dirty submodule contents) are not merge-tree facts. Deferred as hardening: a shared
  tree-entry codec and verdict schema validation (`schema == 2`, `tool == "codex-review"`,
  well-formed entries). **Not implemented — recorded as follow-up work**, with r5's and r6's
  explicit agreement that it does not block.
- **r6** — verified the delta *using the r5 verdict snapshot*, i.e. the mechanism under review was
  used to review itself, and confirmed exactly one file had changed.
- **r7** — confirmed the new batching paragraph in `review-method.md` is true of the code: there is
  no docstring-only escape, and a docstring edit really does make a round stale.
- **r8** — confirmed the manifest repair. Rewriting `expect` values had corrupted the six
  pre-existing entries (their `expect` is a **string**; a list comprehension exploded each into
  single characters). The harness caught it at 570/576 attributed; restored from `origin/master`
  and re-run clean at 576/576.

## The lesson worth more than the feature

**Every round found its defect in the previous round's repair, and never anywhere else.** That is
the claim this branch makes mechanical, demonstrated eight times on itself — including the two
Blockings being the same class one layer apart, and the one finding (r4's High) that was against a
*coordinator adjudication* claiming a mitigation the code did not have.
