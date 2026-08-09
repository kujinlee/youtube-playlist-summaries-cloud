---
status: proposed — supersedes the reservation protocol of ADR-0006's spec (handoff item 4).
  DEPENDS ON ADR-0006 BEING ACCEPTED; ADR-0006 is itself `proposed`, so the two stand or fall together
revised: 2026-08-09. Rounds 13, 14, 15 — three DESIGN reviews, all answered here.
  SCOPE: COORDINATION ONLY. Render addressing was SPLIT OUT (user decision) to
  docs/superpowers/specs/2026-08-09-render-addressing-brief.md (backlog #25) after two designs were
  refuted in two rounds.
  The GC-floor successor is `video_generations.in_flight_until` — ONE sweeper-only marker for every
  kind (user decision, round 15 B2, "option C"), replacing the per-kind table whose `model` half was
  measured to expire mid-call.
  The core decision — delete the reservation protocol — has survived THREE design reviews unbroken;
  every finding in rounds 14 and 15 was in a FIX, not in the decision.
  See docs/reviews/spec-blob-addressing-r1{3,4,5}-coordinator.md
---

# Artifacts are an append-only log; nothing coordinates writers, because writers do not contend

`video_artifacts` records what was produced. It has **no lease, no token, and no attempt counter**.
Paid artifacts are addressed under a generation id chosen before the content. Producer coordination
comes from the job queue's existing lease/heartbeat; "which artifact is current" from the ranking view
that already exists.

⚠ **One marker survives, and it is not a lease.** `video_generations.in_flight_until` tells the
**sweeper** that a paid call is running, so it does not collect bytes that are being paid for. It has
no token, no attempt counter, and **no caller may read it to exclude another** — it coordinates
nobody. That distinction is the whole difference between this and the `pending` state being deleted,
and it is stated here because a reader who meets the column first will otherwise read it as the
reservation growing back.

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
- `[VERIFIED: docs/adr/0006]` + `schema/04_artifacts.sql:147-160` — the blob key is
  `<ws>/videos/<video>/<generation>/…`, derived from the generation id.
- `[VERIFIED: schema/04_artifacts.sql:162-163]` — `video_artifacts_paid_uq` keys on
  `(workspace, video, slot, generation)`, so two generations of one slot are two rows, never a
  conflict.

### ⚠ The claim is TRUE and it is NOT sufficient — read this before using it (round 13, B1)

Round 13 confirmed the claim above by measurement and then showed that **proving it is not the same as
proving there is nothing to coordinate.** Round 5 had already measured the reason
`[VERIFIED: schema/04_artifacts.sql:168-172]`:

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
| what may be deleted | `video_generations_collectable` + `body_collected`, floored by `video_generations.in_flight_until` (one sweeper-only marker, every kind — round 15 B2) | round 8 + round 15 |
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
`[VERIFIED: schema/04_artifacts.sql:26]` maps `slot='model'` → `kind='model'`, and
`art_paid_has_generation` `[VERIFIED: schema/04_artifacts.sql:95]` puts it in the paid set beside
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
  removes this entirely** — single-source rows are untouched, so no already-exhausted document is
  revived, and the migration becomes **idempotent under re-run**, a question the first version never
  addressed.

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
`[VERIFIED: schema/04_artifacts.sql:95]`

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
  `[VERIFIED: schema/04_artifacts.sql:94-95]`. It is the **address** that is unresolved, not the
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
append with a typed outcome and no fence.

**ADDED — one column, and it is the only thing this ADR adds.** ⟳ *Reconciliation pass, 2026-08-09:
the Consequences list recorded every deletion and no addition, so the ADR's net schema effect was
unstated.*
`video_generations.in_flight_until timestamptz` — the GC floor's successor, sweeper-read only, one
marker for every kind (round 15 B2, option C). Plus `video_artifact_sources`, the provenance join
table, which replaces the dropped `source_generation_id` column rather than adding to it.

**NOT deleted — `video_artifacts_free_uq` stays until render addressing is settled.** ⟳ *Round 14 H3
(Codex): this list said "deleted" while the render section said "replaced" — a flat contradiction
inside one document.* It is now **neither**, and that is the honest position: it is the only thing
keeping renders row↔blob **1:1** `[VERIFIED: schema/04_artifacts.sql:164-165]`, and with render
addressing withdrawn there is no successor to replace it with. Deleting it now would leave renders
with no uniqueness at all — strictly worse than today. It goes when the render ADR lands, not before.

**Retired:** §12b's caller obligation. It exists to make a fence safe; with no fence, a worker that
loses its token simply appends nothing, and the job queue already governs whether it may run at all.
The contract test stays — it now documents job-queue behaviour rather than propping up a schema
premise.

**Kept, unchanged:** the ranking views, tenant confinement, and every guard that survived its rounds.

**Kept but NOT unchanged — three the first draft wrongly listed above (round 13):**

- **The GC floor is not preserved by leaving it alone (H1).** `video_generations_collectable` requires
  `g.state = 'complete'` `[VERIFIED: schema/04_artifacts.sql:897]` — round 9's B1 fix, whose comment
  records the measurement: *"collectable WHILE IN FLIGHT: 1 ; sweep collected 1 … Money spent, bytes
  queued for deletion, no error anywhere."* Deleting the `pending` artifact state leaves nothing that
  produces a `pending` generation `[VERIFIED: schema/04_artifacts.sql:307-312 is the only producer]`,
  so the predicate goes **vacuously true** and the guard stops guarding without being deleted. This is
  retrospective B6's shape ("a guard that never started") arriving by *subtraction* — and the mutation
  harness will still score it load-bearing against a fixture no caller can produce.
  **The successor is ONE mechanism for every kind: a sweeper-only in-flight marker on
  `video_generations`.** ⟳ *Round 14 B2 named a per-kind successor; round 15 B2 MEASURED that the
  `model` half of it — the `serve_model_charge` lease — expires before the call it covers. Option C,
  chosen by the user 2026-08-09.*

  > **`video_generations.in_flight_until timestamptz`.** A generation whose `in_flight_until` is in
  > the future is **not collectable**. Written by whoever starts a paid call, for **every** kind.
  > `video_generations_collectable` gains `and (g.in_flight_until is null or g.in_flight_until <= now())`
  > in place of the vacated `g.state = 'complete'`.

  **Why one mechanism and not two.** The per-kind table was itself an exception, and this ADR's rule
  is one mechanism per concern. The concern is *"a paid call is running against this generation"* —
  identical for `summary`, `dig` and `model`. Staged-write ordering stays as it is, but it is no
  longer load-bearing for **GC**: it protects the bytes, the marker protects the row. That separation
  is what lets `model` — which cannot stage, see below — be covered by the same rule as everything
  else.

  **THE INVARIANT THIS ADR PREVIOUSLY OMITTED, stated once and enforced by a check:**

  > **The covering mechanism's lifetime ≥ the covered operation's worst case.**

  Round 15 B2 measured that the previous successor failed exactly this test and that the ADR never
  performed the comparison. The magazine call's worst case is `MAGAZINE_MAX_PASSES` = 3
  `[VERIFIED: lib/gemini-cost.ts:29]` × `REQUEST_TIMEOUT_MS` = 60 000 ms
  `[VERIFIED: lib/gemini.ts:94]` = 180 000 ms, **plus** 400 + 800 ms backoff
  `[VERIFIED: lib/gemini.ts:252, :267]`, **plus** an untimed `countTokens` preflight
  `[VERIFIED: lib/gemini.ts:82-84]`, **plus** an unbounded upload. `in_flight_until` must be set past
  that bound, and **a CI check must fail if any input grows past it** — otherwise the next
  `REQUEST_TIMEOUT_MS` bump silently reopens the window. A derived constant with no gate is an
  enumeration, and this spec has already been bitten twice by enumerations.

  **⛔ TWO RULES THAT KEEP THIS FROM REGROWING INTO THE THING WE JUST DELETED.** `pending` was a
  marker too. What made it a reservation protocol was a token, an attempt counter, and callers that
  read it to exclude each other.

  1. **Only the sweeper may read `in_flight_until`.** No caller may consult it to decide whether to
     proceed. It is a GC hint, never a fence. This is grep-checkable and should be checked.
  2. **It carries no token and no attempt counter.** If either appears, the reservation protocol is
     growing back and this ADR has been reversed without anyone saying so.

  **Why this beats the alternatives** (all four were costed; user chose C):
  - a **renewal RPC** on the serve lease fires this ADR's own trigger for routing `model` through
    `jobs`, and grows the duplicate vocabulary rather than shrinking it;
  - a **derived TTL** on that lease closes the gap but leaves the guard in `supabase/migrations/`,
    which **neither executable gate can see** — `verify-schema.sh` and `mutate-schema.py` read only
    the spec `schema/` dir (round 15 M1). A money-path guard that cannot be asserted or
    mutation-scored is one that will silently stop guarding;
  - an **age floor on `created_at`** is cheapest, and was **rejected**: `04_artifacts.sql:893-896`
    already records the objection — *"a 90-day age predicate in the sweeper would have HIDDEN this
    while leaving the floor wrong"*. An age floor is a heuristic; when the real invariant breaks it
    masks the breakage instead of surfacing it. Recorded here because retiring that objection
    silently is the failure mode this project has already measured.

  `in_flight_until` lives in the spec schema, so `05_assert.sql` can assert it and `mutate-schema.py`
  can score it — the property the lease could never have.

  **Why `model` cannot use the staged route** (unchanged, and it is why one uniform marker was needed).
  `lib/html-doc/model-store.ts:51` writes it with a plain `put`, and the docblock at `:42-43` says the
  staged→promote protocol *"is NOT used for the model"* — deliberately: a regenerated model must
  **overwrite** the stale blob or the serve path re-reserves and re-charges every view until K, then
  503s `[VERIFIED: lib/html-doc/serve-doc.ts:102-104]`. Left uncovered, a `model` generation is
  collectable **while its paid Gemini call is in flight** — round 9's B1 exactly, whose measured
  transcript survives at `schema/04_artifacts.sql:888-892`: *"Money spent, bytes queued for deletion,
  no error anywhere."*

  ⚠ Staged-write ordering **is** a caller obligation — the class this ADR retires two paragraphs
  above. It is accepted for the **bytes** of `summary`/`dig` because it is already implemented and
  load-bearing. It is **no longer** the GC guarantee for any kind; `in_flight_until` is, and the
  sweeper reads it without any caller having to remember anything.

  Note the coupling that makes this necessary at all: §8's grace period was dropped because *"a blob
  written but not yet published is unreferenced — that state no longer exists"*
  `[VERIFIED: …-design.md:891-893]`, and that state existed only because rule 19's record-first order
  put a `pending` row down first. **Delete `pending` and the state returns** — `in_flight_until` is
  what replaces it.
- **The append-only trigger must be tightened in the same change, not after (M1).** It scopes
  immutability by transition `[VERIFIED: schema/04_artifacts.sql:911-913]`, permitting
  `pending → recorded` and `delete an expired pending`. With `pending` gone both are unreachable — but
  they are *permissions*, and an unreachable permission in the one trigger that makes history
  immutable is a fail-open branch waiting for someone to reintroduce the state. Delete both branches.
- **The per-kind attempt ceiling is deleted with no successor, and the numbers disagree (M5).**
  `reserve_artifact_slot` bounds attempts per kind from `guardrail_config`
  `[VERIFIED: schema/04_artifacts.sql:257-262]`. There is no row above for *"how many times may we pay
  for this slot"*. The candidates conflict: `jobs.max_attempts` defaults to **5**
  `[VERIFIED: 0008_jobs_queue.sql:14]` while `summary_max_attempts` is **1**, a difference documented
  as a deliberate product decision `[VERIFIED: schema/04_artifacts.sql:263-270]`. Deleting the
  artifact-layer bound silently promotes summaries from 1 to 5. **The implementing slice must state
  which number wins**; this ADR does not get to leave it implicit.

**Not addressed here:** direct `service_role` DML can still write these tables. With no fence to
bypass, that stops being a hole in an authorization mechanism and becomes an ordinary "trusted role
can write" property. Round 13 confirmed the residue is bounded: `service_role` bypasses **RLS**, not
**triggers**, so `video_generations_freeze_trg` `[VERIFIED: schema/03_generations.sql:498-500]` and
the append-only trigger still hold — *provided* the trigger is tightened per M1 above. Round 12's H1
dissolves on that condition and not otherwise.

## Multi-source render provenance — SETTLED (round 13, H4)

The first draft deferred this to the implementing slice while saying it must not be discovered during
implementation. Those two are incompatible, and round 13 showed why: `source_generation_id` is
load-bearing in two places that both read it as a **scalar**, so a set is a schema change, not a
detail.

- **The ranking view** `[VERIFIED: schema/04_artifacts.sql:814-816]` —
  `(a.slot = 'summary' or a.source_generation_id is null or a.source_generation_id is not distinct
  from s.generation_id) desc`. With a set, *"is this render current w.r.t. its sources"* becomes *"are
  **all** its sources current"*, which one column cannot express and one `desc` cannot rank.
- **The FK** `[VERIFIED: schema/04_artifacts.sql:91-92]` — MATCH SIMPLE, added by round 5's M5
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
   `[VERIFIED: schema/03_generations.sql:362-363]`. So once **any** render carried a provenance row,
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
   `p_source_generation_id` `[VERIFIED: schema/04_artifacts.sql:470]` and writes it with a
   `coalesce(p_source_generation_id, v_src)` carry-forward
   `[VERIFIED: schema/04_artifacts.sql:661-671, esp. :663]`. **Drop the column and leave the RPC
   unchanged and `video_artifact_sources` is always empty** — at which point *both* new guards below
   go **vacuously true**: the ranking rung and the GC `not exists`.

   > This is the identical failure this ADR diagnoses ~100 lines earlier for the GC floor — *"the
   > predicate goes vacuously true and the guard stops guarding without being deleted … a guard that
   > never started, arriving by subtraction."* Committed inside the fix set that names it. **Third
   > occurrence of the signature**, this time between two sections of one round's own work.

   **So: `record_artifact` writes the join rows in the same statement as the artifact row.** The
   re-record case must be stated too — the `coalesce(…, v_src)` carry-forward has no join-table
   analogue, so the ADR must say whether a re-record replaces the source set or unions with it.
   **Replace**, to match the carry-forward's "the row names its own sources" semantics.

   **(b) Provenance must stay append-only.** `[VERIFIED: schema/04_artifacts.sql:969-973]` — the
   append-only trigger raises *"the PROVENANCE of a % paid row is immutable"* on any change to
   `source_generation_id`. A child table with `on delete cascade` on both FKs and **no trigger of its
   own** makes provenance freely insertable and deletable, in the ADR titled *"artifacts are an
   append-only log."* **That trigger branch moves onto `video_artifact_sources`.**

   **(c) The four executable assertions are REWRITTEN, not deleted** — `05_assert.sql:166`, `:354-356`,
   `:360-362`, `:453`. `:453` is the executable proof of (b); deleting it would remove the evidence
   that the guard works rather than the guard.

   `art_summary_has_no_source` `[VERIFIED: schema/04_artifacts.sql:107]` goes with the column, and its
   replacement **cannot be a CHECK** — a CHECK cannot reference another table — so it becomes a
   constraint trigger. That change of mechanism is safe for the reason `:104-106` gives for having the
   CHECK at all (*"service_role bypasses policies, not constraints"*): `service_role` does not bypass
   triggers either. Stated rather than assumed (round 14 M3).

3. **"Current" is defined per source kind** ⟳ *(round 15 M3)*. The rung being replaced compares
   `source_generation_id` against `video_summary_current` `[VERIFIED: schema/04_artifacts.sql:814-816]`,
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
`[VERIFIED: schema/04_artifacts.sql:898-900]` currently checks only an artifact's *own* generation, so
a render referencing a summary generation does not protect it from collection today either. The join
table closes that hole; a hash cannot.

**Consequences to write into the implementing slice, not discover in it:**

- the ranking rung becomes `not exists (select 1 … where source not current)`;
- `video_generations_collectable` gains a second `not exists` over the join table;
- `art_summary_has_no_source` `[VERIFIED: schema/04_artifacts.sql:107]` becomes a cardinality-zero
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
