<!-- codex-review: model=gpt-6.1-sol -->

- **MAJOR — `scripts/check-idle-stop.py:187`: recent files falsely establish running work.** Input: `background_tasks: []`, assistant text `"Starting X now."`, no usage/pause exception, CI complete, and an abandoned worktree containing a README touched 30 seconds ago. Result: **ALLOW**, although nothing runs. A newly checked-out idle worktree also qualifies; the scan includes the orchestrator’s own worktree.

- **MAJOR — `scripts/check-idle-stop.py:243`: quoted questions bypass the guard.** Input: `{"background_tasks":[],"last_assistant_message":"The test fixture contains \"Ready?\" Starting X now."}`, with quiet worktrees and completed CI. Observed: **ALLOW**. The question expression checks punctuation, not whether the assistant asks the owner anything.

- **MAJOR — `scripts/check-idle-stop.py:160`: missing task status counts as running.** Input: `{"background_tasks":[{"id":"finished-job","type":"shell"}],"last_assistant_message":"Starting X now."}`. Observed: **ALLOW**. Unknown or absent status supplies no evidence that a task is live.

- **MAJOR — `scripts/check-idle-stop.py:266`: unavailable observations disable enforcement.** Input: empty tasks, quiet worktrees, `"Starting X now."`, and injected `gh=(-1,"gh could not run (FileNotFoundError)")`. Observed: **NOT CHECKED**, exiting 1 and allowing the idle stop. Missing `background_tasks` and malformed payloads likewise allow it. These documented exceptions defeat the requested false-allow criterion.

- **MAJOR — `scripts/check-idle-stop.py:269`: legitimate completed-work answers are blocked.** Input: owner asks whether work is finished; assistant replies `"Everything is finished and merged."`, tasks empty, worktrees quiet, no open pending CI. Observed: **BLOCK**. The next `stop_hook_active:true` stop passes without launching anything, so the mechanism both interrupts legitimate completion and permits an unchanged idle continuation.

- **MAJOR — `scripts/check-idle-stop.py:121`: transcript reads can exceed the hook timeout before exceptions are evaluated.** Input: an otherwise valid payload with `stop_hook_active:true` and `transcript_path` naming a FIFO with no writer. Blocking `open()` never reaches `decide()`; the configured 10-second timeout terminates the hook. Neither the byte cap nor the exception handler bounds this read. The filesystem walk at line 183 also has no deadline.

- **MAJOR — `scripts/check-idle-stop.py:108`: malformed transcript records crash the hook and allow idle stops.** Input: valid idle payload whose transcript contains the JSONL record `[]`. Observed: `AttributeError: 'list' object has no attribute 'get'`. The shell wrapper maps this failure to nonblocking exit 1.

- **MAJOR — `scripts/check-idle-stop.py:395`: replay and mutation coverage miss production failures.** The fixtures genuinely build temporary directories, set file mtimes, inject clocks/CI, and initialize a Git repository for `main()`. However, the second replay is **02:29**, not the requested **02:28**; it runs through `decide()` only. The 02:24 replay reaches injected `main()`, but neither replay exercises the shell launcher, actual `run_gh()`, or timeout behavior.

  Requested results:
  > 47/47 self-test cases passed

  > OK — delivered scripts mutated: 1 file(s), 48 mutation(s), 48 killed, 48 attributed to the case each names, 0 survivor(s) — measured over ONLY scripts/check-idle-stop.py — a DIAGNOSTIC slice, not the gate

  Own mutation, applied only in memory: remove `"failed"` from `TERMINAL`. Result:
  > 47/47 self-test cases passed

  Concrete surviving failure: `background_tasks:[{"id":"done","type":"shell","status":"failed"}]` becomes running work and allows the stop.

VERDICT: NOT CONVERGED
