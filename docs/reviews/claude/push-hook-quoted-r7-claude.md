Reviewed head: 9ac8a5d6409f1b4140d046456a8ca98e2b393b41

# Round 7 — `push-hook-quoted` (PR #542, backlog #428) — Claude half, SCOPED (past the round cap)

Subject: the round 6 fold `dd70637d` (the one-document payload read and the floor-wiring case), then the merge of
master `9ac8a5d6`. The merge touches none of the hook, the detector, the floor or the mutation manifest. The only
file it changes in scope is the r6 coordinator record (`git diff --stat 48335bf1 9ac8a5d6`).

BLOCKER (the r5 coordinator's narrowed definition): a command the branch's hook ALLOWS that master's hook REFUSES, or
a path where the hook allows without having decided. **None found.**

## What was run (head `9ac8a5d6`, macOS, 12 cores)

| Check | Result |
|---|---|
| `bash .claude/hooks/block-default-branch-push.sh --self-test` | **65/65**, 14.1 s |
| `python3 scripts/push-command.py --self-test` (load average ~54) | **352/352**, 53.3 s |
| Same, under 24 extra busy-loop processes (load 21 → 71) | **352/352**, 111.9 s |
| Branch hook vs master's hook (`git show origin/master:…` → temp file, blob `ddb129b5`) over 43 payload FILES | **0 looser**. 17 identical, 26 branch-stricter |
| Branch hook vs the round 5 hook (`dd70637d^`) over the same 43 files | Differs on **exactly 3**, all multi-document. Each is r5 allow → branch deny |
| The new mutation, alone, in a `stage_tree` copy | rc 1; `expect` matches exactly one red case |

## 1. The one-document read: refuted? No

`jq -ser 'if length == 1 then .[0].tool_input.command | strings else empty end'`, with `|| deny`. The exit status
of `cmd="$(…)"` is jq's, the last stage of the pipe. `-e` exits 4 when nothing is produced. A parse error exits 5. A
type error (`.tool_input` on a number or an array) exits 5. Every one of those reaches `deny … NOT CHECKED`.

**The read refuses all of these.** For each, the branch's verdict follows, with master's verdict in parentheses:
- an empty payload: deny (master: allow);
- a whitespace-only payload: deny (allow);
- two documents, newline-separated: deny (allow);
- two documents with nothing between them: deny (allow);
- R6-F1's non-string `hookspath` document followed by a feature push: deny (deny);
- `ls` followed by a push to master: deny (deny);
- the JSON documents `null`, a bare string and a number: deny (allow);
- an array-wrapped object: deny (allow);
- a command that is a number, null, `false`, an array or an object: deny (allow);
- a missing command: deny (allow);
- `tool_input` that is a string: deny (allow);
- a truncated document: deny (allow);
- a document followed by garbage: deny (allow);
- a lone `\ud800` surrogate: deny (allow). jq 1.7 rejects it as a parse error, exit 5.

**It still allows normal single-document payloads, exactly as round 5 did.** These were allowed:
- a feature push;
- a pretty-printed document with trailing blank lines;
- unicode, raw and quoted;
- a 200 KB command;
- a duplicate `command` key, last one a feature push. jq takes the last, as master does, and a last key pushing to
  master is refused by both;
- a BOM;
- an escaped NUL;
- a command with trailing newlines;
- an empty-string command, as master allows it.

The multi-line, unicode and large commands that push to master were refused, as master refuses them. Some feature
pushes were refused by both the branch and round 5. That is the detector's closed language refusing outside syntax,
not the read:
- `\`-newline continuations;
- heredocs;
- CRLF;
- an unquoted ASCII-escaped `é`;
- invalid UTF-8.

On every single-document payload the branch and round 5 agree. The fold changes the verdict only on multi-document
payloads, and only to deny.

Against master, the read cannot loosen. On one document with a string command it hands the detector the identical
string master's `jq -r '.tool_input.command // ""'` produced. On anything else it refuses, where master either judged
the same text or fell back to `""` and allowed.

## 2. The flake — cause NOT reproduced; both possible routes refuse; it cannot forge a mutation kill

**The recorded failure.** I read the fold agent's transcript (`subagents/agent-aa2cfff272c6e7565.jsonl`, 05:27:31 to
05:31:07Z):
- three sequential runs, with no concurrent edit to the worktree by any agent in that window (scanned across every
  transcript in the session);
- run 3 took 69.4 s against 57.3 and 87.4 s, and recorded
  `[FAIL] hook: C-F2 — a feature push, then --title "Do not push to master", is allowed: got 'deny' want 'allow'`;
- load average 7.41 at the end, with 197,580 pages (≈ 770 MB) free;
- the Codex run had been OOM-killed at 21:10 the same evening.

The deny REASON was not captured: the case compares only `[0]`.

**Which routes can turn this command into a deny?**
- `decide` is deterministic. 300 `PYTHONHASHSEED` values (0–299) through the delivered hook all allow, so set
  ordering is not the cause.
- Master's floor script reads only `git remote`, `symbolic-ref` and `rev-parse` in the self-test's private world. It
  has no clock, no network and no randomness.

That leaves the two time-bounded paths in `scripts/push-command.py`:
1. **`floor-not-run`.** `floor()` gets `budget = max(0.1, DEADLINE_S - 0.5 - elapsed)`, which is about 2.5 s, since
   `decide` takes about 0 ms. A floor past that budget is killed by process group, and the result is
   `deny floor-not-run master's rules did not finish in …`.
2. **Exit 142.** SIGALRM at `DEADLINE_S = 3.0` s, which the hook maps to deny.

**Shrinking the deadline in a copy reproduces the failure exactly.** I used an instrumented copy under the
scratchpad, with `R7_DEADLINE`:

| Deadline | Floor budget | Result |
|---|---|---|
| 0.70 s | 0.200 s | the floor took 0.197–0.207 s: `allow` |
| 0.62 s | 0.120 s | the floor took 0.147 s: `deny floor-not-run master's rules did not finish in 0.1 s` |
| 0.55 s or less | 0.100 s | `deny floor-not-run` |

This is the observed symptom: an allow case reading `deny`.

**Measured timings.** The in-deadline time is the floor alone, so `pre-floor` is 0.000 s.

| Condition | Floor per call | `decide` main, wall | Delivered hook, wall |
|---|---|---|---|
| Load ~4, 20 calls | median 0.113, max 0.491 | median 0.200 | median 0.269, max 0.507 |
| +36 busy loops (load → 30), 10 calls | median 0.285, max 0.891 | median 0.607 | median 0.747 |
| +150 busy loops (load → 148), 6 calls | median 0.363 | median 1.93 | median 2.22, max 2.49 |
| +150 busy loops, instrumented, 5 calls | 0.55–1.07 in-deadline | — | 2.5–3.4 |

In the last row, most of the wall time is interpreter start, which runs before `_arm_deadline` and so falls outside
the deadline.

**The budget against the measurement.** The floor's budget is about 2.5 s and the whole deadline is 3.0 s. The floor
needs about 0.11 s, so the headroom is about 22×.

**CPU load does not explain the flake.** Even at load ~148 the floor stayed at or under 1.07 s, and a full
self-test at load ~70 passed 352/352. Load 7.4 is about a sixth of the contention I applied.

**My untested inference is a multi-second stall.** The floor spawns about 20 short processes (bash, grep, sed, tr,
three gits, jq). Memory-pressure paging could stall them for seconds, and the session's 21:10 OOM-kill and roughly
770 MB free fit that. I did not induce memory pressure: the brief says memory is low, so I did not try.

**In production it fails closed.** Both routes print a `deny … NOT CHECKED`-class refusal, which is a false
refusal, and re-running the command clears it. It is not a BLOCKER.

**CI.**
- `ci.yml:422` runs the self-test once, so the same stall would red that job until it is re-run. On GitHub runners
  that needs a stall of about 20× the floor time.
- The mutation sweep attributes a kill by the NAMED `expect` cases only (`check-plan-code.py`, "the NAMED ones, not
  every red case"). **0 of the 108 `expect` entries name a hook "is allowed" case**, so a flipped allow case cannot
  forge or misattribute a kill.
- The reverse direction exists, but needs the same stall. Take a hook-deny case killed through the floor path: a
  `floor-not-run` deny would turn it green, so the mutant reads as a survivor and the sweep goes red. The direct floor
  case at line 1144 (`budget=2.5`) would also flip.

### R7-F1 — Low — a hook case that flips to `deny` does not say WHY, so the r6 flake cannot be diagnosed

The flake is fail-closed and was not reproduced (section 2), but the evidence that would have named its cause was
thrown away. `_hook` returns `(decision, reason)`, and the case list compares `_hook(work, cmd)[0]` alone. A
`floor-not-run … did not finish in N s` and an exit-142 deny would have been told apart at a glance.

Fix: compare the decision, but print the reason on a mismatch. For example, `case(name, d, want)` with
`d = dec if dec == want else f"{dec} ({why[:120]})"`. That costs 0 s.

Related, cosmetic and also fail-closed: `max(0.1, …)` can grant the floor more time than the alarm leaves, once
elapsed passes 2.9 s. SIGALRM then ends `decide` first, as exit 142, and the floor's process group is orphaned rather
than killed. That group is master's read-only hook. FILED-grade.

### R7-F2 — Low — the new mutation does not show the new case is NEEDED; a `&&`-keyed bypass does

Hand-checked alone in a `stage_tree` copy. I applied the manifest's own edit (anchor found once) and ran
`push-command.py --self-test` in the copy:
- rc 1, 349/352;
- the `expect` matches exactly one red case, `⭐ floor wiring … (r6 C-F2)`;
- the equivalence case is GREEN, as the commit says.

But two r5 cases also go red: `⭐ floor: a floor file that is missing REFUSES` and `⭐ floor: a floor file that is not
master's bytes REFUSES`. Their command, `git push origin feat/x`, holds none of `< > -o -c =`. So this mutant was
already dead before the new case existed, and its kill does not demonstrate that the new case adds coverage.

**A mutant that only the new case catches does exist.** I hand-checked it the same way: `… or "&&" in cmd:`, which
skips the floor for any command with `&&`. Result:
- rc 1;
- exactly ONE red case, `⭐ floor wiring … (r6 C-F2)`;
- the equivalence case and both r5 floor-file cases stay GREEN.

So the new case is genuinely load-bearing, and the manifest entry just does not prove it. Fix: re-key the entry, or
add a second one, to the `&&` bypass, and pin 108 → 109. FILED-grade. The attribution as committed is valid; this is
about the claim the entry was added to make.

## Loosening answers
LOOSENING-CHECK f090c90de19b: not a loosening
LOOSENING-CHECK 2d51171ccc52: not a loosening
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
