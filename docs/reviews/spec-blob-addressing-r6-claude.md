# Adversarial review — ROUND 6 (Claude) — stable blob addressing

Method: executed `schema/{01,03,04,05}.sql` against the live Postgres
(`supabase_db_youtube-playlist-summaries-cloud`) inside `begin … rollback`, from a **copy** in a
scratch directory; 24 hand-written probes; a 38-mutation harness classifying INVALID / RED / GREEN.
Everything marked **MEASURED** was run; the quoted text is real output.

Baseline: `verify-schema.sh` passes (`ASSERTIONS_OK` / `ALL_STATEMENTS_OK`). That is the problem with
six of its assertions — see B2.

**Verdict on the round-5 claim "every guard added in round 5 was mutation-checked and came back RED":
FALSE.** Measured GREEN: `gen_card_complete` (round 5 B1, Blocking), `gen_major_matches_card`
(round 5 H5), `gen_summary_has_format`, `security_invoker` on `video_summary_current` (round 5 B2),
both new client policies on `video_generations` / `workspace_videos` (round 5 B2), the
`source_generation_id` FK (round 5 Codex M5), and **every rung of both view orderings** — including
`(g.card ->> 'mdGeneratedAt')`, the headline of round 5 B3.

---

## BLOCKING

### B1 — `reclaim_expired_reservation` is an unauthenticated cross-tenant write

`04_artifacts.sql:111-120` creates a `security definer` function taking `p_ws uuid` as a *parameter*,
with **no authorization check of any kind**, and never revokes the default `PUBLIC EXECUTE`.

MEASURED:

```
P18b  reclaim_expired_reservation | prosecdef=t | acl = <default: PUBLIC EXECUTE>
P18   anon called reclaim on tenant-1 slot -> returned 0, rows 1 -> 0   <-- CROSS-TENANT WRITE
```

`anon` — no JWT at all — deleted another workspace's in-flight reservation. `security definer` means
RLS is not consulted; the grant is the whole authorization story, and there isn't one. Round 5 B2 was
the *read* half of exactly this shape (identity as grant, #2); the round-5 H4 fix reintroduced it on
the **write** path, in the same batch. That is shape #9's eighth instance and shape #10's sixth: this
repo revokes `PUBLIC` on **every other** `security definer` function it ships —
`0004_test_exec_sql.sql:10`, `0005_reorder_helper.sql:25`, `0010_cancel_job_rowcount.sql:21`,
`0011_cost_guardrails.sql:137` — and the sibling one file away was not swept.

Failure scenario: an unauthenticated attacker loops `reclaim_expired_reservation(ws, video, slot)`
over guessed slots and deletes every expired reservation in the system; combined with H5 this resets
the attempt bound, so a poison slot retries forever, each retry a paid Gemini call.

**Change:** `revoke all on function reclaim_expired_reservation(uuid,text,text) from public, anon,
authenticated; grant execute … to service_role;` — and add an assertion that `anon` calling it raises
`42501`. The privilege sweep must cover `slot_kind` too (harmless but also `PUBLIC`).

### B2 — six of the seven `video_generations` negatives are rejected by a SQL arity error, not by the constraint they name

`05_assert.sql:15-19`'s `assert_raises` catches `when others`, so **any** error counts as "the guard
bit". Six negatives have more target columns than value expressions and never reach the table.

MEASURED (`show_err` printing the real SQLSTATE each `assert_raises` swallowed):

```
gB1 card-incomplete          : [42601] INSERT has more target columns than expressions
gB2 null-card                : [42601] INSERT has more target columns than expressions
gB3 json-nulls (round5 B1)   : [42601] INSERT has more target columns than expressions
gB6 one-null                 : [42601] INSERT has more target columns than expressions
gB4 no-major                 : [42601] INSERT has more target columns than expressions
gB5 major-99 (round5 H5)     : [42601] INSERT has more target columns than expressions
gB7 no-md_hash (round5 B3)   : [23514] … violates check constraint "gen_summary_has_hash"   <- the only real one
```

`05_assert.sql:114-116`, `118-120`, `122-126`, `129-133`, `137-141`, `145-149` each name eight columns
(or seven at gB2) and supply one fewer value — `md_hash` was added to the column list in round 5 and
no value was added beside it.

Corroborated independently by mutation: deleting `gen_card_complete`, `gen_summary_has_format` and
`gen_major_matches_card` from a copy of the schema leaves the suite **GREEN**.

The constraints themselves are correct — MEASURED with the arity repaired:

```
gC5 major-99   ARITY-FIXED : [23514] violates check constraint "gen_major_matches_card"
gC3 json-nulls ARITY-FIXED : [23514] violates check constraint "gen_card_complete"
gC4 no-major   ARITY-FIXED : [23514] violates check constraint "gen_summary_has_format"
```

So round 5's Blocking B1 (the all-null card that *won the ranking*) and High H5 are shipping
unverified, in the file whose header (`05_assert.sql:4-13`) states "EVERY NEGATIVE BELOW MUST VIOLATE
EXACTLY ONE GUARD". Round 5 H1's masking defect was not removed; it was *deepened* — a fixture that
does not parse against the table tests strictly less than one that violates two guards.

**Change:** (a) add the missing seventh/eighth value to all six inserts; (b) make `assert_raises` take
an expected `sqlstate`/constraint name and re-raise on anything else — this class of failure is
undetectable while the harness accepts `when others`.

### B3 — append-only is defeated in two permitted statements, via `detached`

`video_artifacts_append_only()` (`04_artifacts.sql:271`) gates its entire body on
`old.state = 'recorded'`. A `detached` row is therefore completely unprotected — and
`recorded → detached` is the one transition the round-5 rewrite deliberately permits
(`04_artifacts.sql:282`).

MEASURED:

```
P1   DELETE of a DETACHED paid row SUCCEEDED, rows left = 0                              <-- BYPASS
P1b  detach -> update blob_key -> re-record: blob_key=W/videos/vidA/gOLD/HIJACKED.md,
     state=recorded                                                                       <-- BYPASS
```

P1 is the serial-coherence orphaning defect (PR #42) reachable in two statements. P1b is shape #3 —
a mutable value in an address — reachable in three, in the trigger written to make it impossible.
The design also never restricts `detached` to `kind='dig'`, so a **summary** can be detached, which
is what makes P1b and H1 reachable on the money path rather than only on digs.

**Change:** gate on `old.state in ('recorded','detached')`, and permit `detached → recorded` only if
the address is unchanged; add `constraint art_detached_is_dig check (state <> 'detached' or kind =
'dig')` if §6.2's detach is genuinely dig-only. Assert both directions.

### B4 — rung 1 (corrections-currency) diverges between the view and `reconcileClassA`, for the entire corpus

Two independent causes, both measured.

**(a) `workspace_videos.corrections_hash` is never backfilled.** `03_generations.sql:28-29` seeds the
table with `select distinct workspace_id, video_id from videos` — `corrections` and `corrections_hash`
are left NULL for every migrated video, while the real values live in `videos.data`.

MEASURED against the live corpus:

```
workspace_videos after 01+03 : 2903 of 2904 rows have corrections_hash IS NULL
videos (live)                : 99 rows carry a non-empty corrections, 261 carry an mdCorrectionsHash
```

99 users' corrections are dropped by the migration, and rung 1 —
`(g.card->>'mdCorrectionsHash' is not distinct from wv.corrections_hash)`, the **top** rung of both
view orderings (`04_artifacts.sql:173`, `:209`) — reads the column that is now NULL everywhere.

**(b) the two sides disagree about how "no corrections" is spelled.** `pipeline.ts:272` stamps
`mdCorrectionsHash: mdHash('')` — a real 64-hex string, never null — and `reconcileClassA`'s
`cur = mdHash(String(merges.corrections.value ?? ''))` (`sync-run.ts:651`) is likewise `mdHash('')`.
The `gen_card_complete` note at `03_generations.sql:72-76` argues the card's `mdCorrectionsHash` must
be allowed to be JSON *null* because "a null there is the correct, meaningful answer for a video with
no corrections". Against the merged producer that premise is false.

MEASURED with the producer's real value and the migration's real state:

```
P15  view_says_corrections_current = f
     reconcileClassA: mdCorrectionsHash === mdHash('') -> TRUE
```

This is precisely the drift §5.3 asserts has been eliminated — *"the views now order by the same
three rungs on the same values"* (line ~1418). Round 5 B3 fixed rung 3 (`produced_at` →
`card->>'mdGeneratedAt'`) and did not sweep to rung 1, one line above it. Shape #10.

Consequence on the money path: with cloud permanently rung-1-stale and local current,
`reconcile-class-a.ts:39` returns `copyToCloud` on every run, so **every sync appends a new
generation, forever** — verbatim the failure round 5 B3 was written to remove.

**Change:** backfill `workspace_videos.corrections{,_hash}` from `videos.data` in `03`; make the
representation of "no corrections" identical on both sides (either `mdHash('')` everywhere, or a
documented NULL on both, with `is not distinct from` matching whichever is chosen); route
`update_video_annotations` (0021) at `workspace_videos` or keep the two in sync by trigger. Add an
assertion that a `mdHash('')` card and an uncorrected video rank as corrections-current.

### B5 — `md_hash` has no producer, and §10.0 — the section that exists to prevent exactly this — does not mention it

`gen_summary_has_hash` (`03_generations.sql:91`) makes `md_hash` mandatory for every summary
generation. Grepping the spec for `md_hash` returns **three** hits, all inside §5.3 (lines 1389, 1403,
1416). §10.0 *Ordering — the producer fix lands BEFORE or WITH the card constraint, never after*
(line 1867+) enumerates only the `gen_card_complete` fields and names one producer,
`summary-handler.ts:149-164`.

So the newest mandatory column is not covered by the ordering rule, and its stated failure mode is
verbatim: *"every cloud summarize job fails its insert — **after** the Gemini call has been made and
paid for."*

The producer *can* exist — `core.mdContent` is in scope at `summary-handler.ts:172` and
`lib/cloud-sync/content-hash.ts:16` exports `mdHash()` — so the fix is a mechanism rather than a
promise, but nothing currently computes it and nothing in the document says who must. There are also
**three** summary producers (`lib/job-queue/summary-handler.ts`, `lib/cloud-sync/sync-run.ts`,
`lib/storage/worker-persistence.ts`), and the sync one is precisely the producer §5.3 now requires to
write `md_hash`.

**Change:** add `md_hash` to §10.0's table and to the producer task; name all three producers; state
that `md_hash = mdHash(canonicalizeMd(body))` using the existing helper so the two replicas hash the
same string.

---

## HIGH

### H1 — the round-5 H3 GC floor is defeated by the transition the round-5 M1 trigger was rewritten to permit

MEASURED:

```
P10  detach gNEW's summary artifact -> collect gNEW -> re-record it
     summary slot now has 0 current rows
P9   collecting gDIG SUCCEEDED while its dig:120 row is DETACHED
```

`forbid_collecting_current()` (`04_artifacts.sql:226-238`) asks only whether the generation is
*current*, and `video_artifacts_current` filters `a.state = 'recorded'` — so detaching an artifact
makes its generation collectable, and the floor guarantee ("cannot empty a non-empty set") is false
again, by a different route than round 5 measured. P9 is the same hole aimed at §6.2's promise that a
detached dig "is never deleted": a detached dig is by construction never current, so GC may collect
its generation's body — collecting exactly the paid content §6.2 exists to preserve.

**Change:** the guard must be "is this generation referenced by any **non-collected** artifact row in
any state other than a dead pending", not "is it current". Assert both P9 and P10 as negatives.

### H2 — `art_key_names_generation` is a LIKE pattern, so a generation id is a pattern, not a literal

`04_artifacts.sql:76-77`: `blob_key like '%/' || generation_id || '/%'`.

MEASURED:

```
P3   generation "g_LD" ACCEPTED blob_key 'W/videos/vidA/gOLD/dig/55.md'      <-- BYPASS  (_ wildcard)
P3b  generation "%"    ACCEPTED blob_key 'W/videos/vidA/ANYTHING/dig/56.md'  <-- BYPASS  (% wildcard)
P3c  generation "gDIG" ACCEPTED 'OTHERWS/videos/gDIG/gOLD/dig/57.md'         <-- BYPASS  (wrong segment)
```

§4.1 (*What is a `generationId`?*) is explicitly **OPEN**, and two of its three candidates
("timestamp + random", "content hash") can plausibly contain `_`. P3 is shape #4 — a row ranking one
generation's card while serving another's bytes — surviving the constraint added to stop it. P3c
shows the pattern does not constrain *position*: the id may appear as the video segment while a
different generation occupies the generation segment.

**Change:** `strpos(blob_key, '/' || generation_id || '/') > 0` removes the metacharacter problem;
anchoring the whole shape (`blob_key like workspace_id || '/videos/' || video_id || '/' ||
generation_id || '/%'`) removes the position problem too. Add negatives for `_`, `%` and a
wrong-position key.

### H3 — the security controls round 5 added are, with one exception, untested

Mutation results (INVALID / RED / GREEN harness, run against a copy):

```
RED    security_invoker on video_artifacts_current
GREEN  security_invoker on video_summary_current            <-- UNTESTED
RED    policy video_artifacts_owner_read
GREEN  policy video_generations_owner_read                  <-- UNTESTED
GREEN  policy workspace_videos_owner_read                   <-- UNTESTED
```

`05_assert.sql:312-323` reads only `video_artifacts` and `video_artifacts_current` as the second
tenant. `video_summary_current` — the other view, the one the serve path resolves the summary from —
is never read cross-tenant, and neither is `video_generations` or `workspace_videos` directly. Round 5
B2's finding was that a view without `security_invoker` leaks two tenants' `blob_key`s; the fix landed
on both views and is asserted on one. Shape #6, and shape #10 again.

The controls are currently *correct* — MEASURED with them in place, tenant 2 sees
`video_summary_current=0, video_generations=0, workspace_videos=0`, and `anon` sees 0 through both
views. The defect is that nothing would notice if one were dropped.

**Change:** extend the cross-tenant block to read all three tables and both views, and add an `anon`
block (currently `anon` holds `SELECT` with **no policy**, which is the correct deny-all but is also
untested).

### H4 — `anon` can TRUNCATE the paid manifest; TRUNCATE sees neither RLS nor the append-only trigger

MEASURED:

```
P20  video_artifacts | anon          | REFERENCES,SELECT,TRIGGER,TRUNCATE
     video_artifacts | authenticated | REFERENCES,SELECT,TRIGGER,TRUNCATE
     (identical for video_generations, workspace_videos, workspaces and both views)
P21  anon TRUNCATEd video_artifacts -> 0 rows remain      <-- TOTAL PAID-MANIFEST LOSS
```

Source: `pg_default_acl` carries `postgres | r | {…, anon=Dxtm/postgres, authenticated=Dxtm/postgres}`
— `D`=TRUNCATE, `x`=REFERENCES, `t`=TRIGGER. Every table `postgres` creates in `public` inherits it.
The design's explicit `grant select on … to authenticated, anon` lines are *additive*; they do not
narrow what the default already gave, so `04_artifacts.sql:127-130`'s claim — *"The client-readable
surface is stated explicitly, SELECT only, with writes still service_role-only through an RPC"* — is
measurably false.

Honest scoping: this is a pre-existing repo-wide condition, not created by this design. It is Blocking-
adjacent *here* specifically because this is the first design whose central invariant is enforced by a
**row** trigger, and TRUNCATE fires only statement-level `TRUNCATE` triggers. The repo already knows
the pattern — `0011_cost_guardrails.sql:56` explicitly revokes.

**Change:** `revoke all on <each new table> from anon, authenticated;` before the intended
`grant select`. Assert that `anon` truncating raises `42501`.

### H5 — the reclaim loses the attempt bound, cannot distinguish absent from zero, and does not stop the reclaimed writer from paying

Three measured defects in one 10-line function (`04_artifacts.sql:111-120`).

```
P2   reclaim(slot that never existed) = 0    reclaim(row with lease_attempts=0) = 0
     -- indistinguishable
P22  W1 reserves dig:600 -> lease expires -> W2 reclaims and reserves -> W1 records anyway:
     slot dig:600 now has 2 rows (1 pending + 1 recorded) -- TWO paid Gemini calls
```

1. **Absent vs zero (shape #1, on the money path).** `return coalesce(v_attempts, 0)` collapses "there
   was nothing to reclaim" into "I reclaimed a row that had never been attempted". The comment says the
   caller *"carries this into the next reservation and gives up past a terminal bound"* — so the two
   cases must be distinguished and cannot be.
2. **The bound is resettable under concurrency.** Reclaim and reserve are two round trips with no
   atomicity between them. W1 reclaims (gets 2) and W2 reclaims (gets 0, deletes nothing); whichever
   inserts first sets the count. If W2 wins, the count goes 2 → 1 and a poison slot never terminates —
   unbounded paid retries. The unique index makes the *loser* fail; it does not make the *count* survive.
3. **Reclaim does not fence the reclaimed writer.** P22: the money guard is "at most one in-flight
   reservation per slot", but `video_artifacts_inflight_uq` is `where state = 'pending'` only, so the
   original writer — whose row was deleted while it was inside its Gemini call — can INSERT a
   `recorded` row for its own generation and land beside the new reservation. Two paid completions per
   slot, which is the failure the index exists to prevent, arriving through the reclaim added to make
   the index safe. This is the *known* worker-vs-sync fencing gap (backlog #17) reappearing in the new
   design.

Related, Medium: the DELETE also removes a record whose bytes may already exist (record-first order),
which violates rule 19's `bytes ⊆ records` and leaves permanent "unknown key, report never delete"
noise for §4.0's sweeper.

**Change:** return `{reclaimed boolean, attempts int}` rather than a bare int; make reclaim-and-reserve
**one** function so the count is carried atomically; fence the reclaimed writer with a `lease_token`
the record-flip must match (an `update … where lease_token = $1` returning 0 rows is how the writer
learns it lost, and there is currently no way for it to learn).

---

## MEDIUM

- **M1 — every ranking rung is mutation-GREEN.** Removing the corrections rung, the
  `doc_version_major` rung, the `(g.card ->> 'mdGeneratedAt')` rung, or the summary view's
  `not g.body_collected` filter all leave the suite green. The fixture (`05_assert.sql:33-40`) makes
  gNEW win on *every* rung simultaneously, so the rungs mask each other. Round 5 B3's headline change —
  ranking the card's `mdGeneratedAt` instead of `produced_at` — has **zero** coverage because gOLD/gNEW
  have `produced_at` and `mdGeneratedAt` in the same order. Fix: one fixture pair per rung, in which
  only that rung discriminates and the lower rungs point the other way.
- **M2 — §5.3's projection is not obtainable from the view it names.** MEASURED, the columns of
  `video_summary_current` are `workspace_id, video_id, slot, generation_id, kind, state, blob_key,
  source_generation_id, start_sec, end_sec, lease_expires_at, lease_attempts, updated_at, artifact_id`
  — no `card`, no `doc_version_major`, no `md_hash`. Four of the six `ClassASignals` fields are not
  there. "Project `current` down to a `ClassASignals` — one row, one tuple, six fields" needs a join to
  `video_generations`; say so, or add the columns to the view. (The other two fields check out:
  `summaryMdKey` is written at `backfill.ts:10` and read nowhere, and `ClassASignals.backfilled` is
  read nowhere — `reconcile-class-b.ts:43` reads `FieldState.backfilled`, a different type — so
  projecting them as `blob_key` and `false` is genuinely safe.)
- **M3 — `slot='html'` cannot represent the two HTML renders that already exist.**
  `app/api/html/[id]/route.ts:32` serves `type=summary` **and** `type=dig-deeper`. MEASURED:
  `P24 the dig-deeper HTML render is UNREPRESENTABLE: [23505] duplicate key … "video_artifacts_free_uq"`.
  Round 5 L3 anchored `p_slot = 'html'` (`04_artifacts.sql:17`) rather than parameterising it as
  `html:<kind>` beside the already-parameterised `pdf:%`, so the fix hardened the wrong shape. §4.0's
  table has the same asymmetry (`slot='html'` vs `slot='pdf:<kind>'`) for a key template that carries
  `<name>` in both rows.
- **M4 — the `source_generation_id` FK negative is masked.** `05_assert.sql:201-204` uses
  `generation_id='gDIG', kind='digDeeper'`; MEASURED, it is rejected by
  `[23503] video_artifacts_workspace_id_video_id_generation_id_kind_fkey`, not by the source FK.
  Mutation confirms: removing the source FK leaves the suite green. Round 5 H1's own shape, third
  instance in this file.
- **M5 — `forbid_collecting_current` is `before update` only, and one-directional.** MEASURED:
  inserting a generation with `body_collected = true` succeeds (P6b), and `true → false` succeeds
  (P23), the latter producing a row claiming bytes GC has deleted — shape #4. Add `before insert or
  update`, and forbid un-collecting.
- **M6 — §10.0 names one producer of three.** `lib/cloud-sync/sync-run.ts` and
  `lib/storage/worker-persistence.ts` also write summary rows; sync-run is the one §5.3 now requires to
  emit `md_hash`.
- **M7 — nothing ties `md_hash` to the bytes.** Round 5 H5 added `gen_major_matches_card` because "the
  ranking trusts `doc_version_major`, and nothing tied it to the `docVersion` the body actually
  carries". `md_hash` is now trusted by `reconcile-class-a.ts:32` for a *skip* decision and has exactly
  the same property, with the aggravation that a CHECK cannot read a blob. State who verifies it (the
  writer that just wrote the bytes, at record time, per §5.1.1) and that a mismatch is a fault, not a
  copy.

## LOW

- **L1 — the append-only DELETE branch is masked by the address branch.** Mutation:
  neutering `if tg_op = 'DELETE'` leaves the suite green, because on a `before delete` row trigger
  `new` is NULL and `new.slot is distinct from old.slot` fires the *address* exception instead. The
  DELETE negative (`05_assert.sql:253`) is therefore satisfied by two guards; per the file's own rule
  it tests neither.
- **L2 — the state whitelist (`recorded → pending`) has no assertion.** Mutation GREEN.
- **L3 — round 3 B-6's cross-tenant guard has no assertion.** Mutation GREEN for both
  `jobs_workspace_owner_fk` (`01_workspaces.sql:50-51`) and `workspaces unique (id, owner_id)`
  (`:16`). Nothing in `05_assert.sql` inserts a job whose `(workspace_id, owner_id)` pair crosses
  tenants.
- **L4 — the "ISO-8601 compares lexicographically" comment is collation-dependent.**
  `04_artifacts.sql:178` claims the view's `(g.card ->> 'mdGeneratedAt') desc` is "exactly what
  `reconcile-class-a.ts`'s `newer()` does". MEASURED, this DB is `en_US.UTF-8`, where `'T' > 'a'` is
  **true** and in JS it is **false**. I could not reach the divergence with well-formed ISO-8601 —
  offset-vs-`Z`, milliseconds, space-vs-`T` and digit-vs-alpha all agree between the two — so this is
  Low, not High. But the property the comment asserts is a property of `collate "C"`, not of text. Add
  `collate "C"` to both rungs and the claim becomes true by construction.
- **L5 — `assert_raises` cannot fail for the right reason.** `05_assert.sql:17`'s `when others` is what
  made B2, M4 and L1 invisible. It should take the expected SQLSTATE (and, for `23514`, the constraint
  name) and re-raise anything else.

---

## JOB 3 — the invariants

- **Rule 14's floor (`state='recorded'` and `not body_collected`, plus the trigger) — still false.**
  H1 measured it emptied to 0 rows by three permitted statements. The trigger tests *currency*, which
  is not the property the floor needs; the property is *"is anything still pointing at these bytes"*.
- **Rule 19's determinacy (`bytes ⊆ records`) — now violated by the reclaim itself.** The DELETE at
  `04_artifacts.sql:115-118` removes a record whose bytes the record-first order may already have
  written. The `busy` branch is reachable but not *exitable* as a branch: a second writer gets raw
  SQLSTATE `23505` from `video_artifacts_inflight_uq`, which aborts its transaction — shape #8, a
  policy that errors rather than denies. There is no `reserve_artifact_slot` RPC anywhere in the
  schema, so every caller must parse a constraint name out of an error to tell "busy" from "broken".
- **Append-only scoped to the address of recorded paid rows — the right invariant, wrongly fenced.**
  B3 shows the scope is `old.state = 'recorded'` when it needed to be "paid rows in any terminal
  state". H4 shows the enforcement mechanism (a row trigger) cannot see the privilege the database
  hands `anon` by default. Both are the *fence*, not the invariant; the invariant is sound.

---

## VERDICT

**NOT CONVERGED** — 5 Blocking, 5 High.
