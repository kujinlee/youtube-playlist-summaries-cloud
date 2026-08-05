# Claude adversarial review — `2026-08-04-cas-fence-persist-summary-design.md` (round 3)

**Reviewer:** Claude (adversarial mandate)
**Branch:** `docs/cas-fence-spec` @ `b3edfad` (spec v3)
**Date:** 2026-08-04
**Method:** every v3 citation re-read on this branch. Postgres SQLSTATE validity, PostgREST overload
resolution **against v3's actual 5-arg + 8-arg-with-default shape**, custom-errcode surfacing, and
`null`-for-a-defaulted-parameter measured live against
`supabase_db_youtube-playlist-summaries-cloud` / `supabase_rest_…` on `127.0.0.1:54321`. **Supabase
Storage `put`-overwrite and `move`-onto-existing-destination measured against the live storage
container** — this closes round 2's "could not verify" item 1. All probe objects (`public.probe_ps`,
`public.probe_code`, schema `probe_r3`, bucket `probe-r3`) dropped; `select count(*) from pg_proc
where proname like 'probe_%'` → `0`.

---

## Verdict

**NOT CONVERGED.** Three new Blockings, all again in the write/recovery sequence, none in the
predicate — the round-3 standing shape v3 itself wrote down (§11) held for a third round.

- **B-R3-1** — `observedSerial` has **no defined provenance**. The only source §6 names (the `:84`
  read) is `null` on the dominant first-time path, and §4 mandates the `?? null` coercion for
  `p_expected_summary_md` **only**. The natural implementation 404s or raises `22004` *after Gemini
  has been billed*. The one provenance that works (`reserveVideoSlot`'s return) makes the expected
  tuple a **torn read** across two statements, which §6 never acknowledges.
- **B-R3-2** — `p_artifact_is_new` + `publish = put` **together** convert a stale worker's write from
  non-corrupting into destructive. This answers §10 OQ1: **no, the boolean is not safe, and the
  circularity is real.** Measured window: the heartbeat fires every `leaseSeconds/3` = **40 s**
  (`worker-runner.ts:47-52`), so a worker can be up to 40 s past lease loss with
  `ctx.signal.aborted === false`.
- **B-R3-3** — `publish(ref, key)` = `put` **discards the verification it depends on**. The object
  that was verified is the *temp*; the final key receives a **second, unverified** upload, and §6
  mandates no verify-after-write. `copyBlob` verifies after write for exactly this reason
  (`blob-store.ts:161-171` — *"an unproven copy is not a copy"*), and the precedent §6 cites
  (`transferClassA`) does not verify either — so v3 inherits an unverified money-path write.

Two things v3 got genuinely right, and I could not break them (details in *Verified, not findings*):
the `committed → publish → promoted` ordering with its 503 window (H-N3), and the adopt-the-observed
-address rule for the **serial** and **slug** races. G12 is now **confirmed against live storage**,
not just read.

---

## (A) Round-2 findings — genuinely fixed, or reworded?

### Claude round 2

| # | Finding | Status | The v3 text, and whether the behaviour actually changes |
|---|---|---|---|
| **B-N1** | Same expected key passed to both persists → every first-time write rejected | **FIXED** | §6 line 270: `persistSummary(..., expected := (observedSerial, key),  # ← NOTE: `key`, not observedSummaryMd`, with a full paragraph at §6:277-284 deriving *why* the two calls differ, and §0:42-54's asymmetry table (`serialNumber` = any change, `summaryMd` = only a change the worker did not make). §8:363-366 adds the missing positive test — *"A plain first-time summary completes with **one** `'committed'` persist, one publish, one `'promoted'` persist, and **zero** `address-moved` rejections."* I re-walked all six paths in (B)(2); the guard now passes exactly when it should. This is behaviour, not prose. |
| **B-N2** | `promote` skips onto an existing destination → publishes A3's stale body | **FIXED (mechanism) / NEW DEFECT (verification)** | G12 added (§3:129) with `supabase-blob-store.ts:90-97`; §6:286-293 replaces `promote` with `put` and cites `sync-run.ts:386-395`; §8:357-361 now asserts **bytes** (`get(<newBase>.md)` equals the newly generated MD), not pointers. The stale-body loss is genuinely closed — **measured**: `move` onto an existing destination returns `409 Duplicate`, and `put` with upsert overwrites (`AAAA` → `BBBB`). But the replacement is unverified-after-write and unconditionally overwriting → **B-R3-3**. |
| **B-N3** | Stub unapplyable (`cannot change name of input parameter`) + unroutable | **FIXED** | §4:176-186 now writes the stub with **named** parameters and a comment stating both reasons (G15 for the rename, G14 for routability). §4:188 records that `create or replace` preserves the `0021:154-155` grants. Re-measured: a 5-key body against the live pair routes to the 5-arg stub, `HTTP 400 {"code":"0A000","message":"STUB-5ARG"}`. |
| **H-N1** | `undefined` is not `NULL` → PGRST202 after Gemini billed | **PARTIALLY FIXED** | §4:153-165 states *"Required is not non-null, and required is not present"*, gives `p_expected_summary_md: expectedSummaryMd ?? null`, and explains why `tsc` cannot catch it (`readVideo`'s `data.data as Video`). §8:377-378 requires the bare-row case go **through the TS wrapper**. Correct — and re-measured: a 6-key body → `HTTP 404 PGRST202`. **But the identical trap at `p_expected_serial` is not fixed** — see **B-R3-1**. The fix names one of the two parameters it introduced. |
| **H-N2** | Mutation targets dead code; serial branch untestable via A3 | **FIXED** | §8:367-372: *"Mutation checks target the classifier, not the `where`"*, explicitly states the `UPDATE` conjuncts are unreachable as guards, mandates mutating each `elsif`, **and** requires a serial-only fixture move *"modelling `claim_video_slot:65-68`, not A3"* with the reason (A3 always moves both halves, `reconcile-serial.ts:293-295` — verified). Both halves of H-N2 addressed. |
| **H-N3** | Promote-before-metadata trades a visible window for a silent one | **FIXED — and correctly** | G13 added (§3:130) with `serve-summary-core.ts:50` + `supabase-metadata-store.ts:54-55`. §6:295-301 keeps `'committed'`, states *"That 503 **is** what makes the ordering safe"*, and names the alternative's failure (200 with the new body beside A3-era scalars, frozen by the `:86-92` idempotency skip). §6:303-309 fixes inheritance narrowly instead. I attacked this directly (see *Verified*) and the ordering holds. **The narrow fix it chose is where B-R3-2 lives.** |
| **H-N4** | Grants fix has no covering test | **FIXED** | §8:380 — `has_function_privilege('anon', 'persist_summary(uuid,uuid,text,jsonb,text,int,text,boolean)', 'EXECUTE')` is **false**, with the 8-arg signature (matching §4:193-194). Signature string is correct for the v3 shape. |
| **M-N1** | N=3 justification contradicts §1.2 | **FIXED** | §6:311-315 — *"N = 3 is a choice, not a derivation… v2 justified it from PR #45's probe — but §1.2 refutes exactly that reasoning."* The probe argument is withdrawn and the cost is named (one blob round-trip per attempt vs a requeue + fresh ~8¢). |
| **M-N2** | §0 overclaims what the second conjunct guards | **FIXED** | §0:42-54 is rewritten to *"the two halves are NOT symmetric"* with the exact framing suggested: *"the serial is guarded against any change; the key is guarded only against a change this worker did not make."* |
| **M-N3** | SQLSTATEs unnamed → contract unimplementable | **FIXED** | §5:216-228 names `PS001`/`PS002`/`PS003`, puts the observed address in `detail` as JSON, forbids message matching, and requires `PS001`/`PS002` → `NonRetryableError`. **Measured valid and surfaced** — see (B)(5). Residual: `details` arrives as a JSON *string*, not an object (L-R3-3). |
| **M-N4** | Coverage table of untested behaviours | **MOSTLY FIXED** | §8 now covers bytes-not-pointers, the no-loop first-time path, grants, wrapper-level nullability, abort-on-every-attempt (§8:383), loop termination, both signatures live, and the 18 call sites. §8:392-394 names the two it does **not** cover (crash between publish and the promoted persist; loop-vs-lease wall clock) as structural arguments. Honest. New gaps in **M-R3-4**. |
| **L-N1** | "~19" is 18 | **FIXED** | G7 (§3:124) now says *"**18** named-arg RPC sites"*. Measured: `grep -rn "p_artifact_status" --include=*.ts` → **18**. |
| **L-N2** | Zero-row persist retryable today, fatal under the new design | **FIXED** | §5:233-235 — *"Behaviour change to record (L-N2)… a live change to an existing error path."* |
| **L-N3** | §7's "throwaway is one line" understates the work | **FIXED** | §7's table (§7:336) now says the classifier *"**narrows** to two outcomes"*, and §7:342-344 turns the whole section against §5.1's *"trivially sufficient"* claim. |

### Codex round 2

| # | Finding | Status | The v3 text |
|---|---|---|---|
| **C-B1** | `promote` keeps old bytes then advertises new metadata | **FIXED** | Same as B-N2 — G12 + `publish = put`. Codex's crash subcase is also addressed: §6 restores the `'committed'` breadcrumb on the re-address path (§6:295-301), which Codex specifically identified as *"the established committed step… §6 removes that breadcrumb for re-address attempts."* |
| **C-B2** | `p_expected_summary_md` stale-by-construction for a legitimate re-summarize; spec must distinguish "expected current key" from "new key" | **FIXED, and beyond what Codex asked** | Codex's warning — *"If an implementer instead sources `p_expected_summary_md` from the payload key, this exact legitimate re-summarize fails closed"* — is answered by §6:270's explicit `key`-vs-`observedSummaryMd` split and §0's asymmetry table. **But Codex's *other* branch is now what happens:** the adopt rule means the payload key can no longer differ from the row key at all, which silently changes re-summarize addressing — **H-R3-1**. Codex flagged this as *"valid if this is intentional re-summarize behavior"*; v3 changed the behaviour without saying so. |
| **C-H3** | §8 does not test re-address bytes vs an existing final blob | **FIXED** | §8:357-361, *"Bytes, not pointers."* |
| **C-H4** | No contention test for the new `FOR UPDATE` lock shape | **NOT FIXED** | §5:237-240 argues no deadlock (correctly — re-verified: `persist_summary` takes no `playlists` lock, `0021:104` is a bare `perform 1`), but §8 still mandates **no concurrent-session test**. Codex explicitly said *"I do not see a proven deadlock… Still, §8 should include concurrent `reserve_video_slot` / `claim_video_slot` / `persist_summary` coverage."* That sentence is unaddressed. Carried into **M-R3-4**. |
| **Overload check** | Live probe still warranted before implementation | **FIXED (and re-measured for the right shape)** | G14 (§3:131). Note G14 measured 5-arg + **7**-arg; v3's actual shape is 5-arg + **8**-arg-with-a-default. I re-measured the actual shape — it holds — but see **M-R3-5**. |

### Coordinator round 2

| # | Finding | Status | The v3 text |
|---|---|---|---|
| **C1** | Re-address re-derives the slug from the stale payload → re-orphans the digs the guard just saved | **FIXED for the two races it targets** | §6:253-258 implements the coordinator's exact fix (`baseName := baseOf(observedSummaryMd)`, fallback only when null), §6:321-322 requires extracting the module-private `baseOf` (`reconcile-serial.ts:84-86` — verified), and §8:355 requires the slug-race test to assert the **post-recovery** row and dig reachability. Serial race, slug race and first summary all resolve correctly (re-walked, (B)(2)). **The adoption is unvalidated and changes a third path's behaviour** — **H-R3-1**, **L-R3-1**. |

**Nothing in these tables is a rewording.** Every round-2 Blocking is closed in behaviour. Two of the
three fixes carry new defects, which is the pattern the loop exists to catch.

---

## (B) Attacking v3's new design

### Blocking

#### B-R3-1 — `observedSerial` has no provenance, and the only one that works is a torn read

§6:267 passes `expected := (observedSerial, observedSummaryMd)`. §6:254 documents where
`observedSummaryMd` comes from — *"from PS003's detail, or the `:84` read"*. **Nothing anywhere in
v3 says where `observedSerial` comes from on attempt 1.** There are exactly two candidates, and both
are broken:

**Candidate A — the `:84` read (the only one §6 names).** `readVideo` returns `null` for a video
with no row (`worker-persistence.ts:32-39`), which is the dominant first-time path
(`createdThisRun = !existing`, `summary-handler.ts:93`). So `existing?.serialNumber` is `undefined`.
§4 mandates the `?? null` coercion for `p_expected_summary_md` and **only** for it (§4:159). Two
outcomes, both measured, both after Gemini has been billed:

```
# undefined -> JSON.stringify drops the key -> 6-key body
HTTP 404 {"code":"PGRST202","message":"Could not find the function public.probe_ps(
  p_artifact_status, p_expected_serial, p_owner_id, p_playlist_id, p_video, p_video_id)…"}

# coerced to null -> §4:148-150's explicit raise
errcode 22004  (measured: HTTP 400, {"code":"22004"})
```

And a bare *reserved* row (G2, `0009:95`) is worse: it has `serialNumber` but no `summaryMd`, so
`readVideo`'s unchecked `data.data as Video` cast hands back `serialNumber: 7` — the path *appears*
to work in the case that has a row and fails only in the case that does not. `tsc` cannot see it:
`types/index.ts` declares `serialNumber` non-optional, so the compiler believes `existing.serialNumber`
is a `number` the moment `existing` is non-null. This is H-N1's exact root-cause shape, at the
*other* new parameter, and §4's fix names only one of the two.

**Candidate B — `reserveVideoSlot`'s return (`summary-handler.ts:95`).** This is the only value that
is always a usable number, so it is what an implementer will reach for. But then the expected tuple
is assembled from **two different statements at two different times**:

| Component | Read by | When |
|---|---|---|
| `observedSummaryMd` | `readVideo` (`summary-handler.ts:84`) | t₀ |
| `observedSerial` | `reserve_video_slot` RPC (`:95`) | t₁ > t₀ |

A relocation landing between t₀ and t₁ produces an expected tuple that is **half pre-relocation and
half post-relocation** — a state that never existed. The guard then rejects a write that would have
been legitimate under either consistent snapshot, and the loop burns an attempt recovering. Not
data loss, but it means the "expected address" is never a snapshot, which is the property the whole
predicate assumes.

**Why this is Blocking, not High.** §4:153 says *"Required is not non-null, and required is not
present. **Two distinct traps, both measured**"* — and then applies the lesson to one parameter. The
dominant path (every video summarized for the first time) fails **after** the ~8¢ Gemini charge, and
under Candidate A the failure is `PGRST202`/`22004`, which `worker-runner.ts:76` classifies
**retryable** → `max_attempts` = 5 (G11) → **≈40¢ into `dead_letter` per new video**. That is the
exact cost §5:203-204 was written to prevent, reintroduced by the parameter §5 does not discuss.

**Fix.** §4 must state the provenance of both expected values and coerce both
(`p_expected_serial: expectedSerial ?? null`). If the provenance is `reserveVideoSlot`, §6 must say
so and either (a) accept the torn tuple explicitly with the one-attempt cost named, or (b) re-read
both from one statement — `reserve_video_slot` could return the row's `summaryMd` alongside the
serial, making the tuple a genuine snapshot at no extra round-trip. §8 must add: **a brand-new video
(no row at all) completes through the TS wrapper without a 404 or a 22004.** No test in §8 as
written covers a video with no row — §8:382 covers the `serialNumber`-**absent row**, which is a
different case.

---

#### B-R3-2 — `p_artifact_is_new` disables the defence against the caller it defends against, and `put` makes the result destructive. (Answering §10 OQ1: **no.**)

**The interleaving, with values.** W1 and W2 are two workers on the same job; W2 reclaimed after
W1's lease expired.

| # | Actor | State / action |
|---|---|---|
| 1 | W1 | reads `:84` → `(7, '007_alpha.md')`; Gemini; persist rejected `PS003`, detail `(3, '003_alpha.md')` → sets `isReAddress = true`, `observed := (3,'003_alpha.md')` |
| 2 | W1 | attempt 2, top of loop: `ctx.signal.aborted` is **false** — the heartbeat runs every `leaseSeconds/3` = **40 s** (`worker-runner.ts:52`), so lease loss is detected up to 40 s late |
| 3 | W2 | (reclaimed the job) completes the whole sequence: row = `(3, '003_alpha.md', promoted)`, blob `003_alpha.md` = **W2's fresh bytes** |
| 4 | W1 | `putStaged('003_alpha.md')` with **its own older bytes**; verify staged |
| 5 | W1 | `persistSummary(expected := (3,'003_alpha.md'), 'committed', artifactIsNew := true)` → the address **matches** → guard **passes**. `artifactIsNew = true` suppresses `0021:143-148` → row goes `promoted` → `committed` → serve **503** |
| 6 | W1 | `publish(ref, key)` = **`put`** → **overwrites W2's fresh bytes with W1's older ones** (measured: upsert overwrites) |
| 7 | W1 | `persistSummary(expected := (3,'003_alpha.md'), 'promoted')` → passes. Row: `promoted`, W1's stale scalars, W1's stale bytes. **No error anywhere.** |

**Why the address guard cannot see it:** the address never moved. That is by design — but it is
precisely why the *status* rule existed as the second layer.

**This is a regression against a property the code currently claims.**
`summary-handler.ts:166-170`:

> *"Full lease-fencing of `persist_summary` is deferred — **after FIX 1/FIX 2 a stale write is
> idempotent and non-corrupting**; the double-Gemini charge on reclaim is the known
> AbortSignal-does-not-stop-billing limitation."*

FIX 2 is the key-scoped monotonic rule at `0021:138-148`. Its own comment says it exists to
*"preserve `'promoted'` against a **stale** `'committed'` write."* v3 hands the stale writer a
parameter that turns it off, and pairs it with the one blob primitive that overwrites
unconditionally. Today the same interleaving is non-corrupting: `promote` on Supabase would skip
(destination exists) and the monotonic rule would keep `'promoted'`. Under v3 it destroys paid
output silently.

**Is the caller assertion circular? Yes, demonstrably.** The rule's purpose is to protect against a
caller whose view of the world is stale. `p_artifact_is_new` is that same caller's claim about the
world. The row cannot verify it, and the *only* evidence the caller has is a `PS003` it received
**before** the state it is now asserting about. §6:307-308 says the flag is passed *"true only on a
re-address, where the worker has **just been told** the address moved"* — but "just been told" is
exactly the stale-by-the-time-you-act relationship the guard was built to break. A defence that any
caller can switch off is not a defence against callers.

**Fix — make the discriminator row-verifiable.** The row *can* verify monotonicity of a value the
payload already carries. `processedAt` is written on every persist (`summary-handler.ts:163`, and
`0021:126` puts it in the whitelist), and W1's is strictly older than W2's. Replace the boolean
with:

```sql
-- preserve 'promoted' ONLY when the incoming artifact is not demonstrably newer
when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
 and p_artifact_status = 'committed'
 and <key unchanged>
 and coalesce(p_video->>'processedAt','') <= coalesce(v.data->>'processedAt','')
  then 'promoted'
```

This suppresses the preservation for a genuinely-new artifact (the re-address case v3 wants) and
**keeps** it for a stale one, without trusting a caller assertion. If the spec keeps the boolean, it
must state that a stale worker can now destroy a promoted artifact and that this is an accepted
regression — but §6 currently claims the opposite ("Briefly downgrading a servable A3 copy is the
honest cost"). §8 must gain a test: **two workers, the second completes, the first then runs its
re-address branch → the row and the bytes are the second worker's.**

---

#### B-R3-3 — `publish = put` makes the staged verification meaningless, and no verify-after-write is specified

§6:264 stages and verifies; §6:269 publishes. §6:291-292: *"`put` the verified staged bytes to the
final key (atomic upsert, overwrites on **both** backends), then drop the temp."*

**What `putStaged → verify → promote` had that `putStaged → verify → put` does not.** `promote` is a
**move** — the object whose bytes were verified *becomes* the object at the final key. Under `put`,
the verified object is the temp, and the final key receives a **separate, second upload** from the
worker's in-memory buffer. The verify no longer covers anything that lands at the final key. The
sequence is now: upload (unverified) → download (verify) → upload again (unverified) → the row
advertises `promoted`. The repo already ruled on this exact question — `blob-store.ts:161-162`:

> *"Verify-after-write: an unproven copy is not a copy. The caller is about to advance metadata to
> point at this key and then delete the source, so 'probably written' is not good enough."*

`copyBlob` re-reads and byte-compares (`:163-171`). §6 mandates no such step, on a path that then
stamps `promoted`, which the serve path serves with no further check
(`lib/html-doc/serve-summary-core.ts:47-50`).

**The cited precedent does not verify either.** `sync-run.ts:386-396` hashes the *staged* bytes and
then `put`s them — with no read-back. So §6's *"means what `transferClassA` already does for this
exact reason"* imports the gap along with the mechanism.

**Is `put` atomic on `SupabaseBlobStore`?** Per-object, yes — measured: `AAAA` then upsert `BBBB`,
read-back is `BBBB`, no intermediate observed, HTTP 200 both times. But atomicity is not the
property at risk; **provenance** is. And `put` is the one primitive in this codebase with **no
outcome classification**: `copy` returns a six-way `CopyResult` including `destination-exists`
specifically so *"a destination holding different bytes is `destination-exists`, and the caller
decides"* (`blob-store.ts:42-44`). v3 selects the unclassified overwriting primitive for a
destination that is **guaranteed** to hold a paid artifact (A3's copy), on the money path. That is
what makes B-R3-2 destructive rather than merely confusing.

**The temp object.** §6:317-318 says *"A leaked staging object is inert and swept."* **There is no
sweeper.** `_staging` appears in exactly three places in the tree, all of them `putStaged`
implementations (`supabase-blob-store.ts:85`, `local-blob-store.ts:53`,
`in-memory-blob-store.ts:152`) — no cron, no SQL job, no script, no `deletePrefix('_staging')`
caller. Under `promote` the temp was consumed by the move; under `put` it must be explicitly
deleted, and every crash between the `put` and the delete leaks a **permanent** object. The
recovery loop leaks up to N of them per job. Filed as **H-R3-3** so it is not lost inside this one.

**Fix.** §6 must specify `put` → **re-read and byte-compare the final key** → then delete the temp,
and state that the staged copy exists only as a crash-safety artifact (or drop staging entirely and
`put` + verify once — two round-trips instead of four, with strictly more assurance). §8 must assert
the temp is gone after a successful publish, and that a corrupted final read aborts before the
`'promoted'` persist.

---

### High

#### H-R3-1 — the adopt rule silently changes re-summarize addressing, and contradicts §0/§9's scope

§6:253-258's `if observedSummaryMd is not null` branch is **not** scoped to the recovery path — the
comment says *"from PS003's detail, **or the `:84` read**"*, so it fires on **attempt 1** too. That
means the worker can no longer address a summary by the payload's title. Today
`summary-handler.ts:96` computes `baseName` from `payload.title` unconditionally.

| Case | Today | Under v3 |
|---|---|---|
| Row `(7,'007_alpha.md')`, payload title *"beta"*, no sync | writes `007_beta.md`; `dig/007_alpha/*` orphaned | writes `007_alpha.md`; digs stay coherent |

The new behaviour is arguably *better* (stable addressing, and it is where ADR-0006's manifest is
going). The problem is that v3 **does not know it made this change**, and two sections now say
otherwise:

- §0:60-61 — *"Unguarded, deliberately: a re-summarize that moves the key itself after a title
  change… That is **backlog #20**."* Under the adopt rule the key can no longer move, so the
  behaviour #20 describes is not merely unguarded — it is gone.
- §9:403 — #20 *"No second writer, so nothing to compare against."* Still filed as open.

Codex's round-2 C-B2 flagged exactly this fork (*"That is valid **if this is intentional
re-summarize behavior**"*). v3 resolved it by accident.

**Second-order consequence, unexamined:** the address is now pinned by whatever the row happens to
hold, so a row whose `summaryMd` was written by a **different** convention keeps it forever. The
`raw/…` layout is real and supported (`reconcile-serial.ts:128-131` names
`tests/lib/pdf/pdf-path.test.ts` and `buildDocHtml`), so `baseOf('raw/275_x.md')` = `'raw/275_x'`
and the worker will write `raw/275_x.md` and digs at `dig/raw/275_x/`. Self-consistent, but nothing
in §6 or §8 establishes that it is intended.

**Fix.** State the change: *the worker no longer moves the base; the base moves only via sync (A3)*.
Say what it does to #20 (closes it, narrows it, or is orthogonal). §8 needs a test: **re-summarize
with a changed title writes at the existing base**, which is currently the opposite of the code's
behaviour and would otherwise ship as an unremarked regression against `summary-handler.ts:96`.

#### H-R3-2 — `p_artifact_is_new = NULL` is reachable and fails **open in the destructive direction**

§4:146 declares `p_artifact_is_new boolean default false`. §6 gives no SQL for how it enters
`0021:143-148`. The natural phrasing is `... and not p_artifact_is_new then 'promoted'`. Measured:

```
select (true and 'promoted'='promoted' and not null::boolean);   ->  NULL   (falls to ELSE)
select coalesce(null::boolean,false);                            ->  f
```

A `NULL` flag therefore behaves **exactly like `true`** — it suppresses the preservation. And NULL
is reachable over the wire: PostgREST does **not** substitute the default when the key is present
with a JSON `null` (measured against the live 8-arg function → returned `null`, not `isnew=false`).
So `p_artifact_is_new: someOptionalThing ?? null`, or any `Partial<>` shape that lets `undefined`
become `null` on the way through, silently unlocks the destructive branch.

The safe default must be the *preserving* one. **Fix:** §4 must specify
`coalesce(p_artifact_is_new, false)` in the predicate (or `... is not true`, measured `t`), and §8
must mutation-check it: pass `null` → the promoted status must survive. Same standing shape as
H-N1 — *an optional member that does not propagate* — for the third time in this slice, now at the
parameter introduced to fix round 2.

#### H-R3-3 — §6's *"A leaked staging object is inert and swept"* is false

There is no sweeper anywhere in the repo (evidence in B-R3-3). The claim is load-bearing: it is the
sentence that lets §6 treat the discarded temp on every `PS003` retry as a non-issue. With N = 3 and
`max_attempts` = 5, one pathological video can leak up to 15 permanent staging objects, each holding
a full summary body, in a bucket the user pays for and nothing enumerates. `deletePrefix` exists and
would do the job (`supabase-blob-store.ts:110`), so this is a missing line, not a missing capability
— but the spec asserts the line already exists.

**Fix.** Either specify the sweep (who runs it, on what trigger) or delete the claim and specify
explicit `delete(tempKey)` on every abandonment path, including the `PS003` branch (§6:273 says
*"discard temp"* — make that a `delete`, and say what happens when the delete fails).

#### H-R3-4 — the abort check does not cover the destructive window

§6:251 checks `ctx.signal.aborted` at the **top of each attempt** (H4's fix, correctly restated).
The destructive sequence is `persist('committed')` → `publish` → `persist('promoted')` — three
network round-trips with **no abort check between them**, and step 5-7 of B-R3-2's table is exactly
that span. `summary-handler.ts:170` already places one check immediately before the write sequence
for the same reason (*"Shrink the stale-worker write window"*), and v3's loop moves that check
further away from the write by inserting `putStaged` + verify after it.

**Fix.** Re-check `ctx.signal.aborted` immediately before the `'committed'` persist **and** before
`publish` — the latter is the irreversible one. §8:383 mandates *"abort honoured on **every**
attempt"*; that wording is satisfied by the current spec and would not catch this.

---

### Medium

#### M-R3-1 — two different notions of "the address" in one slice

§5:210 conditions on `v.data->>'summaryMd'` and §6:255 adopts from it. But the two consumers whose
paid content this slice exists to protect resolve the address differently:

```ts
// lib/dig/cloud/resolve-summary-key.ts:14
const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
```

`dig-handler.ts:55` derives its `base` from `resolveSummaryMdKey`, and its comment says the rule
*"guarantees the handler writes the exact base the trigger deduped on."* `persist_summary` writes
both from the same payload (`0021:133` and `:141`), so they normally agree — but the spec never
states that they must, never says which is authoritative, and the guard is built on the one the dig
path does **not** prefer. Per the standing rule *"at fix time, list the consumers"*, this is the
grep that was not run.

**Fix.** One line in §3 (a G-fact) establishing that `data->>'summaryMd'` and
`artifacts.summaryMd.key` are written together by every writer, with the enumeration — or a second
conjunct on the artifacts key. §8 should assert they are equal after every persist.

#### M-R3-2 — §8 still mandates a knob that no longer proves anything

§8:358-359: *"Every re-address test runs with `promoteSemantics: 'create-if-absent'`
(`in-memory-blob-store.ts:52`…) or against real Supabase."* §6 no longer calls `promote` on that
path — it calls `put`. `InMemoryBlobStore.promoteSemantics` gates only `promote`
(`in-memory-blob-store.ts:170-175`), so the test now passes identically with either setting. This is
the *"test double that opts out of real behaviour"* shape inverted: a knob that reads as protection
and provides none. The real protection in §8 is the bytes assertion, which is correct and sufficient.

**Fix.** Replace with: the re-address test asserts `get(<newBase>.md)` equals the new MD **and**
that no `promote` call was made on the re-address path (spy), so a future implementer who reaches
for `promote` goes red.

#### M-R3-3 — the deploy stub is analysed forward only; rollback and the in-flight cost are not stated

§4:172-174 justifies the raising stub by the rolling-deploy window. Two consequences are unstated:

1. **Rollback.** If the release is rolled back to the old image, **every** worker calls the 5-arg
   form and every summary job raises `0A000` → retryable (`worker-runner.ts:76`) → 5 attempts →
   `dead_letter`. The stub converts a rollback from "recover" into "total summary outage until a
   forward migration lands." Standard, but it should be a named operational consequence, not a
   surprise.
2. **Forward cost.** Every job an old worker is *already running* when the migration applies fails
   **after** Gemini is billed. §8's money section bounds the recovery-loop cost but not this one.

**Fix.** One paragraph in §4 naming both, and (for 1) whether the stub should instead log-and-no-op
— which is *not* obviously right and is exactly the kind of decision that belongs in the spec.

#### M-R3-4 — coverage: §4/§5/§6 behaviours with no test in §8

| Behaviour | Specified at | §8 |
|---|---|---|
| A **brand-new video** (no row at `:84`) completes through the wrapper | §6 (implied) | **none** — §8:382 covers a serial-absent *row*, not an absent row (B-R3-1) |
| `p_expected_serial` coerced from `undefined` | §4 (absent) | **none** (B-R3-1) |
| Verify-after-publish; the temp is deleted | §6:291 | **none** (B-R3-3) |
| A stale second worker cannot destroy a promoted artifact | §6:303-309 | **none** (B-R3-2) |
| `p_artifact_is_new = NULL` preserves `'promoted'` | §4:146 | **none** (H-R3-2) |
| Abort between `'committed'` and `publish` | §6 | **none** (H-R3-4) |
| Re-summarize with a changed title writes at the existing base | §6:255 | **none** (H-R3-1) |
| Concurrent `reserve_video_slot` / `claim_video_slot` / `persist_summary` under the new `FOR UPDATE` | §5:237-240 | **none** — Codex r2 #4, unaddressed |
| `data->>'summaryMd'` and `artifacts.summaryMd.key` agree | §5/§6 | **none** (M-R3-1) |

#### M-R3-5 — G14 measured a shape v3 does not specify

G14 (§3:131) reads *"5-key body → 5-arg, 7-key → 7-arg, no PGRST203"*. v3's actual pair is the 5-arg
stub and an **8**-arg function whose last parameter is **defaulted** — and `0021:5-12` documents that
a defaulted parameter is precisely what produced PGRST203 for `update_video_annotations` /
`merge_video_data`. The spec asserts a measurement of a different shape than the one it designs.

I re-measured **v3's actual shape** and it holds:

| Body | Resolves to | Result |
|---|---|---|
| 5 keys | 5-arg stub | `HTTP 400 {"code":"0A000","message":"STUB-5ARG"}` |
| 7 keys (`p_artifact_is_new` omitted) | 8-arg | `HTTP 200 "EIGHT-ARG isnew=false"` |
| 8 keys (`p_artifact_is_new: true`) | 8-arg | `HTTP 200 "EIGHT-ARG isnew=true"` |
| 8 keys (`p_artifact_is_new: null`) | 8-arg | `HTTP 200 null` ← **not** the default (H-R3-2) |
| 6 keys (`p_expected_summary_md` dropped) | — | `HTTP 404 PGRST202` |

**No PGRST203.** The claim is true; only its evidence was for the wrong signature. Update G14 to the
8-arg shape and add the null-vs-default row — it is the measurement H-R3-2 turns on.

---

### Low

- **L-R3-1 — `baseOf` is adopted without validation.** `summaryMd.replace(/\.md$/, '')`
  (`reconcile-serial.ts:84-86`) is total, so a malformed row value silently mints a new address:
  `'007_alpha'` (no extension) → key `'007_alpha.md'`, which **differs from the observed value**, so
  the `'committed'` persist moves the address with the guard passing (expected `'007_alpha'` matches
  the row) — a self-inflicted relocation the guard is structurally unable to see. `''` → key
  `'.md'`, which `assertLogicalKey` accepts. Neither is reachable from any current writer that I
  could find, so this is Low — but the validator already exists and is free:
  `assertCloudSummaryMdKey` (`lib/dig/cloud/resolve-summary-key.ts:16`), which is what the dig path
  runs on the same value. §6 should adopt through it and treat a rejection as `PS002`-class (fatal),
  not as an address to write to. *A key from a different video is not reachable* — both sources
  (`v.data->>'summaryMd'` and `PS003.detail`) are read from this video's row under the row lock.
- **L-R3-2 — G13's path is wrong.** §3:130 and §6:297 cite `serve-summary-core.ts:50`; the file is
  `lib/html-doc/serve-summary-core.ts` (the line and the content are right). §4's `0023:46-48`
  mirror-citation and `0021:154-155`, `0021:142-149`, `0009:95`, `0008:14`, `fly.toml:32-34` all
  check out.
- **L-R3-3 — `detail` arrives as a JSON *string*.** Measured:
  `{"code":"PS003","details":"{\"serialNumber\":3,\"summaryMd\":\"003_a.md\"}","hint":null}` —
  `error.details` is a `string`, not an object. §5:226 says *"the observed address rides in `detail`
  … (JSON, so the worker parses rather than scrapes)"*, which is right, but the caller needs an
  explicit `JSON.parse` **and a defined behaviour when it fails** (a malformed detail must not be
  read as "address unchanged" — that would loop forever re-writing the same stale address). One
  sentence in §5 plus one row in §8.

---

## Verified, not findings

Recorded because a checked-and-clean answer is worth as much as a finding, and because two of these
were open questions.

- **G12 confirmed against LIVE Supabase Storage** — round 2's "could not verify" item 1 is now
  closed. `POST /storage/v1/object/move` onto an existing destination returns
  `{"statusCode":"409","error":"Duplicate"}` (HTTP 400), and the destination is unchanged. Combined
  with `supabase-blob-store.ts:94-97`'s `exists` short-circuit (which deletes the temp and returns
  **void** before `move` is ever attempted), B-N2's premise is established by measurement, not
  inference. `put` with upsert overwrites: `AAAA` → `BBBB`, read-back `BBBB`.
- **§5's named errcodes are valid and usable.** `PS001`/`PS002`/`PS003` are accepted by
  `RAISE … USING errcode =` (SQLSTATE requires 5 chars from `[0-9A-Z]`; class `PS` is unassigned by
  PostgreSQL, so there is no collision). All three surface through PostgREST as
  `{"code":"PS001",…}` with **HTTP 400**, identical to `P0001`, `22004` and `0A000` — no 500, no
  swallowed code. §5's *"the contract is the code, not the message"* is implementable exactly as
  written. Only the `details`-is-a-string detail (L-R3-3) needs adding.
- **§6's expected-key transition is correct on every path I could construct.** I enumerated all six
  the brief names plus two more; the guard passes exactly when it should:

  | Path | attempt-1 expected | payload key | committed | promoted expected | Outcome |
  |---|---|---|---|---|---|
  | Bare row, first summary | `(7, NULL)` | `007_alpha.md` | passes (`NULL is not distinct from NULL`) | `(7,'007_alpha.md')` | ✅ one pass, no loop |
  | Re-summarize, same title | `(7,'007_alpha.md')` | `007_alpha.md` | passes | `(7,'007_alpha.md')` | ✅ |
  | Re-summarize, changed title | `(7,'007_alpha.md')` | `007_alpha.md` (adopted) | passes | same | ✅ guard-wise — **behaviour change, H-R3-1** |
  | Re-address after serial race | `(3,'003_alpha.md')` | `003_alpha.md` | passes | same | ✅ digs at `dig/003_alpha/` reachable |
  | Re-address after slug race | `(7,'007_beta.md')` | `007_beta.md` | passes | same | ✅ C1 closed |
  | **Retry of a job that already wrote `'committed'` then crashed** | `(7,'007_alpha.md')` — the row now **holds** the key attempt 1 wrote | `007_alpha.md` | passes | same | ✅ — the adopt rule is what makes this work; a payload-derived base would also work here, but only because the title is unchanged |
  | Crash between `'committed'` and `publish` | — | — | — | — | ✅ row = `committed` → serve **503** → retry repairs. This is H-N3's argument and it holds. |
  | Crash between `publish` and `'promoted'` | — | — | — | — | row = `committed` (503), blob = new bytes; retry re-runs Gemini (~8¢) and re-publishes. Visible, non-serving, costs money — §8:392 names it as uncovered. Honest. |

- **The `observedSummaryMd is null` branch cannot race.** `reconcileCloudBase` returns `agreed`
  immediately when `!cloudVideo.summaryMd` (`reconcile-serial.ts:180`), and `describeDivergence`
  does the same (`:150`). So A3 can never relocate a row that has no `summaryMd` — which means the
  fallback base derivation (`pad(serial) + '_' + slug(title)`) is only ever reached in a state where
  there is nothing to adopt and no concurrent mover. I tried to construct a race against it and
  could not. §6 should record this as the *reason* the fallback is safe; it currently reads as an
  assumption.
- **G5 holds.** `summary-core.ts:60-61` — *"`baseName` is accepted in the input shape … but is not
  needed to build the markdown content itself, so it is intentionally not destructured here."* The
  only two references to `baseName` in the file are the type declaration (`:19`) and that comment.
  So re-addressing genuinely does not invalidate the generated bytes, and §6's "one blob round-trip
  versus ~8¢" premise is sound.
- **G7 = 18, exactly.** `grep -rn "p_artifact_status" --include=*.ts` (excluding `node_modules`) →
  18 lines.
- **No deadlock from the new `FOR UPDATE`** — re-derived independently for the third time.
  `persist_summary` takes a `videos` row lock and **no** `playlists` lock (`0021:104` is a bare
  `perform 1 from playlists`), while `reserve_video_slot:84` and `claim_video_slot:50-52` take
  `playlists` first. No transaction acquires `videos → playlists`, so there is no cycle. (A
  concurrency *test* is still missing — M-R3-4.)
- **Backlog #19/#20/#21 exist with the titles §9 gives them** — `docs/backlog.md:26`
  (`transferClassA` content race), `:27` (title change orphans every dig blob), `:28` (dig writes,
  different sink). §9's cross-references are accurate.

---

## What I could not verify, and why

1. **That the two-worker interleaving in B-R3-2 occurs in production.** I established every
   mechanism it needs — the 40 s heartbeat (`worker-runner.ts:52`), lease reclaim after 120 s,
   `sweepExpired` at `runOnce`'s first line, and the absence of an abort check inside the write
   sequence. I did not run two workers against one job to observe it. The finding does not depend on
   frequency: the monotonic rule exists *because* the interleaving is considered reachable
   (`summary-handler.ts:166-170` says so in as many words), so removing the defence is a regression
   whether or not it fires this week.
2. **Whether a row can hold `artifacts.summaryMd.key` while `data->>'summaryMd'` is NULL**
   (M-R3-1). Every writer I traced sets both from one value. I did not exhaustively enumerate every
   `merge_video_data` caller's patch shape, so I graded it Medium rather than High.
3. **Wall-clock cost of a re-address attempt against the 120 s lease.** Structural argument only —
   same limitation as rounds 1 and 2. §8:393 names it as uncovered, which is the honest disposition.
4. **Whether `processedAt` is monotonic enough to serve as B-R3-2's discriminator in every case.** It
   is set from `new Date().toISOString()` on the worker (`summary-handler.ts:163`), so it is subject
   to clock skew between machines. On a single Fly app this is minutes-safe, not milliseconds-safe.
   It is the best row-verifiable candidate I found; the spec should adjudicate it rather than adopt
   it on my say-so.
5. **`scripts/check-docs.py`** — §11 claims passing. I did not re-run it.

---

## Standing root-cause shapes — hits this round

| Shape | Where it recurred in **v3's own fixes** |
|---|---|
| *an optional member that does not propagate* | **B-R3-1** (`p_expected_serial` — the coercion §4 wrote for its sibling); **H-R3-2** (`NULL` boolean falls to the destructive branch). Third and fourth occurrence in this slice. |
| *a guard with no covering test* | **B-R3-2** (no two-worker test); **H-R3-2** (no null-flag mutation); **M-R3-2** (a knob that now proves nothing) |
| *a test double that opts out of real behaviour* | **M-R3-2**, inverted — the knob §8 mandates no longer gates the code path under test |
| *absent-vs-failed conflation* | **L-R3-3** — a `detail` that fails to parse must not be read as "address unchanged" |
| *a value read in one process and written in another* | **B-R3-2** — W1's expected address is a fact W2 has since replaced, and `p_artifact_is_new` is W1's assertion about it |
| *a claim asserted rather than checked* | **H-R3-3** — *"inert and swept"*, with no sweeper in the tree |
| **new: *a defence a caller can disable is not a defence*** | **B-R3-2** — the parameter that suppresses the monotonic rule is supplied by the caller the rule defends against |

**Round-4 shape to carry, unchanged from round 3:** *the guard is easy; what the caller does with a
rejection is where this slice keeps breaking.* Nine Blockings across three rounds, **zero in the
predicate**.
