# Adversarial review — ROUND 10 (Claude) — stable blob addressing

Target: `docs/superpowers/specs/2026-08-03-stable-blob-addressing/` at `dc92859` (PR #58).
Everything below was run against the live container
`supabase_db_youtube-playlist-summaries-cloud`, inside `begin; … rollback;`.
Mutations were applied to an isolated copy; `git status --porcelain` was clean before and after.

**Verdict: NOT CONVERGED — 1 Blocking, 3 High, 3 Medium, 3 Low.**

---

## The coordinator's numbers — verified, not inherited

| Claim | Result |
|---|---|
| 119 assertions pass | ✅ `grep -c '^NOTICE:  ok'` = **119**, `ALL_STATEMENTS_OK` |
| 58/58 mutations behave | ✅ **58/58**, baseline restored GREEN |
| 38 guards, 31 SHAPE, 7 reconciling | ✅ verbatim |
| `mutate-schema.py` mutates a temp copy | ✅ **PROVEN** — two suites run concurrently, `58/58` each, **verdict-by-verdict identical** (58/58 lines diff-clean), repo untouched. Round 8's corruption is genuinely fixed. |

Round 9's fence is also genuinely fail-closed against a caller with **no** credential. Measured, three
ways — `p_token=NULL` + no pair; a random valid token; a stranger's own `(worker, job)` pair — all
three refused. Round 8's B2 as *round 8 wrote it* is closed. What follows is the same defect reached
by the route round 9 opened.

---

# JOB 1 — attacking round 9

## BLOCKING

### B1 — the "durable credential" is two plaintext columns the attacker can `select`; round 8's B2 reproduced verbatim, plus a new silent-success path

**Defect.** `record_artifact`'s fence accepts `(g.reserved_by_worker = p_worker_id and
g.reserved_by_job = p_job_id)` (`04_artifacts.sql:527-528`), and both values are stored in
`video_generations` (`03_generations.sql:326-327`), which is `grant select, insert, update, delete
… to service_role` (`03_generations.sql:489`). `p_worker_id`/`p_job_id` are ordinary function
parameters bound to nothing about the caller. So the proof of ownership is a shared secret readable
by every party that can call the function.

**MEASURED** (`pD.sql`), no privilege escalation, no forged token:

```
VICTIM reserved dig:4 for gVICTIM -> reserved  (still inside its Gemini call)
ATTACKER reads the credential straight out of the table: worker=worker-VICTIM, job=79c29bbe-…
ATTACKER completes the VICTIM generation -> recorded_after_token_loss
   generation state=complete   md_hash=SHA_ATTACKER   (victim paid, attacker owns the bytes)
VICTIM records its real work -> recorded_after_token_loss   md_hash now=SHA_ATTACKER
```

Round 8's B2 recorded exactly this outcome (`md_hash=SHA_ATTACKER`) and graded it Blocking. The
schema's own claim at `04_artifacts.sql:507` — *"A stranger presents a different pair and is
rejected"* — is measurably false. Round 8's critique of round 7's deleted disjunct ("satisfied by
anyone who can NAME the slot and the generation") applies unchanged: the replacement is satisfied by
anyone who can `select` two columns of the row being fenced.

**And the last line is a second, new defect.** The victim returns with its real token *and* its real
content and is told **`recorded_after_token_loss`** — a success outcome — while `md_hash` stays
`SHA_ATTACKER`. Cause: the fence UPDATE requires `g.state = 'pending'` (`04:526`), the generation is
already `complete`, so `coalesce(p_md_hash, g.md_hash)` never runs; the function then falls through
to the append path, whose `do update` (`04:611-618`) does not touch `md_hash`. The generation now
records a hash describing bytes nobody agreed on — shape #4 — and the writer that paid for the real
bytes was told it succeeded. Shape #5, on the success path, on the money path.

**Threat model, stated plainly.** `record_artifact` is `service_role`-only, so this is not
anon-reachable; the realistic caller is another component of our own system (sync, a second worker,
a repair script). I did not verify that a live component performs this read today. Grading it
Blocking because it is the identical measured bypass round 8 graded Blocking, because the fence's
stated purpose is measurably false, and because the silent-success half is new in round 9 and needs
no attacker at all.

**Change.** Two separable pieces:
1. Make the fence non-replayable. Either keep a secret the caller must already hold (the token) and
   accept that a restarted worker needs an explicit, audited re-adoption RPC, or derive the caller's
   identity from something it cannot type — e.g. require the caller to present the **job lease
   token** and have `record_artifact` verify it against `jobs` itself rather than against a copy.
2. Independently of (1): when the fence UPDATE matches zero rows and the generation is already
   `complete` **with different content**, the current code returns a success string. Check
   `found`, and return a distinct typed outcome (`completed_by_another`) so a caller cannot be told
   its paid bytes were recorded when they were discarded.

---

## HIGH

### H1 — `worker_id` is NOT stable config: it is regenerated on every process start, so the honest restarted worker can never satisfy the fence

**Defect.** Round 9's whole justification (`03_generations.sql:319-322`) is:

> *"Of the three things that identify a worker mid-job, only two survive a restart: `worker_id` is
> stable config, `job_id` is recoverable by querying jobs for `locked_by = me and status = 'active'`
> — and `lease_token` is a random uuid handed out once and held only in memory."*

**Both halves are false against this repo.**

`worker/main.ts:69`:

```ts
const workerId = `${os.hostname()}-${process.pid}-${randomUUID().slice(0, 8)}`;
```

`worker_id` embeds `process.pid` **and a fresh `randomUUID()` minted at process start**. It is
exactly as volatile as the lease token round 9 replaced it for. A restarted worker presents a
different `worker_id` and fails the fence, always — not in an edge case, in every case.

The `job_id` half fails on the same event. `sweep_expired_leases()`
(`supabase/migrations/0009_…:63-77`) sets `locked_by = null, lease_token = null` and
`status = 'queued' | 'dead_letter' | 'cancelled'` for any `active` job whose lease expired. The
recovery query round 9 names (`locked_by = me and status = 'active'`) therefore returns **zero rows
precisely when recovery is needed**. This is not speculation about the queue: the repo already
established it as a reviewed Blocking finding — `lib/cloud-sync/in-flight-job.ts:26-31` says the
swept row *"now looks finished — but the worker process that claimed it may still be inside its
Gemini call … and may write when it returns."* Timings make it ordinary rather than rare: job lease
120 s (`lib/job-queue/worker-runner.ts:25`), wall-clock abort 600 s, so a job may legitimately run
5× its lease and depends on an in-process heartbeat to survive.

**MEASURED** (`pC.sql`) — the state a restarted worker is actually in:

```
4 HONEST W1 restarted, job reclaimed (job=NULL)  -> REFUSED [P0001] video_artifacts: cannot mark
                                                    dig:9 as recorded — generation gW1 is pending
5 HONEST W1 restarted, full durable pair         -> OK: recorded_after_token_loss
```

Case 4 is round 8's H1 verbatim — *"its paid Gemini output destroyed … `[P0001] generation gW1 is
pending`"* — and it is now the only outcome available to a restarted worker, because case 5's
credential cannot be reconstructed. Note the failure is a **raw `P0001` from a trigger**, not a typed
outcome, so the caller cannot even distinguish it from a genuine caller bug. Shape #8, and shape #13
in the fix written for shape #13.

Together with B1 this is round 8's exact verdict about round 7, unchanged: *"A fence that is
simultaneously too permissive and too strict is not mis-tuned; it is asking for the WRONG
CREDENTIAL."* Round 9 swapped one in-memory random uuid for another and wrote down that it had done
the opposite.

**This also silently revokes the standing user decision for the fourth time** (JOB 3's first
question). "The reservation guards SPENDING, not RECORDING" now holds only for a worker whose process
never restarts. Nothing catches it: no assertion exercises a restarted worker, because the assertion
suite supplies `p_worker_id` as a literal that is trivially stable inside one transaction — the test
fixture cannot express the property the production value lacks.

**Change.** Either make `worker_id` genuinely stable config (an env var per machine, with `pid`/uuid
moved to a separate `instance_id` column used for logging only) **and** persist `job_id` where a
restart can read it, or abandon "a credential the worker re-presents" and give a restarted worker an
explicit re-adoption path that is auditable. Whichever is chosen, add an assertion that fences on a
credential *different from the one used at reserve time* — the current suite cannot fail this.

### H2 — round 9's INSERT-half corrections fix created the identical clobber one statement over, on the UPDATE half

**Defect.** Round 9 guarded `videos_corrections_sync_ins_trg` with
`when (coalesce(new.data->>'corrections','') <> '')` (`03_generations.sql:253-257`) so a video added
to a second playlist cannot wipe the shared body. `videos_corrections_sync_upd_trg`
(`03:258-262`) was not swept. The consequence is *created by the fix*: after round 9, the second
playlist's row is left permanently disagreeing with the shared body, and nothing reconciles that
disagreement on any later write.

**MEASURED** (`pA.sql`), one owner, two playlists, one video, no concurrency:

```
step1 (P1 has corrections)        shared = KEEP ME
step2 (P2 added, no corrections)  shared = KEEP ME   <- round 9 fix holds
step3 (P2 sets its own)           shared = P2 TEXT
step4 (P2 CLEARS its own)         shared = <null>
P1 videos.data still says          : KEEP ME
workspace_videos.corrections_hash  : NO-CORRECTIONS constant
```

`03:218` states the invariant this trigger exists to hold: *"`workspace_videos.corrections_hash` is a
DENORMALIZED COPY; the truth lives in `videos.data`"*, and `03:217` promises *"DRIFT IS PREVENTED, NOT
REPAIRED."* At step 4 the truth says `KEEP ME` and the copy says "no corrections". The trigger
produced the drift.

Before round 9 this state was unreachable: step 2 set `shared = <null>`, so P2's row and the shared
body agreed, and step 4 was a no-op. Shape #9 — a fix that moved a defect — and shape #10, in the
round that recorded the eighth instance of shape #10.

**Consequence** (REASONED from the measured state, by the mechanism round 6 B4 measured):
`corrections_hash` is rung 1 of *both* ranking views (`04:728`, `04:764`). With the shared hash now
the no-corrections constant, every generation produced **with** the user's corrections scores rung
1 = false and every generation produced **without** them scores true — the summary that ignores the
corrections outranks the one that applied them. And `reconcile-class-a.ts` compares this hash across
replicas, so cloud and local disagree permanently, which is verbatim the "copyToCloud on EVERY sync,
forever" money path round 6 B4 was written to remove.

**Change.** The UPDATE half needs the general form of the INSERT half's rule, not its special case:
sync to the shared body only when this row is the one the shared body currently reflects (e.g. `when
coalesce(old.data->>'corrections','') is distinct from coalesce(new.data->>'corrections','')` **and**
the shared value is not distinct from `old`'s). A clear from a row that never owned the shared value
must not clear it. Add the mirror of the round-9 assertion (`05_assert.sql:1696-1709`) for the clear.

### H3 — the coverage ratchet's "enumerated whole" omits four guards this spec creates, including the only one labelled cross-tenant

**Defect.** `scripts/check-guard-coverage.py`'s `CATALOG_SQL` (`:158-174`) scopes CHECKs to
`TABLES = ('video_artifacts','video_generations')`, FKs to a hard-coded four-table list that **does
not include `jobs`**, and unique indexes to `TABLES` filtered by `like '%_uq'`. Its own docstring
(`:17-19`) says the whole must come from the catalog "not a list someone maintains" — three of the
four clauses are exactly such a list.

**MEASURED** — spec-created guards that exist in the catalog and are outside the query:

| Guard | Created at | Why invisible |
|---|---|---|
| `jobs_workspace_owner_fk` | `01_workspaces.sql:50-51` — *"§14 Q6's replacement cross-tenant guard, preserving ADR-0002's injection guard"* | `jobs` not in the FK table list |
| `workspaces_owner_id_key` | `01:15` — the reconciler target for `ensure_workspace_for_profile`'s `on conflict (owner_id)` | `workspaces` not in `TABLES`; name not `%_uq` |
| `workspaces_id_owner_id_key` | `01:16` — *"FK target for the Q6 cross-tenant guard"* | same |
| `video_generations_…_kind_key` | `03:346` — FK target for `video_artifacts` | `contype='u'` is in neither the check clause (`'c'` only) nor the `%_uq` index clause |

**Proof it is not cosmetic.** I deleted `jobs_workspace_owner_fk` from `01_workspaces.sql` in an
isolated copy and ran every gate:

```
guards in schema: 38   SHAPE: 31   reconciling: 7        <- unchanged
✅ every guard classified; every SEQUENCE guard reconciles and is mutation-covered
ALL_STATEMENTS_OK / ✅ schema verified (rolled back)      <- 119/119 still green
grep jobs_workspace_owner_fk 05_assert.sql   -> 0
grep jobs_workspace_owner_fk mutate-schema.py -> 0
```

The spec's own cross-tenant guard can be deleted with **all four gates green and the guard count
unchanged at 38** — so the count is not even a canary. Shape #6 (a guard with no test) and shape #11
(an instrument that misreports its own result), instance seven, in the instrument whose thesis is
that absences are only visible against an enumerated whole.

The general answer to JOB 2's question — *what guard could exist that this query cannot see?* — is:
any CHECK outside two tables, any FK on `jobs` or `playlists` or `workspaces`, any unique constraint
declared inline (`contype='u'`), any unique index not named `*_uq`, and **every RLS policy and grant**
(see M1).

**Change.** Derive the table list from the schema files rather than typing it: collect every
`create table` / `alter table` target in `0*.sql` and enumerate against that set. Drop the `%_uq`
name filter and add `contype in ('c','f','u','x')`. Classify the four guards above.

---

# JOB 2 — the instruments

Beyond H3:

## MEDIUM

### M1 — the tenancy root table has an untested policy: widening `workspaces_owner_read` to `using (true)` passes every gate

**Defect.** `05_assert.sql:744-745` introduces the cross-tenant assertion with *"round 5's
cross-tenant assertion read ONE view and ONE table … Read everything."* It then reads **five**
objects (`:750-754`): `video_artifacts`, both ranking views, `video_generations`, `workspace_videos`.
`workspaces` — the table this spec created, and the table every one of those five policies resolves
tenancy *through* — is not among them.

**MEASURED**, in an isolated copy:

```
widened workspaces_owner_read to using(true)   -> ✅ schema verified (rolled back)   [all 119 green]
                                               -> ✅ guard coverage green
```

For contrast, and to the design's credit, I confirmed the covered cases really are covered: removing
`security_invoker` from both views fails with `cross-tenant leak: 0 raw, 6 via the view`, and widening
either `video_artifacts_owner_read` or the two `03` policies fails with `13 rows across 5 objects`.
The gap is specifically `workspaces`.

Note also that this is the one policy written differently from its three siblings — no `to
authenticated`, and bare `auth.uid()` instead of `(select auth.uid())` (`01:22` vs `03:78-79`,
`03:491-492`, `04:674-675`). Same one-site shape.

**Impact** (REASONED): `grant select on workspaces to authenticated, anon` (`01:21`), so a widened
policy discloses every `(workspace_id, owner_id)` pair in the system. That is identifier disclosure,
not content — `art_key_names_workspace` still confines keys, and the artifact tables have their own
policies. Medium rather than High for that reason.

**Change.** Add `workspaces` to the `:750-754` sum, and add mutations for the four policies and the
three `security_invoker` clauses — currently **zero** mutations touch a policy, a grant, a revoke or
`security_invoker` (`grep` over `mutate-schema.py` returns nothing for any of them), so the entire
tenancy surface rests on assertions that no mutation has ever confirmed can fail.

---

# JOB 3 — the invariants

## MEDIUM

### M2 — the free path is fenced by nothing: any caller clears a live lease and repoints the address

**Defect.** `record_artifact`'s free branch (`04:482-490`) upserts on `video_artifacts_free_uq` with
no token check, no state check, and no caller identity — while the two paid paths both fence on
`lease_token = p_token`. Round 9 extended this branch to *clear* `lease_expires_at`, `lease_token`
and `reserved_at` (`04:488`) so a reserved free slot could be recorded; it did not ask who may clear
them.

**MEASURED** (`pB.sql`):

```
W1 reserve free html  -> reserved token=t
   row: state=pending  token set=t  expires set=t
W2 record with NO token, live lease -> recorded_free
   row now: state=recorded  blob_key=STOLEN.html  lease_token=<cleared>
W1 renew its own lease -> lost
```

**Impact.** Bounded: `art_key_names_workspace` (round 9 H5) still confines the key to the caller's own
workspace, renders are free, and re-renders are meant to be deterministic. The cost is that the lease
`04:476` justifies — *"a free render … may still want a lease against two workers doing the same CPU
work"* — provides no exclusion at all, plus a `blob_key` swap the append-only trigger deliberately
does not police for free rows (`04:905`). Medium, not High, because no money and no tenant boundary
is crossed.

**Change.** Fence the free `do update` on `(lease_token is null or lease_token = p_token or
lease_expires_at < now())`, i.e. take the slot only if it is unheld, yours, or dead.

### M3 — round 9's two free-path fixes contradict each other: a free slot can be leased once, ever

**Defect.** Round 9 H2 made `reserve_artifact_slot`'s short-circuit reachable for free slots by
switching to `is not distinct from` (`04:287-292`), so a recorded free slot now returns
`already_recorded`. Round 9's other free fix (`04:467-476`) added lease-clearing so that
reserve-then-record works for free slots. The first makes the second unreachable after the first
render.

**MEASURED** (`pE.sql`):

```
(a) first free record            -> recorded_free
(a) reserve for a SECOND render  -> already_recorded  (token=none)
```

So the CPU-dedup lease `04:476` argues for is available only for a slot that has never been
rendered — exactly the case where two workers colliding matters least. Every subsequent re-render is
unleasable and races freely.

**Change.** Decide which it is. If free slots are leasable, the short-circuit must not fire for a
caller that is asking for a lease on a re-render; if they are not, drop the lease-clearing and the
`reserve` branch for null generations and say so as a guard rather than as the convention round 9
correctly rejected.

## LOW

### L1 — dead branch
`04:517` re-tests `if p_generation_id is not null then` after `04:482` has already returned for the
null case. Always true. Harmless, but it reads as a live free/paid branch and cost me a probe to rule
out. Delete it.

### L2 — recorded free rows are deletable and mutable with no guard, and that decision is not stated where it is enforced
`video_artifacts_append_only` gates its whole body on `old.generation_id is not null` (`04:905`), so
a recorded free row can be deleted outright — **MEASURED**, `(c) DELETE of a recorded FREE row -> 1
row(s) deleted`. This follows from `04:466` ("the ADDRESS IS MUTABLE" for free rows) and is almost
certainly intended, but the trigger that implements it says nothing, and `04:851-875`'s long
append-only argument reads as table-wide. One sentence at `:905`.

### L3 — the 5-minute `produced_at` tolerance: checked, and it is fine
`03:455` accepts `now() + 4 minutes` (measured). For that to change a ranking outcome, rungs 1–3
(corrections currency, `doc_version_major`, card `mdGeneratedAt`) must all tie, which for two
distinct generations means two summaries of the same video at the same format with the same card
timestamp — at which point the ordering is arbitrary anyway. Round 7 B2's actual finding (a value
*years* ahead winning permanently) is still refused, and the suite asserts that. No change.

---

## Standing shapes — where the eleventh and twelfth instances landed

- **Shape #9 (a fix that moved or reintroduced a defect) — eleventh instance: H2.** Round 9's
  INSERT-half corrections guard made the second playlist's row permanently disagree with the shared
  body, and the UPDATE half then clears it. The state was unreachable before the fix.
- **Shape #10 (one-site fix, identical sibling nearby) — twelfth instance: H2 again** (INSERT half
  swept, UPDATE half not), with M2 (paid paths fenced, free path not) and M1 (four policies
  asserted, the fifth not) as the thirteenth and fourteenth.
- **Shape #11 (an instrument that misreports itself) — seventh instance: H3.** The ratchet reports
  the same "38 guards ✅" with the spec's cross-tenant FK present or deleted.
- **Shape #13 (a credential the honest caller cannot present) — H1**, in the fix written for shape
  #13. The premise "worker_id is stable config" is contradicted by `worker/main.ts:69`.
- **Shape #2 (identity as grant) — B1.** The credential is a plaintext column of the row it fences.

## Verdict

**NOT CONVERGED** — 1 Blocking, 3 High, 3 Medium, 3 Low. B1 and H1 are the same fence measured from
its two ends and should be fixed as one change; H2 and H3 are independent.
