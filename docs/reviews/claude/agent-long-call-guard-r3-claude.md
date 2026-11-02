Reviewed head: 3a6951399c3e900d7b4f213ab25de59aa0ca4fc5

# PR #468 — agent-long-call-guard, round 3, Claude half

**Subject:** `git diff 53e087cf..3a695139` (the round-2 fold), and the PR as a whole (backlog #455). The Codex half
is a `REVIEW GAP: codex — alternation`. Round 3 is the last round that folds non-BLOCKERs (`review-method.md` §0 Q4c).
**Method:** I re-read the installed Claude Code 2.1.309 binary myself (`strings` on
`~/.local/share/claude/versions/2.1.309`). I sent crafted payloads through `main()` and through the real launcher
(`bash .claude/hooks/agent-long-call.sh`), with the environment cleared (`env -i`) and then set. I ran the self-test,
the scoped mutation sweep, and `check-selftest-counts.py --changed`. Nothing was edited or committed.

## What I read in the binary, independently of round 2

- `yu`, `Uns` and the three regexes match the hook's transcription exactly. `D=/^[+-]?(\d+(\.\d*)?|\.\d+)[eE][+-]?\d+$/`.
  `_=/^[+-]?\d{1,3}([_,   ])\d{3}(?:\1\d{3})*$/`. `p=/[_,   ]/g`. The hook's character classes are
  byte-for-byte `_ , U+00A0 U+202F space`, and both use `re.ASCII` (JS `\d` without the `u` flag is ASCII).
- `fde`/`gMe` are as the r2 doc quotes them. Both test `!isNaN(t)&&t>0`, and the hook now tests `> 0` in both.
- `Ne()` is `String(e).toLowerCase().trim()` in `["1","true","yes","on"]`, with `!e` returning false first. `harness_bool`
  does lower-then-trim in the same order, and treats `""` the same way.
- The `timeout` preprocessor (`Q2e`, wrapped by `v0`) runs `e.trim()`, tests `/^[-+]?\d+(\.\d+)?$/`, and keeps the
  number only when it is `Number.isFinite`. The hook does the same: a 400-digit string becomes `inf`, `is_number`
  rejects it, and the result is NOT CHECKED.
- Bash call site: `Xt=Wt===!0&&(b===void 0?!qt:!Wye()&&…)` and
  `fn=Math.min(Rt||kQ(),Xt?Ahe():OH(),s?.maxTimeoutMs??1/0)`. `F3n` (`CLAUDE_CODE_AUTO_BACKGROUND_TIMEOUT_MS`) only
  changes `fn` when `isMainAgent`, so it cannot affect a subagent. Not modelling it is correct.

## Verdict on the claim

| Clause | Result |
|---|---|
| denies a subagent's call exactly when the effective timeout (2.1.309) > 270 s and it is not truly backgrounded | **HOLDS** for every input I tried: env values with a BOM, U+0085, `0`, `-1`, an empty string and `1e400`; the flag set to ` TRUE `, `1﻿` and `banana`; and `BASH_MAX_TIMEOUT_MS=` empty → deny at 300000. |
| never denies a main-session call | **HOLDS.** A bad timeout from the main session (`"5m"`) → rc 0, nothing printed. The subagent test runs before the timeout is read. |
| every bad input prints NOT CHECKED at exit 1 | **REFUTED for one crafted input (F1).** `NaN` and a 400-digit integer → NOT CHECKED at rc 1. 1000–100000-deep nesting outside `tool_input` → no raise. |
| the r2 fold introduced no defect | **HOLDS.** I found no fix-induced defect. |
| each re-bound anchor binds the clause its entry names | **HOLDS.** All 5 re-bound anchors are unique in the file and sit on the clause their entry names. `check-plan-code.py --mutate . --only scripts/check-agent-long-call.py` → **36 mutations, 36 killed, 36 attributed, 0 survivors**. The self-test passes 43/43. |

`check-selftest-counts.py --changed` (run in the background, as the fold could not) → **RC 0**: 52 of 76 pinned suites
were verified by running them, `check-agent-long-call.py` among them.

## Findings

**F1 — Low, FILE (or a trivial fold), not fix-induced.** `scripts/check-agent-long-call.py:187` (`sys.stdin.read()`
sits outside the `try`). Input I ran: `printf '\xff' | bash .claude/hooks/agent-long-call.sh` → a `UnicodeDecodeError`
traceback at rc 1, and no `NOT CHECKED`. The call is still non-blocking, and the launcher's own comment covers this
("a crash … shows its own traceback"). The harness cannot produce this input, because `JSON.stringify` output is always
valid UTF-8. Two fixes would close it: read `sys.stdin.buffer` and decode inside the `try`, or narrow the docstring's
claim to *a payload the harness can send*.

**I1 — Info, no action.** `Wye()` is `i.CLAUDE_CODE_DISABLE_BACKGROUND_TASKS||yr()`, and
`yr()=Ne(process.env.CLAUDE_CODE_SIMPLE)||a("--bare")`. Under `CLAUDE_CODE_SIMPLE=1`, a `run_in_background` call with a
600000 timeout runs in the foreground, and the hook allows it (I ran this: rc 0, no output). This is moot, because
the binary says that under bare mode *"settings-file, flag, policy, and plugin hooks never fire there"*, and this hook
is registered in `.claude/settings.json`. At most, add the docstring a clause saying so.

VERDICT: CONVERGED
