# ci-time-limits — round 1 — Claude half

Subject: `fix/ci-time-limits` at `a8419e2f`, `git diff origin/master...HEAD`. That is the `ci.yml` ffmpeg step
(backlog #343), the matrix change 8 -> 12 (backlog #231), one docstring line in `scripts/check-plan-code.py`,
the backlog/dashboard records and the decision-log bet. Mandate: REFUTE.

## What I ran (all outside the repo; scratch dir `scratchpad/r1c-test/`)

1. Pulled the **real failing job's log**: run 40023350011, job 120653259341
   (`gh run view --job 120653259341 --log`).
2. Extracted the delivered step text from `ci.yml` with `js-yaml`. It is byte-identical to the
   implementer's `b3-test/step.sh` (`diff` printed nothing). I ran it in **`ubuntu:26.04`**, the
   runner's real release (see F2), as a non-root user. This used **real `sudo`, real `timeout` and real
   apt**, with no stubs.
3. Ran the self-tests of `check-ci-watched.py` (82/82), `check-merge-ready.py` (74/74) and
   `check-python-pin.py` (111/111). All rc=0.
4. Read the required contexts: `gh api .../branches/master/protection/required_status_checks` ->
   `["verify","schema-gates","mutation-sweep-complete"]`.

## Mandate answers that came back clean

- **(a) No fail-open path.**
  - Exhausting the attempts prints `::error::CANNOT RUN` and runs `exit 1`. My real-apt run with the
    install limit forced to 4 s printed `RESULT attempts=3 limits=120/4 rc=1 elapsed=19s` / `no ffmpeg`.
  - Under `bash -e` (the log confirms `shell: /usr/bin/bash -e {0}`), commands inside the `if`
    condition are exempt from errexit, so a timed-out attempt (rc 124) goes to the retry and does not
    abort the step.
  - The `ffmpeg -version` / `ffprobe -version` checks after the loop are still errexit-guarded.
  - `tests/lib/dig/slide-crop.integration.test.ts` has no skip guard (grep for
    `skip|which ffmpeg|skipIf` found nothing), so a missing binary would make the tests fail, not
    vanish.
  - If the step-level `timeout-minutes: 15` fires, that is a step **failure**, not a skip.
- **(a) The budget is consistent.**
  - The healthy `verify` in run 40031532664 took 5m00s end to end (22:07:26 -> 22:12:26).
  - The worst case is a 15 min step cap + ~5 min for the rest, which is about 20 min, under the job's 30.
  - `dpkg --configure -a` is unbounded, but the step cap covers it.
- **(b) The 12-way partition is sound.**
  - `shard_slice` is `muts[index - 1::total]` (`scripts/check-plan-code.py:2206`). A stride slice is a
    partition by construction. Over 1,623 entries (the count cited at
    `scripts/check-decision-scheme.py:1174`), N=12 gives disjoint shards that cover everything, sized
    135-136. I checked this with python: `True 135 136`.
  - `shard_refusal` would refuse an empty shard. That needs fewer than 12 entries.
  - `mutation-sweep-complete` reads the aggregate `needs.mutation-sweep.result`
    (`ci.yml:1088`, `:1100`), so it requires all 12 shards with no count to update.
  - No guard pins the matrix length. The `/8` literals in `check-plan-code.py:4477-4498` are
    `parse_shard` fixtures, not a count of jobs.
- **(c) Branch protection is unaffected.** The required contexts don't include any `mutation-sweep (N)`,
  and the job names are unchanged.
- **(d) The prediction is labelled as a prediction.**
  - The #231 closure says *"⚠ The post-change number is PREDICTED, not measured … REOPEN if any shard
    there exceeds 1,500 s"*. The dashboard says *"That figure is a prediction"*.
  - The arithmetic re-derives: (1388−221)×8/12+221 = 999; ×1.17 = 1,169.

## Findings

### F1 — Medium — `ci.yml:121-134`: the per-attempt `timeout` covers the local dpkg phase, a kill there leaves an ORPHANED dpkg holding the lock, and `|| true` hides it

- **Input.** Real apt on `ubuntu:26.04`, with `APT_INSTALL_LIMIT_S=17` so that the kill lands after the
  download (135 MB fetched in about 6 s) and during unpack/configure. Everything else was the delivered
  text.
- **Output, quoted:**

  ```
  Fetched 135 MB in 6s (21.6 MB/s)
  ::warning::ffmpeg install attempt 3 of 3 failed or exceeded its 120s/17s limit
  dpkg: error: dpkg database lock was locked by /usr/bin/dpkg process with pid 2767
  ::error::CANNOT RUN — ffmpeg could not be installed in 3 bounded attempts (an apt mirror is slow or down).
  RESULT attempts=3 limits=120/17 rc=1 elapsed=58s
  ```

- **What happens.**
  1. `timeout` terminates `apt-get`, but the `dpkg` that apt-get spawned survives and keeps holding
     `/var/lib/dpkg/lock-frontend`.
  2. The repair, `sudo dpkg --configure -a || true`, then fails on that lock, and `|| true` swallows
     the failure.
  3. The next attempt races the orphan.
  4. The final message blames *"an apt mirror is slow or down"* while the mirror ran at 21.6 MB/s.

  On the runner this has a narrow trigger: a download that finishes inside the last ~7 s of the 150 s
  window. In the real log, dpkg took 21:26:30 -> 21:26:37. Fail-safe is not at risk, because the step
  still exits 1. What is at risk is the **retry**, the thing #343 adds, and the cause it reports. The
  measured incident was a download trickle, so the bound is on the right command but the wrong phase.
- **Fix.** Bound only the network phase:
  - `sudo timeout "$APT_INSTALL_LIMIT_S" apt-get install -y --no-install-recommends --download-only ffmpeg`
    inside the loop;
  - then, after the loop, the install from the local cache without a per-attempt kill (the step cap is
    still the backstop).

  Apt keeps completed `.deb`s in `/var/cache/apt/archives`, so attempts accumulate progress. That is
  UNVERIFIED on the runner: the docker image's `docker-clean` hook deletes them, which is why my
  container re-fetched "135 MB" on each attempt. As a smaller alternative, add
  `-o DPkg::Lock::Timeout=60` to the install and to `dpkg --configure -a`, so a retry waits for the
  orphan instead of colliding with it.

### F2 — Low — `docs/backlog.md` #343 status + `docs/dashboard-entries.md`: the falsifier ran on the wrong release, with a `sudo` that does not exist on the runner

- **Input.** The failing job log shows the runner's archive is **`resolute`** (26.04), for example
  `Get:2 http://azure.archive.ubuntu.com/ubuntu resolute/main amd64v3 libva2 …`. On that release
  `sudo` is `sudo-rs 0.2.13` and `timeout` is `uutils coreutils 0.10.0` (printed by my container).
- **What happens.**
  - The closure records the evidence as *"run under `bash -e` in `ubuntu:24.04`, `apt-get` stubbed"*.
  - The harness's `sudo` is `exec "$@"` (`b3-test/run-case.sh`), and the stub is reached by `PATH`
    precedence. Real `sudo` resets `PATH` through `secure_path`, so on a runner `sudo timeout apt-get`
    would never reach `/stub/apt-get`.
  - The stub cases therefore never exercised real `sudo` -> `timeout` -> apt signal delivery. That
    path is where F1 lives.
  - My run covers the gap: with real sudo-rs and uutils `timeout`, the kill does reach `apt-get`, and
    the loop and the exit code behave as claimed. So the conclusion holds. The record still overstates
    what was tested.
- **Fix.** Say "ubuntu:24.04 with a sudo shim; the runner is 26.04 (sudo-rs, uutils)". Alternatively,
  cite a real-apt run on 26.04.

### F3 — Low / informational — 12 shards against the plan's concurrent-job ceiling (UNVERIFIED)

- One push now starts at least 14 jobs: 12 shards, `verify` and `schema-gates`.
- A PR run that overlaps a master run can exceed the account's concurrent-job limit and queue.
- Queue time is not charged to `timeout-minutes`, so this costs latency, not correctness.
- The prediction "slowest shard ~19.5 min" is wall-clock *once started*. That is worth a clause, so a
  slow first run is not read as the prediction failing.
- I did not measure the account's limit.

## Bet check

The decision-log bet says round 1 finds *"no Blocking/High, no fail-open path for ffmpeg, and no mutation
dropped or duplicated"*. All three held. F1 is a Medium that defeats the retry the change adds and makes
its reported cause wrong. The fix is clearly specified and costs a few lines, so I am not converging over it.

VERDICT: NOT CONVERGED
