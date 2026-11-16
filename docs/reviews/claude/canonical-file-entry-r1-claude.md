Reviewed head: d3430eb1ef6e705e5431006ba68796ae89d667b1

# canonical-file-entry (backlog #658) — round 1 — Claude half

Reviewed range: `84e53b9b..d3430eb1` (`scripts/check-canonical-source.py`,
`scripts/mutations/check-canonical-source.json`, `scripts/mutations/expected_mutations.py`,
`docs/backlog.md`, `docs/dashboard-entries.md`). Mandate: refute.

Baseline at head: `python3 scripts/check-canonical-source.py --self-test` -> `33/33 passed`, rc 0
(rc read from an un-piped run).

Mutations were applied to a copy: a scratchpad directory whose entries are symlinks to the worktree,
except a real, edited `scripts/check-canonical-source.py`, so `ROOT` (the script's parent's parent)
resolves to the copy and `HARNESS_TREE` is read from the real `check-plan-code.py`. No file in the
worktree was written.

## What I tried to break and could not

- **All 15 manifest entries, applied by hand.** Every anchor occurs exactly once in the file, and each
  mutation turns its named case red (rc 1, 32/33). The three new ones:
  - #12 equality -> `c.startswith(tuple(STAGEABLE_FILES))`: the `_spellings` case goes red because
    `.claude/settings.json.bak` and `.claude/settings.json/foo` drop out of the refused set.
  - #13 the exact-file arm removed: the same case goes red because `.claude/settings.json` is now refused.
  - #14 the union reduced to `STAGEABLE_PREFIXES`: the identity case goes red (`got` lacks
    `.claude/settings.json`).
  The two re-bound anchors (#8 `not staged`, #9 the tuple closing after `.githooks/`) still turn their
  named cases red.
- **The identity case when an entry moves or is dropped** (each variant was run on the copy):
  - entry moved from `STAGEABLE_FILES` into `STAGEABLE_PREFIXES`: the identity case stays green, as the
    comment at `check-canonical-source.py:659-661` says. The `_spellings` case goes red because `.bak`
    and `/foo` count as staged, so the regression is caught.
  - entry dropped from `STAGEABLE_FILES`: the identity case and the `_spellings` case both go red.
  - entry in BOTH sets: the identity case goes red because the sorted union holds a duplicate, and the
    `_spellings` case goes red too.
  - a directory entry moved into `STAGEABLE_FILES` was not run. By reading: the union is unchanged, but
    `scripts/x.py` would be refused, so the `_spellings` case's must-accept list would go red.
- **Is the identity case red for the right reason?** It compares sorted lists, so a duplicate counts
  against it. It classifies `HARNESS_TREE` entries by `is_file()` on disk, not by which set holds them.
  That is pre-existing (#651) and correct here, because `.claude/settings.json` is tracked.

## Findings

| # | Severity | Where | Input -> wrong output |
|---|---|---|---|
| 1 | MINOR (fix-induced claim) | `scripts/check-canonical-source.py:288-290`, `docs/dashboard-entries.md` (the 11-15 tech note: "matching `check-plan-code.py`'s `_staged_root`"), `docs/backlog.md` row 658 ("`_staged_root` does match a file entry exactly") | cite `.claude/settings.json/foo` -> `_staged_root(..., HARNESS_TREE)` returns `.claude/settings.json` (STAGED), and `unstageable_cites` REFUSES it. The two copies of the rule still disagree on a spelling this PR's own test names |
| 2 | NIT | `scripts/mutations/expected_mutations.py:1625` | says "One re-bound", but the diff re-binds TWO anchors (#8 and #9). The backlog row and the dashboard entry correctly say two |
| 3 | NIT | `check-canonical-source.py:280` ("THE PREFIXES `HARNESS_TREE` STAGES"), `:652` and the case name at `:662` ("STAGEABLE_PREFIXES is exactly HARNESS_TREE") | the case now compares the UNION. The name and comment describe only the tuple. Renaming the case means changing four `expect` strings in the manifest |
| 4 | INFO (pre-existing, not from this diff) | `check-canonical-source.py:226-228` | the prose list of what `HARNESS_TREE` stages omits `.githooks` and `.claude/settings.json` |

### Finding 1 — detail

`scripts/check-plan-code.py:625-629`:

```python
def _staged_root(path: str, roots) -> "str | None":
    under = [r for r in roots if path.startswith(r + "/")]
    under += [r for r in roots if path == r]   # a FILE entry is its own root
```

The `startswith(r + "/")` arm runs for EVERY root, including the file entry. So `_staged_root` matches
`.claude/settings.json` as "equal OR a path beneath it", which is not exact. I ran both rules over the
same cites:

```
'.claude/settings.json'      _staged_root=True  canonical-staged=True
'.claude/settings.json.bak'  _staged_root=False canonical-staged=False
'.claude/settings.json/foo'  _staged_root=True  canonical-staged=False   DIFFER
```

The fix makes `check-canonical-source.py` correct: it is the stricter copy, and the stricter direction
is the safe one. No harm follows in practice, because `.claude/settings.json/foo` cannot exist while
`settings.json` is a file. But the new comment ("`_staged_root` matches a file entry exactly; this is
that rule's copy") and the dashboard and backlog wording repeat the premise that is false. That premise
was the stated reason the two copies "disagree" and are now aligned.

**Fix:** pick one.
- (a) Correct the comment, the dashboard note and the backlog row: canonical is deliberately STRICTER
  than `_staged_root` on a path beneath a file entry. No code change.
- (b) Restrict `_staged_root`'s prefix arm to directory roots. That is a change to the harness and
  selects the WHOLE manifest, so (a) is the proportionate one.

Other divergences between the two copies (bare `scripts`, `.githooks`, `docs/../CONTEXT.md`) exist, but
they come from different input domains and are not from this diff. `_staged_root` takes paths that
`git diff` has already normalised, and `unstageable_cites` refuses `..` lexically on purpose. I list them
for completeness only. They are not findings.

## Verdict reasoning

The behaviour is correct. Every new and re-bound mutation is load-bearing, and the identity and
`_spellings` cases together catch every move, drop and duplicate I tried. Finding 1 is a false claim
that this diff introduced in three places, and it is the claim that justifies the change. Correcting it
costs one fold.

VERDICT: NOT CONVERGED
