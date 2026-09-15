<!-- codex-review: model=gpt-5.5 -->

**Findings**

High — `scripts/check-review-decision.py:123-125`, `scripts/check-review-decision.py:301-313`, `scripts/check-review-decision.py:108`  
Round adjacency is inferred from list position, not from a validated gapless round sequence. `rounds_for()` parses and sorts by `round`, but never rejects missing rounds or duplicate round numbers; then `converged()` slices `rounds[-need:]`, and `thrashing_component()` compares `rounds[-2]`/`rounds[-1]`.

I confirmed in-process that `r1 + r3` returns converged for a full-loop branch, and `r1 + r3` with fix-induced findings in the same component arms thrashing. A lost `r2` can therefore become either a false `STOP` or a false/false-negative architecture-review decision. Duplicate `r2` documents have the same problem: two records claiming one round can count as two consecutive rounds. This violates the tool’s own “missing input is failure, never pass” posture.

Previous fix caused this? No. This looks like an original sequencing gap, exposed by the new “recorded evidence” model rather than introduced by the r4 repair.

**Override Attack**

I do not have a redesign that dissolves the `tests/` / `.claude/` / `.agents/` question without still needing a policy input. A model like “prose vs executable/operational influence” or “blast radius by authority” still has to decide whether tests, hooks, skills, and agent instructions carry enough authority to require full-loop. That is not a carve-out-list failure in the r1-r3 sense; it is the contained-set boundary itself. I would uphold the coordinator’s override on that point.

**Other Checks**

`r10` vs `r1`: okay. `rounds_for()` does a final numeric sort by parsed `round`, so lexical filename order does not control the result.

The r4 classifier stand-in is not silently green. If `_repo_is_prose()` fails and `_prose = lambda _p: True`, the full-loop scope cases go red, as intended.

Sample card citations resolve. The card currently has 12 `:line` refs, including `:169` to “Can a redesign remove it?”, `:273` to the concurrency table, `:345` to “Hold both halves UNCOMMITTED”, `:400` to the superseded Medium decision rule, and `:454` to recording the call.

`TREE` exit 1: I am not filing this. `TREE` is not a round owed, but it is still “action required,” and the script explicitly declares `NO-CALLER`; CI should not be gating on it. The prose contract could be clearer, but I do not see a live bug under the declared use.

Self-test confirmed: `python3 scripts/check-review-decision.py --self-test` → `49/49`.

**NOT CONVERGED** — one High finding.
