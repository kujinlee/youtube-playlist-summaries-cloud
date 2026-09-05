# Adversarial code review — backlog #95 banner guard, ROUND 2 (Claude half)

Branch `backlog-95-banner-guard`, PR #225.
Scope as briefed: the last fold only — `50fd23b3`'s three surfaces (`_armed()`'s return contract,
`run_decide`'s control flow, the hook's comments).

## ⚠ Two baselines, because the tree moved mid-review

I reviewed `50fd23b3` as briefed. While I was measuring, the working tree changed underneath me:
the Codex half's finding was folded in (a new `Cx-M2` case, plus a hook-comment correction), taking
the suite from 75 to 76 cases. **Every finding below was re-measured against the working tree
after that fold**, and each one says which baseline it holds on. My finding 1 is already fixed;
I am reporting it because it is the round's most important result, not because it needs work.

| baseline | control | verdict |
|---|---|---|
| `50fd23b3` (as briefed) | 75/75 | **NOT CONVERGED** — 1 High, 2 Medium, 3 Low |
| working tree after the concurrent fold | 76/76 | **NOT CONVERGED** — 2 Medium, 3 Low (the High is fixed) |

## Method actually run

- **Control first, both baselines**: `python3 scripts/check-banner-armed.py --self-test` →
  75/75 at `50fd23b3`, 76/76 on the working tree; green in the repo and in a temp copy before any
  mutation.
- All mutation work on copies under `.claude-tmp/.../scratchpad/claude-half/`. **No repo-tracked
  file was modified** (`git diff` over my session shows only the concurrent fold, not my work).
- 15 mutations applied to the **delivered** code one at a time, plus three live `run_decide`
  repros against purpose-built fixtures (an undecodable sentinel, a `chmod 000` sentinel, a
  reordered hook).

---

## Findings

### [High — ALREADY FIXED in the working tree] The M1 fix's WIRING was unguarded: deleting the `armed is None` early-return survived 75/75, and the guard then emitted a factually false warning and wrote a false row into its own false-alarm log

`scripts/check-banner-armed.py:448-452` (at `50fd23b3`)

```python
    armed = _armed()
    if armed is None:
        print("CANNOT RUN: .claude/executing-plan exists but could not be read, so this check "
              "cannot tell whether a banner was owed. TREAT THIS AS NOT RUN.", file=sys.stderr)
        return CANNOT_RUN
```

**Mutation:** delete lines 449-452. **At `50fd23b3`: 75/75 self-test cases passed.**

`_armed()` has exactly two consumers — `run_decide` and the self-test (grepped across `scripts/`,
`.claude/` and CI: no others). The self-test called it only directly, at `:661` and `:664`. So
nothing observed the mapping the commit message asserts: *"None is that third state; run_decide
maps it to CANNOT RUN."*

**Why it was wrong:** with that block gone, `None` falls through `steps = _plan_steps() if armed
else _UNSET` (`:453`) as falsy and into `decide(texts, None, …)`, where `:298` `if armed:` is also
falsy. A session whose sentinel is present and armed is then reported as having no plan.

**Failure scenario — both rows are real runs.** Sentinel present but undecodable; plan has 3
unticked steps; transcript contains `## ▶ STEP 2 of 5 — doing a thing`:

| | exit | stderr | log |
|---|---|---|---|
| delivered | `2` CANNOT_RUN | `CANNOT RUN: … TREAT THIS AS NOT RUN.` | *(none written)* |
| mutant | `1` WARN | `⚠ BANNER WITHOUT A PLAN — … while .claude/executing-plan names nothing.` | `2026-09-05T15:40:15-07:00\ts\tunarmed\tSTEP 2 of 5` |

Two harms, the second worse:

1. *"`.claude/executing-plan` names nothing"* is false — it names a plan the guard could not read.
   The message then tells the reader to run `begin-plan.py <slug>` to arm what is already armed.
2. The appended row says `unarmed`. Per the module docstring (`:11-15`), that log **is** the
   justification for warn-only mode and the evidence base for promoting the guard to blocking. A
   fabricated `unarmed` row is not a missing measurement, it is a wrong one, and nothing downstream
   can tell the difference.

**Status: FIXED in the working tree**, independently, by the Codex half's `Cx-M2` case
(`check-banner-armed.py:729-746`). I re-ran the identical mutation against the fixed tree:

```
  FAIL  Cx-M2 an UNREADABLE sentinel is CANNOT RUN through run_decide, not a quiet False
75/76 self-test cases passed
```

Killed via the case it names. No further work owed on this item. The reason it is still worth
recording: this is the *same defect class* the commit closed one item earlier. M5's finding was
*"delivered against the PREDICATE, not the WIRING"* — M1 got the predicate case and not the wiring
case, in the same commit that fixed it for `edited`.

---

### [Medium — OPEN] The `OSError` arm of `_armed()` is untested; dropping it survives 76/76, and a permission-denied sentinel then becomes an uncaught traceback the hook reports as a WARN

`scripts/check-banner-armed.py:425-430`

```python
    try:
        return _armed_from_text(SENTINEL.read_text())
    except FileNotFoundError:
        return False
    except (OSError, UnicodeDecodeError):
        return None
```

The docstring immediately above names two causes — *"a permission error, undecodable bytes"*
(`:421-422`). Only the second has a case. `:660` uses a non-UTF8 fixture, `:663` a missing path,
and the new `Cx-M2` case uses a non-UTF8 fixture again. **Nothing in the suite produces a
non-`FileNotFoundError` `OSError`.**

**Mutation:** `except (OSError, UnicodeDecodeError):` → `except UnicodeDecodeError:`.
**76/76 self-test cases passed** — re-measured against the working tree after the fold.

**Failure scenario (measured):** `chmod 000 .claude/executing-plan`, then drive `run_decide`.

- delivered → `EXIT: 2 CANNOT_RUN`, correct message.
- mutant → `UNCAUGHT: PermissionError -> [Errno 13] Permission denied: …/.claude/executing-plan`

That traceback exits the interpreter with status **1**. Status 1 is `WARN` in this module's own
table (`:70`), and `block-idle-stop.sh:73` tests only `"$BANNER_RC" != "0"` — so a crashed guard and
a genuine warning are the same event at the hook. This is precisely the failure `_plan_steps`'s
docstring records as measured and deliberately defended against (`:381-383`: *"escaped a narrow
list as a traceback and exit 1, indistinguishable at the hook from a genuine warning"*). The
sibling function has that defence; here it is in the code and held by nothing.

**Fix:** a `chmod(0o000)` case alongside the M1 fixture, guarded on `os.geteuid() != 0` — root can
read a 000 file, and the case would be vacuous in a root container.

**Related note, same code, not a separate finding.** The commit claims each of its 8 mutations was
*"killed via the case it names"*. For M1 that is not what happens: reverting `_armed` wholesale to
`except OSError: return False` makes the undecodable fixture raise straight through `case()` and
abort the run. Measured: exit **1** — so it is red, **not** a false green — but only **52 of 75**
cases execute and the `N/N cases passed` summary line never prints. A future regression in `_armed`
therefore also hides the ~23 cases that follow, including F6/F6b/F6c and every `edited_paths_of`
case. Wrapping the `_armed()` assertions so a raise reports as a failed case would make the kill
match the claim.

---

### [Medium — OPEN, and it got worse during this review] F6 — the only guard on the ordering this entire slice exists to create — can be satisfied by a COMMENT

`scripts/check-banner-armed.py:747-749`

```python
    _obs, _blk = "check-banner-armed.py", 'check-plan-progress.py" "${ARGS[@]}"'
    case("F6 the banner guard is invoked BEFORE the blocking check that can exit early",
         _obs in _hook and _blk in _hook and _hook.index(_obs) < _hook.index(_blk))
```

`_blk` is quoted tightly enough that prose cannot match it. `_obs` is a **bare filename**, and
`str.index` returns the first occurrence anywhere in the file — comments included.

**Measured mutation (J), re-run against the working tree:** restore the observer to its pre-slice
position (below the blocking check — the exact defect F6 exists to catch) *and* reword one clause
of the comment this fold added at `:51`, from `not the observer above` to
`not check-banner-armed.py above`:

```
  PASS  F6 the banner guard is invoked BEFORE the blocking check that can exit early
76/76 self-test cases passed
```

The hook is in the broken order, `run_decide` never sees the sentinel `check-plan-progress` unlinks,
and the suite is green.

**This is no longer hypothetical.** At `50fd23b3` the filename appeared exactly once in the hook, at
`:48` (the invocation). In the working tree it appears **twice** — the concurrent fold's new comment
at `:73` cites `check-banner-armed.py:70`. That occurrence sits *after* the blocking check (`:56`),
so F6 still evaluates correctly today. It is correct by placement luck. The L3 comment block that
this fold re-attached sits at `:51-55`, directly **above** the blocking check, and its entire
subject is the observer-versus-blocking-check distinction — so a comment naming the observer landing
there is the natural next edit, and it silently disarms the guard. One fold produced one new mention
already.

**Fix:** pin the invocation, not the filename — `_obs = 'check-banner-armed.py" --decide'`, which no
comment would plausibly contain, or index on the full `printf … | python3 …` line. Assert the
property, not a token the fix happened to introduce.

---

### [Low — OPEN] The new NotebookEdit case passes `file_path`, so the `notebook_path` fallback — which exists only for NotebookEdit — is still untested

`scripts/check-banner-armed.py:209` and the case at `:789-791`

```python
            path = inp.get("file_path") or inp.get("notebook_path")
```
```python
    case("...and a NotebookEdit counts",
         edited_paths_of(records_since_last_user(
             [user("go"), use("/a/n.ipynb", "n1", "NotebookEdit")]) or []) == ["/a/n.ipynb"])
```

`use()` (`:782-784`) always emits `{"file_path": path}`, so the case exercises `_EDIT_TOOLS`
membership and never the key fallback.

**Mutation:** delete `or inp.get("notebook_path")`. **76/76** — re-measured after the fold.

The docstring at `:179` already flags `notebook_path` as UNVERIFIED, so the code is honest. But M3
closed the membership half and left the key half open, and the case name *"…and a NotebookEdit
counts"* reads as though both are covered. In the real runtime the NotebookEdit tool's argument
*is* `notebook_path` — so the untested branch is the one that actually fires, and the tested shape
is the one that never occurs.

**Fix:** change that case's input to `{"notebook_path": "/a/n.ipynb"}`. One key.

---

### [Low — OPEN] The re-attached L3 comment's escape hatch does not exist for the case the comment is about

`.claude/hooks/block-idle-stop.sh:51-55` (unchanged by the concurrent fold)

```bash
# ⚠ THIS COMMENT DESCRIBES THE BLOCKING CHECK BELOW, not the observer above. The 2026-09-05
# reorder moved the observer in between and orphaned it; re-attached deliberately.
# A hook that cannot run must not silently allow the stop it exists to question — but it also must
# not wedge the session on a broken interpreter. Blocking ONCE with a loud message is the middle
# ground: visible, and cleared by the anti-nag guard on the next attempt.
```

The placement is now right. The claim in the last sentence is false about the code it points at.

The anti-nag is `scripts/check-plan-progress.py:130`, *inside* `decide()`:

```python
    if stop_hook_active and prev_unticked is not None and unticked >= prev_unticked:
        return ALLOW, "", unticked
```

Two paths reach this hook's `exit 2`, and neither is cleared by it:

1. **The broken interpreter the comment names.** If `python3` or the script cannot launch, `decide()`
   never runs, so the anti-nag never runs. Every subsequent stop blocks identically — "blocking
   ONCE" is not what happens.
2. **`check-plan-progress`'s own CANNOT-RUN blocks** at `:106` (plan file missing) and `:114` (zero
   checkboxes) `return BLOCK` *before* reaching `:130`, and return `unticked=None` — so
   `run_decide:183` (`elif unticked is not None`) never writes `STATE`. `prev_unticked` stays `None`
   on the next attempt and the anti-nag's precondition is unsatisfiable by construction.

Not a true wedge: the real escape is printed at `:109` — *"Fix the path or delete
.claude/executing-plan"*. The code is defensible; the comment names a mechanism that does not apply
to it.

Worth flagging as the L3 *class* rather than the L3 instance: the fold checked **where** this
comment sat and did not re-read **what it claims** against the code it was moved next to.

---

### [Low — OPEN] The hook's header still makes the stale-scope claim that L4 fixed in the sibling file

`.claude/hooks/block-idle-stop.sh:5-7`, and `:15` (both unchanged by the concurrent fold)

```bash
# and the anti-nag guard live in scripts/check-plan-progress.py; this wrapper only translates
# Claude Code's stdin JSON into that script's flags.
…
# Contract: exit 2 blocks the stop and feeds stderr back to Claude; exit 0 allows it.
```

All three claims are false about the current file:

- The wrapper invokes **three** scripts (`:48`, `:56`, `:67`), not one.
- *"All of the reasoning … live in check-plan-progress.py"* — the exit-code collapsing rule lives
  only here, at `:70-77`, and has no other home. The concurrent fold just **rewrote** that very
  block (correcting *"Neither may return 2"*, which was false about both observers) without
  revisiting the header that claims the reasoning is not there.
- The contract line names exit 2 and exit 0 and omits the **exit 1** the wrapper now produces on
  every observer warning — the code path this whole slice added.

Identical shape to L4, which the same commit fixed at `check-banner-armed.py:216` (*"Existing
callers unchanged"* describing an empty set). The sweep stopped at the Python file.

---

## Checked and clean — recorded so the absence is not read as "not looked at"

**Surface 2, the question the brief asks directly: `reason` cannot disagree with the branch
`decide()` took.** Traced and confirmed:

- `decide()` returns WARN in exactly two places: `:280` requires `banner is None`; `:301` requires
  `banner is not None`. Complementary on the same value.
- `run_decide:458` recomputes `highest_banner(texts or [])`. When `code == WARN`, `texts` cannot be
  `None` (decide returns CANNOT_RUN at `:261` first), and `[] or []` is `[]` — so `highest_banner`
  gets a byte-identical argument to the one `decide` used. Same pure function, same input, same
  result.
- `if banner:` at `:459` is equivalent to `is not None` here: `highest_banner` returns `None` or a
  2-tuple, and every 2-tuple is truthy (including `(0, 0)`).
- In the `unbannered` branch `steps` is guaranteed a real tuple: it is `_UNSET` only when `armed` is
  falsy, and branch A requires `armed`; and `steps is None` would have returned CANNOT_RUN at `:268`.

**Six of the fold's other fixes are load-bearing**, each killed via the case it names — mutations
applied to the delivered code, one at a time:

| mutation | result |
|---|---|
| `if code == WARN:` → `if code != QUIET:` | 74/75 — `FAIL  ...and nothing is logged for a run that could not measure` |
| `return None if total == 0 else (done, total)` → `return (done, total)` | 74/75 — `FAIL  H1 a plan with ZERO checkboxes is CANNOT RUN…` |
| swap the two log reasons | 74/75 — `FAIL  H3 the UNARMED class still warns AND logs…` |
| delete the message hedge (L5a) | 74/75 — `FAIL  ...and the message hedges about blocking…` |
| drop the import cause from the blindness message (M2) | 74/75 — `FAIL  M2 the blindness message names the import cause…` |
| remove `except FileNotFoundError` | red via `...while a missing sentinel is the ordinary unarmed case, False` |
| *(control)* `_EDIT_TOOLS = ("Edit",)` | 73/75 — `FAIL` M3 Write **and** NotebookEdit |

**The declared count is externally verified.** `check-banner-armed.py` is pinned in
`scripts/check-selftest-counts.py` `POPULATION:88`, and that ratchet exits 0 against the tree — so
the docstring's `# 76 cases` (`:69`) is measured, not asserted.

**The L5b symlink docstring addition (`:51-53`) is accurate.** `_edit_inside_repo:405` calls
`candidate.resolve()` before `:406` `is_relative_to(root)`, so a link inside the repo pointing out
does read as outside, and the stated converse holds.

**No finding on the items the brief listed as known and deliberately not done** —
`check-ci-watched.py`'s unreachability on a blocked stop, the absent shell-execution harness behind
F6/F6b/F6c, the absent mutation manifest, or the stated blindness list.

**One thing this half missed, recorded rather than quietly dropped.** I read
`block-idle-stop.sh:70-72` and did not flag *"Neither may return 2"*, which was false about both
observers (`check-banner-armed.py:70` and `check-ci-watched.py:43` both define 2 as CANNOT RUN).
The Codex half caught it and it is fixed at `:70-77`. It is the same defect class as my findings 5
and 6 — a hook comment whose claim outran its code — which is a reason to treat that class as
under-swept rather than closed.

---

## Summary

| # | Severity | Status | Title |
|---|---|---|---|
| 1 | High | **fixed in tree** | M1's wiring was unguarded; deleting it survived 75/75 and produced a false warning + a false `unarmed` log row |
| 2 | Medium | open | `_armed()`'s `OSError` arm is untested; dropping it makes a permission error a traceback the hook reads as WARN |
| 3 | Medium | open | F6 matches a bare filename, so a comment can satisfy the slice's only ordering guard — and a second mention just appeared |
| 4 | Low | open | The NotebookEdit case uses `file_path`, leaving the `notebook_path` fallback untested |
| 5 | Low | open | The re-attached L3 comment's "cleared by the anti-nag" escape does not exist for either blocking path |
| 6 | Low | open | The hook header's "only translates … into that script's flags" is the un-swept half of L4 |

Findings 2 and 4 are one-case fixes. Finding 3 is a one-string fix. Findings 5 and 6 are prose.
