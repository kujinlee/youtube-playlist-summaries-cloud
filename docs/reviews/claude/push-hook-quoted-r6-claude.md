Reviewed head: ffcdb4b187878e42f213c6ab6cfac4a7cfb7fe1f
REVIEW GAP: codex — the Codex run was killed by the OS for low memory before output (2026-11-08 21:10); this is the Claude adversarial fallback.

# Round 6 — `push-hook-quoted` (PR #542, backlog #428) — Claude adversarial review (Codex fallback)

Subject: the round 5 fold `9bef9dd0` (master's hook kept as a FLOOR; `NAME+=` an assignment), with master
merged in at `ffcdb4b1`. Mandate: REFUTE "no worse than master by construction". BLOCKER = (1) a command the
branch's hook allows that `origin/master:.claude/hooks/block-default-branch-push.sh` refuses, or (2) an
allow without a decision (crash, timeout, floor not run).

## What was run (at `ffcdb4b1`, in this worktree)

| Check | Result |
|---|---|
| `python3 scripts/push-command.py --self-test` | rc 0, **351/351**, 67 s; `equivalence: 261 compared, 58 refused by master` |
| `bash .claude/hooks/block-default-branch-push.sh --self-test` | **59/59**, 0 FAIL |
| `git hash-object scripts/push-floor-master.sh` vs `git rev-parse origin/master:.claude/hooks/block-default-branch-push.sh` | both `ddb129b5d049…` — the floor IS master's current hook, byte for byte |
| Master's hook vs the branch's hook, same payload FILE, same fixture clone (origin/HEAD = master, on `feat/x`) | see each item below |
| Floor load over the self-test corpus (`floor` wrapped to log every refusal) | 12 corpus commands are refused by the floor alone (decide allowed, master refused); three classes, see R6-F2 |
| Mutation hand-check 1: "the floor's bytes are not checked" | KILLED, through its named case only: self-test rc 1, 1 FAIL — `⭐ floor: a floor file that is not master's bytes REFUSES (floor-not-run), never allows: got (0, ['allow\n'])` |
| Mutation hand-check 2: "`main` prints `decide`, not `verdict`" | KILLED, through its named case `⭐ hook: R5-F1 — a redirection target naming master is refused (master's floor)` (got `allow`) plus 6 more (both floor-file cases, 3 hook R5-F1/F2 cases, the floor-message case); self-test rc 1 |

Mutation count: 107 manifest entries in `scripts/mutations/push-command.json` at head.

## Refutation attempts — each one that FAILED to refute

1. **Is the floor skipped for any input master's hook acts on?** `verdict` (`scripts/push-command.py:527-534`)
   skips the floor only when `decide` already denies, or when no view of the command matches `PUSH_WORD`
   (`:118`, `(?<![\w./-])push(?![\w./-])`). Master's hook acts only past its trigger
   `(^|[;&|[:space:]])git[[:space:]]+${GITOPTS}push([[:space:]]|$)`. In that regex `push` is always preceded by
   a `[[:space:]]` character (the tail of `git[[:space:]]+` or of every `GITOPTS` alternative) and followed by
   `[[:space:]]` or end of line, and no `[[:space:]]` character is in `[\w./-]`. So every command master's
   trigger matches has a `PUSH_WORD` match in the RAW view (`views(cmd)[0]`), and reaches the floor. The early
   allow is a superset of master's early allow. Not refuted.
2. **Input differences between the floor and master's real invocation.**
   - *Carriage return.* Hypothesis: Python's text stdin turns `\r` into `\n`, so the reader and the floor would
     see a line split bash does not make (`git push origin feat/x\r master` pushes `master` in bash). Measured:
     `sys.stdin.read()` preserves `\r` (`'a\rb\r\nc'` round-trips), and the branch refuses both
     `git push origin feat/x\r master` and `git push origin feat/x\r-f` as `outside`; master refuses both too.
   - *Trailing newlines and NUL.* Both hooks take the command through `$(jq …)`, which strips trailing newlines
     and drops NUL the same way, and the floor is handed that same stripped string as JSON. Equal.
   - *Payload fields.* Master reads only `.tool_input.command`; the floor's synthetic payload carries it. Equal
     for any single JSON object. The one difference is R6-F1 (multi-document payloads).
   - *cwd and environment.* The floor inherits the hook's cwd (`cwd=None` in `main`) and the full environment,
     as master's hook did; it resolves `git remote` and the branches itself, so the branch's own `has_remote`
     and escape handling cannot weaken it. Equal.
3. **Floor invocation safety.** The file is read once, hashed (`git hash-object` form), and the VERIFIED bytes are
   what `bash -c` runs (`:507`), so there is no hash-then-exec TOCTOU and a symlink can only point at bytes that
   still have to hash to `ddb129b5`. Every non-clean outcome refuses: unreadable (`floor-not-run`), wrong bytes,
   timeout (`killpg`, `floor-not-run`), non-zero exit, unparseable output; an exception anywhere (e.g. `bash`
   missing, `ProcessLookupError` in `killpg`) is a traceback, rc 1, which the hook's catch-all refuses
   (`block-default-branch-push.sh:275`). SIGALRM at `DEADLINE_S` is rc 142, refused (`:271`). The floor's budget
   is the remaining deadline less 0.5 s, so a slow `decide` makes the floor time out — a refusal. A `jq` that is
   present but broken makes master's `deny` print nothing (an allow), but the branch's own `deny` has the same
   dependency and master had it too: not worse.
4. **Rule mapping in the hook.** `floor` and `floor-not-run` both map to a `deny` (`:343-347`), and an unknown rule
   falls to `*) deny`. A multi-line master reason still matches `"0:deny "?*" "?*` (bash `*` matches newlines).

## Findings

### R6-F1 — Low — a payload holding TWO JSON documents is judged on a different command than master's hook judged

`.claude/hooks/block-default-branch-push.sh:235` reads `jq -er '.tool_input.command | strings'`; master reads
`jq -r '.tool_input.command // ""'`. On a stream of two JSON documents whose first `command` is a NON-string,
master prints that value's JSON text into `cmd`; the branch's `strings` drops it and `-e` succeeds on the second.

Repro (payload file `r6/p_multidoc.json`, fixture clone on `feat/x`):

```
{"tool_input":{"command":["hookspath"]}}
{"tool_name":"Bash","tool_input":{"command":"git push origin feat/x"}}
```

Master: **deny** (rule 3, `hookspath` in the normalised text). Branch: **allow**.

Why it is NOT a BLOCKER: it is not a command. Claude Code delivers exactly one JSON object per PreToolUse call,
so this input is not producible through the channel the hook guards, and in it the only command bash would run is
the feature push the branch allows; master's refusal comes from text that is not a command at all. It is a
difference in the payload contract, not in any command's verdict. Fix (optional, one token): `jq -ser 'if length
== 1 then .[0].tool_input.command | strings else empty end'`, i.e. refuse anything that is not exactly one
document — strictly tighter than both hooks.

### R6-F2 — Low — the equivalence case exercises the floor through only three command classes

Wrapping `floor` to log every refusal during `--self-test` shows the floor alone is load-bearing for 12 corpus
commands, all in three classes: a redirection target (`git push origin feat/x > master`, `2>`, `>>`, `<`,
`> --force`, `> -f`, `> --no-verify`, `-o x > master`, `--push-option=x > master`), an option value
(`git push -o x master`), and a `-c` value git runs (`core.editor=…`, `core.pager=…`). A floor bypass keyed to
any OTHER class (say, `verdict` calling the floor only when the text holds `>`, `-o` or `-c`) would leave the
equivalence case green, because the corpus has no decide-allows/master-refuses member outside those classes.

This does not weaken the guarantee — "no worse than master" rests on the four lines of `verdict`, and the two
mutations "the floor is removed" and "`main` prints `decide`" pin those. The equivalence case proves the property
over the corpus only, and the corpus reaches the floor through three classes; the commit's "261 compared, 0
allowed" should not be read as more than that. Filed-grade, not a fold. Fix: a case
that calls `verdict` with a stub `floor` that always refuses, over every corpus command `decide` allows that holds
a push word, and asserts each is refused — that tests the WIRING for every class, independent of whether master
happens to refuse it.

## How the 18 flagged lines were judged

Every flagged id is a line of MASTER's hook that the branch's hook no longer has: master's self-test probe
expecting an unbalanced quote to ALLOW (`:117`, now a deny — stricter), master's `jq -r … // ""` read with its
`|| echo ""` fail-open (`:129`, now `jq -er … | strings` that refuses unreadable input — stricter), and master's
rule 2 / rule 3 / rule 1 text matches and messages (`:163-207`, `:268-273`). Those rules were not deleted: they
run verbatim as the floor, `scripts/push-floor-master.sh`, whose blob equals master's current hook
(`ddb129b5`), and `verdict` runs it on every command that `decide` allows and holds a push word — a superset of
the commands master's trigger acts on (refutation 1 above). So on each path the branch refuses everything master
refused — with ONE exception, on id `2d51171ccc52` (`:129`, the payload read): R6-F1's two-document payload is
refused by master's read and allowed by the branch's. It is answered below as a finding because the answer rule is
literal ("refuses everything master refused on that path"); it is NOT a BLOCKER under this round's definition
(not a command, and not producible by Claude Code, which sends one JSON object), so the verdict stays CONVERGED.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: finding: a hook payload of TWO JSON documents whose first command is a non-string holding hookspath, the second a feature push, is refused by master (its jq read concatenates both) and allowed by the branch (strings drops the first) — R6-F1, not producible by Claude Code, not a BLOCKER
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
