---
name: an-instrument-that-edits-the-repo-corrupts-its-peers
description: "FIRES-WHEN: running an instrument that writes tracked files, severing a tracked file to test a guard, or about to git add -A in a tree another agent can write — mutate a COPY, stage explicit paths, never repair one review while another reads"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 562085d6-32ed-48ac-9814-b2f5e07b1cfe
  modified: 2026-09-14T00:42:42.301Z
---

**RULE: never mutate the tree you (or anyone else) are measuring or committing from.**
- **Instruments and severs work on a COPY.** Copy the whole tree and mutate the copy — never sever a
  tracked file and `git checkout --` it back:
  ```bash
  BASE=$(mktemp -d); TMP=$BASE/tree; mkdir -p "$TMP"
  (cd "$WT" && tar cf - --exclude=.venv --exclude=node_modules .) | (cd "$TMP" && tar xf -)
  ln -s "$WT/node_modules" "$TMP/node_modules"
  ```
  ⚠ **A PARTIAL copy gives a RED CONTROL and then measures nothing** — prove the control green on the
  copy BEFORE trusting any sever on it. If you must touch a tracked file, `shasum` it before and after.
- **Stage explicit paths. `git add -A` is unsafe** in a tree any other agent can write to — which is the
  normal case here. Before committing, `git diff --cached --name-only` and ask whether every path is yours.
- **To back out someone else's file from your commit, update only the index:**
  `git restore --source=master --staged <path>` then commit. `git checkout master -- <path>` overwrites
  the WORKING TREE and destroys work still being typed.
- **Never repair review A while review B reads the same tree.** Serialise, or give B its own checkout.

**Why:** *any instrument that mutates the tree it measures cannot be run twice at once* — and two
reviewers, or a hook and a human, dispatched in parallel is the standing pattern here. None of the
must-serialise operations is mechanically enforced (backlog #67) — these are conventions.

## History
- **2026-08-08, round 8:** `mutate-schema.py` wrote mutations into repo-tracked `schema/*.sql` and
  restored in a `finally`. Two concurrent `check-schema-gates.sh` runs read each other's edits:
  **23/44** in the repo (21 `RED(other)` carrying another mutation's detail) vs **44/44** on an isolated
  copy. Failed loud and wrong; `finally` does not survive `SIGKILL`. Fixed by `cp -r` to a temp dir —
  two suites simultaneously, both 58/58, checkout clean. Same day, two siblings that could not report
  themselves: `classify()`'s `RED(constraint)` branch never compared `expect`; `check-guard-coverage.py`
  enumerated triggers on only two tables.
- **2026-09-13/14 (PR #297), no instrument needed:** (a) my `git add -A` swept another session's
  half-finished `scripts/codex-review.py` into my commits; CI red with
  `[DRIFT] the docstring declares 68 cases; the suite ran 73`. (b) I fixed Codex's findings in the tree
  the Claude half was reviewing; it disclosed three `HEAD`s and re-ran every attack — its discipline,
  not my design.
- **2026-10-13:** I severed `.agents/skills/handoff/SKILL.md` to prove a falsifier, then
  `git checkout --` restored it to HEAD — discarding FOUR uncommitted fold edits. The guard was green
  either way; only a `shasum` before/after caught it. Same day a partial copy (`scripts/ docs/ supabase/`)
  gave a 294/297 control vs 297/297 on the full tree — discarded as CANNOT RUN.

See [[what-mutation-testing-proves]], [[test-harness-can-launder-failures]],
[[guard-classification-shape-vs-sequence]], [[blob-addressing-spec-state]],
[[concurrent-agents-go-wrong]].
