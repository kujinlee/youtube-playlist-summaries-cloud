<!-- codex-review: model=gpt-6.1-sol -->

Found four issues:

1. **High — X1 still fails with duplicate refs.** [goal-tree.py:1055](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499/scripts/goal-tree.py:1055) keeps the first matching thread’s waits. Constructed valid threads:
   ```text
   - fix · backlog #1 · a
   - side · backlog #1 · b · waits on owner
   ```
   With row #1 live and no PR or ledger activity, the leaves derive `next` and `blocked`; the agenda derives `next`. Reordering the declarations changes the agenda’s answer. Universal parity needs a defined policy for conflicting declarations.

2. **High — X1 matches refs by order, and freezes incorrect replacement states.** A leaf naming `backlog #1, backlog #2` with `waits on owner` derives `blocked`; an agenda step naming `backlog #2, backlog #1` derives `next`. Recording its replacement freezes `next`. The requested mixed example also fails: reversing `backlog #1, PR #2` drops the declared wait from an inflight step’s detail.

3. **Medium — Closed-agenda writes still succeed and corrupt replay.** Starting from the accepted prefix `[agenda(id=1, free step), replaced(of=1)]`, both `tick_agenda(..., 1, ...)` and `record_agenda(...)` report success. Subsequent replay rejects the appended tick or duplicate replacement. [The writers](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/.claude/worktrees/build-499/scripts/goal-tree.py:1089) must check whether the last agenda remains open. This prefix requires an interrupted or externally constructed log; ordinary completed writes did not reproduce it.

4. **Medium — Pre-fold logs disable snapshots.** An agenda without `id` produces **exit 1**, `MALFORMED — agenda record 1 has id None, expected 1`, before snapshot append. Given this local, pre-release store, I favor an explicit one-time migration or reset over silently taking snapshot generation down. **The actual main-checkout record currently has `id: 1`**, contrary to the prompt’s premise; it passes this identity check. I separately reproduced failure with the pre-fold format.

Other requested checks:

- `_locked` holds its exclusive flock across reading, validation, callback, append, and close. Four concurrent writers produced 20 replayable agendas. Refused writes left existing bytes unchanged. No false MALFORMED arose from ordinary completed current-format writes.
- Missing agenda file: **2**. Directory as agenda file: **2**. Tick **0** and **−1**, with an existing agenda: **1**, range refusal, unchanged log.
- All **17** mutations containing `backlog #499`: every anchor occurs exactly once; all individually fail their named cases on a temporary scripts copy, without tracebacks.
- Mutation count and pin: **169**. Self-tests: **283/283**, matching the docstring.

No tracked files modified. `.claude/plans/` was not read.

VERDICT: NOT CONVERGED
