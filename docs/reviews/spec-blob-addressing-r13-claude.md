# Round 13 — Claude adversarial DESIGN review of ADR-0007

**Subject:** `docs/adr/0007-artifacts-are-an-append-only-log.md` (status: proposed).
**Question:** is deleting the reservation protocol right, and does what replaces it hold?

**Gate status: NOT downgraded — the schema was EXECUTED.**
`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` ran green against the live
local Postgres (`supabase_db_youtube-playlist-summaries-cloud`) inside a rollback: `ASSERTIONS_OK` /
`ALL_STATEMENTS_OK` / `✅ schema verified (rolled back)`. Findings B1, B2 carry measured transcripts
from a probe run the same way (schema `01+03+04` loaded, probe appended, `rollback`). No repo-tracked
file was modified; the probe lived in the session scratchpad. `git status --porcelain` clean of
tracked changes before and after.

---

## Verdict

**NOT CONVERGED.** 2 Blocking, 4 High, 5 Medium, 1 Low.

The *direction* survives review: I could not break the disjointness claim for the writer pair the ADR
names, and the retrospective's diagnosis (a lock re-solving a problem stable addressing dissolved) is
correct. What does not survive is the ADR **as stated**. Its own falsifier list names two of the two
Blockings, and one of them is reachable in production code today.

---

# BLOCKING

## B1 — There IS a second producer path that does not go through `jobs`, and it produces a PAID kind

ADR-0007's falsifier list: *"A second producer path that does not go through `jobs` (breaks
exclusivity)."* It exists. It is the magazine **model**.

**The caller.** `lib/html-doc/serve-doc.ts:112` calls `generateMagazineModel(...)` — a paid Gemini
call — and writes the artifact at `serve-doc.ts:117` (`writeModelEnvelope`). It is reached from
`lib/html-doc/serve-summary-core.ts:105`, which serves the HTML route (`app/api/html/[id]/route.ts`)
and the cloud PDF route (`app/api/pdf/[id]/route.ts`). It is an **HTTP GET path**. There is no job.
`enqueue_job` / `jobs_idem_active` / `jobs.ever_metered` are not in this call graph at all.

**`model` is a paid kind, not a render.** `schema/04_artifacts.sql:26` maps `slot='model'` →
`kind='model'`; `04_artifacts.sql:95` — `art_paid_has_generation` — puts `'model'` in the paid set
alongside `summary`, `dig`, `digDeeper`.

**Its actual arbiter is a third vocabulary the ADR never mentions.** `reserve_serve_model`
(`supabase/migrations/0012_serve_model_charge.sql:26`, re-created in `0020`) claims a lease in
`serve_model_charge (owner_id, doc_key, day)` with `lease_expires_at` + `attempt_count` bounded by
`max_serve_attempts`, and charges `spend_ledger` per attempt. `doc_key` is
`p_playlist_id::text || '/' || p_video_id` (`supabase/migrations/0020_reservation_release.sql:213`).
`lease_ttl_seconds` defaults to **180** (`0012_serve_model_charge.sql:24`) and there is **no renewal
RPC** on this path.

So ADR-0007's table is false in two rows for one of its four paid kinds:

| ADR-0007 row | For `summary`/`dig` | For `model` |
|---|---|---|
| producer exclusivity ← `jobs_idem_active` | applies | **does not apply** — `serve_model_charge` lease |
| pay at most once ← `jobs.ever_metered` + `reserved_cents` | applies | **does not apply** — `spend_ledger` per attempt |

**MEASURED — the in-flight index is what stops two model producers today, and ADR-0007 deletes it.**

```
--- PROBE A: TODAY. Two serve-path model producers race on ONE model slot ---
 who | outcome  |                token                 | attempts
-----+----------+--------------------------------------+----------
 W1  | reserved | 6178e2d3-b16e-4373-a0e8-3d799c655645 |        1
 who | outcome | token | attempts
-----+---------+-------+----------
 W2  | busy    |       |        1

--- PROBE B: ADR-0007 shape. Delete the reservation -> both producers append ---
DROP INDEX
 paid_model_rows_in_one_slot
-----------------------------
                           2
```

W2 is refused by `video_artifacts_inflight_uq` (`04_artifacts.sql:186-187`), not by anything on
`jobs`. Its own comment is the round-5 measurement of this exact case (`04_artifacts.sql:168-172`):

> *"AT MOST ONE IN-FLIGHT RESERVATION PER SLOT — the money guard. MEASURED by all three round-5
> reviewers independently: without it, two writers insert `pending` for the same slot under their OWN
> generation ids, both succeed (different ids ⇒ the paid unique does not collide), and both call
> Gemini. `count(*) = 2`."*

**This is the sharpest thing round 13 has to say.** ADR-0007's load-bearing claim — *their writes land
on different keys and append different rows* — is **true**, and round 5 measured that its truth is
precisely the mechanism of the double spend. Disjointness of *writes* is not absence of *contention*;
the contended resource was never the key, it was the money. The ADR proves the wrong lemma and reads
it as the conclusion.

**Reachable without any lease expiry.** `doc_key` carries `playlist_id`; the artifact slot
(`workspace_id, video_id, slot`) does not. One video in N playlists of one workspace ⇒ N independent
serve leases against ONE model slot. The spec already measured this and wrote it down —
`docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:2445-2452`, round-1 High H5:
*"G1's cap becomes N times looser"* — and the required re-key of `doc_key` to `(workspace_id,
video_id)` is spec'd at `:2464` and `:2753` and **not implemented** (`0020:213` still concatenates the
playlist id). Second route: a 180 s lease with no renewal expiring under a slow magazine call.

**What would change to fix it.** One of:
1. Add the row. The concern→mechanism table must name `serve_model_charge` as the `model` path's
   exclusivity + spend mechanism, and the ADR must state that deleting `video_artifacts_inflight_uq`
   is safe *only once* `doc_key` is re-keyed to `(workspace_id, video_id)` — i.e. the re-key ships in
   the same slice as the deletion, or the deletion is a money regression rather than a simplification.
2. Or route model generation through `jobs` and make the table true as written. Note this is the
   option ADR-0007 rejects for *sync* ("Route every write through the job queue"), and the rejection
   argument does not transfer: sync replicates, but the serve path genuinely **produces**.

Either is small. Neither is "restore the reservation protocol" — B1 does **not** falsify the decision
to delete it. It falsifies the ADR's justification for deleting it, which is the artifact under review.

---

## B2 — Giving renders a generation-derived address makes the key stop announcing its paid-ness, and §8's sweeper reads nothing else

ADR-0007: *"Every artifact — paid **and free** — has an immutable address derived from an immutable
generation id."* That single sentence collides with the money-safety rule §8 derives for itself.

`§8` (`…-design.md:2095-2100`):

> *"**The paid/free split must be derivable from the KEY ALONE.** An orphan has no manifest entry —
> that is what makes it an orphan — so the sweeper cannot ask the manifest whether a candidate was
> paid. It has to read the key. … any future key that does not announce its own paid-ness is either
> **uncollectable or unsafe to collect**."*

§4.0's classifier is that announcement (`…-design.md:275-282`): paid keys are
`<ws>/videos/<vid>/<gen>/…` and are retained on a 90-day clock; free keys are
`<ws>/videos/<vid>/renders/<name>.{html,pdf}` and are *deleted when not current*. The discriminator is
literally path segment 4: a generation id, or the constant `renders`. Uniform generation-derived
addressing erases exactly that discriminator.

**MEASURED — and both rejections come from constraints ADR-0007 lists as "Kept, unchanged".**

```
--- PROBE C: ADR-0007 renders, under the constraints it lists as "Kept, unchanged" ---
NOTICE: REJECTED [23514] art_key_names_generation  : C1 render + derived generation id,
        at the §4.0 render key <ws>/videos/<vid>/renders/s.pdf
NOTICE: REJECTED [23514] art_paid_has_generation   : C2 render + derived generation id,
        at a GENERATION-shaped key <ws>/videos/<vid>/gRENDER/s.pdf
--- PROBE D ---
NOTICE: ACCEPTED : D1 render, generation_id NULL, §4.0 render key (the status quo)
```

`art_paid_has_generation` (`04_artifacts.sql:95`) is the biconditional the ADR quotes and proposes to
rewrite — expected. `art_key_names_generation` (`04_artifacts.sql:159-161`,
`generation_id is null or split_part(blob_key,'/',4) = generation_id`) is **not mentioned anywhere in
ADR-0007**, and it is what forces the render key under a `<gen>/` segment. ADR-0007 lists "stable
addressing" and "tenant confinement" under **Kept, unchanged**; this measurement says one of them must
change, and changing it is what triggers the §8 collision.

The two exits are both live design work, not implementation detail:

- **Renders keep `renders/` in the key and carry a `generation_id` column anyway.** Then
  `art_key_names_generation` needs a `kind <> 'render'` disjunct — a free/paid branch re-appearing in
  the schema, in the ADR whose headline is *"no free/paid branch in the write path"*. The conflation
  is relocated, not dissolved.
- **Renders move under `<derivedGen>/`.** Then §4.0's classifier cannot tell a render from a paid
  artifact, and by §8's own sentence renders become uncollectable (they accumulate forever — the
  problem §8 exists to solve, and ADR-0006 already flags per-generation HTML as *"accumulation this
  design creates rather than inherits"*, `…-design.md:2113-2114`) or the sweeper becomes unsafe on
  paid bytes.

**A third exit exists and I recommend it** (see H2): make a render's identity `sha256(rendered
bytes)`, keep the `renders/` prefix, and let the *hash*, not a generation segment, be the immutable
address. That satisfies ADR-0007's actual goal — kill `generation_id IS NULL` as a two-meaning
sentinel — with a `render_id` column, while leaving the key shape (and therefore §8) untouched. It
also happens to be what the production PDF path already does.

**Until the ADR picks one and states the consequence for §4.0's table and §8's sweeper, the render
half of the decision is not implementable.** The ADR's own falsifier #3 — *"a render whose identity
cannot be derived deterministically"* — is not the live risk; the live risk is that the derived
identity is fine and the *key shape it forces* breaks a money-safety rule two sections away.

---

# HIGH

## H1 — "Kept, unchanged: … the GC floor" is not established once `pending` is deleted

`video_generations_collectable` requires `g.state = 'complete'` (`04_artifacts.sql:897`). That
predicate is round 9's B1 fix, and its comment records what it cost to find
(`04_artifacts.sql:882-897`): an in-flight reservation has no `video_artifacts_current` row, so its
generation was offered to the sweeper **while the paid call was still running** —
*"collectable WHILE IN FLIGHT: 1 ; sweep collected 1 … Money spent, bytes queued for deletion, no
error anywhere."*

ADR-0007 deletes the `pending` artifact state and `reserve_artifact_slot`. Nothing else in the design
creates a `video_generations` row in state `pending` (`04_artifacts.sql:307-312` is the only
producer). So `g.state = 'complete'` becomes **vacuously true** — the round-9 guard stops guarding
without being deleted. That is retrospective B6's shape ("a guard that never started") arriving by
subtraction: the mutation harness will still find it load-bearing on a fixture that constructs a
`pending` row no caller can produce.

The spec's justification for having no grace period is coupled to the same deletion
(`…-design.md:891-893`):

> *"§8's grace period was justified by 'a blob written but not yet published is unreferenced' — **that
> state no longer exists**, so the grace period now covers only the orphan root set."*

That state no longer existed **because** rule 19's record-first order put a `pending` row down before
the bytes. Delete `pending` and the state exists again.

**There may be a successor and the ADR should say whether it is relying on it.**
`lib/job-queue/summary-handler.ts:173-179` writes through `putStaged` → `exists` verify →
`persistSummary('committed')` → `promote` → `persistSummary('promoted')`, and staged bytes live under
`_staging/<uuid>/<finalKey>`, which the containment table exempts from the sweeper permanently
(`…-design.md:874`). If staged-then-promote-after-record is the new write-window guarantee, that is a
**caller obligation** — precisely the class of rule ADR-0007 is retiring in the same document ("Retired:
§12b's caller obligation"). Name it, or reinstate §8's grace period with an age predicate on the
blob. "Kept, unchanged" is currently false either way, on the one path with no undo.

## H2 — `hash(source_generation_ids, GENERATOR_VERSION)` is an incomplete render identity, and weaker than what production already ships

**`GENERATOR_VERSION` is not the renderer's version.** `lib/html-doc/constants.ts:1-5`:

> *"Bumped whenever the **magazine model's** shape or generation prompt changes, so a cached model
> that predates the change is treated as stale"* — `export const GENERATOR_VERSION = 'magazine-skim v2'`

It versions the paid `model` artifact. It is *reused* as an HTML-cache freshness key
(`lib/html-doc/build-doc-html.ts:56`, `lib/html-doc/render.ts:113`) by convention, not by definition.

**There are three independent generator-version constants, and a PDF's bytes depend on all of them:**

| Constant | `file:line` | Governs |
|---|---|---|
| `GENERATOR_VERSION` | `lib/html-doc/constants.ts:5` | magazine model shape/prompt |
| `PDF_RENDER_VERSION` | `lib/pdf/pdf-render-version.ts:10` | PDF settings **and the pinned Chromium** |
| `DIG_GENERATOR_VERSION` | `lib/dig/generate.ts:15` | dig bodies; drives dig staleness in `lib/html-doc/dig-merge.ts:104` and `lib/html-doc/batch.ts:44`, which decide what a dig-deeper render contains |

`lib/pdf/pdf-render-version.ts:5-9` states the failure mode in its own docstring: *"Bump when ANY PDF
render setting (A4/margins/printBackground/print-media/fonts) OR the pinned Playwright/Chromium
version changes — **these alter PDF bytes WITHOUT changing the HTML**."* Under ADR-0007's hash, a
`PDF_RENDER_VERSION` bump produces **the same address for different bytes**. In an append-only log
that is a silent overwrite (if the writer overwrites) or an unrecordable artifact (if
`video_artifacts_paid_uq` holds) — the brief's "worse than the bug it replaces", exactly.

**And the existing key is already complete.** `lib/pdf/pdf-render-version.ts:22` —
`pdfs/${base}.r${PDF_RENDER_VERSION}.${sha256(html)[:16]}.pdf`, called at
`app/api/pdf/[id]/route.ts:54` on the **nonce-free rendered HTML**. That is content addressing over
the actual output; it subsumes every version constant, present and future, without anyone having to
enumerate them. ADR-0007 would replace a complete identity with an incomplete one.

**Recommendation:** a render's id is `sha256(rendered bytes)`. It is deterministic (falsifier #3
satisfied), complete by construction, needs no version enumeration, and is already in production for
PDFs. Note the one constraint it must respect — `…-design.md:893`: *"A generation id must be chosen
before its content, which rules out content-hash ids for anything on a spend path; §4.1 already
recommends UUIDs there and content hashes only for free re-renders."* Renders are the free side, so
the rule already permits this. But observe what that means for the ADR's thesis: **the free/paid
branch survives, relocated from `record_artifact` into "how do I mint an id".** ADR-0007 should say so
plainly and put the branch somewhere data-driven (a `slot_kind`-style function) rather than in caller
convention, or it is trading one unwritten caller rule for another.

## H3 — "producer exclusivity ← `jobs_idem_active`" is wrong even for the job-driven kinds, and "pay at most once" is true of reservations and false of spend

`jobs_idem_active` (`supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:11-13`)
is `unique (owner_id, playlist_id, video_id, section_id, job_kind, job_version) where status in
('queued','active','completed')`. It dedupes **enqueues**. It says nothing about how many workers are
executing the one job it admits.

The brief's scenario — lease expires, old worker still alive, a reclaimer starts — is answered by a
different mechanism: `lib/job-queue/worker-runner.ts:49-51` heartbeats the lease and calls
`leaseLost.abort()` on a failed or throwing heartbeat, composed into the handler's signal
(`worker-runner.ts:30-32`), and `lib/job-queue/summary-handler.ts:170` re-checks `ctx.signal.aborted`
immediately before the irreversible blob/persist sequence. **So they do not append two paid rows** —
the reclaimed worker stops. Good news for the decision; bad news for the table, which files this under
*execution liveness* and credits exclusivity to an index that cannot provide it. The ADR's own rule
("every concern has exactly one mechanism, and every mechanism serves exactly one concern") is
violated by the table stating it.

The money row needs the same precision. `jobs.ever_metered` + `reserved_cents`
(`0020_reservation_release.sql:25-32`) make the *reservation* durable across retries — they prevent an
under-count on release. They do not prevent a second real Gemini charge, and the code says so:
`lib/job-queue/summary-handler.ts:169` — *"the double-Gemini charge on reclaim is the known
AbortSignal-does-not-stop-billing limitation."* Write the row as "pay-at-most-once **accounting**",
and state that at-most-once *spend* rests on heartbeat-abort plus `guardrail_config`'s per-kind
attempt bounds.

## H4 — The "Open design question" cannot be deferred: `source_generation_id` is load-bearing in two views, and a set is a schema change

ADR-0007 defers set-valued render provenance to the implementing slice. It has two consumers in the
executable schema today, both of which read it as a **scalar**:

- **The ranking view.** `04_artifacts.sql:814-816` —
  `(a.slot = 'summary' or a.source_generation_id is null or a.source_generation_id is not distinct
  from s.generation_id) desc`. With a set, "is this render current w.r.t. its sources" becomes "are
  **all** its sources current", which a scalar column cannot express and a `desc` on one column cannot
  rank.
- **The FK.** `04_artifacts.sql:90-91` — `foreign key (workspace_id, video_id, source_generation_id)
  references video_generations (…)`, MATCH SIMPLE. Round 5 M5 added it precisely so provenance cannot
  name a generation that does not exist. A set needs a join table to keep that guarantee.

**Recommendation: both, and they answer different questions.**

1. **Address** = `sha256(rendered bytes)` (H2). A canonical sorted hash of source ids is strictly
   worse — it is an enumeration of inputs, and enumerations are what H2 shows this codebase gets wrong.
2. **Provenance** = a `video_artifact_sources (artifact_id, source_generation_id)` join table, FK'd to
   `video_generations` the same way, `on delete restrict`.

A sorted hash alone cannot answer *"which generations does this render reference"* without re-deriving
it from data you would need the answer to find — and **GC needs that answer**.
`video_generations_collectable` (`04_artifacts.sql:898-900`) currently checks only
`c.generation_id`, i.e. an artifact's *own* generation; a render referencing a summary generation does
not protect it from collection today either. The join table closes that hole; a hash cannot.

Consequences to write into the ADR, not discover: the ranking rung becomes
`not exists (select 1 … where source not current)`; `video_generations_collectable` gains a second
`not exists` over the join table; `art_summary_has_no_source` (`04_artifacts.sql:107`) becomes a
cardinality-zero rule on the join table rather than a NULL check.

**Why it cannot wait:** all three are schema. The ADR's own sentence — *"it must not be discovered
during implementation"* — is correct and is not satisfied by deferring it to the implementing slice.

---

# MEDIUM

## M1 — Deleting `pending` leaves the append-only trigger with permitted-transition branches for a state that no longer exists

`04_artifacts.sql:911-913` scopes the immutability trigger by transition:

```
update pending -> recorded : rule 19's record-first order    -> PERMITTED
delete an expired pending  : C1's reclaim                    -> PERMITTED
update/delete recorded paid: nothing needs it                -> REJECTED
```

With `pending` gone the first two are unreachable, but they are *permissions*, and an unreachable
permission in the one trigger that makes history immutable is a fail-open branch waiting for someone
to re-introduce the state. ADR-0007's "Not addressed here" paragraph correctly says the append-only
trigger should be what makes history immutable; that makes tightening it part of this decision, not
after it. Delete both branches in the same change.

## M2 — Round 12's H1 (`service_role` DML) genuinely dissolves as an authorization finding; the residue is M1, and the scoping is honest

With no token there is no fence to bypass, so "a future path using a table `UPDATE` bypasses it
entirely" stops being a hole in an authorization mechanism. What still protects content is
**triggers**, and triggers are not bypassed by `service_role` (only RLS is):
`video_generations_freeze_trg` (`03_generations.sql:498-500`) and the append-only trigger
(`04_artifacts.sql:904+`). ADR-0007's refusal to claim H1 closed is honest scoping, **provided** M1
lands with it. Verdict: **dissolves**, conditional on M1.

## M3 — The guard-coverage ratchet's blind spots survive ADR-0007 untouched, and the deletion will move its numbers for unrelated reasons

Round 12's Medium (RLS policies omitted; 26 guards unclassified while the success line prints *"every
guard classified"*) is orthogonal to this decision and unaffected by it. It is called out here because
deleting ~600 lines changes the guard census wholesale — which is the moment a stale ratchet gets
re-baselined instead of fixed. Fix the enumeration (`scripts/check-guard-coverage.py`) **before** the
implementing slice, or the re-baseline launders it.

## M4 — The population ratchet ("proves two INSERTs, not two callers") survives and becomes MORE load-bearing, not less

Deferred in rounds 10 and 12. Under ADR-0007 "two callers on one slot" stops being an error case and
becomes **the designed state** — so this ratchet is now the only instrument asserting that the
designed state is exercised at all. Carrying it a fourth round while its subject matter is promoted
from edge case to core semantics is how a known weakness becomes furniture (round 12's own words).

## M5 — The per-kind attempt ceiling is deleted with no successor named, and the numbers disagree

`reserve_artifact_slot` bounds attempts per kind from `guardrail_config` (`04_artifacts.sql:245-252`),
MEASURED from the live config on 2026-08-08 as `summary=1, dig=1, serve=5`. ADR-0007's table has no
row for "how many times may we pay for this slot". The candidates disagree: `jobs.max_attempts`
defaults to **5** (`supabase/migrations/0008_jobs_queue.sql:14`) while `summary_max_attempts` is
**1**, and the schema comment at `04_artifacts.sql:253-260` documents that difference as a deliberate
product decision owned by whoever owns the guardrail numbers. Deleting the artifact-layer bound
silently promotes the job-layer bound from 1 to 5 for summaries. State which number wins, in the ADR.

---

# LOW

## L1 — Falsifier #1, as written, fires on the replicator the ADR is defending

> *"A caller that writes an artifact for a generation it did not create (breaks the disjointness claim)."*

That is the definition of a replicator: `transferClassA` (`lib/cloud-sync/sync-run.ts:372-394`) copies
a body it did not produce. The ADR's own A1/A2 argument depends on this being fine. The falsifier
means something narrower — *a caller that writes an artifact for a generation another writer is
concurrently creating* — and in the one section written to be mechanically checkable, the difference
matters. Reword.

---

# Round-12 leftovers — adjudication table

| Finding | Fate under ADR-0007 | Why |
|---|---|---|
| **H1** `service_role` DML bypasses the fence | **Dissolves** (conditional on M1) | No fence to bypass; content immutability moves to triggers, which `service_role` does not bypass. ADR-0007's scoping is honest — see M2 |
| **H2** `video_artifacts_generation_complete` misclassified SHAPE | **Dissolves** | It raised in B1 because a *reclaimed* caller met a generation reserved by someone else. With no reservation and no reclaim, a producer completes its own generation in the same transaction as its append. ⚠ Its SHAPE/SEQUENCE verdict must be **re-derived**, not inherited — a classification is a claim about the surviving mechanism |
| **H3** `completed_by_another` returned to the writer that completed it | **Dissolves** | The outcome exists to distinguish reservation losers. With no reservation there is no "another". `record_artifact`'s "typed outcome and no fence" must not re-introduce it |
| **M** guard ratchet omits RLS policies / 26 guards | **Survives** | Orthogonal; and the deletion will move its numbers — see M3 |
| **M** population ratchet proves two INSERTs, not two callers | **Survives, and worsens in importance** | See M4 |
| **M** a free slot can be reserved once in its life | **Dissolves** | No free reservation exists |
| **M** three `pending` biconditionals labelled bare SHAPE | **Dissolves** | `art_pending_is_leased` / `art_pending_has_token` / `art_pending_has_reserved_at` (`04_artifacts.sql:96,101,102`) are deleted with the state |

---

# What I could NOT break

Recorded so the next round does not re-run it.

- **The disjointness claim for producer × replicator holds.** `transferClassA`
  (`lib/cloud-sync/sync-run.ts:372-394`) reads the winner's body and writes it at the winner's key; it
  makes no Gemini call and takes no reservation. Under generation-derived addressing a producer's new
  generation and a replicator's existing one are different keys and different rows. I found no path by
  which sync mints a generation id.
- **No third paid cloud producer beyond the model.** Full sweep of `generateSummary` /
  `generateMagazineModel` / `generateDig` / `extractQuickView` call sites across `lib/ app/ worker/
  scripts/`: summary → `lib/job-queue/summary-handler.ts:114` (job); dig →
  `lib/job-queue/dig-handler.ts:100` (job, enqueued at `app/api/videos/[id]/dig/[sectionId]/route.ts:61`);
  model → `lib/html-doc/serve-doc.ts:112` (**serve path — B1**). `app/api/videos/[id]/regenerate/route.ts:66`
  and `app/api/quick-view/backfill/route.ts:62` also call Gemini but are **local-only** — both require
  `outputFolder` and neither branches on `STORAGE_BACKEND`. No `scripts/*.ts` writes an artifact.
- **The two-producers-after-lease-expiry case does not double-append**, for the job kinds — see H3 for
  the mechanism that actually prevents it.
- **The retrospective's central diagnosis (A5/A6) is correct.** The reservation was designed for a
  world with one mutable address per slot; stable addressing removed that world. Nothing I measured
  contradicts it.

---

# Verdict

**NOT CONVERGED.**

Blocking reasons:

- **B1** — ADR-0007's own falsifier *"a second producer path that does not go through `jobs`"* fires:
  the magazine `model` is a paid kind produced on the serve path (`lib/html-doc/serve-doc.ts:112`),
  governed by `serve_model_charge`, whose `doc_key` still carries `playlist_id`
  (`0020_reservation_release.sql:213`) while the artifact slot does not. Two rows of the
  concern→mechanism table are false for it, and the fence being deleted is measurably the only thing
  stopping two paid model generations in one slot (probe A/B).
- **B2** — Uniform generation-derived addressing for renders makes the blob key stop announcing its
  paid-ness, which §8 states is *"either uncollectable or unsafe to collect"*
  (`…-design.md:2097-2100`). MEASURED: a render carrying a generation id is rejected by
  `art_key_names_generation` at the §4.0 render key and by `art_paid_has_generation` at a
  generation-shaped key — both listed by the ADR as **Kept, unchanged**.

Neither Blocking argues for restoring the reservation protocol. Both say the ADR's *justification* is
incomplete in ways that would be discovered during implementation — which is the specific failure this
round exists to prevent. Fix B1 by naming the `model` path's real mechanism and shipping the `doc_key`
re-key in the same slice; fix B2 by addressing renders on `sha256(rendered bytes)` under the existing
`renders/` prefix, which also settles H2 and half of H4.
