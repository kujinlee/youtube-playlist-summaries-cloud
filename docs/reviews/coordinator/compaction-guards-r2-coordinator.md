# Round 2 — `compaction-guards` — coordinator — ⟳ NOT CONVERGED (Codex); REDESIGN two components

Claude half: a narrow wording review (does each printed sentence claim more than the code does) on the pinned 44ae10d9 — `docs/reviews/claude/compaction-guards-r2-claude.md`, 5 Major + 8 Minor, NOT CONVERGED.

```yaml
round: 2
fixes_nontrivial: true
subject: compaction-guards
halves:
  codex: ran
  claude: ran
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: extraction, disposition: fixed}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: extraction, disposition: fixed}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: XM4, severity: Medium, aim: deliverable, fix_induced: true, component: print, disposition: fixed}
  - {id: XM5, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Xm6, severity: Low, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: CM1, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: Cm2, severity: Low, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: CM3, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: CM4, severity: Medium, aim: deliverable, fix_induced: false, component: audit, disposition: fixed}
  - {id: CM5, severity: Medium, aim: deliverable, fix_induced: false, component: snapshot, disposition: fixed}
  - {id: CM6, severity: Medium, aim: deliverable, fix_induced: false, component: extraction, disposition: fixed}
  - {id: Cm7, severity: Low, aim: deliverable, fix_induced: true, component: print, disposition: fixed}
  - {id: Cm8, severity: Low, aim: deliverable, fix_induced: true, component: print, disposition: fixed}
  - {id: Cm9, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm10, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm11, severity: Low, aim: process, fix_induced: false, component: prose, disposition: fixed}
  - {id: Cm12, severity: Low, aim: deliverable, fix_induced: true, component: prose, disposition: fixed}
  - {id: Cm13, severity: Low, aim: deliverable, fix_induced: false, component: prose, disposition: fixed}
```

Codex on `44ae10d9`. All six round-1 reproductions now fail. **XM1** a question from another session (or a summary,
notification or wrongly typed flag) still authorises an answer, and a repeated question record reopens a consumed id.
**XM2 (fix-induced)** the new paste parser is quadratic: 450,000 chars of openers ran past 16 s. **XM3** a FIFO dashboard
read and a joined executor thread keep the process alive past the 15 s timeout. **XM4 (fix-induced)** PostCompact takes
the LATEST receipt, so session A's summary is audited against B's capture. **XM5** a corrupt ledger still yields "names
everything". **Xm6** owner-wait keys bypass the bound (15,700 chars). **Held:** 82/82, 57/57, 39 + 30 mutations, 2,405
real, 18 hooks, worktree ledger read/write, rc 0 on garbage, the 48-status case in 10.03 s, the 82 MB transcript in 0.45 s,
and the RECORDED wording.

**Thrashing?** No: two fix-induced findings in round 2, none in round 1, so no two CONSECUTIVE rounds with fix-induced
findings in one component. **But the route moves to REDESIGN for two components**, because both failures are classes, not
instances. XM2 + XM3 show that a deadline enforced inside the process cannot bound the process: each patch closes one
path, and a blocking read or a joined thread opens the next. That is the same shape as #373, #376 and #382 — proving a
negative from inside the interpreter. XM4 shows that one shared slot makes every reader responsible for not mixing
sessions. Process isolation with a hard kill, and per-session directories, remove both by construction.

**The Claude half found what Codex did not, and the overlaps confirm the redesign.** CM1 (`backlog #376` counted as
the open PR #376 — five of seven open PR numbers collide with backlog rows) and CM3 (5 of 37 asks audited, reported as
"names everything") make the completeness claim false on TODAY's state. CM5 (one 10 s deadline is false: 19.6 s on a
250 MB transcript) and CM4 (a failed main-checkout lookup audits as an empty ledger) are XM3 and XM5 found
independently, from the wording side. Process isolation is the fix that covers CM5 and XM3 together.
