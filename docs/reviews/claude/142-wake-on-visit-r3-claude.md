# Claude adversarial review — backlog #142 wake-on-visit — round 3

STATUS: complete

Subject: `git diff b048f8a7..HEAD` at HEAD `44625b36` (the fold of Codex round 3), with
`git diff master...HEAD` for context. Worktree
`/Users/kujinlee/.claude-tmp/.../wt142`.

## Verdict: FINDINGS — 1 Medium, 3 Low. **Fold and ship; a round 4 is not warranted.**

Nothing found this round changes runtime behaviour. One comment makes a claim its own code and its
own test both refute; three Lows are a guard bound to a timing accident, a latent unhandled
rejection inside the wake module, and a documentation claim ("ships inert") that is false in one
particular I could name and measure.

## ⚠ MY SUBJECT MOVED UNDER ME, AND THEN MY FINDINGS WERE FOLDED WHILE I WAS WRITING THEM

Two separate things happened, in this order, and both are worth recording because they change what
the next reader is looking at.

**1. At 20:10 PDT, `worker/main.ts` was edited in this worktree by something that is not me** — the
`server.listen` declination rewritten to cite a `node:22-bookworm-slim` / `v22.23.2` measurement,
which is the exact measurement I had taken in a container minutes earlier and had not yet reported.

**2. Between 20:30 and 20:45, three more files were modified — and they are folds of the findings
below, citing my own numbers** (`review r3 Medium 1`, `r3 Low 2`, `r3 Low 4`): the read-path comment
in `app/api/jobs/route.ts`, `void p.finally(…).catch(() => {})` in `lib/job-queue/worker-wake.ts`,
and the `catchSpy` rewrite of the enqueue-side case in `tests/lib/worker-wake.test.ts`.

Everything below is the review of the **committed** tree at `44625b36`, as instructed. None of those
four files is my edit and I have reverted none of them. **My own mutations are all reverted**, and I
re-verified `lib/job-queue/enqueuer.ts` clean immediately before and after the one mutation I ran
against the folded tree.

⚠ **The consequence for whoever reads this next: the findings section describes text that no longer
exists on disk.** Read the findings for the argument and the evidence; read `git diff` for what the
tree now says. The two agree, which I checked — see *The live fold, verified* at the end.

## Is this converged? — my argument, with what would change my mind

**Short answer: the severity trend is real; the count trend is partly an artefact, and I can show
which part.**

The case that it is an artefact. Every one of the five prior review documents concentrates on the
same five files — `worker/main.ts`, `lib/job-queue/worker-wake.ts`, `fly.toml`, `fly.worker.toml`,
`app/api/jobs/route.ts`. Findings fall when the search space stops moving, and this search space
stopped moving after round 1. The test of that is direct: go somewhere no round has been and see
whether anything is there. I did, and something was — Finding 1 comes from
`lib/storage/supabase/supabase-job-queue.ts:28`, a line **no review document on this branch has
ever cited**, and it makes a load-bearing comment in the diff false. So "reviewers checked the same
things" is not a hypothesis here, it is a measured fact about the corpus, and it did conceal a
defect.

The case that it is converged anyway. Having found that, I then deliberately swept the rest of the
unreviewed ground — `lib/storage/job-queue.ts`, the producer loop, the dig route's enqueuer
construction, the `runOnce`/`sweepPolicy` interaction from PR #318, the runbook's secret list
against what `main()` actually requires at startup, and Next's own SIGTERM handling — and the worst
thing left standing is one comment that overclaims and two latent one-liners. The three things this
round was told to attack hardest all **survived measurement**:

- the rewritten `kill_timeout` comment is accurate in every particular I could check, including the
  clause the coordinator flagged as asserted-not-measured (§ Re-derivation, claim 1);
- the new enqueue-side test genuinely kills the mutation it names (§ claim 2);
- the `server.listen` declination is now settled by measurement in the real image base (§ claim 4).

That is the shape of a converged branch: the reviewers' aim was narrow, widening it produced
*documentation* defects rather than behavioural ones, and the previous round's fixes held.

**What would change my mind.** If Finding 1 had been a behavioural defect rather than a false
comment — if the dig strand had been reachable from a shipped UI — I would be asking for round 4
on the grounds that round 3 found a live defect in unreviewed code and therefore the unreviewed
area is not exhausted. It is not reachable: the cloud dig route has no frontend
(`app/api/videos/[id]/dig/[sectionId]/route.ts:56-59` says so), and the whole wake path is a no-op
until two secrets are set. Equally, if the concurrent edit to `worker/main.ts` turns out to change
anything but comments, this verdict does not cover it.

**Against `docs/review-method.md`'s stop condition** (diminishing returns, not a round count):
round 3 produced 0 Blocking / 0 High across both halves, both halves' findings are in prose and
test-strength, and the two halves agree. Fold these four and take the tree gate. I am not
authoring a retreat here — the documented rule is the one I applied, and it says stop.

## Re-derivation of the claims

**1. The rewritten `kill_signal`/`kill_timeout` comments — "verify the new text is accurate in every
particular." It is. Including the clause you flagged as unmeasured.**

The comment (`fly.toml:21-35`, `fly.worker.toml:38-52`) makes four claims. Each checked:

| Claim | Verdict | Evidence |
|---|---|---|
| The abort signal IS the handler's signal | TRUE | `worker-runner.ts:99-101` — `AbortSignal.any([wallClock.signal, leaseLost.signal, opts.shutdownSignal])`, handed to the handler as `ctx.signal` at `:106` |
| SIGTERM → handler aborted, `fail_job(billableSucceeded: true)`, `dead_letter` at `summary_max_attempts = 1` | TRUE | r2 measured it on the real path; I re-derived the SQL: `fail_job` (`0020_reservation_release.sql`) takes `elsif v_attempts >= v_max then v_new := 'dead_letter'` |
| `kill_timeout` buys time to **release the lease row** | TRUE, with a wording caveat below | `fail_job`'s `update jobs set … locked_by = null, lease_token = null, lease_expires_at = null` — the lease IS cleared on the shutdown path |
| …**close the wake listener, exit** | TRUE | `worker/main.ts:359-362` — `listener.close()` in a `finally`; `close()` is idempotent and returns early when `!server.listening` |

The clause you flagged — "releasing the lease row / closing the listener is actually what happens"
— is the one I most expected to fail, because it has a hidden precondition: **the terminal write
only lands inside `kill_timeout` if the handler returns promptly after the abort.** It does. The
signal is plumbed the whole way down, not just checked at the top: `gemini.ts:302`, `:573`, `:815`
forward it into `model.generateContent`, and `:310`, `:596`, `:831` use `abortableSleep(…, signal)`
for the retry backoff, so a SIGTERM during a retry sleep does not sit out the backoff. Add
`summary-handler.ts:170`'s pre-write abort check and the handler unwinds in roughly one network
round trip.

⚠ **The wording caveat, not filed as a finding because the paragraph above it already says the
right thing.** *"Release the lease row"* is true — the lease columns are NULLed — but it is the
lease being cleared as part of a **terminal `fail_job` write to `dead_letter`**, not a release that
frees the job for retry, and read alone it suggests the opposite of the paragraph two lines above.
Two further conditions are unstated and both are benign: with no job in flight there is no lease row
at all, and if the handler ever did outlast 120s the SIGKILL would leave the row `active` for the
sweep. If you touch this comment again, *"finish the terminal write that clears the lease, close the
wake listener, exit"* is the precise version.

⭐ **And the comment understates its own case in a way worth recording, because it sharpens #139.**
Fly's documented defaults are `SIGINT` and **`kill_timeout = 5s`**
(https://fly.io/docs/reference/configuration/, fetched 2026-09-18). r1 F9 measured that on `master`
these two keys parsed into `[http_service]` and were therefore not app settings at all — so
**production has been running on SIGINT/5s**, and 5s is genuinely tight for abort-propagation plus a
`fail_job` round trip. The worker traps `SIGINT` too (`worker/main.ts:349`), so the shutdown path is
the same; what changes is the grace. This branch does not merely document the drain, it is the first
time the 120s has existed. (See Low 3 — that also means it is not inert.)

**2. The new enqueue-side test. The mutation dies; the 50ms settle is load-bearing; a delayed
rejection would NOT be caught.** All three measured, control first.

```
control    npx jest tests/lib/worker-wake.test.ts        →  22 passed
mutant     void this.wake().catch(() => {})  →  void this.wake();
                                                      →  1 failed, 21 passed
           FAIL at tests/lib/worker-wake.test.ts:182 — "flycast unreachable",
           thrown through SupabaseEnqueuer.enqueue (lib/job-queue/enqueuer.ts:78)
```

Killed **via the case it names**, not collaterally. Then the two follow-up questions:

```
mutant + `await new Promise(res => setTimeout(res, 50))` DELETED   →  22 passed   (mutant SURVIVES)
mutant + settle kept, wake rejects after 100ms instead of at once  →  22 passed   (mutant SURVIVES)
```

So: the settle is **load-bearing** (the comment claiming so is correct), and the case is bound to a
rejection that lands **within 50ms**. Filed as Low 2, with a timing-free replacement I verified
green-on-control and red-on-mutant rather than proposed.

I also re-derived Codex's claim about the *other* call site, since it was its evidence for closing
r2 Medium 4 on the read path:

```
mutant     void workerWakeFromEnv()().catch(() => {})  →  void workerWakeFromEnv()();
           npx jest tests/api/jobs-route-wake.test.ts  →  1 failed, 5 passed
           FAIL at app/api/jobs/route.ts:94, through GET
```

Confirmed — the read-path `.catch()` is genuinely bound.

**3. Counts, types, configs, gates.**

```
npx tsc --noEmit                    rc=0
npm test -- --runInBand             278 suites / 2883 tests passed, rc=0
fly config validate -c fly.toml           ✓ Configuration is valid
fly config validate -c fly.worker.toml    ✓ Configuration is valid
check-docs.py            rc=0
check-review-rounds.py   rc=0
check-anchors.py         rc=0
check-dashboard-entry.py rc=0
check-test-counts.py     rc=0   "roadmap test counts match the suite: 2,883 unit / 278 suites"
```

2883/278 confirmed twice (once by `--runInBand`, once by the `--ci --json` run). The roadmap's
`2882 → 2883` edit at `docs/roadmap-to-launch.md:2040` is correct.

⚠ **`check-test-counts.py` exited 1 on my first pass, and it was MY fault, not the branch's.**
It reported *"the jest results are STALE: 1 test file(s) changed AFTER the run that produced them —
treat this check as NOT RUN"*, naming `tests/lib/worker-wake.test.ts`. That is the gate correctly
detecting that my mutation work had `cp`-restored the file and bumped its mtime past
`jest-results.json`. I regenerated the results honestly
(`npm test -- --ci --json --outputFile=jest-results.json`, gitignored, untracked) rather than
touching mtimes, and it exits 0. **The coordinator's claim that all five gates pass is correct.**
Recording it because a reviewer who saw that rc=1 and reported it would have filed a defect that
the reviewer created.

**4. THE NODE 22 QUESTION — SETTLED. `listen(port)` with no host binds `::` on Node 22, in the real
image base, and on Linux it is genuinely dual-stack.**

Measured in the image the Dockerfile actually uses (`FROM node:22-bookworm-slim`), not locally:

```
$ docker run --rm -v /tmp/listen-probe.js:/probe.js node:22-bookworm-slim node /probe.js
node v22.23.2 address: {"address":"::","family":"IPv6","port":8081}
127.0.0.1: CONNECTED
::1: CONNECTED

$ docker run --rm node:22-bookworm-slim cat /proc/sys/net/ipv6/bindv6only
0
```

The declination at `worker/main.ts:247-253` is correct and the finding is closed for good:
Flycast is IPv6, `::` receives it, and `'0.0.0.0'` would bind IPv4 only — the change that would
actually break the path. Codex's caveat ("I did not measure Node 22 inside the image") is answered.

⚠ **One thing the old comment's evidence did not support, worth knowing even though the conclusion
holds.** The word *dual-stack* was attributed to a `node -e` that reported
`{ address: '::', family: 'IPv6' }` — and that output does **not** establish dual-stack. On macOS,
where that measurement was taken, `net.inet6.ip6.v6only` defaults to **1**, so a `::` bind there is
IPv6-only; the same output means different things on the two platforms. The claim was true of the
platform that matters and the evidence was from the platform where it is weakest. The container run
above is what actually establishes it. *(The uncommitted edit described at the top of this document
appears to be exactly this correction already being folded.)*

## Findings

### [Medium] 1 — The read-path poke's comment claims a generality the code does not have, and its own test says the opposite. A queued **dig** job can never trigger it

**Evidence:** `app/api/jobs/route.ts:84-85` states:

> *"Poking here fixes that generally rather than narrowly: it also covers a crashed worker, and any
> future code path that creates work without going through `enqueue()`."*

Both halves of that sentence are measurably false.

*(a) The kind filter.* The poke is gated on the rows this route returns, and those rows come from
`bundle.jobQueue!.listByPlaylist(playlistId)` — which is
`lib/storage/supabase/supabase-job-queue.ts:24-29`:

```ts
.eq('playlist_id', playlistId).eq('job_kind', 'summary')
```

`job_kind = 'summary'`, hard-filtered. A `dig` job is enqueued through the **same** `SupabaseEnqueuer`
and therefore the same wake (`app/api/videos/[id]/dig/[sectionId]/route.ts:60`), so it inherits the
same exit-window race r1 F4 / Codex r1 Blocking 2 filed — and the recoverer built for that race
cannot see it. There is no second poker: `grep` for `workerWakeFromEnv` finds exactly two call
sites, the enqueuer and this route. `listByPlaylist` is cited in **no** review document on this
branch except in passing as an example of an unrelated convention (r1, line 555); the `job_kind`
filter has never been read by any round.

*(b) The status predicate.* `route.ts:94` is `jobs.some((j) => j.status === 'queued')`. A worker that
crashed mid-job leaves its row `active`, not `queued`, and nothing sweeps it back to `queued` while
the machine is stopped — the sweep runs inside the worker. So "it also covers a crashed worker"
names the one state the predicate excludes. **The route's own test file says so, in the opposite
direction:** `tests/api/jobs-route-wake.test.ts:58-60` —

> *"`active` … A job abandoned by a DEAD worker is a different question, and it is **not this
> route's to answer** — the worker's own drain check counts `active` rows for exactly that reason."*

The test comment is right and the route comment is wrong, and they sit ten lines apart in the diff.

**Introduced by an earlier round's fix?** Yes — the whole read-path poke, including this sentence,
is r1 F4's fix.

**Why it matters:** not because a dig job is likely to strand today — it is not; the cloud dig route
has no frontend (`dig/[sectionId]/route.ts:56-59`: *"this is a generation-only slice with no dig
frontend yet"*), and the feature is inert until two secrets are set. It matters because this is a
comment that **retires a question**. A future reader asking "is the exit-window race covered?" gets
"yes, generally" from the only place that would tell them, and the class of defect this branch has
spent three rounds on is exactly a config or comment sentence that is plausible and false — r2 High
1 and r3 Codex Medium 1 were both that, in the same slice.

**Fix:** correct the sentence to what the code does — *the read path recovers a **queued summary**
job, which is the F4 window; it deliberately does not poke for `active` (see the test), and it
cannot see `dig` jobs because `listByPlaylist` filters `job_kind = 'summary'`.* Then decide
separately, and record the decision, whether the dig path needs its own recoverer. If it does, the
cheapest shape is a poke in the dig enqueue route's GET-equivalent rather than widening
`listByPlaylist`, whose filter is load-bearing for the playlist UI.

### [Low] 2 — The new enqueue-side guard is bound to a *synchronously* rejecting wake; a rejection that lands after the settle survives the mutation

**Evidence:** measured, as § claim 2 above. With `.catch()` removed from
`lib/job-queue/enqueuer.ts:78` and the test's wake changed from `Promise.reject(…)` to a promise
that rejects after 100ms, `tests/lib/worker-wake.test.ts` stays **22 passed** — the mutant survives.
The real hazard shape is not synchronous: a rejection out of `worker-wake.ts` would follow a
`fetch`, i.e. up to the 1500ms `DEFAULT_TIMEOUT_MS`.

**Introduced by an earlier round's fix?** Yes — this is r3 Codex Low 2's fix.

**Why it matters:** r2 Medium 4's whole finding was that the guard for this invariant *"passed only
because it returned before the microtask queue drained"*. The replacement is a strictly better
version of the same dependency — it now depends on the rejection landing inside a 50ms window
instead of inside a microtask. It is still a timing accident, and it is the second one in this file.

**Fix — verified, not proposed.** Assert the property (*the call site attached a handler*) rather
than the symptom (*no unhandled rejection surfaced in time*):

```ts
const rejected = Promise.reject(new Error('flycast unreachable'));
const catchSpy = jest.spyOn(rejected, 'catch');
const wake = jest.fn(() => rejected);
…
expect(catchSpy).toHaveBeenCalledTimes(1);   // the CALL SITE attached the handler — timing-free
rejected.catch(() => {});                    // soak it so the assertion above cannot be the soak
```

Measured on this tree: **green on the unmutated enqueuer (22 passed), red on the mutant** (fails at
the `catchSpy` assertion), and it is independent of when — or whether — the rejection lands.

### [Low] 3 — "The whole feature ships INERT" is false in one particular: the `kill_signal`/`kill_timeout` relocation arms on the next **web** deploy, with no command and no secret

**Evidence:** `docs/deploy.md:172` — *"**Everything here ships INERT** — the code is deployed but
does nothing until the steps below are done"* — and the dashboard entry, which is what the human
reads before deciding: *"Nothing about this is switched on yet — turning it on is six commands on
Fly."*

r1 F9's own `tomllib` measurement established that on `master` these keys parse into
`[http_service]` and are **not app settings**. So today the app runs on Fly's documented defaults,
`SIGINT` / `kill_timeout = 5s` (https://fly.io/docs/reference/configuration/, fetched 2026-09-18).
On this branch they are at top level (`fly.toml:36-37`), which is app-level and therefore applies to
**every process group in `youtube-playlist-summaries`** — the `web` group and the old `worker` group
that `fly.toml:56-58` still declares. The next `fly deploy` of the web app changes both machines
from SIGINT/5s to SIGTERM/120s. None of the six commands is involved.

**Introduced by an earlier round's fix?** Yes — r1 F9's fix.

**Why it matters, and why it is only a Low:** I checked both consumers and the change is **benign**.
Next's standalone server installs a SIGTERM handler
(`node_modules/next/dist/server/lib/start-server.js:386-390`, `process.on('SIGTERM', cleanup)`,
exiting 143 at `:375-377`), so web deploys are not slowed by the longer timeout; the worker traps
SIGTERM at `worker/main.ts:348`. It is a Low because the claim the human is deciding against is
"nothing is switched on", this branch is the second time something on it arms itself on deploy
(r1 F2's `[[services]]` block was the first), and the dashboard entry already half-discloses it —
it says the 120s *"is corrected now"* without saying that the correction takes effect on the next
web deploy rather than on step 4 of the runbook.

**Fix:** one sentence in the dashboard entry and one in `deploy.md` § Step 5 — *the wake path is
inert until steps 1–6; the `kill_signal`/`kill_timeout` correction is not, and takes effect on the
next `fly deploy` of the web app, moving both process groups from Fly's SIGINT/5s default to
SIGTERM/120s.*

### [Low] 4 — `void p.finally(…)` inside `worker-wake.ts` reproduces the exact hazard the call sites just stopped depending on, one module in

**Evidence:** `lib/job-queue/worker-wake.ts:88`:

```ts
const p = send();
inFlight = p;
void p.finally(() => { if (inFlight === p) inFlight = null; });
return p;
```

The `.catch()` r2 Medium 4 added protects the promise the **caller** holds. It does not protect
this one: `.finally()` returns a *new* promise that adopts the rejection, and it is `void`ed.
Measured in isolation, with the caller's handler present exactly as in `enqueuer.ts:78`:

```
$ node /tmp/void-finally.js
UNHANDLED REJECTION: send() rejected
exit=3
```

**Introduced by an earlier round's fix?** No — this line predates the round-2 work; r2 Medium 4's
fix is what makes it visible as an inconsistency.

**Why it matters:** latent, not live — `send()` cannot reject today, because its body is
`try { await doFetch(…) } catch { } finally { clearTimeout(timer) }`. But that is precisely the
invariant r2 Medium 4 decided the codebase should stop leaning on, and the decision was applied to
the two call sites and not to the module itself. Under Node's default
`--unhandled-rejections=throw` the cost of being wrong is the worker process dying.

**Fix:** `void p.finally(() => { … }).catch(() => {});` — or drop the `void` chain and clear
`inFlight` inside `send`'s own `finally`. Either makes the module independent of its own invariant,
which is the property the fix was supposed to establish.

## Codex round 3's two findings — closed or not

**Medium 1 (the disproven "finishes the in-flight job" sentence survives in both Fly configs) —
CLOSED, and correctly.** Both copies are replaced (`fly.toml:21-35`, `fly.worker.toml:38-52`), the
replacement is accurate in all four of its claims (§ Re-derivation 1), and it names backlog #139 as
Codex asked. `grep -rn "finishes the in-flight job"` over the tree now returns only the quoted-as-false
occurrences inside the new comments, `worker/main.ts:280`'s "the better behaviour … needs a second
controller", and backlog #139's own row (see the answer on that below).

**Low 2 (the enqueue-side `.catch()` is present but not mutation-guarded) — CLOSED, with a
residual.** The mutation Codex ran now dies via the named case (§ Re-derivation 2). The residual is
that the new guard is bound to a synchronous rejection — Low 2 above. Codex's own proposed fix said
*"wait one macrotask/settle window so the unhandled rejection lands if `.catch()` is removed"*, and
that is exactly what shipped; the filed fix was a hypothesis and it survived contact, but only for
the rejection shape it described.

## Backlog #139's stale citation — is flagging sufficient? My answer, and the population is THREE, not one

**Flagging is sufficient. Editing the row is not yours to do. But the thing to flag is not the one
you named — there are three stale citations, two of them in living documents, and your question
named one.**

First, the citation is stale in the worst available way: **the quote still greps.** On `master`,
`fly.toml:45-46` is exactly

```
# Graceful drain: worker traps SIGTERM (worker/main.ts) → stops claiming, finishes the in-flight
# job, exits. …
```

so the row was accurate when filed. On this branch `kill_signal`/`kill_timeout` are at `:36-37`, and
the sentence survives only at `:26`, **inside the comment that refutes it**. A reader checking the
row greps `finishes the in-flight job`, finds it in `fly.toml`, and concludes the citation is good —
when the file now asserts the opposite. The row's companion pointer, *"`:49` buys 120s of grace"*,
now lands on `NEXT_PUBLIC_SUPABASE_ANON_KEY` in `[build.args]`.

Second, the population:

| Where | Living? | Verdict |
|---|---|---|
| `docs/backlog.md:167` (#139's row) | yes | stale — the one you named |
| `docs/roadmap-to-launch.md:462` | **yes** | **stale, and not named.** Same quote, same `fly.toml:45-46`, same `:49`, in *Dev-infrastructure debt (NOT tied to any feature slice — survives every merge)* |
| `docs/dashboard-entries.md:10229` | no — append-only by design | **correctly immune.** A dated historical entry describing what was true then; editing it would be the defect |

That the coordinator's question named one of two live instances is the instance-not-class shape this
branch has now hit three times (r2 High 1 → r3 Codex Medium 1 was the same thing across two config
files).

Third, on "does leaving it constitute shipping a known-false document". No — and the distinction
matters. **#139's *finding* is still true**: the code still aborts the handler, still keeps the
spend, still dead-letters at `max_attempts = 1`. What this branch invalidated is the row's
*premise citation* — "the config promises X" — because the branch fixed the config's prose. The
finding outliving its evidence is not a false document; it is a document whose falsifier now points
at the wrong line. Nothing mechanical will catch it: `check-backlog-closure.py` compares closing
subjects to `✅` markers and is warn-only, and no gate reads a row's citations.

**So: flag, do not edit — with one condition.** A flag that lives only in a review document is a
flag with no reader; the human reads the dashboard entry. The branch's second entry already
discloses one #139 staleness (*"recorded as having three causes. This makes a fourth … the count has
changed and the note describing it has not"*) and not this one. One sentence in the same entry
closes it: *#142 also invalidates #139's and the roadmap's citation into `fly.toml` — the quoted
sentence is still in the file, as the thing the new comment refutes.* Then the edit to both rows is
the human's, made knowingly, which is what `agree before filing` is for.

## What no round has reviewed, and what I found when I looked

Named in advance, then opened. Findings in **bold**.

| Subject | Result |
|---|---|
| `lib/storage/supabase/supabase-job-queue.ts` | **Finding 1** — `listByPlaylist`'s `job_kind = 'summary'` filter, never cited by any round, makes the read-path comment false for dig |
| `lib/storage/job-queue.ts` (`hasUnfinishedWork` contract) | Correct. `queued` + `active`, terminal statuses excluded, throws rather than guessing empty (`supabase-job-queue.ts:107-113`), `head: true` so no rows cross the wire. The docstring's *"once per idle window"* claim is true given `main.ts:171`'s idle-clock reset |
| The dig route's enqueuer construction | Correct — `new SupabaseEnqueuer(createServiceClient())` at `:60`, default wake, so dig enqueues DO poke. It is the *read* side that has no poker (Finding 1) |
| `lib/job-queue/producer.ts` enqueue loop | Correct. Sequential `await enqueuer.enqueue(...)` over up to 50 videos at `:104-110`; the wake is not awaited, so r1 F3's ~75s is genuinely gone rather than shrunk. Coalescing makes pokes 2..50 free (`worker-wake.ts:82-90`) |
| `runOnce` / `sweepPolicy` interaction with idle-exit (PR #318) | Correct, and the two compose properly. `makeSweepGate`'s cursor starts at `-Infinity` (`main.ts:102`) so a freshly woken machine sweeps immediately rather than inheriting the previous machine's stranded leases; `runOnce:91` refuses to claim after a shutdown arrives during the sweep. A worker woken to deal with an `active` row it cannot yet claim stays alive on `hasUnfinishedWork`, waits out the 120s lease, sweeps, and runs it |
| `lib/job-queue/worker-wake.ts` internals | **Low 4** — `void p.finally(…)`. Coalescing itself is correct: `inFlight` join, `lastSentAt` window, per-URL shared instance so suppression is not reset per request |
| The runbook's secret list vs what `main()` actually requires at startup | **Correct and complete.** `main()` fail-fasts on `GEMINI_API_KEY`, `YOUTUBE_API_KEY`, `SUPABASE_SERVICE_ROLE_KEY` (`:329`) plus `NEXT_PUBLIC_SUPABASE_URL` / `NEXT_PUBLIC_SUPABASE_ANON_KEY` via `validateStorageEnv()` → `getSupabaseEnv()`. `deploy.md` step 3 sets exactly those five on the new app. A missing one would have crash-looped `yps-worker` under `on-failure` forever |
| Next's own SIGTERM handling, i.e. does the relocated `kill_timeout` slow web deploys | **Low 3** — it arms on deploy, but benignly; `start-server.js:386-390` handles SIGTERM and exits 143 |
| `tests/lib/worker-idle-exit.test.ts` config pins | Correct, and stronger than r2 left them. Position **and** value for both files (`:267-289`), `internal_port === WAKE_PORT` (`:199-207`), `[[services.ports]]` presence (`:210-223`), no `auto_stop_machines` in the worker service, `fly.toml` declares no `[[services]]` at all |

## Things I checked and found correct

- **`onFatal` is required and unconditional.** `startWakeListener(onFatal: () => void, …)` at
  `main.ts:243`, called at `:286` with no `?.`, and the single call site passes `() => ac.abort()`
  at `:353`. Reverting the call site no longer compiles, which is the point of the parameter order.
- **The idempotent `close()`** guards on `server.listening` (`:301`) before `server.close()`, so a
  second close from `main()`'s `finally` cannot turn a recovery into an `ERR_SERVER_NOT_RUNNING`
  rejection that loses the original error.
- **`fail_job` clears the lease on the shutdown path** — `locked_by = null, lease_token = null,
  lease_expires_at = null` in `0020_reservation_release.sql`, inside the `status = 'active'` fence.
- **The abort is prompt**, so the terminal write lands well inside `kill_timeout` — the signal
  reaches `model.generateContent` and the retry backoff, not just a top-of-handler check.
- **`idleExitMsFromEnv` fails safe** — blank, non-finite or `<= 0` logs and returns `undefined`,
  i.e. never exit, rather than 0 (exit on the first idle poll).
- **`queueIsDrained` fails safe** — an unanswerable question resolves to "not drained" (`:318-325`).
- **The runbook's falsifier proves *which* worker did the work** (`fly logs -a yps-worker` showing
  the claim), which is what r2 Medium 6 was about.
- **The `fly config validate` green is correctly described as insufficient** for the
  `[[services.ports]]` case, with the unit test named as the real guard.

## The live fold, verified — three of the four findings are already on disk, and they hold

Because the fold landed inside my own round, I checked it rather than leaving it to round 4. All of
this is against the **working tree**, not `44625b36`.

| Folded | Verdict |
|---|---|
| Medium 1 — read-path comment | **Correct, and it goes further than the finding asked.** It enumerates ✅ queued summary / ⛔ crashed-worker (`active`) / ⛔ dig, names `listByPlaylist`'s `job_kind` filter as the reason, records that the dig gap is a real gap rather than a division of labour, and carries the *"do NOT widen `listByPlaylist`"* warning forward. Nothing in it overclaims |
| Low 2 — enqueue-side guard | **Correct and stronger.** `jest.spyOn(rejected, 'catch')` + `expect(catchSpy).toHaveBeenCalledTimes(1)`, with the soak moved after the assertion so it cannot be doing the soaking. Re-measured on the folded tree: mutate `void this.wake().catch(() => {})` → `void this.wake();` and it goes red **at the `catchSpy` line** (`1 failed, 21 passed`); restored, clean |
| Low 4 — `void p.finally(…)` | **Correct.** `.catch(() => {})` on the finally chain, with the measured `UNHANDLED REJECTION … exit=3` recorded in the comment |
| Low 3 — "ships inert" | **Correct.** `deploy.md:171` now reads *"The wake path ships INERT"*, with a ⚠ block naming the `kill_signal`/`kill_timeout` relocation, Fly's SIGINT/5s default, the two affected process groups, and both consumers as checked-and-benign. The dashboard entry carries the plain-language version |
| #139 / roadmap stale citations | **Not folded**, correctly — editing either row is the human's step. ⚠ But the dashboard sentence I asked for is also **not** there: the new entry still flags only the *count* staleness (*"the fourth cause"*) and says nothing about the citation into `fly.toml` being stale in `backlog.md:167` **and** `roadmap-to-launch.md:462`. That is the one thing this round asked for that has no home yet |

```
npx tsc --noEmit                                                      rc=0
npx jest tests/lib/worker-wake.test.ts tests/api/jobs-route-wake.test.ts   28 passed, 2 suites
```

⚠ **`check-test-counts.py` now exits 1 again, and this time it is the fold's, not mine.** Same
CANNOT-RUN reason: `tests/lib/worker-wake.test.ts` changed after the run that produced
`jest-results.json`. I deliberately did **not** regenerate it a second time — the tree is mid-fold
and the count belongs to whoever finishes the fold. It is a *regenerate-before-commit* item, not a
defect. The count itself should not move: the case was rewritten, not added.

## What I could not run — treat every line here as NOT VERIFIED

- **No live Fly deploy, and no observation of real Flycast traffic.** Everything about
  autostart, autostop, Machine lifecycle, and what a `fly deploy` does to an existing stopped
  Machine is read from documentation, not measured. The runbook's own "NOT VERIFIED in either
  direction" note on that last point still stands.
- **Nothing was run against prod or against a live Supabase stack.** No integration or E2E suite;
  `test:integration` and `test:e2e` need a stack this worktree does not have. The `fail_job` and
  `sweep_expired_leases` behaviour above is read from the migration SQL, not executed.
- **`yps-worker` does not exist**, so the "must never have a public IP" property — the entire
  security argument for r1 F2's fix — is unasserted by anything, here or in the repo. r2 Medium 5
  said this; it is still true and it is still the human's to check with `fly ips list`.
- **I did not re-measure the #139 abort path myself** (`handlerSawAbort=true,
  handlerFinished=false`). I re-derived the code path and the SQL that make it true; the
  measurement is r2's.
- **The concurrent uncommitted edit to `worker/main.ts` is not reviewed.** I read the diff and it
  appears to be comments only, but it landed after my subject was fixed and I have not verified it
  against the suite.
