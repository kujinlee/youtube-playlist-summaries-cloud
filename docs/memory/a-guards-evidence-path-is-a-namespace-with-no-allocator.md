---
name: a-guards-evidence-path-is-a-namespace-with-no-allocator
description: "FIRES-WHEN: about to pass --out to codex-review.py — codex-review.py derives the verdict filename from the caller's --out stem, so naming an output r3-codex.md silently OVERWROTE the committed spec-round-3 verdict"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 566236fc-7408-4c0d-a3c9-fb655a2e4621
  modified: 2026-09-12T16:19:52.707Z
---

MEASURED 2026-09-03. Running the r3 CODE review with
`--out .../r3-codex.md` made `scripts/codex-review.py` write
`docs/reviews/verdicts/r3-codex.verdict.json` — a **committed** file belonging to the *spec*
round-3 review. It was overwritten (`4606 chars` → `2605 chars`). Restored from `HEAD`; the real
run re-saved as `codex-code-r3.verdict.json`.

**The convention that already existed:** code rounds use `codex-code-rN`, spec/plan rounds use
`plan-rN-codex` / `rN-codex`. Two different subjects legitimately want the same round number, and
nothing enforces the prefix.

**Backlog #68 closed the wrapper's path INFERENCE, not the collision CHANNEL.** The verdict path is
still derived from a caller-chosen stem; the guard writes evidence, and nothing checks the name it
writes to is unclaimed.

⚠ **A collision OVERWRITES, so the filesystem can never testify that one happened.** `ls | uniq -c`
shows every name exactly once whether or not it was clobbered — I ran that check and it was the
wrong instrument. Only `git status` / `git diff` reveals it, and only while the tree is dirty.

**How to apply:** pass `--out` with a stem that names the SUBJECT as well as the round —
`codex-code-r4.md`, not `r4-codex.md` — and run `git status` right after any `codex-review.py` call.
If a tracked verdict file shows as modified, you just overwrote someone's evidence.

---

## ⭐⭐ 2026-09-12 — THE SAME CLASS VIA **AGENT NAMES**, and `git status` COULD NOT SEE IT

Worse instance, different channel. A previous session left a subagent named `mut-review-r1-claude`
running. This session spawned another for the SAME task; the harness silently renamed mine
`mut-review-r1-claude-2`. **Both wrote `docs/reviews/claude/goal-page-mutations-r1-claude.md`.**
I read one, committed the other **without re-reading it**, and wrote the commit message and a
`check-plan-code.py` ratchet justification from the one that no longer existed.

Cost: a source comment justified moving a ratchet with *"Claude staged the tree, applied 24
candidate weakenings and measured 11 SURVIVING"* — **a measurement no committed artifact contains**.
And the surviving review's High (`parse_adr`'s front-matter split, a case that could not fail) was
recorded as CLOSED by work that never touched it. A round-2 reviewer found both by grepping the
file I had cited.

⛔ **THE INSTRUMENT THIS FILE ALREADY RECOMMENDED WOULD NOT HAVE CAUGHT IT.** The advice above is
`git status` — which works only for a **tracked** victim. Here both agents created the same
**untracked** file, so `git status` printed `?? …r1-claude.md` identically whether one review or
two had been written. Same blind spot as `ls | uniq -c`, one layer out.

**How to apply (revised):**
- **Two things may not share an output path.** Give every concurrently-dispatched agent a name that
  is unique *across sessions* (include the branch/round/subject), and a **distinct output path** —
  a name collision silently becomes a path collision.
- **Before spawning a reviewer, check whether one of that name is already running.** A leftover
  agent from a prior session is invisible until it writes.
- ⛔ **RE-READ any agent-written file immediately before committing it, and quote it from the
  COMMITTED copy when writing a commit message or a source comment.** Never write provenance from
  what you remember reading — that is the same failure as [[a-retrospective-number-needs-provenance]],
  with an agent instead of a recollection as the source.
- Two idle notifications for one dispatched task is the tell that two agents ran.

Related: [[a-report-format-is-a-contract]], [[measure-the-population-the-code-actually-sees]],
[[a-mechanism-can-be-silently-overridden]], [[a-retrospective-number-needs-provenance]],
[[concurrent-agents-go-wrong]], [[concurrent-agents-go-wrong]].
