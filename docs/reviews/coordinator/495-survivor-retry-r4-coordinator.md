# Round 4 — `495-survivor-retry` (PR #564, backlog #495) — coordinator — CONVERGED (Codex), scoped to the r3 fold

Codex half: `docs/reviews/codex/495-survivor-retry-r4-codex.md`, reviewed `1b9110e0` (the r3 fold `5abc9c2c` plus a merge of
master), scope `73f27830..5abc9c2c`.

REVIEW GAP: claude — alternation (rounds 2+ run ONE half; round 4 is Codex's, scoped per `docs/review-method.md` §0 Q4c).

```yaml
round: 4
fixes_nontrivial: false
subject: 495-survivor-retry
halves:
  codex: ran
  claude: skipped
findings: []
```

The round answered one question — does the r3 fold introduce a BLOCKER? — and found none. Self-tests: sweep-red-alert 33/33,
check-plan-code 443/443, batch-ci 169/169, check-merge-ready 400/400; the sweep-red-alert manifest 23/23 killed. Driving `main`
through a fake `gh` over five shard shapes (38/38 with 0 or 1 FLAKY, 37/38 with 1 or 0, 0/38), under both a green and a red sweep:
every found FLAKY name is filed before a missing shard fails the run, no incomplete scan claims "no FLAKY", and `sweep-red` opens on
every red sweep and on no green one.

Loosening answer `3658aa4ac1f3` names the change the owner asked for (backlog #495, 2026-11-11 19:25): a first-run survivor whose one
fresh re-run kills it by its named case stays green as FLAKY, where master rejected every survivor. That is the requested rule, not a
defect; the harness cases keep it a survivor, never a kill, and it is filed as a `sweep-flaky` issue.

Review closed. Remaining FILE-ONLY items are backlog #617 and the armed Phase 6 review, backlog #618.
