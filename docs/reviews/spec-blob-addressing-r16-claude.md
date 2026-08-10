# Round 16 — Claude adversarial VERIFICATION review

**Subject:** `docs/adr/0007-artifacts-are-an-append-only-log.md` on `fix/adr-0007-round-13-findings`,
HEAD `5de5ac3`. Surface under review: `git diff 00d0c83..HEAD` (298 lines of ADR + 1 line of
`scripts/check-sentinel-meanings.py`). Round 15's fixes only; the round 14/15 "could not break" lists
were not re-reviewed, and render addressing is out of scope.

**Verdict: NOT CONVERGED — 1 Blocking, 2 High, 3 Medium, 2 Low.**

The core decision (delete the reservation protocol) still stands; I attacked it and could not move it.
Every finding below is in a **fix**, and the Blocking is in the one thing this round *adds*.

---

## ✅ THE SUITE RAN — this is not a read-only review

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` executed against the live
local Postgres (`supabase_db_youtube-playlist-summaries-cloud`, `postgres:17.6.1.147`, up 2 weeks,
healthy) inside a rolled-back transaction:

```
ASSERTIONS_OK
ALL_STATEMENTS_OK
ROLLBACK
✅ schema verified (rolled back)
```

Option C was then probed directly against that database in a separate rolled-back transaction loading
`01_workspaces.sql` + `03_generations.sql` + `04_artifacts.sql` over the live corpus. Every
`MEASURED` line below is psql output from that run. No repo-tracked file was modified; the sentinel
gate was exercised against a copy of the schema dir under the session scratchpad.

---

## BLOCKING

### B1 — `in_flight_until` has no moment at which it can be written: after `reserve_artifact_slot` is deleted, no `video_generations` row exists between the start of a paid call and its recording

The ADR says the marker is *"Written by whoever starts a paid call, for **every** kind"*
(`0007:424`). There is nothing to write it to.

**The row that would carry it cannot exist yet.** The only INSERT into `video_generations` anywhere in
the spec schema is inside `reserve_artifact_slot` at
`schema/04_artifacts.sql:307-313`, and it inserts `state = 'pending'`:

```sql
    insert into public.video_generations
      (workspace_id, video_id, generation_id, kind, state, reserved_by)
    values (p_ws, p_video, p_generation_id, p_kind, 'pending', v_token)
```

`record_artifact` is not a second writer — its generation write is an **UPDATE only**
(`schema/04_artifacts.sql:556`, `where … and g.state = 'pending'`), never an insert.
Verified by absence across every writer of that table:
`grep -rn "into public.video_generations\|update public.video_generations" supabase/migrations/*.sql
<spec>/schema/*.sql` returns exactly three hits, all in `04_artifacts.sql` (`:308` insert, `:366`
denial-cleanup update, `:556` completion update). `video_generations` does not exist in
`supabase/migrations/` at all — it is spec-only, so there is no live writer either.

**And Consequences deletes both halves of that.** `0007:383` deletes `reserve_artifact_slot`;
`0007:413-414` states in its own words that *"Deleting the `pending` artifact state leaves nothing that
produces a `pending` generation `[VERIFIED: schema/04_artifacts.sql:307-312 is the only producer]`"*.
The ADR reasons from that fact to *"the predicate goes vacuously true"* and stops one step short of the
consequence that matters: **the row itself is gone, not just its state.**

**MEASURED — the pre-content insert is refused, and only the deleted route works:**

```
NOTICE:  P2a summary pre-content insert: REJECTED -> [23514] … violates check constraint "gen_card_complete"
NOTICE:  P2d summary + produced_at only:  REJECTED -> [23514] … violates check constraint "gen_card_complete"
NOTICE:  P2b model pre-content insert:    REJECTED -> [23514] … violates check constraint "gen_complete_has_produced_at"
NOTICE:  P2c model pre-content + produced_at: ACCEPTED
NOTICE:  P2e summary pre-content WITH state=pending: ACCEPTED   (the deleted route)
```

With `pending` unreachable, `state` defaults to `'complete'` (`schema/03_generations.sql:291`) and the
four completeness CHECKs gated on `state <> 'complete'` — `gen_complete_has_produced_at` `:394`,
`gen_card_complete` `:395-408`, `gen_summary_has_format` `:409-410`, `gen_summary_has_hash` `:411-412`,
`gen_major_matches_card` `:417-420` — all become unconditional. A `summary` or `dig` generation cannot
be inserted until its card, `md_hash` and `doc_version_major` exist, and those exist only **after** the
paid Gemini call.

**This is the double-locked door already recorded in this schema**, at
`schema/03_generations.sql:271-283`:

> *"MEASURED: a cloud summarize could not RESERVE its summary slot. Reserving with no generation row
> raised [23503] on the artifact's FK; creating the generation row from what is knowable BEFORE the
> Gemini call raised [23514] gen_card_complete. **The paid call sits between those two, so both doors
> were locked.**"*

`state = 'pending'` is the key that was cut for that lock. This ADR throws the key away and then hangs
a new mechanism on the door.

**Every exit is also a defect, which is why this is Blocking rather than an omission:**

| Route the implementer could take | Why it falsifies the ADR as written |
|---|---|
| Keep `state='pending'` so a pre-content row can exist | Then `pending` is **not** deleted, `g.state = 'complete'` is **not** "vacated" (`0007:426`), and replacing a live guard with the marker *removes* a guard instead of succeeding one |
| Gate the four completeness CHECKs on `in_flight_until is null` instead | NULL then means both *"no paid call is running"* (GC) **and** *"the content has been produced"* (completeness) — the conflated sentinel `scripts/check-sentinel-meanings.py` exists to forbid |
| `model` only (P2c is the one ACCEPTED case) | Requires stamping `produced_at` **at call start**, and `produced_at` is a ranking rung carried as data (`03_generations.sql:348`) and frozen forever by the same trigger (`:484`). A clock lie in the ranking key. And it is a **per-kind** successor again — the thing option C was chosen to eliminate |
| Accept that no row exists during flight | Then the marker is **unwritable and unnecessary**: `video_generations_collectable` (`04_artifacts.sql:878-900`) can only return rows that exist, so round 9's B1 window is closed by the deletions themselves |

**The last row is the one worth sitting with.** If it is the true answer, this ADR adds a column, a CI
check, two prose rules, an assertion burden and a mutation-scoring burden to re-close a window that its
own deletions already closed — *"two mechanisms for one concern"*, in the document written to stop
exactly that, at the one place where round 15 forced a new mechanism in. That is the third occurrence
of the signature the ADR itself names at `0007:582-586`.

**Fix.** State, in one sentence, **when the `video_generations` row is created** in the post-ADR world.
That sentence decides everything else. Then either (i) show a pre-content row is still reachable and
say by what mechanism, or (ii) show it is not, and **delete `in_flight_until`** with the reasoning
recorded — dissolving the GC-floor problem is a better outcome than covering it, and it is the same
move that earned this ADR its headline.

---

## HIGH

### H1 — the stated invariant is verified for the smallest of the three kinds it covers, and is off by ~5× for the largest

`0007:437`: *"The covering mechanism's lifetime ≥ the covered operation's worst case."* The ADR then
computes exactly one bound — the magazine's — and the marker is declared *"for **every** kind"*
(`:424`).

The magazine arithmetic is **correct**, and every tag in it resolves: `MAGAZINE_MAX_PASSES` = 3 at
`lib/gemini-cost.ts:29`, `REQUEST_TIMEOUT_MS` = `60_000` at `lib/gemini.ts:94`, `baseDelayMs = 400` at
`lib/gemini.ts:252`, the `baseDelayMs * 2 ** attempt` backoff at `lib/gemini.ts:267`, the untimed
`countTokens` preflight at `lib/gemini.ts:82-84`. 3 × 60 000 + 400 + 800 = **181 200 ms**.

**The summary path is 4× longer and is never computed.** `lib/gemini-cost.ts:27`:

```ts
export const SUMMARY_MAX_PASSES = MAX_SUMMARY_ATTEMPTS * (GENERATE_JSON_RETRIES + 1); // = 12
```

and that is one call, not four: `lib/gemini.ts:361` is
`for (let i = 0; i < MAX_SUMMARY_ATTEMPTS; i++)` wrapping an `attempt()` that calls `generateJson` with
the default `retries` (`lib/gemini.ts:344` passes `undefined`). So **12 × 60 000 = 720 000 ms**, plus
`TRANSCRIBE_MAX_PASSES` = 3 (`lib/gemini-cost.ts:26`) × 60 000 = 180 000 ms in the same job, plus the
same unbounded upload — **≥ 900 s against the 181 s the ADR computed.**

Because `in_flight_until` has **no renewal** (deliberately — a renewal RPC is rejected at `0007:459`),
its value must be set to the full worst case at write time. Set from the magazine bound, it expires
mid-summary and the sweeper collects a generation whose paid call is still running: round 9's B1
verbatim, reached through the mechanism written to prevent it. This is structurally the **same defect
round 15 B2 measured in the `serve_model_charge` lease** — a covering lifetime shorter than the covered
call — reproduced by its replacement.

Compounding it: *"a CI check must fail if any input grows past it"* (`0007:445`) is a **promise, not a
gate**. No such script exists (`ls scripts/` shows no bound check; the six named in
`docs/dev-process.md` do not include one). An unenforced rule stated as a guard is this project's
recorded failure mode.

**Fix.** Compute the bound **per kind** and set the marker from the maximum, or state that the marker's
value is a function of kind. Write the CI check in the same slice, and have it assert against
`SUMMARY_MAX_PASSES`, `TRANSCRIBE_MAX_PASSES` and `MAGAZINE_MAX_PASSES` — all three are already
exported from `lib/gemini-cost.ts` for exactly this reason.

### H2 — inside one numbered item, (a) says a re-record **replaces** the source set and (b) says provenance is **immutable**; the citation given for "replace" says the opposite on the very path that matters

Both are sub-items of the round-15 B3 fix, ~10 lines apart:

- `0007:582` — *"**So: `record_artifact` writes the join rows in the same statement as the artifact
  row.** … **Replace**, to match the carry-forward's 'the row names its own sources' semantics."*
- `0007:588-592` — *"**Provenance must stay append-only.** … **That trigger branch moves onto
  `video_artifact_sources`.**"*

A replace is a delete-and-insert. The trigger being moved is
`schema/04_artifacts.sql:969-973`, which raises on **any** change to provenance, and `:959-961`, which
forbids `DELETE` outright:

```sql
    if new.source_generation_id is distinct from old.source_generation_id
       or new.start_sec is distinct from old.start_sec
       or new.end_sec   is distinct from old.end_sec then
      raise exception 'video_artifacts: the PROVENANCE of a % paid row is immutable (slot %, gen %)',
```

So the join table cannot both accept a replacing re-record and carry that trigger.

**And the justification inverts the mechanism it cites.** `coalesce(p_source_generation_id, v_src)` at
`04_artifacts.sql:663`, with `v_src` read from the *same* (slot, generation) row at `:654`, means
**omission = keep what is recorded**. That is precisely how a re-record avoids tripping `:969` today: it
re-states an identical value, so `is distinct from` is false. "Replace" on the omission path does the
opposite — it **wipes** the source set — which is not "the row names its own sources", it is the row
forgetting them. The carry-forward is an argument for **idempotent re-statement**, not for replacement.

This matters beyond consistency: a wiped source set makes both new guards vacuously true — the ranking
rung and the GC `not exists` — which is the failure the same item diagnoses at `0007:576-580` and calls
its *"third occurrence of the signature."*

**Fix.** State the rule as: a re-record must present the **same** source set or raise; an omitted
`p_source_generation_id` carries forward the recorded set unchanged. Then the moved append-only branch
and the re-record path agree, and the round-5 M5 guarantee survives the column drop intact.

---

## MEDIUM

### M1 — *"Restricting the clamp to rows that actually merge removes this entirely"* is false; it removes the single-row case only

`0007:195-198` claims the `count(*) > 1` restriction *"removes this entirely"* and that no
already-exhausted document is revived. Take a video in two playlists on one day, one `doc_key` at
`attempt_count = 5` (exhausted, `max_serve_attempts` = 5 per
`0012_serve_model_charge.sql:21`) and its sibling at 1. `count(*) = 2`, so the clamp applies:
`least(5 + 1, 4) = 4`. The merged key is now **below** the bound, and the exhausted document gets a
fresh paid Gemini attempt — `magazine_est_cents` against `serve_owner_budget` and `spend_ledger`
(`0020_reservation_release.sql:237-247`), the exact money effect round 15 H3 measured.

The restriction shrinks the population from *every* row to *multi-playlist* rows; it does not empty it.
It is a defensible trade (the alternative, `SUM = 6 > 5`, denies service with no stale fallback —
`0007:177-181`), and the residual is bounded: a one-time migration, at most one extra paid magazine call
per (owner, video, day). **The defect is the word "entirely"** — a completeness claim on the money path
in the paragraph whose own lesson is *"name what the rule ranges over, and check that it is what you
are deciding"* (`0007:202-203`).

**Fix.** Replace "removes this entirely" with the true statement: it removes the single-source case
completely and bounds the merged case to one additional attempt per merged key, once, at migration
time. Or clamp to `least(sum, max_serve_attempts)` and accept that an exhausted member keeps the merged
key exhausted.

*(The other two questions on this item check out — see "what I could not break".)*

### M2 — *"Only the sweeper may read `in_flight_until` … grep-checkable and should be checked"*: no script exists, and the grep it names has a hole

`0007:453-454`. "Should be checked" is not a check; nothing in `scripts/` implements it, and
`docs/dev-process.md`'s enforcement table lists six schema gates, none of them this.

Worse, the grep it proposes cannot see the main read path. The sweeper reads the marker through
`video_generations_collectable`, whose projection is `select g.*` (`04_artifacts.sql:879`), and the view
is granted to `service_role` (`:902`) — the same role every RPC runs as. A caller that selects from that
view, or `select *` from `video_generations`, obtains the column without the identifier
`in_flight_until` ever appearing in the source. A grep for the column name returns clean while the rule
is broken.

**Fix.** Either write the script and have it scan for the view/table as well as the column, or drop the
claim of enforceability and state the rule as an unenforced convention. Stating an unenforced rule as a
guard is the failure mode `check-guard-coverage.py` was written for.

### M3 — the ADR never says whether `in_flight_until` is ever cleared

The brief's question, and the document is silent. Lapsing is the right answer and it is a genuine
strength — a crashed producer's marker simply expires and the row self-heals, where `pending` needed a
reclaim protocol that produced three rounds of defects. On the success path a lapsed marker is harmless
because a recorded generation is excluded from `video_generations_collectable` by the
`not exists (… video_artifacts_current …)` clause (`04_artifacts.sql:898-900`) anyway.

But silence invites an implementer to add a clear-on-success, and that is a **caller obligation** — the
class this ADR retires two paragraphs earlier (`0007:483-486`, *"the sweeper reads it without any caller
having to remember anything"*). One sentence closes it.

**Fix.** *"`in_flight_until` is never cleared; it lapses. A caller that clears it has added an
obligation this ADR removed."*

---

## LOW

### L1 — the ADDED paragraph contradicts itself in three lines

`0007:387-392`: *"**ADDED — one column, and it is the only thing this ADR adds.**"* … *"Plus
`video_artifact_sources`, the provenance join table."* A table is not a column. The parenthetical that
follows ("replaces the dropped column rather than adding to it") explains why it is not a net addition,
but the bolded headline is the sentence a reader carries away, and it is false as written. Introduced by
reconciliation edit #2 — a pass whose purpose was removing exactly this shape.

**Fix.** *"ADDED — one column and one table, and they are the only additions."*

### L2 — `check-sentinel-meanings.py` is missing from the ADR's list of gates the new column must satisfy

`0007:471-472` names the gates `in_flight_until` gets: `05_assert.sql` and `mutate-schema.py`. It omits
the sentinel registry, which is mandatory for every nullable column in `video_generations`
(`scripts/check-sentinel-meanings.py:46-47`, `:142-146`).

**MEASURED** — schema dir copied to the session scratchpad, `in_flight_until timestamptz` added to the
temp copy only, gate run against it:

```
❌ UNDOCUMENTED  video_generations.in_flight_until
              A nullable column with no recorded meaning.
1 problem(s) — sentinel meanings NOT met
```

Low because the gate fails loudly and cannot be shipped past. The one-clause meaning is available and
passes the conjunction test: *"no paid call is running against this generation."*

---

## What I could not break

- **⚠ The freeze trigger does NOT reject the marker — the brief's top suspicion is not a defect.**
  MEASURED on a `state = 'complete'` row:
  ```
  NOTICE:  P1a SET on complete row:   ACCEPTED
  NOTICE:  P1b CLEAR on complete row: ACCEPTED
  ```
  `video_generations_freeze()` (`schema/03_generations.sql:456`) freezes an explicit **denylist** —
  `card`, `md_hash`, `doc_version_major`, `produced_at`, `kind`, `generation_id` (`:481-486`) — not an
  allowlist, and `:430` records that `body_collected` sits deliberately outside it for the same reason.
  `in_flight_until` joins that side. Both the write and the clear pass `video_generations_freeze_trg`
  (`:498-500`) untouched. The `produced_at` future-bound at `:470` is not reached either, since the
  marker write does not touch it.
- **Crash lifecycle.** A lapsing timestamp is strictly better than `pending`: no reclaim, no attempt
  counter, no token, no permanently-uncollectable row. Nothing to attack here.
- **NULL means one thing** — *"no paid call is running against this generation"*. No conjunction, no
  second fact.
- **No new vocabulary collision.** `in_flight` is in `MECHANISM_STEMS`
  (`scripts/check-vocabulary-collisions.py:53-55`) but the check fires only on a stem appearing on more
  than one table, and `in_flight_until` would be the only such column. The `expires_at` /
  `lease` / `token` / `reserv` entries in `ALLOWED` go stale as designed when the artifact-side lease is
  deleted.
- **The four costed alternatives are honest.** The age-floor rejection quotes `04_artifacts.sql:893-896`
  accurately, and the objection it retires is a real one rather than a convenient one. The "derived TTL
  lives in `supabase/migrations/` where neither executable gate can see it" argument holds — I checked,
  and `verify-schema.sh` and `check-sentinel-meanings.py` both read only the spec `schema/` dir.
- **Item 2 is complete.** `grep -n source_generation_id` returns 19 occurrences in `04_artifacts.sql`
  (`:43 :87 :91 :107 :227 :320 :323 :330 :470 :644 :654 :661 :663 :671 :815 :816 :949 :950 :969`) and 6
  in `05_assert.sql` (`:166 :354 :356 :360 :362 :453`). Every one has a stated fate: the column and FK
  drop, `art_summary_has_no_source` becomes a constraint trigger, the `reserve_artifact_slot` sites go
  with the function, the `record_artifact` sites are (a), the ranking rung is item 3, the append-only
  branch is (b), and the assertions are (c)'s four sites — `:356` and `:362` fall inside the stated
  ranges. No occurrence is unaccounted for. (H2 is about *what* (a) says, not about coverage.)
- **Item 3's other two questions.** `count(*) > 1` does identify the merged set correctly, since the
  grouping key is the post-re-key `(owner_id, workspace_id||video_id, day)` and same-video/different-day
  rows are separate groups by construction. And the migration **is** idempotent under re-run: after the
  first pass each key has one row, so `count(*) = 1` and the clamp does not fire.
- **Reconciliation edits 1, 3, 4 and 5 are correct and introduce nothing.** The fourth
  `video_artifacts_free_uq` fate is genuinely gone from the "Dissolved" list; the concern-table row now
  names the marker; the headline qualification at `:23-28` is accurate about what the marker is not; and
  the one-column partition restatement is supported by both its tags —
  `schema/03_generations.sql:264` is the five-value `artifact_kind` enum and `04_artifacts.sql:94-95` is
  `art_paid_has_generation`, `(kind in ('summary','model','dig','digDeeper')) = (generation_id is not
  null)`, which is exactly *free ⇔ `generation_id is null`* over exactly five kinds.
- **Whole-document coherence on the four named axes is clean.** Grepping the ADR for `exclusivity`,
  `render_id`, `sha256` and per-kind language: no surviving claim of a per-kind successor, no live
  "exclusivity" guarantee (both sites are now corrections naming round 15 H2), the withdrawn render
  design appears only inside `~~strikethrough~~` at `:306-307` or in explicit removal notes, and
  `video_artifacts_free_uq` has exactly one fate — *it stays*.
- **New citation integrity (item 6).** Every tag added or moved in `00d0c83..HEAD` resolves and
  supports its claim: `lib/gemini-cost.ts:29`, `lib/gemini.ts:94`, `:252`, `:267`, `:82-84`,
  `0012_serve_model_charge.sql:64-65` (the reclaim `where lease_expires_at < now() and attempt_count <
  max`), `schema/03_generations.sql:264`, `schema/04_artifacts.sql:94-95`, and
  `scripts/check-sentinel-meanings.py:90-98` (the restated deletion trigger, which the same commit
  actually wrote). The `grep -rn "renew" supabase/migrations/*.sql` verification-by-absence at `:133-134`
  reproduces: zero hits. **0 wrong tags** among the new set, against round 14's 1-wrong / 1-partial /
  3-off-by-N and round 15's 1 created by the split.
- **The load-bearing claim, the paid/free partition, tenancy, `settle_serve_model`, the `doc_key`
  re-key** — not re-reviewed per the brief.

---

## Verdict

**NOT CONVERGED.**

**Blocking reason:** B1 — `video_generations.in_flight_until`, the only mechanism this ADR adds, has no
defined moment at which it can be written. Deleting `reserve_artifact_slot` removes the sole producer of
a pre-content generation row, and it is measured-impossible to insert one for `summary`/`dig` without
the `state = 'pending'` this ADR makes unreachable. Every available exit either restores something the
ADR says it deletes, conflates the new sentinel, reintroduces a per-kind successor, or shows the marker
to be unnecessary. The ADR must state **when the generation row is created**; that one sentence decides
whether option C is a mechanism or a dissolution.

H1 and H2 are independent of B1 and stand on their own: the invariant is verified only for the shortest
covered call, and the provenance fix contains two rules that cannot both be built.
