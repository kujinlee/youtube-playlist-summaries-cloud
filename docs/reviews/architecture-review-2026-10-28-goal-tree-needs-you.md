# Architecture review — 2026-10-28 — the goal tree's NEEDS YOU list and its rebuild trigger (PR #433, backlog #363)

**Convened by THRASHING:** `needs-you` and `regen-hook` carry fix-induced findings in rounds 2 and 3, consecutively.

## The wall — the sixth subject in two days

After the fixture, em, import-time-launch, compaction-guard and memory-budget-hook reviews: **a check that infers a
property of arbitrary text that the text can defeat.** Here two claims: *"these sources state the same decision"*
(read from prose in round 1, from a token in round 2 — and the token can contradict the prose beside it), and
*"this Bash command runs `gh pr merge`"* (a regex in round 1, a quote-aware tokenizer in round 2 — and quoting,
escapes, heredocs and assignments each defeat a tokenizer that is not bash).

## What held

NOT READ propagation from every source (no false all-clear since round 1); decisions apart from actions; a count only
from an explicit annotation; the may-be-answered flag only from an explicit `backlog #N`; the replay notice; every
generator bounded and independent. The backlog data: four rows decided on the rows' own recommendations, four more
under the standing rule with written reasoning, #306 the owner's, #126 and #347 answered through their parents.

## Decision (owner's standing AFK rule — not critical)

**SPLIT.**
1. **The rebuild trigger stops parsing shell.** It fires when the Bash command TEXT contains `gh pr merge` — a plain
   substring test, deliberately over-eager. A false fire costs one rebuild (~18 s); a miss needs `eval`, an alias or a
   merge spelled without that text, and the docstring states it. The tokenizer is deleted, with its mutation entries
   retired. The page's built-at time and replay notice make staleness visible either way.
2. **Identity stays structural and becomes conflict-safe.** An item's kind comes from its own marker (`ACTION:` or
   `NEEDS-OWNER-ACTION`); an identity token that disagrees with it does NOT merge and is reported as a conflict on the
   page. Identity and count are parsed from the same whole source entry before any text is shortened.
3. **#318's reasoning is corrected** to the recorded history; the vocabulary choice itself stands.

⚠ **Falsifier for this decision:** a merge whose command text contains `gh pr merge` and does not trigger a rebuild,
or an item merged across a declared-kind conflict.
