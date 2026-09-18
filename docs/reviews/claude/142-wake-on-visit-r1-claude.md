# Claude adversarial review — backlog #142 wake-on-visit — round 1

## Verdict: FINDINGS — NOT CONVERGED

Two Blocking. The slice as written **cannot be deployed at all** (F1), and once F1 is fixed the
next deploy **arms a live defect on the public website** (F2) — which is the one thing the slice's
own safety argument ("ships INERT, nothing happens until someone runs `fly ips allocate-v6`") claims
is impossible.

The TypeScript is good. `worker-wake.ts`, the enqueue ordering, the `queueIsDrained` fail-safe
direction and the idle-clock reset are all correct, and I tried hard to break them. Every Blocking
and High finding below is in the **Fly configuration** and in **what the code does at the seams**,
not in the unit-tested logic — which is exactly what one would predict of a slice whose only
executable evidence is a Jest suite that regex-matches a TOML file nothing ever validated.

---

## Baseline re-derivation

| Claim in brief | Re-derived | Match? |
|---|---|---|
| `npx tsc --noEmit` clean | exit 0, no output | ✅ |
| `npm test` → 2860 tests / 277 suites, 1 snapshot | `Test Suites: 277 passed, 277 total` / `Tests: 2860 passed, 2860 total` / `Snapshots: 1 passed` | ✅ |
| `tomllib` parses `fly.toml` | parses | ✅ — **but see F1/F3: parsing is not validity, and the parse tree is not the file you think it is** |

Branch `wake-on-visit` @ `5aca44a6`. Worktree clean at start and at finish (`git status --porcelain`
shows only untracked review artifacts).

Two numbers the brief did not give, which I derived and which matter below:

- `worker/main.ts:15` — `const POLL_MS = 2000;`
- `lib/job-queue/producer.ts:12` — `export const MAX_VIDEOS_PER_ENQUEUE = 50;`

---

## Findings

### [Blocking] F1 — `[[restart]] policy = "no"` is not a valid fly.toml value. `fly deploy` refuses the ENTIRE config, and the guard test pins the broken value

**Evidence.** `flyctl v0.4.87` (`fly version`), run against a *copy* of the branch's `fly.toml` in a
scratch directory:

```
$ fly config validate --config .../flycheck/fly.toml
Validating .../fly.toml
invalid restart policy: no

   ✘ invalid app configuration

Error: App configuration is not valid
```

Control — the same bytes with one token changed:

```
$ sed 's/policy = "no"/policy = "never"/'      fly.toml > fly-never.toml   →   ✓ Configuration is valid
$ sed 's/policy = "no"/policy = "on-failure"/' fly.toml > fly-onfail.toml  →   ✓ Configuration is valid
$ sed 's/policy = "no"/policy = "on-fail"/'    fly.toml > fly-onfail2.toml →   invalid restart policy: on-fail
```

Fly's configuration reference, *The `restart` section*, fetched live today:

> - **always**: Attempts to restart the machine regardless of exit code
> - **never**: Will not restart the machine even with non-zero exit codes
> - **on-failure**: Only restarts if the machine exits with a non-zero exit code (this is the default)

`"no"` is the **Machines API** spelling. fly.toml is validated against the documented set, and `"no"`
is not in it.

**Why it matters.** This is not a subtle runtime difference. It is a hard validation failure of the
*whole app config*, web included, before anything is built. The slice is described as shipping
"inert"; it ships **undeployable**. Collaterally, backlog #141's `min_machines_running = 0` — the
armed trap this slice was supposed to disarm by riding in the same file — cannot land either.

**Aggravating, and the more interesting half: the guard test pins the invalid literal.**
`tests/lib/worker-idle-exit.test.ts:155-164`:

```ts
  // Break this catches: deleting the restart policy, which would turn every idle-exit into an
  // instant restart — a boot loop that bills more than never exiting at all.
  test('fly.toml gives the worker restart policy "no", so exiting means stopped', async () => {
    ...
    expect(/policy\s*=\s*"no"/.test(workerBlock as string)).toBe(true);
  });
```

**Mutation, control proved green first** (in the worktree, then reverted — `git status` clean):

```
CONTROL (unmutated):   Tests: 8 passed, 8 total
MUTATION = the only fix that makes the config deployable ( "no" -> "never" ):
    > 163 |     expect(/policy\s*=\s*"no"/.test(workerBlock as string)).toBe(true);
    Expected: true   Received: false
    Tests: 1 failed, 7 passed, 8 total
REVERTED:              Tests: 8 passed, 8 total
```

So the guard is green on a config flyctl refuses, and goes **red on the correction**. A maintainer
who fixes the deploy failure is met with a failing test telling them to put the broken value back.
It asserts the *token the author typed*, not the property *"the worker is not restarted after it
exits"* — the project's own recorded failure mode (`assert-the-property-not-the-mechanism`).

**Also wrong, inside the sentence written to prevent exactly this.** `fly.toml:93-94`:

```
# (`fly deploy`'s default is `on-fail`, which would also allow a clean exit — stated explicitly so
# it cannot drift silently.)
```

`on-fail` is not a fly.toml value either (validated above; the documented default is `on-failure`).
Two wrong policy spellings in one seven-line block, one of them in the clause claiming it cannot
drift silently.

**Fix.**
1. `fly.toml:96` → `policy = "never"` (but read F5 first — `"on-failure"` is probably the right
   choice, and it is *also* valid).
2. `tests/lib/worker-idle-exit.test.ts:163` → assert the property, not the literal.
3. `fly.toml:93` → `on-failure`.
4. ⭐ **The class, not the instance.** Nothing in this repo has ever asked flyctl whether `fly.toml`
   is a valid *Fly* config. `tomllib.load()` proves it is valid *TOML*, which is a different claim,
   and every literal in the file is otherwise guarded by regexes that check what the author wrote
   against no authority at all. Add `fly config validate` as a gate — failing loudly as CANNOT RUN
   when flyctl is absent, never skipping silently.

---

### [Blocking] F2 — the worker's `[[services]]` claims external port **80**, which `[http_service]` already owns. Fly Proxy routes by port and ignores process groups, so this (a) breaks the public website on HTTP and (b) makes the wake a coin flip

**Evidence — Fly's docs, fetched live.**

*Run multiple process groups in an app*:

> "Make sure processes handle connections on different external ports. **Fly Proxy doesn't know
> about process groups; it load-balances requests among all Machines with a service configured on
> the requested port.**"

*App configuration → `http_service`*:

> "An `[http_service]` section defines a service that **listens on ports 80 and 443**. Port 80 will
> have an HTTP handler."

*Connect to an App Service*:

> "If your configuration includes any services for Fly Proxy to route to, and the app has a public
> IP, **that service is exposed to the whole internet**."

**Evidence — the live app.** `fly ips list -a youtube-playlist-summaries`:

```
 v6      │ 2a09:8280:1::152:2a1e:0 │ public ingress (dedicated) │ global
 v4      │ 66.241.124.211          │ public ingress (shared)    │
```

Two public IPs. **No private Flycast IPv6 allocated.** `fly status` confirms exactly one machine per
group: `web 28654674b19d78` (suspended), `worker 8654504a454428` (stopped).

**Evidence — the config.** `fly.toml:37-48` `[http_service]` → web, ports 80+443, `force_https = true`.
`fly.toml:72-89` new `[[services]]` → worker, `[[services.ports]] port = 80, handlers = ["http"]`.

**Why it matters — two distinct consequences, both bad.**

**(a) The public website.** External port 80 is now served by *both* services. Per the quote above,
the proxy load-balances port-80 requests across **all** machines with a port-80 service — one web
machine and one worker machine. Roughly half of all plain-HTTP requests to
`http://youtube-playlist-summaries.fly.dev/` (and to the shared v4, and the dedicated public v6)
will be routed to the worker machine's port 8081, where `startWakeListener` answers **every path and
every method with `200 awake\n`** (`worker/main.ts:196`, and `tests/lib/worker-wake.test.ts:99-107`
asserts precisely that it does). Those requests never reach `force_https`, so the HTTPS redirect is
bypassed too. And since the worker service sets `auto_start_machines = true`, **any anonymous
internet request to port 80 boots the worker machine** — a free cost-amplification and
wake-storm vector against the exact machine this slice exists to keep stopped.

**(b) The wake does not reliably reach the worker.** `WORKER_WAKE_URL = http://<app>.flycast/wake` is
port 80 implicitly (the comment at `fly.toml:85-86` says so). Flycast exposes *"Services configured
in your app's `fly.toml` with an `[http_service]` or `[services]` section"* — i.e. both of them, on
the same port 80. So the poke lands on the **web** machine a large fraction of the time, where
`force_https = true` returns a 301 to `https://<app>.flycast/…` — and Fly's own Flycast page says
**"Flycast is HTTP-only"** and **"Don't use `force_https`."** The poke is swallowed by design
(`worker-wake.ts:47-51`), so this failure is completely silent.

**⭐ This is the finding that breaks the slice's stated safety property.** The brief and the backlog
row both say the slice ships INERT — "nothing happens until someone runs `fly ips allocate-v6
--private` and sets `WORKER_WAKE_URL` / `WORKER_IDLE_EXIT_MS`". That is true of the *idle-exit* and
true of the *poke*. It is **not true of the `[[services]]` block**: the app already has public IPs,
so the port-80 collision arms itself on the next `fly deploy` with no env var, no Flycast IP, and no
further human action. The single change in this diff that can take the website down is the one the
safety argument does not cover.

**Fix — pick one.**
- **Give the worker a distinct external port.** `[[services.ports]] port = 8081` (or any unused
  port), and `WORKER_WAKE_URL = http://<app>.flycast:8081/wake`. This is the smallest change and
  also removes the public-port-80 exposure, though the service is still internet-reachable on 8081
  while a public IP exists.
- **Move the worker to its own Fly app** with no public IP, which is what the design originally said:
  `lib/job-queue/worker-wake.ts:19` gives the example `http://yps-worker.flycast/wake` — a
  *different app* — while `fly.toml:66` says `fly ips allocate-v6 --private --app
  youtube-playlist-summaries` — the *same app*. The two files disagree about the topology, and the
  same-app choice is precisely what creates this collision. Settle it explicitly.

Either way, **do not ship a deploy of this file until the port question is settled**, and re-run
`fly config validate` afterwards (flyctl accepted the duplicate port without complaint — I checked:
with `policy = "never"` the whole file validates clean, so validation is not a defence here).

---

### [High] F3 — the wake fires once per *video*, so one playlist enqueue issues up to **50 sequential** pokes and can add **~75 s** to a user-facing request

**Evidence.** `lib/job-queue/enqueuer.ts:62-66` — `await this.wake()` sits inside `enqueue()`, once
per call. `lib/job-queue/producer.ts:105-108`:

```ts
  for (let i = 0; i < toEnqueue.length; i++) {
    const { videoId, ok: payload } = toEnqueue[i];
    try {
      const { jobId, status, joined: didJoin } = await enqueuer.enqueue(
        ctx, { playlistId, videoId, sectionId: -1, kind: 'summary', version }, payload);
```

A **sequential** loop, bounded by `producer.ts:12` `MAX_VIDEOS_PER_ENQUEUE = 50`. Each iteration
now awaits a POST bounded at `worker-wake.ts:27` `DEFAULT_TIMEOUT_MS = 1_500`.

`app/api/jobs/route.ts:37,54` builds one `SupabaseEnqueuer` and hands it to `enqueuePlaylist` inside
`POST` — so all 50 pokes are on one user request.

**Why it matters.** 50 × 1500 ms = **75 seconds** added to `POST /api/jobs`. And the worst case is
not pathological — it is the *expected* case: the first enqueue after the worker has stopped targets
a **booting** machine, and a connection to a booting machine is exactly what the 1500 ms timeout
exists to bound. The scenario this slice creates is the scenario that hits the tail. Every poke after
the first also buys nothing: the machine is already starting.

The brief's L6 framing ("up to 1500 ms") understates this by a factor of up to 50.

**Fix.** Coalesce. Either hoist one poke to the end of `enqueuePlaylist`/`enqueueDig`, or make
`WorkerWake` self-limiting — at most one in-flight poke, and a short success-suppression window
(e.g. skip if a poke was sent in the last 10 s). The latter keeps the seam where it is and fixes
every caller including future ones.

---

### [High] F4 — a job enqueued in the exit window is stranded with no bound and no recoverer

**Evidence.** `worker/main.ts:154-159`:

```ts
      } else if (deps.idleExitMs !== undefined) {
        idleSince ??= Date.now();
        if (Date.now() - idleSince >= deps.idleExitMs && await queueIsDrained(deps.queue)) return;
      }
```

`return` → `main()`'s `finally` closes the listener (`:268`) → process exits 0 → machine `stopped`.

The window: after `hasQueuedWork()` has returned `false` and before Fly marks the machine `stopped`,
an enqueue can commit its row and poke. The machine is still `started`, so **Fly Proxy starts
nothing** — it routes the poke to a process that is shutting down or gone, and `worker-wake.ts:47-51`
swallows the refusal.

**Nothing recovers it.** I searched the whole tree:

```
$ grep -rn "WORKER_WAKE_URL|workerWakeFromEnv|makeWorkerWake" --include=*.ts --include=*.yml --include=*.toml
```

The only non-test consumer is `lib/job-queue/enqueuer.ts`. There is no pg_cron (`grep -rln
"pg_cron|cron.schedule" supabase/` → nothing), no scheduled workflow that pokes, and the status-poll
path does not wake. So a stranded job waits for **the next unrelated enqueue, by anyone, forever**.
Meanwhile the user who submitted it watches a `queued` spinner with no error anywhere — the silent
failure mode this project's own notes keep flagging as the expensive one.

The probability per enqueue is low (the window is a few hundred ms). The consequence is unbounded and
invisible. That combination is what makes it High rather than Medium.

**Fix.** The cheap, complete one: **make the wake path also reachable from the read side**. The job
status/poll route already runs on the web machine and already knows a job is `queued`; have it poke
when it sees a `queued` job that has not progressed for more than a poll interval or two. That closes
F4 *and* F5's crash case *and* covers any future path that creates work without going through
`enqueue()`. A scheduled poke (GitHub Actions cron, Supabase cron) is the alternative, but it defeats
part of the cost saving and adds a second mechanism for one concern.

Narrowing the window (re-checking `hasQueuedWork()` after the listener closes) does **not** fix this —
it only makes the window smaller, and this project has a whole memory note about proving a negative
by interception never terminating.

---

### [High] F5 — `never` costs crash recovery and buys nothing over `on-failure`; the comment in the file states the premise that refutes the choice

**Evidence.** `fly.toml:91-97`, and Fly's documented semantics (fetched live, quoted in F1):
`on-failure` restarts **only** on a non-zero exit. The worker's idle-exit is `return` → `main()`
resolves → exit **0**. So under `on-failure` an idle exit produces a `stopped` machine, identically
to `never`. The file says so itself at `:93` — *"which would also allow a clean exit"*.

The only behavioural difference is a **crash** (non-zero exit: OOM on Chromium/PDF, an unhandled
rejection, a bad deploy). Today that machine restarts and the sweep reclaims the job within
`SWEEP_MS = 60_000` (`worker/main.ts:81`, with `makeSweepGate`'s `-Infinity` cursor making a fresh
worker sweep immediately). With `never`, the machine goes to `stopped` and — per F4 — **nothing
sweeps while it is stopped**, so the crashed job's `active` row sits with an expired lease until some
unrelated enqueue happens to wake a worker.

So `never` is strictly worse than `on-failure` for this slice's purpose, and the file never says why
it was chosen. This is the brief's L1, **confirmed**.

**Fix.** `policy = "on-failure"` (valid — I validated it), optionally with an explicit `retries` to
bound a crash loop. If `never` really is wanted, the config must say what it buys that `on-failure`
does not, because the sentence currently there says the opposite.

---

### [Medium] F6 — `hasQueuedWork()`'s cost is documented as "once per idle window"; it actually runs once per **poll**, indefinitely

**Evidence.** `lib/storage/job-queue.ts:42-43`:

> *"This is asked only when the worker is deciding whether to shut itself down, so its cost is once
> per idle window."*

`worker/main.ts:156-158`: `idleSince` is **not** reset when the drain check says "not drained". So
once `Date.now() - idleSince >= idleExitMs`, `queueIsDrained()` → `hasQueuedWork()` runs on **every
subsequent iteration**, i.e. every `POLL_MS = 2000` ms, for as long as anything is `queued`-but-
unclaimable (a `run_after` backoff set by `sweep_expired_leases`,
`0009_…:70-72`).

The branch's own test encodes the real behaviour — `tests/lib/worker-idle-exit.test.ts:63`
`expect(calls.hasQueued).toBeGreaterThan(1)` — so the test and the interface docstring disagree, and
the docstring is the wrong half.

**Why it matters.** PR #318 landed three weeks ago because idle worker polling was **100% of the
project's Supabase traffic** at ~79,800 req/day. This adds a second per-poll query in the one state
where the worker will not leave. It is a `count: 'exact', head: true` on `jobs` filtered by
`status = 'queued'` (`supabase-job-queue.ts:105-110`) — and `0008_jobs_queue.sql:32` only indexes
`(lease_expires_at) where status = 'active'`, so there is no index serving this predicate.

**Fix.** Correct the docstring, or reset `idleSince` after a non-drained check so the question really
is asked once per window. Prefer the latter — it makes the documented cost true rather than the
documentation match the accident.

---

### [Medium] F7 — the drain predicate is unbounded in the "stay alive" direction: one long-backed-off job pins the machine up 24/7, silently defeating the slice

**Evidence.** `hasQueuedWork()` counts every `queued` row in the table with no age or bound
(`supabase-job-queue.ts:105-110`). `sweep_expired_leases`
(`0009_job_playlist_identity_and_worker_persistence.sql:68-74`) requeues with
`run_after = now() + 10 * power(4, least(greatest(attempts - 1, 0), 15))` seconds.

At today's prod config this is unreachable (`0011_cost_guardrails.sql` — `summary_max_attempts`
default 1, `dig_max_attempts` default 1; the row dead-letters instead of backing off). But
`guardrail_config` is **data, not code**: raising `dig_max_attempts` to 10 makes the attempt-9 backoff
`10 * 4^8 = 655,360 s ≈ 7.6 days`, during all of which `hasQueuedWork()` returns `true` and the worker
never exits — costing the exact ~$10.60/mo the slice exists to remove, with nothing red anywhere.

**Why it matters.** The failure is *silence in the other direction*, and the tests only exercise the
strand direction. A config change made for an unrelated reason turns the feature off without anyone
being able to connect the two — the same shape as backlog #141's own "the failure mode is silence"
argument.

**Fix.** Ask a bounded question: `queued AND run_after <= now() + <idle window>`, or treat a job whose
`run_after` is further out than some horizon as "not worth staying up for" (it will be picked up on
the next wake, which is exactly the contract for every other stopped-machine case). Either way the
predicate should be derived from the thing it is protecting, not from `status` alone.

---

### [Medium] F8 — `hasQueuedWork()` is blind to an orphaned `active` job, so a woken worker can exit and re-strand it

**Evidence.** The predicate is `.eq('status', 'queued')`. The in-flight status is `'active'`
(`lib/storage/job-queue.ts:5`; `claim_next_job` sets `status='active'`,
`0008_jobs_queue.sql:102`).

Sequence, all steps individually normal:
1. Worker is SIGKILLed mid-job (see F9 — the kill timeout is not what the file thinks it is). Job row
   stays `active`, `lease_expires_at` ~120 s out. Machine `stopped`.
2. Within those 120 s an unrelated enqueue pokes; a worker boots, sweeps
   (`makeSweepGate` starts at `-Infinity`, so it sweeps immediately) — **the lease has not expired
   yet, so nothing is reclaimed**. It claims and finishes the new job.
3. It goes idle. `hasQueuedWork()` → `false` (the orphan is `active`, not `queued`). It **exits**.
4. The lease expires seconds later with nobody left to sweep it.

The orphan is now stranded exactly as in F4, and step 3 is the branch's new code choosing to leave.

**Fix.** The drain question should be *"is there anything a worker would eventually have to do"*, which
includes `status = 'active' AND locked_by <> me` (or simply any `active` row, since a worker exiting
cannot itself be holding one). Cheapest correct form: `status in ('queued','active')`.

---

### [Medium] F9 — `kill_signal` / `kill_timeout` are inside `[http_service]`, not at top level, so the worker's 120 s graceful drain does not exist

**Evidence — the parse tree, not the text.** `python3 -c "import tomllib; …"` on the branch's
`fly.toml`:

```json
  "http_service": {
    "internal_port": 3000, ..., "processes": ["web"],
    "kill_signal": "SIGTERM",
    "kill_timeout": "120s"
  },
```

Lines 53-54 sit *after* the `[http_service]` header (line 37), so TOML puts them **in that table**.
Fly's configuration reference (fetched live): kill_signal and kill_timeout are **top-level app keys** —
*"They control controlled shutdowns such as: When using `fly deploy`; When using `fly machine stop`;
When a machine stops due to `auto_stop_machines`."*

**This is pre-existing on `master`** — the diff shows both as unchanged context. I am reporting it
because this slice's correctness argument leans on it directly: `fly.toml:50-52` says *"Graceful drain:
worker traps SIGTERM (worker/main.ts) → stops claiming, finishes the in-flight job, exits. Give it
time before SIGKILL so a deploy/rollout doesn't strand a reservation."* That guarantee is not in
effect; the worker gets Fly's default kill timeout, and a summary job takes far longer. It is very
likely the mechanism behind backlog **#139** ("every deploy dead-letters the in-flight summary AND
keeps the spend"), which is currently filed as a deploy-trigger problem.

**Fix.** Move `kill_signal` / `kill_timeout` above the first table header (e.g. beside
`primary_region`). One line each. Since this PR is already the one that touches `fly.toml`, and
`fly config validate` is silent about it (it validated clean with `policy = "never"`), it should ride
here. Then re-check #139 against the corrected config before closing it.

---

### [Low] F10 — a post-`listen` error on the wake server is swallowed into an already-settled promise

**Evidence.** `worker/main.ts:186-190`:

```ts
  return new Promise((resolve, reject) => {
    server.once('error', reject);
    server.listen(port, () => {
      ...
      resolve({ port: ..., close: ... });
```

`once('error', reject)` stays attached after `resolve`. The **first** error after the server is
listening calls `reject` on a settled promise — a no-op — and removes the handler. The doorbell can
die (EMFILE, a socket-level failure) with no log, no crash and no signal, leaving a machine that looks
healthy and can never be woken. A **second** error then has no listener at all, which for a
`net.Server` throws.

**Fix.** Attach a durable `server.on('error', …)` that logs after resolve, and decide deliberately
whether a dead doorbell should kill the process (it probably should — a worker that cannot be woken
is worse than one that restarts).

**Related, same function, worth deciding rather than discovering:** a `listen` failure *before*
resolve rejects out of `main()` → non-zero exit → with F5's `never`, the machine is **permanently
bricked** until a human runs `fly machine start`. That is a new startup failure mode this slice
introduces; under `on-failure` it self-heals.

---

### [Low] F11 — the doc comment says the wake URL is read "at call time"; it is read at **construction** time

**Evidence.** `lib/job-queue/worker-wake.ts:55-60`:

```ts
/** The production wake, read from the environment at call time so a deploy can turn it on without
 *  a code change. */
export function workerWakeFromEnv(...)  { return makeWorkerWake(process.env[WORKER_WAKE_URL_ENV], opts); }
```

`process.env` is read when `makeWorkerWake` runs — i.e. when the enqueuer is constructed — and the
`!url` branch is decided **then**, permanently, for that closure.

This is harmless today (see L4 below: both construction sites are per-request), which is exactly why
it should be corrected rather than relied on: the sentence describes a property the code does not
have, and a future module-scope singleton enqueuer would freeze the value at import with the comment
still claiming otherwise.

---

### [Low] F12 — process residue: no dashboard entry, no backlog tick, no deploy doc

- `python3 scripts/check-dashboard-entry.py` →
  `REFUSED — 8 tracked file(s) changed and no entry was added to docs/dashboard-entries.md.`
- `git diff master...HEAD --name-only` touches **no** file under `docs/`. Backlog rows 141 and 142
  (`docs/backlog.md:169,170`) still read *"open — not started"*, against `dev-process.md` Phase 5's
  rule that status ticks ride in the same PR.
- `grep -n "flycast|Flycast|WORKER_IDLE_EXIT_MS|allocate-v6|min_machines_running" docs/deploy.md`
  → **no matches**. The two new env vars and the one-off `fly ips allocate-v6 --private` exist only in
  code comments and a backlog row. The operator instructions for turning this on are not in the
  operator document.

---

## Leads L1–L7 — confirmed or refuted

- **L1 — `policy = "no"` threw away crash recovery for nothing** — **CONFIRMED, and worse than
  stated.** `on-failure` restarts only on non-zero exit, so it permits the clean idle exit identically;
  `never` differs *only* by losing crash recovery, and the file's own comment says so (F5). The lead
  did not anticipate that `"no"` is not a valid fly.toml value at all (F1).
- **L2 — an exit/enqueue race may strand a job** — **CONFIRMED, and nothing recovers it.** It waits
  for the next unrelated enqueue by anyone, unbounded; there is no cron, no scheduled poke, and the
  status-poll path does not wake (F4).
- **L3 — `hasQueuedWork()` only counts `queued`** — **CONFIRMED, with a concrete sequence.** An
  orphaned `active` row whose lease has not yet expired is invisible to the drain check, so a woken
  worker can finish other work and exit before the lease expires, re-stranding it (F8). The status
  literal is `'active'`, not `'running'` as the lead assumed.
- **L4 — `workerWakeFromEnv()` as a default parameter freezes `process.env`** — **REFUTED as a live
  defect.** Both non-test construction sites are inside request handlers —
  `app/api/jobs/route.ts:37` (inside `POST`) and `app/api/videos/[id]/dig/[sectionId]/route.ts:60`
  (inside the handler) — so the env is read per request. The *doc comment* is still wrong (F11).
- **L5 — `server.listen(port)` with no host may not receive Flycast traffic** — **REFUTED,
  empirically.** `node -e "http.createServer(...).listen(0, ...)"` → `address(): {"address":"::",
  "family":"IPv6"}`. Node binds the unspecified IPv6 address dual-stack when no host is given, which
  covers 6PN/Flycast IPv6 and IPv4. (Measured on Node v20.18.2 locally; the image runs Node 22, same
  documented behaviour.) Note this makes the listener reachable on every interface, which is what
  makes F2(a)'s public exposure bite.
- **L6 — the wake adds up to 1500 ms and fires on `joined: true` too** — **CONFIRMED and materially
  understated**: it is up to **50 × 1500 ms** on one playlist request (F3). On the `joined` half
  specifically: poking on a join is *defensible* — the previously-enqueued job may itself be stranded
  by F4, and the poke is the only thing that would recover it — so I would not remove the join case;
  I would coalesce the fan-out, which fixes the cost without removing the recovery.
- **L7 — `await sleep(pollMs)` runs only on idle, and the exit check sits before it** — **REFUTED as
  an off-by-one; CONFIRMED as a cost bug.** The arithmetic is right: `idleSince` is set on the first
  idle poll and the exit needs `elapsed >= idleExitMs`, so the worker waits at least the window. Two
  true consequences worth writing down rather than leaving implicit: (i) the effective granularity is
  `POLL_MS`, so `idleExitMs < pollMs` still yields a first exit no earlier than one poll — harmless,
  but undocumented; (ii) `idleSince` is never reset after a *failed* drain check, which is F6.

---

## The author's own pre-round fix — checked adversarially

The `[[services.ports]]` sub-table added in `5aca44a6` is **correct as far as it goes**: Fly's
reference does require at least one `services.ports` entry per `services` section, and the service
without it really would have been inert.

But the fix is **instance, not class**, and it introduced F2. The question *"is there any other part
of this config that is declared but unreachable in the same way?"* was the right question and the
answer was found by reading the reference — while the adjacent question, *"is this port already
spoken for?"*, has an answer in the same document family and was not asked. Answering both mechanically
costs one command, `fly config validate`, which nothing in this repo runs (F1 fix 4).

Two sub-answers the brief asked for explicitly:

- **`internal_port = 8081` agrees with `WAKE_PORT`** — ✅ verified, `worker/main.ts:172`
  `export const WAKE_PORT = 8081;`, and pinned by `tests/lib/worker-idle-exit.test.ts:140-152`.
  That guard reads the *right* literal, unlike the restart one.
- **`port = 80` + `http` "agrees with `WORKER_WAKE_URL`"** — ✅ internally consistent, ❌ not
  *correct*, because agreeing with the URL was the wrong thing to check. See F2.

## Things I checked and found correct — stated plainly

- **`auto_stop_machines` omitted from the worker service is safe.** Fly's reference: *"The default if
  not set is `"off"`."* The comment at `fly.toml:68-71` asserting the proxy may start but never stop
  this machine is **true**, and the reasoning behind it (autostop documents `soft_limit` concurrency
  and says nothing about in-flight requests blocking a stop) is sound.
- **The enqueue→wake ordering is right**, and `tests/lib/worker-wake.test.ts:124-137` pins it by
  observed order, not by mocking a sequence. The failure path (`:139-147`) correctly does *not* poke.
- **`queueIsDrained`'s fail-safe direction is right** (`worker/main.ts:210-215`): an unanswerable
  question resolves to "not drained". The asymmetry argument in its docstring is correct and the test
  at `tests/lib/worker-idle-exit.test.ts:70-85` exercises it through a real throw.
- **The idle clock resets on work** (`worker/main.ts:154-155`), pinned at `:87-116` by a test that
  asserts `hasQueuedWork` was *never called* while work kept arriving — a good negative assertion.
- **`idleExitMsFromEnv`** refuses `''`, non-numeric, `0` and negatives, and logs rather than silently
  defaulting to an immediate exit (`worker/main.ts:179-187`).
- **`hasQueuedWork` reading `jobs` directly rather than via an RPC is not a new pattern** —
  `getStatus` (`supabase-job-queue.ts:8`) and `listByPlaylist` (`:24`) already do. `npx tsx
  scripts/check-service-confinement.ts` → `service_role confinement OK`.
- **`npm test` 2860/277 green, `tsc --noEmit` clean, `check-docs.py` → `Documentation integrity OK`.**

---

## What I could not run — treat every line here as NOT VERIFIED

- **No live Fly end-to-end.** I did not allocate a private IPv6, did not deploy, and did not set
  `WORKER_WAKE_URL` / `WORKER_IDLE_EXIT_MS`. F2's routing consequence is derived from Fly's own
  documentation plus `fly ips list` and `fly status` on the live app — it is **not** an observed
  packet. The doc sentence it rests on is unambiguous (*"Fly Proxy doesn't know about process groups;
  it load-balances requests among all Machines with a service configured on the requested port"*) and
  the app demonstrably has public IPs, but the specific split of traffic is inference. The falsifier
  is cheap and should be run before merge: deploy to a scratch app with the same two services on port
  80, curl port 80 twenty times, count how many say `awake`.
- **`fly config validate` does not check routing.** It accepted the duplicate port 80 without comment
  (the file validates clean with `policy = "never"`). Its green says nothing about F2.
- **No integration or e2e suite** (`test:integration`, `test:e2e` need a live Supabase stack). The new
  `hasQueuedWork()` SQL path has therefore never executed against a real Postgres — its behaviour is
  only asserted against hand-written fakes in `tests/lib/worker-idle-exit.test.ts`. In particular the
  `count: 'exact', head: true` PostgREST call shape is unverified end to end.
- **F9's consequence is inferred, not measured.** I established from the parse tree that
  `kill_timeout` lands inside `http_service`; I did **not** observe what Fly does with an unknown
  field there, nor measure the actual SIGKILL delay on the running worker. That `#139` is caused by
  this is a hypothesis with a good motive, not a result.
- **Node bind behaviour measured on v20.18.2 locally**, not on the Node 22 image the Dockerfile ships.
- **I did not read the Codex half** (`docs/reviews/coordinator/142-wake-on-visit-r1-codex.md` was
  already on disk when I started); this review is independent of it.
