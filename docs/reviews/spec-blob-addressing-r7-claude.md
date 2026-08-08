# Round 7 — Claude adversarial review — stable blob addressing

**Verdict: NOT CONVERGED** — 2 Blocking, 3 High, 5 Medium, 1 Low. Every Blocking and High is an
interaction *between* two of the four merged items, which is the condition this round was called to
test.

Everything below was **measured** against the live local Postgres (`supabase_db_…-cloud`) inside a
rolled-back transaction, using the same harness pattern as `verify-schema.sh`. Error text is verbatim.

## The coordinator's two claims, independently checked

| Claim | Verdict |
|---|---|
| 89/89 assertions pass | **TRUE.** `verify-schema.sh` → `ASSERTIONS_OK` / `ALL_STATEMENTS_OK` |
| 35/35 mutations behave as expected | **TRUE.** `./mutate-schema.py` → `35/35`, exit 0, baseline restored GREEN |

Both hold. The findings below are things neither instrument can see, and three of them are cases where
an instrument reports success over a live defect.

---

# JOB 1 — the four items cross-derived against each other

## BLOCKING B1 — `record_artifact` discards paid work and raises a raw SQLSTATE, on three separate paths. Item 4 × item 4, exposed by item 3.

The design states the property outright:

> `record_artifact` | Flips in place when the token matches, otherwise **appends**. Never refuses
> — `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:2151`

and the whole reason the reviewer's `lease_token` veto was **declined** on 2026-08-07 was
*"rejecting W1 does not prevent the double charge — it throws away one of the two things we paid for"*
(`schema/04_artifacts.sql:192-203`). Measured: it throws the work away anyway, just via a raw 23505
instead of a typed `refused`.

The cause is that the append-after-loss path (`04_artifacts.sql:412-417`) **re-derives the row from
its arguments instead of from the reservation**, and inserts unconditionally. Three reachable
consequences:

**B1a — a single worker, no race, no reclaim, live lease.** A worker reserves, restarts, and no longer
knows its `lease_token`. The token no longer matches, so the flip takes the append path — and collides
with its own still-pending row, because `video_artifacts_paid_uq` has no state predicate:

```
=== PROBE F ===
 reserve | reserved            (lease still LIVE, nobody else touched anything)
ERROR:  duplicate key value violates unique constraint "video_artifacts_paid_uq"
DETAIL:  Key (workspace_id, video_id, slot, generation_id)=(…, pv7, dig:3, gONLY) already exists.
CONTEXT:  SQL statement "insert into public.video_artifacts …"
          PL/pgSQL function public.record_artifact(…) line 19 at SQL statement
```

No concurrency is needed. This is the plain crash-recovery path for any worker that does not durably
store its token — and nothing in the design says it must.

**B1b — the same generation id re-reserved after its own lease expired.** `reserve_artifact_slot`
explicitly anticipates this: the `on conflict do nothing` at `04_artifacts.sql:268-272` is justified as
handling *"a completed one being retried … because this slot's row was reclaimed"*. Reserve accepts it
(`reserved`), and then record cannot survive it:

```
=== PROBE C ===
 first reserve        | reserved
 reclaim, SAME gen id | reserved
the first incarnation returns from Gemini with its STALE token:
ERROR:  duplicate key value violates unique constraint "video_artifacts_paid_uq"
DETAIL:  Key (…, pv3, dig:7, gSAME) already exists.
```

**B1c — the two paths are not equivalent given identical arguments.** The holder path never reads
`p_source_generation_id`/`p_start_sec`/`p_end_sec` (the UPDATE at `04:406-409` touches only state and
lease columns), so a caller may legitimately omit them and rely on what reserve stored. The append path
requires them:

```
=== PROBE I ===
I1 HOLDER path, caller omits span:  holder path -> recorded_as_holder   (stored span 1,9 preserved)
I2 LOSS   path, same omission:      loss path REJECTED [23514] new row for relation
                                    "video_artifacts" violates check constraint "art_dig_has_span"
```

So the caller that works in the common case fails only under the race — the worst possible place to
put a latent argument requirement.

**Why no round caught it.** `05_assert.sql:569-584` is the only `recorded_after_loss` test, and it
gives the loser a *different* generation id (`gDIG` vs the holder's `gOTHER`) **and** re-passes the span.
That is the one configuration in which the append path works. The paid-uniqueness assertion
(`05_assert.sql:325-328`) pits two *recorded* rows against each other, never a pending one against a
recorded one.

**Change I would make.** Make the append idempotent against the pending row rather than blind:
`on conflict (workspace_id, video_id, slot, generation_id) where generation_id is not null do update
set state = 'recorded', lease_expires_at = null, lease_token = null, reserved_at = null` — and take
the span/provenance from `coalesce(p_…, video_artifacts.…)` so both paths agree. Return a fourth typed
outcome (`recorded_after_token_loss`) rather than a 23505. This is shape #8, the exact defect
`reserve_artifact_slot:304-306` fixes for itself and did not sweep to its sibling — the **seventh**
instance of shape #10.

## BLOCKING B2 — the `detached_at` bound rejects the value its sibling trigger just wrote. Item 1 × item 3.

`video_artifacts_append_only` **owns** `detached_at` on UPDATE (`04_artifacts.sql:660-664`:
`new.detached_at := … now()`). `video_artifacts_generation_complete` then bounds it against the
generation's `produced_at` (`04_artifacts.sql:714-723`). Nothing bounds `produced_at` to `<= now()` —
`gen_complete_has_produced_at` only requires NOT NULL, and `record_artifact` takes it as a caller
parameter precisely so sync can carry a remote clock's value (`04:388-393`, `:402`).

So a dig whose generation carries a future `produced_at` **can never be detached**, and the error
blames the writer for a value the writer never supplied:

```
=== PROBE A ===  (generation gFUT, produced_at = now() + 10 days; plain `update … set state='detached'`)
ERROR:  video_artifacts: detached_at 2026-08-08 00:58:48+00 precedes generation gFUT
        produced_at 2026-08-18 00:58:48+00 (backdated retention clock)
CONTEXT:  PL/pgSQL function public.video_artifacts_generation_complete() line 27 at RAISE
```

§6.2 becomes unimplementable for that artifact — permanently, since `produced_at` is frozen by
`video_generations_freeze` and `detached_at` cannot be supplied by the writer on the UPDATE path.
This is not exotic: the design's own fixture `gC_STALE` carries `produced_at '2026-09-09'`
(`05_assert.sql:788-789`), a month ahead of today.

**And the other half is worse — as shipped, the UPDATE-path bound enforces nothing.** The comment at
`04_artifacts.sql:727-730` claims the firing order is *"required rather than incidental: on UPDATE the
append-only trigger OWNS `detached_at`, so the bounds above must read the value it settled"*. Measured
in both orders, the effect is exactly inverted:

```
=== PROBE H — writer backdates detached_at to 2020-01-01 via UPDATE, generation produced 2026-02-01 ===
AS-SHIPPED       (append_only first):  ACCEPTED -> stored detached_at = 2026-08-08 01:01:58+00
REVERSED-ORDER   (bounds first):       REJECTED [P0001] … detached_at 2020-01-01 … precedes … produced_at
```

Under the shipped order the bound only ever inspects a value the sibling trigger wrote one statement
earlier, so it can never fire on writer input — it can only fire on the pathology in PROBE A. The order
the schema says would be wrong is the one under which the bound actually does its job.

**Change I would make.** Two independent fixes: (1) bound `produced_at` (`check (produced_at <= now())`
is not available in a CHECK — do it in `record_artifact` and in a generation-side BEFORE trigger);
(2) on the UPDATE path, skip the bounds entirely when the trigger owns the value — `if tg_op = 'INSERT'
and new.state = 'detached' then …` — and say so, instead of claiming an ordering does work it does not.

## HIGH H1 — the "required" trigger order is pinned by nothing and covered by nothing.

Renaming `video_artifacts_append_only_trg` → `zz_video_artifacts_append_only_trg`
(`04_artifacts.sql:671`) inverts the documented-as-load-bearing order. Result:

```
$ ./verify-schema.sh          # with the two BEFORE triggers in the opposite name order
ASSERTIONS_OK
✅ schema verified (rolled back)
```

89/89 green. No assertion reads `pg_trigger.tgname` ordering, no mutation in `mutate-schema.py` touches
a trigger name, and the correctness argument rests entirely on `v` sorting after `a` — a property any
future rename silently breaks. This is shape #6 (a guard with no test) sitting under the one place the
file says the design depends on ordering. Given B2, the honest fix is to remove the dependency; if it
is kept, assert the order.

## HIGH H2 — `record_artifact` completes a generation with no ownership fence at all, and poisons its real owner.

The generation UPDATE (`04_artifacts.sql:396-404`) filters on `(workspace_id, video_id, generation_id)`
only — no token, no `state = 'pending'`, no check that the caller's pending artifact points at this
generation, and no `slot`. It runs **before** and **independently of** the artifact write. Measured:

```
=== PROBE I3 ===
W1 reserves pvJ/dig:1 with gA;  W2 reserves pvJ/dig:2 with gB.
W2 records slot dig:2 but NAMES gA:      W2 naming gA -> recorded_after_loss
  gA | complete | 2026-01-01 00:00:00+00      <- completed with W2's production time
  gB | pending  |
now W1, the real owner of gA, comes back:
  W1 REJECTED [P0001] video_generations: the CONTENT of complete generation gA is immutable
```

W1's paid work is unrecordable, forever — `complete` is terminal by design. Worse, `gA`'s recorded
facts now describe bytes W2 wrote at `…/gA/dig/2.md` while W1's blob sits at `…/gA/dig/1.md`. That is
shape #4 (a row claiming something the blob does not satisfy) reached through `video_generations`,
which has no `art_key_names_generation` equivalent.

This needs a caller passing a generation id it does not hold, and every caller is `service_role`, so it
is a caller-error amplifier rather than an attacker path — but every other write in this design is
fenced and this one is not, and the failure it produces is silent-then-terminal.

**Change I would make.** Add `and state = 'pending'` to the generation UPDATE and require that the
caller's reservation names it: fold the generation completion into the artifact UPDATE's `where` via a
CTE, so a caller that does not own the slot completes nothing.

## HIGH H3 — a denied reservation still writes a permanent `pending` generation row. Item 3 × item 4.

Item 3 put the generation INSERT at `04_artifacts.sql:268-272`, **before** the upsert that decides
whether the caller gets the slot. The `already_recorded` short-circuit is correctly placed above it;
`busy` and `exhausted` are not. Measured — three reserve calls on one slot, two of them denied:

```
=== PROBE B ===
 W1 | reserved      W2 | busy      W3 | busy
generation rows left behind (pv2):        artifact rows (pv2):
 gW1 | pending                             gW1 | pending
 gW2 | pending   <- orphan
 gW3 | pending   <- orphan
```

Nothing ever removes these. `forbid_collecting_current` and §8's sweep key on `body_collected`, which
is meaningless for a generation no artifact points at; the row is not reachable from either ranking
view, so no consumer will ever notice it. A worker looping on `busy` with a fresh generation id per
attempt grows `video_generations` without bound, and every row is an FK-valid parent that makes the
table's own semantics ("a generation is a thing we produced") false.

**Change I would make.** Move the generation INSERT below the upsert, into the `if found then` branch —
the only branch that hands out a slot. It cannot go after `record_artifact` because the artifact FK
needs it, but it does not need to run for a caller that got nothing.

---

# JOB 2 — the instruments

## MEDIUM M1 — two `security definer` functions were not swept. Shape #10, again, in the file that names the habit.

`04_artifacts.sql:420-425` claims *"Sweeping all THREE replacements here, not just the one that
inherited the name — that one-site habit is what produced B1 in the first place."* Measured `pg_proc`:

```
=== PROBE D ===
 forbid_collecting_current           | secdef t | <NULL = default: PUBLIC EXECUTE>
 video_artifacts_append_only         | secdef t | <NULL = default: PUBLIC EXECUTE>
 video_artifacts_generation_complete | secdef t | {postgres=X/postgres}
 video_generations_freeze            | secdef t | {postgres=X/postgres}
 sync_corrections_to_workspace_video | secdef t | {postgres=X/postgres}
 slot_kind / no_corrections_hash / corrections_hash_of | {postgres=X/postgres}
```

`has_function_privilege('anon', 'video_artifacts_append_only()', 'EXECUTE')` → `t`.

**Exploitability is near zero** and I want to be straight about that: a direct call is refused by
Postgres itself — measured `blocked: [0A000] trigger functions can only be called as triggers`. I am
reporting it because the *claim of completeness* is false, and because the sweep is the only thing
standing between this design and round 6's B1. Two lines: `revoke all on function
video_artifacts_append_only() from public, anon, authenticated;` and the same for
`forbid_collecting_current()`.

## MEDIUM M2 — the round-7 `RED(trigger)` fix is one instance short of fixing its own class. Shape #11.

The brief asks whether the new regex is *too permissive*. It is not — it is **too narrow**, which is
the same catch→miss failure it was added to remove. `mutate-schema.py:292` anchors on
`ERROR:\s*video_(artifacts|generations):`, and two of the schema's seven `raise exception` messages do
not carry that prefix. Called directly:

```
append-only DELETE     -> ('INVALID', 'ERROR:  video_artifacts is append-only: cannot DELETE …')
forbid_collecting      -> ('INVALID', 'ERROR:  refusing to collect generation gNEW — it is CURRENT …')
append-only ADDRESS    -> ('RED(trigger)', …)
gen freeze terminal    -> ('RED(trigger)', …)
gen-complete guard     -> ('RED(trigger)', …)
```

`video_artifacts is append-only:` has no colon after the table name (`04_artifacts.sql:637`), and
`forbid_collecting_current` uses no prefix at all (`04_artifacts.sql:572`). Today no mutation lands on
either message, so `35/35` is honest — but the next one to do so will be reported as an untested guard.
Anchor on `ERROR:.*(video_artifacts|video_generations|refusing to collect)` or, better, give every
`raise` in the schema one prefix and match that.

## MEDIUM M3 — `forbid_collecting_current` has no mutation entry.

`MUTATIONS` in `mutate-schema.py` covers items 1–4 and the round-5 fixes, but the round-5 H3 guard
(`04_artifacts.sql:564-579`) — the one standing between §8's sweeper and the current summary — has
none. Combined with M2, adding one today would report `INVALID`.

## MEDIUM M4 — a stale comment asserts a hole the code above it closes.

`04_artifacts.sql:734-746` is the file's last word and it says:

> ⚠ NOT `before insert`, and the omission is deliberate … A writer can therefore backdate a detached
> row it is inserting for the first time … **FLAGGED FOR ROUND 7 rather than left silent**

The trigger it annotates is `before insert or update` (`04_artifacts.sql:731-733`), the bound does run
on INSERT, and `05_assert.sql:1067-1076` (G13) asserts both directions. `04_artifacts.sql:704-713` and
the design doc (`…-design.md:1764-1780`, correctly struck through) both say it is closed. Per the
brief's own rule — where prose and schema disagree, the prose is the defect — delete it. Left in place
it will be re-reported as an open item by the next reader, which is how a fixed defect gets a second
life.

## MEDIUM M5 — nothing bounds `produced_at` to the past.

Stated separately from B2 because it is a defect in its own right: `produced_at` is a **ranking rung**
(`04_artifacts.sql:518`, `:549`) and a caller-supplied value with no upper bound. A single sync from a
replica with a fast clock ranks a generation above everything real until the clock catches up. Round 4's
J2-3 removed clock *reads* from the ranking; it did not stop a clock *value* being injected into it.

## Fixtures that describe a world no producer can reach

I re-ran the brief's own question over `05_assert.sql`. The one it already found (item 3's
hand-inserted complete generations) is real and now covered by the G-block. Two survive:

- `gC_STALE` / `gC_CUR` (`05:779-794`) are inserted directly as `complete` summaries with hand-written
  cards. A real producer reaches that state only through `reserve` → `record_artifact`, and `gC_STALE`
  carries a `produced_at` a month in the future. This is the fixture that makes B2 reachable in
  practice, sitting in a passing test.
- `05:335-338` hand-builds a `pending` row with a hand-made token rather than calling
  `reserve_artifact_slot`. That is why B1a is invisible to the suite: no assertion ever calls
  `record_artifact` with a token the reservation did not issue.

---

# JOB 3 — the invariants

**"A generation must be complete when something recorded points at it"** — I could not find a path
around `video_artifacts_generation_complete_trg`. `COPY FROM` fires BEFORE-INSERT row triggers; the
upsert in `reserve_artifact_slot` fires it on both the INSERT and DO UPDATE arms; `TRUNCATE` is not
granted to `service_role` (only `select, insert, update, delete`, `04:449`) and is revoked from the
client roles (`04:448`). The invariant holds. **Sound as written.**

**"`state` defaults to `complete`"** — I argued the opposite as instructed and the coordinator's
version survives. A `pending` default makes all four completeness CHECKs optional for any writer that
omits the column, and mutation `state defaults to pending instead of complete` goes `RED(trigger)`,
which is the proof. **Sound as written.**

**"The reservation guards SPENDING, not recording"** — the decision is sound; its *implementation* is
not, and that is B1. The design permits two recorded generations in one slot and the ranking handles it
(`05:569-584` asserts it) — but only when the two carry different generation ids. The moment they
carry the same one, which reserve itself permits, the design that was chosen to keep paid work throws
it away. **Right in substance, wrong in one specific place.**

**"`complete` is terminal and the content freezes"** — sound in the schema, and H2 is what it costs:
because it is terminal, the first writer to complete a generation wins permanently, so an unfenced
completion is not a recoverable error. The two rules are individually right and jointly produce the
un-recordable paid artifact in PROBE I3. I did not audit `persist_summary`'s layer-2 merge against it
(backlog #17's residue); that remains open and I flag it rather than claim it clear.

---

# Verdict

**NOT CONVERGED.** 2 Blocking, 3 High, 5 Medium, 1 Low.

The pattern the brief predicted held exactly: **every Blocking and High is an interaction between two
merged items, and none is a defect in either one on its own.** B1 is item 4's append path meeting the
uniqueness index item 4 itself added; B2 and H1 are item 1's trigger-owned clock meeting item 3's
bound; H2 is item 3's payload meeting item 3's freeze; H3 is item 3's generation row placed inside item
4's control flow. The four items were each reviewed against themselves and are each defensible; the set
is not.

The single most important finding is **B1**: `record_artifact` is documented as never refusing, was
deliberately designed not to refuse after a user decision on 2026-08-07, and refuses — with a raw
23505 and a rolled-back generation completion — on the plainest crash-recovery path there is, with no
concurrency required.

## Low

**L1 — the holder path silently ignores three of its own parameters.** `record_artifact`'s in-place
UPDATE (`04:406-409`) never writes `source_generation_id`, `start_sec` or `end_sec`, so a caller that
passes values differing from the reservation's has them accepted-and-discarded on one path and honoured
on the other (measured as I1/I2 above). Either read them into the UPDATE or drop them from the
signature and take them from the reserved row on both paths.

## Reproduction

All probes are in `<scratch>/probes/{B,C,D,E,F,G,H,I}.sql`, run as
`printf 'begin;\n'; cat schema/0{1,3,4}*.sql; cat probes/X.sql; printf 'rollback;\n'` piped to
`docker exec -i supabase_db_youtube-playlist-summaries-cloud psql -U postgres -d postgres`.
The trigger-order experiment is a copy of the spec dir with `create trigger
video_artifacts_append_only_trg` renamed to `zz_…` at `04_artifacts.sql:671`.
