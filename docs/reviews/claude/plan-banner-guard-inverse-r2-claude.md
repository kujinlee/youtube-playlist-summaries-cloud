# Claude adversarial review — banner guard inverse PLAN, round 2

**Subject:** `docs/superpowers/plans/2026-09-04-banner-guard-inverse.md` (v2)
**Spec:** `docs/superpowers/specs/2026-09-04-banner-guard-inverse-design.md` (v3, approved — not re-litigated)
**Method:** the plan's Tasks 1–7 were applied **literally** to a copy of `scripts/check-banner-armed.py`
and `.claude/hooks/block-idle-stop.sh` in a scratch repo, and `--self-test` was **run**. Every anchor
was asserted to occur exactly once before substitution; the run aborted at Task 6's anchor and failed
at Task 5's F4. Reconstruction scripts: `<scratchpad>/r2/{apply.py,apply_hook.py,diag_*.py}`.

**Round 1's lesson repeated:** v2's fixes for B2 and H1 are *themselves* the two Blocking findings
below. Both were found by executing, and neither is visible by reading.

---

## Blocking

### B1 — F6's new anchor occurs **zero** times in the hook, before *or* after Task 6. The suite does not FAIL, it **crashes**.

**Claim.** Task 6 Step 1 anchors on `check-plan-progress.py "${ARGS[@]}"`. That substring does not
exist in `.claude/hooks/block-idle-stop.sh` in either state, so `hook.index(...)` raises
`ValueError` and `_self_test()` aborts before printing a summary line. Tasks 6 and 7 can never go
green.

**Evidence.** The hook quotes the *path*, so a `"` sits between `.py` and the space:

```
.claude/hooks/block-idle-stop.sh:39
if ! python3 "$REPO_ROOT/scripts/check-plan-progress.py" "${ARGS[@]}"; then
```

The plan's anchor (`…/2026-09-04-banner-guard-inverse.md:678`) is
`'check-plan-progress.py "${ARGS[@]}"'` — no closing quote. Measured on both states:

| anchor | today | after Task 6 applied literally |
|---|---|---|
| plan v2's `check-plan-progress.py "${ARGS[@]}"` | **0 occurrences → ValueError** | **0 occurrences → ValueError** |
| corrected `check-plan-progress.py" "${ARGS[@]}"` | 1 occurrence, F6 → **FAIL** | 1 occurrence, F6 → **PASS** |

Task 6 Step 3's own code block reproduces the quoted form, so applying the plan verbatim does not
create the anchor either. The run:

```
  PASS  an ordinary repo file counts
Traceback (most recent call last):
  File ".../check-banner-armed.py", line 515, in _self_test
    < hook.index('check-plan-progress.py "${ARGS[@]}"'))
ValueError: substring not found
RC=1
```

**Downstream.** Task 6 Step 2 says *"Expected: F6 prints `FAIL`"* — it does not; nothing prints.
Step 4's *"every case PASSES"* is unreachable. `.github/workflows/ci.yml:195-196` goes red.
`scripts/check-selftest-counts.py:243` then reports `check-banner-armed.py: --self-test exited 1 —
its own cases are red`, so Task 7 Step 3's *"Expected: PASS"* is unreachable too.

**Why this is worse than round 1's B2.** v1's `hook.index("exit 2")` at least matched something and
produced an honest `FAIL`. v2's replacement matches nothing and converts a falsifier into a crash —
the fix moved the defect from *wrong verdict* to *no verdict*.

**Smallest fix.** In Task 6 Step 1, use `'check-plan-progress.py" "${ARGS[@]}"'` (include the quote
that closes the path). Verified above: exactly one occurrence, red today, green after Task 6, and it
cannot match the three comment mentions of the filename (`:6`, `:12`, and Task 6's own
`check-plan-progress.run_decide`), none of which carry `" "${ARGS[@]}"`.

---

### B2 — Task 5's F4 fixture cannot produce a `WARN`. It fails after the plan is fully applied, for **two independent** reasons.

**Claim.** F4 is the one test whose whole purpose is to execute `run_decide` (round 1's H1). With
B1's anchor repaired so the suite can reach it, F4 **fails**:

```
54/55 self-test cases passed
  FAIL  F4 run_decide WARNS on the new class and APPENDS a line — the side effect
```

**Cause (a) — the fixture has no `scripts/`, so the CANNOT_RUN hoist fires, not the WARN branch.**
`_load_plan_progress()` (plan `:354-355`) resolves `ROOT / "scripts" / "check-plan-progress.py"`, and
Task 5's fixture creates only `.claude/` and `plans/` under the patched `ROOT`. Measured:

```
_load_plan_progress()  -> RAISED FileNotFoundError: .../tmpXXXX/scripts/check-plan-progress.py
_plan_steps()          -> None
run_decide(...)        -> rc = 2 = CANNOT_RUN     (F4 asserts WARN)
log written?           -> False
```

So `decide(texts, armed=True, steps=None, edited=…)` lands on §4.4's hoist (plan `:400`), exactly as
the review brief suspected. **The assertion fails; it does not pass for a wrong reason.**

**Cause (b) — on darwin the fixture's own edit path is not "inside the repo".**
`tempfile.TemporaryDirectory()` returns `/var/folders/…`; `Path.resolve()` returns
`/private/var/folders/…`. `is_relative_to` is lexical, so `_edit_inside_repo` returns `False`:

```
edited_paths_of      -> ['/var/folders/.../tmpXXXX/scripts/x.py']
Path(p).resolve()    -> /private/var/folders/.../tmpXXXX/scripts/x.py
is_relative_to(ROOT) -> False
_edit_inside_repo    -> False
```

**Both are independently fatal** — the isolation matrix, each fix applied alone and together:

| fixture | rc | F4 passes |
|---|---|---|
| plan's fixture as written | `CANNOT_RUN` | **False** |
| loader fixed only (`scripts/check-plan-progress.py` copied in) | `QUIET` | **False** |
| symlink fixed only (`Path(_d).resolve()`) | `CANNOT_RUN` | **False** |
| **both fixed** | `WARN` | **True**, log `…\tunbannered\t3 unticked` |

**Task 5 Step 2's stated reason for the red is also wrong.** It says F4 fails because *"`run_decide`
does not yet write for a banner-less WARN"*. The red is the CANNOT_RUN hoist, which is present from
Task 3b and **persists through Step 3** — so Step 4's *"every case PASSES"* is unreachable. This is
round 1's H1 in a new costume: the plan again believes it is exercising the WARN path and is not.

**Scope.** This is a **fixture** defect, not a product one: real `ROOT` is
`Path(__file__).resolve().parent.parent` (`check-banner-armed.py:59`), already resolved, and the real
repo does have `scripts/`. The consequence is that the branch the whole row exists to add ships with
**no executing test**, which is precisely the gap round 1 filed.

**Smallest fix.** In Task 5 Step 1: (i) `_root = Path(_d).resolve()`; (ii) create
`(_root / "scripts").mkdir()` and copy the real `check-plan-progress.py` into it
(`shutil.copy(_saved[0] / "scripts" / "check-plan-progress.py", _root / "scripts")`, taken from the
pre-patch `ROOT`). Both are needed; neither alone works.

---

## High

### H1 — Task 7's docstring repair range excludes the sentence that this change makes most wrong.

**Claim.** Task 7's **Files** line is `scripts/check-banner-armed.py:30-48`, and Step 2 rewrites only
`:35-37`. The docstring's *stated rule* sits at `:27-28`, outside that range, and after this change it
describes one of **two** warning classes:

```
scripts/check-banner-armed.py:25-28
THE RULE, stated so its false alarms are predictable:

    warn  <=>  the HIGHEST banner in this turn is `STEP i of N` with i < N,  AND
               `.claude/executing-plan` names no plan.
```

Two more, also unaddressed by any step:

* `:2` — *"Did this turn announce a multi-step job and then stop partway with nothing armed?"* — the
  one-line summary of a file that now answers the opposite question too.
* `:41-43` — *"FAILS CLOSED ON ITS OWN BLINDNESS. No transcript, an unreadable one, or zero
  assistant text parsed -> exit 2 with CANNOT RUN"* — the enumeration is now incomplete; §4.4 adds
  *an armed plan that cannot be measured*, which is the hoist Task 3b introduces.

**Why High, not Medium.** This repo has already paid for exactly this: backlog #94 was *"anti-nag
docstring overclaims"*, and `dev-process.md`'s own line is that a docstring is the declaration an
external observer checks. Leaving `THE RULE` stating half the rule, in the file whose header claims
the rule is *"stated so its false alarms are predictable"*, reproduces the defect the previous row
closed — and no gate can see it.

**Smallest fix.** Widen Task 7's Files range to `:2, :25-48` and add to Step 2: restate `THE RULE`
with both disjuncts, update `:2`, and add the unmeasurable-plan case to `:41-43`.

---

## Medium

### M1 — Global Constraints says **three** crash-reds and names Tasks 1, 2, 3. There are **four**, and Task 4 is the omitted one.

Plan `:27`: *"Three red steps are CRASHES, not failures… 'Expected: FAIL' in Tasks 1, 2 and 3 means
the suite aborts."* But Task 4 Step 2 (`:466`) says *"Expected: **suite ABORTS** — `_edit_inside_repo`
is not defined"*, and after the 3a/3b split the crash-reds are **T1, T2, T3a, T4**. The Self-Review's
`L1→Global Constraints (crash reds named)` inherits the same miscount.

This matters because that constraint is the plan's own defence against reading a crash as a pass —
an enumeration that omits one of its members is the shape it exists to prevent.

**Smallest fix.** *"Four red steps are crashes — Tasks 1, 2, 3a and 4."* Note also that Task 4's red
is **mixed**: three `FAIL` lines print (F1 and its two message cases return `QUIET`) before the
`NameError` aborts. Worth saying, since "the suite aborts" alone predicts no output.

### M2 — `_armed_from_text` is a **second** sentinel parser in a file that also borrows `parse_sentinel`, and the two measurably disagree.

Spec §4.3 says *"Borrow `parse_sentinel` alongside `count_steps`"*, and Task 3b does — inside
`_plan_steps`. Task 2 then hand-rolls a different sentinel grammar in the same file
(plan `:250-257`), keyed on `line.split(":", 1)[0].strip()` with **no requirement that a colon be
present**. `check-plan-progress.parse_sentinel:64-67` skips any line without `":"`. Measured
disagreement:

| sentinel | `_armed_from_text` | blocking guard sees `paused`? | |
|---|---|---|---|
| `plan: p.md\npaused: waiting on CI` | `False` | `True` | ok |
| `plan: p.md\n**paused**` (no colon) | `False` | **`False`** | **disagree** |
| `plan: p.md\n**paused **` (no colon) | `False` | **`False`** | **disagree** |

In the disagreeing rows this guard stands down while `check-plan-progress` still **blocks** — the
stop is refused and the banner warning that would explain it is suppressed. The direction is quiet,
which is the direction this repo's memory `a-mechanism-can-be-silently-overridden` names as the
dangerous one.

The real producer always writes a colon (`begin-plan.py`:
`SENTINEL.read_text().rstrip("\n") + f"\npaused: {why.strip()}\n"`), so the trigger is a hand-edited
sentinel — which is exactly what `check-plan-progress.py`'s own block message instructs the human to
do (*"add a line `paused: <why>`"*). Real, not theoretical.

**Smallest fix.** One line in Task 2 Step 3: `if ":" not in line: continue` at the top of the loop.
That makes the two parsers agree on the grammar without introducing an ordering dependency on Task 3's
loader.

### M3 — F6 makes the self-test read a file **outside `scripts/`**, which the mutation harness does not stage.

`scripts/check-plan-code.py:739` stages mutation runs with
`shutil.copytree(root / "scripts", d / "scripts")` — `scripts/` **only**. F6 (Task 6 Step 1) adds
`(ROOT / ".claude/hooks/block-idle-stop.sh").read_text()` to `_self_test`, and in a staged tree
`ROOT` resolves to `d`, where that path does not exist → `FileNotFoundError` → the suite crashes and
`control_is_green` refuses the whole run.

**Verified not currently live:** `check-banner-armed.py` appears in no manifest — the mutation
targets today are `check-dashboard-entry.py`, `check-plan-code.py`, `check-selftest-counts.py`,
`check-theme-token-coverage.py`, `gen-dashboard.py`, `page_chrome.py`, `page_markup.py`. So this is
**latent**, and it fails loudly rather than silently. It matters because spec §6 lists *"A mutation
manifest for this guard"* as deliberately out of scope **for now** — i.e. someone is expected to add
one, and this is the trap waiting for them.

**Smallest fix.** One sentence in Task 6 Step 1's comment block, next to the existing *"THIS IS A
STRUCTURAL TEST"* warning: F6 reads outside `scripts/`, so a future mutation manifest for this file
must either stage `.claude/hooks/` or skip F6 under a staged root.

### M4 — the *"What round 1 found"* table silently re-grades one Blocking and omits two findings.

The table presents itself as the fold record with a *"fixed in"* column. Checked against both halves:

* `docs/reviews/coordinator/plan-banner-guard-inverse-r1-codex.md:3` files **Blocking** —
  *"Intermediate task commits leave CI red because the declared self-test count is not updated until
  Task 7."* The table carries it as **`M1`** (Medium). The mitigation in Global Constraints (don't
  push before Task 7) is reasonable; **relabelling the severity without saying so is not.**
* `…codex.md:19` **High** — *"Spec §8 says both 'Nothing is blocked' messages are corrected, but the
  plan edits only `check-banner-armed.py`"* — absent from the table. It **is** answered, in the
  *Refuted* paragraph and Task 7 Step 1's ⚠, but a reader auditing the fold cannot find it.
* `…codex.md:27` **Medium** (Task 3's reds are not behavioural) — absent from the table; present only
  in the Self-Review as `Cx-M2`.

The header counts (5 B / 4 H / 6 M) are **accurate** against the two halves — 2/2/4 Claude + 3/2/2
Codex. It is the table that under-reports.

**Smallest fix.** Add the two missing rows, and mark the re-grade explicitly:
*"Cx-B1 — downgraded to Medium by decision: mitigated by not pushing before Task 7."*

### M5 — `steps is _UNSET or steps is None` is duplicated, and the copy in `run_decide` is **dead**.

Task 4 puts it in `decide` (plan `:504`); Task 5 puts it in `run_decide`'s log block (`:629`). In the
log block the guard cannot fire: reaching the `else` requires `code == WARN` **and** `banner is None`,
which only the new arm produces, and that arm requires `unticked > 0` — so `steps` is always a
`tuple` there. The expression reads as a live safety check and is not one; if the arm's condition
ever changes, the two copies are where they will disagree.

The plan's own Task 3 docstring argues the opposite principle for `count_steps` (*"the rule worth
protecting from duplication is `count_steps`' SEMANTICS, which drift quietly"*), and this is that
shape.

**Smallest fix.** In Task 5's log block use `unticked = steps[1] - steps[0]` with a one-line comment
stating why `steps` is a tuple on this path — one expression, one place, and the invariant written
down instead of re-guarded.

---

## Low

### L1 — `_plan_steps`' docstring says *"NEVER raises"*. Measured: three `BaseException` types escape.

Plan `:370`. Executed against the delivered code with a deliberately broken borrowed file:

| module-scope failure | result |
|---|---|
| `NameError` | `returned None` ✓ (round 1's H2, correctly fixed) |
| `SyntaxError` | `returned None` ✓ |
| `MemoryError` | `returned None` ✓ |
| `SystemExit` | **escaped** |
| `KeyboardInterrupt` | **escaped** |
| `GeneratorExit` | **escaped** |

`except BaseException` would be the wrong fix — swallowing `KeyboardInterrupt` in a Stop hook is
worse. And the realistic trigger is closed: `check-plan-progress.py` has an
`if __name__ == "__main__":` guard and loads clean under the alias `_plan_progress` (verified;
`count_steps` and `parse_sentinel` both present). The defect is the **absolute claim**, in a file
whose culture is that an unfalsifiable guarantee is worse than a bounded one.

**Smallest fix.** *"Never raises an `Exception`. `BaseException` (SystemExit, KeyboardInterrupt) is
deliberately not caught."*

### L2 — two internal-reference slips.

* The round-1 table's `H2` row says *"fixed in **T3 Step 3**"*; after the split it is **T3b** Step 3,
  which is what the Self-Review says. Given the plan's own rule against bare unqualified ids, `T3`
  now names two tasks.
* Ordering note (`:793`): *"T6 depends on nothing but is **last** so the guard is correct before it
  becomes reachable."* T7 is last, and T7 Step 3 depends on T6 having added F6 to the suite.

---

## Claims I verified as CORRECT

* **The bound `steps` local (round 1's B1) is genuinely fixed.** `steps = _plan_steps() if armed else
  _UNSET` (plan `:536`) is an unconditional assignment before `decide` and before Task 5's log block.
  The reconstructed suite raised no `NameError` on any path, including the one F4 executes.
* **Task 3a genuinely changes nothing.** Executed with a signature-widening shim over the delivered
  `decide` body: both 3a cases pass, and the *"passing steps explicitly"* case is the one that drives
  the change (the first is vacuous today but is a real regression pin).
* **Task 3b's red is behavioural, not a crash** — the point of the split. Executed against the 3a
  state: F2 → `0` (want `2`) `FAIL`, F3 → `0` `FAIL`, the TREAT-THIS-AS-NOT-RUN case `FAIL`, the
  paused case `PASS`, **no exception raised**. Round 1's `Cx-M2` is correctly closed.
* **Task 7 Step 4's backlog quotes are exact.** `**tracked**` appears **0** times in `docs/backlog.md`;
  both quoted sentences appear **exactly once** each, and they are the only two `tracked file`
  occurrences inside row 95 (the other two are in the `check-dashboard-entry` row). Round 1's M2 is
  correctly closed.
* **Task 1's Files range is correct.** `:73-104` is `assistant_texts_since_last_user` alone;
  `_is_tool_result` (`:107`) and `_text_blocks` (`:114`) survive and are called by the replacement.
  Round 1's M4 is correctly closed, and the reconstruction imports cleanly.
* **The `globals()` patching in F4 reaches every read.** `decide`, `_edit_inside_repo`, `_plan_steps`
  and the `WARN_LOG.relative_to(ROOT)` interpolation all read module globals at call time; the
  `finally` restores the saved triple. When both B2 causes are fixed the log line is written and the
  message renders — no `ValueError` from `relative_to`.
* **F6b is correct and honestly described.** `"$ROOT/scripts"` is absent from the hook today and after
  Task 6, so it *"guards the fix, it does not drive it"* — accurate.
* **The log-grammar change breaks no reader.** `grep -rn 'banner-warnings'` outside `docs/reviews/`
  returns the writer, the hook comment (deleted by Task 6), the spec, the plan, and
  `docs/dashboard-entries.md:3287` — which says only *"Log: `.claude/banner-warnings.log`
  (gitignored)"*, with no column shape. Spec §7's claim holds.
* **The count instruction is sufficient.** `check-plan-code.count_drift:1121` requires
  `--self-test\s+#\s*(\d+) cases`; Task 7 Step 3 quotes `:47`'s existing `# 25 cases`, so replacing the
  number in place preserves the canonical form. (For reference: the repaired reconstruction printed
  `55/55`.) The instruction to read rather than predict is the right call.
* **Ordering is sound.** T4 needs T1 + T3b; T5 needs T4's local; T6 is independent. Verified by
  applying in order.
* **Spec coverage is complete.** §2 → T4 message + T6 comment + T7 S1; §4.1 → T6; §4.2 → T2;
  §4.3 → T3a/T3b; §4.4 → T3b; §4.5 → T1; §4.6 → T1 + T4; §4.7 → T4; §5 F1–F6 and R1–R6 all present
  and mapped as claimed; §7 → T5; §8's five items → T7 S1–S5; §9 → T7 S2. **No spec item is
  unassigned.** The defects above are in how three of those tasks are *instrumented*, not in what
  they cover.

---

## Summary

2 Blocking, 1 High, 5 Medium, 2 Low.

Both Blockings are **in v2's own repairs**: the replacement F6 anchor matches nothing (worse than the
anchor it replaced), and the new side-effect F4 — the test written specifically because round 1's H1
found nothing was executing `run_decide` — still does not reach the WARN path. The design continues to
hold; the plan cannot be executed to green as written.

VERDICT: NOT CONVERGED
