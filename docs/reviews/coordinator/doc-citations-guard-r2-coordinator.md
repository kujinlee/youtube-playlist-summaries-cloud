# Round 2 — `doc-citations-guard` (backlog #49) — coordinator

⚠ **RECONSTRUCTED 2026-10-15, after round 3, from the two filed halves** — see the same note on
round 1. `fix_induced` is the field this round exists to record, and every `true` below is cited.

```yaml
round: 2
fixes_nontrivial: true
subject: doc-citations-guard
halves:
  codex: ran
  claude: ran
findings:
  - {id: B1, severity: Blocking, aim: deliverable, fix_induced: true, component: self-citation-corpus, disposition: fixed}
  - {id: H1, severity: High, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: M1, severity: Medium, aim: deliverable, fix_induced: true, component: cannot-run, disposition: fixed}
  - {id: M2, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: M3, severity: Medium, aim: deliverable, fix_induced: true, component: delivery-figures, disposition: fixed}
  - {id: L1, severity: Low, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CH1, severity: High, aim: deliverable, fix_induced: true, component: diff-extraction, disposition: fixed}
  - {id: CM1, severity: Medium, aim: instrument, fix_induced: true, component: suite, disposition: fixed}
  - {id: CL1, severity: Low, aim: deliverable, fix_induced: true, component: delivery-figures, disposition: fixed}
```

## Verdict: NOT CONVERGED — 1 Blocking, 2 High

## 9 of 9 findings were caused by round 1's own fixes, and here is each one

| id | Finding | Caused by |
|---|---|---|
| B1 | the branch was **RED against its own gate** — `docs/dashboard-entries.md:15116`, prose this branch added describing the paren false positive, parsed as a live citation of a fixture path | r1's first-segment restriction: after it, the bracket is correctly not captured, so `lib/a.ts:2` extracts intact |
| H1 | removing a `---` horizontal rule disabled the guard for the rest of the hunk | r1's boundary fix — stated in the half at `doc-citations-guard-r2-claude.md:79` |
| M1 | a file that exists but cannot be read raised out of a function documented **PURE**, outside the `try` that produces CANNOT RUN | r1 M1's `_reader` |
| M2 | the case added to fix the ambient-pass defect **was itself ambient** — it passes when re-scoping works *and* when header handling is removed entirely | r1 M2/M3's fix |
| M3 | all three documents' figures off by one, structurally | r1 H2's numeric repair |
| L1 | `_header_path` contradicted its own docstring on undecodable bytes (`errors="replace"` never raises) | r1 CH1's quoted-path decoding |
| CH1 | the strict-decoding fix introduced a **real Git-header fail-open** — it rejected the literal UTF-8 git emits under `core.quotePath=false` and skipped the file | r1 CH1's fix, tightened |
| CM1 | the new read-error handler had no witness: returning success survived | r1 M1's handler |
| CL1 | the numerical repair left contradictory figures across the delivery documents and CI | r1 H2's repair |

**That is the arming condition's first round.** Three of the nine (H1, CH1, L1) are the *second*
generation of the same fail-open: a header parser that cannot be made total, because the thing it
parses is a filename it has no independent knowledge of.

## The redesign that round 2's fixes became

Round 2 did not patch a fourth header defect. `6c1d5e4e` deleted `_header_path()` and the boundary
clause, made `violations()` take the path as a parameter, and moved filename knowledge to
`git diff --name-status -z`, which emits paths NUL-delimited and never quoted. The claim it makes is
that header misparsing and scope leaking are **impossible by construction** — round 3's job was to
break that claim.
