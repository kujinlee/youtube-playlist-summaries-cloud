# Round 6 — `mutation-early-stop` (PR #476, backlog #405) — coordinator — CONVERGED (Codex half); one Medium FILED

Codex half: `docs/reviews/codex/mutation-early-stop-r6-codex.md`, which reviewed `a8698566`, the tree with early stop
withdrawn.
REVIEW GAP: claude — alternation (rounds 2+ run ONE half per round, `docs/review-method.md` → *Round topology*).

```yaml
round: 6
fixes_nontrivial: false
subject: mutation-early-stop
halves:
  codex: ran
  claude: skipped
findings:
  - {id: X6-M1, severity: Medium, aim: deliverable, fix_induced: false, component: ci-concurrency, disposition: filed}
```

- **X6-M1: filed as backlog #482**, under the round cap (r4+ findings are filed unless a BLOCKER). Codex verified it
  against GitHub's documented semantics but did not execute it. GitHub replaces a group's PENDING run with the newest
  one, so `cancel-in-progress: false` on master protects only a RUNNING run. The claim "a push to master is never
  cancelled" was too strong. Three of its copies (backlog #405, the dashboard entry and the PR body) now say RUNNING and point at #482. The `ci.yml` comment is left as it was, because editing it would need a seventh round on a comment. #482's fix rewrites that line, and the row says so. The configuration did not change.
- **Codex confirmed the rest:**
  - both harness files are byte-identical to master;
  - no early-stop flag remains;
  - `--no-renames` can only turn the sweep ON;
  - the merge-ready allowance is exact;
  - rows #480 and #481 are accurate;
  - the merge-ready self-test passes 256/256.
