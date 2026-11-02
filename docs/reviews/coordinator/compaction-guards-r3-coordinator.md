# Round 3 — `compaction-guards` — coordinator — ⟳ NOT CONVERGED (both halves); THRASHING → architecture review → SPLIT

Claude half: `docs/reviews/claude/compaction-guards-r3-claude.md` (wording vs code, on the pinned 3c282379), 3 Major + 7 Minor.

```yaml
round: 3
fixes_nontrivial: true
subject: compaction-guards
halves:
  codex: ran
  claude: ran
findings:
  - {id: XR1, severity: Medium, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: XR2, severity: Medium, aim: deliverable, fix_induced: true, component: audit, disposition: fixed}
  - {id: XR3, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: XR4, severity: Medium, aim: deliverable, fix_induced: true, component: storage, disposition: fixed}
  - {id: XR5, severity: Medium, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: XR6, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: XR7, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Xr8, severity: Low, aim: deliverable, fix_induced: false, component: extraction, disposition: fixed}
  - {id: Xr9, severity: Low, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: Xr10, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: CR1, severity: Medium, aim: deliverable, fix_induced: true, component: snapshot, disposition: fixed}
  - {id: CR2, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: CR3, severity: Medium, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cr4, severity: Low, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: Cr5, severity: Low, aim: deliverable, fix_induced: false, component: print, disposition: fixed}
  - {id: Cr6, severity: Low, aim: deliverable, fix_induced: true, component: print, disposition: fixed}
  - {id: Cr7, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cr8, severity: Low, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Cr9, severity: Low, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Cr10, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Both halves on `3c282379`. All round-2 reproductions from both halves now fail; 101/101 and 60/60; all 91 mutations
killed at their named cases; 2,427 real; the real 83 MB transcript pairs all 40 answers in 0.56 s; the hard kill held at
10.98 s on a 262 MB transcript with a 7.9 s `gh`.

**Found:** XR1 parent-side artifact reads (FIFO `snapshot.md`/`receipt.json`/`audit.md`) block PostCompact and SessionStart
past 15 s. **XR2 (fix-induced)** the backlog-exclusion matcher is quadratic: `"backlog #410 " * 100000` past 16 s. XR3 the
LIVE SessionStart (`session-state.py`) waits unbounded on an escaped `setsid` grandchild's pipe — 61 s against its 60 s
timeout. **XR4 (fix-induced)** a symlinked `.remember/compaction/<sid>` writes outside the directory. XR5 a delayed
PostCompact or a PreCompact racing SessionStart binds the wrong capture — session identity is not compaction identity.
XR6 / CR2 `backlog item: #410`, `backlog **#410**`, `backlog #364, #376 and #383` still name PRs. XR7 / Cr8 a PR list cut
at 100 audits as complete. **CR1 (fix-induced by 3c282379)** per-call `start_new_session` takes running calls out of the
capture's group, so a `sleep 61` survives the 11 s kill. **Cr6 (fix-induced)** the stale-audit message says "nonce" when
the epoch differed. Plus heading, docstring, CLAUDE.md and PR-body wording.

**THRASHING ARMED.** `print` carries fix-induced findings in round 2 (Cm7, Cm8) and round 3 (Cr6), consecutively, in one
component. Convened: `docs/reviews/architecture-review-2026-10-28-compaction-guards.md`. Its decision — SPLIT — is the
route for the round-3 fold. Reaching round 4: **thrashing, not a prose floor** — the evidence is above, and the review
names why each fix moved the outside rather than closing it.
