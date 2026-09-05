<!-- codex-review: model=gpt-5.5 -->

## Verdict
NOT CONVERGED

## Findings

### [Medium] M1 does not protect `run_decide`’s new `None` fail-closed branch
scripts/check-banner-armed.py:660 — `case("M1 a sentinel that EXISTS but cannot be read is None, not a quiet False",`
scripts/check-banner-armed.py:661 — `_armed() is None)`

Why it is wrong:
The last fold made `_armed()` three-valued and added a `run_decide` obligation: `None` must stop before it can be treated as falsy. The added M1 case only proves `_armed()` returns `None`; it does not prove `run_decide` maps that `None` to `CANNOT_RUN`.

Failure scenario (concrete inputs -> wrong output):
With `.claude/executing-plan` present but invalid UTF-8 and a readable transcript containing `## ▶ STEP 2 of 5`, deleting the early return makes `armed=None` flow into `decide(...)` as falsy. The result becomes `WARN` / `unarmed` instead of `CANNOT_RUN`. With no banner, it becomes `QUIET`.

The mutation that leaves it green:
Replace scripts/check-banner-armed.py:449-452 with `if False: pass`. I ran the self-test after that mutation: `75/75 self-test cases passed`.

### [Low] Hook comment falsely says observers may not return 2
.claude/hooks/block-idle-stop.sh:70 — `# Any non-zero from EITHER observer surfaces as exit 1 — Claude Code's non-blocking error, which`
.claude/hooks/block-idle-stop.sh:71 — `# shows stderr to the human and lets the stop proceed. Neither may return 2: a detector that only`
.claude/hooks/block-idle-stop.sh:72 — `# observes must not be able to wedge a turn it has no stake in.`

Why it is wrong:
`check-banner-armed.py` can return `2` by design on `CANNOT_RUN`; the hook stores that in `BANNER_RC` and later maps it to hook exit `1` if the blocking check passes. The observer may return 2; the hook must not surface 2 from the observer.

Failure scenario (concrete inputs -> wrong output):
If `.claude/executing-plan` exists but cannot be read, `check-banner-armed.py --decide` returns `2`. The current comment says neither observer may return `2`, which is false about the current code path.

The mutation that leaves it green:
Not a vacuous-test claim; this is a comment correctness finding.
