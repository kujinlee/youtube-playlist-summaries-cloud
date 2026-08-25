---
status: accepted 2026-08-24 (M3) — supersedes the reservation protocol of ADR-0006's spec (handoff
  item 4). Its stated dependency is now DISCHARGED: ADR-0006 was accepted the same day, and this ADR
  said the two stand or fall together. Its own five design reviews (13-17) are all answered below.
  ⚠ ACCEPTED IS NOT IMPLEMENTED for the schema half — the coordination implementation landed in
  `1a7c076`, but the schema it edits has never run as a migration. The ONE residue round 17 assigned
  to a later slice, §5.1's now-false "a crash before recording leaves nothing", was corrected in the
  design spec on 2026-08-24; the orphan it names is covered by §8's grace period, which remains
  SPECIFIED AND UNIMPLEMENTED (no sweeper exists; `BlobStore` exposes no object age).
revised: 2026-08-09. Rounds 13, 14, 15, 16, 17 — five DESIGN reviews, all answered here.
  SCOPE: COORDINATION ONLY. Render addressing was SPLIT OUT (user decision) to
  docs/superpowers/specs/2026-08-09-render-addressing-brief.md (backlog #25) after two designs were
  refuted in two rounds.
  The GC floor needs NO successor: round 16 MEASURED that after these deletions no `video_generations`
  row exists during a paid call, so nothing is collectable and the window closes itself. Rounds 14-16
  proposed three covers (per-kind table, `serve_model_charge` lease, an `in_flight_until` marker); all
  three are withdrawn. What still needs protecting is the ORPHAN BLOB, via §8's reinstated grace period.
  The core decision — delete the reservation protocol — has survived FIVE design reviews unbroken;
  every finding in rounds 14-17 was in a FIX, not in the decision.
  See docs/reviews/spec-blob-addressing-r1{3,4,5,6,7}-coordinator.md
---

# Artifacts are an append-only log; nothing coordinates writers, because writers do not contend

`video_artifacts` records what was produced. It has **no lease, no token, and no attempt counter**.
Paid artifacts are addressed under a generation id chosen before the content. Producer coordination
comes from the job queue's existing lease/heartbeat; "which artifact is current" from the ranking view
that already exists.

⚠ **Nothing survives to coordinate writers — not even a GC marker.** Three rounds tried to give the
garbage collector an in-flight signal; round 16 measured that it needs none, because after these
deletions **no generation row exists while a paid call runs** (see *When is a `video_generations` row
created?*). The bytes written during that window are orphans, and §8's grace period is the
mechanism for them — **specified, not yet implemented** (round 17 H2).

**Three qualifications, stated up front rather than buried:**

1. **The `model` kind is a paid producer with no job**, arbitrated by `serve_model_charge` instead.
   The one-mechanism-per-concern rule has this standing exception, and deleting
   `video_artifacts_inflight_uq` requires re-keying `doc_key` in the same slice. *(Round 13 B1.)*
2. **The free/paid distinction does not vanish** — it moves out of the write path into how an id is
   minted (UUID-before-content for paid, content-derived for free). Smaller and more honest, but not
   zero.
3. ⚠ **Render addressing is NOT settled by this ADR.** Two successive designs failed design review in
   two consecutive rounds, which is this project's own escalation criterion. The render half is carved
   out pending its own design pass; **everything else here stands on its own.** *(Round 14 B4/H1.)*

We decided this because the reservation protocol built alongside ADR-0006 produced a Blocking or High
in **six consecutive adversarial rounds**, and four of those defects were introduced by the previous
round's own fix. Every other component of that spec converged and stayed converged. The problem was
not any of the twelve defects; it was that the mechanism re-solved a problem ADR-0006 had already
dissolved.

## The load-bearing claim

Stated in one sentence so a reviewer can attack it directly rather than hunting for it in prose:

> **A producer and a replicator writing the same slot cannot collide, because the producer writes a
> NEW generation and the replicator copies an EXISTING one, and the address is derived from the
> generation id — so their writes land on different keys and append different rows.**

If that is false, this ADR is wrong and the reservation protocol should be restored. It rests on:

- `[VERIFIED: lib/cloud-sync/sync-run.ts:372-394]` — `transferClassA` copies an existing body between
  replicas. No Gemini call, no payment. Sync **replicates**; it does not produce.
- `[VERIFIED: docs/adr/0006]` + `schema/04_artifacts.sql:181-187` — the blob key is
  `<ws>/videos/<video>/<generation>/…`, derived from the generation id.
- `[VERIFIED: schema/04_artifacts.sql:189-190]` — `video_artifacts_paid_uq` keys on
  `(workspace, video, slot, generation)`, so two generations of one slot are two rows, never a
  conflict.

### ⚠ The claim is TRUE and it is NOT sufficient — read this before using it (round 13, B1)

Round 13 confirmed the claim above by measurement and then showed that **proving it is not the same as
proving there is nothing to coordinate.** Round 5 had already measured the reason
`[VERIFIED: schema/04_artifacts.sql — round 5's reason was DELETED with the reservation; the surviving statement of it is 05_assert.sql:453-455]`:

> *"without it, two writers insert `pending` for the same slot under their OWN generation ids, both
> succeed (different ids ⇒ the paid unique does not collide), and both call Gemini. `count(*) = 2`."*

Landing on different keys is precisely **why both writers succeed**, and therefore why both pay. The
contended resource was never the key — it was the **money**. This ADR proves disjointness of *writes*;
what a slot needs is exclusivity of *paid work*, which is a different property with a different owner.

So the claim licenses exactly one thing: deleting the reservation as a **write-coordination**
mechanism. It licenses nothing about spend. Every row of the table below that mentions payment must
name a money mechanism by `file:line`, and this ADR is wrong wherever it substitutes one for the other.

## What already serves each concern

This table is the check that was never run. **Round 13 found two of its rows false**; they are
corrected here, and the correction is why the "exactly one" rule below now carries a stated exception
rather than being quietly untrue.

The rule this table is meant to enforce: every concern has exactly one mechanism, and every mechanism
serves exactly one concern. **`model` is a standing exception — see the next section.**

| Concern | Mechanism | Evidence |
|---|---|---|
| producer **enqueue** dedup | `jobs_idem_active` — one job per (owner, playlist, video, section, kind, version) whose status is `queued`/`active`/**`completed`** (the predicate includes the terminal `completed`, so a finished job still blocks a re-enqueue) | `[VERIFIED: 0009_job_playlist_identity_and_worker_persistence.sql:11-13]` |
| producer **execution**: stale-writer window **bounded, not excluded** | lease + heartbeat → `leaseLost.abort()`, re-checked immediately before the irreversible write. Stale writes are tolerated because they are **idempotent** — merge-safety, not mutual exclusion. Full lease-fencing of `persist_summary` is **deferred** | `[VERIFIED: lib/job-queue/worker-runner.ts:48-51, :30-32]` + `[VERIFIED: lib/job-queue/summary-handler.ts:166-170]` |
| pay-at-most-once **accounting** | `jobs.ever_metered` + `reserved_cents`, durable across retries — prevents an under-count on release, **not** a second real charge | `[VERIFIED: 0020_reservation_release.sql:25-32]` |
| at-most-once **spend** | heartbeat-abort (above) + per-kind attempt bounds in `guardrail_config`. **Bounded, not zero** — a reclaim after the Gemini call has already billed is a known residual | `[VERIFIED: lib/job-queue/summary-handler.ts:166-169]` |
| execution liveness | job lease + heartbeat + `sweep_expired_leases` | `[VERIFIED: 0009_…:63-78]` |
| stable addressing | generation id → blob key | ADR-0006 |
| which artifact is current | `video_artifacts_current` ranking | `schema/04_artifacts.sql` |
| what may be deleted | `video_generations_collectable` + `body_collected`; no in-flight floor is needed, because no generation row exists during a paid call (round 16 B1). Orphan **blobs** in that window need §8's grace period, which is **specified but UNIMPLEMENTED** — there is no orphan sweeper in any code, and `BlobStore` exposes no object age (round 17 H2) | round 8; `…-design.md:1995-1996` **(not implemented)** |
| **`model`: bounded single-flight + spend** | `serve_model_charge` lease, **not** `jobs` — see the next section. ⟳ *Round 15 H2: this row said "exclusivity" one row after that word was removed from `jobs` for being unsupportable. The reclaim clause `[VERIFIED: 0012_serve_model_charge.sql:64-65]` admits a second producer the moment the lease lapses, which round 15 B2 measured happens mid-call. It is a bounded window, not exclusion* | `[VERIFIED: 0012_serve_model_charge.sql:7-13, :53]` |

**Two corrections round 13 forced, recorded so they are not re-lost.** `jobs_idem_active` dedupes
**enqueues**; it says nothing about how many workers execute the one job it admits, so it could never
have provided execution exclusivity. And `ever_metered`/`reserved_cents` govern *accounting*, not
*spend* — the code says so in its own words at `summary-handler.ts:166-169`. Both rows previously
claimed a guarantee their mechanism does not make.

The reservation protocol re-implemented the first four concerns in a second vocabulary — `lease_token`,
`lease_expires_at`, `lease_attempts`, `reserved_by` against `jobs`' `lease_token`,
`lease_expires_at`, `attempts`, `locked_by` — and **every defect of rounds 7–12 lived in the seam
between the two**.

## The `model` exception — a paid producer that has no job (round 13, B1)

This ADR's falsifier list asks for *"a second producer path that does not go through `jobs`."* One
exists, it was missed by the first draft, and it is stated here rather than left for the implementing
slice to discover.

**The magazine `model` is generated on the serve path, by an HTTP GET, with no job anywhere in the
call graph.** `[VERIFIED: lib/html-doc/serve-doc.ts:112]` calls `generateMagazineModel` — a paid
Gemini call — reached from `[VERIFIED: lib/html-doc/serve-summary-core.ts:105]`, which serves both
`app/api/html/[id]/route.ts` and `app/api/pdf/[id]/route.ts`. `model` is a **paid** kind:
`[VERIFIED: schema/04_artifacts.sql:28]` maps `slot='model'` → `kind='model'`, and
`art_paid_has_generation` `[VERIFIED: schema/04_artifacts.sql:119-120]` puts it in the paid set beside
`summary`, `dig`, `digDeeper`.

Its arbiter is a **third coordination vocabulary** — `serve_model_charge`, keyed
`(owner_id, doc_key, day)` `[VERIFIED: 0012_serve_model_charge.sql:7-13]` with a lease and an
`attempt_count` bounded by `max_serve_attempts` (default **5**)
`[VERIFIED: 0012_serve_model_charge.sql:21]`, enforced at `[VERIFIED: 0012:65]` and `[VERIFIED: 0012:80]`.
It has a 180 s TTL `[VERIFIED: 0012_serve_model_charge.sql:22]` and **no renewal RPC** — verified by absence:
`grep -rn "renew" supabase/migrations/*.sql` returns zero hits. ⟳ *Round 15 M4: this previously cited
`0012:3`, which says "no **release** RPC" — a different mechanism, and a claim now false anyway since
`settle_serve_model` IS a release RPC. A citation that resolves without supporting.*

⟳ *Round 14 M5: the three tags in this paragraph were previously one tag pointing at `0012:24`, which
is a comment header — the TTL is at `:22`, the attempt bound at `:21`/`:65`/`:80`, and "no release
RPC" at `:3`. A citation audit of all 57 `[VERIFIED:]` tags in this document found 1 wrong, 1
partial-wrong, 3 off-by-N, and 1 claim-vs-code mismatch; all are corrected. In a document whose entire
method is these tags, a tag that resolves to the wrong line is the failure mode, not a typo.*

### The coupling that makes the deletion safe, and without which it is a money regression

`doc_key` is `p_playlist_id::text || '/' || p_video_id` `[VERIFIED: 0020_reservation_release.sql:213]`
— it carries the **playlist**. The artifact slot `(workspace_id, video_id, slot)` does not, because
`workspace_videos` is keyed `(workspace_id, video_id)` `[VERIFIED: schema/03_generations.sql:64]`.

**One video in N playlists of one workspace therefore holds N independent serve leases against ONE
model slot** — no lease expiry required. Round 13 measured that `video_artifacts_inflight_uq` is the
only thing stopping two paid model producers today (`W2 → busy`; dropping the index yields
`paid_model_rows_in_one_slot = 2`). The spec already found this as round-1 H5 — *"G1's cap becomes N
times looser"* `[VERIFIED: …-design.md:2445-2452]` — and specced the re-key at `:2464` and `:2753`,
where it has sat unimplemented.

> **Therefore: `doc_key` is re-keyed to `(workspace_id, video_id)` in the SAME slice that deletes
> `video_artifacts_inflight_uq`. Shipping the deletion without the re-key is a money regression, not a
> simplification.** The re-key touches one line in each of the three migrations that recreate the RPCs
> — `0012:53`, `0014:47`, `0020:213` — plus a data migration and
> `tests/integration/serve-doc-materialize.test.ts:78`, which hardcodes the formula.

**Data migration — `least(sum(attempt_count), max_serve_attempts - 1)`, applied ONLY where a merge
actually occurs (`count(*) > 1` over the source rows). Single-source rows are left byte-identical.**

⟳ **Round 14 H3 — this was plain `SUM`, and the justification was wrong.** Both reviewers found it.
The rule quoted to license SUM — *"over-count is safe, under-count is the bug"*
`[VERIFIED: lib/html-doc/serve-doc.ts:105-109]` — is scoped to **refunding a single attempt whose
metering status is uncertain** ("when in doubt, do not refund"). It says nothing about merging
independent counters, where over-counting costs no money and instead **denies service**:

- `attempt_count` is a **retry/lease bound, not a spend ledger.** Spend is accounted separately, in
  `serve_owner_budget` and `spend_ledger`, both incremented by `magazine_est_cents`
  `[VERIFIED: 0020_reservation_release.sql:237-247]`. So SUM buys no money protection at all.
- `max_serve_attempts` defaults to **5** `[VERIFIED: 0012_serve_model_charge.sql:21]`. A video in
  three playlists at two attempts each SUMs to 6 > 5.
- The result is `attempts_exhausted` → **HTTP 503** `[VERIFIED: lib/html-doc/serve-summary-core.ts:121]`
  — and this is **the one serve outcome with no stale fallback.** D5's title-stable stale serve is
  reachable only from `owner_over_budget` `[VERIFIED: lib/html-doc/serve-doc.ts:90-95]`. The `model`
  exception above cites that D5 fallback as a reason the serve path deserves its exception; SUM then
  routed users into the sibling branch that lacks it.

The clamp keeps the no-under-count intent while guaranteeing at least one attempt survives the
migration. **Bound, stated honestly — BOTH bounds, availability AND money:**

- *availability:* a fresh model short-circuits before the reserve
  `[VERIFIED: lib/html-doc/serve-doc.ts:56-57]`, so only documents whose model is absent/drifted/
  stale-version are affected at all, and rows are per-day, so anything missed clears at UTC midnight.
- *money:* ⟳ **round 15 H3 — the clamp MOVES MONEY and the first version said only the above.**
  Applied to every row, `least(5, 4) = 4` rewrites a single-playlist document that legitimately
  exhausted all `K = 5` attempts down to 4, **granting it a fresh paid Gemini attempt**
  (`magazine_est_cents` against `serve_owner_budget` and `spend_ledger`
  `[VERIFIED: 0020_reservation_release.sql:237-247]`); and `least(1, 0) = 0` fully resets an
  exhausted document, since `max_serve_attempts >= 1` is permitted
  `[VERIFIED: 0012_serve_model_charge.sql:21]`. **Restricting the clamp to rows that actually merge
  removes the single-source case completely**, and bounds the merged case to at most one extra paid
  magazine call per merged key, once, at migration time. ⟳ *Round 16 M1: the first version said
  "removes this entirely", which is false — a video in two playlists with one key at `attempt_count = 5`
  (exhausted) and its sibling at 1 still has `count(*) = 2`, so `least(5 + 1, 4) = 4` revives it. The
  restriction shrinks the affected population from every row to multi-playlist rows; it does not empty
  it. A completeness claim on the money path, in the paragraph whose own lesson is "name what the rule
  ranges over" — the third instance of that error, caught by the round that came looking for it.* The
  migration is **idempotent under re-run**: after the first pass each key has one row, so `count(*) = 1`
  and the clamp does not fire.

**This is the third round in which the same substitution appeared, and it is recorded rather than
quietly fixed.** Round 13 B1: a true lemma about *writes* read as a conclusion about *money*. Round 14
H3: a true rule about *spend* read as a conclusion about *availability*. Round 15 H3: **the fix for
that** stated an availability-only bound for a change that also moves money. The rule the ADR needs is
not "quote a rule" but **"name what the rule ranges over, and check that it is what you are deciding."**

**Recorded because it is the pattern, not the instance:** round 13's B1 found this ADR proving a true
lemma about *writes* and reading it as a conclusion about *money*. This paragraph took a true rule
about *spend* and read it as a conclusion about *availability* — the same substitution, made in the
fix for the first one. A citation that **resolves** is not a citation that **supports**.

### Why `model` is not routed through `jobs` (decided 2026-08-09, user)

Routing it through `jobs` would make the concern table true with no exception, and it remains the
better end state. It was **not** chosen for this slice because it is a product change, not a refactor:

- a first view would wait on a queued job, or return a "generating…" state needing polling/SSE — a
  frontend change;
- the anonymous share path is **read-only by invariant** and never generates
  `[VERIFIED: app/s/[token]/route.ts:81]`, so it depends on the model already existing. Making
  generation asynchronous reopens backlog #14 (share-before-view) in a new form;
- it would discard six earned serve outcomes `[VERIFIED: lib/html-doc/serve-doc.ts:80-98]` —
  `denied`, `in_flight` single-flight, `attempts_exhausted`, `at_capacity`, `owner_over_budget`
  (which serves a **title-stable stale** model rather than failing, spec D5), `reserved`. A job queue
  has no equivalent of serve-stale-rather-than-fail, and that was a product decision;
- G1's per-owner serve budget `[VERIFIED: 0014_serve_owner_budget.sql]` is a fairness cap on the
  serve path specifically, deliberately separate from the job daily cap.

The re-key is not wasted work if `jobs` wins later: a workspace-scoped key is what that design needs
anyway.

**Status: STRUCTURAL, not transitional.** `model` has two mechanisms because it has two call shapes,
and this ADR says so rather than letting the schema quietly contradict a rule stated in prose.
**TRIGGER for revisiting** (a Parking-Lot item without one rots): when the serve path next needs
either lease renewal or a bounded wait — i.e. when a magazine call routinely exceeds the 180 s TTL, or
when first-view latency becomes a product complaint. At that point `serve_model_charge` is
reimplementing the job queue and should be replaced by it.

### ⚠ The vocabulary gate cannot see this collision — MEASURED 2026-08-09

`serve_model_charge` duplicates `jobs`' coordination vocabulary almost exactly — a lease, an
`lease_expires_at`, an `attempt_count`, a per-attempt token — which is the precise smell
`scripts/check-vocabulary-collisions.py` was built for one day earlier (PR #63).

**It does not fire, and it cannot.** `[VERIFIED: scripts/check-vocabulary-collisions.py:44,88]` scans
only `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/0*.sql`.
`serve_model_charge` lives in `supabase/migrations/` and is outside its glob. Run today the script
reports *"columns scanned: 79 … ✅ no unjustified duplicate mechanism"* — a green line produced by a
tool that cannot see the shipped schema where the largest live duplicate sits.

This is the same shape the script exists to catch, one layer out: **an instrument whose success line
claims more than its input covers.** Compare round 12's Medium — a guard ratchet printing *"every
guard classified"* while omitting RLS policies — and the two-sandboxes note in `docs/plugins.md`. The
inventory was right; the scope was wrong.

**Do not treat the green line as evidence that `model`'s duplication is acceptable.** It is
acceptable because of the reasoning above, which a human wrote and a human must re-check. Widening the
script's glob to `supabase/migrations/` is follow-up work, and until it happens the script's verdict
covers the spec schema only.

## Considered options

- **Keep patching the reservation (status quo, rejected).** Twelve rounds, five successive
  credentials, none surviving a round. Rejected because the failures were not independent: the fence
  had to be PERMISSIVE so a reclaimed writer could still record its paid work, and STRICT so a
  stranger could not complete a generation. Those are two different coordination philosophies —
  append-only-plus-merge, and mutual exclusion — wired to one SQL predicate. No credential resolves
  that, which is why five did not.

- **Route every write through the job queue (rejected — but the argument is narrower than it looked).**
  Attractive until checked: sync replicates rather than produces
  `[VERIFIED: lib/cloud-sync/sync-run.ts:372-394]`, so enqueueing a job would mean *generating*
  something that already exists. The producer/replicator asymmetry is real and must be modelled, not
  flattened.
  ⟳ **Round 13 correction:** this rejection covers *replication only*, and the first draft silently
  extended it to every write. It does **not** transfer to the `model` serve path, which genuinely
  produces — so routing *that* through `jobs` was a live option, evaluated on its own merits, and
  rejected for product reasons recorded in the `model` section above. A rejection argument that is
  sound for one caller and reused for another is the same substitution B1 caught.

- **Append-only log, no coordination (chosen).** The writers do not contend (see the load-bearing
  claim), so there is nothing to coordinate. What remains — *which of several appended rows is
  current* — is a merge question, and the ranking view is already the merge function.

## Renders keep their special case — for now, and deliberately

This ADR was drafted believing it would dissolve the render conflation as well. **It does not**, and
saying so plainly is the point of this section.

`generation_id is null` currently encodes **two independent facts**:
`[VERIFIED: schema/04_artifacts.sql:119-120]`

```sql
constraint art_paid_has_generation check (
  (kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))
```

— "this is free" (a *money* property) and "this address may be overwritten" (an *addressing*
property). That conflation is the same root cause as nullable `corrections_hash` ("no corrections" vs
"never computed") and absent-vs-failed-to-read, and it produced five of the twelve rounds' findings.

Two designs were written to dissolve it. **Both were refuted, and both are withdrawn:**

> ⛔ **WITHDRAWN (round 13, B2).** ~~A render gets a derived generation id:
> `hash(source_generation_ids, GENERATOR_VERSION)`.~~
>
> ⛔ **WITHDRAWN (round 14, B4/H1).** ~~A render's identity is `sha256(rendered bytes)`, carried in a
> `render_id` column, and the key keeps its existing `<ws>/videos/<vid>/renders/…` prefix.~~

### ⛔ Render addressing is OUT OF SCOPE — split to its own slice (user decision, 2026-08-09)

Two designs were refuted in two consecutive rounds — round 13's `hash(source_generation_ids,
GENERATOR_VERSION)` and round 14's `sha256(rendered bytes)`. That meets this project's own escalation
criterion (*two consecutive rounds whose findings were caused by the previous round's fixes ⇒
escalate from fix to redesign*), so **this ADR does not attempt a third design.**

**Everything — the problem, both refutations with evidence, the constraints any design must satisfy,
the ruled-out list, and the open questions — moved to
[`docs/superpowers/specs/2026-08-09-render-addressing-brief.md`](../superpowers/specs/2026-08-09-render-addressing-brief.md)**
(backlog #25). It awaits a Phase 1 design pass, which neither previous attempt ever had: both were
written as a single paragraph while fixing something else.

**What this ADR still asserts about renders — and it is only this:**

- The paid/free **partition** is sound and total **as the schema states it today**: *free ⇔
  `generation_id is null`*, over exactly the five kinds `[VERIFIED: schema/03_generations.sql:264]`
  `[VERIFIED: schema/04_artifacts.sql:119-120]`. It is the **address** that is unresolved, not the
  partition. ⟳ *Round 15 M5: this previously stated the partition as "exactly one of `generation_id` /
  `render_id`", naming a column that exists in no schema and whose home is now the brief. The
  two-column form belongs there; the one-column form is what these two tags actually verify.*
- `video_artifacts_free_uq` **stays** until the render slice lands — see Consequences.
- Nothing in the reservation deletion depends on render addressing. The two collide on one column,
  not on one question: the reservation is a **coordination** defect, render addressing an **identity**
  one.

### Does the founding conflation dissolve? NOT YET — and this is the honest state (round 14)

This ADR exists because `generation_id IS NULL` carries **two** meanings: *"this is free"* (money) and
*"this address may be overwritten"* (addressing). The first draft dissolved it by giving renders a
generation id (refuted, round 13 B2). Round 13 claimed it dissolved via `render_id` instead.

**Round 14 B4 refuted that too, and the reason is exactly the conflation's second half.** The argument
was: *"a render addressed by `sha256(rendered bytes)` is immutable, so renders stop being
overwritable."* But renders were never *addressed by* it — the key was unchanged, so renders **remain
overwritable**. The second meaning does not go away, and therefore the conflation does not dissolve.

**What this means, stated plainly rather than papered over:** the ADR's founding motivation is
**unmet** until render addressing is settled. `scripts/check-sentinel-meanings.py`'s entry for
`art_paid_has_generation` — whose deletion trigger now reads *"delete this entry when the
render-addressing slice lands"* `[VERIFIED: scripts/check-sentinel-meanings.py:90-98]` — must **stay**
for now (⟳ round 15 H1: this previously quoted the entry's OLD trigger at a line that now holds a
bare newline, a wrong tag CREATED by the split), and must not be deleted
on the strength of either withdrawn plan. Deleting it would be the gate laundering an unfixed defect.

**What is settled**, and survives whatever render addressing turns out to be: the paid/free
**partition** — *free ⇔ `generation_id is null`* (the two-column `render_id` form belongs to the
brief) — is total across all
five kinds (see the Renders section). The partition is sound; the address is not. Those are separable,
and only the second is open.

⚠ This is the strongest argument for the scope split: **the reservation deletion does not depend on
the conflation dissolving.** The conflation is a defect in *addressing*; the reservation is a defect
in *coordination*. Round 13 bundled them because the same `NULL` participates in both.

⟳ **Round 15 B1 — a normative instruction list stood here and has been deleted.** It told the
implementer to build the `render_id` design that this document withdraws 60 lines earlier, and it gave
`video_artifacts_free_uq` a second, contradictory fate (*"replaced"*, against Consequences' *"not
deleted"*). That is round 14's B1 reintroduced by the change meant to remove the refuted material.

**The mechanical consequences of dissolving the conflation belong to the render slice**
(`2026-08-09-render-addressing-brief.md`), not here. This ADR says exactly one thing about
`video_artifacts_free_uq`, in Consequences: **it stays.**

**Dissolved rather than fixed**, and this is the measure of the decision: round 8's free-render
reconciler; round 8/9's `NULL = NULL` unreachable short-circuit; round 9's tenant-confinement gap;
round 10's free-lease theft; round 11's typed `busy`; round 12's once-in-a-lifetime free reservation.
Plus the whole free branch of `record_artifact`. ⟳ *Reconciliation pass, 2026-08-09:
`video_artifacts_free_uq` was listed here too, which would have been its FOURTH fate in one document.
It is NOT dissolved — see Consequences: it stays until the render slice lands. Round 15 B1 caught three
of these; this one it missed, and only a pass asking "which sections constrain each other" found it.*

## Consequences

**Deleted:** `reserve_artifact_slot`, `renew_artifact_lease`, the lease columns on `video_artifacts`,
`reserved_by` on `video_generations`, and the `pending` artifact state. `record_artifact` becomes an
append with a typed outcome and no fence — **and gains the generation INSERT that
`reserve_artifact_slot` used to perform; see REPLACED below, without which nothing creates a generation
row at all** (round 17 B1).

**ADDED — exactly one table, and no columns.** ⟳ *Reconciliation pass 2026-08-09 added this because
the list recorded every deletion and no addition. ⟳ Round 16 L1 then caught it calling a table a
column, and round 16 B1 removed the column entirely.*
`video_artifact_sources`, the provenance join table, which **replaces** the dropped
`source_generation_id` column rather than adding to it — so this ADR's net schema effect is one
column removed, one table added, and everything else deleted.

**REINSTATED:** §8's **specified but UNIMPLEMENTED** grace period, as an age predicate on orphan blobs.
It was dropped on a premise (*"a blob written but not yet published is unreferenced — that state no
longer exists"*) that these deletions falsify. ⟳ *Round 17 H2: this said "the orphan sweeper's existing
mechanism". §8's grace period is real and reinstatable `[VERIFIED: …-design.md:1995-1996]`, but §8's own
opening says "There is no GC of superseded blobs anywhere… GC is currently impossible"
`[VERIFIED: …-design.md:1949-1953]`, and no orphan sweeper exists in any code. Calling it "existing" was
the ADR's own diagnosed failure — an instrument whose success line claims more than its input covers.*

**⚠ REPLACED — `record_artifact` INSERTs the generation row (round 17 B1, MEASURED).** This is the
sentence the round-16 dissolution rested on and never wrote.

> `record_artifact` **inserts** `video_generations` — born `state='complete'` — and then inserts the
> artifact row that FKs it, in one transaction. The FK `[VERIFIED: schema/04_artifacts.sql:110-111]`
> forces that order.

The RPC already accepts every column required: `p_card`, `p_md_hash`, `p_doc_version_major`,
`p_produced_at`, `p_kind` `[VERIFIED: schema/04_artifacts.sql:354-359]`. Today its generation write is
an **UPDATE** `[VERIFIED: schema/04_artifacts.sql — that UPDATE is DELETED by T1; the INSERT that replaced it is at :442-447]` gated on `g.state = 'pending'` *and* `g.reserved_by = p_token` —
**both deleted by this ADR**, so the function would not even resolve after the column drop. That UPDATE
is **replaced**, not merely unfenced. A second writer stays safe through the existing
`on conflict do nothing` + `completed_by_another` outcome `[VERIFIED: :576-583]` — MEASURED in round 17
(T5): a record against an already-complete generation returns `completed_by_another` and does **not**
overwrite `md_hash`.

Without this paragraph the previous section's claim held for a degenerate reason — no row exists during
the call because no row is ever created — and **MEASURED (T4)** every paid record raises
`[P0001] cannot mark summary as recorded — generation … is <absent>`.

**`video_generations.state` survives, and becomes single-valued** ⟳ *(round 17 M2)*. With `pending`
unreachable it always reads `'complete'`, and T4 narrowed the CHECK to admit nothing else
`[VERIFIED: schema/03_generations.sql:324-325]`.

⟳ **Corrected by the implementation review (M1 / Codex Low).** This paragraph said the column is kept
"because five consumers still read it: the four completeness constraints (all written
`state <> 'complete' or …`)". **T4 deleted that disjunct from all five constraints**
`[VERIFIED: schema/03_generations.sql:410-435]` — because with the domain single-valued it is
constantly false, so the constraints now bind *unconditionally* — and no CHECK on the table references
`state` at all any more. Four of the five cited consumers no longer exist, and this paragraph is the
justification for keeping a column: a reason that has stopped being true is worse than no reason,
because it reads as settled. The three real reasons, which are the ones the schema itself already
carries `[VERIFIED: schema/03_generations.sql:305-322]`:

- **the single-valued domain is what makes the five CHECKs unconditional** — the relaxation round 6 B5
  granted the reservation is repaid rather than merely unused, and re-widening `state` fails *closed*
  (a pending row would have to satisfy all five in full);
- **`record_artifact` reads it to decide `completed_by_another`**
  `[VERIFIED: schema/04_artifacts.sql:438, :463-465]`;
- **`video_artifacts_generation_complete` selects it to tell present-and-complete from `<absent>`**
  `[VERIFIED: schema/04_artifacts.sql:1176, :1186]` — which, once the GC floor predicate goes, is the
  **only** guard left between a record and a missing generation, and `<absent>` is the branch T1
  measured (`cannot mark summary as recorded — generation gG1 is <absent>`). Dropping the column
  deletes that typed message and leaves a bare FK `[23503]` in its place.

**NOT deleted — `video_artifacts_free_uq` stays until render addressing is settled.** ⟳ *Round 14 H3
(Codex): this list said "deleted" while the render section said "replaced" — a flat contradiction
inside one document.* It is now **neither**, and that is the honest position: it is the only thing
keeping renders row↔blob **1:1** `[VERIFIED: schema/04_artifacts.sql:191-192]`, and with render
addressing withdrawn there is no successor to replace it with. Deleting it now would leave renders
with no uniqueness at all — strictly worse than today. It goes when the render ADR lands, not before.

**Retired:** §12b's caller obligation. It exists to make a fence safe; with no fence, a worker that
loses its token simply appends nothing, and the job queue already governs whether it may run at all.
The contract test stays — it now documents job-queue behaviour rather than propping up a schema
premise.

**Kept, unchanged:** the ranking views, tenant confinement, and every guard that survived its rounds.

**Kept but NOT unchanged — three the first draft wrongly listed above (round 13):**

- **The GC floor's predicate dies, and needs no replacement — DELETE it (round 13 H1 → round 16 B1).**
  `video_generations_collectable` requires `g.state = 'complete'`
  `[VERIFIED: schema/04_artifacts.sql — the predicate is DELETED by T2; the view is now :918-928]` — round 9's B1 fix, whose comment records the measurement:
  *"collectable WHILE IN FLIGHT: 1 ; sweep collected 1 … Money spent, bytes queued for deletion, no
  error anywhere."* Deleting the `pending` artifact state leaves nothing that produces a `pending`
  generation `[VERIFIED: schema/04_artifacts.sql — DELETED by T1; the ⛔ block recording what it was stands at :289-321]`, so the predicate goes
  **vacuously true**. That is retrospective B6's shape ("a guard that never started") arriving by
  *subtraction*, and the mutation harness would still score it load-bearing against a fixture no
  caller can produce — so **the dead predicate is removed from the view rather than left standing as
  decoration** — and **its paired assertion and mutation are retired with it, not orphaned**
  ⟳ *(round 17 M1)*: the assertion *"not collectable while pending, and visible after"*
  `[VERIFIED: schema/05_assert.sql:1428-1445]` and the named mutation *"B1: the collectable floor drops
  `state = complete`"* `[VERIFIED: mutate-schema.py:410-413]`, whose anchor is the exact line being
  deleted. Left in place the anchor stops matching and the harness reports **INVALID**, which this
  project has measured reads as *untested* rather than *retired*. This ADR applied that standard to
  the provenance assertions and not to these.

  **Rounds 13-15 read "the predicate is vacuously true" as "the guard needs a successor". It does
  not**, and the difference is the whole of round 16 B1: a vacuous predicate and an absent row are
  different facts, and the second makes the first harmless. Three mechanisms were designed before
  anyone asked whether the row exists.
  **THE GC FLOOR NEEDS NO SUCCESSOR. IT IS DISSOLVED, NOT COVERED.** ⟳ *Round 16 B1, MEASURED. Round
  14 named a per-kind successor; round 15 measured its `model` half expiring mid-call; round 15's fix
  (option C) added `video_generations.in_flight_until`. Round 16 measured that **the marker has no row
  to be written to**, and in doing so answered the underlying question the previous three rounds never
  asked.*

  ### When is a `video_generations` row created? **At record time — after the paid call.**

  That one sentence decides everything here. For `summary` it is **forced by this ADR's own
  deletions**; for `model`, `dig` and `digDeeper` it is an invariant that must be **carried**, not
  inferred — see the boxed warning below, which is the difference between a schema consequence and a
  convention:

  - `reserve_artifact_slot` is the **only** production INSERT into `video_generations`
    `[VERIFIED: schema/04_artifacts.sql — DELETED by T1; the ⛔ block stands at :289-321. The successor claim — record_artifact is now the only inserter — is ASSERTED rather than stated: 05_assert.sql, the two T4/H1 blocks]` — every other `insert into video_generations` in the
    repo is a fixture in `05_assert.sql`. This ADR deletes that function.
  - It inserts `state = 'pending'`, and that state is the only thing making a contentless row legal for
    a **summary**. `state` is `not null default 'complete'`
    `[VERIFIED: schema/03_generations.sql:324]`, and the completeness constraints are written
    `state <> 'complete' or <requirement>`, so with `pending` unreachable they bind.

  ### ⚠ …but only `summary` is FORCED. The other three paid kinds are convention (round 17 H1, MEASURED)

  ⟳ *This previously said the constraints "demand `card`, `md_hash`, `doc_version_major` and
  `produced_at`" for every kind. **Three of the four are also gated `kind <> 'summary'`** —
  `gen_card_complete` `[VERIFIED: schema/03_generations.sql:411]`, `gen_summary_has_format` `[:425-426]`,
  `gen_summary_has_hash` `[:427-428]`. Only `gen_complete_has_produced_at` `[:410]` ranges over all
  kinds, and `produced_at` is knowable before any Gemini call — `record_artifact` defaults it to `now()`
  `[VERIFIED: schema/04_artifacts.sql:446]`.*

  **MEASURED (round 17, T1):** a `model`, `dig` or `digDeeper` row inserted with **only** `produced_at`
  is **ACCEPTED**; the same shape for `summary` is refused `[23514] gen_card_complete`. The repo already
  relies on this — `05_assert.sql:138-139` inserts `gDIG`/`gMODEL` complete with `card` and `md_hash`
  NULL, and the suite is green.

  > **So the invariant must be carried, not inferred:** *no generation row is created before its paid
  > call completes.* For `summary` the constraints enforce it. For `model`, `dig` and `digDeeper`
  > **nothing does** — the implementing slice must either extend the constraints to those kinds or
  > assert the rule.

  ### ✅ IMPLEMENTED (T4) — and the answer is "carried", with the reason measured

  The implementing slice ran the measurement this section asked for, and **a constraint cannot close
  the gap**: it searched every producer for a column that could *witness production* and found none.
  A CHECK sees one row, and for `model`/`dig`/`digDeeper` **no value in that row is a function of the
  paid output** — so there is nothing for a constraint to test. Extending `gen_card_complete` to those
  kinds would have required a card they legitimately do not have.

  So the fix ran the other way — rather than *requiring* a card of kinds that have none, the schema now
  **forbids** one (`gen_card_is_summary_only`, `gen_major_is_summary_only`), which makes the taxonomy
  exact without pretending to enforce something it cannot.

  **What carries the invariant is one structural fact:** `record_artifact` is the only function that
  inserts into `video_generations`, and it runs after the paid call. **The structural fact is the
  guard, so the structural fact is what is tested** — an assertion now fails if a second inserter ever
  appears.

  **And the cost is measured rather than described.** A characterisation test records what a pre-call
  generation for a non-summary kind actually does today — the paid record succeeds and the row is *not*
  visible in `video_artifacts_current`, i.e. it buries its own paid bytes — and raises
  `CHARACTERISATION STALE` if that ever changes. A gap that cannot be closed is at least a gap that
  cannot move silently.

  **`pending` is now unrepresentable**, not merely unproduced: `check (state in ('complete'))`. T2 had
  noted the schema still *admitted* a hand-written pending row which, with the GC floor's predicate
  gone, would have been collectable. That door is shut in the schema rather than by the absence of a
  caller. `model` is the sharp case: no job, no staging, its own serve lease, and an early
  > row would reopen round 9's window with the floor already deleted and no assertion to go red.

  **Fifth instance of "name what the rule ranges over"** — after round 13 B1, round 14 H3, round 15 H3
  and round 16 M1 — this time in the paragraph that *is* round 16's load-bearing argument. The quoted
  *"both doors were locked"* measurement below is likewise summary-specific: its second door,
  `gen_card_complete`, is a summary-only constraint.

  So both doors are locked, which this schema already recorded when it hit them
  `[VERIFIED: schema/03_generations.sql:271-283]`:

  > *"Reserving with no generation row raised [23503] on the artifact's FK; creating the generation
  > row from what is knowable BEFORE the Gemini call raised [23514] gen_card_complete. **The paid call
  > sits between those two, so both doors were locked.**"*

  `state = 'pending'` was the key cut for that lock. This ADR throws the key away — so the row is born
  **complete, at record time**, and there is no instant during the paid call at which it exists.

  ### Therefore: nothing is collectable during the call, and `in_flight_until` is DELETED

  `video_generations_collectable` `[VERIFIED: schema/04_artifacts.sql:918-928]` can only return rows
  that exist. Round 9's B1 window — *"collectable WHILE IN FLIGHT … Money spent, bytes queued for
  deletion, no error anywhere"* — is closed **by the deletions themselves**.

  Adding a marker to re-close it would have been a column, a CI check, two prose rules, an assertion
  burden and a mutation-scoring burden spent on a window that was already shut: **two mechanisms for
  one concern, in the document written to stop exactly that.** Dissolving beats covering, and it is
  the same move that earned this ADR its headline.

  **Everything option C dragged in goes with it** — the "covering lifetime ≥ covered worst case"
  invariant and its promised CI check, the sweeper-only read rule, the marker's NULL meaning, and the
  per-kind bound arithmetic. Round 16's H1 (the bound was computed for `MAGAZINE_MAX_PASSES` = 3 while
  `SUMMARY_MAX_PASSES` = 12 `[VERIFIED: lib/gemini-cost.ts:27, :29]`), M2 (the "grep-checkable" rule
  had no script and a hole), M3 (was it ever cleared?) and L2 (the sentinel registry) all dissolve
  with it rather than being fixed. **That is the tell that the dissolution is the right call:** four
  findings, one deletion.

  ### What DOES still need protecting: the blob, not the row

  The bytes are written before any row references them, so during the call they are an **orphan** —
  and §8's grace period is the mechanism for orphans. This ADR previously noted that the grace period
  was dropped because *"a blob written but not yet published is unreferenced — that state no longer
  exists"* `[VERIFIED: …-design.md:891-893]`, which was true **only because** rule 19's record-first
  order put a `pending` row down first.

  > **Delete `pending` and that state returns. §8's grace period is REINSTATED, as an age predicate on
  > the blob.**

  ### ⚠ Rule 19 bought TWO more things, both on the money path (round 17 H4)

  ⟳ *The first version named only the GC knock-on. Six rounds passed without anyone checking what else
  the record-first order was load-bearing for.*

  §5.1's rule-19 resolution `[VERIFIED: …-design.md:864-887]` also bought **bytes ⊆ records** and:

  > *"**A crash before recording leaves nothing — no bytes, no row, no orphan — so spending again is
  > correct rather than a double-charge.**"*

  It was adopted against a MEASURED defect — *"Slot absent, no key to probe, serve path spends again …
  **6¢ → 12¢**"* `[VERIFIED: …-design.md:860-863]`.

  **With `pending` gone the row cannot precede the bytes.** So a crash *after* the blob write leaves
  paid bytes at a generation-derived key **no later attempt can name** — each attempt mints a fresh id
  — and the next attempt spends again. That is the shape rule 19 was rewritten to remove, reintroduced
  by this deletion, and §5.1's sentence *"a crash before recording leaves nothing"* is now **false and
  must be corrected in the same slice**.

  **Bounded, and named rather than hidden:** `summary_max_attempts` = 1
  `[VERIFIED: schema/04_artifacts.sql — DELETED by T1; recorded in the ⛔ block at :309-313]` and `max_serve_attempts` = 5
  `[VERIFIED: 0012_serve_model_charge.sql:21]`, so the residual is at most one extra paid call per
  attempt bound — the same class as the reclaim residual the concern table already carries. It is
  recorded here because this ADR's falsifier #4 (*"a paid kind whose spend is not bounded by a
  mechanism named in the concern table"*) exists to surface exactly this.

  §8's grace period is not a new mechanism — it is the one §8 already specifies, and it is uniform
  across kinds. **It is specified and NOT implemented**; see the concern table's evidence column.

  Note this is **not** the age-floor-on-generations that `[VERIFIED: schema/04_artifacts.sql — that objection's text went with the GC floor predicate (T2); the surviving age/currency asymmetry is stated at :828-837]`
  rejects (*"a 90-day age predicate in the sweeper would have HIDDEN this while leaving the floor
  wrong"*). That objection is about masking a wrong **state floor on rows**; this is §8's original
  grace period on **orphan blobs**, a different mechanism for a different object. Recorded because
  retiring an objection silently is this project's measured failure mode.

  **The grace period's length is the implementing slice's number**, and it must satisfy the one
  invariant worth keeping from option C: **it is longer than the worst-case paid call**, computed per
  kind from `SUMMARY_MAX_PASSES`, `TRANSCRIBE_MAX_PASSES`, `MAGAZINE_MAX_PASSES` **and
  `DIG_GENERATE_MAX_PASSES`** `[VERIFIED: lib/gemini-cost.ts:51]` — ⟳ *round 17 M3: the first version
  named three of the four and omitted dig, whose bytes are paid and whose cloud producer is
  `[VERIFIED: lib/job-queue/dig-handler.ts:100]`. A grace period shorter than a dig's worst case
  collects paid dig bytes mid-call — the exact failure the reinstatement exists to prevent. An
  enumeration missing a member, in the text that replaced the dissolved warning about enumerations.
  The constants are exported "for the guard test" `[VERIFIED: lib/gemini-cost.ts:25]`, not for this* — and bounded only once `countTokens`
  `[VERIFIED: lib/gemini.ts:82-84]` and the blob upload `[VERIFIED: lib/html-doc/model-store.ts:51]`
  are given timeouts, since both are untimed today (round 16, Codex). **Those timeouts are a blocking
  precondition of the implementing slice**, not a promise this ADR can keep by itself.

  ⚠ Staged-write ordering is unchanged and remains a caller obligation for the **bytes** of
  `summary`/`dig` `[VERIFIED: lib/job-queue/summary-handler.ts:173-179]`. It was never the GC
  guarantee, and with the floor dissolved nothing pretends it is.
- **The append-only trigger must be tightened in the same change, not after (M1).** It scopes
  immutability by transition `[VERIFIED: schema/04_artifacts.sql:993 — T4 replaced the transition gate with `old.generation_id is not null`; both permissions are gone]`, permitting
  `pending → recorded` and `delete an expired pending`. With `pending` gone both are unreachable — but
  they are *permissions*, and an unreachable permission in the one trigger that makes history
  immutable is a fail-open branch waiting for someone to reintroduce the state. Delete both branches.
- **The per-kind attempt ceiling is deleted with no successor, and the numbers disagree (M5).**
  `reserve_artifact_slot` bounds attempts per kind from `guardrail_config`
  `[VERIFIED: schema/04_artifacts.sql — DELETED by T1; the reads stood in the ⛔ block at :289-321]`.
  There is no row above for *"how many times may we pay
  for this slot"*. The candidates conflict: `jobs.max_attempts` defaults to **5**
  `[VERIFIED: 0008_jobs_queue.sql:14]` while `summary_max_attempts` is **1**, a
  difference documented as a deliberate product decision. Deleting the
  artifact-layer bound silently promotes summaries from 1 to 5. **The implementing slice must state
  which number wins**; this ADR does not get to leave it implicit.

  ⟳ **It did not state it, and for two commits the loss existed only as a comment — now tracked as
  [`docs/backlog.md` #26](../backlog.md)** *(implementation review, M2)*. The slice declined the
  decision **in writing** (04's ⛔ block: *"WHICH NUMBER WINS IS AN OPEN DECISION, not something this
  file settles"*) and the assertion that enforced the bound — *"with `summary_max_attempts`=1 a
  crashed summary slot is NOT retryable"* — was retired with the function it tested. Backlog #26
  carries both numbers, three candidate resolutions, and the trigger: **close it before a real caller
  reaches `record_artifact` for a `summary`**, i.e. before T5 (task #44). It is a spec regression
  today and not yet a money regression — nothing outside `docs/` calls either function — and that is
  why it was invisible, not why it is harmless.

**Not addressed here:** direct `service_role` DML can still write these tables. With no fence to
bypass, that stops being a hole in an authorization mechanism and becomes an ordinary "trusted role
can write" property. Round 13 confirmed the residue is bounded: `service_role` bypasses **RLS**, not
**triggers**, so `video_generations_freeze_trg` `[VERIFIED: schema/03_generations.sql:557-558]` and
the append-only trigger still hold — *provided* the trigger is tightened per M1 above. Round 12's H1
dissolves on that condition and not otherwise.

## Multi-source render provenance — SETTLED (round 13, H4)

⟳ **"Settled" means the SHAPE is settled, not that a caller can build one** *(implementation review,
L1)*. The table, the ranking rung and the GC reachability check are all set-shaped; **`record_artifact`
is not** — it takes a scalar `p_source_generation_id` and writes `array[p_source_generation_id]`, so
**no RPC caller can create a multi-source artifact today**. The code says so where it matters rather
than only here: the two-source fixture in `05_assert.sql` is written by direct DML and its comment
calls that *"an honest gap rather than a choice of style"*, and the statement-level INSERT enforcer is
deliberately built to permit the multi-row first write the day a producer appears. Whoever adds that
producer changes the signature; until then the heading and the code disagree only about tense, and
this paragraph is what stops the heading from reading as "and it works".

The first draft deferred this to the implementing slice while saying it must not be discovered during
implementation. Those two are incompatible, and round 13 showed why: `source_generation_id` is
load-bearing in two places that both read it as a **scalar**, so a set is a schema change, not a
detail.

- **The ranking view** `[VERIFIED: schema/04_artifacts.sql:767-777 — T3 replaced the scalar comparison with the set-shaped `not exists`]` —
  `(a.slot = 'summary' or a.source_generation_id is null or a.source_generation_id is not distinct
  from s.generation_id) desc`. With a set, *"is this render current w.r.t. its sources"* becomes *"are
  **all** its sources current"*, which one column cannot express and one `desc` cannot rank.
- **The FK** `[VERIFIED: schema/04_artifacts.sql:242-243 — T3 moved it to `vas_source_generation_fk`, per SOURCE]` — MATCH SIMPLE, added by round 5's M5
  precisely so provenance cannot name a generation that does not exist.

**Decision: address and provenance are different questions, and only ONE of them is in scope here.**

⟳ *Round 15 B1: an "Address = `sha256(rendered bytes)` (previous section)" item stood here, pointing
at a section the split deleted and re-asserting a withdrawn design. Removed. **Address is out of
scope** — see `2026-08-09-render-addressing-brief.md`. Provenance stays, because it is a coordination
concern (what may be collected) rather than an addressing one.*

1. **Provenance** = a `video_artifact_sources (artifact_id, source_generation_id)` join table, FK'd to
   `video_generations` **`on delete cascade`** — and to `video_artifacts (artifact_id)` on delete
   cascade as well.

   ⟳ **Round 14 B3 corrected this from `on delete restrict`, which was MEASURED to break account
   deletion.** ⟳ *Round 15 L1 corrected the REASON, which matters because the first one invited an
   obvious objection: "then why doesn't the existing `source_generation_id` FK break account deletion
   today?" **The operative fact is DEPTH, not `RESTRICT`.** Measured: a one-hop child with the same
   shape survives a parent cascade even as plain `NO ACTION` (which is what the live FK at
   `04_artifacts.sql:91-92` is — it has no `ON DELETE` clause), while a **two-hop grandchild** aborts
   the cascade even with `NO ACTION`. The join table breaks account deletion because it sits one hop
   deeper than the column it replaces — and `on delete no action` was never an available alternative
   either.* The live chain is
   `profiles → workspaces → workspace_videos → video_generations`, all `on delete cascade`
   `[VERIFIED: schema/01_workspaces.sql:13]` `[VERIFIED: schema/03_generations.sql:49]`
   `[VERIFIED: schema/03_generations.sql:360-361]`. So once **any** render carried a provenance row,
   `delete from profiles` failed — the account-erasure path, which is a real caller, not a
   hypothetical.
   `RESTRICT` had been chosen to stop GC collecting a still-referenced generation. **That protection
   is already provided by a different mechanism** — the second `not exists` over this join table added
   to `video_generations_collectable` below. Keeping `RESTRICT` too was two mechanisms for one
   concern, in a table introduced by a fix, and the redundant one was the one that broke a live path.

2. **`source_generation_id` is DROPPED in the same change**, and the round-5 M5 guarantee migrates to
   this table's FK. ⟳ *Round 14 H4: the first draft added the join table and rewrote two of the
   column's consumers without ever saying whether the column survived. If it survives, provenance has
   two representations that can disagree — the exact root cause the retrospective names, reintroduced
   by a fix for it.*

   ### ⚠ Dropping the column is NOT sufficient — three consumers move with it (round 15 B3)

   Round 15 MEASURED that the round-14 fix named *"two places"* while the column has **19 occurrences
   in `04_artifacts.sql` and 6 in `05_assert.sql`**. Two of the omissions are structural, and without
   them **this fix reproduces the exact defect it was written beside**:

   **(a) `record_artifact` is the ONLY writer of provenance, and it survives this ADR.** It takes
   `p_source_generation_id` `[VERIFIED: schema/04_artifacts.sql:356]` and writes it with a
   `coalesce(p_source_generation_id, v_src)` carry-forward
   `[VERIFIED: schema/04_artifacts.sql — the `coalesce` carry-forward is DELETED by T3; omission now carries forward STRUCTURALLY, :547-607]`. **Drop the column and leave the RPC
   unchanged and `video_artifact_sources` is always empty** — at which point *both* new guards below
   go **vacuously true**: the ranking rung and the GC `not exists`.

   > This is the identical failure this ADR diagnoses ~100 lines earlier for the GC floor — *"the
   > predicate goes vacuously true and the guard stops guarding without being deleted … a guard that
   > never started, arriving by subtraction."* Committed inside the fix set that names it. **Third
   > occurrence of the signature**, this time between two sections of one round's own work.

   **So: `record_artifact` writes the join rows in the same statement as the artifact row.** ⟳ *Round 16
   H2 corrected the re-record rule, which said **replace** and contradicted (b) ten lines below: a
   replace is a delete-and-insert, and the trigger being moved forbids exactly that.*

   > **A re-record must present the SAME source set, or raise. An omitted `p_source_generation_id`
   > carries the recorded set forward unchanged.**
   >
   > **Enforced by a `before insert` trigger on `video_artifact_sources`** (or an explicit set
   > comparison inside `record_artifact`) — **not** by the moved append-only branch.

   That is what the cited carry-forward actually does: `coalesce(p_source_generation_id, v_src)` with
   `v_src` read from the same (slot, generation) row `[VERIFIED: schema/04_artifacts.sql — `v_src` and its second read are DELETED by T3; see the note at :571-581]`
   means **omission = keep what is recorded**, which is how a re-record avoids tripping the
   immutability raise today — it re-states an identical value, so `is distinct from` is false. The
   carry-forward is an argument for **idempotent re-statement**, not for replacement. "Replace" on the
   omission path would have **wiped** the source set, making both new guards vacuously true — the very
   failure (a) is written to prevent.

   **(b) Provenance must stay append-only.** `[VERIFIED: schema/04_artifacts.sql:1071-1084 — T3 moved the branch onto `video_artifact_sources`]` — the
   append-only trigger raises *"the PROVENANCE of a % paid row is immutable"* on any change to
   `source_generation_id`. A child table with `on delete cascade` on both FKs and **no trigger of its
   own** makes provenance freely insertable and deletable, in the ADR titled *"artifacts are an
   append-only log."* **That trigger branch moves onto `video_artifact_sources`** — and it is **NOT
   sufficient on its own.** ⟳ *Round 17 H3, MEASURED: that branch is installed `before update or delete`
   `[VERIFIED: schema/04_artifacts.sql:1085-1087]`, and a re-record naming a different source is an
   **INSERT**, which fires no such trigger — the probe got a silent **union**, neither the same set nor
   a raise. The schema states the rule twice in its own comments: "a constraint governs STATES, a
   trigger governs TRANSITIONS, and an INSERT is a state with no transition"
   `[VERIFIED: schema/04_artifacts.sql:1012]`. The round-16 fix assigned an invariant to the one
   mechanism shape that structurally cannot see the operation that violates it — "a guard that never
   started", the signature this ADR names three times.*

   **(c) The four executable assertions are REWRITTEN, not deleted** — `05_assert.sql:166`, `:354-356`,
   `:360-362`, `:453`. `:453` is the executable proof of (b); deleting it would remove the evidence
   that the guard works rather than the guard.

   `art_summary_has_no_source` `[VERIFIED: schema/04_artifacts.sql:1136-1152 — T3 made it a constraint trigger over the join table]` goes with the column, and its
   replacement **cannot be a CHECK** — a CHECK cannot reference another table — so it becomes a
   constraint trigger. That change of mechanism is safe for the reason `:104-106` gives for having the
   CHECK at all (*"service_role bypasses policies, not constraints"*): `service_role` does not bypass
   triggers either. Stated rather than assumed (round 14 M3).

3. **"Current" is defined per source kind** ⟳ *(round 15 M3)*. The rung being replaced compares
   `source_generation_id` against `video_summary_current` `[VERIFIED: schema/04_artifacts.sql:767-777 — T3 replaced the scalar comparison with the set-shaped `not exists`]`,
   which has one row per (workspace, video) — **no row at all for a `dig` generation**. So a
   `digDeeper` render's sources have no defined currency under the naive rewrite, which is precisely
   the multi-source case the join table exists for. **Only summary-kind sources participate in the
   rung**; other kinds are recorded for GC reachability and do not rank. State it, or the rung is
   undefined exactly where it is needed.

4. **A generation row is deleted ONLY by parent cascade, never individually** ⟳ *(round 15 M2)*. This
   is the premise `on delete cascade` rests on. MEASURED: with `sources → gen on delete cascade`,
   deleting a lone generation leaves the render row with zero sources, and `not exists (…)` is then
   **true** — an orphaned render ranks as fully current and protects nothing. No caller reaches this
   today (nothing deletes `video_generations` except cascade), which is why it is an invariant to
   write down rather than a defect to fix. GC collects by `update body_collected`, not by deleting the
   row — Codex verified this independently and it is why `cascade` opens no collection window.

A hash alone cannot answer *"which generations does this render reference"* without already knowing
the answer — and **GC needs that answer**. `video_generations_collectable`
`[VERIFIED: schema/04_artifacts.sql:918-928]` currently checks only an artifact's *own* generation, so
a render referencing a summary generation does not protect it from collection today either. The join
table closes that hole; a hash cannot.

**Consequences to write into the implementing slice, not discover in it:**

- the ranking rung becomes `not exists (select 1 … where source not current)`;
- `video_generations_collectable` gains a second `not exists` over the join table.
  ⟳ **And that `not exists` is a PERMANENT PIN, not a retention delay — [`docs/backlog.md` #27](../backlog.md)**
  *(implementation review, H3)*. The implementing slice's comment claimed §8's retention clock would
  eventually release a pinned source; **MEASURED 2026-08-10, no such release exists** — the provenance
  row cannot be deleted while its artifact lives, the paid artifact cannot be deleted at all, and the
  sweeper selects *through* the view, so a summary generation stays pinned even after the only render
  built from it has itself been swept. Since `model` is generated on first serve, that is every served
  document. The comment is corrected and the pin is now asserted as a **characterisation** in
  `05_assert.sql` (it goes RED if someone implements the release, which is the intended signal); the
  retention decision itself is open, with the measured candidate predicate recorded in #27. It is not
  taken here because deciding when paid bytes become deletable is a retention rule, and this ADR did
  not decide one;
- `art_summary_has_no_source` `[VERIFIED: schema/04_artifacts.sql:1136-1152 — T3 made it a constraint trigger over the join table]` becomes a cardinality-zero
  rule on the join table rather than a NULL check.

## What would falsify this

- A caller that writes an artifact for a generation **another writer is concurrently creating**
  (breaks the disjointness claim). ⟳ *Reworded, round 13 L1: the first phrasing was "a generation it
  did not create", which fires on the **replicator this ADR is defending** — `transferClassA` copies a
  body it did not produce, and that is fine by design. In the one section written to be mechanically
  checkable, the difference matters.*
- A second producer path that does not go through `jobs` **other than the `model` serve path already
  named above** — breaking the **spend bound**, not "exclusivity". ⟳ *Round 15 H2: this said "breaks
  exclusivity", a guarantee the concern table itself no longer claims for either `jobs` or `model`.
  The one mechanically-checkable section was testing for the breach of a promise the document had
  already withdrawn.* ⟳ *Round 13 fired this one. The exception is enumerated, not
  open-ended: a NEW one still falsifies.*
- A render whose identity cannot be derived deterministically (breaks the uniform-address claim).
- **A paid kind whose spend is not bounded by a mechanism named in the concern table** (breaks the
  money claim). ⟳ *Added round 13: the first three falsifiers were all about writes, which is exactly
  the substitution B1 caught — the ADR proved disjointness of writes and read it as absence of
  contention. This one asks the money question directly.*

Each is a concrete check, not a judgement — which is the point.

## Round 13 — what was tried and could NOT break this

Recorded so later rounds do not re-spend the effort.

- **Producer × replicator disjointness holds.** `transferClassA`
  `[VERIFIED: lib/cloud-sync/sync-run.ts:372-394]` copies a body it did not produce, makes no Gemini
  call, and mints no generation id. No path was found by which sync mints one.
- **No third paid cloud producer beyond `model`.** Full sweep of `generateSummary` /
  `generateMagazineModel` / `generateDig` / `extractQuickView` call sites: summary →
  `lib/job-queue/summary-handler.ts:114` (job); dig → `lib/job-queue/dig-handler.ts:100` (job); model →
  `lib/html-doc/serve-doc.ts:112` (serve path — the named exception). The other two Gemini callers
  (`app/api/videos/[id]/regenerate/route.ts:66`, `app/api/quick-view/backfill/route.ts:62`) are
  local-only. No `scripts/*.ts` writes an artifact.
- **Two producers after a lease expiry produce MERGE-SAFE appends**, for the job kinds — the
  heartbeat-abort row is the mechanism. ⟳ *Round 15 L2: this said "do not double-append", which is
  neither what the mechanism provides nor what the design wants — under this ADR's central claim two
  producers with different generation ids append two rows BY DESIGN.* They may still double-*charge*; that residual is
  pre-existing, documented, and tracked to 1D, and is not caused by this decision.
- **The retrospective's central diagnosis stands.** The reservation was designed for a world with one
  mutable address per slot; stable addressing removed that world.

## Dependency note (round 13, M6)

This ADR builds on ADR-0006, which is itself `status: proposed — supersedes ADR-0002 if accepted`.
So ADR-0007 currently rests on an unaccepted decision, and both should be accepted together or not at
all. Recorded because round 13's brief wrongly told both reviewers ADR-0006 was accepted and
non-re-litigable; no finding turned on it, but the next round should not inherit the error.
