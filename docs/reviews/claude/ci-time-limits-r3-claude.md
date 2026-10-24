# ci-time-limits — round 3 — Claude half

Subject: `git diff origin/master...HEAD` on `fix/ci-time-limits` at `1bf7a764` (step text from `dfccc2b1`).
I reviewed the whole branch again from the start. The implementer's report was used only to find the
harness layout. Every behavioural claim below was re-run.

**What ran:**
- The image was `b3-runner26` (FROM `ubuntu:26.04`, real sudo-rs, uutils `timeout`, real apt).
- The step text was extracted from the delivered `ci.yml` with js-yaml. It is byte-identical to the
  implementer's `step.sh`.
- My own harness is at `scratchpad/r3c/case.sh`. Faults came from an `/usr/local/bin/apt-get` wrapper
  and real `fcntl` locks. One network fault used a real blackholed proxy (`10.255.255.1`) for the
  download only, so real apt really waited on the lock and then really hung.
- The runner release was confirmed from job 120680691193's log: `Image: ubuntu-26.04`,
  `Version: 20261012.163.1`. The harness matches the runner.

## Findings

### M1 (Medium): a network hang is reported as a lock problem if apt waited on the lock at all, even briefly

- **Where:** `.github/workflows/ci.yml`, in `bounded()`. The lock `grep` runs before the
  `rc = 124/137` checks: `if grep -qE 'Could not get lock|Unable to acquire the dpkg frontend lock|Unable to lock' "$log"`.
- **Why it happens:** while apt waits under `DPkg::Lock::Timeout`, it prints progress lines of the form
  `Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 37 (perl)...`
  These lines go to the log even when nothing is attached to a tty, and they match the grep. So any
  operation that waited on the lock at all is classified as "lock". This holds even when the lock was
  released and the operation then failed for some other reason.
- **Input (case `lockshort-dlhang`):** the frontend lock was held for 15 s. Then the download hung on the
  network. The download bound was 30 s.
- **Output (verbatim):**
  ```
  Waiting for cache lock: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 37 (perl)...
  ::warning::attempt 1 of 3: downloading ffmpeg's packages (network): the apt/dpkg lock was held by another process for over 60s — NOT a mirror problem
  ::warning::attempt 2 of 3: downloading ffmpeg's packages (network) exceeded its 30s bound and was killed
  ```
- **Why the message is wrong:** it makes two claims, and both are false. The lock was held for 15 s,
  not "over 60s". It *was* a network problem.
- **Where it can surface:**
  - The same path exists in the install phase. A brief lock wait followed by a dpkg hang becomes
    `CANNOT RUN — installing …: the apt/dpkg lock was held … over 60s`.
  - It reaches the final `::error::` whenever the brief contention falls on the last attempt or on
    the install.
- **Why it matters:** this is the inverse of round 1's defect (a lock reported as a mirror). The step's
  own comment and the #343 closure say failures are named by phase and cause. That is not true here.
  It still fails closed: rc=1 and CANNOT RUN.
- **Fix (verified):**
  - Classify the timeout codes first.
  - Match only apt's terminal `E:` lines, not its `Waiting for cache lock:` progress lines:
    `if [ "$rc" != 124 ] && [ "$rc" != 137 ] && grep -qE '^E: (Could not get lock|Unable to acquire the dpkg frontend lock|Unable to lock)' "$log"; then`
  - Results with the patched copy (`scratchpad/r3c/fix/step.sh`):
    - The same `lockshort-dlhang` input now prints `exceeded its 30s bound and was killed` on all
      three attempts. rc=1, 92 s.
    - A lock held throughout (wait 5 s) still prints `the apt/dpkg lock was held … over 5s`. The
      terminal line is `E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?`.
- **Missing test:** add `lockshort-dlhang` to the harness as a case that must name the bound.

### M2 (Low–Medium): `apt-get update` does not wait for its lock, so the comment's "it WAITS" is false, and the "over 60s" in the message is invented

- **Where:** the `ci.yml` comment `Every operation passes DPkg::Lock::Timeout, so it WAITS for a lock instead of colliding`, and the `why=` text, which always says `over ${DPKG_LOCK_WAIT_S}s`.
- **Why it happens:** `apt-get update` takes `/var/lib/apt/lists/lock`. `DPkg::Lock::Timeout` governs
  the dpkg frontend lock, not that one.
- **Input:** `/var/lib/apt/lists/lock` held for 8 s with an `fcntl` write lock (case `listslock-short`).
- **Output (verbatim):** all three attempts fail within the same 2 seconds:
  ```
  E: Could not get lock /var/lib/apt/lists/lock. It is held by process 20 (perl)
  E: Unable to lock directory /var/lib/apt/lists/
  ::warning::attempt 1 of 3: apt-get update (network): the apt/dpkg lock was held by another process for over 60s — NOT a mirror problem
  ...
  ::error::CANNOT RUN — on all 3 attempts, the last: apt-get update (network): the apt/dpkg lock was held by another process for over 60s — NOT a mirror problem. Re-run the job.
  RESULT mode=listslock-short rc=1 elapsed=2s
  ```
- **What goes wrong:**
  - A lock that would have been free 6 s later burns every retry.
  - The message states a 60 s wait that never happened.
  - It still fails closed and names a lock, which is correct.
- **How likely it is:** a contender for the lists lock on the hosted runner (for example an
  apt-daily timer) is NOT MEASURED, so I am not rating this higher.
- **Fix:**
  - Either name it truthfully (`… the apt lists lock was held — apt-get update does not wait for it`),
    or make a lock failure in the update phase sleep before the next attempt (for example
    `sleep "$DPKG_LOCK_WAIT_S"`, which the budget already covers).
  - Correct the comment either way.
  - The #343 closure's line "Every operation passes `DPkg::Lock::Timeout=60`" is literally true but
    implies a wait that does not happen. Qualify it in the same edit.

## Checked and refuted (no finding)

- **(a) Fail-open:**
  - Every exhausted path reaches `cannot_run` → `exit 1`.
  - The binaries are executed afterwards.
  - The step has no `continue-on-error` and is not skippable.
  - Under GitHub's `bash -e {0}`, `cmd || rc=$?` and `if bounded …` behave as intended. There are no
    pipes, so `pipefail` is irrelevant.
- **The round-3 question, whether anything can outlive the bound (case `escape`):**
  - Input: the download wrapper started `( setsid sleep 1000 & )` and a plain `sleep 1000 &`.
  - The plain child was killed with its group. The three `setsid` escapees survived, each in its own
    session.
  - The step still ended on time: rc=1, 17 s, every attempt named "exceeded its 5s bound".
  - The escapees hold the log *file*, not a pipe, so neither `cat "$log"` nor the shell waits for them.
  - No lock wait sits outside a `timeout`: all seven operations go through the one `sudo timeout --kill-after` site.
- **(f) Budget:**
  - The worst case is 3 × (130 + 160) + 190 = 1,060 s. The lock waits (60 s) sit inside each bound,
    because 60 < 120, 150 and 180.
  - The step cap is 1,200 s.
- **Job fit:** the real `verify` (job 120680691193) took 5m00s, of which ffmpeg was 23 s. So everything
  else is about 4.6 min. 20 + 4.6 + about 0.1 of setup before the step is under 25 min, which fits the
  job's 30 min. The "~5 min" in the comment holds.
- **(g) Output to a file:** `cat "$log"` runs before every classification, so a failed step prints the
  full output of each attempt.
- **(b) Shard count:**
  - The matrix list is the only copy of N. `--shard0 "$SHARD_INDEX/$SHARD_TOTAL"` comes from
    `strategy.job-index`/`job-total`.
  - `shard_slice` is `muts[index-1::total]`, a partition by construction: no entry is dropped or
    duplicated.
  - `shard_refusal` refuses an empty shard, so 12 cannot produce a vacuous green while there are at
    least 12 entries.
  - `mutation-sweep-complete` reads the aggregate `needs.mutation-sweep.result` with `always()`. It
    therefore requires all 12.
  - Grep of `scripts/` and `.claude/hooks/`: no guard counts shards or expects 8. The `range(1, 9)` in
    `check-decision-scheme.py:2716` is unrelated fixture data.
  - Self-tests: `check-ci-watched` 82/82, `check-merge-ready` 74/74, `check-python-pin` 111/111.
- **(c) Required checks:** the job names are unchanged. Branch protection requires
  `mutation-sweep-complete`, not the per-shard contexts, so the move to 12 needs no settings change.
- **(d) Records:** the #231 closure states the after-number as PREDICTED and says to REOPEN if any shard
  exceeds 1,500 s. The arithmetic checks out: 1621/1388 = 1.17; (1388 − 221) × 8 / 12 + 221 ≈ 999;
  × 1.17 ≈ 1,170. The sweep will run on this PR, because `scripts/check-plan-code.py` changed, so that
  measurement will exist.

## Verdict

Both findings are about diagnostics, not bounds. The step always fails closed and always ends inside
its cap. But the branch's stated purpose for this step, in its comments and in #343's closure, is that
every failure names the right phase and cause. M1 is a reachable, measured case where it names the
wrong cause and states a number that is false. The fix is one line and it is verified.

VERDICT: NOT CONVERGED
