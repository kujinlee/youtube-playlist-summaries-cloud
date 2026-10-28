---
name: run-pr-only-gates-before-push
description: "FIRES-WHEN: about to push a branch for a PR — the PR-only CI gates (namespaces, fixture variation) are not in my local habit, and ffmpeg flakes HIDE them"
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6abe358-4c0b-44cb-a058-5446372998ef
  modified: 2026-10-26T18:25:28.994Z
---

⛔ **2026-10-26: three PRs went red in CI on gates I never ran locally** — `check-reference-namespace.py --base
origin/master` (bare `#N` in rows I EDITED, incl. pre-existing text — 51 on the scrub) and
`check-fixture-variation.py` (a new function's parameter passed one value at every call site). ⚠ Worse: on PR #402 the
ffmpeg install failed first, twice, so `verify` never reached the namespace gate — a flake HID a real red for an hour.

**How to apply:** before every push of a PR branch run, in its worktree:
`python3 scripts/check-reference-namespace.py --base origin/master && python3 scripts/check-fixture-variation.py`
(plus check-docs, check-selftest-counts). `check-merge-ready.py --pr N` runs the PR-only steps too, but only after
CI exists. A new pure function: vary EVERY parameter in at least two cases. When CI fails on ffmpeg, the steps
after it were NOT run — run them locally before calling the branch green.

See [[a-check-result-is-not-the-claim]], [[parallel-threads-need-a-thread-map]].

⛔ **AND READ `$?` BEFORE ANY OTHER EXPANSION — TWICE ON 2026-10-26.** `echo "$(basename $c) rc=$?"` and
`echo "$w $(git rev-parse HEAD) recorded=$?"` both printed the INNER command's status (always 0), so every gate in
those loops read green while three branches had real reds. Write `cmd; rc=$?; echo "... rc=$rc"` — always.
⚠ Related cost, worth a backlog row: `check-plan-code.py`'s literal mutation TOTAL conflicts on EVERY concurrent PR
(and once merged SILENTLY wrong, 2115+2115 → 2115 instead of 2125), and each resolution then needs a confirmation
round because `check-review-recorded` sees `check-plan-code.py` changed. Set it from the real sum, never by hand.
