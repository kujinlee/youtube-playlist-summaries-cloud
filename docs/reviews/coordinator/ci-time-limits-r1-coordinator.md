# Round 1 — `ci-time-limits` — coordinator — ❌ NOT CONVERGED (2 Medium, 2 Low)

```yaml
round: 1
fixes_nontrivial: true
subject: ci-time-limits
halves:
  codex: ran
  claude: ran
findings: [repair-unbounded, timeout-kills-dpkg-phase, test-image-overstated, concurrent-job-queue]
```

Both halves found the same area. Codex Medium: the `dpkg --configure -a` repair between attempts was
unbounded — a hanging repair consumed the step cap and bypassed the remaining attempts and the CANNOT RUN
diagnostic (reproduced, OUTER_RC=124). Claude Medium, reproduced on `ubuntu:26.04` (the runner image per the
failing job's log) with real sudo-rs, uutils `timeout` and real apt: the per-attempt `timeout` also covered
apt's LOCAL dpkg phase, so a kill after the download left dpkg holding the lock, the `|| true` repair failed
silently, and the final message blamed a slow mirror that ran at 21.6 MB/s. No fail-open path either way, and
the 12-shard split is a true partition.

Dispositions (§Q3): both Mediums are in the deliverable — FIX: retries cover the NETWORK only (`update` +
`install --download-only`), then one bounded `--no-download` install; `DPkg::Lock::Timeout=60` on every
operation; no repair step; budget 990 s inside an 18-minute step cap; each failure names its phase (a held lock
as a lock). Testing the fold found two more defects, both fixed (`--download-only` also takes the lock; `| tee`
hung when a lock-holder outlived the kill). Claude Low (the recorded test ran on 24.04 with a sudo stand-in) —
the records now say exactly what ran, on which image. Claude Low (14 concurrent jobs may queue) — noted on
backlog #231, not changed. FOLD: implementer subagent (`cc0e2c9e`, `fcdaa513`); master merged (`efd4fc02`).
Round 2: Codex.
