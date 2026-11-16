Reviewed head: 39c468cc46405aad6d08639046d93efe4206c6e9

# Round 3: `idle-stop-guard`, Claude adversarial half

Subject: `scripts/check-idle-stop.py`, `.claude/hooks/check-idle-stop.sh`, the Stop registration (backlog #663).
Mandate: refute that the guard is ready. Look first at defects the r2 fold (`39c468cc`) introduced, then at any
remaining way the 02:24/02:29 replay is ALLOWED.

## Gates run

- `python3 scripts/check-idle-stop.py --self-test` on HEAD, last line: **`93/93 self-test cases passed`** (2.4 s).
- **The real corpus, replayed through the real `last_tool_asked`.** I took every `stop_hook_summary` record in the
  82 transcripts under `~/.claude/projects/<this project>/`, which is 3,146 real Stops. For each one I passed in
  the 2 MiB that preceded it. Results: **False 3,142, True 4, None 0.** The 4 True stops are all the owner's
  "clarify these questions" rejection, and the assistant then asked "What would you like to clarify?" No ANSWERED
  card was let through, and no real tail read as unreadable. So in this corpus the r2 split, torn-line and
  catch-all changes cause no false "unreadable" blocks.
- **The usage cache, fuzzed.** I sent `usage_stop` the inputs `1e309`, `1e400`, `10**400` ints, `NaN`, `true`,
  `-1e300`, `[1]`, `"x"`, `null`, `{"rate_limits": []}` and `{"five_hour": []}`. Every one returned `None`. None
  of them raised, so none can crash the hook into the launcher's allowing exit 1.
- **(b) on the real tree.** `moved_worktrees` over the 41 real worktrees took 0.11 to 0.58 s against the 1.0 s
  budget. The per-file deadline does not cause false "unread" blocks here.
- **Wedge search.** `decide` returns ALLOW at `stop_hook_active is True` before it reads anything else, and the
  launcher maps every exit except 2 to 1. I found no input that blocks a continuation stop. Wedge direction:
  **none found.**

## My own mutations: temp copies under the scratchpad, never in place

| Mutant | Result |
|---|---|
| `ends = {idx[0], idx[-1]}` → `ends = set(idx)` (skip every torn line, not only the edges) | **killed**: the torn MIDDLE line case, 92/93 |
| `pending_ci`'s shape check `for k in ("__typename", "status", "state")` → `("status", "state")` | **SURVIVES**, 93/93 (Cm1) |
| `last, card, answered = b.get("name"), b.get("id"), False` → `last, card = b.get("name"), b.get("id")` (do not reset `answered` for a new card) | **SURVIVES**, 93/93 (Cm2) |

Neither surviving mutant is in `scripts/mutations/check-idle-stop.json`. The manifest has a different mutant at
line 150, `last or b.get("name")`.

## Findings

### CB1, BLOCKER: the pause marker lasts 24 h, so last night's "stop until 02:30" exempts this morning's 02:24 replay, and the block message tells the agent to write that marker

- **Where:** `scripts/check-idle-stop.py:109` (`PAUSE_MAX_S = 24 * 3600`), `:210` (`paused`), `:334`
  (`pause = paused(main, now)`, checked before any signal), and `:365` (the refusal text: *"if the owner paused
  the work — touch .claude/paused in the main checkout"*).
- **Concrete input:** the real chronology. On 11-15 at 05:31 the owner said *"stop working until next early
  morning (say 2:30 am)"*, which is the instruction the daily-wake cron prompt quotes. If the orchestrator
  records that pause the way the guard's own message tells it to, `.claude/paused` gets an mtime of 11-15 05:31.
  At 11-16 02:24 the marker is 20 h 53 min old, which is under 24 h.
- **Observed** through `main()`, with a real git checkout, `background_tasks: []`, no worktrees, a `gh` answer
  showing CI complete, and the payload `"Now starting backlog #657."`:
  - with no marker: `(2, '⛔ IDLE STOP REFUSED: nothing is running …')`
  - with the 05:31 marker: **`(0, '')`, ALLOWED, silently.**
- **Why it is the guard's own defect:**
  - The daily routine is "pause in the evening, wake by 02:30", and the wake turn is exactly the turn #663 was
    filed for. A pause marker that outlives the wake switches the guard off at the replayed hour.
  - Nothing deletes the marker. A grep of the repo for `claude/paused` finds only this script, the backlog row
    and a dashboard entry.
  - The agent the guard polices is also the one taught to write the marker. After one block it can `touch` the
    marker, and that excuses every idle stop for the next 24 h. The guard reads state, but this piece of state
    is one the guarded agent can write itself, which is the self-satisfiable escape that backlog #48 rejected
    for prose.
- **Fix direction (a hypothesis, not tested):** end a pause at the next human or cron prompt. For example, the
  marker counts only when it is newer than the last `type: user` prompt record in the tail, and the 02:24 turn
  was opened by the wake prompt. Another option is an explicit expiry written in the marker, where an absent or
  unparseable expiry means no pause. Either way, the refusal should stop advertising the marker to the agent, or
  at least say that only the owner's words justify it.
- **fix_induced: no.** The 24 h pause and the instruction to write it date from the first build; r1 and r2 did
  not raise them. Component: pause-exception.

### Cm1, Minor: `pending_ci`'s `__typename` shape check is unpinned, so a malformed `__typename` can be dropped and the result flips from block to allow

- **Where:** `scripts/check-idle-stop.py:313`.
- **Concrete input:**
  `[{"number":1,"statusCheckRollup":[{"__typename":["StatusContext"],"status":"IN_PROGRESS"}]}]`
- **Observed:** HEAD returns `None` (unread, so block). The mutant without `__typename` in the check returns
  `[1]` (pending, so ALLOW), and it still passes 93/93.
- XM4's own cases cover a bad status, state, rollup and check, but not a bad `__typename`. The clause is real but
  unwitnessed. Add the case above.
- **fix_induced: yes** (XM4's fold). Component: ci-signal.

### Cm2, Minor: the per-card reset of `answered` is unpinned

- **Where:** `scripts/check-idle-stop.py:173`.
- **Concrete input:** `go`, then `ask(q1)`, then `result(q1, "answered: Yes")`, then `ask(q2)`, then
  `result(q2, <REJECTED text>, is_error)`. That is two cards in one turn, the first answered and the second
  rejected with "clarify".
- **Observed:** HEAD returns `True` (exception). The mutant that does not reset `answered` returns `False`, and
  it still passes 93/93.
- The mutant fails toward blocking, so it is not an idle-stop ALLOW. But the clause that makes the exception
  follow the LAST card, which is XM1's whole design, has no case. Add the two-card case.
- **fix_induced: yes** (XM1's fold). Component: question-exception.

### Cm3, Minor: a transcript FILE that cannot be read is silently treated as "no card", and the refusal does not name it

- **Where:** `scripts/check-idle-stop.py:394` and `:362`.
- **Concrete input:** `transcript_path` is a FIFO, a missing path, a directory, or a file with mode 000.
  `read_tail` returns `None`, then `last_tool_asked(None)` returns `False`, not `None`.
- **Observed:** the stop is blocked. That direction is correct, but the reason leaves out *"The transcript could
  not be read, so the AskUserQuestion exception was not applied."* r2 added that sentence only for a record that
  cannot be parsed.
- An owner-rejected card in an unreadable transcript is blocked by a refusal that hides why the exception did not
  apply. That goes against the module's own "the reason names what could not be read". Fix: `read_tail`
  returning `None` for a payload that names a path should make `asked` None.
- **fix_induced: no.** r1 behaved the same way; r2 named one cause of unreadability and left this one out.
  Component: question-exception.

## Observations, not findings

- **A second torn-record rule.** `last_tool_asked` has its own torn-line policy: it skips the first and last line
  and skips a record that is not an object. `bounded_read.parse_jsonl` already defines one: it drops only a torn
  final record, and a record that is not an object is CANNOT RUN. The tail's cut first line is a real difference,
  but two policies for one rule will drift.
- **A misleading message.** When `pending_ci` rejects valid JSON of the wrong shape, the refusal says "unreadable
  JSON". "Unexpected shape" would be accurate.
- **A torn last line can let a stop through.** If an ANSWERED card's `tool_result` is the torn last line when the
  hook reads the file, it is skipped, the card reads as unanswered, and the stop is ALLOWED. This needs a read
  that races a partially written record. No case of it appears in the 3,146-stop corpus. The bound is stated
  here, not filed.
- **Other ways the replay could be allowed.** I found no remaining route besides CB1 that does not need real
  activity: a live background task, a worktree write in the last 10 min, or a started check on some open PR.
  Those are the stated bounds of (a), (b) and (c). The 02:24 transcript shows no background launch between 08:30
  and 10:35Z other than `CronCreate`.

## Thrashing classification

Two of the Minor findings are fix-induced, and each sits in a component that r2 also had a fix-induced finding
in: Cm2 in question-exception, after r2's XM1, and Cm1 in ci-signal. Both are untested clauses, not wrong
behaviour, but they were caused by r2's fold, so they are reported as fix_induced: yes. The BLOCKER CB1 is
**not** fix-induced.

```yaml
round: 3
subject: idle-stop-guard
half: claude
findings:
  - {id: CB1, severity: BLOCKER, fix_induced: false, component: pause-exception}
  - {id: Cm1, severity: Minor, fix_induced: true, component: ci-signal}
  - {id: Cm2, severity: Minor, fix_induced: true, component: question-exception}
  - {id: Cm3, severity: Minor, fix_induced: false, component: question-exception}
```

VERDICT: NOT CONVERGED
