<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — backlog #142 wake-on-visit — round 2

## Verdict: FINDINGS

## Re-derivation of the five claims

1. **Matched.** `npx tsc --noEmit` exited 0 with no output.

2. **Matched.** `npm test` output:
```text
Test Suites: 278 passed, 278 total
Tests:       2879 passed, 2879 total
Snapshots:   1 passed, 1 total
Time:        34.116 s
```

3. **Matched.**
```text
fly config validate
✓ Configuration is valid

fly config validate -c fly.worker.toml
✓ Configuration is valid
```

4. **Partially re-derived, not fully matched.** I did not rerun all 10 mutations. I reran the one the commit called out as previously surviving:
```text
MUTATION: if (inFlight) return inFlight; -> if (false && inFlight) return inFlight;
FAIL tests/lib/worker-wake.test.ts
Expected number of calls: 1
Received number of calls: 2
```
So `joins an in-flight poke even after the suppression window has expired` genuinely isolates that branch.

I also tested a config mutation I doubted:
```text
MUTATION: fly.worker.toml auto_start_machines = true -> false
npm test -- tests/lib/worker-idle-exit.test.ts --runInBand
Tests: 13 passed

fly config validate -c fly.worker.toml
✓ Configuration is valid
```
That is a real guard gap: wake-on-visit needs autostart, but the config tests do not pin it.

5. **Matched, by parsing.**
```text
--- fly.toml
top kill_signal SIGTERM
top kill_timeout 120s
http_service has kill_signal False
processes has kill_signal False

--- fly.worker.toml
top kill_signal SIGTERM
top kill_timeout 120s
http_service has kill_signal False
processes has kill_signal False
restart [{'policy': 'on-failure', 'processes': ['worker']}]
```
Fly docs also confirm `kill_signal`/`kill_timeout` are top-level runtime options: https://fly.io/docs/reference/configuration/

## Findings

### [Medium] 1 — Wake-listener post-bind errors do not actually make the process exit

**Evidence:** `worker/main.ts:229-232` handles post-bind server errors with:
```ts
process.exitCode = 1;
server.close();
```
But `main()` is still awaiting `runWorkerLoop()` at `worker/main.ts:291-294`; nothing aborts that loop or rejects into `main()`. The process exits only if/when the loop later returns.

The eventual `finally` then calls `listener.close()` again at `worker/main.ts:295-298`. Node local proof:
```text
first close error: undefined
second close error: Server is not running.
```

**Introduced by round 1's fix?** yes — this is the re-armed error handler added by the fix.

**Why it matters:** The comment says this exits so Fly restarts the machine. It usually does not exit immediately; it can keep polling with the doorbell closed. With `WORKER_IDLE_EXIT_MS` enabled, it may restart later after the idle path trips and the double-close rejects. With no idle exit, it may never restart.

**Fix:** Make the listener error a fatal signal to `main()`: abort the worker loop and exit non-zero after graceful shutdown, or explicitly `process.exit(1)` if this condition is considered unrecoverable enough to interrupt current work. Also make `listener.close()` idempotent so the `finally` path is not relying on a double-close rejection.

### [Medium] 2 — The transitional old `worker` process group is not safe across a normal web deploy

**Evidence:** `fly.toml:44-46` still defines:
```toml
[processes]
  web = "node server.js"
  worker = "node worker.js"
```
and `fly.toml:80-83` still defines a worker VM. `docs/deploy.md:225-228` says to keep the old worker Machine stopped until deleting that group.

Fly’s live docs say `fly deploy` creates at least one Machine for each process group and starts at least one Machine for each group on first deploy/addition; it also updates deploy-managed Machines. Source: https://fly.io/docs/launch/processes/

`fly config show --local` confirms the current web app config still has both `web` and `worker`.

**Introduced by round 1's fix?** yes — the fix moved the real wakeable worker to `yps-worker` but deliberately left the old worker group in the public app.

**Why it matters:** If someone deploys both apps today, the separate `yps-worker` exists, and a normal `fly deploy` of `youtube-playlist-summaries` still creates/updates a worker Machine in the old app. That violates the runbook’s own “keep the old worker Machine stopped so two workers never poll the same queue.” The queue lease logic makes this unlikely to corrupt jobs, but it reintroduces an always-on worker/cost path and duplicate queue consumers.

**Fix:** Do not leave this as a passive doc warning. Either remove the old worker group before the dual-app rollout is considered done, or add an explicit deploy step/gate that scales the old app’s worker group back to zero immediately after any web deploy during the transition.

## Things I checked and found correct

- `workerWakeFromEnv()` sharing is intentional and URL-keyed: `lib/job-queue/worker-wake.ts:97-117`. Same URL shares suppression state; changed URL creates a new instance. Tests with `opts` get private instances.
- The read-path poke matches the enum: schema allows `queued`, `active`, `completed`, `failed`, `dead_letter`, `cancelled` at `supabase/migrations/0008_jobs_queue.sql:22`; `app/api/jobs/route.ts:92` pokes only on `queued`.
- `hasUnfinishedWork()` counts `queued` and `active` only at `lib/storage/supabase/supabase-job-queue.ts:107-111`. Other callers found: only `worker/main.ts:256`.
- The in-flight coalescing regression test is real; the mutation was killed.
- Current Flycast topology matches the human decision: `fly.worker.toml` has the service, `fly.toml` has no `[[services]]`. Flycast docs confirm private Flycast routing and warn that services in apps with public IPs are public: https://fly.io/docs/networking/flycast/
- Worktree was clean after mutations: `git status --short` produced no output.

## What I could not run

- I did not run a live Fly deployment or end-to-end wake test with both Machines stopped.
- I did not rerun all 10 mutations from commit `1d2a4ebc`; I reran the in-flight mutation explicitly called out and one additional config mutation I doubted.
