---
name: wake-on-visit-merged-322
description: "FIRES-WHEN: citing PR #322 or worker wake-on-visit — ⭐ MERGED e693f36a (PR #322). Worker sleeps/wakes; own Fly app `yps-worker`, NO public IP. SHIPS INERT except one part. 4 rounds; 3 of my own fixes became the next round's finding"
metadata:
  type: project
---

**MERGED 2026-09-19 — `e693f36a`, PR #322.** Backlog #141 and #142 both closed. 2892 tests / 278 suites.

## It is INERT except for one thing, and that exception is the thing to remember

Nothing happens until the six Fly commands in `docs/deploy.md` § Step 5 run **in order**.
⚠ **EXCEPT the `kill_signal`/`kill_timeout` relocation, which takes effect on the next `fly deploy`
of the web app with no command at all** — on master those keys parsed into `[http_service]` and were
never app settings, so both process groups move from Fly's `SIGINT`/5s defaults to `SIGTERM`/120s.
Checked benign in both consumers; still a behaviour change arriving with an ordinary deploy.

## What it does

Worker exits when its queue drains → machine `stopped`. A visitor's enqueue pokes
`http://yps-worker.flycast/wake`; Fly Proxy starts the machine. ⭐ **The proxy may START it and never
STOP it** — Fly's autostop docs say nothing about an in-flight request blocking a stop, so the worker
stops itself. The job commits to Postgres BEFORE the poke, which is why a failed poke costs latency
and never work.

## Unresolved, deliberately — do not assume these are covered

- **Crash + machine GONE** → an orphaned `active` row. The read-path poke only fires on `queued`, so
  nothing wakes for it. (Crash + machine survives IS covered: `on-failure` restarts and sweeps.)
- **Dig jobs have no recoverer** — `listByPlaylist` filters `job_kind = 'summary'`.
- **Deploy mid-summary** → backlog #139, blocked on a human design call. ⚠ This PR added a FOURTH
  trigger (the listener-failure path) and it needs no deploy. #139's row still cites `fly.toml:45-46`
  and quotes a sentence this branch moved — **that citation is now stale**.
- `fly.toml` still declares the old `worker` process group; removal is one atomic follow-up step, and
  the interim rule is `fly deploy --process-groups web`.

## What the review cost, and what it taught

4 rounds (3 full dual + 1 single-half final-tree pass). ⛔ **Three of my own fixes became the next
round's finding**: the `[[services.ports]]` fix created a port-80 collision with the website; the
listener-recovery fix set an exit code that cannot cause an exit; and "no unit test can guard this"
was refuted by a reviewer writing one.

⭐ **Four tests passed for AMBIENT reasons**, all found by mutation, none by reading. One mutation is
killed by the COMPILER instead — `onFatal` optional → required, because reverting the single call
site left all 35 cases green. See [[review-convergence-is-not-the-final-tree-gate]] for why the gate
then could not be satisfied by iterating.
