# work-lines — round 3 — Claude half

Reviewed range: `2a86990b..34aceb4f` (the fold of round 2; the feature is `d9f27342..34aceb4f`).

Everything below was executed against copies under the session scratchpad (`.../scratchpad/r3/`),
never against the repo's `.claude/`. Baselines: `gen-work-lines.py --self-test` 36/36,
`begin-plan.py --self-test` 78/78 (Python 3.14.4).

## What I tried to break and could not

- **`build_forest` cycle cut (focus a, mandate 1).** 200,000 random parent graphs (1–7 nodes;
  parents drawn from {None, an absent slug, any node including itself}; random `touched`). For
  each one I checked: every plan placed exactly once; every node that was not cut keeps its REAL
  parent (orphan parents and `None` become roots); every cycle gets exactly ONE cut, at
  `min(cycle)`; no edge that is not on a cycle is ever cut; only cut nodes carry `cycle`.
  Result: `trials 200000 bad 0`. The comment's claim holds: a placed node's children are always
  placed, so an unplaced node's parent is unplaced and present, and with one parent per node the
  walk must end on exactly one cycle. `by_slug[n]["parent"]` cannot be `None` or absent inside
  the walk (both made the node a root in the first loop). Several cycles sharing tails cannot
  exist: a tail has one parent, so it hangs below exactly one cycle, and `place(node)` after the
  cut places that cycle and every tail below it, still attached. Duplicate slugs collapse in
  `by_slug` but are unreachable from `read_plans` (stems of one directory).
- **The `place()` visited-skip (mandate 6).** Replaced `continue` with
  `raise AssertionError("visited-skip fired")`: 36/36 still pass, and the 200k sweep never
  reaches it. It masks nothing in correct code.
- **The three shipped mutation entries (mandate 5).** Each applied to a copy reddens its named
  case and only that case (`walk[0]` → 35/36, the cycle-ON-the-cycle case; drop `.md` → 77/78,
  the non-.md case; hand-listed separators → 77/78, the vertical-tab case). ⚠ The brief says
  **8** new entries; this range adds **3** (`gen-work-lines.json` 12→13, `begin-plan.json`
  22→24, declared sum 1725→1728, counts match the files).
- **`_derive_parent` (focus b, mandate 3).** Executed, each with a fresh `begin`:
  `real.MD` (on case-insensitive APFS, where the file IS `real.md`), `real.md.bak`, a directory
  `dir.md`, a `.md` symlink to a `.txt` → all "no parent recorded" with the warning (fail-safe).
  `../plans/real.md`, an absolute path, trailing whitespace (`real.md `) → `parent: real`.
  No programmatic caller of `begin-plan.py` reads its stderr (grep over `.claude/hooks`,
  `scripts`, settings).
- **Refusal ordering (mandate 4).** The `--serving` check (begin-plan.py:395) precedes
  `PLAN_DIR.mkdir` and every write; refused values leave no file.
- **Re-arm lineage (mandate 2).** A hand file with two `parent:` markers → the kept parent is
  the first (`<!-- parent: first -->`), and the generator's `PARENT` is the identical pattern
  with the same `.search`, so writer and reader agree. A pre-field (markerless) plan stays
  markerless on re-arm — honest under the docstring's three-state rule. An explicit new
  `--serving` replaces the old one; that is an explicit act.

## Findings

### 1. Minor — the r2 fix RE-ADMITS a trailing newline, and whitespace-only objectives render as a quoted blank
`scripts/begin-plan.py:395`

`len(serving.splitlines()) > 1` is not "contains a line boundary": a value ENDING in a separator
splits to one element. Executed (temp copy, `cmd_begin(..., serving=s)`):

```
'ask\x0b' rc 0 serving read: 'ask'   head: '...<!-- serving: ask\x0b -->...'
'ask\n'   rc 0 serving read: 'ask'   head: '...<!-- serving: ask\n -->...'
'\n'      rc 0 serving read: ' '     head: '...<!-- serving: \n -->...'
'   '     rc 0 serving read: ' '
```

- `"ask\n"` and `"\n"` were **refused by the r1 code** (`git show 2a86990b:scripts/begin-plan.py:390`
  — `"\n" in serving`). The r2 fold regressed them: the marker is now written across TWO physical
  lines, contradicting the refusal's own sentence ("must be ONE line"). The readers happen to
  recover only because `\s*` before `-->` crosses the newline — a property nobody asserts.
- `"\n"` / `"   "` parse as `' '` (the reader's `(.+?)` needs one char), which is truthy, so the
  page renders the objective as an empty quotation instead of "no objective was stated":
  `['<p class="serving">“ ”</p>']` (executed through `parse_plan` → `render`).
- Consequence today is cosmetic; no step is smuggled (`count_steps` → `(0, 1)` for all of them).

**Fix:** refuse when `serving.splitlines() != [serving]` (catches trailing separators; `""` gives
`[]` and is handled below), and treat `serving.strip() == ""` as an explicit refusal (see 2).
Add `"ask\n"` and `"\n"` to the refused-values loop.

### 2. Minor — `--serving ""` on a re-arm silently erases the human's original words
`scripts/begin-plan.py:415–418` (from the r1 fold, not r2)

Executed: `begin keep … --serving "the original ask"`, then `begin keep … --serving ""` →
the `serving:` line count in `keep.md` goes from 1 to **0**, rc 0, no message. `serving is None`
is false for `""`, so the old value is not kept, and `render_plan`'s `if serving:` writes nothing.
This is the one field the code says is never rewritten ("these are the human's own words, and
silently editing them is the one thing this field must not do"), and `--serving "$VAR"` with an
unset variable reaches it. Not caused by the r2 fold.

**Fix:** refuse an empty/whitespace-only `--serving` outright (same check as finding 1), so
"keep" vs "replace" are the only two outcomes.

### 3. Minor — the separator case pins ONE member of the class, so an instance fix survives it
`scripts/begin-plan.py:847–851`, mutation `begin-plan.json` "hand-lists separators again"

Mutant applied to a copy: `("\n" in serving or "\r" in serving or "\x0b" in serving or "-->" in serving)`
→ **78/78 pass**. Under that mutant, executed, seven other `str.splitlines` boundaries are
accepted and each produces a step that `parse_steps` (the banner/`--tick` reader) counts:

```
'\x0c' rc 0   '\x1c' rc 0   '\x1d' rc 0   '\x1e' rc 0   '\x85' rc 0   ' ' rc 0   ' ' rc 0
parse_steps titles for each: ['smuggled -->', 'One']
```

The shipped code is correct; the suite cannot tell it from the instance fix that the r2 fold's
own comment warns against. (Side observation, pre-existing: `count_steps` in
`check-plan-progress.py:102` uses `re.M`, whose `^` follows only `\n`, so the Stop guard counts
1 step where `parse_steps` counts 2 — two readers of one checkbox rule that disagree on these
inputs. Not caused by this fold.)

**Fix:** loop the case over every boundary, derived independently of the code under test, e.g.
`[c for c in map(chr, range(0x2030)) if len(("a"+c+"b").splitlines()) > 1]`.

### 4. Minor — "the alphabetically first member of that cycle" is untested; `cut = n` survives
`scripts/gen-work-lines.py:133`

Mutant `cut = n` (the first REPEATED node, i.e. wherever the walk entered the cycle) → **36/36
pass**. In every fixture the walk enters the cycle at its minimum. A fixture where it does not:
`y.parent=x, x.parent=z, z.parent=y, a.parent=z, b.parent=y` — the walk from `a` enters at `z`,
`min(cycle)=x`. Shipped code cuts `x` (executed: render shows `x ⛔ cycle`, 1 line). The mutant
cuts `z`: still a valid tree, but not the documented, deterministic choice. (`walk from max
unplaced` also survives and is an equivalent mutant — the cut is `min(cycle)` either way.)

**Fix:** add that 3-cycle fixture asserting the root is `x`.

### 5. Minor — one non-plan entry named `*.md` takes the whole page down (pre-existing, not from the fold)
`scripts/gen-work-lines.py:281–285`

Executed: a directory `.claude/plans/dir.md` →
`CANNOT RUN — dir.md could not be read: [Errno 21] Is a directory`, rc 2. A dangling `*.md`
symlink would do the same (UNVERIFIED, same `OSError` path). `begin-plan` treats the same entry
as "not a plan" (`is_file()`), so the two disagree about what a plan file is. Loud rather than
silent, so this is a judgement call, not a defect of the fold.

**Fix (optional):** `if not f.is_file(): continue` with a stated count of skipped entries, or keep
CANNOT RUN deliberately and say so in the docstring.

### 6. Minor — symlink identity differs between writer and reader
`scripts/begin-plan.py:366` vs `scripts/gen-work-lines.py:287`

`_derive_parent` names the RESOLVED target's stem; the generator names the UNRESOLVED file's
stem. Executed: armed `alias2.md -> real.md` → child records `parent: real` while the page also
shows `alias2` as its own plan; armed `linkmd.md -> b.txt` → no parent recorded, though the page
reads `linkmd` as a plan. Both fail toward "no claim" or toward an existing plan with identical
content, so nothing false is asserted. Informational.

**Fix (optional):** check `.md`/parent on the unresolved path (`(ROOT/prev)` normalised with
`os.path.normpath`, not `resolve()`), matching what `read_plans` sees.

## Is this thrashing or the prose floor?

| Finding | Introduced by the r2 fold? | Evidence |
|---|---|---|
| 1 trailing separator | **Yes** | r1 code (`2a86990b:390`) refused `"ask\n"`/`"\n"`; r2's `splitlines()` admits them |
| 2 empty `--serving` erases | No | the keep/replace branch is from the r1 fold (`2a86990b`) |
| 3 one-member separator case | **Yes** (its test) | the case and mutation entry were added in `34aceb4f` |
| 4 `cut = n` survives | **Yes** (its test) | the cycle walk and its fixture were added in `34aceb4f` |
| 5 `*.md` directory | No | `read_plans` predates both folds |
| 6 symlink identity | No | `resolve()` is from the r1 fold |

Round 2's two Majors were both caused by the r1 fold (the cycle cut it introduced; the PLAN_DIR
check it introduced, missing `.md`). Round 3 again has fix-caused findings in `begin-plan.py`
(1, 3) and `gen-work-lines.py` (4). So the **shape** of thrashing is present for two rounds
running. But the **character** changed: round 2's were Major behaviour defects (a wrong line
structure, a wrong parent); round 3's are a cosmetic regression and two test-strength gaps, with
the shipped behaviour verified correct over 200k graphs and every sentinel variant tried. My
read: **prose floor, not thrashing** — the fixes are converging in behaviour, and what remains is
the residue any new code carries. Not an argument to convene an architecture review.

VERDICT: CONVERGED
