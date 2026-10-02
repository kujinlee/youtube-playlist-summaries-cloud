---
name: mutation-harness-home-redirect-state
description: "FIRES-WHEN: citing PR #181 or the mutation harness HOME redirect — ✅ MERGED 2026-08-30 — GitHub PR #181 (`ebec7bc`), Phase 6 candidate 3, the HOME question decided. ⚠ $HOME governs Path.home() and a bare ~ and NOTHING else: getpwuid() and ~user reach the real home"
metadata: 
  node_type: memory
  type: project
  originSessionId: 8e2946ca-210f-40fa-a95f-012c8dc525e5
  modified: 2026-08-31T04:24:33.116Z
---

**✅ MERGED 2026-08-30 — GitHub PR #181, squash `ebec7bc`, branch deleted.**

## What it decides

Phase 6 **candidate 3**, from architecture review 2026-08-30's *"what we decided that isn't written
down"* item 2. It was never a decision — `grep HOME scripts/check-plan-code.py` returned nothing.
Now `run_suite` (the ONLY spawn point of a delivered script, 4 call sites) runs every child under a
`HOME` redirected into the run's own temp tree, via `child_env(d)`.

**The trade it was posed on measured ZERO:** no hardcoded home literal anywhere in `scripts/` or
`scripts/mutations/` (control-backed grep), so every home assertion computes `Path.home()` on both
sides and shifts together. `--mutate .` held at **73 mutations / 0 survivors** throughout.

## ⚠ The scope fact worth keeping

**`$HOME` governs `pathlib.Path.home()` and a bare `~`. Nothing else.** Measured under a redirected
home: `getpwuid(os.getuid()).pw_dir` and `expanduser("~<user>")` both returned `/Users/kujinlee`.
`home_escapes()` in `check-plan-code.py` is the standing guard — it refuses a mutation target *or a
mutation's replacement text* using those routes. Static, therefore incomplete, and its docstring says
so.

## Review round 1 — 4 findings, all fixed in-branch

`docs/reviews/home-redirect-{codex,coordinator}-r1.md`. Codex: the scope overclaim above; `check()`
(plan mode) got the redirect but never created the directory; the canary's identity was its filename
so cleanup could delete a same-named real file (identity is now its CONTENT). Coordinator, against
Codex #1's own fix: the scan read the source BEFORE the mutation —
[[fixing-a-premise-is-not-covering-the-branch]], second occurrence.

⚠ **REVIEW GAP recorded:** the Claude half was coordinator-run, not an independent subagent.
`check-review-rounds.py` REFUSED the round while the file was named `-coordinator-` — the check
drawing exactly that distinction — and the gap line is the honest resolution, not a rename to
`-claude-`. Good behaviour; expect it.

## The falsifier pattern, worth reusing

A redirect over scripts that write nothing under `~` today is **invisible when broken** — "it held"
and "nothing tried" are the same observation. So the guard asserts the PROPERTY: a child that really
writes to `Path.home()/explainers/` lands in the run's tree and NOT the reader's.
[[assert-the-property-not-the-mechanism]]. Mutation-test it with the PARENT's `HOME` redirected too
(`HOME=$(mktemp -d) python3 scripts/check-plan-code.py --self-test`), or proving it load-bearing
means writing into the real tree — [[a-mutation-loses-its-binding]].

## Also carried in this PR

`docs/roadmap-to-launch.md`'s inline-renderer section said **PR OPEN**; corrected to merged via #180.
Batched rather than pushed to master alone.

## Open

1. The merge (human gate).
2. The **candidate 4** recommendation — see [[a-costbenefit-finding-expires-when-the-denominator-moves]].
   Not filed; filing is the user's step.
