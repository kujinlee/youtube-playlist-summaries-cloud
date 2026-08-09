---
status: proposed — supersedes the reservation protocol of ADR-0006's spec (handoff item 4)
revised: 2026-08-09, round 13 (first DESIGN review of this spec). 2 Blocking, 4 High, 6 Medium, 1 Low
  — all answered here. The decision to delete the reservation SURVIVED review; its justification did
  not, and that is what changed. See docs/reviews/spec-blob-addressing-r13-coordinator.md
---

# Artifacts are an append-only log; nothing coordinates writers, because writers do not contend

`video_artifacts` records what was produced. It has **no lease, no token, and no attempt counter**.
Every artifact has an immutable derived address: paid kinds under a generation id chosen before the
content, renders under `sha256(rendered bytes)`. Producer exclusivity comes from the job queue's
existing lease/heartbeat; "which artifact is current" from the ranking view that already exists.

**Two qualifications, both forced by round 13 and both stated up front rather than buried:**

1. **The `model` kind is a paid producer with no job**, arbitrated by `serve_model_charge` instead.
   The one-mechanism-per-concern rule has this standing exception, and deleting
   `video_artifacts_inflight_uq` requires re-keying `doc_key` in the same slice.
2. **The free/paid distinction does not vanish** — it moves out of the write path into how an id is
   minted (UUID-before-content for paid, content hash for free). Smaller and more honest, but not
   zero.

We decided this because the reservation protocol built alongside ADR-0006 produced a Blocking or High
in **six consecutive adversarial rounds**, and four of those defects were introduced by the previous
round's own fix. Every other component of that spec converged and stayed converged. The problem was
not any of the twelve defects; it was that the mechanism re-solved a problem ADR-0006 had already
dissolved.

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
| producer **enqueue** dedup | `jobs_idem_active` — one non-terminal job per (owner, playlist, video, section, kind, version) | `[VERIFIED: 0009_job_playlist_identity_and_worker_persistence.sql:11-13]` |
| producer **execution** exclusivity | lease + heartbeat → `leaseLost.abort()`, re-checked immediately before the irreversible write | `[VERIFIED: lib/job-queue/worker-runner.ts:48-51, :30-32]` + `[VERIFIED: lib/job-queue/summary-handler.ts:170]` |
| pay-at-most-once **accounting** | `jobs.ever_metered` + `reserved_cents`, durable across retries — prevents an under-count on release, **not** a second real charge | `[VERIFIED: 0020_reservation_release.sql:25-32]` |
| at-most-once **spend** | heartbeat-abort (above) + per-kind attempt bounds in `guardrail_config`. **Bounded, not zero** — a reclaim after the Gemini call has already billed is a known residual | `[VERIFIED: lib/job-queue/summary-handler.ts:166-169]` |
| execution liveness | job lease + heartbeat + `sweep_expired_leases` | `[VERIFIED: 0009_…:63-78]` |
| stable addressing | generation id → blob key | ADR-0006 |
| which artifact is current | `video_artifacts_current` ranking | `schema/04_artifacts.sql` |
| what may be deleted | `video_generations_collectable` + `body_collected` | round 8 |
| **`model` exclusivity + spend** | `serve_model_charge` lease, **not** `jobs` — see the next section | `[VERIFIED: 0012_serve_model_charge.sql:7-13, :53]` |

**Two corrections round 13 forced, recorded so they are not re-lost.** `jobs_idem_active` dedupes
**enqueues**; it says nothing about how many workers execute the one job it admits, so it could never
have provided execution exclusivity. And `ever_metered`/`reserved_cents` govern *accounting*, not
*spend* — the code says so in its own words at `summary-handler.ts:166-169`. Both rows previously
claimed a guarantee their mechanism does not make.

## What already serves each concern

This table is the check that was never run. Every concern has exactly one mechanism, and every
mechanism serves exactly one concern.

| Concern | Mechanism | Evidence |
|---|---|---|
| producer exclusivity | `jobs_idem_active` — one non-terminal job per (owner, playlist, video, section, kind, version) | `[VERIFIED: unique partial index on jobs]` |
| producer idempotency | the same index | as above |
| pay at most once | `jobs.ever_metered` + `reserved_cents`, durable across retries | `[VERIFIED: 0020_reservation_release.sql:25-32]` |
| execution liveness | job lease + heartbeat + `sweep_expired_leases` | `[VERIFIED: 0008_jobs_queue.sql:96-130]` |
| stable addressing | generation id → blob key | ADR-0006 |
| which artifact is current | `video_artifacts_current` ranking | `schema/04_artifacts.sql` |
| what may be deleted | `video_generations_collectable` + `body_collected` | round 8 |

The reservation protocol re-implemented rows 1–4 in a second vocabulary — `lease_token`,
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
`(owner_id, doc_key, day)` with a lease and an `attempt_count` bounded by `max_serve_attempts`
`[VERIFIED: 0012_serve_model_charge.sql:7-13]`. It has a 180 s TTL and **no renewal RPC**
`[VERIFIED: 0012_serve_model_charge.sql:24]`.

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

**Data migration — `attempt_count` merges by SUM, not MAX.** Collapsing N playlist-scoped rows into
one workspace-scoped row per day must preserve attempts that were really paid for. The governing rule
is the serve path's own: *"over-count is safe, under-count is the bug"*
`[VERIFIED: lib/html-doc/serve-doc.ts:105-109]`. `max` would license spend that already happened.
Rows are per-day, so any over-tightening clears the next day.

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

## Renders lose their special case too

`generation_id is null` currently encodes **two independent facts**:
`[VERIFIED: schema/04_artifacts.sql:95]`

```sql
constraint art_paid_has_generation check (
  (kind in ('summary','model','dig','digDeeper')) = (generation_id is not null))
```

— "this is free" (a *money* property) and "this address may be overwritten" (an *addressing*
property). That conflation is the same root cause as nullable `corrections_hash` ("no corrections" vs
"never computed") and absent-vs-failed-to-read, and it produced five of the twelve rounds' findings.

**A render therefore gets an immutable derived address too — but NOT a generation id, and NOT under a
`<gen>/` key.** The first draft proposed `hash(source_generation_ids, GENERATOR_VERSION)`. Round 13
measured that this breaks two things, so it is replaced:

> **A render's identity is `sha256(rendered bytes)`, carried in a `render_id` column, and the key keeps
> its existing `<ws>/videos/<vid>/renders/…` prefix.**

**Why not a generation-shaped key (B2 — MEASURED).** §8 derives a money-safety rule for itself:
*"the paid/free split must be derivable from the KEY ALONE… any future key that does not announce its
own paid-ness is either uncollectable or unsafe to collect"* `[VERIFIED: …-design.md:2096-2100]`. The
discriminator is literally path segment 4 — a generation id, or the constant `renders`
`[VERIFIED: …-design.md:275-282]`. Uniform generation-derived addressing erases exactly that
discriminator, and renders become uncollectable (the accumulation §8 exists to prevent, which ADR-0006
already flags at `…-design.md:2113-2114`) or the sweeper becomes unsafe on paid bytes.

Round 13 also measured that `art_key_names_generation`
`[VERIFIED: schema/04_artifacts.sql:159-161]` — a constraint the first draft never mentioned while
listing stable addressing as *"Kept, unchanged"* — rejects a render carrying a generation id at the
§4.0 render key, and `art_paid_has_generation` rejects it at a generation-shaped key. Both routes were
closed by constraints this ADR claimed to be preserving.

**Why not a hash of source ids + `GENERATOR_VERSION` (H2 — the identity was incomplete).**
`GENERATOR_VERSION` does not version the renderer. It versions the paid magazine model's shape and
prompt `[VERIFIED: lib/html-doc/constants.ts:1-5]`; its use as an HTML-cache key is convention. There
are **three** independent constants, and a PDF's bytes depend on all of them:

| Constant | Evidence | Governs |
|---|---|---|
| `GENERATOR_VERSION` | `[VERIFIED: lib/html-doc/constants.ts:5]` | magazine model shape/prompt |
| `PDF_RENDER_VERSION` | `[VERIFIED: lib/pdf/pdf-render-version.ts:10]` | PDF settings **and the pinned Chromium** |
| `DIG_GENERATOR_VERSION` | `[VERIFIED: lib/dig/generate.ts:15]` | dig bodies — decides what a dig-deeper render contains |

`pdf-render-version.ts:5-9` states the failure mode itself: those bumps *"alter PDF bytes WITHOUT
changing the HTML."* Under the first draft's hash, a `PDF_RENDER_VERSION` bump yields **the same
address for different bytes** — in an append-only log, a silent overwrite or an unrecordable artifact.
An identity built by enumerating version constants is only as complete as the enumeration, and this
codebase has three constants and a Chromium pin to forget.

**Content addressing is complete by construction, and production already does it.**
`[VERIFIED: lib/pdf/pdf-render-version.ts:22]` keys PDFs as
`pdfs/${base}.r${PDF_RENDER_VERSION}.${sha256(html)[:16]}.pdf`, called on the nonce-free rendered HTML
`[VERIFIED: app/api/pdf/[id]/route.ts:54]`. It subsumes every version constant, present and future,
without anyone maintaining a list.

- Re-rendering the same source with the same renderer yields the **same** address — idempotent,
  nothing to overwrite.
- Any change to bytes — model, dig, renderer setting, Chromium — yields a **different** address.
- The ADR's falsifier #3 (deterministic derivability) is satisfied: it is a hash of the output.

**One constraint it must respect, and does.** `[VERIFIED: …-design.md:893]`: *"A generation id must be
chosen before its content, which rules out content-hash ids for anything on a spend path; §4.1 already
recommends UUIDs there and content hashes only for free re-renders."* Renders are the free side, so
this is the permitted case — paid kinds keep UUID generation ids chosen before the Gemini call.

**Note honestly what this costs the headline.** The free/paid distinction does not vanish; it moves
from `record_artifact`'s write branch into *how an id is minted* — UUID-before-content for paid,
hash-of-content for free. That is a smaller and more honest place for it, but it is not zero, and this
ADR should not claim renders lost their special case entirely. **Put the branch in a data-driven
function** beside `slot_kind` `[VERIFIED: schema/04_artifacts.sql:20]` rather than in caller
convention, or it becomes exactly the unwritten caller rule §12b was retired for being.

### Does the founding conflation still dissolve? Yes — by a different route, and it must be checked

This ADR exists because `generation_id IS NULL` carries **two** meanings: *"this is free"* (money) and
*"this address may be overwritten"* (addressing). The first draft dissolved it by giving renders a
generation id. Renders now get a `render_id` instead, so the question has to be re-answered rather
than inherited — and `scripts/check-sentinel-meanings.py` will ask it, since its current entry for
`art_paid_has_generation` says *"delete this entry when renders get a derived generation id"*, which
is no longer the plan.

**It dissolves, because the second meaning is what actually goes away.** A render addressed by
`sha256(rendered bytes)` is immutable: re-rendering identical bytes lands on the same address (nothing
to overwrite) and any byte change lands on a new one (a new row). So renders stop being overwritable
whether or not they carry a generation id. `generation_id IS NULL` is then left meaning exactly one
thing — *"this kind is free"* — which is a **money** property with a single owner, and that is the
condition the sentinel gate enforces.

The mechanical consequences, for the implementing slice:

- `video_artifacts_free_uq` — *one row per slot, overwritable* `[VERIFIED: schema/04_artifacts.sql:164]`
  — is **not** simply deleted as the first draft said; it is **replaced** by uniqueness on
  `(workspace_id, video_id, slot, render_id)`, the free-side mirror of `video_artifacts_paid_uq`.
  Deleting it outright would leave renders with no uniqueness at all.
- `art_paid_has_generation` becomes a two-way rule over two columns: a paid kind has a `generation_id`
  and no `render_id`; a render has a `render_id` and no `generation_id`. Exactly one is non-null.
- Update the `check-sentinel-meanings.py` entry to match this route, rather than deleting it on the
  strength of a plan that changed.

Free-ness becomes what it always was: a property of the *kind*, consulted only by the money path.

**Dissolved rather than fixed**, and this is the measure of the decision: round 8's free-render
reconciler; round 8/9's `NULL = NULL` unreachable short-circuit; round 9's tenant-confinement gap;
round 10's free-lease theft; round 11's typed `busy`; round 12's once-in-a-lifetime free reservation.
Plus `video_artifacts_free_uq` and the whole free branch of `record_artifact`.

## Consequences

**Deleted:** `reserve_artifact_slot`, `renew_artifact_lease`, the lease columns on `video_artifacts`,
`reserved_by` on `video_generations`, `video_artifacts_free_uq`, and the `pending` artifact state.
`record_artifact` becomes an append with a typed outcome and no fence.

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
  **The implementing slice must state the successor explicitly.** The candidate is the existing
  staged-write order — `putStaged` → `exists` verify → `persistSummary('committed')` → `promote`
  `[VERIFIED: lib/job-queue/summary-handler.ts:173-179]`, with staged bytes under `_staging/…`
  permanently exempt from the sweeper `[VERIFIED: …-design.md:874]`. ⚠ If that is the new guarantee it
  is a **caller obligation**, which is the very class this ADR retires two paragraphs above. Name it,
  or reinstate §8's grace period with an age predicate on the blob. Note the coupling: §8's grace
  period was dropped because *"a blob written but not yet published is unreferenced — that state no
  longer exists"* `[VERIFIED: …-design.md:891-893]`, and that state existed only because rule 19's
  record-first order put a `pending` row down first. **Delete `pending` and the state returns.**
- **The append-only trigger must be tightened in the same change, not after (M1).** It scopes
  immutability by transition `[VERIFIED: schema/04_artifacts.sql:911-913]`, permitting
  `pending → recorded` and `delete an expired pending`. With `pending` gone both are unreachable — but
  they are *permissions*, and an unreachable permission in the one trigger that makes history
  immutable is a fail-open branch waiting for someone to reintroduce the state. Delete both branches.
- **The per-kind attempt ceiling is deleted with no successor, and the numbers disagree (M5).**
  `reserve_artifact_slot` bounds attempts per kind from `guardrail_config`
  `[VERIFIED: schema/04_artifacts.sql:245-252]`. There is no row above for *"how many times may we pay
  for this slot"*. The candidates conflict: `jobs.max_attempts` defaults to **5**
  `[VERIFIED: 0008_jobs_queue.sql:14]` while `summary_max_attempts` is **1**, a difference documented
  as a deliberate product decision `[VERIFIED: schema/04_artifacts.sql:253-260]`. Deleting the
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
- **The FK** `[VERIFIED: schema/04_artifacts.sql:90-91]` — MATCH SIMPLE, added by round 5's M5
  precisely so provenance cannot name a generation that does not exist.

**Decision: address and provenance are different questions and get different mechanisms.**

1. **Address** = `sha256(rendered bytes)` (previous section). A canonical sorted hash of source ids is
   strictly worse — it is an enumeration of inputs, and the section above is the record of this
   codebase getting an enumeration wrong.
2. **Provenance** = a `video_artifact_sources (artifact_id, source_generation_id)` join table, FK'd to
   `video_generations` the same way, `on delete restrict`.

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
  named above** (breaks exclusivity). ⟳ *Round 13 fired this one. The exception is enumerated, not
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
- **Two producers after a lease expiry do not double-append**, for the job kinds — the heartbeat-abort
  row of the concern table is the mechanism. They may still double-*charge*; that residual is
  pre-existing, documented, and tracked to 1D, and is not caused by this decision.
- **The retrospective's central diagnosis stands.** The reservation was designed for a world with one
  mutable address per slot; stable addressing removed that world.

## Dependency note (round 13, M6)

This ADR builds on ADR-0006, which is itself `status: proposed — supersedes ADR-0002 if accepted`.
So ADR-0007 currently rests on an unaccepted decision, and both should be accepted together or not at
all. Recorded because round 13's brief wrongly told both reviewers ADR-0006 was accepted and
non-re-litigable; no finding turned on it, but the next round should not inherit the error.
