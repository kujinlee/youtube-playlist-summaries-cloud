# Round 8 — Claude adversarial review — stable blob addressing

Independent of the parallel Codex run. Everything below was executed against the live local
Postgres (`supabase_db_youtube-playlist-summaries-cloud`) inside `begin; … rollback;`, using a
pristine copy of the schema taken from `git show HEAD:` (commit `0b27094`, working tree clean).
Verbatim error text is quoted; where I could not measure, I say so.

**Verdict: NOT CONVERGED.** 3 Blocking, 5 High, 6 Medium, 2 Low.

---

## 0. Your three claims

| Claim | Verdict |
|---|---|
| 103 assertions pass | ✅ **true** — `grep -c '^NOTICE:  ok'` on gate 1's output = **103**, gate 1 exits 0 |
| 44/44 mutations behave | ⚠️ **true only in isolation** — see **M4**. In the repo the gate reported **23/44 and FAILED**; in an isolated copy, 44/44. The gate is not safe to run concurrently and said so in a way that looks like a real regression |
| 32 guards classified, 28 SHAPE / 4 SEQUENCE | ✅ **true** as counts — but the labels are not all right (**M3**), and the ratchet's obligations are satisfiable without being true (**M1**) |

Four things I set out to break and could **not** — recorded because a failed attack is evidence too:

- **The round-7 H3 delete is safe.** To reach it `v_made_generation` must be true, which means this
  transaction created the generation moments earlier; no other transaction can hold an FK to an
  uncommitted row, so the `delete … where state='pending'` cannot remove a row anything depends on.
- **`art_key_names_generation` has no mutation entry, but it is assertion-covered.** I replaced it
  with `check (true)` and ran the full suite: `ASSERTION FAILED — should have been rejected: a row
  ranking wB's card while serving gOLD's BYTES (shape #4 on the paid path)`.
- **The `t_writes` coverage instrument is not trivially satisfied.** I suspected the `after insert
  **or update**` trigger let a pending→recorded state flip count as "the same slot written twice".
  It does not: narrowing the trigger to `after insert` keeps the coverage assertion green, so every
  kind genuinely gets two distinct INSERTs.
- **The free branch cannot smuggle a change to a paid row.** A paid `p_kind` with a null generation
  and a free kind *with* a generation are both rejected by `art_paid_has_generation`, and no paid
  and free row can ever share a slot because `kind` is a function of `slot`.

---

# JOB 1 — the round-7 fixes and the classification pass

## BLOCKING B1 — `video_generations_collectable` admits IN-FLIGHT generations; GC collects a paid summary while it is being paid for

`04_artifacts.sql:730-736`. The view's entire predicate is *"not collected"* and *"not current"*.
A generation that `reserve_artifact_slot` created seconds ago — `state='pending'`, Gemini call in
progress, money already committed — satisfies both, because a pending generation is not current and
never will be until the worker returns.

MEASURED, following exactly the sweeper protocol the round-8 C3 comment prescribes
("the currency test becomes something the sweeper SELECTS THROUGH"):

```
A1. reserve outcome = reserved (a PAID summary is now in flight)
A2. gINFLIGHT in video_generations_collectable = 1 row(s)   <-- in flight, money being spent
A3. sweeper (selecting THROUGH the view, as C3 prescribes) set body_collected = t
A4. the worker paid and RECORDED: recorded artifact rows = 1
A5. generation state = complete , body_collected = t
A6. >>> rows served from video_summary_current = 0  <<<
A7. >>> rows in video_artifacts_current = 0  <<<
```

The worker completed normally. `record_artifact` returned success. The artifact is `recorded`, the
generation is `complete`, and **the user is served nothing** — both views filter
`not g.body_collected`, and `body_collected` is not frozen by anything, so nothing ever puts it back.

This is round 5's H3 and round 3's A-2 (*"the summary vanishes from the page"*) reached through the
fix written to close H3. Shape #9, instance ten: round 8's C3 moved the currency test out of the
trigger and into a view, and the view lost the only condition that made the trigger's *timing* safe —
the trigger fired at the moment of collection, when the generation's state was knowable; the view
answers a question about a generation that has not happened yet.

`forbid_collecting_current` cannot save it: gINFLIGHT is not current, so the backstop is silent.

**The §8 age predicate is not a defence, and this is why leaving it out is not defensible.** The
comment at `04:727-729` says the 90-day age test "belongs to the sweeper, because it is a tunable
retention heuristic and this view is a correctness floor". Inverted: the age test is the *only* thing
that would have stopped this, and it is the tunable one. A correctness invariant is being carried by
a knob, in the schema whose own between-rounds rule says *visible tuning knobs are safe; invisible
ones are the dangerous kind*. Round 8's C3 comment even predicts the failure — "does it invite a
sweeper that forgets it?" — and then ships the view that invites it.

**Change:** add `and g.state = 'complete'` to the view, and add a grace window on
`produced_at` so a generation completed moments ago is not swept before its artifact is visible
(ADR-0006's Consequences already require one: *"it needs a grace period so a blob written but not
yet published is never collected"* — that requirement never reached the schema). Then assert it: a
reserved-but-not-recorded generation must return **zero** rows from the view.

## BLOCKING B2 — `record_artifact` refuses, and destroys paid work, when a worker lost BOTH its token and its slot

`04_artifacts.sql:450-463` (the round-7 H2 ownership fence) states its own coverage argument:

> Both are needed: fencing on the token alone breaks the restarted worker, and fencing on the slot
> alone breaks the reclaimed one.

Both disjuncts are about a **single** loss. Nothing considered the conjunction, and the conjunction
is ordinary: a worker that crashes loses its in-memory token (that is round 7 B1's `B1a` premise) and
its lease then lapses, which is precisely what invites a reclaim.

MEASURED (`dig_max_attempts` raised to 3, the value `04:230-231`'s own comment reasons from — see
M6):

```
F1. W1 reserves dig:8 with gW1 -> reserved  (W1 calls Gemini and PAYS)
F2. W2 reclaims dig:8 with gW2 -> reserved  (slot re-pointed to gW2)
F3. restarted W1 records its PAID work (token lost)
      -> REFUSED [P0001] video_artifacts: cannot mark dig:8 as recorded — generation gW1 is pending
F4. gW1 state=pending ; recorded artifacts for gW1 = 0
F5. CONTROL — same call WITH the token -> recorded_after_loss
```

The control proves the fence is the cause: the identical call with the token succeeds. Without it,
neither disjunct holds (`reserved_by <> null-token`, and the slot's pending row now names gW2), the
generation stays `pending`, and then round 7's *other* fix —
`video_artifacts_generation_complete` — rejects the append.

Three things make this Blocking rather than High:

1. It is the failure the design explicitly forbids. `04:387` — **"THE FLIP — and it NEVER REFUSES."**
   It refuses, with a raw `P0001`, which is shape #8 in the function that fixed shape #8 for itself.
2. It discards paid Gemini output — the exact outcome the user decision of 2026-08-07 ("proceed and
   keep the paid work") was made to prevent, revoked by a later fix that never mentioned it. That is
   the *second* time this has happened to that decision (JOB 3 asks whether it is structurally
   protected: **no**, see H-J3 below).
3. It is round 7's own pattern, again: B1's fix and H2's fix are each individually right and wrong as
   a set.

**Change:** the generation-completion fence needs a third disjunct for the worker that can prove
neither — the honest one is *"this generation has no recorded artifact anywhere and is still
pending"*, since a pending generation nobody else can complete belongs to whoever holds its bytes.
Alternatively pass the generation's own `reserved_by` back to the caller at reserve time and let a
restarted worker re-read it from `video_generations` (it is durable; the token is not). Either way,
assert the doubly-lost worker as a named scenario — it is currently absent from all 103.

## BLOCKING B3 — after this migration nothing can ingest a new video

`01_workspaces.sql:41-43` sets `videos.workspace_id NOT NULL` with **no default and no trigger**;
`03_generations.sql:96-97` then adds `videos_workspace_video_fk` to `workspace_videos`, whose only
population is the one-shot seed at `03:89-95`.

Every live writer inserts a fixed column list that omits `workspace_id` — `claim_video_slot`
(`0023:87`), `0009:94`, `0007:35` — and nothing anywhere creates a `workspace_videos` row for a video
that did not exist at migration time.

MEASURED, running the exact INSERT `claim_video_slot` performs:

```
I1. claim_video_slot's INSERT (0023:87) -> REFUSED [23502] null value in column "workspace_id"
                                          of relation "videos" violates not-null constraint
I2. same INSERT + workspace_id supplied  -> REFUSED [23503] insert or update on table "videos"
                                          violates foreign key constraint "videos_workspace_video_fk"
```

Two independent breakages, one behind the other. The same shape applies to `jobs.workspace_id`
(`01:46-48`): every enqueue RPC's column list — `0008:54`, `0009:26`, `0011:83`, `0018:32` — omits
it. (I did not get a clean measurement there because `jobs` has an unrelated pre-existing
`job_version` NOT NULL that my synthetic insert tripped first; the column lists are direct evidence.)

This is **not** the out-of-scope "it is not a real migration" report. The defect is in the design:
the schema mandates two values per new video and the spec names no producer for either. §5.0.1
describes `workspace_videos` as *"the entity the manifest keys on"* and never says who inserts a row
into it. A rule that depends on every future caller remembering is the shape this review keeps
finding — here it is not even written down to be remembered.

**Change:** the design must name the writer. The cheapest form consistent with the rest of the
schema is a `before insert on videos` trigger that resolves `workspace_id` from `playlists` and
upserts the `workspace_videos` parent — the same "prevented, not repaired" argument `03:99-108`
makes for the corrections sync, and for the same reason (there is already more than one writer).

## HIGH H1 — `reserve_artifact_slot` hits `video_artifacts_free_uq` raw; round 8's C1 fixed one of the two sites

Round 8's C1 gave the free path a reconciler **in `record_artifact`** and left the sibling entry
point alone. MEASURED:

```
B1. record free html           -> recorded_free
B2. re-render (C1's fix)       -> recorded_free
B3. reserve the same free slot -> RAW [23505] duplicate key value violates unique constraint
                                  "video_artifacts_free_uq"
```

Root cause, and it is worth naming because it is invisible: `reserve_artifact_slot`'s
`already_recorded` short-circuit (`04:256-260`) tests `generation_id = p_generation_id`. For a free
slot both sides are NULL, and `NULL = NULL` is **NULL, never true** — measured. So the short-circuit
is not merely wrong for free slots, it is *unreachable* for them, and the INSERT below it uses the
in-flight partial index as its conflict arbiter, which a recorded free row can never match.

Shape #10, instance eight — a fix applied at one site with an identical sibling three screens away,
in the round that added the fix.

**This also settles JOB 2's check-then-act race, in the only way available without two sessions.**
Round 7 could only reason about it. The free branch makes the *same* defect deterministic: a
short-circuit that fails to fire, followed by an INSERT whose arbiter does not cover the guard that
actually collides, producing a raw `23505` where a typed outcome was promised. The paid interleaving
(C1 reads, C2 records, C1 inserts → `video_artifacts_paid_uq`) is the identical structure with a race
in front of it; I could not construct the interleaving inside a rolled-back transaction, and I am not
willing to commit DDL to a database another agent is reading. **Analysis for the paid case; measured
for the free case; same defect.**

**Change:** give the free path its own short-circuit (`generation_id is null` rather than `=`), and
name **both** indexes' reconcilers in the guard-coverage note (see M2).

## HIGH H2 — a free slot that was reserved can never be recorded

`record_artifact`'s free branch (`04:432-439`) sets `blob_key` and `state` and leaves
`lease_expires_at`, `lease_token` and `reserved_at` in place — unlike both paid paths, which clear
all three. MEASURED:

```
C1. reserve a FREE slot -> outcome=reserved  (state=pending)
C2. record it           -> RAW [23514] new row for relation "video_artifacts"
                           violates check constraint "art_pending_has_reserved_at"
```

The slot is now permanently unrecordable: every retry takes the same branch and fails the same way.
`04:243`'s aside — *"'render' is free and never reserved"* — is the only thing standing between the
design and this, and it is a convention, not a guard: `p_generation_id` has no default, so passing
NULL is an ordinary call, and `reserve_artifact_slot` has a dedicated `if p_generation_id is not
null` branch precisely to support it.

**Change:** either clear the three lease columns in the free branch's `do update` (one line, and it
makes reserve-then-record work), or make `reserve_artifact_slot` reject `p_generation_id is null`
with a typed outcome so the convention becomes a guard.

## HIGH H3 — `p_blob_key` is silently discarded whenever a row already exists

Neither the holder path (`04:466-469`) nor the append path's `do update` (`04:525-532`) assigns
`blob_key`. Only the fresh INSERT uses it. MEASURED:

```
D1. record with a DIFFERENT key -> recorded_as_holder
D2. blob_key the manifest now names = …/videos/vidP/gD/RESERVED.md
```

The caller wrote its bytes at `ACTUALLY-WRITTEN.md`, was told `recorded_as_holder`, and the manifest
points at `RESERVED.md`. `art_key_names_generation` cannot catch it — it constrains segments 1–4, and
both keys agree on all four.

This is shape #4 (a row claiming something the blob does not satisfy) in the spec whose entire
subject is the address, and it is silent on the success path. If the reservation's key is meant to be
authoritative, the honest design raises on a mismatch — that is a caller bug, a SHAPE violation, and
rejecting is correct. Silently keeping one of two divergent addresses is the one option that cannot
be right.

**Change:** compare and raise, or assign `excluded.blob_key` on both paths. Assert the mismatch.

## HIGH H4 — the `produced_at` future bound has zero tolerance and is measured against `transaction_timestamp()`

`03_generations.sql:289-292`. MEASURED:

```
transaction_timestamp | 2026-08-08 20:32:56.309397+00
wall_clock            | 2026-08-08 20:32:56.773142+00

G1. produced_at = clock_timestamp() (real production time) -> REFUSED [P0001] … is in the FUTURE
G2. produced_at 250ms ahead (ordinary NTP skew)            -> REFUSED [P0001] … is in the FUTURE
```

Two distinct consequences:

- **G2 — cross-replica.** `p_produced_at` exists *because sync carries a remote clock's value*
  (`04:409-411`). Two machines are never exactly in step; 250 ms of skew is unremarkable NTP
  behaviour. A replica whose clock is marginally ahead cannot replicate its own generations at all,
  and because this is a `raise` rather than a typed outcome it aborts the entire sync batch, not one
  row.
- **G1 — long transactions.** `now()` in a trigger is transaction start. Any writer that opens a
  transaction, does work, and then stamps the real production time is rejected — the value is in the
  future *relative to a clock that stopped when the transaction began*. This is the batch-sync shape
  named in the brief, and it needs no clock skew at all.

Round 7 B2 was right that an unbounded caller-supplied value on a ranking rung is a defect; the fix
is a bound with no tolerance on the one axis where tolerance is mandatory. It is also shape #12 — it
rejects a caller who did nothing wrong.

**Change:** bound against `clock_timestamp()`, not `now()`, and allow an explicit skew grace
(a named constant, openly a heuristic — those are the safe kind). A clock 5 minutes ahead still
cannot meaningfully outrank; a clock 250 ms ahead is not an attack.

## HIGH H5 — a free artifact's `blob_key` has no workspace confinement at all

`art_key_names_generation` (`04:147-152`) is `generation_id is null or (…)`. Every free row —
`pdf:*`, `html` — takes the `or` and is unconstrained. MEASURED:

```
E1. tenant A free row naming tenant B's key -> ACCEPTED
      (blob_key=fffff149-fd94-41e8-9d96-8696e5e53932/videos/OTHER/secret.pdf)
E2. visible in video_artifacts_current for tenant A = 1 row(s)
```

Tenant A's manifest names tenant B's blob and the row is served through `video_artifacts_current`,
whose RLS keys on `workspace_id` — the row's, not the key's. RLS is doing exactly what it should and
is the wrong control for this; the constraint is the right one and it is switched off for half the
taxonomy.

The comment above the constraint reasons entirely about generation ids and metacharacters. The first
three segments (`workspace_id / 'videos' / video_id`) are meaningful for a free row too, and the
`generation_id is null` escape hatch was written to exempt the *fourth*.

**Change:** split it — segments 1–3 unconditionally, segment 4 only when `generation_id is not
null`. One line, and it closes a cross-tenant address on the serve path.

## MEDIUM M1 — the guard-coverage ratchet is satisfiable without being true

`scripts/check-guard-coverage.py:180` — `if name not in mutation_text`. That is a substring search
over the whole of `mutate-schema.py`. Every SEQUENCE guard's requirement is satisfied **today by its
own name appearing inside a mutation's label string**, and by nothing else:

```
video_artifacts_inflight_uq : mutate-schema.py:105  (label text only)
video_artifacts_paid_uq     : mutate-schema.py:133  (label text only)
video_artifacts_free_uq     : mutate-schema.py:343, 359  (label text only)
forbid_collecting_current   : mutate-schema.py:374  (label text only)
```

`video_artifacts_inflight_uq`'s "mutation" does not touch the index — it inverts the busy/exhausted
branch order in the RPC, a different guard entirely. Rename any label and the ratchet goes red for a
guard that is still covered; add a label mentioning a guard while mutating something else and the
ratchet goes green for a guard with no mutation.

The script's own docstring says it exists because *"an absence is only visible against an ENUMERATED
WHOLE"* — and then verifies coverage against free text. **Change:** add an explicit
`covered_by=[label, …]` field to `GUARDS` and match on the mutation *labels*, not on the file body.

## MEDIUM M2 — the SEQUENCE reconciler notes are single-site, and two are now false

- `video_artifacts_free_uq`: *"record_artifact's free branch upserts"* — true, and incomplete;
  `reserve_artifact_slot` hits the same index raw (**H1**, measured).
- `video_artifacts_paid_uq`: *"record_artifact: on conflict do update"* — true, and incomplete;
  `reserve_artifact_slot`'s check-then-act path reaches the same index with the wrong arbiter.

The note field exists because *"'this one is fine' is exactly the judgement that needs to survive the
next reader"*. It survives as a claim about one call site, and both guards have two.

## MEDIUM M3 — SHAPE/SEQUENCE is a per-guard binary label, and at least three guards have both faces

This is JOB 3's audit, and the answer is **yes — a guard labelled SHAPE is answering a sequencing
question, and B2 measures it rejecting a caller who did nothing wrong.**

| Guard | Label | The sequencing face |
|---|---|---|
| `video_artifacts_generation_complete` | SHAPE | *"has the generation been completed yet?"* is an ordering question. **Measured** in B2 rejecting a worker whose only fault was restarting and being reclaimed |
| `video_generations_freeze` | SHAPE | *"has this already happened?"* is the SEQUENCE question verbatim. It is reconciled — `record_artifact`'s `g.state='pending'` filter makes re-completion a no-op — but the reconciler is undocumented because notes are only required for SEQUENCE |
| `art_dig_has_span` | SHAPE | Round 7's own record says the P22 assertion failed on it *because a reclaimed writer's row was gone* — a caller who arrived second. It is SHAPE **only because** `record_artifact` recovers the span; that reconciler has no note and appears **zero** times in `mutate-schema.py` |

The pattern is consistent: a guard is SHAPE *given* a reconciler somewhere in an RPC, and the
classification records the conclusion while discarding the premise. The ratchet then attaches its
obligations (a note, a mutation) to the label — so the reconcilers that keep three SHAPE guards from
rejecting a second caller are exactly the ones nothing protects. That is the classification pass
enforcing the half that was never the problem: both defects it was built from
(free-render, GC batch abort) were found by asking the SEQUENCE question of something that looked
like SHAPE.

**Change:** make the class a property of the *guard × call site*, or at minimum require a note on any
SHAPE guard whose SHAPE-ness depends on a reconciler, and name the reconciler.

## MEDIUM M4 — the mutation gate edits repo-tracked files in place, and misreported itself to me

`mutate-schema.py:main` writes the mutation into
`docs/superpowers/specs/…/schema/{03,04}*.sql` — the real files — and restores them in a `finally`.
Two agents running `./scripts/check-schema-gates.sh` at once therefore read each other's mutations.

MEASURED. In the repo:

```
23/44 mutations behaved as expected
❌ FAILED: …/mutate-schema.py
```

with 21 entries reported `RED(other)` carrying detail text belonging to a *different* mutation —
21 of them the same string, `ASSERTION FAILED — backfill lost corrections: wv has 0, videos has 99`,
which is mutation #9's own expected failure. In an isolated copy of the same commit:

```
44/44 mutations behaved as expected
baseline restored: GREEN ✅
```

Shape #11, instance four — an instrument that misreports its own result — and the most expensive
kind, because it fails **loud and wrong**: I spent a probe cycle treating a green artifact as broken,
and the opposite mistake is equally available (a concurrent run can mask a genuine GREEN as
`RED(other)`, which the script counts as *bad* but a reader skimming the ⚠️ lines may not).

The `finally` also does not survive `SIGKILL`, so an interrupted run leaves a mutated,
repo-tracked schema file on disk.

**Change:** copy the schema to a temp directory and mutate the copy — `verify-schema.sh` already
resolves its schema dir from its own location, so this is a `cp -r` and a path.

## MEDIUM M5 — a dig detached one second ago is immediately collectable

MEASURED: `L1. dig detached at 2026-08-08 20:36:28 ; in video_generations_collectable = 1 row(s)`.

Correct under the 2026-08-06 retention decision *only* because §8's 90-day clock lives in the
sweeper. Same structure as B1 — a correctness-shaped consequence resting on a tunable knob outside
the "correctness floor" — but here the decision was made deliberately, so it is Medium, not Blocking.
Worth stating explicitly in the view's comment, since the view is the thing a future sweeper author
will read.

## MEDIUM M6 — the live `dig_max_attempts` is 1, not the 2 the schema reasons from

MEASURED from `guardrail_config`: `summary_max_attempts=1`, **`dig_max_attempts=1`**,
`max_serve_attempts=5`, `lease_ttl_seconds=180`, `max_duration_seconds=1800`.

`04:230-231` argues the per-kind bound is necessary because the knobs *"disagree by 5x
(summary_max_attempts=1, dig_max_attempts=2, max_serve_attempts=5)"*, and `05_assert.sql` asserts
*"past dig_max_attempts=2 the outcome was reserved"* — so the assertions set the value they then
verify, and the production value is different. With 1, `04:245-252`'s named consequence — *a worker
that CRASHES leaves a slot no one can retry* — silently extends from summaries to digs, and B2's
scenario is unreachable in production for the accidental reason that no dig slot is ever reclaimable
at all. (That is not a mitigation: the same conjunction is reachable through the summary path once
`summary_max_attempts` is ever raised, and through any kind using `max_serve_attempts=5`.)

**Change:** state the live values in the comment, or read them in the assertion rather than setting
them, so the schema's reasoning and the running system cannot drift.

## LOW L1 — `recorded_after_token_loss` is returned for a plain idempotent retry

`v_existed` (`04:491-493`) is true for a **recorded** row too, so a worker retrying after a fully
successful record gets `recorded_after_token_loss` — "this was your own reservation, you just could
not prove it" — when nothing was lost. Harmless today; misleading in a log.

## LOW L2 — the span recovery borrows `end_sec` across generations, and the justification covers only `start_sec`

`04:495-511`. The argument is *"`dig:8` is seconds 8..88 in every generation of it"*. The start is
encoded in the slot name, so borrowing it is definitional. `end_sec` is the **next** section's
boundary, which can legitimately move when the summary is regenerated — that is the whole subject of
the section-timestamp work (PR #21). Borrowing it manufactures a claim, which is the same objection
the very next paragraph raises to borrowing `source_generation_id`.

---

# JOB 2 — the three things round 7 could not settle

- **The check-then-act race.** Settled as far as it can be without two sessions — see **H1**. The
  free path makes the identical structure deterministic and measured; the paid interleaving is the
  same defect with a race in front of it. I did not commit DDL to construct real concurrency because
  another agent is reading the same database.
- **The inert `pending` generation. It is NOT inert.** It is **collectable** (B1, measured), which is
  the one behaviour that turns it from litter into data loss. It also holds `reserved_by` forever,
  satisfies the FK so nothing reclaims it, and — with `summary_max_attempts=1` — is permanent.
  The chain that matters: a crashed worker's pending generation is swept to `body_collected=true`;
  if the slot is ever retried under the *same* generation id, `reserve`'s `on conflict do nothing`
  adopts it, the retry pays, records, completes — and the paid artifact is invisible in both views
  forever, exactly as measured in A6/A7.
- **`persist_summary`'s merge semantics.** Read (`0021:99-155`). Nothing in the live path updates a
  `video_generations` row, so the freeze trigger forbids nothing today — it writes only
  `videos.data`, and the fields it writes (`mdCorrectionsHash`, `mdGeneratedAt`, `docVersion`,
  `summaryMd`) are the card's fields living in the *old* home. Two observations for the cutover:
  (1) it never touches `corrections`, so `videos_corrections_sync_upd_trg`'s `when` clause keeps it
  free — good; (2) its whole design is *last-writer-merges* on a mutable row, which is the opposite
  of the append-only generation model, so the cutover is a rewrite rather than a re-point. **No
  finding**, but backlog #17's residue is real and this is not the round that closes it.

---

# JOB 3 — the invariants

- **"The reservation guards SPENDING, not RECORDING."** **Not structurally protected — violated a
  third time, measured (B2).** It has now been revoked by round 6's freeze (round 7 H2 found it),
  by round 7's fence (this round found it), and it will be revoked again, because it is enforced
  nowhere: no constraint, no trigger, no assertion states it. Every other load-bearing rule in this
  design was eventually moved into a guard precisely because *"a rule that depends on every future
  caller remembering"* fails. This one is still prose. **The single highest-value change available
  is an assertion**: for each way a worker can lose (token, slot, both, and a duplicate generation
  id), `record_artifact` must return a typed outcome and must never raise. That is four rows, it
  would have caught B2, and it converts the user decision into something a fix cannot silently undo.
- **"A generation must be complete when something recorded points at it."** Holds for INSERT and
  UPDATE via `video_artifacts_generation_complete` (`before insert or update`, correct — an INSERT is
  a state with no transition). It does **not** hold for `COPY … FROM` with `FREEZE`, for
  `TRUNCATE`-then-reload, or for logical replication apply, none of which fire row triggers; and
  `service_role` holds `insert, update, delete` on the table. That is the same class as round 6's H4
  (`anon` TRUNCATEd the table), one privilege level up, and I would treat it as accepted rather than
  fixed — but it should be *written down* as accepted, because right now the invariant reads as
  absolute.
- **The SHAPE/SEQUENCE audit** — see **M3**. Answer: yes, and B2 is the measured instance.

---

## Standing shapes — what this round found

| # | Shape | Instance |
|---|---|---|
| 3 | Mutable value in an address | **H3** — `p_blob_key` silently discarded; manifest and bytes diverge |
| 4 | A row claiming what the blob does not satisfy | **H3**, **H5** |
| 8 | A policy that errors rather than denies | **B2** (`P0001` from the function that "never refuses"), **H1**, **H2** (raw `23505`/`23514`) |
| 9 | A fix that moved or reintroduced a defect — **instance ten** | **B1** (round 8's C3 reopened round 5's H3), **B2** (round 7's H2 × round 7's B1) |
| 10 | A fix at one site with an identical sibling nearby — **instance eight** | **H1** (C1 fixed the free path in `record_artifact`, not in `reserve_artifact_slot`) |
| 11 | An instrument that misreports its own result — **instance four** | **M4** (the mutation gate mutates shared files: 23/44 in the repo, 44/44 isolated) |
| 12 | A guard that rejects a caller who did nothing wrong | **B2** (restarted + reclaimed), **H4** (250 ms of NTP skew), **B1** (a worker swept mid-payment) |

## Verdict

**NOT CONVERGED** — 3 Blocking and 5 High, all new.

The round-7 pattern held again and is now the dominant signal: **B1 and B2 were each created by a
round-7 or round-8 fix**, and neither is a defect in the fix considered alone. Round 8's own
between-rounds step ("classify the rules, then cross-derive them") was run on the *rules*; it was
not run on the *fixes*, and both Blockings are interactions between two fixes written the same day.
Before round 9, I would cross-derive the four round-7/8 changes against each other explicitly — in
particular, every path by which a generation can be `pending` at a moment some other guard assumes
it is not.
