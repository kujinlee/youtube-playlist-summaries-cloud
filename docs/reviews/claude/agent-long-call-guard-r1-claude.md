Reviewed head: d41eb9b9e42189cc30dca1d3adda3c9e8dcc6e38

# PR #468 — agent-long-call-guard, round 1, Claude half

**Subject:** `git diff origin/master...d41eb9b9` (backlog #455). The hook is `scripts/check-agent-long-call.py`,
launched by `.claude/hooks/agent-long-call.sh` through `run-hook.sh`, and registered under the `Bash` matcher in
`.claude/settings.json`.
**Method:** I sent about 70 crafted payloads through the real launcher (`bash .claude/hooks/agent-long-call.sh`),
with the `BASH_*` environment stripped and then set. The probe script is in the scratchpad (`r468/probe.py`),
not in the repo. I ran the self-test and the scoped mutation sweep, and made 5 hand mutations in a throwaway
copy. I statically read the Claude Code 2.1.309 binary for how the hook input and the Bash timeout are built.
Nothing was committed, and no settings file was touched.

## Verdict on the claim

| Clause | Result |
|---|---|
| never blocks a main-session call | **HOLDS.** With no `agent_id`, `agent_id: ""`, `" "` or `123`, and an `agent_id` inside `tool_input`, the payload `gh pr checks 1 --watch; sleep 900` with `timeout 600000` → allow. A broken checker exits 1 (non-blocking), never 2. |
| denies every direct foreground form over 270 s | **HOLDS for the bound that matters.** The timeout rule is the real bound (see F1): `timeout` 270000 → allow; 270000.5, 270001, a string, `null` or `true` → deny; `BASH_DEFAULT_TIMEOUT_MS=300000` with no timeout → deny. The `sleep` and watch matchers have gaps (F3), but every gap is still capped by the timeout rule. |
| unreadable payload is never a wedge and never silent | **HOLDS, with one wording gap (F2).** Payloads `""`, `"  "`, `{bad`, `[1]` and `null` → exit 1 with `NOT CHECKED` on stderr. |
| each self-test case fails when its named behaviour is removed | **HOLDS.** 37/37 pass. `check-plan-code.py --mutate . --only scripts/check-agent-long-call.py` → 21/21 killed, each attributed to the case it names. Some clauses that no case names are untested (F4). |

## Findings

**F1 — Low, FILE, not fix-induced.** `scripts/check-agent-long-call.py:27-29`. The docstring says *"a call killed
at its timeout has done no work"*. In 2.1.309 a foreground call that reaches its timeout is **moved to the
background**, not killed. I saw this happen in this review: my own teammate Bash call returned *"Command did not
complete within its 120s timeout and was moved to the background (ID: b57cy7h72)"*, and the command went on to
finish. The bound argument still stands, and it is stronger than stated: the turn is released at the timeout. One
consequence should be said in the docstring. Under the default 120 s timeout, a `sleep 300` or a `--watch` never
blocks past 120 s, so those two rules deny calls that would NOT expire the cache. They are kept because the
backlog row's falsifier requires them. Fix: correct the sentence.

**F2 — Low, FILE, not fix-induced.** The docstring at :34-35 and the launcher comment say an error in the rules
becomes *"the same non-blocking NOT CHECKED"*. RAN: `BASH_DEFAULT_TIMEOUT_MS=inf`, command `make` → rc 1, and
stderr is a raw `Traceback … OverflowError`, from `int(t)` at :116. The launcher only maps the exit code. It never
prints `NOT CHECKED`. The failure is visible, so the claim is not broken, but its message is not the one
documented. The env parse also differs from the harness. The binary's `fde()` takes `yu()` (parseInt-like) and
falls back to 120000 when the value is NaN or not above 0. The hook uses `float()`, so `"1e6"` → hook DENY where the
harness gives 1 ms, and `"300000ms"` → hook reads 120000 (allow) where the harness gives 300000. `timeout: 0` or
`-1` → the hook reads 0, while the harness treats a non-positive value as unset (`N3n`), so with a large
`BASH_DEFAULT_TIMEOUT_MS` that is a missed deny. `BASH_MAX_TIMEOUT_MS` (a clamp) is not read, so a value of 270000
or less false-denies an explicit `timeout: 600000`. Neither variable is set in this repo or in
`~/.claude/settings.json` (checked). Fix: wrap `decide` in `main` and print NOT CHECKED, and parse the env the
way the harness does (`int`, ignore ≤0 or invalid, `timeout ≤ 0` → default).

**F3 — Low, FILE, not fix-induced: matcher gaps.** These are **allowed** although they block (each RAN, subagent,
no timeout): `{ sleep 300; }`, `! sleep 300`, `time sleep 300`, `command sleep 300`, `env sleep 300`,
`/bin/sleep 300`, `timeout 600 sleep 300`, ``echo `sleep 300` ``, `sleep 1e3`, `sleep 300>/dev/null` (the
lookahead does not admit `>`), `gh -R o/r pr checks 12 --watch` (a global flag before `pr`), and
`while ! gh pr checks 1; do sleep 30; done` (an unbounded poll loop with no long sleep). Bound (1) at :37-39
states `bash -c` and scripts. Its definition of a command position implies the `{` `!` `time` forms, but not
`1e3`, `>`, `-R` or the loop. All of them are capped by the timeout rule (F1), so none of them expires the cache;
only the advice is lost. These are **denied** although they do not block (false deny): a heredoc or commit
message with `sleep 600` at the start of a line (`cat <<EOF\nsleep 600\nEOF` → DENY), and
`gh pr checks 12 --watch=false` → DENY. An agent that writes a script by heredoc gets a misleading refusal.
Fix: state the gaps in bound (1). For the heredoc case, a remedy line saying "use the Write tool" is enough.

**F4 — Low, FILE, not fix-induced: untested named clauses.** Hand mutations in a copy: dropping `then`/`else` from
`CMD_POS` → 37/37 still pass. Dropping `(` → 37/37. Dropping the `isinstance(ti, dict)` guard at :134 → 37/37,
and a non-object `tool_input` then raises at `ti.get` (exit 1, not a decision). Dropping `\n` → 1 red (killed),
and making `is_number` always true → red (TypeError). Fix: add one case each for `then sleep 300`,
`(sleep 300)` and `tool_input: "x"`.

**F5 — Low, FILE, not fix-induced: rollout noise.** The hook has no `if`, so it runs on **every** Bash call. That
includes the main session's, at about 63 ms each (5 calls measured in 0.316 s). `run-hook.sh` runs the copy in
the cwd's checkout. A worktree branched before this merge has no `agent-long-call.sh`, so every Bash call there
gets `run-hook: NOT RUN agent-long-call.sh` at exit 1. That is a non-blocking error the UI shows on each call;
3 of the 4 worktrees that exist now lack the file. This is documented launcher behaviour (L5), and it fades as
worktrees are rebased, but this is the first un-filtered hook on the busiest matcher. Fix: name it in the PR body.

## The extra question: does an in-process teammate's PreToolUse payload carry `agent_id`?

**ESTABLISHED STATICALLY from the 2.1.309 binary (strings), not by a live capture.** The chain:
1. The base hook input builder `$u(e,n,r,s)` returns `{session_id, transcript_path, cwd, …, permission_mode,
   agent_id: s?.agentId, agent_type: h, …}`. Here `s` is the tool-use context, and `h = s?.agentType ?? lA()`.
   The schema text reads: *"Subagent identifier. Present only when the hook fires from within a subagent … Absent
   for the main thread, even in --agent sessions"*.
2. `spawnInProcessTeammate` sets `resumableAgentId: o.resumableAgentId ?? h_(e)`. That is always set, and `h_`
   returns `` `a${name}-${hex}` ``.
3. `[inProcessRunner]` calls the shared agent runner `LR({… override:{…, ...e.resumableAgentId&&{agentId:
   e.resumableAgentId}}})`.
4. Inside `LR`, `ge = K?.agentId ? K.agentId : h_()`, where `K` is the override. So every runner context has an
   id, and the child tool-use context is built with `QIr(s,{…, agentId: ge, …})`.

So a teammate's tool calls run with `toolUseContext.agentId` set. The hook input reads exactly that field, the
same one the builder measured for plain and named subagents. The guard **applies to teammates**. The weak link is
step 4 → step 1: I assume the PreToolUse dispatch passes that same context as `$u`'s 4th argument. The builder's
live `claude -p` capture of a plain subagent shows that this holds for a subagent run by `LR`.
**Cheapest live check after merge:** have a named teammate run `sleep 300` with `run_in_background: false`.
The expected result is `⛔ REFUSED (backlog #455)`. A plain `echo $?` gives no signal. I did not run it, because
this session's settings come from master, which lacks the hook, and I was told not to edit them.

## Not covered, and whether the PR says so

`bash -c` and scripts: said, at :38-39. A foreground Agent call: said, at :40. Monitor: said. The F3 forms and the
F5 rollout noise: not said.

No BLOCKER: no wrong result goes against the cache goal or the main session, and every finding is FILE-grade.

VERDICT: CONVERGED
