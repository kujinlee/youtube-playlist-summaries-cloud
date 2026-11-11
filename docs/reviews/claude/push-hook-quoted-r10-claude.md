Reviewed head: 20de258e16ae1f768819454a59fc04917f4838df

# Round 10 — `push-hook-quoted` (PR #542, backlog #428) — Claude half, scoped to the round 8 `deny` change

**Mandate:** refute round 8's change (`git show 28c68e49`). Can the new `deny` print nothing, or print something
that is not a valid deny JSON? Did the change alter anything else on the decision path?

**Result: no BLOCKER.** One Low finding (R10-F1). On that path the branch fails exactly as master does, and it is
not a loosening.

## What was checked

- **Scope of the change.** `git diff 9ac8a5d6 HEAD -- .claude/ scripts/ .githooks/ .github/` touches one file, the
  hook. In it, the only change outside `--self-test` is the `deny` function plus `REASON_MAX=4000`. Every `deny` call
  site is at top level, never inside `$( )` or a pipeline, so its `exit 0` ends the hook. `set -uo pipefail` has no
  `-e`, so a failing `out="$(…)"` cannot abort before the `case` runs. Nothing else on the decision path changed.
- **Self-tests:** `bash .claude/hooks/block-default-branch-push.sh --self-test` gives 71/71 (rc 0).
  `python3 scripts/push-command.py --self-test` gives 352/352 (rc 0).
- **Codex's four 1.1 MB repros, built as FILES** (unknown option `--z…` of 1,100,000 characters, then `--force`,
  `--no-verify`, `master` or `HEAD:master`). The branch returns a valid deny of 4195 bytes, with the reason
  truncated and the marker present (`1100282 characters, the first 4000 shown`). Master also denies all four.
- **Comparisons against master's blob** (`git show origin/master:…` into a temp file): 67 payload files, each run
  through both hooks. Each output was parsed with `json.loads`. **0 looser.** The branch is stricter on 2: a lone
  surrogate `\ud800`, and an unbalanced quote. Master allows both.
  - **Truncation boundary:** reason lengths around 4000 (option lengths 3700 to 4100). All valid.
  - **Multibyte cut:** QUOTED unknown options made of `€` (3 bytes), `😀` (4 bytes) and `é` plus a combining accent,
    each shifted by 0 to 3 bytes so a character straddles the cut. Run under `en_US.UTF-8` and under `LC_ALL=C`.
    Under `C`, `${r:0:4000}` cuts by BYTE and can split a character; jq `-R` replaces the broken bytes with U+FFFD.
    Every output decodes as UTF-8 and parses as a deny.
  - **Bad input:** raw invalid UTF-8 bytes (`\xff\xfe`, a cut `\xe2\x82`, inside quotes and not), C0 controls, and
    an escape-heavy reason (`\x02`×4500, each 6 bytes once escaped). All give a valid deny.
  - **NUL:** a NUL cannot reach `deny`. Bash cannot hold one in a variable, and command substitution drops it in
    BOTH hooks. A NUL inside an oversized option gives a valid, truncated deny. `git push origin master\u0000x` is
    allowed by both hooks, so the two hooks agree on it; it is not a loosening.
  - **Rule lines:** 28 ordinary commands (`--force`/`-f`/`--force=`, `--no-verify`, every `hooksPath` and
    `ALLOW_PLAN_LEAK` form in master's own probes, `master`/`HEAD:master`/`refs/heads/master`, chained and
    multi-line forms, plus the allowed controls `feat/x` and `--force-with-lease`). The branch matches master on
    each, except the unbalanced quote, which the branch refuses (stricter).
- **jq failing inside `deny`:** a stub `jq` was put first on PATH. It answers only the `-Rsc` call and passes every
  other call to the real jq. Run on `big_force` and on a 3700-character reason:

  | stub behaviour | branch | master (same stub on its `-nc` call) |
  |---|---|---|
  | SIGKILL, no output | literal deny | **empty = allow** |
  | exits without reading stdin (SIGPIPE to `printf`) | literal deny | **empty = allow** |
  | exit 1, no output | literal deny | **empty = allow** |
  | SIGSEGV | literal deny | **empty = allow** |
  | prints `not-json` | literal deny | invalid JSON |
  | prints a valid **allow** object | literal deny | **allow** |
  | prints the deny PREFIX, then exit 1 or SIGKILL | **invalid JSON, rc 0** (R10-F1) | invalid JSON, rc 0 |

  In every row the branch is at least as strict as master, and strictly stricter in six.

### R10-F1 — Low — `deny` accepts a TRUNCATED jq output that merely starts with the deny prefix

The `case` checks only that `out` STARTS WITH `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",`.
It ignores jq's exit status. Suppose jq is killed (or fails) after writing part of its object. The hook then prints a
truncated object with rc 0. Under Claude Code's documented hook contract, stdout that is not valid JSON is not a
decision, and exit 0 proceeds.
That last step is documented behaviour; I did not measure it.

The comment above `deny` says *"whatever jq does — fails, is killed, prints nothing or prints something else — if
its output is not a deny, a FIXED LITERAL deny is printed"*. The partial-write case is the one exception to that
claim.

**Not a loosening and not a BLOCKER:**
- Master's `deny` has the same exposure: jq writes straight to stdout, and the stub repro shows master prints the
  same partial object.
- Reaching this case needs jq to be killed from outside, between two of its `write`s. Normal `-Rsc` output is about
  4.2 KB for ASCII and up to about 12.4 KB for 4-byte characters.

Repro (stub; `$H` is the hook, `$F` a payload file from Codex's repro):

```
d=$(mktemp -d); P='{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",'
printf '#!/bin/sh\ncase "$1" in -Rsc) printf %%s '"'"'%s"permissionDecisionReason":"Blo'"'"'; kill -9 $$ ;; esac\nexec %s "$@"\n' "$P" "$(command -v jq)" > $d/jq; chmod +x $d/jq
PATH=$d:$PATH bash $H < $F   # prints {"hookSpecificOutput":{…"permissionDecisionReason":"Blo   rc 0
```

(The harness actually run is `scratchpad/r10/stubs.sh`; this is its `partial_kill` stub.)

**Suggested fix (one line):** also require jq to succeed, e.g.
`out="$(printf '%s' "$r" | jq -Rsc '…' 2>/dev/null)" || out=""`. Under `pipefail`, a killed jq then yields the
literal deny. File or fold at the coordinator's discretion. It does not hold the merge.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: not a loosening
LOOSENING-CHECK ce1282293e59: not a loosening
LOOSENING-CHECK 90a173413926: not a loosening
LOOSENING-CHECK 85052e8ab73c: not a loosening
LOOSENING-CHECK 8ca795163b8f: not a loosening
LOOSENING-CHECK 4d7974581a8f: not a loosening
LOOSENING-CHECK 4a3b8fdd91c6: not a loosening
LOOSENING-CHECK e2997ee94d34: not a loosening
LOOSENING-CHECK a37789af0a0d: not a loosening
LOOSENING-CHECK 19e3cb6a182b: not a loosening
LOOSENING-CHECK 6a9e243ccfd4: not a loosening
LOOSENING-CHECK e6c86a86ce2e: not a loosening
LOOSENING-CHECK 30d52ad23ac7: not a loosening
LOOSENING-CHECK 4a4c20c73163: not a loosening
LOOSENING-CHECK e886704a5c48: not a loosening
LOOSENING-CHECK 727e65f884c9: not a loosening
LOOSENING-CHECK 484e60231961: not a loosening
LOOSENING-CHECK 2fec52dc562d: not a loosening
LOOSENING-CHECK c361c21aa22d: not a loosening
LOOSENING-CHECK 1c483d300bca: not a loosening
LOOSENING-CHECK 0639175f96f3: not a loosening
LOOSENING-CHECK 6ed1cdc83491: not a loosening
LOOSENING-CHECK 475f8e419a00: not a loosening
LOOSENING-CHECK b4c2d38505b1: not a loosening

VERDICT: CONVERGED
