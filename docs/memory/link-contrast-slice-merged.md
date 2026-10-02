---
name: link-contrast-slice-merged
description: "FIRES-WHEN: citing PR #175 or dark-mode link contrast — PR #175 MERGED 2026-08-29 (squash 96626cd) — dark-mode link contrast + the guard rewrite; two dual review rounds found 6 defects after the branch was called ready"
metadata: 
  node_type: memory
  type: project
  originSessionId: 44b2b306-b802-467e-8eb8-4d81cc0ddd80
  modified: 2026-08-30T00:39:46.971Z
---

**MERGED 2026-08-29T22:31Z — PR #175, squash `96626cd`, branch deleted.** Follow-on to PR #174
(`5620150`, the dashboard slice). Master gates re-verified green *after* the squash: gen-dashboard
**113/113**, gen-backlog-page **73/73**, check-plan-code 121/121 + `--compare . --verify-evidence`
at 2 files / 43 mutations / 0 survivors.

**It arrived unreviewed and two dual rounds found SIX real defects — five by a reviewer, one by me.
Three were in fixes written during the review itself.** See
`docs/reviews/pr-175-link-contrast-{claude,codex}{,-r2}.md`.

What shipped: `--link`/`--link-visited` on the dashboard (1.90:1 → 8.90:1 dark); an **unscoped**
`a{}` on the backlog page (five correct scoped rules missed 3 links at 1.84:1); and both guards
rewritten from *presence* to **measured WCAG ratio** — see
[[assert-the-property-not-the-mechanism]] for the general lesson, which is the durable part.

## Still open, deliberately not fixed here

- ~~**Backlog #70 — the manifest gap**~~ → **#70 is CLOSED, PR #176 merged 2026-08-29 (`da5cd27`).**
  See [[mutation-manifest-retarget-merged]]. ⚠ **The gap this bullet named did NOT close with it.**
  #70 moved the manifest onto the delivered scripts (44/0) — it did not widen coverage, and a branch
  review then measured **six survivors the manifest misses**. `--verify-evidence` is gone from CI;
  the successor question is the same one, now asked of `--mutate .`. Carried into **backlog #69**.
- **`--ink-3` is sub-AA as BODY TEXT on the backlog page** — 4.26:1 on `--ground`, 4.22:1 light /
  4.40:1 dark on `--pending-bg` (`h2`, `.cnt`, `.rootref`, figure captions). Pre-existing, **not** a
  link defect, **NOT FILED** — filing is the user's step ([[feedback-agree-before-filing]]).
- Round 3 was never run. Round 2 converged with nothing outstanding, and the user chose to merge.

## The queue after this

~~Backlog **#70**~~ (done, `da5cd27`) → **#69** (external `--self-test` count ratchet) → **#67/#68**
(concurrent-agent interference; the Codex gate failing silently). See [[launch-roadmap-state.md]].

⚠ `.remember/remember.md` and `docs/dashboard-entries.md` both describe this branch as OPEN in
places written before the merge. **Git is the truth** — check `git log --oneline -3` on master.
