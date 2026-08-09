# Round 15 — Claude adversarial design review of the COORDINATION-ONLY ADR-0007

**Subject:** `docs/adr/0007-artifacts-are-an-append-only-log.md` @ `9d28d5e` (527 lines), branch
`fix/adr-0007-round-13-findings`. Targets: round 14's five fixes, and the scope split.

**Verdict: NOT CONVERGED.** 3 Blocking · 3 High · 5 Medium · 2 Low.

**Gate strength: NOT downgraded.** `verify-schema.sh` executed against the live local Postgres
(`supabase_db_youtube-playlist-summaries-cloud`, `postgres:17.6.1.147`) inside a rollback →
`ASSERTIONS_OK` / `ALL_STATEMENTS_OK` / `✅ schema verified (rolled back)`. Two additional structural
probes run in throwaway schemas inside `begin … rollback` (cascade-depth semantics, clamp
arithmetic). `check-docs.py`, `check-sentinel-meanings.py`, `check-vocabulary-collisions.py` all run
green. No repo-tracked file modified; `git status` clean of tracked changes throughout.

**Out of scope, honoured:** render *addressing* (no design proposed, the open conflation is not
reported as a finding), and round 14's "what I could not break" list (disjointness, partition
totality, tenancy, heartbeat coverage, the vocabulary-gate self-indictment) — none re-run.

**The core decision is not attacked here.** Nothing in this round bears on "delete the reservation
protocol." Every finding is in a fix, and every fix is from round 14 or the split — the signature
holds for a third round.

---

## BLOCKING

### B1 — the implementing-slice instruction list still mandates the WITHDRAWN `render_id` design, and contradicts Consequences three ways

**Claim.** ADR `:328-339` is a normative list addressed to the implementer ("The mechanical
consequences, for the implementing slice:") that survived the split unedited, and it instructs the
implementer to build the design the same document withdraws 60 lines earlier.

**Evidence — all four statements are in the file at `9d28d5e`:**

| Line | Text | Says |
|---|---|---|
| `:275-276` | ⛔ WITHDRAWN (round 14, B4/H1) ~~…carried in a `render_id` column…~~ | the design is dead |
| `:296` | "`video_artifacts_free_uq` **stays** until the render slice lands — see Consequences" | stays |
| `:330-333` | "is **not** simply deleted … it is **replaced** by uniqueness on `(workspace_id, video_id, slot, render_id)`" | **replaced** |
| `:352-357` | "**NOT deleted** … It is now **neither**, and that is the honest position" | neither |

`:334-335` compounds it: *"`art_paid_has_generation` becomes a two-way rule over two columns: a paid
kind has a `generation_id` and no `render_id`; a render has a `render_id`…"* — a schema change
premised entirely on the withdrawn column. `:336` then tells the implementer to *"Update the
`check-sentinel-meanings.py` entry to match this route"*, and `:339` (*"Free-ness becomes what it
always was: a property of the kind"*) is the withdrawn plan's conclusion.

This is round 14's B1 **exactly** — two copies of a normative statement at equal authority, one of
them refuted — reintroduced by the change that was supposed to remove the refuted material. The
brief asked whether `video_artifacts_free_uq` is "kept" consistently everywhere. It is not: the
document says *stays*, *replaced*, and *neither* in three places, and an implementer reading top-down
hits **replaced** last before Consequences.

**Fix.** Delete `:328-339` outright, or strike it through and replace with one line: *"the mechanical
consequences of dissolving the conflation belong to the render slice —
`2026-08-09-render-addressing-brief.md`."* `video_artifacts_free_uq` then has exactly one statement,
in Consequences.

---

### B2 — the `model` GC-floor successor expires before the paid call it must cover (MEASURED)

**Claim.** Round 14's B2 fix names *"the live `serve_model_charge` lease"* as the in-flight guarantee
for `model` after `pending` is deleted (ADR `:384`). Measured against the code, the lease's fixed
180 s TTL is **shorter than the worst case of the call it covers**, and there is no renewal — so the
generation becomes collectable while its paid Gemini call is still running. That is round 9's B1
returning on the one kind the fix exists for.

**Evidence — the serve path's in-flight window, in order:**

| Step | Site | Bound |
|---|---|---|
| lease taken, TTL 180 s | `lib/html-doc/serve-doc.ts:74` → `supabase/migrations/0012_serve_model_charge.sql:22` (`lease_ttl_seconds … default 180`) | starts the clock |
| input-cap preflight | `lib/gemini.ts:548` → `assertMagazineInputWithinCap` → `model.countTokens({…})` at `lib/gemini.ts:82-84` | **no `timeout`, no `signal` — unbounded** |
| generation, up to 3 attempts | `lib/gemini.ts:549` → `generateJson`, `retries = GENERATE_JSON_RETRIES` = **2** (`lib/gemini-cost.ts:22`), each `{ timeout: REQUEST_TIMEOUT_MS }` = **60 000 ms** (`lib/gemini.ts:94`, `:259`) | 180 000 ms |
| retry backoff | `lib/gemini.ts:252` (`baseDelayMs = 400`), `:267` (`baseDelayMs * 2 ** attempt`) | +400 +800 ms |
| blob upload | `lib/html-doc/serve-doc.ts:117` `writeModelEnvelope` | unbounded |

3 × 60 000 + 1 200 = **181 200 ms > 180 000 ms**, *before* the untimed preflight and *before* the
upload. And nothing extends the lease: `grep -rn "renew" supabase/migrations/*.sql` returns **zero
hits**, and `settle_serve_model` (`supabase/migrations/0020_reservation_release.sql:277-280`) sets
only `reserved_cents = 0, release_token = null` — it never touches `lease_expires_at`.

The ADR names both facts itself, at `:393`: *"no job, no staging, no renewal RPC, a 180 s TTL … and a
paid call on an HTTP GET"* — as the reason `model` is the worst kind to leave uncovered. It then
designates that same lease as the cover, without once comparing the TTL to the call's duration.
**A successor that is itself unreliable is worse than one that is absent, because it will be trusted**
— the brief's own words, and the measurement says this one is.

Consequence, in the ADR's own terms (`schema/04_artifacts.sql:888-892`): *"Money spent, bytes queued
for deletion, no error anywhere."*

Secondary, same mechanism: once the lease expires mid-call, `reserve_serve_model`'s reclaim clause
(`0012:64-65`, `where serve_model_charge.lease_expires_at < now() and … attempt_count <
max_serve_attempts`) admits a **second** paid producer for the same slot while the first is still
running. See H2.

**Fix — one of:**
1. give the serve lease a renewal RPC and heartbeat it from the serve path (this is the ADR's own
   `:203-205` revisit trigger firing *now*, not later); or
2. derive `lease_ttl_seconds` from the call's bound —
   `MAGAZINE_MAX_PASSES (=3, lib/gemini-cost.ts:29) × REQUEST_TIMEOUT_MS + backoff + a stated margin
   for the untimed preflight and upload` — and put a timeout on `countTokens`; or
3. stop using the lease as the GC floor and give `model` a real in-flight marker on
   `video_generations` that the sweeper reads (the honest per-kind successor, at the cost of a
   column).

Whichever is chosen, the ADR must state the comparison it currently omits: *the covering mechanism's
lifetime ≥ the covered operation's worst case.*

---

### B3 — dropping `source_generation_id` removes provenance's only writer and its only immutability guard; the consumer list is incomplete

**Claim.** Round 14's H4 fix decides `source_generation_id` "is DROPPED in the same change" (ADR
`:462`) and enumerates its consumers as *"load-bearing in two places"* (`:429-430`) plus the CHECK
(`:466`). The real count in the spec schema is **19 occurrences in `04_artifacts.sql` and 6 in
`05_assert.sql`**, and two of the omitted ones are load-bearing in ways that change the design.

**Evidence — every consumer, measured (`grep -n source_generation_id`):**

| Site | What it does | Fate under the ADR |
|---|---|---|
| `04:91-92` | the FK (round 5 M5) | named ✓ |
| `04:107` | `art_summary_has_no_source` CHECK | named ✓ |
| `04:814-816` | the ranking rung | named ✓ |
| `04:227`, `:320`, `:323`, `:330` | `reserve_artifact_slot` param + upsert | dies with the RPC ✓ (ADR `:348`) |
| **`04:471`, `:654-671`** | **`record_artifact`'s `p_source_generation_id` and its `coalesce(p_source_generation_id, v_src)` carry-forward** | **never mentioned — and `record_artifact` SURVIVES (ADR `:350`)** |
| **`04:969-975`** | **the append-only trigger's `raise … 'the PROVENANCE of a % paid row is immutable'` branch** | **never mentioned** |
| `05_assert.sql:166`, `:354-356`, `:360-362`, `:453` | four executable assertions incl. "a provenance UPDATE must raise" | never mentioned |

**Two consequences the ADR does not state, and both are structural:**

1. **Nothing writes the join table.** `record_artifact` is the only surviving producer of provenance
   (`04:471`, `:663`). Drop the column, keep the RPC unchanged, and `video_artifact_sources` is
   **always empty** — at which point *both* of the ADR's new guards go vacuously true: the ranking
   rung `not exists (… where source not current)` (ADR `:480`) and the GC `not exists` over the join
   table (ADR `:481`). Measured, on the general form: probe B below left an artifact row with zero
   source rows and `not exists(…) = true`.

   This is the **identical failure the ADR diagnoses 100 lines earlier** for the GC floor —
   *"the predicate goes vacuously true and the guard stops guarding without being deleted … a guard
   that never started, arriving by subtraction"* (`:371-376`) — committed inside the fix set that
   names it. Third occurrence of the signature, this time between two sections of the same round's
   own work.

2. **Provenance stops being append-only.** `04:970-975` today raises
   `'video_artifacts: the PROVENANCE of a % paid row is immutable (slot %, gen %)'` on any change to
   `source_generation_id` of a recorded paid row. The replacement is a child table with **no
   append-only trigger of its own** and `on delete cascade` on both FKs (ADR `:446-447`), so
   provenance becomes freely insertable and deletable — in the ADR titled *"artifacts are an
   append-only log."*

**Fix.** State, in the ADR and not in the slice: (a) `record_artifact` writes the join rows in the
same statement as the artifact row (and what happens on re-record — the `coalesce(…, v_src)`
carry-forward at `04:663` has no join-table analogue); (b) the append-only trigger's provenance
branch moves onto `video_artifact_sources`; (c) `05_assert.sql:354-356`, `:360-362` and `:453` are
rewritten, not deleted — `:453` is the executable proof of (b).

---

## HIGH

### H1 — `[VERIFIED: scripts/check-sentinel-meanings.py:90]` is wrong, and the string it quotes no longer exists

ADR `:315-318` quotes the sentinel entry as *"delete this entry when renders get a derived generation
id"* and tags it `[VERIFIED: scripts/check-sentinel-meanings.py:90]`.

**Measured:** `sed -n '90p' scripts/check-sentinel-meanings.py` → `        "\n"`. And
`grep -n "derived generation id" scripts/check-sentinel-meanings.py` returns **nothing** — the
commit under review (`9d28d5e`) rewrote that entry, replacing the quoted trigger with *"NEW TRIGGER:
delete this entry when the render-addressing slice lands."*

So the ADR quotes a dead string, at a line number that holds a bare newline, in the paragraph whose
subject is *"Deleting it would be the gate laundering an unfixed defect."* The same commit also makes
ADR `:336` (*"Update the `check-sentinel-meanings.py` entry to match this route"*) stale in the
opposite direction — the entry is already updated, to a different route (see B1).

Round 14's M5 audited all 57 tags and fixed five. This one was **created** by the split. In a
document whose entire method is these tags, a tag that resolves to the wrong line is the failure
mode, not a typo — the ADR says so itself at `:129-130`.

**Fix.** Requote the current text and retag to `:90-98` (the `⟳ 2026-08-09` block), and delete `:336`.

### H2 — the concern table still claims "exclusivity" for `model`, one row after that word was removed from `jobs`

Round 14's H2 fix reworded the execution row to *"stale-writer window **bounded, not excluded** …
merge-safety, not mutual exclusion"* (ADR `:85`). The row four lines below is still labelled
**`model` exclusivity + spend** (ADR `:92`).

The same argument applies to it, and B2 supplies the measurement: `reserve_serve_model`'s reclaim
clause (`0012:64-65`) admits a second producer as soon as `lease_expires_at < now()`, and the paid
call's worst case exceeds the 180 s TTL with no renewal. `serve_model_charge` therefore provides a
**bounded single-flight window**, exactly like the heartbeat — not exclusivity.

This propagates: falsifier #2 (ADR `:492-494`) tests for a producer path that *"breaks exclusivity"*,
a property the table's own execution row now disclaims. The ADR's one mechanically-checkable section
is checking for the breach of a guarantee it no longer claims to make.

**Fix.** Reword `:92` the way `:85` was reworded, and restate falsifier #2 in terms of *spend*
bounding (which falsifier #4 already does correctly) rather than exclusivity.

### H3 — the `least(sum, K-1)` clamp is a money change carrying an availability-only bound

The clamp applies to **every** row in the data migration, not only to rows that merge. Measured
(`select least(5,5-1)` → **4**; `select least(1,1-1)` → **0**):

- a video in **one** playlist whose model legitimately exhausted all `K = 5` attempts today is
  rewritten from 5 to 4, and gets a **new paid Gemini attempt** — `magazine_est_cents` charged to
  `serve_owner_budget` and `spend_ledger` (`0020:237-247`);
- `max_serve_attempts = 1` is permitted (`check (max_serve_attempts >= 1)`, `0012:21`); the clamp
  then yields **0**, a full reset of a genuinely exhausted document.

The ADR's honest-bound paragraph (`:170-173`) says *"only documents whose model is
absent/drifted/stale-version are affected at all"* — true, and it **omits the already-exhausted
subset**, which is precisely the set the clamp changes. Round 14's H3 was *a true rule about spend
read as a conclusion about availability*; the replacement states an availability bound for a change
that also moves money. Same substitution, one round later, in the fix for it.

The magnitude is small (≤ `magazine_est_cents` per affected doc, one day, clears at UTC midnight) —
this is High for the *unstated* class, not the amount.

**Fix.** Either state the money bound explicitly beside the availability bound, or apply the clamp
only where a merge actually occurs (`count(*) > 1` over the source rows), leaving single-source rows
byte-identical. The second makes the migration re-runnable with no effect at all, which also answers
the idempotency question the ADR never addresses.

---

## MEDIUM

**M1 — the `model` half of the GC-floor successor is outside both executable gates.**
`verify-schema.sh:9-12` builds its SQL from `"$DIR"/0*.sql` where `DIR=…/schema`; `mutate-schema.py:583`
copies only `SPEC / "schema"`. `grep -rn serve_model_charge docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/`
returns **zero hits** — the table lives in `supabase/migrations/`. So the one successor row that is
not staged-write ordering can never be asserted by `05_assert.sql` nor scored by the mutation
harness. This is the *same* blind spot the ADR self-indicts at `:207-227`
(`check-vocabulary-collisions.py`'s glob excludes `supabase/migrations/`), one section away and
unnoticed — an instrument whose green line covers less than the design it is certifying. State it, as
the ADR states the other one.

**M2 — `on delete cascade` makes an orphaned render vacuously current.** MEASURED (throwaway schema,
rolled back): with `sources → gen on delete cascade`, deleting a lone generation left
`gen=0 art=1 src=0` and `not exists(select 1 from src where art=200)` → **true**. So a render whose
provenance was cascaded away ranks as fully current and protects nothing. `restrict` prevented this;
`cascade` does not, and the ADR's claim at `:457-460` that the second `not exists` provides the same
protection covers GC-of-the-generation but **not** the ranking rung. No caller reaches it today —
`video_generations` appears in **no** file under `supabase/migrations/` (the table is spec-only) and
nothing deletes it except cascade — so Medium, not Blocking. **Fix:** write the invariant down now
("a generation row is deleted only by parent cascade, never individually"), because it is the
premise `cascade` rests on.

**M3 — the rewritten ranking rung does not define "current" for a non-summary source.** The rung it
replaces (`04:806-816`) compares `a.source_generation_id` against `s.generation_id` from
`video_summary_current` — one summary generation per (workspace, video). A `digDeeper` render's
sources include **dig** generations, for which `video_summary_current` has no row at all. The ADR's
replacement, *"the ranking rung becomes `not exists (select 1 … where source not current)`"*
(`:480`), leaves `not current` undefined precisely for the multi-source case that motivated the join
table. **Fix:** name the currency relation per source kind, or state that only summary-kind sources
participate in the rung.

**M4 — `[VERIFIED: 0012_serve_model_charge.sql:3]` does not support the claim it is attached to.**
ADR `:123-124` cites it for *"**no renewal** RPC"*; `sed -n 3p` reads
`-- (Option A+): lease single-flight + charge-per-attempt + K-attempt bound + no release RPC.` —
"release", not "renewal", a different mechanism. The cited assertion is also now **false**:
`settle_serve_model` (`0020:268`) *is* a release RPC. The renewal claim itself is true
(`grep -rn renew supabase/migrations/*.sql` → 0 hits), so this is a citation that resolves without
supporting — the exact class round 14's headline named. **Fix:** cite the absence directly (the grep)
or drop the tag.

**M5 — an in-scope claim is stated over an out-of-scope column.** ADR `:293-295` keeps, as one of the
three things the ADR *"still asserts about renders"*, the partition *"exactly one of `generation_id` /
`render_id` is non-null"*, tagged `03:264` + `04:94-95`. `render_id` exists in no schema; it was
introduced by the design withdrawn at `:276` and moved to the brief. The two tags describe a
**one-column** property (`(kind in (…)) = (generation_id is not null)`). Round 14 verified the
totality and I am not re-litigating it — the issue is that after the split the surviving claim names a
column whose home is now another document. **Fix:** state the partition in terms of the schema that
exists (*"free ⇔ `generation_id is null`, total over the five kinds"*) and let the brief carry the
two-column form.

---

## LOW

**L1 — the causal account of round-14 B3 is the wrong lemma; the operative fact is depth, not
RESTRICT.** ADR `:449-452` explains the account-deletion break as *"a RESTRICT child aborts a parent
delete even when that parent delete is itself a cascade step."* Measured, in two throwaway schemas
inside a rollback:

- a **one-hop** child with the *same* relationship survives: `wv → {gen, art}` both cascade, with
  `art.src → gen` as plain **NO ACTION** (the live `04:91-92` shape, which has no `ON DELETE`
  clause) — `delete from wv` **SUCCEEDED**, `wv=0 gen=0 art=0`;
- a **two-hop grandchild** fails even with plain **NO ACTION**: `sources.gen → gen` with no
  `ON DELETE` aborted with `ERROR: update or delete on table "gen" violates foreign key constraint
  "src_n_gen_fkey"`.

So the join table breaks the cascade because it sits one hop deeper than the column it replaces, and
`on delete no action` was **not** an available alternative either. The fix (`cascade`) is right; the
stated reason invites the obvious objection *"then why doesn't the existing `source_generation_id` FK
break account deletion today?"* — which has a good answer the ADR does not give.

**L2 — `:517` claims more than the row it cites.** *"Two producers after a lease expiry **do not
double-append**, for the job kinds — the heartbeat-abort row of the concern table is the mechanism."*
That row now says the window is *bounded, not excluded*, and stale writes are tolerated *because they
are idempotent*. Under the ADR's own central claim two producers with different generation ids append
**two rows**, by design. "Do not double-append" is neither what the mechanism provides nor what the
design wants. **Fix:** "do not double-*charge* beyond the documented residual", or "their appends are
merge-safe."

---

## What I could not break

Recorded so round 16 does not re-spend the effort.

- **The split is not lossy.** Every piece carved out of the ADR landed in
  `docs/superpowers/specs/2026-08-09-render-addressing-brief.md`: the three-constant enumeration
  table (`:70-72`), the RULED-OUT list with both refutations (`:59-108`), §8's key-alone rule
  (`:117`), the probe-key/identity split (`:115`), and the open questions (`:148-165`). No evidence
  was destroyed. B1 is the *reverse* problem — material that should have moved and did not.
- **The headline is still honest.** *"nothing coordinates writers"* is qualified in the first ten
  lines (`:20-24`, qualification 1 names `model` and `serve_model_charge` explicitly). A reader
  cannot reach the concern table without meeting the exception.
- **The ADR index and doc gates are consistent with the split.** `check-docs.py` passes; its
  `check_adr_index` tightening (`:105-113`) is a genuine fix — the old bare-filename regex read the
  date-named brief as a missing ADR, and the new `\]\((\d{4}-[a-z0-9-]+\.md)\)` matches link targets
  only. `check-sentinel-meanings.py` and `check-vocabulary-collisions.py` also pass.
- **The `check-sentinel-meanings.py` rewrite is correct in substance** (only its ADR citation is
  wrong — H1): the old trigger *"when renders get a derived generation id"* could never fire after
  round 13 B2, and replacing a dead trigger beats leaving one that rots.
- **`artifact_id` exists**, so the join table's `video_artifacts(artifact_id)` FK is well-formed —
  `04:81-82`, surrogate PK with two partial uniques.
- **Every other `[VERIFIED:]` tag I spot-checked resolves and supports**: `0012:21` (K=5), `:22`
  (180 s), `:53` (`doc_key` formula), `:65`, `:80`; `0020:213`, `:237-247`; `03:264`; `04:91-92`,
  `:94-95`, `:107`, `:164-165`, `:898-900`; `…-design.md:874`, `:891-893`, `:2445-2452` (the
  *"G1's cap becomes N times looser"* quote is verbatim at `:2451`), `:2464`, `:2753`.
- **The re-key coupling holds.** `doc_key` really does carry the playlist (`0012:53`, `0020:213`)
  while the artifact slot does not (`03_generations.sql:64`), so the N-leases-one-slot argument at
  `:132-149` stands as written.
- **`settle_serve_model` is idempotent against a stale or forged token** (`0020:279-281`, matches on
  `release_token = p_token` and returns false when not found) — I could not turn the release path
  into a double-refund.

---

## Verdict

**NOT CONVERGED.**

**Blocking reason:** three defects that would ship wrong. **B1** — the implementer's own instruction
list mandates a withdrawn design and gives `video_artifacts_free_uq` three different fates in one
document. **B2** — the `model` GC-floor successor's 180 s lease is measurably shorter than the paid
call it covers, with no renewal, which re-opens round 9's B1 on the exact kind the fix was written
for. **B3** — dropping `source_generation_id` leaves the join table with no writer and no
immutability rule, making both new guards vacuously true, which is the ADR's own diagnosed failure
mode reproduced inside its own fix set.

**All three are in round 14's fixes or the split.** The core decision — delete the reservation
protocol — was not attacked this round and remains unbroken after three design reviews. The
signature ("each round's fix causes the next round's defect") is now on its **third** consecutive
round, and B3 and B1 are both "two sections that must agree and never mention each other," which is
what round 14's M4 already named. That is a reconciliation-pass problem, not a design problem — but
it has now survived being named twice.
