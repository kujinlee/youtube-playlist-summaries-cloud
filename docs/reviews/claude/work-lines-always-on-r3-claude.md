# work-lines-always-on — round 3 — Claude half

Reviewed range: `771e92d7..d1b8ef4e` (the fold of round 2, `docs/reviews/codex/work-lines-always-on-r2-codex.md`).

Method. Everything below was executed against copies. `git archive d1b8ef4e` was extracted into a
temporary git repository under the session scratchpad, with `HOME` pointed at a scratch directory.
The real `.claude/`, the real `~/explainers/`, the repository's git state and port 7391 were not
touched. Anything not executed is labelled UNVERIFIED.

Baseline on the copy:

```
begin-plan.py --self-test           120/120 self-test cases passed
check-plan-progress.py --self-test   65/65 self-test cases passed
check-plan-code.py --self-test      212/215 — the 3 reds are all "node_modules/typescript is missing"
                                    (an archive has no node_modules: environmental, not this change)
manifest lengths                    begin-plan.json 56, check-plan-progress.json 34 (= declared)
```

Mutations. A small harness (`tools/mut.py` in scratch) applies each entry's edits to a fresh copy,
requires every anchor to occur exactly once, runs the file's `--self-test`, parses `[FAIL] ` lines
and checks that every `expect` label is red. Results:

- **check-plan-progress.json: all 34 entries KILLED, each through its named case.** That includes
  the 3 new entries and the 4 re-anchored ones.
- **begin-plan.json: the 3 new entries plus the moved-expectation entry are all KILLED** through
  their named cases.

---

## Findings

### F1 — Minor — the partial-clear case captures the hook's result and never asserts it, so the "MANDATORY clear" contract the fold wrote down has no case

`scripts/check-plan-progress.py:1038` and the comment at `:596–602`.

The fold's comment says:

```
# is optional and protected (r1 Codex 3); the clear is MANDATORY and stays outside the
# boundary with its old error behaviour.
```

The new regression case binds the hook's outcome and then drops it:

```python
_partial = _attempt(lambda: run_decide(False))
```

`_partial` is never read again. `grep -n _partial scripts/check-plan-progress.py` finds only
`:1038`. The case asserts only that `.claude/last-plan` names the new plan.

**Executed.** This probe mutation makes the mandatory clear optional, so the state unlink is
swallowed and the hook ALLOWs with rc 0:

```
SENTINEL.unlink(missing_ok=True)
run_optional("clear", lambda: STATE.unlink(missing_ok=True))
```

```
MISS rc=0 nfail=0 PROBE the mandatory clear is made optional (state unlink swallowed)
```

All 65 cases stay green. The unmutated hook on the same state behaves the way the comment says.
This was run end to end on the copy: a directory at `.claude/executing-plan.state` and a
fully-ticked plan.

```
PermissionError: [Errno 1] Operation not permitted: '…/.claude/executing-plan.state'
rc=1
```

Nothing pins that. The clear's error behaviour also had no pin before this range. What the fold
added is the sentence claiming the behaviour is kept, and a case that sits exactly on the
triggering state, captures the verdict, and discards it.

**Fix.** Assert `_partial` in the existing case. It is `"RAISED PermissionError"` on macOS and
`"RAISED IsADirectoryError"` on Linux, so assert `str(_partial).startswith("RAISED ")`. Then add a
manifest entry that wraps either unlink in `run_optional`, with that case as its expectation.
Alternatively, drop "with its old error behaviour" from the comment. Either way, the claim and the
suite should agree.

---

## Answers to the mandate (no finding unless stated)

**1. Record-before-clear: verdict, message, rc.** The ordering changes none of them on any path I
could construct.

- `decide()` runs before both steps and its result is not touched.
- The record's only output is stderr, through `run_optional` or the recorder's own failure line,
  and that went to stderr before the reorder too.
- The stdout message is printed after the block, as before.
- `record_last_plan` no longer calls git, so nothing slow or external was moved in front of the
  clear.

Record succeeds, then the clear fails. Executed both ways on the copy, with session `S1` and
`PR_LINE_STATE` stubbed to `open`:

- **State unlink fails** (a directory at the state path). Stop 1: rc=1 with a traceback, the
  sentinel is gone and `last-plan` names `fin`. Stop 2: rc=0, nothing armed. The next
  `_derive_parent()` asks about `feat/new` and returns `fin`. This is honest, and it is exactly the
  r2 Codex 1 scenario, now fixed.
- **Sentinel unlink fails** (`chflags uchg .claude/executing-plan`). Both stops give rc=1
  (`PermissionError`) and the sentinel survives. `last-plan` names `fin`, so **a record now exists
  for a plan that was NOT cleared**. This does no harm: `_derive_parent()` reads the sentinel while
  one exists, and it returns `fin`, the same plan. The record is consulted only when nothing is
  armed. If the plan is later edited, its fingerprint changes and no marker is recorded.

**2. Separate optional steps; does the rebuild run when it must not?** No. The rebuild comes after
both unlinks, so a raising clear skips it. A probe running the rebuild in a `finally:` survives the
suite, but that gap does no harm: `gen-work-lines.py` never reads `.claude/executing-plan` or
`.claude/last-plan` (grep finds them only in prose), so the page cannot show anything about the
clear. The rebuild after a recorder failure now runs. The cpp probe printed `_rebuilt == [1]` with
the recorder raising, and the mutation that re-joins the two is killed.

**3. OPEN in the second answer.**

- **Correctness.** Under `--limit 1`, `--state all` returns the newest PR. If that is OPEN while
  `--state open` just said `[]`, a PR opened or reopened in between, so `open` is right. The
  `why` text ("it appeared between the two questions") is an inference. It is also never printed:
  `_parent_from_last_finished` reads `why` only for `None` and `none`.
- **The first query is not redundant.** With `--limit 1`, the all-states answer is one PR, the
  newest. A branch whose newest PR is MERGED but which has an older OPEN one is found only by the
  first question. The 30-merged case is that state.
- **The moved expectation is honest.** Executed, mutating the first-query check to `if False:`
  turns exactly one case red: "an OPEN PR older than 30 merged ones…". Every other fixture answers
  OPEN to both questions, so the second check now masks the first, which is expected. The move is
  disclosed in the commit message. It is not in the dashboard entry, which mentions only the "four
  anchors re-anchored". That is acceptable, and I am not filing it.

**4. `md_literal`, all 32 marks.**

- **Rendering.** I ran it through the repo's `node_modules/markdown-it` (read-only `require`).
  Eleven inputs were tried: `~~x~~`, `&copy;`, `&#x41; &amp;`, `# heading`, `- item`, `> q`,
  `1. one`, a mixed `PR #384: a|b <x> [l](u) `c` *e* _f_ 1. 2) !x`, a lone backslash, and a
  truncated string ending in a backslash. Each `"…"` came back as its literal input with no
  `<s>/<em>/<a>/<h1>/<li>` markup. The one difference, trailing spaces, comes from
  `gen-work-lines.SERVING` stripping before `-->`, not from the escape.
- **Readability.** The rendered banner reads cleanly. The raw text is heavier: for example,
  `make the work\-lines page always current \(PR \#384\, 2026\-10\-22\)`. Since the text always
  follows `> **Line:** "`, block-level marks (`#`, `-`, `.`, `)`, `>`) cannot fire there, so about
  half of those escapes are unnecessary. The two real `serving:` lines under `.claude/plans/` get 2
  and 0 backslashes. That is a judgement call, not a defect, so it is not filed.
- **Non-Markdown sinks.** None. The Line is emitted only at `begin-plan.py:443`, to stdout, as part
  of `render_banner`. The page uses its own `esc(r["serving"])` (`gen-work-lines.py:204`), so no
  HTML shows backslashes. Nothing else reads `Line:`, `work_line` or `md_literal`. Code-span slugs
  in the chain are not escaped, which is correct.

**5. Renamed zero-call cases.** They assert what their names say. Probing both loops showed that
each iteration, including the "no-fault control", really goes through the clear path:

- begin-plan: `'cleared .claude/executing-plan\n'` both times.
- cpp: `✅ every step … is ticked (2/2). Clearing …` both times.

So the counters see a real clear, not a vacuous one. Both injection points count every call: a
module `setattr` for begin-plan, and the module global for cpp. Each "queries the current branch
again" mutation is killed through the zero-call case.

**6. New and re-anchored entries.** All six new entries are KILLED through their named case, and
so are the four cpp re-anchors and the moved begin-plan expectation. Every anchor matched exactly
once.

- The begin-plan "--finish queries the current branch again" entry also turns the recorder case
  red, because the inserted call raises outside `run_optional`. That is collateral, not a wrong
  reason: the zero-call counter is red too.
- The cpp "clears BEFORE recording again" entry is killed only by the partial-clear case, and for
  the stated reason: `last-plan` keeps `other.md`.

---

## Thrashing or prose floor?

Provenance of round 2's five findings, checked against `git show` of earlier trees:

| r2 finding | Introduced by | Fold-caused? |
|---|---|---|
| Codex 1 (clear before record) | the original feature, `7fdd335c` (`3a2795d1` already cleared first) | no |
| Codex 2 (shared lambda) | r1 fold, `cbef908c` | yes |
| Codex 3 (two-question race) | r1 fold, `cbef908c` (the open question asked directly) | yes |
| Codex 4 (eight-char escape set) | r1 fold, `cbef908c` | yes |
| Codex 5 (vacuous "raises" names) | r1 fold, `cbef908c` | yes |

Provenance of this round's findings:

| r3 finding | Introduced by the r2 fold? | Evidence |
|---|---|---|
| F1 (unasserted `_partial`, unpinned "MANDATORY" claim) | **partly**: the claim sentence and the dropped capture are new in `d1b8ef4e`; the missing pin on the clear's error behaviour predates the whole range | `git diff 771e92d7..d1b8ef4e` adds both lines; the probe mutation needs no new code to survive |

Verdict on the question: **the prose floor, not thrashing in substance.** The letter of the arming
condition is met only narrowly. One Minor in `run_decide` follows a round-2 fold-caused Minor in the
same function. But that Minor is a test-strength gap over behaviour that is unchanged and correct;
I executed it and it fails closed as the comment says.

- No behavioural defect was introduced by the round-2 fold.
- Every r2 fix holds under execution.
- All 38 relevant mutations are attributed.
- Severity fell from Major+4 Minor to one Minor.

A redesign would not remove F1: it is one missing assertion. **Do not convene an architecture
review over it.**

VERDICT: CONVERGED
