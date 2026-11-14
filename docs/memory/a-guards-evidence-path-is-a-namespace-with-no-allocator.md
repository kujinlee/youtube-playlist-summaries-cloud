---
name: a-guards-evidence-path-is-a-namespace-with-no-allocator
description: "FIRES-WHEN: choosing a --review-id / output path for codex-review.py, or spawning agents that write files — two writers sharing one output path silently clobber evidence (a committed verdict was overwritten; two same-named agents wrote one review file). Unique id + distinct path per writer; RE-READ before committing"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 566236fc-7408-4c0d-a3c9-fb655a2e4621
  modified: 2026-09-12T16:19:52.707Z
---

**The rule: any evidence path chosen by a caller is a namespace with no allocator — a collision OVERWRITES, so the
filesystem can never testify that one happened.**

**How to apply (current):**
- **`codex-review.py`:** the verdict file is now named from the REQUIRED `--review-id`
  (`docs/reviews/verdicts/<review-id>.verdict.json`, `verdict_path()`), not from the `--out` stem; `--out` is scratch and
  must be OUTSIDE the repository, and an existing filed review is refused (exit 3) unless `--allow-overwrite`
  (verified in `scripts/codex-review.py` 2026-11-14). So the collision now lives in the **review-id**: make it name
  the SUBJECT as well as the round (`<subject>-r<N>-codex`), never a bare `r3-codex`.
- **Two writers may not share an output path.** Give every concurrently-dispatched agent a name unique *across sessions*
  (branch/round/subject) and a **distinct output path** — a name collision silently becomes a path collision.
- **Before spawning a reviewer, check whether one of that name is already running** (a leftover from a prior session
  is invisible until it writes). Two idle notifications for one dispatched task = two agents ran.
- ⛔ **RE-READ any agent-written file immediately before committing it, and quote it from the COMMITTED copy** in a
  commit message or source comment — never from what you remember reading
  ([[a-retrospective-number-needs-provenance]]).
- `git status` reveals a clobbered **tracked** file only; an **untracked** victim looks identical whether one or two
  writers hit it, and `ls | uniq -c` shows nothing either way.

## History

- **2026-09-03:** `--out .../r3-codex.md` made `codex-review.py` write `docs/reviews/verdicts/r3-codex.verdict.json`,
  a **committed** file belonging to the *spec* round-3 review (`4606 chars` → `2605 chars`). Restored from `HEAD`; the
  real run re-saved as `codex-code-r3.verdict.json`. Backlog #68 closed the path INFERENCE, not the collision channel.
- ⭐⭐ **2026-09-12, via AGENT NAMES:** a prior session's `mut-review-r1-claude` was still running; the harness renamed
  mine `mut-review-r1-claude-2`, and **both wrote `docs/reviews/claude/goal-page-mutations-r1-claude.md`**. I committed
  the survivor without re-reading it and justified moving a `check-plan-code.py` ratchet with *"Claude staged the tree,
  applied 24 candidate weakenings and measured 11 SURVIVING"* — **a measurement no committed artifact contains** — and
  recorded the surviving review's High (`parse_adr`'s front-matter split) as CLOSED by work that never touched it. A
  round-2 reviewer found both by grepping the cited file.

Related: [[a-report-format-is-a-contract]], [[measure-the-population-the-code-actually-sees]],
[[a-mechanism-can-be-silently-overridden]], [[concurrent-agents-go-wrong]].
