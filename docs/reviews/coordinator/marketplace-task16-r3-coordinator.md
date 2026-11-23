# Round 3 — `marketplace-task16` — coordinator — NOT CONVERGED (Claude); THRASHING → Phase 6 rule built

Claude ran r3 on f5a477ea (the r2 fold 2f4b59ce, its rescan and records a8fa1eec):
`docs/reviews/claude/marketplace-task16-r3-claude.md`. It found 2 MAJOR (M1, M2) and 4 MINOR (m1 to m4), and its verdict
is NOT CONVERGED. The Codex half is a gap by alternation; round 4 is Codex's.

REVIEW GAP: codex — alternation.

```yaml
round: 3
fixes_nontrivial: true
subject: marketplace-task16
halves:
  codex: gap
  claude: ran
findings:
  - {id: M1, severity: Major, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
  - {id: M2, severity: Major, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
  - {id: m1, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
  - {id: m2, severity: Minor, aim: deliverable, fix_induced: true, component: publishability-install-root, disposition: fixed}
  - {id: m3, severity: Minor, aim: deliverable, fix_induced: false, component: publishability-install-root, disposition: fixed}
  - {id: m4, severity: Minor, aim: documentation, fix_induced: false, component: publishability-install-root, disposition: fixed}
```

**The thrashing pair.** Round 2's X1 and X2 were caused by the r1 fold. Round 3's M1 and m1 are regressions caused by
the r2 fold, and M2 and m2 are partly caused by it. All of them are in detector 2's install-root rule
(`publishability-install-root`). Two consecutive rounds therefore carry findings caused by the previous round's fix in
one component. That is the arming condition, so Phase 6 convened:
`docs/reviews/architecture-review-2026-11-21-publishability-install-root.md`.

The review found a MECHANISM defect: two lists (derivations, and inert uses) met at one boundary, and an omission in one
list met a listing in the other as silence. The redesign built here is its §4 **mention walk**:

- `_Scopes` (for detector 2), `_from_file`, `_fstring_path`, `INERT_CALLS`, `_inert` and `_rebinds` are deleted from
  detector 2. `_Scopes` stays only for detector 6's `~`-path names.
- Every mention of a file-anchored value is walked upward through ONE decoder, `_step`. Its default is USE (reported),
  so a form nobody listed is a finding, never a silence.
- Calls are read through ONE table, `ROLES`, keyed `(callee, (position, keyword))`, so a keyword spelling is the same
  row as a positional one. A keyword the table does not list is USE.
- A name is followed only when every one-name assignment of it in the file binds the same value (`_census`, a
  file-wide default-deny). Otherwise its root is reported AT THE BINDING, as `.`: coarser, never silent.
- The only silent exits are the closed tests of §4.1: an inert use, a part that leaves the tree, a level that is not the
  install depth, and a shipped target.

Every r1 to r3 input is now a self-test case (`P6 corpus: …`, 49 inputs). At HEAD b79d4bad, 22 cases were red; all of
them are green on the build.

## Dispositions

| Finding | Disposition | Case, and what the rule now answers |
|---|---|---|
| **M1** (MAJOR, fold-caused regression). `os.chdir(os.path.relpath(path=ROOT))` was silent. | FIXED | `relpath`'s `path` keyword is the same `ROLES` row as position 0, so the root is handed on to `chdir`: reported. Cases *P6 (r3 M1, M2, m2)* and *P6 corpus: r3-M1*. The invariant case *P6 (r3 M1): each keyword row …* checks the table's keyword rows against an independent literal list, and checks that each answers the same spelt both ways. |
| **M2** (MAJOR, partly fold-caused). The root in a LATER f-string piece was lost (argv, `PYTHONPATH`, an env dict). | FIXED | Any piece of an f-string that carries a file-anchored value is a mention. It is walked, and reported at the piece's use. Corpus rows *r3-M2 argv*, *PYTHONPATH*, *env dict* and the swapped *control*. |
| **m1** (MINOR, fold-caused regression). A walrus inside a comprehension was mis-scoped for `nonlocal`. | FIXED (detector 2); residual FILED as backlog #691 | Detector 2 no longer asks `_Scopes`. `root` is assigned more than once in the file, so it is not followed and is reported at its binding: corpus row *r3-m1 walrus nonlocal* gives `(6, '.')`. The same mis-scoping still lives in `_Scopes`, which only detector 6's HOME names use now. That residual, and the 16 `_Scopes`/`_literal` mutants it no longer kills, are backlog #691. |
| **m2** (MINOR, partly fold-caused). A `//` f-string tail was read as an absolute path. | FIXED | The tail's leading `/`s are stripped before the join, so the tail is a path below the root: `(5, 'docs/x.md')`. Corpus row *r3-m2 // tail*; mutant *a `//` f-string tail is not joined* is killed by it. |
| **m3** (MINOR, r1 code). A chained assignment `R = X = ROOT` hid the root; `R /= …` failed toward silence. | FIXED | A multi-target or augmented store denies the name in the census, so the root is reported at its binding. Case *P6 (r3 m3)* and three corpus rows. The design's "fails toward a finding" sentence now holds for the augmented bound too. |
| **m4** (MINOR, the master merge). The committed scan's line numbers were stale. | FIXED | Rescanned at the build commit: `docs/marketplace/scan-2026-11-21.json`. |

## The rescan, explained

Against the r2 scan (`measured_at` 2f4b59ce), the install-root findings changed by +9 and −7. Every difference has a
cause:

- **Two findings gained, as predicted:**
  - `check-plan-code:2` at `scripts/check-plan-code.py:6355`, `.`. This is the reused-name shape, now reported at its
    binding.
  - `check-surface-recall:2` at `:519`, `.claude/hooks/does-not-exist.sh`. This is a self-test fixture string, an
    over-report. It is stated in L5 of `docs/marketplace/experiment-tier-a.md`.
- **Three findings moved, as predicted.** The line numbers changed and the targets did not:
  - gen-dashboard `docs/dashboard-entries.md`, 3305 → 3297;
  - check-docs `docs/backlog.md`, 369 → 368;
  - check-docs `docs/roadmap-to-launch.md`, 563 → 562.
- **Four goal-tree findings moved, not predicted.** These are m4's own cause: `scripts/goal-tree.py` changed in the
  master merge 70fefa79, after 2f4b59ce.
  - `docs/goal-tree-answers.json`, 3030 → 3107;
  - `.`, 3082 → 3159;
  - `.claude/hooks/session-state.sh`, 3765 → 3842;
  - `docs/explainers`, 5447 → 5524.
- **Other detectors:** their findings differ only in line numbers, from the same master-merge files. There is one new
  detector-4 `guard-name` mention in `mutation-manifests`: a new mutation's `expect` text names `check-plan-code`.

The six tier-A components keep every named target and their counts: regen-pages 2, goal-tree 4, gen-backlog-page 3,
gen-features-page 7, gen-goals-page 3 and gen-dashboard 2 (§5 observation 2).

## Mutants and manifest

`scripts/mutations/check-publishability.json` goes from 237 to 228 entries, and the pin in
`scripts/mutations/expected_mutations.py` from 237 to 228.

- **Removed (45):**
  - 29 whose anchors the build deleted, in `_from_file`, `_fstring_path`, `_inert`, `_rebinds` and the old
    `_install_root_uses`.
  - 16 on `_Scopes` and `_literal`. These survived with rc=0 once detector 2 stopped calling them, because detector 6's
    cases do not reach those branches. That is backlog #691.
- **Added (36):** one per branch of `_placed`, `_role`, `_step`, `_census` and the new `_install_root_uses`. Each was
  verified KILLED on a scratch copy by exactly the case its `expect` names.
- **Re-run:** the 67 remaining detector-2 entries were run again on scratch copies. All are KILLED except the 2 above,
  which are among the 16 removed.
- Every anchor in every manifest resolves exactly once (6375 anchors).

## Next

Round 4 is Codex's, by alternation. Per §6 of the architecture review, it is briefed to REFUTE §4.1, that is, to find a
silent hand-on. If it finds one caused by this build, that is §5 observation 3: stop, and take it to the owner. A
precision finding (`.` at a binding, or a false positive) is filed, not folded.
