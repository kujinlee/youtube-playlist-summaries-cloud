---
name: running-codex
description: "FIRES-WHEN: about to dispatch, wait on, or fall back from a Codex review — ⭐⭐ Codex operationally: a \"timeout\" is almost always MY --timeout (DOUBLE it, default 900s, big reviews 2700-3600), and run it from the coordinator with dangerouslyDisableSandbox"
metadata:
  type: feedback
---

> Merged 2 memories, bodies kept VERBATIM. Former names (still referenced by other memories): `codex-timeout-raise-it-dont-fall-back`, `codex-sandbox-run-from-coordinator`

## codex timeout raise it dont fall back

⛔ **When `scripts/codex-review.py` reports `timed out — any partial message is an incomplete
review`, the FIRST move is to raise `--timeout`, not to fall back to a Claude stand-in.**

**The user's words, 2026-09-16: *"we had it before and doubling timeout limit resolved"*** — so this
is a RECURRING condition with a KNOWN fix, not a fresh diagnosis to make each time.

**The knob:** `scripts/codex-review.py --timeout <seconds>`, **default 900 (15 minutes)**
(`:666`). I had never passed it.

**Measured 2026-09-16 on PR #311:** three rounds, three "timeouts", each returning ≈15 minutes after
dispatch — i.e. every one hit the default wall exactly. The Claude half of the *same* review took
**40–60 minutes** each time. So the review was simply longer than the budget I gave it, and I
concluded from that that **Codex was unavailable** and invoked `docs/plugins.md`'s fallback three
times. That branch merged on **single-half review** as a result, with `REVIEW GAP: codex` recorded in
all three round documents — a real loss, because that file's own notes say the two halves catch
different classes.

**Why I got it wrong:** a timeout is a statement about MY budget, not about the other side. This
project already has [[a-hang-is-not-a-diagnosis]] for exactly this shape and I walked into it anyway,
because the wrapper's message *says* "timed out" and `plugins.md` lists a timed-out run under
"unavailable" — which is true only once the timeout is appropriate to the task.

**How to apply:**
- ⭐ **Scale the timeout to the JOB before dispatching.** A review that sweeps a 2,000-line file, runs
  a ~12-minute mutation harness, and applies dozens of mutations needs **45–60 min**
  (`--timeout 2700`–`3600`), not 15. Compare against what the Claude half takes for the same brief.
- **On a timeout: DOUBLE IT AND RE-RUN ONCE.** Only fall back if it times out again at the larger
  budget, or fails for a non-timeout reason (auth, HTTP 4xx/5xx, usage limit).
- ⚠ `plugins.md`'s *"do not wait, do not retry"* is about **not burning time on a genuinely absent
  reviewer**. It is not a licence to accept a self-inflicted deadline as evidence of absence.
- The wrapper is right to refuse a partial review — that behaviour is not the problem and should not
  be changed.

⭐ **WHAT THE RE-RUN BOUGHT, measured (PR #312, merged `08af5c3b`).** At `--timeout 3600` Codex
completed first try and found **two live defects on master** that three Claude rounds had swept past:
a filename carrying markup straight into `/src/`'s `<title>`/`<header>`, and `/secret%2eenv` bypassing
a path rule `/secret.env` obeyed. Neither is deeper than what the Claude halves found — they are a
**different habit of attack**: Claude tested hostile CONTENT and hostile PATHS exhaustively; Codex
tested a hostile FILENAME and an ENCODED spelling of a path already covered. That is what
`docs/plugins.md` means by *the two halves catch different classes*, and it is what a self-inflicted
deadline threw away three times.

⚠ **`plugins.md` had a SECOND paragraph giving the same bad advice** — *"treat a quiet output file as
a hang after ~2–3 minutes"* — and it survived the first repair because I fixed the paragraph I was
looking at. The wrapper buffers, so a 45-minute review is silent for 45 minutes. Both corrected.

See [[a-hang-is-not-a-diagnosis]], [[dual-review-what-it-catches]],
[[check-the-assumption-not-just-the-code]], [[seed-manifest-122-merged]].

## codex sandbox run from coordinator

> **⚠ CORRECTED 2026-08-07 — THIS NOTE COVERED THE OUTER SANDBOX ONLY, AND I TREATED IT AS THE CLASS.**
> There are **two independent sandboxes**. `dangerouslyDisableSandbox` governs whether *we* may launch
> the process. `codex exec` then applies its **own** Seatbelt policy to itself, defaulting to
> `workspace-write` — so in round 7 the reviewer could not open the Docker socket
> (`dial unix …/docker.sock: operation not permitted`), reported `0/35 mutations … SQL did not run`,
> and **reviewed by reading while the gate reported success**.
> Fix: `scripts/codex-review.py` now passes `-s danger-full-access` (verified). `trust_level =
> "trusted"` does NOT substitute — it governs approval prompts, not socket access — and no narrower
> mode works, because the socket lives outside every workspace root.
> **If a review says it could not run the suite, the gate did not run.** See `docs/plugins.md`.

Codex adversarial reviews must be run from the **coordinator (main loop)** via the Bash tool with `dangerouslyDisableSandbox: true`:

```
# run in a run_in_background:true Bash (dangerouslyDisableSandbox:true). NOTE: GNU `timeout` is
# NOT on macOS (exit 127 "command not found") and there's no gtimeout — use a bash watchdog:
M="$(python3 scripts/codex-frontier-model.py)"
codex exec --sandbox read-only -m "$M" "$(cat <promptfile>)" < /dev/null > <outfile> 2>&1 &
CPID=$!; ( sleep 900; kill -TERM $CPID 2>/dev/null; sleep 3; kill -KILL $CPID 2>/dev/null ) & WD=$!
wait $CPID; RC=$?; kill -TERM $WD 2>/dev/null; echo "CODEX_EXIT=$RC"
```

**Two guards, both required:**
- **`< /dev/null`** — see below; prevents the stdin-block hang (this is the guard that actually fixed the observed hang).
- **A watchdog killer** (15 min) — bounds ANY hang (network/model stall). Do NOT use `timeout`/`gtimeout` on macOS (neither exists → exit 127, the review silently doesn't run). Use the background `( sleep 900; kill … ) &` pattern above (or a perl fork+alarm wrapper). A hung job then gets killed and the bg task NOTIFIES within the window instead of waiting forever. If it times out, treat as the Codex-unavailable fallback (a single re-run is fine, then run a Claude adversarial pass per `docs/plugins.md`).

**CRITICAL — always redirect `< /dev/null`.** `codex exec` prints `Reading additional input from stdin...` and BLOCKS on stdin even when the prompt is passed as an argument. In a `run_in_background: true` Bash the shell's stdin is an open pipe that never sends EOF, so codex hangs **forever** (observed 2026-07-09: a Task-1 review stuck 1h40m, output frozen at that one line — the process is alive, the bg job never notifies, `pkill -f "codex exec"` to clear). `< /dev/null` gives instant EOF so codex proceeds with the arg prompt. Earlier runs that omitted it only worked by luck (stdin happened to be closed); make it deterministic. Bounded-wait check: if the output file is stuck at `Reading additional input from stdin...` and not growing → it's the stdin hang, not a slow review; kill + relaunch with `< /dev/null` (a single re-run is fine, then fall back to a Claude adversarial pass per `docs/plugins.md`).

Do **NOT** dispatch the `codex:codex-rescue` subagent in this environment — it runs inside a restricted sandbox where nested `codex exec` fails with `Operation not permitted` (cannot create temp files / init the app-server client), and it self-reports it can only forward to `task` (can't poll/status/write files). That is the recurring "Codex unavailable → fall back to Claude" gap.

**Why it works:** the outer sandbox override gives `codex` real filesystem/temp access, while codex's *own* `--sandbox read-only` flag keeps it review-only (no edits). Validated 2026-07-09 (returned `SANDBOX_OK`, model `gpt-5.5`, codex v0.142.5).

**How to apply:** for any `codex:rescue` / adversarial-review gate, invoke codex directly via coordinator Bash and capture output to `docs/reviews/...-codex.md`. Pass the prompt as an argument (not stdin). Keeps the true dual-review (Codex + Claude) intact instead of substituting. See [[dev-process]], [[process-conventions]]; governance lives in `docs/plugins.md` (Codex fallback section) — candidate to codify there once the user confirms.

