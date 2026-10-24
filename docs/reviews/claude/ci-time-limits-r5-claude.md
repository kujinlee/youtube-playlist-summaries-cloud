# ci-time-limits — round 5 — Claude half

Subject: `git diff origin/master...HEAD` at `c9d0145a` (branch `fix/ci-time-limits`) — `.github/workflows/ci.yml`,
`scripts/check-plan-code.py` (one docstring line), backlog #343 and #231, dashboard entry, review records.
Mandate: REFUTE, final tree. Harness of my own: the delivered `run:` block and `env:` extracted by line range
from the workflow (not retyped), `bash -n` clean, run as a non-root `runner` user with NOPASSWD sudo inside
`ubuntu:26.04` with real `sudo-rs 0.2.13-0ubuntu1.2` and `timeout (uutils coreutils) 0.10.0`. Scratch:
`scratchpad/r5c/` (`step.sh`, `env.sh`, `case.sh`). `RETRY_PAUSE_S` overridden to 1 for speed in the fault cases only.

## What I ran, and what it showed

| Case | Result |
|---|---|
| healthy, delivered limits | `rc=0`, 38 s, no `::warning::`/`::error::` lines |
| env NOT sourced (my harness bug on the first run — every limit empty) | `rc=1` at once: `::error::CANNOT RUN — all  attempts failed; the last: .` — an accidental fail-closed check: an empty `FFMPEG_ATTEMPTS` cannot pass |
| download operation SIGKILLed from outside (`kill -KILL $$` in an apt-get wrapper) | `rc=1`, 2 s; every warning and the error read `terminated by SIGKILL (exit 137) — the status alone does not establish whether its 150s bound and 10s kill grace expired`. Round 4 Codex's Medium is folded and TRUE in its case |
| download operation dies of SIGSEGV (`kill -SEGV $$`) | `rc=1`, 2 s, phase named correctly — but see L1 |
| `sudo timeout --kill-after=10 5 /nonexistent-cmd` (and a bad shebang) | `rc=127`, `timeout: failed to execute process: No such file or directory` — see L1 |

I did not re-run round 3's lock and hang cases: Codex r4 re-ran them on this tree minus the 137 text
(M1 rc=1 in 122 s naming the download timeout, M2 recovery rc=0, held-lock / download-hang / install-hang
failing closed with the right phase), and `c9d0145a` changes only the 137 message string and its records —
I diffed it. Treat those cases as Codex's measurement, not mine.

## Mandate items

- **a. Fail-open?** No. Every failure path ends in `cannot_run` → `exit 1`; no `continue-on-error`, no
  `|| true` on the outcome; `bounded` is called only in `if`/`!` context so `bash -e` cannot abort it mid-way
  and lose the message. The final `ffmpeg -version`/`ffprobe -version` still execute the binaries. The step
  cap (`timeout-minutes: 20`) failing is a step FAILURE, also closed. No pipes, so pipefail is irrelevant.
- **f. Budget.** 3 × (130 + 160) + 2 × 15 + 190 = 1,090 s is a true upper bound (the real worst path is
  lower: a finished update is not repeated). Lock waits are inside the two install bounds. 1,090 < 1,200;
  the pre-step work (checkout, setup-node) plus the post-step remainder historically ~5 min keeps the job
  inside `timeout-minutes: 30`. Worst-case total remains unmeasured, which the comment says.
- **g. Output to a file.** `bounded` `cat`s the whole log after every operation, and `cannot_run` tails the
  last 40 lines again; nothing a reader needs is lost. An orphan cannot hold the step's stdout.
- **b/c. Shards.** The matrix list is the only copy of N (`--shard0` takes `strategy.job-index`/`job-total`);
  `mutation-sweep-complete` keys on `needs.mutation-sweep.result`, the matrix aggregate, under `if: always()`,
  so it requires all 12 and its context name does not move. Branch protection requires that one context, not
  the 12. Grep for `8 shards`/`/8`/`1..8` in scripts and workflows finds only parse-format test literals and
  history comments. Self-tests run by me: `check-ci-watched` 82/82, `check-merge-ready` 74/74,
  `check-python-pin` 111/111. Partition-exactly-once (2,003 mutations, 11×167 + 1×166) is Codex r4's
  measurement; I did not repeat it.
- **d. Records.** #231's closure says the post-change number is PREDICTED and names the reopen condition
  (any shard > 1,500 s on the first CI run). #343 and the dashboard carry the r4 137 wording; no stale
  "ignored SIGTERM" claim remains in the diff (grepped).

## Findings

**L1 — Low — `.github/workflows/ci.yml` (`bounded`, the `*)` arm).**
Input: an operation that ends by a signal other than KILL (measured: SIGSEGV → 139), or `timeout`/`sudo`
failing to run the command (measured: `timeout` → 127 "failed to execute process").
What happens (139, quoted): `::error::CANNOT RUN — all 3 attempts failed; the last: downloading ffmpeg's
packages (network): apt/dpkg exited with an error (exit 139) — its own message is in the output.`
A process killed by a signal printed no message, and for 125/126/127 the status is `timeout`'s, not apt's —
so the `*)` arm still asserts a cause the status does not establish, the same class as round 4's 137 Medium.
It is Low, not Medium, because it is still fail-closed with the correct PHASE named, the full log is printed
beside it, and 125–127 are not realistic on a runner (coreutils and apt-get are always present); 128+N from
an OOM kill or crash is the plausible input. Fix (text only, optional): `*) why="$what: exited with status
$rc — see its output above"`, optionally `128+N` as "terminated by signal N". Not blocking.

No Blocking, High or Medium findings.

VERDICT: CONVERGED
