# Round 2 — `dashboard-retire-spec` — coordinator — ⟳ NOT CONVERGED (Codex); 2 fixed, 0 rejected

REVIEW GAP: claude — alternation (rounds 2+ run one half; the Claude half ran round 1 and runs round 3).

```yaml
round: 2
fixes_nontrivial: true
subject: dashboard-retire-spec
halves:
  codex: ran
  claude: gap
findings:
  - {id: XM1, severity: Medium, aim: deliverable, fix_induced: false, component: store-gate, disposition: fixed}
  - {id: Xm1, severity: Low, aim: deliverable, fix_induced: false, component: retired-reference-gate, disposition: fixed}
```

Subject: `docs/superpowers/specs/2026-11-24-dashboard-retire-design.md` at `5eb16ffa` (reviewed); fold at the
commit after it.

- Codex half: `docs/reviews/codex/dashboard-retire-spec-r2-codex.md` — 1 MAJOR, 1 MINOR (here XM1, Xm1). NOT
  CONVERGED.
- Claude half: not run (alternation).

**Method — what was run in the fold, not taken from the half:**
- XM1: read the id scheme — `parse_entries` assigns `entry["id"] = f"{date}/{seen[date]}"`
  (`scripts/check-dashboard-entry.py:671`), purely positional; `_slug` (`scripts/gen-dashboard.py:769`) only
  escapes that id, so no stable key exists. Built a four-entry fixture (old narrative; master's same-day ask A;
  the branch's ask B; the branch's `[resolved: 2026-11-25/1]` written when B was `/1`) and ran the real
  `parse_entries`, `unresolved` and `added_reference_errors`: authored view, 0 open; merged master-first, ask B
  OPEN and ask A silently closed; `added_reference_errors(new_base, merged)` = `[]`; K9's prefix holds. Codex's
  claim CONFIRMED. The hazard exists TODAY (today's reference check is the same function); whether it ever fired
  on master was not measured.
- Found in the same fixture, a defect in r1's K9 text: an exact `raw` prefix refuses every ordinary append,
  because the base's LAST entry keeps a trailing blank line only while it is last. With `raw.rstrip()` the prefix
  holds. K9 now compares rstripped text. Not a review finding; recorded so round 3 reviews it.

## Dispositions

| Finding | Severity | Disposition | Spec section changed |
|---|---|---|---|
| **XM1** K9 compares with the current merge base, so a merge of master shifts the branch's same-day ids and its answer resolves master's ask | Medium | FIXED with the smallest mechanism inside the unchanged grammar (a stable key would be a grammar change, out of scope): new **K10** — for each added `[resolved: X]`, X's target at the first first-parent branch commit holding that entry must be X's target at HEAD (by `raw.rstrip()`). Rewriting the id in the merge passes, since the rewritten entry first appears at the merge. Three commit-built fixtures (the shift refused with K9/K1–K3 passing as control; the rewritten answer passes; an answer to a merge-base entry passes). Bound stated: a REBASE replays the shifted id and K10 cannot see it | §2.1; §2.2; §3 K9, new K10, CI paragraph; §4.2 rename row; §5 S2; §8 three rows |
| **Xm1** K8's acceptance only says "K8 passes"; a scanner that finds nothing would pass | Low | FIXED: K8's `--self-test` seeds one retired reference per covered category (each must fail) and two passes (a prose/comment mention, the `RETIRED_FILES` row); S3's acceptance names them | §3 K8; §5 S3 |

**Non-trivial fixes (why `fixes_nontrivial: true`):** K10 is a new history-reading check; K9's comparison
changed to `rstrip`. Round 3 (Claude half, by alternation) owes a review of both.
