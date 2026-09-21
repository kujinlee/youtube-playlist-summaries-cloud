# Claude adversarial review — backlog #142 wake-on-visit — round 2

## Verdict: FINDINGS

1 High, 5 Medium, 6 Low. Subject: `git diff b98d370f..HEAD`, HEAD = `ca586477`, worktree
`.../5cbc47e9-.../wt142`. Both fold commits reviewed (`1d2a4ebc` = round 1's findings,
`ca586477` = Codex round 2's).

**The one-sentence verdict on Codex's fixes: Medium 1 is closed in substance and wrong in its
stated mechanism** — the process does now exit, but it exits by **aborting the in-flight job**, not
by "finishing" it, which is the behaviour backlog #139 filed as 🔴 three weeks ago. Medium 2 is
correctly left open with the human; my independent read agrees it is unsafe, disagrees with the
mechanism Codex gave, and **refutes one of Codex's two proposed fixes using Fly's own docs**.

---

## Re-derivation of the claims

Every claim in `ca586477` was re-derived independently. All five hold.

| Claim | Result | Evidence |
|---|---|---|
| `npx tsc --noEmit` clean | ✅ **matched** | exit 0, no output |
| `npm test` = 2882 tests / 278 suites | ✅ **matched** | `Test Suites: 278 passed, 278 total` / `Tests: 2882 passed, 2882 total` / `Snapshots: 1 passed` / 34.049 s |
| `fly config validate` (both files) | ✅ **matched** | `✓ Configuration is valid` for `fly.toml` and for `-c fly.worker.toml`, flyctl v0.4.87 |
| M11, M13, M14 killed by tests | ✅ **matched** | see below |
| M12 killed by the COMPILER | ✅ **matched** | `worker/main.ts(323,26): error TS2554: Expected 1-2 arguments, but got 0.` |

Mutations, each applied over the green control above and reverted individually:

```text
M11  delete `onFatal?.();` from the post-bind handler (worker/main.ts:258)
     → npm test tests/lib/worker-wake.test.ts: 1 failed, 20 passed        KILLED
M12  revert the call site to `startWakeListener()` (worker/main.ts:323)
     → npx tsc --noEmit: error TS2554: Expected 1-2 arguments, but got 0  KILLED (compiler)
M13  delete `if (!server.listening) return res2();` (worker/main.ts:271)
     → npm test tests/lib/worker-wake.test.ts: 1 failed, 20 passed        KILLED
M14  fly.worker.toml auto_start_machines = true -> false
     → npm test tests/lib/worker-idle-exit.test.ts: 1 failed, 13 passed   KILLED
```

I also re-ran round 1's previously-surviving mutation, because the brief asked whether the
replacement test genuinely isolates that branch:

```text
lib/job-queue/worker-wake.ts:85   if (inFlight) return inFlight;
                               -> if (false && inFlight) return inFlight;
     → npm test tests/lib/worker-wake.test.ts: 1 failed, 20 passed        KILLED
```

It does isolate it. The mechanism is in the test's own comment and it is correct: `suppressMs: 10`
is tuned *below* the request duration and the injected clock is advanced past it, so suppression has
already expired while the first request is still open, and only the in-flight join can prevent the
second `fetch`. Reverted; `git status --short` shows only this review file.

And two mutations of my own that **survived** — those are findings 3 and (in the killed direction)
7 below.

---

## Findings

### [High] 1 — The fix's own justification is false: `onFatal` does not let the in-flight job finish, it aborts it — and that makes a fourth, unrecorded trigger for open backlog #139

**Evidence.** `worker/main.ts:247-254` states the mechanism the fix rests on:

```
 *  ⭐ AND `onFatal` IS WHAT MAKES THAT MORE THAN A LOG LINE (review r2, Codex Medium 1). ...
 *  `onFatal` aborts the shutdown signal, so the loop finishes its in-flight job and returns
 *  through the normal drain path, and the non-zero exit then brings the machine back under
 *  `on-failure`.
```

`main()` wires it at `worker/main.ts:323` as `startWakeListener(() => ac.abort())`, and `ac.signal`
is also `runWorkerLoop`'s `shutdownSignal` (`worker/main.ts:326`), which `runOnce` folds straight
into the **handler's** signal:

```ts
// lib/job-queue/worker-runner.ts:99-101
const signal = AbortSignal.any(
  [wallClock.signal, leaseLost.signal, opts.shutdownSignal].filter(...),
);
```

I drove the real path — `startWakeListener(() => ac.abort(), 0)`, then `runOnce` with that
`ac.signal`, then `listener.server.emit('error', …)` from inside a handler that watches `ctx.signal`
the way the summary handler does. Measured output:

```text
PROBE handlerSawAbort= true handlerFinished= false outcome= failed
fail args= [["j1","probe","t","The operation was aborted",
            {"retryable":true,"billableSucceeded":true,"metered":false}]]
```

So: the handler is **aborted**, it does not finish, and `fail_job` is called with
`billableSucceeded: true`. `supabase/migrations/0008_jobs_queue.sql:153-156` then decides:

```sql
elsif v_attempts >= v_max then v_new := 'dead_letter';
```

and `attempts` is already ≥ 1 (incremented at claim time), with the **measured live**
`summary_max_attempts = 1`. That is `dead_letter` on the first occurrence, money kept.

This is not a new discovery — it is `docs/roadmap-to-launch.md:461-470`, open, 🔴:

> **backlog #139 — 🔴 a deploy kills the summary it interrupts AND keeps the money.** `fly.toml:45-46`
> promises the worker *"finishes the in-flight job"* on SIGTERM … **It does not**: `shutdownSignal`
> is folded into the handler's signal, so the handler **aborts** … ⚠ Fixing only SIGTERM leaves the
> other two — instance-not-class.

The branch does three things with that sentence, none of them correcting it:

| Where | What | Introduced by |
|---|---|---|
| `fly.toml:21-22` | **relocated** the exact sentence #139 quotes as false (verbatim from `master:fly.toml:45-46`), while editing those very lines for r1 F9 | round 1's fix |
| `fly.worker.toml:38-39` | a **new verbatim copy** of it in a brand-new file | round 1's fix |
| `worker/main.ts:253-254` | a **third statement** of it, as the justification for the r2 fix | round 2's fix |

**Introduced by an earlier round's fix?** Yes — two of the three copies, and the third is r2's.

**Why it matters.** Not because `process.exit(1)` would be better; it would not (an abandoned
`active` row is swept at lease expiry and `sweep_expired_leases` dead-letters at
`attempts >= max_attempts` too). It matters because (a) the comment is what a future reader will
cite when deciding whether this path is safe, and it says the opposite of what the code does; and
(b) #139's row explicitly warns that fixing one trigger and leaving the others is
instance-not-class — there were three, and this fix quietly makes four, with nothing written down.
The honest version of the fix is that it chose the **only** behaviour available today, and the
better behaviour needs a second controller (stop claiming, let the current job finish, then exit
non-zero) — which is exactly the design call #139 is holding open.

**Fix.** Three lines of prose and one backlog edit, no behaviour change:
1. `worker/main.ts:253-254` — say what it does: *aborts the in-flight job, which with
   `summary_max_attempts = 1` dead-letters it and keeps the charge (backlog #139); accepted because
   an unwakeable Machine is worse, and because `process.exit(1)` loses the same job via the sweep.*
2. `fly.worker.toml:38-39` — do not copy the disproven sentence into a new file; state the measured
   behaviour and point at #139.
3. Add this trigger to #139's row — it now has four, and one of them fires with no deploy involved.

### [Medium] 2 — Round 1's Codex Medium 3 (`server.listen` has no host) was dropped with no fix and no written declination, while the fold commit says it folded everything

**Evidence.** `worker/main.ts:240` is unchanged in both fold commits:

```ts
server.listen(port, () => {
```

`grep -rn "0\.0\.0\.0"` over the tree returns hits in `app/auth/callback/route.ts`, three test
files, `docs/deploy.md:158`, `docs/dashboard-entries.md:9434` and
`docs/reviews/coordinator/142-wake-on-visit-r1-codex.md` — **and nothing in `worker/`**. The
commit message of `1d2a4ebc` opens with *"Folds every finding from review round 1"* and its
section headers cover F1–F9 (+F2 topology); Codex's r1 Medium 3 and its L5 restatement appear
nowhere in either commit message, in `docs/deploy.md`, or in the code.

Fly's live docs, on the blueprint this design is an implementation of:

> "To be reachable by Fly Proxy, an app needs to listen on `0.0.0.0` and bind to the
> `internal_port` defined in the `fly.toml` configuration file."
> — https://fly.io/docs/blueprints/autostart-internal-apps/

**Introduced by an earlier round's fix?** No — it is round 1's finding, unclosed.

**Why it matters.** Two separate things, and only the second is certain. (i) The substance is
**probably benign**: Node with an omitted host binds `::` dual-stack, and on Linux with the default
`net.ipv6.bindv6only=0` that accepts IPv4 connections too, so Fly Proxy's IPv4 hop would land. I
could not test this inside a Fly Machine, so it stays a probability. (ii) The **process** failure
is certain: a Medium from a review half was dropped silently, and the commit that dropped it claims
completeness. If the bind is genuinely fine, that is a one-sentence declination in the fold commit;
if it is not, the symptom is the whole feature being inert with nothing red — the exact failure
mode `tests/lib/worker-idle-exit.test.ts:162-169` was written to prevent.

**Fix.** `server.listen(port, '0.0.0.0', …)` and assert `server.address().address` in the existing
listener test — it costs one argument and removes the question. If the decision is to keep `::`,
write the declination down with the reason, because the next reviewer will file it again.

### [Medium] 3 — `kill_signal` / `kill_timeout`: r1 F9 pinned the POSITION and left the VALUE unpinned. `SIGTERM → SIGKILL` survives the suite and `fly config validate`

**Evidence.** Mutation over the proved-green control:

```text
MUTATION  fly.worker.toml  kill_signal = "SIGTERM"  ->  "SIGKILL"
npm test -- tests/lib/worker-idle-exit.test.ts tests/lib/worker-wake.test.ts
    Test Suites: 2 passed, 2 total
    Tests:       35 passed, 35 total            SURVIVED
fly config validate -c fly.worker.toml
    ✓ Configuration is valid                   SURVIVED
```

The guard that exists for these two keys is `tests/lib/worker-idle-exit.test.ts:269-281`, and it
asserts only that each key appears **above the first table header**. Nothing reads the value. The
same hole applies to `kill_timeout = "120s"` → `"1s"`, and to both files.

**Introduced by an earlier round's fix?** Yes — r1 F9's fix. The finding was *"the keys are in the
wrong table, so the 120s drain has never been in effect"*, and the test written for it proves the
placement rather than the property the placement exists to deliver.

**Why it matters.** `SIGKILL` cannot be trapped, so the worker's `process.on('SIGTERM')` handler
(`worker/main.ts:318`) never runs: every deploy kills the in-flight job outright and leaves an
`active` row to be swept and dead-lettered. That is strictly worse than the state r1 F9 was
correcting, it is one character, and both the position test and `fly config validate` say
"configuration is valid". This is the project's own *"assert the PROPERTY, not the mechanism"* shape.

**Fix.** In the same loop that already checks position, also assert
`kill_signal = "SIGTERM"` and a `kill_timeout` of at least the lease (120s) — both files.

### [Medium] 4 — Both `void wake()` call sites depend on `wake` never rejecting, and the test that names that hazard is green only because it returns before the rejection lands

**Evidence.** `app/api/jobs/route.ts:92` and `lib/job-queue/enqueuer.ts:72` both fire the poke with
a bare `void` and no `.catch()`. `tests/api/jobs-route-wake.test.ts:90-98` is the test that claims
to cover it:

```ts
// Break this catches: a poke that can 500 the poll. `wake` is built never to reject, but the call
// site must not depend on that being true forever — an un-awaited rejection would otherwise become
// an unhandled rejection and, depending on Node's settings, take the process down.
test('a rejecting wake does not break the response', async () => { … expect(status).toBe(200); });
```

I copied that test verbatim into a probe file and added **one** line — `await new Promise(r =>
setTimeout(r, 50))` after the assertion. It goes red:

```text
FAIL tests/api/zz-r2-probe3.test.ts
    flycast unreachable
      at GET (app/api/jobs/route.ts:92:72)
Tests: 1 failed, 1 total
```

So the suite is *not* blind to unhandled rejections (a `void Promise.reject(…)` probe also fails);
this test passes solely because it returns before the microtask queue is drained. And the
consequence the comment describes is real, measured locally:

```text
$ node -e 'const p=Promise.reject(new Error("boom")); void p; setTimeout(()=>console.log("STILL ALIVE"),100);'
Error: boom            → "STILL ALIVE" never printed, exit 1
```

**Introduced by an earlier round's fix?** Yes — round 1's F3 fix is what changed
`await this.wake()` to `void this.wake()`, and this test was added with it.

**Why it matters.** The hazard is **latent, not live**: `makeWorkerWake`'s `send()` swallows
everything (`lib/job-queue/worker-wake.ts:73-77`), and both production construction sites use the
default wake (`app/api/jobs/route.ts:39`, `app/api/videos/[id]/dig/[sectionId]/route.ts:60`), so
nothing can reject today. What is wrong now is the guard: the call site *does* depend on a
promise-never-rejects invariant enforced one module away, and the test that exists to stop that
dependency from mattering is passing for an ambient reason — the second such case on this branch
(the first was the `inFlight` mutation round 1 caught).

**Fix.** `void this.wake().catch(() => {})` and `void workerWakeFromEnv()().catch(() => {})`, and
add the 50ms settle to the existing test so it measures what it claims.

### [Medium] 5 — "`yps-worker` must never have a public IP" is the entire security argument for r1 F2's fix, and nothing anywhere asserts it

**Evidence.** The claim is made three times — `fly.worker.toml:23-26`, `fly.toml:63-71`,
`docs/deploy.md` Step 5 — always as prose plus a runbook instruction (`fly ips allocate-v6
--private`). `tests/lib/worker-idle-exit.test.ts:296-301` pins the repo-side half (fly.toml
declares no `[[services]]`), and that is genuinely good. But the property that makes the *new* app
safe is platform state, not file state, and no check reads it. The commands exist and are correct in
this flyctl (v0.4.87): `fly ips allocate-v6 --private` (`--private  Allocate a private IPv6
address`) and `fly ips list`.

**Introduced by an earlier round's fix?** Yes — r1 F2 was a Blocking about internet exposure, and
its fix replaces "a port collision you must avoid" with "an IP allocation you must not make".

**Why it matters.** A single `fly ips allocate-v4 --app yps-worker` — the reflex when someone wants
to curl the doorbell to debug it — re-creates the whole of r1 F2: `auto_start_machines = true` on a
service reachable from the internet, which by the file's own argument *"cannot be defended in
application code, because the proxy boots the Machine BEFORE our process sees the request."* Under
CLAUDE.md's rule, this is a decision, not a gate: it names no observation that would make it fail.

**Fix.** The repo already has exactly one scheduled gate for the class of thing no push
corresponds to — `prod-drift` in `.github/workflows/schema-gates.yml`. One line there, or in the
Step 3b smoke list: `fly ips list --app yps-worker` must show no public address, and CANNOT RUN
(no token) must fail rather than pass.

### [Medium] 6 — The runbook's falsifier does not require the old worker Machine to be stopped, so the one step that proves the new worker can do work can be satisfied by the old one

**Evidence.** `docs/deploy.md` Step 5:

> **Falsifier — the whole feature, in one pass.** With both Machines stopped: visit the site (the
> web machine resumes), request a summary, and confirm `fly status --app yps-worker` reaches
> `started` with no human action, the summary completes, and the Machine returns to `stopped`
> afterwards.

"Both Machines" is web + `yps-worker`. The old `worker` group in `fly.toml:44-46` + `:80-83` is
never mentioned in the six numbered commands; the instruction to stop it appears only in the prose
section below them, *after* the falsifier. Today that Machine exists and runs (roadmap release-v10
note: *"worker `7811d65df64328`"*).

**Introduced by an earlier round's fix?** Yes — r1 F4/F2's fix wrote this runbook.

**Why it matters.** If the old worker is still running when the falsifier is executed, three of its
four observations still pass for the wrong reason: `yps-worker` reaches `started` (the poke does
that on its own), *"the summary completes"* (the old always-on worker claims it), and *"returns to
`stopped`"* (the new worker finds an empty queue and idles out). The falsifier would be green over
a `yps-worker` that has never successfully processed a single job. This is the *"green check over
the wrong subject"* shape, in the one gate that stands between this feature and production.

**Fix.** Make stopping the old Machine step 0 of the six, and add an observation only the new
worker can satisfy — e.g. the completed job's `locked_by` (the worker id is
`${os.hostname()}-${pid}-…`, `worker/main.ts:315`) must be a `yps-worker` host, or check
`fly logs --app yps-worker` for the claim.

### [Low] 7 — `fly config validate` found round 1's Blocking and runs nowhere automatically

**Evidence.** `grep -rn "fly config validate\|flyctl\|superfly" .github/workflows/ scripts/check-schema-gates.sh` → **zero hits**. The only instruction to run it is prose in `docs/deploy.md`
("Before editing either Fly config") and the same in `fly.worker.toml:84-85`. It is also the only
gate that catches a whole class: I mutated `fly.worker.toml`'s `[processes] worker =` to
`jobrunner =`, leaving every `processes = ["worker"]` filter pointing at a group that no longer
exists — the unit tests stayed **35/35 green** (they find the block *by* that filter, which is
still there) and `fly config validate` returned `✘ invalid app configuration`. That is a config in
which the service, the restart policy and the VM sizing all attach to nothing and the wake is dead.

**Why it matters.** r1's F1 Blocking (`policy = "no"`) was found by a human typing this command,
over a suite of 2,860 green tests that were *defending* the invalid value. Nothing has changed about
how the next one gets caught.

**Fix.** `superfly/flyctl-actions/setup-flyctl` + `fly config validate` on both files is a ~5s CI
step needing no token (validation is local — I ran it against `fly.worker.toml` with a bare relative
path). Or, if CI-installing flyctl is unwanted, say in `dev-process.md` that this is a **manual**
gate and which build it was last verified against.

### [Low] 8 — `onFatal?.()` is an optional call on a parameter whose docstring exists to say it is required

**Evidence.** `worker/main.ts:258` is `onFatal?.();`, thirty lines below
`worker/main.ts:226-235`, whose entire subject is *"`onFatal` IS REQUIRED … Making it required
moves the failure from 'a test might catch it' to 'it does not compile'"*, and whose signature is
`onFatal: () => void` (non-optional). The `?.` is a leftover from the version that was optional.

**Introduced by an earlier round's fix?** Yes — round 2's, as residue of its own first attempt.

**Why it matters.** Small, but in the one direction that matters here: it re-admits the exact
mutation M12 is supposed to make unwritable, via `startWakeListener(undefined as never)` or a
JS caller. It also makes the code disagree with the comment a reader is relying on.

**Fix.** `onFatal();`.

### [Low] 9 — The idempotence comment justifies itself with a code path the same commit deleted

**Evidence.** `worker/main.ts:266-269`:

```
// ⚠ IDEMPOTENT. `main()` closes this in a `finally`, and the fatal path above can already
// have brought the server down; …
```

The fatal path above no longer closes anything: `ca586477` removed `server.close()` from it (diff:
`-        server.close();` / `+        onFatal?.();`). `http.Server` does not close itself on an
`error` event, so after a post-bind error the doorbell is normally **still listening** until
`main()`'s `finally` closes it.

**Introduced by an earlier round's fix?** Yes — round 2's.

**Why it matters.** The property is worth keeping (M13 proves a test defends it, and `close()` can
still meet a self-closed socket), so this is documentation only — but the stated reason is the kind
a future reader would cite to *remove* the guard once they notice the fatal path does not close.
Worth noting as a behaviour change nobody wrote down: leaving the doorbell open during the drain is
arguably better (wakes are still answered while the machine is on its way out), and it is now true
by accident rather than by decision.

**Fix.** Re-state the reason as the one that is true (a server may have closed itself; `main()`'s
`finally` must never reject and bury the original error), and say the fatal path deliberately
leaves the listener up.

### [Low] 10 — `WAKE_PORT`'s docstring points at the file that now states the opposite

**Evidence.** `worker/main.ts:185-186`: *"Must match `internal_port` of the worker service in
fly.toml, or Fly Proxy has nowhere to route."* `fly.toml:63-71` now says **"⚠ NO WORKER SERVICE
HERE, AND THAT IS THE DECISION, NOT AN OMISSION"**, and the invariant lives in
`fly.worker.toml:75` — which is also what the test reads
(`tests/lib/worker-idle-exit.test.ts:201`).

**Fix.** `fly.worker.toml`.

### [Low] 11 — "a predicate no index serves" is asserted twice and is probably false

**Evidence.** `worker/main.ts:163` and `tests/lib/worker-idle-exit.test.ts:118-119` both state that
the drain COUNT runs *"on a predicate no index serves"*. The query is
`.in('status', ['queued','active'])` with `count: 'exact', head: true`
(`lib/storage/supabase/supabase-job-queue.ts:107-111`). The schema has two partial indexes that
between them cover exactly that predicate:

```sql
-- supabase/migrations/0008_jobs_queue.sql:31-32
create index jobs_claim on jobs (run_after, created_at, id) where status = 'queued';
create index jobs_sweep on jobs (lease_expires_at)          where status = 'active';
```

A `BitmapOr` of two partial index scans is available to the planner. I did **not** run `EXPLAIN`, so
this is "unverified in the other direction" rather than a refutation.

**Why it matters.** The fix (reset the idle clock) is right regardless — the cost that mattered was
~43,200 round trips/day, which is network and PostgREST, not plan shape. But the sentence is the one
a future reader will cite when deciding whether this query is cheap, and the project's rule is to
measure the constraint rather than assert it.

**Fix.** Either `EXPLAIN` it against the schema-gates container and state the plan, or cut the
clause — the request count carries the argument on its own.

### [Low] 12 — The dashboard entry, which is the artifact the human reads before deciding, is a round behind

**Evidence.** `docs/dashboard-entries.md` (entry dated 2026-09-18): *"2879 tests / 278 suites"* —
the roadmap was updated to **2882** in the same commit (`ca586477` touches
`docs/roadmap-to-launch.md:2040`) and the entry was not. The entry describes round 1 only
(*"Review round 1: 2 Blocking, 3 High, 4 Medium, 3 Low; 10 mutations"*), and its **Waiting on you**
section names only the six-command decision — not the decision `ca586477`'s own commit message says
it is escalating (*"Going back to the human, since leaving it was my recommendation and the
argument for it no longer holds"*).

**Why it matters.** `check-test-counts.py` pins the roadmap's numbers, not the dashboard's, so the
two documents now disagree with nothing to notice it; and the Ask tray is where a decision waiting
on the human is supposed to be visible.

**Fix.** Update the count, add one line for round 2, and put the process-group decision in the
**Waiting on you** section.

---

## Codex round 2's two findings — closed, partly closed, or not closed

### Medium 1 (listener error does not cause an exit) — **PARTLY CLOSED**

Closed: the process now does exit. Verified end-to-end rather than by reading —
`onFatal` → `ac.abort()` → `runWorkerLoop`'s `while (!deps.shutdownSignal.aborted)` returns →
`finally` closes the listener → `main()` resolves → `process.exitCode = 1` is the exit code. Three
sub-cases all terminate: mid-`sleep` (the abort-aware `sleep` at `worker/main.ts:116-123` resolves
early), mid-`runOnce`, and *before* the loop is entered (the loop sees an already-aborted signal and
returns immediately). `close()` idempotence is real and tested (M13 kills it).

Not closed: **the mechanism the fix documents is not the mechanism it has** — finding 1 above. The
loop does not "finish its in-flight job"; it aborts it, dead-letters it under
`summary_max_attempts = 1`, and keeps the charge. Codex's own suggested alternative
(`process.exit(1)`) would lose the same job via the lease sweep, so the *choice* is fine; the
*description* is what is wrong, plus the missing #139 entry.

On the brief's two sub-questions:
- **Can this `ac.abort()` be confused with a real SIGTERM?** Structurally yes — both are a bare
  `ac.abort()` with no reason, and only the `console.error` at `worker/main.ts:256` distinguishes
  them (nothing asserts that line is emitted). The one place it bites: `process.exitCode` is
  process-global and monotonic here, so once the fatal path has set it to 1, a *subsequent*
  deliberate stop also exits 1 and Fly's `on-failure` restarts a Machine that was meant to stay
  stopped. Cost is one boot; reachability is low (the doorbell must fail first). Not filed.
- **Is `process.exitCode = 1` still correct now the loop drains normally?** Yes, and it is now the
  load-bearing half: nothing calls `process.exit()`, so this is the only thing that makes the exit
  non-zero, and `fly.worker.toml:106-108`'s `on-failure` is the only thing that turns non-zero into
  a restart. Both are pinned by tests.

### Medium 2 (transitional `worker` process group) — **NOT CLOSED, deliberately, with the human.** My independent read is below.

---

## The transitional worker process group — my independent read

**Conclusion: the transitional state is not safe, I agree with Codex's severity, I do not agree
with the mechanism it gave, and one of its two proposed fixes is refuted by Fly's own docs.**

What the docs actually support, quoted:

> "`fly deploy` creates at least one Machine for each process group, and destroys all the Machines
> that belong to any process group that isn't defined, in your app's `fly.toml` file." … "on the
> first deployment … flyctl creates and starts at least one Machine for each process group in
> `fly.toml`." … "If you add new process groups in an app's `[processes]` block, then the next
> `fly deploy` spins up at least one new Machine to run each new process."
> — https://fly.io/docs/launch/processes/

> "If there are no existing Machines, then `fly deploy` seeds the app with new Machines in the
> `primary_region` and according to the `[processes]` configured in your `fly.toml` file."
> — https://fly.io/docs/apps/scale-count/ (the page's worked example scales `web=0 worker=0` and a
> plain `fly deploy` brings both groups back)

CLI evidence from the pinned flyctl (v0.4.87), which confirms the default from the other direction:

```text
--update-only        Do not create Machines for new process groups
--process-groups     Deploy to machines only in these process groups
```

**Where Codex is right.** The group is not passive. Any state in which the web app has *no* worker
Machine is one the platform actively refills on the next `fly deploy`, documented. And Codex is
right that a passive doc warning is not a mitigation.

**Where Codex overstates.** Its sentence is *"a normal `fly deploy` creates/starts a Machine for
every declared process group"*, and the runbook's actual instruction is *"keep the old worker
Machine `stopped`"* — a Machine that **exists**. For that case the docs Codex cites say only
"creates", and creation does not apply; the "starts" language is scoped to the *first* deployment
and to *newly added* groups. I could not verify whether flyctl restarts an existing stopped Machine
during a rolling update: Fly's docs do not address it, and the closest live evidence points the
other way — a community report that on deploy *suspended* Machines "get updated and then stopped",
i.e. flyctl updates in place and does not leave them running
(https://community.fly.io/t/suspended-machines-are-stopped-on-new-deploy/24592). **Treat the
stopped-Machine case as NOT VERIFIED in either direction.**

**Where I think both of us were looking at the wrong hazard.** The dangerous property is not that a
deploy starts the old worker; it is that *"no worker in the web app"* has no stable representation:

- destroy it or `fly scale count worker=0` → the next web deploy **seeds it back and starts it**
  (documented above);
- leave it stopped → it is one `fly machine start`, one host migration, or one operator poking at
  the dashboard away from running, and nothing observes that;
- and if it does come up, it comes up **with `WORKER_IDLE_EXIT_MS` unset**, because `docs/deploy.md`
  step 6 sets that secret on `yps-worker` only. So the duplicate does not idle out. It is a
  permanently-running second consumer — precisely the ~$10.60/mo and the idle Supabase traffic this
  slice exists to remove — while every user-visible symptom stays green, because jobs *do* get done.

**Why it is not Blocking.** The whole feature ships inert (no `WORKER_WAKE_URL`, no
`WORKER_IDLE_EXIT_MS`), and two workers on this queue is lease-safe by construction — `claim_next_job`
fences by lease token and `fail_job`/`complete_job` are fenced writes. The cost of the transitional
state is money and duplicated polling, not corruption.

**What I would do, which is neither of Codex's options.** Codex's option (b) — *"add an explicit
deploy step that scales the old app's worker group back to zero immediately after any web
deploy"* — **is the worst of the available choices and should be dropped**: zero Machines is the
one state Fly's scale-count page documents a deploy as refilling, so that step would have to be
re-run after every deploy forever, and forgetting it produces a *started* worker rather than a
stopped one. Codex's option (a) — remove the group — is sound, and `docs/deploy.md`'s stated reason
for not doing it inverts the argument:

> "So deleting it makes the next **web** deploy tear down the existing worker Machine"

That teardown is the goal, not the risk. The ordering that has no unstable intermediate state is:

1. Deploy `yps-worker`, run the falsifier (with finding 6's fix, so it proves the new worker did the
   work). The old worker keeps **running** throughout — that is today's behaviour, costs today's
   money, and strands nothing.
2. In one commit: delete `worker` from `fly.toml`'s `[processes]` and its `processes = ["worker"]`
   `[[vm]]`, and deploy the web app. That deploy destroys the old worker Machine —
   *"destroys all the Machines that belong to any process group that isn't defined"* — so the
   transition ends in a single documented, atomic step, with no window in which anyone must
   remember to keep something stopped.
3. Only then set `WORKER_IDLE_EXIT_MS` on `yps-worker`.

Nothing in the interval requires two workers to be avoided, so the "keep it stopped" instruction —
the part that is unenforceable — can simply be deleted. If step 2 must be deferred, then the
interim guard should be `fly deploy --process-groups web` (a real flag, quoted above) written into
the runbook as the *only* supported web-deploy command, not a post-deploy cleanup step.

---

## Things I checked and found correct

- **The idle-clock reset arithmetic** (`worker/main.ts:146-174`). One drain query per `idleExitMs`,
  not per poll; `idleSince` is cleared on any non-idle result so a busy worker never leaves; it
  cannot exit *later* than one poll past the window, and cannot exit while `r !== 'idle'`. The
  counting assertion at `tests/lib/worker-idle-exit.test.ts:125-143` has a wide, deliberate margin
  (~4 calls with the reset, ~300 without), so it cannot go red on timing jitter.
- **`queueIsDrained` fails safe** (`worker/main.ts:288-295`): a throwing check returns `false`
  (stay alive), which is the asymmetric direction the docstring argues for, and it is tested.
- **`hasUnfinishedWork` counts `queued` + `active` only** (`supabase-job-queue.ts:107-111`),
  `head: true` so no rows cross the wire, and it throws rather than guessing on error. The only
  non-test caller is `worker/main.ts:290`. Counting `active` does not create a new never-exit path
  in practice: an orphaned `active` row is reclaimed by the startup sweep (cursor `-Infinity`) or
  the 60s sweep gate, and a `dead_letter`/`failed` row is not counted.
- **Status literals match the enum.** `0008_jobs_queue.sql:22` allows
  `queued|active|completed|failed|dead_letter|cancelled`; the read-path poke fires only on
  `'queued'` (`app/api/jobs/route.ts:92`) and four cases pin the non-poking statuses. Not poking on
  `active` is right for this route — the orphan case belongs to the worker's drain check, which is
  where it is.
- **`workerWakeFromEnv`'s shared instance** (`worker-wake.ts:97-117`). Keyed on the URL, so a
  changed `WORKER_WAKE_URL` yields a fresh instance and no reset hook is needed; `opts` opts out, so
  tests cannot inherit each other's suppression window; both properties are tested. The shared state
  is timing-only (a timestamp and an in-flight promise), so concurrent requests, double imports and
  multiple web Machines are all safe — the worst case is one extra poke per process. A secret
  rotation restarts the Machine anyway, and a same-URL rotation needs no invalidation.
- **The poke is not awaited anywhere it matters**, and the test that proves it **hangs** rather than
  measuring a duration (`tests/api/jobs-route-wake.test.ts:79-88`) — that is the right shape.
- **The suppression window's interaction with the strand it exists to close.** The read-path poke
  can be suppressed for up to 10s by the enqueue-time poke that preceded it (shared instance, by
  design), so a job stranded in the exit window waits up to ~`DEFAULT_SUPPRESS_MS` rather than one
  poll. Bounded, small, and strictly better than the unbounded wait before r1 F4. Not a finding.
- **The ordering argument** in `enqueuer.ts:55-73`: the row is committed before the poke, and the
  test asserts the order rather than just the call.
- **`fly.toml` declares no `[[services]]`** and the guard distinguishes a real table header from a
  comment naming one (`tests/lib/worker-idle-exit.test.ts:179-190, 296-301`) — that helper is the
  right fix for the failure its own comment records.
- **Round 1's F1/F5 fix is complete**: `on-failure` in `fly.worker.toml:106-108`, the test pins both
  Fly's accepted *set* and the specific value, and the group name in `[processes]` matches every
  `processes = ["worker"]` filter (and a mismatch is caught by `fly config validate`, finding 7).
- **Worktree clean.** Every mutation and probe reverted; `git status --short` at the end shows only
  this review file as untracked.

---

## What I could not run — treat every line here as NOT VERIFIED

- **No live Fly deployment, of either app.** Everything about Fly Proxy, Flycast routing, autostart,
  restart policy and deploy behaviour is judged against Fly's live documentation and flyctl
  v0.4.87's own help output, never against an observed deploy.
- **Whether `fly deploy` restarts an existing STOPPED Machine** in a declared process group. Fly's
  docs do not address it; the only live evidence I found points at "updated in place, left stopped",
  and it is a community post, not documentation. This is the single load-bearing unknown in the
  process-group section, and my recommendation there is written so that it does not depend on the
  answer.
- **Whether `server.listen(port)` (binding `::`) is reachable from Fly Proxy inside a Fly Machine.**
  I reasoned from Node's dual-stack behaviour and Linux's default `bindv6only=0`; I did not observe
  it. Finding 2 is filed on the process failure, which does not depend on this.
- **`EXPLAIN` for the drain COUNT** (finding 11). No Postgres was started for this review, so the
  index claim is refuted only by reading the schema, not by a plan.
- **Integration and E2E suites** (`test:integration`, `test:e2e`) — not run; they need a live
  Supabase stack.
- **`npm test` on Node 22.** The local runtime is v20.18.2, and the unhandled-rejection measurement
  in finding 4 was taken there; CI pins Node 22, where the default is the same (`throw`), but I did
  not re-measure it on 22.
