---
name: split-295-src-root-merged
description: "FIRES-WHEN: citing PR #310, PR #295, or the parked restart remainder — PR #310 MERGED (756c41fa) — the /src/ half split out of parked #295. #295 remains OPEN with the restart feature, blocked behind #122; do NOT merge it as-is"
metadata:
  type: project
---

**PR #310 merged 2026-09-15 as `756c41fa`.** It is the `/src/` half extracted from PR #295, which
round 8 parked by a pre-committed split rule. `/src/` now serves from the checkout the server runs
from — verified live on master, 200 for repo files, 404 for path escape and `.env*`.

⛔ **PR #295 IS STILL OPEN AND MUST NOT BE MERGED AS-IS.** It still contains the `/src/` work, now on
master by a different route, so merging would re-apply a superseded copy. Its body records the split.
What remains parked: `RESTART_LOCK`, `Handler._restart`, `/_alive`, `/_restart`, `RESTART_LOG`,
`respawn()`, `--restart`/`--respawn`, the pipe rewrite of `start()`, `page_chrome`'s restart control.
Backlog **#125/#126/#127** travel with them, **all blocked behind #122** (seed
`scripts/mutations/explainer-serve.json`). When #122 lands: rebase the remainder on master and
re-review against a ratchet that works.

**Filed this branch: backlog #128** — `codex-review.py` derives the verdict path from the caller's
`--out` stem, so a generic stem OVERWRITES a committed verdict belonging to unrelated merged work.
Measured twice on one branch; both restored. Third occurrence of
[[a-guards-evidence-path-is-a-namespace-with-no-allocator]]. **Until it is fixed, always pass a
branch-specific `--out` stem** — that workaround is explicitly not the fix.

**The three rounds' real subject was the instrument, not the server** — see
[[proving-a-negative-by-interception-cannot-terminate]] and
[[a-retrospective-number-needs-provenance]]. Architecture review (including its own
refuted conclusion): `docs/reviews/architecture-review-2026-09-15-src-caller.md`.

`scripts/explainer-serve.py` suite is now **144 cases** on master (was 88).
