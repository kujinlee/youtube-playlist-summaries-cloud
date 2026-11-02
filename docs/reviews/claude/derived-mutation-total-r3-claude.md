# Round 3 — `derived-mutation-total` (PR #455, backlog #359) — Claude half — NOT CONVERGED

Reviewed: `git diff bf7782a8..e777d546` (branch `derived-mutation-total`, merge of master `e116574f` included).
Mandate: REFUTE *"any change whose effective pins, as the harness sees them, fall or vanish is HELD;
check-merge-ready never fails open; nothing that master's literal total caught now slips through."*
Every run below was made on `git archive` scratch copies under the session scratchpad. Nothing was written to the
worktree.

## Gates run (foreground, scratch copy of e777d546, node_modules symlinked)

| Check | Result |
|---|---|
| `python3 scripts/check-merge-ready.py --self-test` | **230/230 passed**, 3.7s |
| `python3 scripts/check-plan-code.py --self-test` | **265/265 passed**, 6.5s |
| Full `--mutate` | not run (CI's, per the brief) |

## Findings

### F1 — HIGH — a pin lowered only when the process is NOT `--print-pins` (or only under `CI=true`) is READY; master went red on both

- **Location:** `scripts/check-merge-ready.py:895` (`effective_pins`) and `:859-862` (the stated BOUNDS);
  `scripts/check-plan-code.py:6913` (`--print-pins`).
- **Fix-induced:** **yes.** r1's `pin_shape_problems` refused this write in CI. r2 deleted it, and nothing in the same
  process as the harness replaced it.

**Input.** Add two lines after the `EXPECTED_MUTATIONS` display in the head's `check-plan-code.py`, and delete the
last 5 entries of `scripts/mutations/check-merge-ready.json`:

```python
if "--print-pins" not in sys.argv:          # variant: if os.environ.get("CI") == "true":
    EXPECTED_MUTATIONS["scripts/check-merge-ready.py"] -= 5
```

**Measured, in a real git repository** (base = e777d546's `scripts/`, head = the edit above). The production
`gather` + `pin_pair` + `hold_reasons` were driven by a scratch driver, `r3drv/argv.py` and `r3drv/full.py`:

| Observer | argv variant | `CI` env variant |
|---|---|---|
| `hold_reasons(..., pins=pin_pair(...))` | **`[]`** (READY) | **`[]`** (READY) |
| `--print-pins` (what check-merge-ready reads) | 87 | 87 (local, no `CI`) |
| the value the `--mutate` harness holds | 82 | 82 (under `CI=true`) |
| head `--self-test`, local | **265/265** | 264/265 (only the local run sees the drop) |
| head `--self-test`, `CI=true` | **265/265** | **265/265** |
| CI `--mutate` `pin_drift` (82 pinned vs 82 on disk) | green | green |

**Master caught both.** I applied the same edit to `origin/master`'s tree, and its self-test went red under `CI=true`:
`[FAIL] the declared counts are the real ones: got 2975 want 2980` (247/249). An input built to dodge master
(`if "--self-test" not in sys.argv:`) went red too, on the other witness:
`[FAIL] ...the entry count they yield is the pinned sum ... got 2975 want 2980` (248/249). Master put its two
witnesses **in one process**: the pins against a HELD literal, and the pins against the manifests on disk. A value
conditioned on how that process was started could satisfy one of them, never both.

The redesign splits the witnesses across **two invocations**:
- pins against the base, in a local `--print-pins` subprocess;
- pins against the disk, in CI's `--mutate` and `--self-test`.

The design assumes the module evaluates to the same dict in both. Nothing checks that assumption, and module-level
code can read `sys.argv`, `os.environ`, `sys.flags.isolated` (the probe runs `-I`, CI does not) and
`sys.version_info` (the probe runs the local interpreter, CI pins its own).

**The stated bound does not cover it.** `:862` says only *"a write made only on the `--mutate` path, after
`--print-pins` has returned, is not seen."* This write happens at import, before `--print-pins` has run.

**Calibration.** This is an adversarial input aimed at the checker, not an ordinary edit. That is the same character
as r2's default-argument, decorator and shadowed-`dict` inputs, which were rated High. Master could also be beaten by
a checker-aware edit, but that edit had to rewrite its two self-test cases, which is visible checker code. This one is
two lines of module-level code beside the data.

**Recommended fix (structural, and it deletes machinery).** Tie the effective dict to the DISPLAY inside the
consumer's own process. Then compare the DISPLAYS as data.
1. In `check-plan-code.main`'s `--mutate` path, before `mutate_delivered`, assert
   `ast.literal_eval(<the one module-level EXPECTED_MUTATIONS display>) == EXPECTED_MUTATIONS`. If they differ, the
   result is CANNOT RUN or FAIL. Put the assertion in `main`, not in `mutate_delivered`: the self-test rewrites the
   pins around `mutate_delivered` legitimately. Assert the same at the top of `--self-test`.
2. `check-merge-ready` reads the display at the merge base and at HEAD with `ast` plus `literal_eval`, and needs no
   execution. That removes the subprocess, the tar, the timeout and the base-only legacy fallback; a base that
   predates the flag is no longer a case. Require exactly one display; anything else is CANNOT RUN.
   `literal_eval` keeps the LAST duplicate key as Python does, and a string literal is outside the display node, so
   r1's and r2's inputs are still held at their values.
3. One owner for "find the display": both scripts call the same function.

**Feasibility, measured.** On e777d546 the display equals the effective dict under the harness's own argv
(`--mutate .`) and `CI=true`: `{}` differences. On the argv attack, the env attack and the master-dodging attack, the
same comparison in the harness's invocation gives `{'scripts/check-merge-ready.py': (87, 82)}`,
`(87, 82)` and `(85, 80)`. Each is red where the harness runs.

**What is left after that fix.** A write made inside the harness's own functions after the assertion (for example in
`mutate_delivered`) is a checker edit. That is the same class as rewriting master's cases. State it as the bound.

**Alternative, if the fold keeps `--print-pins`:** amend `:859-862` to say that a pin conditioned on the invocation
(argv, environment, interpreter, isolation flags) is not seen, and retract the claim that nothing master caught slips
through, because it is false.

### F2 — LOW — the docstring of `effective_pins` says a tree with no `PINS_SCRIPT` pins `{}`, but a tree with no `scripts/` is CANNOT RUN

- **Location:** `scripts/check-merge-ready.py:895-900`.
- **Fix-induced:** yes (new code).
- **Input:** the merge base has no `scripts/` directory. `git archive <rev> scripts` exits 128 (pathspec), which
  becomes `PinsUnreadable`, and `main()` returns rc=2.

This fails CLOSED, so it is not a defect in the verdict, only in the sentence. It cannot happen in this repository.
Fix by rewording the docstring, or leave it.

## The fail-open sweep, through the real `main()` (item 3)

Driver: `r3drv/fo.py`. `gh` and `git` are faked READY, the interpreter is real, and the `main()` wiring is the
production code.

| Input | rc | Verdict |
|---|---|---|
| control, unchanged | 0 | READY (correct) |
| `--print-pins` times out (`TimeoutExpired`) | 2 | CANNOT RUN ✓ |
| empty stdout, rc 0 | 2 | CANNOT RUN ✓ |
| extra key in head (not a fall) | 0 | READY (correct) |
| non-int `5.0` / bool `True` / a JSON list | 2 / 2 / 2 | CANNOT RUN ✓ |
| warning line printed before the JSON | 2 | CANNOT RUN ✓ |
| prints JSON, then exits 1 | 2 | CANNOT RUN ✓ |
| base has no `check-plan-code.py` (new repo) | 0 | READY: base `{}`, nothing can fall (correct) |
| base has no `scripts/` at all | 2 | CANNOT RUN (see F2) |
| `git merge-base` fails (shallow or unrelated history) | 2 | CANNOT RUN ✓ |
| head `git archive` fails | 2 | CANNOT RUN ✓ |
| big int `10**30` | 0 | READY (a rise, correct) |

**No path returns READY over an unread side.** The fail-open claim holds. Only F1 breaks the HOLD claim.

## Item 2 — the base fallback

- **HEAD cannot reach it.** `pin_pair` passes `legacy_ok=False` for `"HEAD"`, and the self-test case
  *"a HEAD without --print-pins is CANNOT RUN"* pins that.
- **The trigger text** `unrecognized arguments: --print-pins` is argparse's exact wording.
- **On the real master it IS the live path today.** Measured: the base `--print-pins` exited 2, the probe took over,
  and the result was base 81 keys / sum 2980 against head 81 keys / sum 2989, `falls []`.
- **The probe's import differs from the subprocess's** (`__name__ == "pins_probe"`, argv `['-c', path]`, `-I`). That
  only matters on the base, which is the reviewed side, and the probe disappears entirely under F1's fix.

## Item 4 — cost

`pin_pair` on the real worktree takes **0.72s** in all:

| Step | Time |
|---|---|
| `merge-base` | 0.01s |
| two `git archive` of `scripts/` | 0.06s each |
| head `--print-pins` | 0.12s |
| base `--print-pins` refused | 0.13s |
| base probe | 0.12s |

`check-merge-ready`'s own self-test takes 3.7s. Archiving `scripts/` is enough: `check-plan-code`'s only
non-stdlib import is `coverage_verdict` (in `scripts/`). Module level reads no file, environment variable or argv on
the current tree. `--print-pins` under `-I` with `CI=true` gives 81 keys / 2989, the same as without.

## Item 5 — the master merge `e116574f`

- `git diff e116574f^1 e116574f` holds master's 18 lines exactly: backlog, goal-threads, process-checklists, and a
  3-line dashboard entry.
- `--cc` on `docs/dashboard-entries.md` shows both 2026-10-31 entries kept, master's first. The one added blank line
  is a separator.
- No script file was touched by the merge.
- r2's later edit to the branch's entry correctly drops the stale *"held by `PIN_LINE`"* sentence. Its counts
  (merge-ready 85 → 87, plan-code 140 → 147) match master and HEAD: pins `85/140 → 87/147`, manifests `85/140 → 87/147`.

**The merge is correct.**

## Item 6 — the architecture-review question

**Test (review-method.md, *Can a redesign remove it?*).** Apply it to each class.

1. **The class that thrashed in r1 and r2 is REMOVED, not moved.** That class was proving a runtime value by
   enumerating source-text shapes (`PIN_LINE`, then `pin_shape_problems`'s deny-list). All seven of those inputs now
   go through a VALUE comparison and are held. The suite replays them, and I re-ran it: 230/230. The component
   `pin-shape` no longer exists. No finding this round lives in it.
2. **F1 is a sibling class the redesign introduced.** The value is read in one invocation and asserted to be the
   value in another. It passes the same test: a redesign removes it. F1's fix asserts display == effective inside the
   consumer's own process and compares the displays as data. That closes the invocation dimension, and it also
   deletes the subprocess and fallback machinery. It is a mechanism defect, not branch coverage.
3. **By the letter of the escalation ladder** (review-method.md, *Redesign or accretion*), a unit that still carries
   findings after a restructuring fold escalates REDESIGN → SPLIT. I flag that honestly rather than argue it away.
   - **Judgment:** F1's fix COMPLETES this round's redesign; it does not retry it. The idea is still "compare
     effective values". What changes is that the witness that ties them together moves to where they are consumed.
     It is one enumerable dimension with a measured fix, not an open deny-list.
   - **I do NOT judge a separate Phase 6 architecture review necessary.** The thrashing component was deleted, not
     patched, and the remaining defect has a concrete structural remedy whose feasibility is measured above.
   - **The observation that should trigger SPLIT:** if round 4 finds a further gap between the effective dict and the
     harness's dict after that fix, the redesign route is exhausted. Then the next step is SPLIT: ship the derived
     total with the HOLD's bound stated, and give the falling-pin witness its own subject.

## Verdict

**NOT CONVERGED.** One High (F1): it is fix-induced, it refutes the third clause of the claim with a measured READY
over a 5-mutation coverage drop, and master was red on the same input. One Low (F2). The fail-open clause holds
across 12 inputs. The merge is correct. Cost is 0.72s.
