# Claude adversarial review — `2026-08-04-cas-fence-persist-summary-design.md` (round 1)

**Reviewer:** Claude (adversarial mandate)
**Branch:** `docs/cas-fence-spec` @ `19133e7`
**Date:** 2026-08-04
**Method:** every cited `file:line` re-read on this branch; jsonb and privilege semantics **measured**
against the running local Postgres (`supabase_db_youtube-playlist-summaries-cloud`), not inferred.

---

## Verdict

**NOT CONVERGED — do not implement as written.** The central insight (guard the sink) is right and the
predicate is type-safe against every writer that exists today. But the design has **2 Blocking** defects
that each convert a data-loss bug into a *money* bug — the guard's failure taxonomy routes two
non-race conditions into the retryable bucket where each one costs up to 5 full Gemini runs, and §6's
recovery pseudocode as written re-persists the **stale key** under a green guard, silently reproducing
the exact incoherence the slice exists to remove. Separately, §0 and §7 give **contradictory
justifications** for deferring the slug half, and only §7's is true.

---

## Blocking

### B1 — The predicate is false for THREE row states; §5's taxonomy has room for two, and the third lands in the bucket that spends money

`v.data->'serialNumber' = to_jsonb(p_expected_serial)` (spec §4) is not-true for three distinct
states, which I measured rather than assumed:

```
to_jsonb(null::int) IS NULL                     → true    (to_jsonb is STRICT)
'{"s":7}'::jsonb->'s'  = to_jsonb(null::int)    → NULL    (⇒ 0 rows)
'{"x":1}'::jsonb->'s'  = to_jsonb(7)            → NULL    (⇒ 0 rows)   -- key ABSENT
'{"s":7}'::jsonb->'s'  = to_jsonb('7'::text)    → false
'{"s":7}'::jsonb->'s'  = to_jsonb(7.0::numeric) → true                 -- scale is fine
```

So zero affected rows means **(a)** the serial moved, **(b)** the row has no `serialNumber` key at
all, **(c)** `p_expected_serial` arrived as NULL, or **(d)** the stored value is not a JSON number.
§5's re-probe asks only *"does a row exist for (playlist, video, owner)?"* — and for (b), (c) and (d)
the answer is **yes**. All four therefore classify as `serial-moved` → **recoverable → retry**.

**What that costs, concretely.** Take a row where `data` has no `serialNumber` key. The re-address loop
(§6) calls `reserveVideoSlot` first. `reserve_video_slot` raises
`'reserve_video_slot: existing video %/% has no serialNumber (invariant)'`
(`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:90`). That raise is not a
`NonRetryableError`, so in `lib/job-queue/worker-runner.ts:69-76`:

- `retryable: !isNonRetryable(e)` → **true** → the job requeues;
- `billing.metered` is **true** (Gemini already ran), so `release` at `:66-68` is false → the
  reservation is **not** released — the spend is kept, correctly;
- `jobs.max_attempts` defaults to **5** (`supabase/migrations/0008_jobs_queue.sql:14`).

⇒ **5 full Gemini summary runs (~8¢ each, ≈40¢/video) ending in `dead_letter` with no summary.**
Today, with no guard, that same row persists successfully on attempt 1 and costs 8¢. The guard makes
the money outcome **5× worse** for this input, and it looks like the guard working.

Case (c) is not hypothetical hygiene: "required, not defaulted" in PostgreSQL means *the argument must
be supplied*, **not** that it must be non-NULL. `Video.serialNumber` is `z.number().int().positive().optional()`
(`types/index.ts:67`), and `persistSummary` takes `video: Partial<Video>`
(`lib/storage/worker-persistence.ts:20`) — an `undefined` reaching the RPC serialises to JSON `null`
and fails **closed and silently**. `claim_video_slot` already faces this exact problem and solves it
properly at `supabase/migrations/0023_claim_video_slot_desired_serial.sql:46-48` with an explicit
`raise` — the precedent exists in the repo and §4 does not follow it.

Note this is the spec's own standing root-cause shape (§11: *absent-vs-failed conflation*) applied to
its own predicate: a value meaning ABSENT is also what a FAILURE produces.

**Fix.**
1. `if p_expected_serial is null then raise exception 'persist_summary: p_expected_serial is required'; end if;` — mirroring 0023:46-48.
2. Make the taxonomy **three**-way, and probe the **value**, not the row's existence:
   ```sql
   select v.data->'serialNumber' into v_actual from videos v where …;   -- row-existence + value in one probe
   if not found                              then raise … 'row-gone'      (FATAL)
   elsif v_actual is null
      or jsonb_typeof(v_actual) <> 'number'  then raise … 'serial-unusable' (FATAL)
   else                                            raise … 'serial-moved'  (RETRYABLE)
   ```
3. The worker must map both fatal codes to `NonRetryableError` — otherwise §5's "the two errors must be
   distinguishable *by the caller*" is satisfied on paper while the caller still burns `max_attempts`.

### B2 — §6's loop is not specified to rebuild the payload, and reusing it re-persists the STALE key under a green guard

`summary-handler.ts:149-164` builds the `Video` literal **once**, carrying `serialNumber: serial`
(`:156`) and `summaryMd: \`${baseName}.md\`` (`:157`). §6's pseudocode recomputes `serial` and
`baseName` and re-stages the blob, but the persist line is written as
`persistSummary(..., expected := serial, 'committed')` — it never says the `video` payload is rebuilt.

If an implementer reads that literally (and the pseudocode invites it — `video` is not in the loop
body at all), attempt 2 passes:

| | value |
|---|---|
| `p_expected_serial` | `3` — the NEW serial |
| row's `data->'serialNumber'` | `3` |
| **guard** | **passes** ✅ |
| `p_video->>'summaryMd'` | `'007_alpha.md'` — the **OLD** key |

`persist_summary` resolves `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')`
(`0021_cloud_sync_signals.sql:133`) — **payload wins** — and stamps
`artifacts.summaryMd.key = '007_alpha.md'` at `:137`. The row ends up `serialNumber 3` beside
`summaryMd 007_alpha.md`: **byte-for-byte the incoherence in the spec's own §1 table, step 5**, now
produced *by the fix*, *with the guard green*, and with a freshly staged blob sitting unreferenced at
`003_alpha.md`.

This is a money/data-loss path, so it must be stated, not inferred. **Fix:** §6 must say explicitly
that `serialNumber`, `summaryMd` and `baseName` in the payload are **recomputed on every attempt**, and
§8 must require a positive assertion — after a successful re-address, `data->>'summaryMd'` equals
`<newBase>.md` **and** `data->'artifacts'->'summaryMd'->>'key'` equals `<newBase>.md`. §8's current
"assert the row is not incoherent" is the right *shape* but is satisfiable by a test that only checks
the RPC raised.

---

## High

### H1 — Required-and-undefaulted + drop/recreate breaks the rolling deploy, and the repo already documented this exact hazard twice

`fly.toml:32-34` runs `web` and `worker` as **two process groups from one image**. Migrations apply
before the image finishes rolling out, so for the length of the window old worker machines are still
calling the 5-arg `persist_summary`.

`supabase/migrations/0023_claim_video_slot_desired_serial.sql:27-35` documents this precise failure and
solved it by keeping an explicit 2-arg back-compat wrapper, spelling out that a `DEFAULT` does **not**
help because *"PostgREST resolves an RPC by the named arguments in the request body."*
`0021_cloud_sync_signals.sql:5-12` documents the sibling PGRST203 footgun. §4 of the spec asserts
"the function must be dropped and recreated" with **no wrapper, no deploy note, and no mention of
either migration's lesson.**

Consequence: during the rollout every in-flight persist from an old worker gets PGRST202
*function not found* — **after Gemini has already been billed** — requeues, and re-runs Gemini.

There is a genuine tension here and the spec should resolve it rather than ignore it: a back-compat
wrapper *is* an unguarded path, which is what §4's "required, not defaulted" rule exists to forbid.
The resolution that satisfies both: **keep the 5-arg signature alive but make it raise**
(`raise exception 'persist_summary: caller must pass p_expected_serial'`). Deploy-safe (old callers get
a clean, classifiable error instead of a schema-cache miss) and fail-closed (no unguarded write can
ever land). Whichever is chosen, §4 must say which and why.

### H2 — Grants do not survive the drop, and the failure is silent because the default is *more* permissive

Measured on the live DB:

```
create function probe_tmp.f(int) …;
  → pg_proc.proacl = NULL   (= default: EXECUTE to PUBLIC)
  → has_function_privilege('anon','probe_tmp.f(int)','EXECUTE') = true
```

`0023:24-25` states the rule outright — *"Privileges do not survive the drop, so the revoke/grant is
re-issued below."* The spec never mentions grants. If the migration omits
`revoke all on function persist_summary(uuid,uuid,text,jsonb,text,int) from public;` +
`grant execute … to authenticated, service_role;` (mirroring `0021:154-155`), the function still
**works** for every legitimate caller via the PUBLIC default — so nothing fails, no test goes red, and
the regression ships unnoticed.

Impact is contained rather than critical: `persist_summary` is `security invoker` and raises
`'not authorized'` at `0021:103` for a caller that is neither the owner nor `service_role`, so an
`anon` caller gets a denial, not data. It is a hardening regression and a break from the pattern every
other migration in this repo follows — worth a line in §4 and a line in the migration.

### H3 — ~19 existing named-arg call sites break, and Open Question 2 asks the wrong question

OQ2 asks whether anything calls `persistSummary` **positionally**. Nothing does — but that is not where
the breakage is. PostgREST resolves by argument **names**, so a 5-key request body against a
6-arg-only signature is a PGRST202 *at runtime*, invisible to `tsc`:

- `tests/integration/worker-persistence-rpcs.test.ts` — 16 direct `admin.rpc('persist_summary', {…5 keys})`
  calls at `:59, :60, :71, :86, :99, :100, :109, :118, :130, :141, :156, :159, :172, :175, :195, :218`
- `tests/integration/helpers/cloud.ts:118-125` — a **shared helper** wrapping the RPC; used by
  `tests/integration/cloud-sync/stamping.int.test.ts:93`. This is the one to watch: the breakage fans
  out from one file.
- `tests/integration/worker-storage-bundle.test.ts:87` — via the TS wrapper, which gains a required
  parameter (this one `tsc` *will* catch).

OQ2 should be reworded to "does any caller pass arguments by name?" — answer: **all of them do**, and
all must be updated in the same commit. The `as any` warning in OQ2 is correct but aimed at a risk that
does not exist here; the real one is that integration tests are not type-checked against the RPC schema
at all.

### H4 — The recovery loop lengthens the post-Gemini window and the spec never mentions the lease

`runOnce` (`lib/job-queue/worker-runner.ts`) leases **120 s** by default (`:25, :28`), heartbeats every
`leaseSeconds/3` ≈ 40 s (`:48-52`), and hard-aborts the entire job at `wallClockMs` = **600 000 ms**
(`:45`). §6's loop adds up to 3 × (putStaged → exists → persist → promote → persist) ≈ **15 extra
network round-trips**, all *after* Gemini has consumed most of that wall clock.

`summary-handler.ts:170` checks `ctx.signal.aborted` exactly **once**, before the first write, and its
comment says why: *"don't start the irreversible blob/persist sequence"* if the lease was lost. §6's
loop re-enters that irreversible sequence up to three more times and **never re-checks the signal**. A
lost lease means `sweep_expired_leases` (`0009:63-77`) requeues the job and a second worker starts
Gemini concurrently — a double charge caused by the fix for a stale write.

**Fix:** §6 must specify `if (ctx.signal.aborted) throw AbortError` at the top of **every** attempt, and
should state the wall-clock budget the loop is allowed to consume.

### H5 — §0 and §7 give contradictory reasons for deferring the slug half, and §0's is false

§0 defers the slug to backlog #20 on the grounds that *"it is not a race: it needs no second writer and
no window."* That is wrong for A3 specifically, and A3 is the source this spec analyses.

`lib/cloud-sync/reconcile-serial.ts:151-155` computes the target from local's **full base** (serial
*and* slug), and `:183-186` relocates whenever the **bases** differ — including when the serials
**agree** and only the slug moved (a YouTube title change on one side). Interleaving with values:

| Step | Actor | Effect |
|---|---|---|
| 1 | worker | `reserveVideoSlot` → `7`; pins `baseName = 007_alpha` (`summary-handler.ts:95-96`) |
| 2 | worker | Gemini — minutes |
| 3 | sync | local title changed; `describeDivergence` → `from='007_alpha'`, `to='007_beta'`; A3 copies `dig/007_alpha/*` → `dig/007_beta/*`, writes `summaryMd='007_beta.md'` (`:296`), deletes `dig/007_alpha/*` (`:358-361`). **`serialNumber` stays `7`.** |
| 4 | worker | `persistSummary(..., expected := 7)` — row serial is still `7` → **guard PASSES** |
| 5 | — | row = `serialNumber 7` beside `summaryMd 007_alpha.md`; paid digs stranded at `dig/007_beta/` |

Identical damage, identical mechanism, second writer, real window — under a green guard. §0's stated
reason for deferring is therefore not merely incomplete, it is **wrong**, and a reader who accepts it
will conclude the concurrent half is closed when it is closed only for serial-only divergence.

§7 already gives the **true** reason — G2: a bare reserved row carries no `summaryMd`, so a base-keyed
guard has nothing on the left-hand side of a first-summary predicate. Keep §7's argument, delete §0's,
and state plainly in §2 that **slug-only concurrent divergence is a known residual this guard does not
close.** (Then §0's *"there is exactly one sink"* framing survives; it is the *predicate* that is
partial, not the location.)

---

## Medium

### M1 — The stated rationale for jsonb-over-cast is wrong in a way that will mislead the implementer

§4 rejects `(v.data->>'serialNumber')::int = p_expected_serial` because it *"would raise on any row
whose serial is malformed"*, and calls the jsonb form *"total."* Two problems:

1. The same unguarded cast on the same column already exists **three times** in the functions this
   design depends on: `0009:86` (inside `reserve_video_slot`, the **first** call the §6 loop makes),
   and `0023:57, :65, :83`. A serial malformed enough to raise raises in `reserveVideoSlot` before the
   guard is ever consulted. The risk the jsonb form avoids is not avoidable.
2. The jsonb form makes the **predicate** total, not the **operation**. Its real behavioural difference
   is that it is **silent** where the cast is loud: a malformed serial becomes "not equal" → "the base
   moved" → retry (see B1) instead of an immediate, correctly-classified error.

jsonb equality is still the right choice — but for the honest reason: *the predicate must distinguish
"different" from "unreadable" rather than conflating them into a raise*. Which is exactly why B1's
explicit `jsonb_typeof` check has to accompany it. As currently argued, §4 tells the implementer the
predicate handles a case it merely hides.

### M2 — G1 ("`serialNumber` is present on every video row") is enforced at one door; a second door removes it

G1's evidence proves only that `reserve_video_slot` (`0009:79-100`) maintains it. There is **no CHECK
constraint, no NOT NULL, no trigger** — I looked. And `SupabaseMetadataStore.upsertVideo`
(`lib/storage/supabase/supabase-metadata-store.ts:113-121`) does a **wholesale replace**:
`.update({ data: stripComputed(video) })` — not a merge. Any caller whose `Video` lacks
`serialNumber` (the field is `.optional()` at `types/index.ts:67`) **erases the key from the row.**

The nearest live path: `copyAdditiveVideo` sets `sanitized.serialNumber = slot.serialNumber` only
`if (slot)` (`lib/cloud-sync/sync-run.ts:277`), and `slot` is `null` when the receiver row already
existed (`ensureReceiverSlot:188`) — the comment at `sync-run.ts:265-267` calls that "unreachable in a
single-run sync," which is a claim about scheduling, not a constraint. `sanitized` is typed `any`
(`:275`), so nothing checks it.

The test suite itself constructs counterexamples on purpose
(`tests/integration/worker-persistence-rpcs.test.ts:181-184`,
`tests/integration/quickview-route-cloud.test.ts:119`).

G1 should be restated as *"maintained by convention at every writer; not enforced by the schema"* —
because a guard that fails **closed** on absence (measured: `'{"x":1}'::jsonb->'s' = to_jsonb(7)` → NULL
→ 0 rows) is only as safe as that convention. With B1's fix this degrades to a clean non-retryable
error instead of a retry storm, which is the point of raising it here.

### M3 — Re-address + the key-scoped monotonic status can advertise `promoted` for bytes still in staging

`0021:142-150` preserves `'promoted'` against a `'committed'` write **when the key is unchanged**.
The re-address loop can now satisfy that condition with a *different blob*:

1. A3 relocates `7 → 3`: copies the old body to `003_alpha.md` and writes
   `artifacts.summaryMd = { key: '003_alpha.md', status: 'promoted' }` (`reconcile-serial.ts:296`).
2. Worker's guard rejects; it re-addresses to `003_alpha`, stages `003_alpha.md`, calls
   `persistSummary(..., 'committed')`.
3. Existing key `003_alpha.md` **equals** `coalesce(p_video->>'summaryMd', …)` = `003_alpha.md`, and
   existing status is `'promoted'` ⇒ `0021:145-149` **keeps `'promoted'`** — for bytes that are still
   in staging.

Not a 404: the object at that key holds A3's copied (stale) body, so the serve path returns *old*
content, and it self-heals one round-trip later at `promote` + the `'promoted'` persist. But this is
outside the case the key-scoping was designed for (`0021:138-141` reasons about a *different* key
meaning a genuinely new artifact), §5/§6 assert nothing about it, and §8 has no test. At minimum name
it in §5; better, have the loop persist the first write of a re-addressed attempt in a way that cannot
inherit a foreign `promoted`.

### M4 — The dig path has the same exposure, a *different* sink, and §2/§9 never mention it

`lib/job-queue/dig-handler.ts:55-57` derives `base` from `resolveSummaryMdKey(video)`, then spends
minutes in Gemini (`:100-113`), then writes `dig/<base>/<sectionId>…` at `:119-125`. A relocation in
that window writes a **paid dig straight into a prefix A3 has already deleted**.

Two reasons the spec's silence is not defensible as written:

- The code the spec cites contradicts it. `reconcile-serial.ts:44-52` names `dig-handler.ts:51-57` as
  an equal hazard, and `lib/cloud-sync/in-flight-job.ts:69-70` says outright: *"NOT FILTERED BY
  `job_kind`. Summary jobs and dig jobs BOTH pin `base` … A `job_kind` filter here would silently
  reopen the window for digs."*
- §0's "**there is exactly one sink**" is **false** for dig. The dig sink is a **blob write**, not an
  RPC — there is no row-conditional write to attach a CAS to. So "one guard covers every source,
  including sources not written yet" does not extend to it, and a reader will conclude digs are covered.

Dig does not need to be *in* scope. But §9 must list it explicitly with a backlog number, and §0's
one-sink claim must be scoped to the summary path.

### M5 — Open Question 1 is answerable now: no deadlock, but `reserveVideoSlot` is the wrong re-read

**Answer: safe, and the question can be closed.** `reserve_video_slot` takes `for update` on the
`playlists` row (`0009:84`). Each PostgREST RPC is its own transaction, so the lock is acquired and
released **within one call** — the loop never holds it across the blob round-trips. There is no second
lock to order against: `merge_video_data` (`0021:71-72`, A3's metadata write) takes **no** `for update`,
and `claim_video_slot:50-52` takes the same single lock. No deadlock, no livelock.

Livelock is separately bounded by PR #45: while the job is `active`, `supabaseInFlightJobProbe`
(`in-flight-job.ts:21, :116`) reports `inFlight` and A3 **refuses** to relocate — so a second relocation
cannot occur *during* the loop. **This is the missing justification for N = 3** (§6 currently asserts
the bound with no argument) and it should be written into the spec.

But `reserve_video_slot` is still the wrong tool: it is a **write** function used as a read, it takes a
lock it does not need, it costs a round-trip, and it is the function that **raises** on both B1 failure
modes (`:86` cast, `:90` invariant). Better: have `persist_summary` **return the observed serial** in
the rejection (via `errcode` + `detail`, or by returning a row instead of `void`). The worker then needs
no re-read at all — one fewer round-trip, no lock, and the classification is decided by the same
statement that observed the state, which is the TOCTOU argument §4 already makes about the predicate,
applied one level up.

### M6 — §6's cleanup sentence is wrong for the second branch: the leak is a *promoted* blob, not a temp one

§6 says *"Temp-blob cleanup is best-effort. A leaked staging object is inert and swept by existing
staging cleanup."* True for the first branch. But the second branch is `promote(ref)` → then
`persistSummary(…, 'promoted')` rejected → *"next attempt (re-stage and re-promote under the new
base)"*. At that point `<oldBase>.md` is a **promoted, permanent** object that no staging sweep
collects. Whether A3's cleanup removes it is timing-dependent — `reconcile-serial.ts:358-361` deletes
only the plan computed from `paidKeysUnder` **before** the copy phase, so a blob promoted after that
enumeration is never in the plan. Small (storage, not loss), but the sentence as written is factually
inaccurate about the branch that actually leaks.

---

## Low

- **L1 — §8's double-charge test is under-scoped.** *"Assert Gemini is invoked exactly once across a run
  that re-addresses"* covers only the **successful** re-address. The expensive path is **exhaustion**:
  the loop throws retryable → requeue → attempt 2 runs Gemini again. Add an assertion for the
  exhaustion path, and state the honest bound: `jobs.reserved_cents` is **per-job and reused across
  retries** (`0020_reservation_release.sql`, Task-13 comment), so there is **no second reservation** —
  but there are up to `max_attempts` = 5 **real** Gemini charges against one reservation, i.e. the
  ledger **under-counts** actual spend on this path. That is the money claim to assert, and §8 should
  say it in those terms rather than "no double charge."

- **L2 — §11's `check-docs.py` line is a verification step, not evidence it passed.** Cheap to run
  before the next round; it is the repo's own unpromoted-decision detector.

- **L3 — Open Question 3 (`docVersion`) should be closed, not carried.** The version mismatch is already
  handled non-retryably at `summary-handler.ts:73-77`, and `docVersion` is not part of `base`, so a
  relocation cannot strand blobs through it. Say "out of scope, and here is why" rather than leaving it
  open.

---

## Spec claims I checked

### Confirmed correct

| Claim | Verified |
|---|---|
| **G1** `reserve_video_slot` inserts `jsonb_build_object('id',…,'serialNumber',…)`; raises `(invariant)` | insert `0009:94-96`, `jsonb_build_object` on `:95`, raise `:90` ✅ (but see **M2** — it is one door of two) |
| **G2** a bare reserved row has only `id` + `serialNumber` | `0009:95` ✅ |
| **G3** `summaryMd` payload-wins, `serialNumber` row-wins | `0021:133` vs the whitelist ✅ |
| **G4** zero rows raises exactly one error today | `0021:152` ✅ |
| **G5** `summaryCore` accepts `baseName` and deliberately never destructures it | `lib/ingestion/summary-core.ts:60-62` — the comment is verbatim at `:60-61` ✅ |
| **G6** stage → persist(committed) → promote → persist(promoted) | `summary-handler.ts:172-179` ✅ |
| **G7** `persistSummary` has exactly one production caller | `worker-persistence.ts:18-27`, called only from `summary-handler.ts:177,179` ✅ (test callers exist — see **H3**) |
| **G8** `transferClassA` never writes `serialNumber` | `sync-run.ts:371-437`; `completeTuple` `:397-432` contains no `serialNumber` ✅ |
| §0: `checkSerialInvariant` cannot fail on the slug, because `applySerial` copies the slug out of the value being checked | `lib/serial-invariant.ts:54` is exactly `const expected = applySerial(value, serial);`, and `applySerial` (`lib/serial-filename.ts:21-27`) strips-then-re-prefixes the same basename ✅ **The sharpest observation in the spec, and it is right.** |
| §0: "fencing" is already taken for lease fencing | `0008_jobs_queue.sql:94` is the lease-fencing comment; `0009:55` is the `lease_token` predicate ✅ Both citations exact. |
| §1.2: PR #45 refuses while a job is pending or recently swept | `reconcile-serial.ts:239-251`; statuses at `in-flight-job.ts:21, :33` ✅ |
| §1.2: the `:236` comment states the honest scope | `reconcile-serial.ts:236` — *"a large reduction, not an elimination."* ✅ |
| §6: the idempotency skip keys on `status === 'promoted'` and so cannot rescue a rejected write | `summary-handler.ts:86-92` ✅ |
| §4: jsonb equality is type-strict (`7` ≠ `"7"`) | **measured**: `false` ✅ — and no writer produces a string today (see below) |

### Found wrong or imprecise

| Claim | Finding |
|---|---|
| §1.2 cites `reconcile-serial.ts:232-236` for *"a loop of N sequential blob round-trips"* | **Wrong citation.** `:231-236` is *comment prose describing* the loop. The loop is `:281-290`. The statement is true; the pointer sends a reader to the wrong construct. |
| §1.1 cites `0021:121-134` for the whitelist | Off by a few lines: the `jsonb_build_object` whitelist is `:120-132`; `:133` is the `summaryMd` line (correctly cited separately) and `:134` begins `artifacts`. Cosmetic. |
| §4: the jsonb predicate is *"total"* | **Misleading** — see **M1**. It is total as a *predicate* and silently wrong as a *classifier*. |
| §4: "required, no default" prevents an unguarded call | **False as stated** — a required parameter can still be passed `NULL`, and `to_jsonb(null::int)` is SQL NULL (measured), so the write fails closed and is misclassified. See **B1**. |
| §3 G1: "`serialNumber` is present on **every** video row" | **Not enforced.** No constraint; `upsertVideo` replaces `data` wholesale. See **M2**. |
| §0: the slug half *"is not a race: it needs no second writer and no window"* | **False.** A3 relocates on slug-only divergence with the serial unchanged. See **H5**. |
| §0: *"There is exactly one sink."* | **True for summary, false for dig** — the dig sink is a blob write with no row to CAS against. See **M4**. |
| §10 OQ1 ("is `reserveVideoSlot` safe in a retry loop?") | **Answerable now — yes.** See **M5**; close it rather than deferring to implementation. |
| §10 OQ2 ("does anything call positionally?") | **Wrong question.** Nothing calls positionally; ~19 call sites call by **name** and all break. See **H3**. |

### The claim I most expected to break, and it held

I searched every writer of `data->'serialNumber'` — `reserve_video_slot:95`, `claim_video_slot:67,89`,
`merge_video_data` (`0021:79-90`, via `updateVideoFields`), `upsertVideo`
(`supabase-metadata-store.ts:113-121`), `reconcile-serial.ts:294`, `sync-run.ts:277`,
`serial-migrate-exec.ts:16`, `pipeline.ts:107` (`parseInt`), plus every test fixture that seeds one
(`helpers/seed.ts:39`, `helpers/cloud.ts:394`, `review-route-cloud.test.ts:179`,
`annotations-rpc.test.ts:81,108`, `quickview-route-cloud.test.ts:81,96,119`). **Every one writes a
number.** The SQL sites pass an `int` into `jsonb_build_object`; the TS sites pass a `number` typed by
`z.number().int().positive()` (`types/index.ts:67`).

So the predicate is type-safe **against the writers that exist today** — the review brief's hypothesis
does not land. What I would record instead: nothing *enforces* it. `upsertVideo` replaces `data`
wholesale from a value that reaches it as `any` at `sync-run.ts:275`, and there is no CHECK constraint.
B1's `jsonb_typeof(v_actual) <> 'number'` branch costs one line and converts that from a latent
retry-storm into a clean non-retryable error.

---

## What I could not verify, and why

1. **That PostgREST returns PGRST202 (not PGRST203) for a 5-key body against a 6-arg-only signature.**
   The local `supabase_edge_runtime` / pooler services are stopped, so I could not issue a live RPC. I
   verified the *mechanism* from `0023:27-35` and `0021:5-12`, which document PostgREST's named-argument
   resolution from prior measured incidents on this repo. **H3 and H1 rest on that documented behaviour,
   not on my own measurement** — worth one live probe before implementation.

2. **The actual `jobs.reserved_cents` value and therefore whether 5 retries can exceed the reservation.**
   I read the reserve→release lifecycle (`0020`) and the per-job reuse comment, but did not trace the
   sizing function. L1's claim is directional ("the ledger under-counts") and safe; the exact multiple
   is unverified.

3. **Whether any *production* input actually reaches `copyAdditiveVideo` with `slot === null`.**
   `sync-run.ts:265-267` argues it is unreachable in a single-run sync. I did not attempt to construct a
   counterexample. M2 does not depend on it — the wholesale-replace shape of `upsertVideo` is the
   finding; that path is one illustration.

4. **End-to-end timing of the §6 loop against the 120 s lease.** H4 is a structural argument from
   `worker-runner.ts:25,28,45,48-52`; I did not measure real blob round-trip latency, so I cannot say
   how often the loop would actually outlive a lease — only that nothing in §6 checks.

5. **`scripts/check-docs.py`** — not run (L2); it is a step the spec itself lists as pending.

---

## Standing root-cause shapes (§11) — hits this round

| Shape | Where it recurred |
|---|---|
| *absent-vs-failed conflation* | **B1** — the guard's own predicate has three false-cases and a two-case taxonomy |
| *a guard with no covering test* | **B2** — no test asserts the payload's key after a re-address; **M3** — no test for the inherited `promoted` |
| *a value read in one process and written in another* | **H4** — the lease/abort signal is read once by the handler and mutated by the runner's heartbeat, and §6 re-enters the write sequence without re-reading it |
| *an optional member that does not propagate* | **B1(c)** — "required" in SQL does not mean "non-NULL"; `Partial<Video>` makes `serialNumber` optional at the wrapper |
