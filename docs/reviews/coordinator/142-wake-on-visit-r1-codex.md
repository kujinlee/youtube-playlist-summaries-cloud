<!-- codex-review: model=gpt-5.5 -->

# Codex adversarial review — backlog #142 wake-on-visit — round 1

## Verdict: FINDINGS

## Baseline re-derivation

Matched the brief’s baseline:

`npx tsc --noEmit` → clean  
`npm test` → 277 suites / 2860 tests passed, 1 snapshot, 46.498s  
`python3 -c "import tomllib; tomllib.load(open('fly.toml','rb'))"` → parses

Additional load-bearing config check did **not** pass:

`fly config validate` → `invalid restart policy: no`

## Findings

### [Blocking] 1 — `fly.toml` is not a valid Fly config, and the intended policy is `on-failure`

**Evidence:** `fly.toml:95-97` sets:

```toml
[[restart]]
  policy = "no"
  processes = ["worker"]
```

`fly config validate` on this tree:

```text
Validating .../fly.toml
invalid restart policy: no
✘ invalid app configuration
```

Changing only the actual policy line to `policy = "on-failure"` in a temp copy made `fly config validate` pass. Changing it to `on-fail` still failed.

Fly’s current config reference says valid restart policies are `always`, `never`, and `on-failure`, and that `on-failure` restarts only non-zero exits and is the default. Fly’s machine restart docs also state that `on-fail`/`on-failure` allows clean exits while preserving crash restart behavior.

Sources:
https://fly.io/docs/reference/configuration/#the-restart-section  
https://fly.io/docs/machines/guides-examples/machine-restart-policy/

**Why it matters:** As written, the slice cannot deploy with current `flyctl` validation. Also, the design does not need to give up crash recovery: `on-failure` lets idle exit 0 stop the Machine and still restarts crashes.

**Fix:** Use:

```toml
[[restart]]
  policy = "on-failure"
  processes = ["worker"]
```

Update the test at `tests/lib/worker-idle-exit.test.ts:157-164`, which currently asserts the invalid value.

### [Blocking] 2 — Exit/enqueue race can strand a committed job indefinitely

**Evidence:** The enqueue path commits first, then awaits wake: `lib/job-queue/enqueuer.ts:56-67`. The worker exits after one drained check: `worker/main.ts:156-159`, calling `queueIsDrained()` which is a single `hasQueuedWork()` read at `worker/main.ts:227-229`.

Race:

1. worker polls idle;
2. `hasQueuedWork()` returns false;
3. enqueue commits a queued row and pokes `/wake`;
4. because the worker is still running, Fly Proxy has no stopped Machine to start;
5. worker returns from `runWorkerLoop` and exits 0.

The wake listener itself only responds HTTP 200 at `worker/main.ts:202-203`; it does not reset the idle clock or force another poll.

I mutation-tested this by temporarily adding a test that flips “queued” immediately after the drained check returns false. Control: full suite was green first. Mutated test failed:

```text
Expected: true
Received: false
at tests/lib/worker-idle-exit.test.ts:146
```

That proves current tests do not catch this race. I removed the temporary test and reran `npm test -- tests/lib/worker-idle-exit.test.ts --runInBand`: 8/8 passed.

**Why it matters:** This violates row #142’s “do NOT exit while anything is queued” falsifier. The job can sit until the next unrelated enqueue or manual worker start; ordinary polling/visiting does not poke the worker.

**Fix:** Make a wake received by a running worker observable to the loop and prevent exit until another poll sees the queue empty after that wake. Also add a regression test for “job appears immediately after drained check”.

### [Medium] 3 — Wake listener relies on implicit `::` binding, while Fly documents `0.0.0.0` for Fly Proxy/Flycast

**Evidence:** `worker/main.ts:206` calls `server.listen(port)` with no host. Locally, Node reports:

```text
{ address: '::', family: 'IPv6', port: ... }
TCP *:... (LISTEN)
```

Node documents that omitted host binds `::` when IPv6 is available, and may also bind IPv4 depending on OS behavior. Fly’s app-service docs say Fly Proxy reaches services through a private IPv4 address and the process should listen on `0.0.0.0:<port>`; the Flycast blueprint repeats that requirement.

Sources:
https://nodejs.org/api/net.html#serverlistenport-host-backlog-callback  
https://fly.io/docs/networking/app-services/  
https://fly.io/docs/blueprints/autostart-internal-apps/

**Why it matters:** This wake path is too important to rely on IPv4-mapped IPv6 being enabled in the Fly VM. If it is not, Flycast routes to a service that is configured but not reachable.

**Fix:** Bind explicitly: `server.listen(port, '0.0.0.0', ...)`, and assert `server.address().address`.

### [Low] 4 — Wake cost is per job, sequential, and paid even for joins

**Evidence:** `DEFAULT_TIMEOUT_MS = 1_500` at `lib/job-queue/worker-wake.ts:27`; `SupabaseEnqueuer.enqueue()` awaits wake on every successful enqueue at `lib/job-queue/enqueuer.ts:62-67`. Playlist fanout is sequential for up to 50 videos: `lib/job-queue/producer.ts:12`, `lib/job-queue/producer.ts:104-108`.

`joined: true` can mean an existing `queued`, `active`, or `completed` row: `supabase/migrations/0018_enqueue_dig.sql:71-81`.

**Why it matters:** With a slow or blackholed wake URL, a 50-video playlist can add up to 75s of request latency. Joined completed jobs also poke even though no worker can do useful work for them.

**Fix:** Coalesce to one best-effort wake per request after at least one fresh queued row, or fire the wake without awaiting the full timeout on the user path.

## Leads L1-L7: confirmed / refuted, one line each

L1 — Confirmed, and worse: `policy = "no"` is invalid for `fly.toml`; `on-failure` is the correct value and preserves crash recovery.

L2 — Confirmed: a job can commit after `hasQueuedWork()` returns false, receive a wake while the worker is still running, then be stranded by worker exit.

L3 — Partly confirmed as a design residual: `hasQueuedWork()` only sees queued rows, but `runOnce()` sweeps expired active leases on worker start; while the worker is stopped, nothing sweeps until a later wake/manual start.

L4 — Refuted for deployment risk: production construction sites are inside request handlers (`app/api/jobs/route.ts:38`, dig route `:60`), not module scope; the “at call time” comment is imprecise because env is read at construction.

L5 — Confirmed as risky/not Fly-verified: Node binds `::` when host is omitted, while Flycast/Fly Proxy docs require `0.0.0.0`.

L6 — Confirmed: the wake is awaited on every successful enqueue, including joins, with a 1500ms timeout.

L7 — Refuted: if `idleExitMs < pollMs`, the worker exits late by up to one poll, not early; the check-before-sleep shape does not create an off-by-one stranding bug by itself.

## What I could not run

I did not run a live Fly end-to-end with both Machines stopped, a private Flycast IPv6 allocated, and `WORKER_WAKE_URL`/`WORKER_IDLE_EXIT_MS` set.

I did not verify the omitted-host listener inside an actual Fly Machine; I verified Node’s behavior locally and checked it against Fly’s live docs.
