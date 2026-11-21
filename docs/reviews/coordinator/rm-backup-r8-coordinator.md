# rm-backup — round 8 coordinator (Claude half; past the round cap)

Reviewed: the round-7 fold `fb91c343` (every `[` in an `rm` target is refused). The verdict was recorded
against `2ba7acbd`, the merge of origin/master on top of it. That merge changes none of
`scripts/check-rm-backup.py`, `scripts/mutations/` or `expected_mutations.py`; `git diff --stat fb91c343 2ba7acbd`
over those paths is empty.

**Verdict: CONVERGED — no BLOCKER.** The fold holds. Every attempt was run against `/bin/bash` 3.2:
- a `[` smuggled in through `$'\x5b'`, a variable, brace expansion, a command substitution or `"$@"` is refused,
  because the check runs after expansion;
- removing the bracket code reopened no `*`/`?` shape (11 shapes match bash);
- the literal/pattern split is intact;
- the manifest has 95 unique anchors.

Self-test 128/128. Sweep 95/95 killed.

| Finding | Severity | Disposition |
|---|---|---|
| R8-1 `find -rm` (bfs's name for `-delete`) passes the prefilter | MAJOR | **FILED** to backlog #686 — past the cap, not a BLOCKER |
| R8-2 a `-`-leading word is never globbed, so `rm -*` deletes a file named `-` | MAJOR | **FILED** to #686 |
| R8-3 an alias defined earlier in the command | MINOR | **FILED** to #686 |
| R8-4 `LC_ALL=C;` as a separate statement | MINOR | **FILED** to #686 |
| R8-5 no mutation on the `"*?"` glob-or-not check | MINOR | **FILED** to #686 |

None of the five comes from the round-7 fold; each is an older hole that this round found elsewhere.
Backlog row 686 now counts 18 measured shapes.
