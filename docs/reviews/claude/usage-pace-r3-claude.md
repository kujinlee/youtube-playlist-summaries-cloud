# Round 3 — usage-pace — claude

**NOT CONVERGED**

Subject: PR #446 (backlog #399), branch `usage-pace`. I reviewed the r2 fold `b37549ce..ccc5ed79` first, then the gate at `ccc5ed79`. My mandate was to refute this bet: *"no way to wake an agent at 90% or more without the override, and no cache content or file that silences a weekly REFUSE or stalls a prompt beyond the deadline."*

**Result: the bet is refuted on its first clause, measured end to end.** The caller-identity redesign holds against forgery: I could not make the main session look like a subagent. But the redesign also exempts every subagent, so a subagent can wake an idle sibling at 95% with no override.

```yaml
round: 3
subject: usage-pace
findings:
  - {id: C1, severity: High,   fix_induced: true, component: scope,      aim: deliverable}
  - {id: C2, severity: Medium, fix_induced: true, component: cache-read, aim: instrument}
  - {id: C3, severity: Low,    fix_induced: true, component: cache-read, aim: deliverable}
  - {id: C4, severity: Low,    fix_induced: true, component: scope,      aim: deliverable}
```

## Findings

### C1 — High — a subagent wakes an idle sibling at 95%, with no override (fix-induced: yes, component: scope)

`scripts/check-usage-pace.py:552` together with `sent_by_subagent` at `:453`.

The gate exempts any SendMessage that carries a top-level `agent_id`. Every subagent's call carries one. A subagent's message to a sibling is therefore allowed, and that message wakes the sibling. The docstring at `:77-79` names this as a BOUND. The bet says "no way to wake an agent", so the bound contradicts the bet. Either the bet is false, or the bound has to go.

**How I measured it.** I ran a throwaway `claude -p --model haiku` project on Claude Code 2.1.309, with a PreToolUse `*` hook that dumped its stdin to a file.
1. The main session spawned `probeA`. `probeA` ran `echo A-first` and finished.
2. The main session spawned `probeB`. `probeB` called `SendMessage {"to":"probeA","message":"please-run-your-wake-step"}`. Its hook input carried `agent_id: a638612a517f58c2c`.
3. `probeA` was resumed. Its next hook input was `Bash echo A-woken`, under `agent_id: a4101631eb4e48c34`. **The sibling woke.**

I then fed `probeB`'s captured payload to `python3 scripts/check-usage-pace.py --hook wake`. The cache held weekly 95% with a valid reset, `ALLOW_SPAWN_OVER_LIMIT` was unset, and no override file existed. The result was **rc 0 with empty stdout: ALLOWED.** The main session's captured payloads, which carry no `agent_id`, were DENIED under the same conditions.

**Why it matters here.** This repo runs long-lived teammates. The session I am reviewing from lists about 80 named agents. Any in-flight subagent that coordinates others can wake parked agents at 95%, and that is the expensive path the gate exists to close (69.5% of weighted usage). If `team-lead` is itself a teammate and not the main thread, every wake it sends is exempt. INFERRED: I did not determine which one `team-lead` is. A broadcast (`to: "*"`) from a subagent would wake all of them at once. INFERRED: I did not test broadcast delivery.

**The fix is a decision for the coordinator, not a mechanical change:**
- (a) Restate the bet as "no wake **from the main session**" and accept sibling wakes as a measured bound, or
- (b) Allow a subagent's message only when it is addressed to the reserved coordinator target. That means reading the recipient again, which is the r2 X1 hazard. So (b) is sound only if it is checked against the resolver's exact-name-first rule: a registered agent literally named `main` exists in this very session's agent list.

### C2 — Medium — surviving mutant: a non-daemon reader thread keeps the hook alive for the whole stall (fix-induced: yes, component: cache-read)

`scripts/check-usage-pace.py:304`.

I changed `daemon=True` to `daemon=False` in a copy of `scripts/` plus `.claude/`.
- `--self-test` still reported **247/247 passed**.
- `scripts/mutations/check-usage-pace.json` has no entry that touches `daemon`; `grep -c daemon` returns 0.

Under that mutant I injected a 30 s stall into `_read_now`, using `scratchpad/r3probe/stall-mut.py` with the `sleep` mode. `main()` returned after **1.01 s**, but the process exited after **30.09 s**. The deadline then bounds only the function, not the hook, which is the property X3 asked for. The suite's stall cases are in-process, so they can only see `main()` return and never see the process outlive it.

**Fix:** add a case that runs the checker as a child process with an injected stall, and asserts the child's wall time is under about 2 s.

### C3 — Low — the deadline's rationale refutes itself for the case it names (fix-induced: yes, component: cache-read; INFERRED, not reproduced)

`scripts/check-usage-pace.py:288-296`.

The docstring rejects `signal.alarm` because "a read from a regular file on a stalled disk does not [return EINTR]", which is an uninterruptible sleep. In that same state a daemon thread blocks **process exit**. The thread shares the fd table, so the stdout pipe is not closed, `run-hook.sh` keeps waiting, and the harness reads to its 30 s timeout. The thread therefore bounds the stall cases where alarm would also have worked, not the D-state case it cites. "Returns within `deadline` whatever the filesystem does" is true of the function and not of the hook.

What I measured: for an *interruptible* block, both a real `os.read` on an empty pipe and a `time.sleep`, the process exits at 1.06–1.08 s with the daemon thread. **I could not create a D-state read on macOS without FUSE, so the uninterruptible case is inferred.**

**Fix:** narrow the claim in the docstring to interruptible stalls, and name the uninterruptible one as a bound.

### C4 — Low — the main session cannot shut down, approve or subscribe at REFUSE (fix-induced: yes, component: scope)

`scripts/check-usage-pace.py:549-553`.

The gate ignores `tool_input` entirely. At 95% the main session is therefore denied all of these:
- `{"type":"shutdown_request"}`, so it cannot retire parked agents;
- `plan_approval_response`, so a teammate waiting on plan approval stalls. That is work in flight, which the docstring says "continues";
- a message-less `notify_when_idle` subscription, which the SendMessage contract says "costs that session nothing".

These follow directly from the code. I did not drive them live. A shutdown also costs a turn, so denying it may be acceptable. Either way, the docstring's "work in flight continues" should name the plan-approval case.

## What I VERIFIED, and what I INFERRED

| Question | Answer | Basis |
|---|---|---|
| Does a main-session SendMessage carry a top-level `agent_id`? | **No.** Two main-session SendMessage calls had neither `agent_id` nor `agent_type`. | VERIFIED: stdin dump, 2.1.309 |
| Does a subagent's SendMessage carry one? | **Yes.** Both subagent calls had `agent_id` and `agent_type`. | VERIFIED |
| Can the model set it? | **No.** The main session sent SendMessage with an extra `agent_id: "forged123"`. The call succeeded, the field appeared neither at top level nor in `tool_input`, and the hook input had no `agent_id`. | VERIFIED: one attempt. "Cannot" in general is INFERRED, since the harness builds the envelope and I tried only one route. |
| Is a `--agent` main session gated? | Not re-run. The suite case at `:1029` covers the shape. | NOT VERIFIED live |
| Teammates in a separate process (tmux / split-pane) | Such a teammate's own main thread would likely carry no `agent_id`. Its reports to the lead would then be DENIED at REFUSE, which is an over-gate that strands finished work. | INFERRED, not measured |
| Is there a wake path other than SendMessage? | The Agent tool in this version has no resume parameter; a new Agent call starts fresh, and the spawn gate denies it at REFUSE anyway. SendMessage resumed a finished agent. A subagent's SendMessage is the open path (C1). | VERIFIED for SendMessage; Agent schema READ |
| Does the reader thread leak? | No for interruptible stalls: the process exits at about 1.07 s and the fd count is unchanged. Yes under the `daemon=False` mutant (C2). Probably yes for D-state (C3). | VERIFIED / VERIFIED / INFERRED |
| Does any cache content silence a valid weekly REFUSE? | None found. `10**400` and `-10**400` in five-hour, and NaN/Infinity literals, keep the weekly REFUSE; the suite holds those cases and they pass. A stalled, oversized or unparseable cache is CANNOT RUN, and the spawn/wake gates are **silent** on it: only the next prompt is loud. That is by design and is not counted as a finding. | RAN suite; READ `gate_output` |

## Latency

20 runs per row, piped stdin, direct `python3` (no `run-hook.sh`):

| Hook, cache | ccc5ed79 median / p90 | b37549ce median / p90 |
|---|---|---|
| prompt, 50% | 78.5 / 82.4 ms | 72.1 / 77.7 ms |
| prompt, 95% | 103.2 / 114.6 ms | 100.0 / 115.3 ms |
| wake, 95% | 110.6 / 131.3 ms | 101.0 / 117.1 ms |
| spawn, 95% | 110.4 / 144.9 ms | 101.5 / 120.4 ms |

That is about +6 ms on the common path, consistent with the `threading` import, and +9 ms at REFUSE. **No regression worth a finding.** The coordinator's 88–110 ms reproduces within noise.

## Commands run

- `python3 scripts/check-usage-pace.py --self-test` → **247/247 passed** (Python 3.14.4).
- `python3 scripts/check-plan-code.py --mutate . --only scripts/check-usage-pace.py` → **85 mutations, 85 killed, 85 attributed, 0 survivors** — the tool's own words: "a DIAGNOSTIC slice, not the gate". C2 is a survivor that is **not in** the manifest.
- Two throwaway `claude -p --model haiku` runs in `scratchpad/r3probe`. I did not edit, stage or commit in the worktree, I did not read `.claude/plans/`, and I made no edit to `~/.claude`. The harness wrote its own session transcripts for the probe's directory under `~/.claude/projects/`; I left them in place rather than delete inside `~/.claude`.

**NOT CONVERGED** — 1 High (C1), 1 Medium (C2), 2 Low (C3, C4).
