---
name: split-295-src-root-merged
description: "FIRES-WHEN: citing PR #310, PR #295, or the explainer-server restart feature — #310 MERGED (756c41fa, the /src/ half); #295 was RETIRED 2026-09-29 (PR #359) and its restart work refiled as backlog #193"
metadata:
  type: project
---

**Current state (verified 2026-11-14):**
- **PR #310 merged 2026-09-15 as `756c41fa`** — the `/src/` half split out of PR #295. `/src/` serves from the
  checkout the server runs from (verified live on master then: 200 for repo files, 404 for path escape and `.env*`).
- **PR #295 is RETIRED, not open** — "Retire PR #295: preserve its eight rounds of testimony, refile its work as
  backlog #193" (`3221ecdb`, PR #359, 2026-09-29). Do not revive it; the restart feature is backlog **#193**.
- Its blockers are closed: backlog **#122** (mutation manifest for `scripts/explainer-serve.py`) ✅, **#125** ✅,
  **#128** ✅ (`codex-review.py` deriving the verdict path from `--out` and overwriting committed verdicts — the
  "always pass a branch-specific `--out` stem" workaround is no longer required).

The restart work that #193 carries: `RESTART_LOCK`, `Handler._restart`, `/_alive`, `/_restart`, `RESTART_LOG`,
`respawn()`, `--restart`/`--respawn`, the pipe rewrite of `start()`, `page_chrome`'s restart control. When built,
rebase on master and review against the ratchet that #122 added.

## History
- Round 8 of #295 parked it by a pre-committed split rule; #310 shipped `/src/` alone. `scripts/explainer-serve.py`
  suite went 88 → 144 cases.
- #128 was measured twice on one branch (both restored) — third occurrence of
  [[a-guards-evidence-path-is-a-namespace-with-no-allocator]].
- The three rounds' real subject was the instrument, not the server — see
  [[proving-a-negative-by-interception-cannot-terminate]] and [[a-retrospective-number-needs-provenance]].
  Architecture review (including its own refuted conclusion): `docs/reviews/architecture-review-2026-09-15-src-caller.md`.
