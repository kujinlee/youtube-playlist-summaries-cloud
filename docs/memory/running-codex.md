---
name: running-codex
description: "FIRES-WHEN: about to dispatch, wait on, or fall back from a Codex review — run it through scripts/codex-review.py from the coordinator; a \"timeout\" is almost always MY --timeout (DOUBLE it; default 900s, big reviews 2700-3600); the prompt says \"your final message IS the review; write no file\""
metadata:
  type: feedback
---

**The rule as it stands:**
1. **Run Codex only through `scripts/codex-review.py`**, from the coordinator's Bash with `dangerouslyDisableSandbox: true`,
   prompt via `--prompt-file` (never a shell argument). The wrapper already closes stdin (`stdin=subprocess.DEVNULL`)
   and passes `-s danger-full-access` so the reviewer can reach the Docker socket. Do NOT dispatch the
   `codex:codex-rescue` subagent here — nested `codex exec` fails with `Operation not permitted` in its sandbox.
2. **Scale `--timeout` to the job before dispatching.** Default 900 s (verified 2026-11-14). A review that sweeps a
   2,000-line file or runs a mutation harness needs `--timeout 2700`–`3600`; compare with what the Claude half takes.
3. **On a timeout: DOUBLE it and re-run ONCE.** Fall back to a Claude adversarial half only if it times out again at the
   larger budget or fails for a non-timeout reason (auth, HTTP 4xx/5xx, usage limit). A timeout is a statement about MY
   budget, not about Codex being unavailable — user, 2026-09-16: *"we had it before and doubling timeout limit
   resolved"*. The wrapper buffers, so a 45-minute review is silent for 45 minutes; a quiet file is not a hang.
4. **Every prompt carries "your final message IS the review; write no file"** (and "REPORT only; do not touch GitHub",
   see [[a-reviewer-told-findings-are-filed-files-them]]). After the run: `grep 'verdict: gate_ran' <task output>` and
   `git status` the worktree BEFORE staging; never `| tail -2` the wrapper output (it dropped the capture path).
5. **If a review says it could not run the suite, the gate did not run** — whatever the exit code.

**Why:** the halves catch different classes ([[dual-review-what-it-catches]]); every self-inflicted "Codex unavailable"
merges a branch on single-half review.

**How to apply:** the canonical contract (exit codes 0/1/2/3, `--review-id`, `--out` outside the repo) is in
`docs/plugins.md` → Code Review; read it there rather than from here. See [[a-hang-is-not-a-diagnosis]],
[[check-the-assumption-not-just-the-code]], [[seed-manifest-122-merged]], [[dev-process]], [[process-conventions]].

## History (merged from `codex-timeout-raise-it-dont-fall-back`, `codex-sandbox-run-from-coordinator`)

- **2026-07-09:** a Task-1 review hung 1h40m on `Reading additional input from stdin...` — `codex exec` blocks on an
  open stdin pipe in a background Bash. Fixed by `< /dev/null` (now `stdin=DEVNULL` in the wrapper). GNU `timeout` does
  not exist on macOS (exit 127). Also found: the `codex:codex-rescue` subagent cannot run nested `codex exec`.
- **2026-08-07 (round 7):** two independent sandboxes — `dangerouslyDisableSandbox` governs launching; `codex exec`
  applied its own `workspace-write` policy, could not open `docker.sock`, reported `0/35 mutations … SQL did not run`,
  and reviewed by reading while the gate reported success. Fix: `-s danger-full-access`; `trust_level = "trusted"` does
  not substitute.
- **2026-09-16 (PR #311):** three rounds, three "timeouts", each ≈15 min after dispatch (the 900 s default exactly)
  while the Claude half took 40–60 min. I fell back three times; the branch merged on single-half review with
  `REVIEW GAP: codex` in all three round docs. `plugins.md` also carried "treat a quiet output file as a hang after
  ~2–3 minutes" — both paragraphs corrected.
- **PR #312 (`08af5c3b`):** at `--timeout 3600` Codex completed first try and found two live defects three Claude rounds
  missed — a filename carrying markup into `/src/`'s `<title>`/`<header>`, and `/secret%2eenv` bypassing a rule
  `/secret.env` obeyed. A different habit of attack (hostile FILENAME, ENCODED spelling), not a deeper one.
- **2026-10-26:** without the "write no file" line, a Codex round wrote its review as a FILE; the wrapper recorded
  `gate_ran=false` and I read the self-written file as the gate until `check-review-rounds` went red. The next round
  wrote a file AND a backlog row into the worktree, and my commit staged the row unread.
