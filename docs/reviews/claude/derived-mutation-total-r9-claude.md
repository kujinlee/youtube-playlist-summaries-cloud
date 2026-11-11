# Round 9 — `derived-mutation-total` (PR #455, backlog #359) — Claude adversarial half — CONVERGED (no BLOCKER; 2 FILE)

Reviewed: head `3bdff458`, the WHOLE PR (`git diff origin/master...HEAD`) plus the r8 delta (`git diff 256f0844..HEAD`).
Route: DEFER (decision-log row 159). Anything below that is not a BLOCKER is FILED, not folded.

```yaml
round: 9
subject: derived-mutation-total
half: claude
findings:
  - {id: C1, label: FILE, severity: Medium, aim: goal, fix_induced: false, component: pin-layout}
  - {id: C2, label: FILE, severity: Low, aim: doc, fix_induced: false, component: sibling-import}
verdict: CONVERGED
```

## Gates run, in the foreground, at `3bdff458`

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | **256/256** passed (2.5 s) |
| `python3 scripts/check-plan-code.py --self-test` | **281/281** passed (10.3 s) |
| `python3 scripts/check-plan-code.py --mutate . --only scripts/check-merge-ready.py` | **97 of 97 killed, 97 attributed**, 0 survivors (4 m 06 s). This is a diagnostic slice, not the full sweep |
| `python3 scripts/check-selftest-counts.py` | 72 scripts, every declared count verified (`256`, `281` match the docstrings) |
| `python3 scripts/check-docs.py` | OK |

## 1. The original goal (backlog #359)

- **The literal is gone.** `declared_total()` (`scripts/check-plan-code.py`, `return sum(EXPECTED_MUTATIONS[target] for target in EXPECTED_MUTATIONS)`)
  replaces master's `case("the declared counts are the real ones", sum(EXPECTED_MUTATIONS.values()), 2980)`. The only
  `2980` left under `scripts/` is the mutation entry that re-types it (`scripts/mutations/check-plan-code.json`, "the
  mutation total is typed again"). That is a mutation the harness applies, not a reader.
- **No reader of the old literal remains.** Master's `PIN_TOTAL` regex and its `declared mutation total drops` HOLD
  are retired in `check-merge-ready.py`, with a comment saying so at `hold_reasons`. `git grep` for `declared_total`
  outside `check-plan-code.py` finds only that comment. `typed_total_sites` refuses a re-typed total in any spelling it
  cases.
- **Merge cascades: they end for most file pairs, not all of them. This is C1.** I simulated it in a scratch clone of
  the worktree. Each branch appended one entry to a manifest and bumped that file's pin by one:

| Branch A bumps | Branch B bumps | Pin lines | `git merge` |
|---|---|---|---|
| `check-merge-ready.py` (`:2219`) | `check-anchors.py` (`:817`) | far apart | **clean** |
| `check-paid-caller-arrival.py` (`:2220`) | `check-vocabulary-collisions.py` (`:2221`) | **adjacent** | **CONFLICT** in `check-plan-code.py` |

## 2. The r8 delta

- **The empty-map refusal is reached only when the file is present.** `pins_at` returns `{}` when `git ls-tree`
  finds no file, before `_cross` and `_exact_pins` run. The new case "an ABSENT check-plan-code.py at both revisions
  still pins {}: READY, rc=0" pins that path. `_exact_pins` raising `ValueError` lands in `_cross`'s `except
  BaseException`, so the result is `PinsUnreadable` and CANNOT RUN, rc 2. The F1 case passes, and the mutation that
  removes the refusal (`if not out:` changed to `if False:`) is killed by that case.
- **The self-test `_cross`.** `_base_pins` is now computed as `_cross(lambda: _rdr.pin_display(_real_src), ...)`
  inside the existing `try`. I agree with the r8 note that no case drives `_self_test()` itself with a hostile reader.
  That gap is not a blocker: a hostile working-tree reader makes the rest of the suite red anyway (see the probe in §3).
- **The three new cases.** Each one goes through the real `main()` / `_main`. The adjacent negative (the real reader
  still gives HOLD, rc 3) is the right control for the F1 case.

## 3. BLOCKER hunt

Each input below was run against a real falling pin. The scratch branch lowers `check-vocabulary-collisions.py` 5 -> 4
and deletes that manifest's last entry, so CI's own drift check stays consistent. I ran `pin_pair` and `hold_reasons`
from the real `check-merge-ready.py`, and `check-plan-code.py --self-test`. In the scratch clone the self-test is
**278/281 on the untouched base**: 3 `HARNESS_TREE` cases fail because the clone has no `node_modules/typescript`.
That baseline is environmental and identical on every row, so a row is "CI-green" when it stays at 278.

| Input | merge-ready verdict | `check-plan-code --self-test` | `check-merge-ready --self-test` (CI runs it via `check-selftest-counts`) | Blocker? |
|---|---|---|---|---|
| plain fall, real reader | **HOLD** "drops 5 -> 4" | 278 (green) | green | — correct |
| `def pin_display(src): return dict(EXPECTED_MUTATIONS)` appended (reader ignores its input) | **READY, `hold_reasons == []`** | 278 (green) | **RED, 10+ cases** ("a pin LOWERED in the display is HELD: got []", …) | no: CI red |
| a caching `pin_display` that returns its first answer forever | READY | **267/281, red** | red | no: CI red |
| `pin_display` returns `{}` (r8 F1) | CANNOT RUN, rc 2 | red | — | no |
| `EXPECTED_MUTATIONS` renamed / turned into a `json.load` / a value that is not an int literal | CANNOT RUN (`PinDisplayError` at base or head) | — | — | no (fails closed) |
| a pin key respelled (`"scripts/x.py "`, prefix dropped), or `check-plan-code.py` moved | HOLD, "is removed" | — | — | no (a false HOLD, still closed) |

Master's `check-merge-ready.py` gives the src-ignoring reader **HOLD** ("drops 5 -> 4"), because it read pins from diff
text with its own regex. So on that input this PR changes the verdict from HOLD to READY. CI still refuses the PR,
which is why it is not a BLOCKER. It does make the docstring bound inaccurate; that is C2.

**No ordinary edit gives READY on a fall that CI also misses.** Only a reader built to target one specific key, which
leaves every synthetic-source case and the `_hit` vocabulary case intact, gets past both suites. That edit is
deliberate, and it falls inside the F4 bound the split pre-committed to.

## 4. HOLD triage

I ran `failure_path_removals(git diff origin/master...HEAD)`. It returns **the same 6 lines**: 5 in `check-merge-ready.py`
and 1 in `check-plan-code.py`. `gate_invocation_removals` and `scope_exits` are both empty. Each of the 6 is a
**FALSE HOLD**: a rewrite whose replacement is in the head.

| Removed (master) | Replacement (head) |
|---|---|
| `code, line = 2, (f"CANNOT RUN — could not read the branch's diff ({exc…` | `:1292`, the same CANNOT RUN, now "…diff or its mutation pins" |
| `[r.split(":")[0] for r in hold_reasons([G], _398, None, None, True)],` | `:1623`, the same call with `pins=({}, {})` |
| `hold_reasons(["worker/run.ts"], "", "f00d", "f00d", False), [])` | `:1626`, the same call with `pins=({}, {})` |
| `has(H([PC], DF(PC, '-    "scripts/a.py": 30,')), "…(30) is removed"), True)` | `:1988`, `pin_falls({"scripts/a.py": 30}, {})`, same expectation |
| `has(H([PC], DF(PC, '-…b.py": 12,', '+…c.py": 12,')), "…(12) is removed"), True)` | `:1990`, `pin_falls({"scripts/b.py": 12}, {"scripts/c.py": 12})` |
| `_evT.files["scripts/thing.py"]["tail"].strip(), "[FAIL] the value is one")` | `check-plan-code.py:4407`, `.get(…, {}).get("tail", "")`. A missing key now yields `""`, which still fails the equality, so the case is not weaker |

## 5. Doc accuracy

- The declared counts (`# 256 cases`, `# 281 cases`) match the measured counts. `check-selftest-counts` verifies both.
- `pin_display`'s docstring (exactly one module-level assignment, str-literal keys, int-literal values, no duplicates)
  matches the code.
- `_exact_pins`'s new sentence ("NOT EMPTY: a present file with no pins is unreadable") matches the code, and so does
  its comment that the caller reaches it only when the file exists.
- **C2:** the phrase "exactly as master trusts it" (`check-merge-ready.py:509`, `:969`, `check-plan-code.py:2868`) is
  not accurate. Details below.
- **C1:** the dashboard entry says "Two pull requests still conflict when they change the same file's count, because
  that conflict is real". That implies PRs on different files do not conflict, and the adjacent-pin row in §1 shows
  they can.

## Findings

### C1 — FILE — Medium — PRs bumping ADJACENT pins still conflict, so the cascade is narrowed, not ended

- **Where:** `scripts/check-plan-code.py`, the `EXPECTED_MUTATIONS` display, e.g. `:2219`–`:2221`. Also the dashboard
  entry's claim in `docs/dashboard-entries.md`.
- **Input:** branch A bumps `"scripts/check-paid-caller-arrival.py"` 6 -> 7 and appends one entry to its manifest.
  Branch B bumps `"scripts/check-vocabulary-collisions.py"` 5 -> 6 and appends to its manifest. `git merge`:
  `CONFLICT (content): Merge conflict in scripts/check-plan-code.py`. git treats two changed lines with no unchanged
  line between them as one conflicting region.
- **Measured:** 81 pins, **14 adjacent pairs**. The layout is identical on master.
- **Fix-induced?** No. It is structural: the PR removed the one line every PR touched and left 81 lines, some of which
  touch each other.
- **Proposed fix:** keep one unchanged line between every pair of pins. Either put each pin's existing rationale
  comment above it, or add a blank line, and have `pin_display`'s case assert the spacing. Re-measure with the same
  two-branch simulation; the falsifier is a clean merge for every adjacent pair. Correct the dashboard sentence in the
  same change.
- **Proposed backlog row:** *"Adjacent `EXPECTED_MUTATIONS` pins still conflict on merge: 14 of 80 neighbouring pairs
  share no unchanged line, so two PRs adding mutations to different files can still collide (backlog #359 residue)"*

### C2 — FILE — Low — the bound "a wrong but well-typed answer is trusted, exactly as master trusts it" is not what master did

- **Where:** `scripts/check-merge-ready.py:509` (`_cross` docstring), `:969` (the pin-reading block comment),
  `scripts/check-plan-code.py:2868`.
- **Input:** append `def pin_display(src):\n    return dict(EXPECTED_MUTATIONS)\n` to `check-plan-code.py` on a branch
  that lowers a pin 5 -> 4 together with its manifest entry. This PR's `hold_reasons` returns `[]` (READY). Master's
  `check-merge-ready.py` on the same diff returns `['loosens a gate: the mutation pin for
  scripts/check-vocabulary-collisions.py drops 5 -> 4']`.
- **What is wrong:** master read pins with merge-ready's own `PIN_LINE` regex over the diff. It trusted no code in
  `check-plan-code.py`. This PR moves the reader into `check-plan-code.py`, which every mutation-adding PR edits, and
  the reader comes from the HEAD's working tree, so the PR's own reader judges that PR. The trust surface grows from one
  file to two.
- **Why it is not a BLOCKER:** the input above turns `check-merge-ready --self-test` red. CI runs that suite through
  `check-selftest-counts`. Getting past CI needs a reader that targets one key on purpose, and that is the pre-committed
  F4 bound.
- **Fix-induced?** No. It comes from the r3 design (import the reader), not from the r8 fold.
- **Proposed fix:** reword the three sites to say "master read the pins with this script's own regex; this extends the
  trust to `check-plan-code.py`, whose `pin_display` the same PR can edit". Optionally, read the pins with the MERGE
  BASE's `pin_display` (`git show <mb>:scripts/check-plan-code.py`), falling back to the working tree when the base
  predates `pin_display`, so a PR cannot change the reader that judges it.
- **Proposed backlog row:** *"check-merge-ready judges a PR's pins with that PR's own `pin_display`; the bound says
  'as master trusts it', but master read pins with its own regex — reword, or read with the merge base's reader"*

## Verdict

**CONVERGED.** There is no BLOCKER: no ordinary edit gives READY on a coverage fall that CI also misses. C1 and C2 are
FILE under the DEFER route.
