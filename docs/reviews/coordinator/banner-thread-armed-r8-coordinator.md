# Round 8 — `banner-thread-armed` — coordinator — ✅ CONVERGED (provenance re-run)

```yaml
round: 8
fixes_nontrivial: false
subject: banner-thread-armed
halves:
  codex: ran
  claude: "GAP: provenance re-run — round 7 reviewed the same tree but was launched from the main checkout"
findings: []
```

REVIEW GAP: claude — this round repeats round 7's Codex review of the final tree, launched FROM THE WORKTREE so the verdict records the commit under review. Not a failure to run.

Why it exists: `codex-review.py` stamps the verdict's `head` from its own working directory. Rounds
1–7 of this branch were launched from the main checkout, so their verdicts name `master` (`cd7134f8`),
and `check-review-recorded` correctly reported that no round had seen the code. This verdict names
`4a02af85` with a clean tree. The review content of round 7 stands; only its provenance was wrong.
