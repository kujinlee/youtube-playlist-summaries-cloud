---
name: lease-sweep-merged-318
description: "FIRES-WHEN: citing PR #318, lease sweep, or worker idle database traffic — Lease-sweep cadence MERGED (PR #318, 35cf44c6). Found #139 🔴 a deploy dead-letters the in-flight summary AND keeps the spend. Fly bill cut 66%; fly.toml drift will silently revert it"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5cbc47e9-0d41-4233-8828-361c8830d6bb
  modified: 2026-09-18T17:44:52.712Z
---

**PR #318 MERGED 2026-09-18 as `35cf44c6`.** Started from a screenshot of Supabase hit every 2s on a
day with no work. Gated `sweepExpired()` to 60s (`SWEEP_MS`) instead of the 2s claim poll.

**Measured on prod (plan=`free`):** ~79,800 REST req/day and the idle worker was **100% of it** —
an exact 25/25 pair of `sweep_expired_leases`/`claim_next_job`, auth/realtime/storage all 0. At
921 B/response that is 2.13–2.28 GB/mo = **43–46% of the 5 GB free egress**. Supabase bills egress,
NOT request count ("all plans include unlimited API requests").

## ⭐ The big find, and it is STILL OPEN — [[backlog-139-deploy-kills-summaries]]

`fly.toml:45-46` promises the worker *"finishes the in-flight job"* on SIGTERM. **It aborts it.**
`shutdownSignal` is folded into the handler's signal → `AbortError` → `isNonRetryable` says
retryable → `fail_job` (`0008:152-156`) takes `attempts >= max_attempts` → with live
`summary_max_attempts = 1`, **`dead_letter` on the first interruption, every deploy** — and
`classifyGeminiFailure` returns `'keep'` once aborted, so `billableSucceeded: true`, **the spend is
kept**. Backlog **#139** 🔴 + roadmap. NOT fixable in `runOnce`: `claim_next_job` increments
`attempts` with no un-claim. Complete fix is SQL, and it is a design call (drain vs don't-charge).
Backlog **#140** 🟢 = collapse `SweepPolicy` to one `run(fn)`.

## Fly: 66% cut, with a trap

~$15.80/mo → ~$0–1/mo idle. Worker machine `8654504a454428` **stopped** (0 jobs in 30 days; it was
created 9 days AFTER the last job ever ran). Web `min_machines_running` 1→0 via the **Machines API,
deliberately not `fly deploy`** — the running image is from 24 Aug and master has 177 commits since,
6 touching shipped code (M4 `0027` promotion, the corrections feature). A "config-only" deploy would
have shipped all of it.

⚠ **`fly.toml` still says `min_machines_running = 1`. The next `fly deploy` silently reverts the web
saving.** Agreed next slice: wake-on-visit — worker gets a private service + **Flycast** (routes
through Fly Proxy, so it autostarts; `.internal` does NOT), web pokes it after enqueue best-effort
(the queue is durable, so waking is an optimisation not a correctness requirement), worker exits 0
when idle with `[[restart]] policy = "no"` → machine stops. Do NOT rely on the proxy to stop it
mid-job: Fly documents `soft_limit` but says nothing about in-flight requests blocking a stop.

## What this slice actually taught — see [[a-retrospective-number-needs-provenance]]

Six adversarial reads (Codex ×2, Claude ×4): 1 High, 4 Medium, 12 Low. **I was wrong six times and
reviewers caught all six**, including three numbers that reached the user before being verified.
Worst: my fix for r1's Medium **starved job claiming entirely** (measured 40 sweeps / 0 claims).

⭐ **I raised a THRASHING alarm and it was refuted on the project's own rules:** `dev-process.md`
arms on two consecutive **ROUNDS**; round 1 cannot qualify (no previous round) → count was **one**,
and severity FELL (High→Medium), which `review-method.md` makes part of the tell.
⭐ **The redesign I proposed (hoist `sweepExpired()` into `runWorkerLoop`) was refuted line by
line** — all three findings follow the code to the new file; three guards relocate, none dissolve.
Pre-committed override falsifier, still binding: **fires to REDESIGN if a future round finds
anything in `runOnce`'s sweep/claim sequence caused by the r2 shutdown-guard fix.**

⚠ **Three review subagents stalled or died** (one 500'd mid-run leaving a mutation in the working
tree). Always `git status` before committing after a reviewer runs. See
[[concurrent-agents-go-wrong]] and [[an-instrument-that-edits-the-repo-corrupts-its-peers]].
