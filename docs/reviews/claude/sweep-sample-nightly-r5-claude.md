Reviewed head: c1230d3bcc1431676d0b1af787dc2f049bb34db2

# Round 5 — `sweep-sample-nightly` (backlog #651, PR #593) — Claude half, over the merge delta

Scope: ONLY what merge commit `58ab89d8` (origin/master, PR #592, into the branch) brought that no round has seen —
`git diff f0ddab94 58ab89d8 -- scripts/`, and how it composes with master's side (`git diff 0340751d 58ab89d8 --
scripts/`). Head `c1230d3b` adds only a dashboard edit after the merge. Mandate: refute each of the delta's three
claims. Round 5 is past the cap (`docs/review-method.md` §0 Q4c): anything short of a BLOCKER is FILED, not fixed.

```yaml
round: 5
half: claude
findings:
  - {id: C5-1, severity: MINOR, component: canonical-source-stageability, fix_induced: false}
```

## Gates run (this worktree, head c1230d3b)

| Check | Result |
|---|---|
| `python3 scripts/check-canonical-source.py --self-test` | rc=0, `33/33 passed` |
| `python3 scripts/check-canonical-source.py` | rc=0, `canonical sources OK — 3 mechanism(s) described once each (handoff-path, corpus-search, marketplace-inventory)` |
| `python3 scripts/session-state.py --self-test` | rc=0, `157/157 self-test cases passed` (docstring `:64` says 157 — agrees) |
| `python3 scripts/check-plan-code.py --self-test` | rc=0, `506/506 passed` |
| All-manifest recount (own script: every `scripts/mutations/*.json` entry counted per `file`, every `edits[i][0]` counted in its file) | 5271 entries; 0 pin mismatches against `EXPECTED_MUTATIONS`; 0 anchors present ≠ 1 time |
| 3-way recount of `session-state.json` by entry name (base `9cba3f50` = merge-base, ours `f0ddab94`, theirs `0340751d`) | base 119, ours 140, theirs 127, head 148; 0 missing, 0 extra, 0 duplicate names, 0 entries changed on both sides, 0 head entries differing from the side that changed them |
| The same for `goal-tree.json` | base 395, ours 395, theirs 438, head 438; 0 missing, 0 extra, 0 content diffs |

The session-state mutation sweep was NOT run (29 min; PR CI runs it), so "every new entry dies" is not checked here.

## Claim 1 — REFUTED as worded, harmless in effect: C5-1

### C5-1 — MINOR — `fix_induced: false` — component `canonical-source-stageability`

**A bare FILE entry in a PREFIX tuple accepts every path that merely starts with it.** The consumer is
`scripts/check-canonical-source.py:339`:

```python
if ".." in parts or not c.startswith(STAGEABLE_PREFIXES):
```

`str.startswith` with the new entry `".claude/settings.json"` (`:291`) is a prefix test, so the claim "a cite of
exactly `.claude/settings.json` counts as staged; `.claude/settings.jsonX` and `.claude/settings.json/foo` do NOT"
is false for the second half. Run against `unstageable_cites` on this head:

```
'.claude/settings.json'        []                               (stageable — correct)
'.claude/settings.jsonX'       []                               (stageable — WRONG)
'.claude/settings.json/foo'    []                               (stageable — WRONG)
'.claude/settings.json.bak'    []                               (stageable — WRONG)
'.claude/settings.local.json'  ['.claude/settings.local.json']  (refused — correct)
```

The comment at `:288-290` ("a cite must name it whole to count as staged") states the rule the code does not
implement. The harness's own rule is exact for a file entry — `check-plan-code._staged_root` (`scripts/check-plan-code.py:625-629`)
tests `path.startswith(r + "/")` OR `path == r` — so the duplicate now disagrees with the copy its identity case
claims it equals: the identity case (`:657-660`) compares the TUPLE CONTENTS, not the predicate, and the predicate
fixture (`_spellings`, `:670-690`) has no case naming the file entry or a sibling of it, so no case and no
mutation can see the difference.

**Why MINOR, not a BLOCKER.** A wrong "stageable" verdict here cannot let a real defect through silently.
`audit()` requires a declared citing site to EXIST, `.claude/settings.json/foo` cannot exist (the parent is a
file), and a tracked `.claude/settings.json.bak` declared as a citing site would be absent from the staged tree,
so `check-canonical-source`'s CONTROL would go red there and the harness would refuse the shard loudly
("NOT MEASURED") — the failure this predicate exists to pre-empt, but a loud one, not a false green. No such cite
is declared today (the live run lists three canons, none citing anything under `.claude/` but `hooks/`).

**Fix (to file):** split the tuple — keep directory prefixes in `STAGEABLE_PREFIXES` and put file entries in a
`STAGEABLE_FILES` set tested by equality (`c in STAGEABLE_FILES or c.startswith(STAGEABLE_PREFIXES)`), or mirror
`_staged_root` exactly; have the identity case compare the union; and add to `_spellings` one must-refuse
`.claude/settings.json.bak` and one must-accept `.claude/settings.json`, so a mutation from `==` back to
`startswith` dies.

## Claim 2 — HOLDS

`scripts/mutations/check-canonical-source.json`: the re-bound entry's anchor now ends at `".githooks/",\n`, present
exactly once; the new entry's anchor (`e.value if (ROOT / e.value).is_file() else …`) present exactly once, and its
expectation names the identity case, which is the only case that reads that expression. Pin 12 = 12 entries. The
identity case is host-independent in the places it runs: `.claude/settings.json` is tracked (`git ls-files`), so it
exists in a CI checkout and in the staged tree (`stage_tree` copies a file entry with `copy2`, `:999`).

## Claim 3 — HOLDS

No entry lost, duplicated, or left with an anchor that is absent or ambiguous (table above). Every head entry equals
the side that changed it relative to the merge-base, and no entry was changed on both sides, so the by-name merge
had no conflicts to resolve. `scripts/session-state.py` passes its own suite at 157/157, matching its docstring.

## Thrashing

None. C5-1 is not fix-induced: it is in code the merge commit added to satisfy the identity case after master
added the FILE entry to `HARNESS_TREE`, and it is the first finding in this component.

VERDICT: CONVERGED
