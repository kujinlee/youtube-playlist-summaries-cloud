# Round 2 — `agent-long-call-guard` (PR #468, backlog #455) — coordinator — NOT CONVERGED (Codex); three harness-reader mismatches fixed

```yaml
round: 2
fixes_nontrivial: true
subject: agent-long-call-guard
halves:
  codex: ran
  claude: skipped
findings:
  - {id: C1, severity: Medium, aim: deliverable, fix_induced: true, component: timeout-reading, disposition: fixed}
  - {id: C2, severity: Low, aim: deliverable, fix_induced: true, component: timeout-reading, disposition: fixed}
  - {id: C3, severity: Medium, aim: deliverable, fix_induced: true, component: timeout-reading, disposition: fixed}
```

REVIEW GAP: claude — alternation. Round 2 runs ONE half; this round it is Codex (`review-method.md` → *Round topology*).

Codex reviewed head `53e087cf`: **NOT CONVERGED**, two BLOCKERs (Q4c) and one Medium. All three are the hook reading
an environment value differently from the harness, and all three came from the round-1 fold. I re-read each in the
installed Claude Code 2.1.309 binary (`strings`), as round 1 did.

## What I read in the binary

- `gMe(n)`: `let e=n.BASH_MAX_TIMEOUT_MS; if(e){let t=yu(e); if(!isNaN(t)&&t>0) return Math.max(t,fde(n))} return Math.max(i,fde(n))` (`i` = 600000).
- `fde(n)`: `let e=n.BASH_DEFAULT_TIMEOUT_MS; if(e){let t=yu(e); if(!isNaN(t)&&t>0) return t} return a` (`a` = 120000).
- `yu(e)`: `let n=String(e).trim(); return Uns(n) ?? parseInt(n,10)`. `.trim()` is JavaScript's.
- `Ne(e)`: `if(!e) return false; if(typeof e==="boolean") return e; let n=String(e).toLowerCase().trim(); return ["1","true","yes","on"].includes(n)`.
  `M.bool()` is `i((n)=>Ne(n))`, and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` is declared `M.bool()`, read by `Wye()` as `i.CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`.

## Per finding

- **C1 (BLOCKER, `BASH_MAX_TIMEOUT_MS` of 0 or -1 bypassed the guard)** — fixed. The round-1 fold dropped the `> 0`
  test on the strength of "a value at or below 0 is under 270000 either way". That was wrong for the MAXIMUM: an
  invalid maximum is not zero, it falls back to the 600000 cap, so the call keeps its own timeout. `effective_timeout_ms`
  now ignores a cap that is not above 0; `default_timeout_ms` tests `> 0` too (no verdict differs there, so no case
  pins it and I say so in the docstring rather than add a case that cannot fail). Case: a non-positive
  `BASH_MAX_TIMEOUT_MS` (0, -1) with `timeout: 300000` is denied. Mutation: the `not cap > 0` test removed.
- **C2 (BLOCKER, Python `strip()` is not JavaScript `trim()`)** — fixed. New `js_trim` strips exactly the JS
  WhiteSpace and LineTerminator set (`JS_WHITESPACE`): it includes U+FEFF and excludes U+0085, U+001C-U+001F. Used by
  `harness_int` and by the numeric-string `timeout` reader. Cases: a BOM-prefixed default is read (deny); a U+0085-prefixed
  default is NaN (allow); the same two for a `timeout` string (deny, NOT CHECKED). Mutations: `strip()` for `js_trim`;
  U+0085 added to the set; `timeout` trimmed with `strip()`.
- **C3 (false-valued `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` wrongly denied background calls)** — fixed, though not a
  BLOCKER. `harness_bool` mirrors `Ne()`: true only for a trimmed, case-insensitive `1`, `true`, `yes`, `on`. Cases:
  `false`, `0`, `banana` keep the exemption; ` TRUE `, `Yes`, `ON`, `1` + BOM disable it. Mutations: `bool(v)` for the
  reader; the flag not trimmed; a word dropped from the set.

## Evidence after the fold

- Self-test **43/43** (37 before; +6 cases: C1 1, C2 3, C3 2). Every new case went red against the
  round-1 code through its mutation.
- `check-plan-code.py --mutate . --only scripts/check-agent-long-call.py`: **36 mutations** (29 + 7), pinned in
  `EXPECTED_MUTATIONS`.
- Docstring, backlog row 455 and the dashboard entry updated to the new semantics and counts.

## Bounds stated, not closed

Unchanged from round 1: `backgroundTasksDisabled` in settings, `shellWallCapMs`, `maxTimeoutMs`, and the teammate
`agent_id` read statically. `Ne()` also accepts a real boolean; an environment value is always a string, so the hook
does not model that branch.
