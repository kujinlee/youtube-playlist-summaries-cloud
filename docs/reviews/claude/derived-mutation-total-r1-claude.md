# derived-mutation-total — round 1, Claude adversarial half

**Subject:** PR #455, branch `derived-mutation-total`, head `9fad9a10`, against `origin/master` (`3a1cc908`).
**Built on:** scratch copies made with `git archive` of the head and the base, with `node_modules` symlinked in. Nothing was written inside the worktree.
**Mandate:** refute the claim *"no guarantee is lost; every way coverage could shrink unnoticed before is still caught; no reader of the old literal remains."*

## Verdict: NOT CONVERGED

The first half of the claim is refuted. Two shrink routes pass both self-tests and `check-merge-ready`'s HOLD detection on the head. On the base, the same routes forced an edit to the typed literal, and `PIN_TOTAL` then HELD the PR. The other parts of the claim hold up:
- the retirements are real;
- the moved code is faithful;
- every anchor resolves;
- no live reader of the literal remains.

## Evidence run

| Check | Result |
|---|---|
| `python3 scripts/check-plan-code.py --self-test` (head) | `253/253 passed` (7.4s) |
| `python3 scripts/check-merge-ready.py --self-test` (head) | `209/209 self-test cases passed` |
| `load_manifests` + `anchor_problems` (the harness's own rule) over **all** manifests at head | 0 load problems, **0 anchor problems**, 2981 entries, `declared_total() == 2981`, `pin_drift == []` |
| Every `EXPECTED_MUTATIONS` key line at head matched against `PIN_LINE` (AST walk; key, value and line agree) | 81/81 keys match, 81 unique |
| Retired entry's anchor `if ot and nt and nt[0] < ot[0]:` | base 1 occurrence, head **0**. The subject is gone, not only its test |
| `PIN_TOTAL` symbol at head | 0 occurrences in `scripts/` |

## Shrink scenarios, run end to end

How each scenario was run, by the driver in the scratchpad (`scen.py` / `scen2.py`):
1. Reset to the committed copy.
2. Apply the edit and stage it.
3. Feed `git diff --cached -M` to the real `check-merge-ready.hold_reasons`.
4. Run both self-tests in full.

| # | Input | HOLD at head | plan-code self-test at head | Caught? |
|---|---|---|---|---|
| S0 | control: `check-merge-ready` pin 84→80 and 4 entries deleted | `pin … drops 84 -> 80` | 253/253 | ✅ HOLD |
| **S1** | 4 entries deleted, and a **duplicate key** `"scripts/check-merge-ready.py": 80,` appended at the end of the dict. The original `84` line is left untouched, and Python keeps the last value | **none** | **253/253** | ❌ **silent** |
| **S2** | 4 entries deleted, and a module-level `EXPECTED_MUTATIONS["scripts/check-merge-ready.py"] -= 4` placed after the dict | **none** | **253/253** | ❌ **silent** |
| S3 | `check-paid-caller-arrival.json` deleted together with its pin line | `pin … (6) is removed` | 252/253 | ✅ |
| S4 | multi-line pin edit, lowered: `"…": (\n 80),` | `pin … (84) is removed` | 253/253 | ✅ HOLD (conservative) |
| S5 | pin moved to the end of the dict and lowered | `drops 84 -> 80` | 253/253 | ✅ |
| S6 | target renamed: pin key, manifest `file` fields and the script, same count | `pin … (6) is removed` | 250/253 | ✅ |

**The base caught S1 and S2.** On the base, S2 reddens `the declared counts are the real ones: got 2976 want 2980`. The only way back to green is to type the literal down to 2976. After that edit, the base's `hold_reasons` returns `['loosens a gate: the declared mutation total drops 2980 -> 2976']` at 249/249. S1 behaves the same way, with both total cases red.

## Findings

### M1 — Medium — fix-induced. Two pin routes that `PIN_LINE` cannot see now shrink coverage with no HOLD and a green suite

`scripts/check-merge-ready.py:861-867` and `:868-870` (the retirement comment), `scripts/check-plan-code.py:6494-6501`.

Inputs: S1 and S2 above.

The retirement rests on *"the total can only fall when a pin falls, and a falling pin is held above"* (`check-merge-ready.py:868-870`). That is true only of the pins `PIN_LINE` can see. `PIN_LINE` is a text proxy over one line shape in one file's diff. The typed literal was a semantic observer: any net fall in the evaluated sum, by any route, had to pass through one line that `PIN_TOTAL` could read. With it gone, two routes are no longer seen:
- **a duplicate dict key.** This is also a plausible result of a botched merge resolution;
- **any write to `EXPECTED_MUTATIONS` outside the dict display**, for example an override, `-=`, `.update`, or moving the dict to another module.

Each of these lowers the effective pin with no `-` line that `PIN_LINE` matches. `pin_drift` stays green because the manifests were trimmed to match.

**Fix (restores the equivalence the comment assumes).** Add a source-structure case in `check-plan-code --self-test`, using `ast` over `__file__`. It should check that:
- `EXPECTED_MUTATIONS` is assigned **exactly once**, at module level, as a dict display;
- its keys are **unique** string literals and its values are int literals;
- every key's line matches `PIN_LINE`, imported from `check-merge-ready` and not restated;
- no other module-level statement stores into it.

Give that case two mutation entries: a duplicated key, and a second module-level store. A semantic alternative is for `check-merge-ready` to evaluate the old and new dict through `ast` from both blobs, but that is a larger change.

### L1 — Low — fix-induced. The source scan that refuses a typed total is shape-specific

`scripts/check-plan-code.py:6503-6505`.

The regex catches `case(…, declared_total(), N)` and `sum(EXPECTED_MUTATIONS.values()), N)`, confirmed: inserting the former reddens it. It does not catch `case("t", declared_total() == 2981, True)`, `assert declared_total() == N`, or `len(load_manifests(...)[0]), N`. In my run, inserting the `==` form failed only through the docstring case-count `[DRIFT]`, which goes away when the count is bumped.

This is a cost regression (conflicts come back), not a coverage one, hence Low. Either broaden the pattern to a numeric literal compared with `declared_total()` or `len(...entries)` in any form, or rename the case to say what it actually refuses. It also has no mutation entry.

### L2 — Low — fix-induced. The case "pins that match their manifests report nothing, not even a total" cannot go red on its own

`scripts/check-plan-code.py:6522-6523`.

I applied the natural mutations by hand:
- `if drift:` → `if True:` crashes the suite at `:4226` (`KeyError: 'scripts/thing.py'`, an earlier `mutate_delivered` case indexes a result that the extra line suppressed) before this case is reached;
- `if drift:` → `if counts:` crashes the same way.

The property is defended, because the suite goes red and the earlier `--mutate catches a mutation in the DELIVERED tree` reddens. But the harness attributes a kill by the named case, and this case never prints a `[FAIL]`. So my verdict: it is **not vacuous**, because placed earlier or with `:4226` made crash-proof it would redden. It **is redundant by ordering**, and a mutation entry naming it would be refused as unattributed.

Either:
- make `:4226` non-crashing (`.get(...)`), then add the `if drift:` → `if True:` entry naming this case; or
- delete the case and let the earlier cases own the property, saying so in the comment.

### L3 — Low — fix-induced. The new on-disk per-file case is indistinguishable from the total it replaced on any consistent tree

`scripts/check-plan-code.py:6567-6568`.

I mutated it back to a total-only comparison (`[] if len(_live_entries) == declared_total() else ['x']`). Result: **253/253 green.** That is inherent to a live-data case, because on a consistent tree both forms agree. The per-file direction is pinned only by the synthetic swap case at `:6517-6521`.

The comment *"It now compares every manifest with its own pin"* is true, but nothing would notice it reverting. This is informational. No action is needed beyond not counting it as a defended improvement.

### L4 — Low — fix-induced. The docstring's "the totals follow as the last line" is false when home-escape lines follow

`scripts/check-plan-code.py:2802-2804` against `:2870-2890`.

`mutate_delivered` appends home-escape and replacement-text findings to `drift` **after** `pin_drift` returns. Concrete input: one drifted pin plus one target that contains `os.environ["HOME"]` gives an `in all:` line that is not last. The behaviour is harmless. Either reword the docstring to "a total line follows the per-file lines" or append the escape findings first.

### L5 — Low — not fix-induced, but now stale. The narration above the self-test still speaks of "this case" and "this literal"

`scripts/check-plan-code.py` ~`:5550-6490`.

The long history block that preceded the retired case still says *"THIS CASE caught it"* (`:5589`) and *"This literal is the outside observer of the sum"* (`:5771`). It now sits above `every relevant root is a real HARNESS_TREE member`.

The PR added an "is retired" note at `:6543`, but that is **below** the block. The marker at `EXPECTED_MUTATIONS` (`:772-776`) covers only the dict's comments. Add one line at the top of the self-test narration block.

## What was checked and holds

- **The moved code is faithful.** The counts loop and the two drift loops in `manifest_counts`/`pin_drift` are character-identical to the removed block of `mutate_delivered`. The only addition is the `in all:` line, and no existing case asserts the exact drift list (253/253).
- **The new mutation entries are killed by the case they name.** `return 2980` reddens `the declared total is the sum…`. `sorted(...)[1:]` reddens `a drifted pin reports the DERIVED total…`. Both anchors resolve exactly once.
- **The retirements are real.** `check-merge-ready` pin 85→84: the retired entry's anchor no longer exists at head. Cases 211→209: the deleted loop iterated over two tuples, and the suite runs 209.
- **No live reader of the old literal remains.** I searched `scripts/`, `.claude/hooks`, `.claude/commands`, `.agents`, `.github` and the process docs. The only hits are historical review documents, a dashboard entry, and the docstring and comment text in this PR.
