# Claude adversarial review — banner guard inverse PLAN, round 1

**Subject:** `docs/superpowers/plans/2026-09-04-banner-guard-inverse.md` against
`docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v3, approved).
Spec design decisions are **not** re-litigated. The question is whether this plan implements them.

**Method — the plan was EXECUTED, not read.** Every code block in Tasks 1–7 was applied literally to
a reconstruction of `scripts/check-banner-armed.py` in a scratch repo
(`…/scratchpad/repo/scripts/check-banner-armed.py`) beside real copies of
`scripts/check-plan-progress.py` and `.claude/hooks/block-idle-stop.sh`. The suite was run, Task 6's
hook move was applied, and `--decide` was driven end-to-end against a fixture transcript. Both
Blocking findings below are measured outputs, not predictions. No repo file was modified.

Reconstruction result: **51/52 cases pass; F6 is the single red**, and it is red *after* Task 6, not
only before it.

---

## Blocking

### B1 — `steps` is undefined in `run_decide`, so the flagship WARN never reaches anyone. Measured.

**Claim.** Task 4's `run_decide` snippet passes `steps` as a keyword *argument*; Task 5's logging
block reads `steps` as a *local*. It is never bound. Every firing of the new `unbannered` class dies
with `NameError` before the message is printed and before the log is written — and no self-test can
see it, because nothing in the plan executes `run_decide`.

**Evidence.** Task 4 (plan `:506-509`) delivers:

```python
    code, message = decide(
        texts, armed,
        steps=_plan_steps() if armed else _UNSET,
        edited=_edit_inside_repo(edited_paths_of(records or []), ROOT))
```

Task 5 (plan `:580`) then reads `steps` in the `else` arm of the log block, and the plan's only
acknowledgement is a prose aside at `:592` — *"⚠ `steps` must be in scope here — hoist it to a local
in `run_decide` before the `decide()` call"* — with **no replacement snippet**. Task 4's own
"Interfaces"/Self-Review sections do not mention it; `:730` repeats the note as a "known ordering
constraint" rather than an edit. Two tasks therefore ship contradictory code and the later one wins
only if a reader notices a sentence.

Driven against a fixture (armed sentinel, plan with 3 unticked steps, one `Edit` to a repo file, no
banner) the reconstruction produced:

```
  File ".../scripts/check-banner-armed.py", line 273, in run_decide
    unticked = 0 if steps in (_UNSET, None) else steps[1] - steps[0]
                    ^^^^^
NameError: name 'steps' is not defined
exit code: 1
--- was anything logged? ---
(no log file)
```

The failure is exactly co-extensive with the feature: `banner` is `None` **by construction** in the
new class (spec §7), so the `else` arm is the only arm it ever takes. The pre-existing `unarmed`
class takes the `if banner:` arm and is unaffected — which is why the defect is silent.

Consequences beyond the crash:
* the WARN message is never printed (`print(message, …)` is *after* the log block, `check-banner-armed.py:221-222`);
* nothing is appended to `.claude/banner-warnings.log`, so spec §7's *"the rate is a number"* is false for the class §7 exists to record;
* the script exits 1, which the hook maps to exit 1 — **indistinguishable from a legitimate warning**. The one invariant that does hold is the plan's Global Constraint at `:20`: it never returns 2.

**Smallest fix.** In Task 4 Step 3's `run_decide` snippet, bind it:

```python
    armed = _armed()
    steps = _plan_steps() if armed else _UNSET
    code, message = decide(texts, armed, steps=steps, edited=…)
```

Applied to the reconstruction, the same fixture then prints the full `⚠ PLAN WITHOUT A BANNER`
message and appends `2026-09-04T22:32:53-07:00\t-\tunbannered\t3 unticked`. Delete the aside at
`:592`; a note is not an edit. See also H1 — the reason no test caught this.

### B2 — F6 fails after Task 6, not just before it. `hook.index("exit 2")` finds a COMMENT.

**Claim.** Task 6 Step 4 states *"Expected: all PASS"*. It is not achievable by the edit Task 6
describes. The first occurrence of `exit 2` in `block-idle-stop.sh` is in the header comment at
`:15`, which the plan does not touch and which sits above every line the banner block could move to.

**Evidence.** Measured on the real file:

```
check-banner-armed.py first at line 54 (char 2939)
'exit 2'              first at line 15 (char  925)
  -> '# Contract: exit 2 blocks the stop and feeds stderr back to Claude; exit 0 allows it.'
F6 assertion (banner < exit2) today: False
```

Both occurrences of the string, enumerated: line 15 (the comment) and line 40 (the real
`exit 2`). Applying Task 6's move exactly as written — banner block inserted after `:38`, blocking
`if` following it, old block at `:43-57` deleted, `check-ci-watched` left in place — and re-running:

```
=== AFTER Task 6 (banner block moved ahead) ===
  FAIL  F6 the banner guard is invoked BEFORE the blocking check's exit 2
51/52 self-test cases passed
check-banner-armed.py first at line 46 (char 2695)
'exit 2'              first at line 15 (char  925)
F6 assertion: False
```

So Task 6 Step 4, and Task 7 Step 5's `python3 scripts/check-banner-armed.py --self-test` gate, are
both red as specified. Task 6 Step 2's stated red reason (*"today `check-banner-armed.py` appears at
`:54`, after the `exit 2` at `:40`"*) is **the wrong cause**: the assertion is false because of
`:15`, and would be false with the invocation at line 1.

This is also the honesty problem the brief asks about (attack 7) in its sharpest form: F6 does not
merely *risk* matching a comment — it *does*, today, and the plan's own red-step explanation
misattributes it.

**Smallest fix.** Anchor on the executable line rather than the string. Either
`hook.index("check-banner-armed.py") < hook.index("\nexit 2\n")` (matches the bare statement at
`:40`/`:50`, not the prose), or better, compare against the block that owns it:

```python
    blocking = hook.index('check-plan-progress.py "${ARGS[@]}"')
    case("F6 the banner guard is invoked BEFORE the blocking check",
         hook.index("check-banner-armed.py") < blocking)
```

and keep the structural-limits comment. Do **not** fix it by rewording `:15` — spec §2 quotes that
line as the routing contract, and a test that forces a documentation edit to pass is measuring the
wrong subject.

---

## High

### H1 — F4 was downgraded from a side-effect test to a pure shape test, breaking §5's own sorting rule.

**Claim.** Spec §5 F4 is *"a WARN of the new class → **a line appears in the log**"*, and §5's
governing sentence is *"no test expecting `QUIET` can discriminate a fix. Only `WARN`, `CANNOT RUN`,
or a **side effect** can."* The plan implements F4 as an assertion about `log_line`'s **string
format** (plan `:544-546`) — a pure function, no side effect, no `run_decide`. That substitution is
what let B1 through.

**Evidence.** Plan `:543-546`:

```python
    case("F4 the banner-less class has a log shape — 3 unticked, no banner",
         log_line("unbannered", "3 unticked", "2026-09-04T07:00:00-07:00", "s").split("\t")[2]
         == "unbannered")
```

Nothing in Tasks 1–7 calls `run_decide`. Confirmed by search over the existing suite
(`check-banner-armed.py:228-317`) and over every case block the plan adds: zero references. So the
entire I/O shell — the `_plan_steps()`/`_UNSET` wiring, the `_edit_inside_repo(edited_paths_of(…), ROOT)`
composition, and the log write — is untested by construction. B1 is the first bug that fell in;
replacing `_edit_inside_repo(...)` with a bare `bool(edited_paths_of(...))` (i.e. deleting spec R3's
whole path scope at the call site) would also pass 52/52.

**Smallest fix.** Add one case that drives `run_decide` against a temp fixture, asserting the side
effect §5 asks for: write a sentinel + plan + JSONL under `tempfile.TemporaryDirectory()`,
monkeypatch `SENTINEL`/`WARN_LOG`/`ROOT` module globals for the duration, call
`run_decide(json.dumps({"transcript_path": …}))`, and assert `WARN_LOG.read_text()` ends with
`\tunbannered\t3 unticked\n`. That is F4 as specified, it is the smallest thing that could have
caught B1, and unlike F6 it is an execution test. (It is *not* the shell-hook harness §6 puts out of
scope — `run_decide` is Python.)

### H2 — `_plan_steps`' except list cannot hold what `exec_module` throws. Measured escape.

**Claim.** Task 3's docstring (plan `:348-349`) says *"exec_module can surface SyntaxError — so the
catch is deliberately wide"*, and spec §4.3 says *"`exec_module` can surface **anything**"*. The
delivered list is `(ImportError, OSError, SyntaxError, KeyError, AttributeError, ValueError)` —
finite, and it does not cover "anything". The stated purpose of catching at all
(plan `:316-319`: *"a rename must not kill the working half with a traceback instead of this file's
own TREAT THIS AS NOT RUN vocabulary"*) is therefore not achieved.

**Evidence.** Appending one undefined name at module scope to the borrowed
`scripts/check-plan-progress.py` in the scratch repo, then running `--decide`:

```
  File ".../scripts/check-plan-progress.py", line 284, in <module>
    UNDEFINED_NAME_AT_MODULE_SCOPE
NameError: name 'UNDEFINED_NAME_AT_MODULE_SCOPE' is not defined
REAL exit code: 1
```

A traceback, exit 1, no `TREAT THIS AS NOT RUN`, and — because the hook maps 1 and 2 identically —
**indistinguishable at the hook from a genuine warning**. A partially-edited
`check-plan-progress.py` (this repo edits it: it is the sibling guard) is the realistic trigger.
Note this is the *same shape* as B1's exit code: the plan has two distinct ways to emit exit 1 that
mean "I crashed", and one that means "I have something to say".

**Smallest fix.** `except Exception:` in `_plan_steps`, with the existing docstring paragraph
kept as the reason. The narrow list buys nothing here — every listed exception maps to the same
`return None`, so widening changes no behaviour except the one that currently escapes.

---

## Medium

### M1 — the declared self-test count is stale across six of the seven commits.

`check-banner-armed.py:47` declares `# 25 cases`; the reconstruction prints **52**. Task 7 Step 3 is
the only step that updates it, so the commits ending Tasks 1–6 each leave
`python3 scripts/check-selftest-counts.py` red (DRIFT, exit 1) — and that command is a CI step at
`.github/workflows/ci.yml:217`, not a local nicety. Case counts after each task, measured by
construction: T1 → 29, T2 → 32, T3 → 37, T4 → 49, T5 → 50, T6 → 52, T7 → 52. Each task's Step 4 says
"Expected: all PASS" about `--self-test` only, so nothing in the plan surfaces this.

**Smallest fix.** Either add "update the declared count at `:47` to the printed number" to each
task's Step 4, or state explicitly in Global Constraints that `check-selftest-counts.py` is red until
Task 7 and that intermediate commits must not be pushed alone. The second is cheaper and honest.

### M2 — Task 7 Step 4's quoted backlog string does not exist, and there are two occurrences, not one.

Plan `:706` says: change *"edits a **tracked** file"* to *"edits a file inside the repo"*. Measured
against `docs/backlog.md` row 95: `**tracked**` appears **zero** times; `tracked` appears **twice**,
neither bolded:

1. *"…the predicate needs a second clause — most plausibly \*the turn edited a tracked file\*."*
2. *"**FALSIFIER FOR ANY FIX:** a session that arms a plan, edits a tracked file and emits no banner must WARN…"*

An executing subagent searching for the quoted string finds nothing; one searching for `tracked`
finds two and is not told which. Spec §3 and §8.3 both say the *falsifier* is the one that must
change — but occurrence 1 is the row's statement of the predicate, which the plan's own §4.7 also
contradicts. This is the instance-not-class shape.

**Smallest fix.** Name both occurrences and their edits explicitly, by their surrounding words rather
than by a bolding that is not there.

### M3 — §2's two-reader table has a third state, and Task 6's comment restates the table as exhaustive.

Task 6's hook comment (plan `:650-652`) asserts *"a blocked stop exits 2 and Claude reads it …; an
unblocked stop exits 1 and the human reads it (the auditor, **when nothing is left to correct**)"*.
There is a state where the stop is unblocked and there *is* something left to correct:
`check-plan-progress.decide` at `:130-131` ALLOWs when `stop_hook_active and prev_unticked is not
None and unticked >= prev_unticked` — the anti-nag, which this repo measured firing three times in
one session (backlog #94, quoted in that file's own docstring at `:28-36`). In that state the plan is
armed, steps are unticked, and the warning written for the assistant is routed to the human.

The WARN message hedges (*"If this stop is being blocked, you are reading this mid-plan"*), so this
is a comment-accuracy defect, not a routing defect — but the comment is the artefact §2 asked for,
and it is stated as a complete enumeration.

**Smallest fix.** One clause in the Task 6 comment: *"…or exits 1 because the anti-nag let a
no-progress stop through, in which case the human sees a message addressed to the assistant."*

### M4 — Task 1's two line ranges disagree, and the wider one deletes helpers the new code calls.

Task 1's **Files** line (plan `:52`) says *"Modify: `scripts/check-banner-armed.py:73-121` (split the
helper)"*. Step 3 (plan `:102`) says *"Replace `assistant_texts_since_last_user` (`:73-104`)"*.
`:107-121` is `_is_tool_result` and `_text_blocks` — both **called** by the replacement block
(`records_since_last_user` at plan `:137`, `texts_of` at `:147`). Taking the Files range literally
deletes them and the suite dies at import. Step 3 is right; the Files row over-claims.

**Smallest fix.** Change the Files row to `:73-104`.

---

## Low

**L1 — three of the seven red steps are crashes, not failures.** Task 1 Step 2, Task 2 Step 2 and
Task 3 Step 2 expect `NameError` / *"unexpected keyword argument"*. Because `case(...)` evaluates its
argument eagerly, these abort `_self_test` before any line prints — so "Expected: FAIL" describes a
traceback with **zero** case output, not a red case. Behaviourally the reds are still honest (F5,
`_armed_from_text`'s paused clause and F2/F3 each fail on an assertion once the name exists, verified
in the reconstruction), so this is a labelling defect. Say "Expected: the suite ABORTS with …".

**L2 — F6b can never go red in this plan.** `"$ROOT/scripts" not in hook` is true today (measured:
`$REPO_ROOT/scripts` does not contain the substring `$ROOT/scripts`, because `$` is followed by `R`,
`E`, `P`). It is green before Task 6 and after it, and it stays green if the banner invocation is
deleted outright. It guards a v2 regression that never shipped, which is legitimate, but Task 6 Step
2's "Expected: F6 FAILS" should say F6b is a standing assertion, not part of the red.

**L3 — `_armed_from_text` and `parse_sentinel` disagree on a colon-less `paused` line.** Task 2's
helper takes `line.split(":", 1)[0].strip()`, so a bare line `paused` (no colon) returns `False`
(stood down). `check-plan-progress.parse_sentinel:64-67` only records lines *containing* `:`, so the
same file is **not** paused there and the stop blocks. §4.2's requirement is that the two agree about
what "armed" means. Rare, and it fails in the quiet direction, but it is a divergence in the one
function written to remove one. Fix: derive from `parse_sentinel` rather than re-splitting, or add a
case pinning the colon-less line.

**L4 — Task 7 Step 2's range orphans a bullet.** `:35-37` is the `WHAT IT CANNOT SEE` header plus the
first bullet; the second bullet (*"whether the work was genuinely finished…"*, `:38-39`) is still
true and still wanted, but would be left hanging under the §9 replacement's own header. Either say
`:35-39` and re-include it, or say "keep `:38-39`".

**L5 — a vacuous absence-assertion.** Plan `:409-410`: `"Nothing is blocked" not in decide([], armed=True, steps=S, edited=True)[1]`.
The new WARN message is written fresh in the same task and never contained the string; the case
passes against any implementation that returns any message at all. This repo has a memory note on
exactly this shape. Keep it if it is meant as a ratchet, but label it so rather than counting it as
coverage.

**L6 — `_edit_inside_repo` returns True when the path IS the root.** Measured:
`_edit_inside_repo(["/repo"], Path("/repo")) is True`, because `relative_to(root).parts[:1]` is `()`
and `".git" in ()` is False. Unreachable in practice (`file_path` is always a file), noted for
completeness.

**L7 — `decide()` loses its type annotations.** The current signature is
`decide(texts: list[str] | None, armed: bool) -> tuple[int, str]` (`:139`); Task 3's replacement is
bare. `_UNSET` is not expressible in the annotation, but `steps: tuple[int, int] | None | object`
keeps the rest.

**L8 — Global Constraints cites `:66-73` for the exit-1 mapping.** It is `:68-73`; `:66` is `CI_RC=$?`.

---

## Claims I verified as CORRECT

Each of these was a plausible defect the plan could have had. It does not.

* **`steps in (_UNSET, None)` with a tuple is safe.** Executed: `_UNSET → True`, `None → True`,
  `(1,4) → False`, `(4,4) → False`, no exception. `tuple.__eq__` returns `NotImplemented` against
  `object()`, identity fallback gives `False`. No numpy-style ambiguity.
* **`Path.resolve()` on non-existent paths behaves as assumed on darwin.** Executed:
  `/repo/scripts/x.py → /repo/scripts/x.py`, `/repo-old/x.md → /repo-old/x.md`,
  `/tmp/scratch/x.md → /private/tmp/scratch/x.md`. All five `_edit_inside_repo` cases pass, including
  the sibling-checkout and `.git` cases. `resolved.relative_to(root).parts[:1]` does test the first
  component, as the comment claims. The real `ROOT` resolves to itself
  (`/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud`), so the macOS symlink
  hazard does not bite here.
* **`ROOT / "scripts" / "check-plan-progress.py"` is the right base.**
  `ROOT = Path(__file__).resolve().parent.parent` (`check-banner-armed.py:59`) is the repo root;
  `begin-plan.py` uses a `SCRIPTS` constant for the same path. `importlib.util` is correctly added.
* **`fields["plan"]` is safe.** `parse_sentinel` returns a plain dict; a missing key raises
  `KeyError`, which *is* in the catch. An empty `plan:` value gives `IsADirectoryError` (an `OSError`)
  and is also caught — and cannot arise anyway, since `_armed_from_text` requires a non-empty value.
* **Importing `check-plan-progress.py` runs no work** — its module body is guarded by
  `if __name__ == "__main__"` (`:269`), and the reconstruction imports it cleanly.
* **`_armed_from_text` is resolvable from `_self_test`.** Module-scope definition, name resolved at
  call time; all three Task 2 cases pass in the reconstruction despite the "I/O shell" placement.
* **No existing self-test case changes behaviour.** Attack 4, answered by execution: with `_UNSET` as
  the default, all 25 originals pass. In the 52-case reconstruction the *only* red is F6. In
  particular `:257-258` (`decide([B], armed=True)`) stays QUIET — the `armed and steps is None` hoist
  does not see `_UNSET` — and the `assistant_texts_since_last_user` wrapper preserves the
  `None`-vs-`[]` distinction the cases at `:285-286` and `:305-306` depend on (`None if records is
  None`, not `if not records`).
* **Only `:255-256` and `:311-313` break, and both are handled.** Enumerated over all 25: the message
  cases at `:251-254` survive Task 7's rewording, the windowing cases survive Task 1's split, and the
  log case is the one Task 5 replaces. No unmentioned breakage.
* **Task 5's red is honest.** Against the old `log_line(step, total, when, session)`, the new call
  yields `"…\tsess\tSTEP unarmed of STEP 2 of 5\tunarmed\n"` — both cases fail on the assertion, not
  on a `TypeError`.
* **F5, R6, R1–R4 and the finished-plan case all discriminate.** Verified by running: swapping
  `steps[1] - steps[0]`, hardening `edited`, dropping `armed`, reordering the branches, or relaxing
  `unticked > 0` to `>= 0` each turns a named case red.
* **The moved hook is syntactically valid and the arithmetic survives.** `bash -n` clean;
  `BANNER_RC` is set before the blocking `if` and reaches `:66`; `CI_RC` is still set on every path
  that reads it; no variable is used before assignment.
* **`check-ci-watched.py`'s behaviour is genuinely unchanged.** It was already unreachable on a
  blocked stop (the `exit 2` at `:40` preceded it) and still is. The plan's "leave it exactly where it
  is" is accurate; spec §6 and §4.1 are consistent with the delivered edit.
* **Nothing parses the warnings log.** `grep -rn 'banner-warnings'` over the repo returns the writer,
  its self-test, the hook comment at `:50`, `docs/dashboard-entries.md:3287` (prose only — *"Log:
  `.claude/banner-warnings.log` (gitignored)"*, no column shape), the spec and the review docs. The
  column-grammar change breaks no reader, as `:566-567` claims.
* **The self-test count instruction is sufficient (attack 8).** `count_drift`
  (`check-plan-code.py:1121`) matches `--self-test\s+#\s*(\d+) cases`, which `:47`'s form satisfies,
  and `check-selftest-counts.printed_total` reads the **denominator of the last line containing
  "passed"**. The suite's per-case lines print `PASS`/`FAIL` (uppercase), so they are filtered out —
  which is what saves the R6 label *"52 of 72 such records"* from being read as a total, since
  `RATIO` would otherwise match it. Reading the printed `N/N` and copying it is correct. The number
  is **52**.
* **`check-plan-task-order.py` passes on the plan** — *"6 tasks produce, 6 consume — ✅ no forward
  references"*, exit 0. The plan's stated ordering (T4←T1,T3; T5←T4) holds.

## Spec coverage map (attack 5)

| Spec | Plan | Verdict |
|---|---|---|
| §2 two-reader contract | T6 comment, T4 message, T7 Step 1 | Implemented; comment incomplete → **M3** |
| §4.1 move one observer | T6 | Implemented; its falsifier is broken → **B2** |
| §4.2 paused | T2 | Implemented; edge divergence → **L3** |
| §4.3 borrow by path | T3 | Implemented; catch too narrow → **H2** |
| §4.4 hoist blindness | T3 | Implemented, verified F2/F3 |
| §4.5 `isMeta` only | T1 | Implemented, verified F5/R6 |
| §4.6 two new inputs | T1 + T4 | Implemented |
| §4.7 path test | T4 | Implemented, all five cases verified |
| §5 F1 | T4 | Implemented, discriminates |
| §5 F2, F3 | T3 | Implemented, discriminate |
| §5 **F4** | T5 | **Downgraded to a shape test → H1** |
| §5 F5 | T1 | Implemented |
| §5 F6 | T6 | **Cannot pass → B2** |
| §5 R1, R2, R4 | T4 | Implemented |
| §5 R3 | T4 (helper level only) | Partial — the call-site wiring is untested (H1) |
| §5 R5 | T2 (helper level) | Implemented at `_armed_from_text` rather than `decide`; acceptable |
| §5 R6 | T1 | Implemented |
| §7 log records the new class | T5 | **Code present, never executes → B1** |
| §8.1 declared count | T7 Step 3 | Implemented; stale for six commits → M1 |
| §8.2 docstring | T7 Step 2 | Implemented; range orphans a bullet → L4 |
| §8.3 backlog falsifier | T7 Step 4 | **Quoted string does not exist → M2** |
| §8.4 both "Nothing is blocked" | T7 Step 1 + T4 | Implemented |
| §8.5 dashboard entry | T7 Step 4 | Implemented |
| §9 blind spots | T7 Step 2 | Implemented |

R6 and F5 are where the plan claims (Task 1). F4 is not.

## Counts

Blocking 2 · High 2 · Medium 4 · Low 8.

Both Blocking findings are single-line fixes with executed evidence, and neither is a design
disagreement — the plan's own stated expectations ("Expected: all PASS" in Tasks 6 and 7; §7's log
guarantee) are the things measured false.

VERDICT: NOT CONVERGED
