# Round 4 — `merge-when-ready-rule` — coordinator — ⏸ STOPPED, DEFERRED (3 Medium, all fail CLOSED)

```yaml
round: 4
fixes_nontrivial: false
subject: merge-when-ready-rule
halves:
  codex: ran
  claude: skipped
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: true, component: path-identity, disposition: declined}
  - {id: XM2, severity: Medium, aim: deliverable, fix_induced: true, component: path-identity, disposition: declined}
  - {id: XM3, severity: Medium, aim: deliverable, fix_induced: true, component: path-identity, disposition: declined}
```

REVIEW GAP: claude — round 4 alternates to the Codex half on the final tree (`review-method.md`, *The
protocol*, step 4; backlog #339).

`X` = Codex half, final tree `882166b6`, run against real git diffs. It re-applied all 50 mutations over a
green control (50/50 via their named cases) and reproduced the 8-of-40 replay.

**Thrashing or prose floor? THRASHING**, in one component. Rounds 3 and 4 both carry findings caused by the
previous round's own fix in `path-identity`: r3's lazy header split (XM1, ` b/` inside a path), r3's
`_unquote` (XM2, literal Unicode under `core.quotePath=false`), and r3's role comparison (XM3, a gained role
read as a lost one). Each round has found a NEW path shape after fixing the last. The cause is structural:
paths are recovered from human-readable patch headers, a format with no end of edge shapes.

**Why stop here rather than fold:** all three fail CLOSED — XM1 and XM3 are false HOLDs (the owner is
notified, nothing merges) and XM2 is a crash (exit 1, NOT READY). None is a false READY, which is the one
direction the house rule exists to prevent, and no detector-logic probe has failed since round 2.

**Dispositions — all DECLINED here and FILED as backlog #353,** on the owner's ruling (card, 2026-10-25,
option A: defer, ship as is). The row names the class fix (paths and statuses from
`git diff --name-status -z -M`, patch text for hunks only) and the condition that reverses the deferral:
any path shape yielding a false READY. Decision log: the split bet is scored LOST and a `defer` row closes
the unit at round 4.

**`check-review-decision.py` arms ARCHITECTURE_REVIEW** (thrashing in `path-identity`, r3 and r4), and that is
recorded, not skipped. Its question — *can a redesign remove the class?* — already has an answer: yes, by not
parsing paths from patch headers at all (`git diff --name-status -z -M`). That redesign IS backlog #353's class
fix, so the review's output is filed rather than convened; the owner's defer ruling covers convening it now. ⚠
Nothing gates on that verdict (no CI step, hook or merge check reads it), so this paragraph is the only record.
