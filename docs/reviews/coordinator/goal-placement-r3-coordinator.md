# Round 3 — `goal-placement` (backlog #514 c + d, PR #588) — coordinator — ✅ CONVERGED (Claude); STOPPED; THRASHING armed → backlog #646

```yaml
round: 3
fixes_nontrivial: false
subject: goal-placement
halves:
  codex: gap
  claude: ran
findings:
  - {id: N1, severity: Nit, aim: deliverable, fix_induced: true, component: waits, disposition: filed}
  - {id: N2, severity: Nit, aim: deliverable, fix_induced: true, component: timeline, disposition: filed}
```

REVIEW GAP: codex — alternation (round 3 is one half; Codex ran round 2).

Half: `docs/reviews/claude/goal-placement-r3-claude.md`, head 84ca2b0a. CONVERGED: no BLOCKER, MAJOR or MINOR; r2's
three findings did not recur in any constructed form. Both nits were filed, not folded — folding would add a fourth
unreviewed fix to the component under watch.

| Finding | Disposition |
|---|---|
| **N1** — a PARKED entry's wait on a `next` thread leaves the leaf ⬜ next, where the same wait on the thread line makes it blocked. The information is shown either way; only the glyph differs by source. | FILED → backlog #646 |
| **N2** — handoff identity is the ledger id cut to 60 characters, so two ids sharing a 60-character prefix collide (the cut already keys `placed`/`inflight_loose` on master; the ledger has no id that long). | FILED → backlog #646 |

**THRASHING — the rule, quoted (`docs/dev-process.md`):** *"two consecutive rounds carry findings caused by the
previous round's own fix, in one component"*. r2's three findings were caused by the r1 fold, r3's two by the r2 fold,
both in the ledger-placement component of `scripts/goal-tree.py` (waits + timeline). The reviewer judged the nits too
small to count; the rule names no severity floor, so it FIRES. The precedent (backlog #629, backlog #639) is: the
change merges on READY and the Phase 6 review is filed, with the round's findings inside it. Filed as backlog #646.

**CI fix in this fold (not a review finding):** CI refused `scripts/mutations/goal-tree.json` — the r2 entry
"joining two items keeps only the first wait" repeated the anchor of "a wait declared under a later goal is lost". Its
anchor now spans the next line too; the mutation is unchanged. `load_manifests`: 5100 entries, no problems.
