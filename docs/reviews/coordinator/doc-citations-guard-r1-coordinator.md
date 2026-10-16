# Round 1 — `doc-citations-guard` (backlog #49) — coordinator

⚠ **RECONSTRUCTED 2026-10-15, after round 3, from the two filed halves** — not written at the time.
`scripts/check-review-decision.py` reported `rounds=0` for this branch while six halves sat
committed under `docs/reviews/`, so the two counters the decision procedure turns on were being
derived by hand in a conversation instead of from disk. Every `fix_induced` and `aim` value below is
a judgement taken from the half's own text, cited where it is not obvious; none is recalled.

```yaml
round: 1
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: H1, severity: High, aim: deliverable, fix_induced: false, component: resolution-oracle, disposition: fixed}
  - {id: H2, severity: High, aim: deliverable, fix_induced: false, component: delivery-figures, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: false, component: cannot-run, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: M3, severity: Medium, aim: instrument, fix_induced: false, component: mutation-manifest, disposition: fixed}
  - {id: M4, severity: Medium, aim: deliverable, fix_induced: false, component: delivery-figures, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: false, component: citation-grammar, disposition: declined}
  - {id: L2, severity: Low, aim: deliverable, fix_induced: false, component: citation-grammar, disposition: declined}
  - {id: L3, severity: Low, aim: deliverable, fix_induced: false, component: resolution-oracle, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: false, component: diff-extraction, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: citation-grammar, disposition: fixed}
  - {id: CM2, severity: Medium, aim: deliverable, fix_induced: false, component: delivery-figures, disposition: fixed}
  - {id: CM3, severity: Medium, aim: instrument, fix_induced: false, component: suite, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: false, component: citation-grammar, disposition: fixed}
```

## Verdict: NOT CONVERGED — 3 High

`H*` are the Claude half (`docs/reviews/claude/doc-citations-guard-r1-claude.md`), `C*` the Codex
half (`docs/reviews/codex/doc-citations-guard-r1-codex.md`).

## What the round established

- **The existence oracle was the wrong one.** H1: the guard asked `path in tracked`, so a citation
  into a real, readable, *untracked* file was reported unresolvable — reproduced against
  `.claude/skills/shared/explainer-delivery.md`, which is where this project's own harness lives.
  The filesystem is now the oracle; `tracked` is used only for suffix search, which genuinely needs
  a file list.
- **CH1 is the first of the three fail-opens that eventually forced the redesign.** Git's default
  quoting of a non-ASCII document name (`+++ "b/docs/\355\225\234\352\270\200.md"`) left `current`
  unset or holding the *previous* document's scope, and the run reported OK with `rc=0`.
- **None of the three headline numbers reproduced** (H2), and the cause was structural rather than
  careless: the rule changed underneath the figures — `md` joined the extensions, the suffix
  exemption arrived, and CM1 widened the grammar again in this same round. Every conclusion
  survived; not one number did.
- **CM2 refuted a claim I had already written down.** The nine historical firings resolve against
  *today's* tree, so they measure drift since the line was written, not nine defects the gate would
  have blocked at the time — `git show 5128b99b:scripts/check-ci-watched.py | sed -n '860p'` returns
  a populated `def main(...)`. The docstring now states what the rate is *not*.
- **Two advertised cases passed after the behaviour they named was removed** (CM3) — the first of
  five ambient cases this one file produced.

## Dispositions that were not fixes

- **L1 (ranges) and L2 (fenced code) were DECLINED and recorded as stated limits**, not fixed. L2's
  recorded reason is the one that matters later: *"Fixing it means reading the file rather than the
  diff, which is a different guard."* Round 4 revisits exactly that sentence.
