# Round 2 — `anchor-precheck` — coordinator — ⟳ NOT CONVERGED; one fold-induced Medium, fixed

```yaml
round: 2
fixes_nontrivial: false
subject: anchor-precheck
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: manifest, disposition: fixed}
```

REVIEW GAP: claude — round 2 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

- **XM1 (fold-induced, fixed):** the r1 fold's new manifest entry repeated the wiring entry's find-string, and
  `load_manifests` refuses duplicate anchors — the live-manifest case went red (243/245). I appended it without
  re-running the suite. Re-anchored on `drift += … \n    if drift:`; the mutant still reddens exactly its case. My
  local append helper now refuses a duplicate anchor tuple.
- Also folded (CI's `check-fixture-variation`, not a review finding): `anchor_problems(read=…)` was passed one
  reader at every call; a case now drives a reader that cannot read.

Codex confirmed the case itself sound (it asserts the orphan's own diagnostic; its `finally` restores both the
manifest and `EXPECTED_MUTATIONS`). A Codex confirmation round follows on this tree.
