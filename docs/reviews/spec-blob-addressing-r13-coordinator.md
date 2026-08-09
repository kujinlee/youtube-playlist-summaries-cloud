# Round 13 — coordinator adjudication

**Verdict: NOT CONVERGED.** 2 Blocking, 4 High, 6 Medium, 1 Low. Round 14 mandatory.

**This was the first DESIGN review of the series** — triggered by the escalation rule armed in PR #64
(two consecutive rounds whose findings were caused by the previous round's fixes ⇒ escalate from *fix*
to *redesign*, and review the redesign's premises rather than hunt defects in the mechanism it
deletes). The rule fired correctly and bought something the previous twelve rounds could not: both
Blockings are about **the ADR's justification**, not about SQL.

**The headline, and it is good news:** *the decision to delete the reservation protocol survives.*
Neither Blocking argues for restoring it. Both reviewers independently failed to break the
producer × replicator disjointness claim, and both endorsed the retrospective's diagnosis. What does
not survive is ADR-0007 **as stated** — its concern→mechanism table is false in two rows, and its
render half is not implementable as written.

Gate strength: **not downgraded.** Both reviewers executed `verify-schema.sh` against live Postgres
inside a rollback (`ASSERTIONS_OK` / `ALL_STATEMENTS_OK`). Claude additionally ran measured probes
(A–D) from the scratchpad; the working tree was clean before and after. Codex reached `gpt-5.5` after
`gpt-5.6-{sol,terra,luna}` returned HTTP 400 — the wrapper's fallthrough worked as designed.

---

## Where the reviewers SPLIT — adjudicated by reading the code

This is the fourth time in this project's history that the two reviewers disagreed. The standing
lesson is that disagreement is the signal and the adjudicator must read the code. I did.

**Codex Blocking:** lease expires while W1 is still in Gemini → W2 sweeps, reclaims, and *"both
producers may write different new generation ids… and append rows."*

**Claude H3:** they do **not** double-append — `lib/job-queue/worker-runner.ts:48-51` aborts
`leaseLost` on a failed/throwing heartbeat, composed into the handler signal at `:30-32`, and
`lib/job-queue/summary-handler.ts:170` re-checks `ctx.signal.aborted` immediately before the
irreversible blob/persist sequence.

**Adjudication — both are partly right, and the split is exactly along rows-vs-money.** I verified
`worker-runner.ts:48-51` and `summary-handler.ts:170` directly: Claude is correct that the second
producer does not append. But the Gemini call has *already been billed* by the time the abort fires,
which the code says in its own words at `summary-handler.ts:166-169` — *"the double-Gemini charge on
reclaim is the known AbortSignal-does-not-stop-billing limitation."* So:

- Codex's **stated consequence** (two appended rows) is **REFUTED**.
- Codex's **underlying claim** — the row *"producer exclusivity ← `jobs_idem_active`"* is false — is
  **CONFIRMED**, independently, by all three of us.
- The residual double *spend* is **pre-existing, documented, and tracked to 1D**. ADR-0007 neither
  causes nor worsens it. It must not be charged to this decision.

**Disposition: Codex's Blocking is merged into H3 (High), not carried as Blocking.** It is a true
finding about a false table row with an overstated consequence.

---

## BLOCKING — both from Claude, both verified by me

### B1 — There is a second producer path that does not go through `jobs`, and it produces a paid kind

ADR-0007's own falsifier list says *"a second producer path that does not go through `jobs` breaks
exclusivity."* It exists: the magazine **model**.

Verified by hand:
- `lib/html-doc/serve-doc.ts:112` calls `generateMagazineModel(...)` — a paid Gemini call — on an
  **HTTP GET** path (`serve-summary-core.ts:105` → `app/api/html/[id]/route.ts`, `app/api/pdf/[id]/route.ts`).
  There is no job. `jobs_idem_active` / `jobs.ever_metered` are not in that call graph.
- `model` is a **paid** kind: `schema/04_artifacts.sql:26` maps `slot='model'` → `kind='model'`, and
  `art_paid_has_generation` (`:95`) puts it in the paid set.
- Its real arbiter is a **third vocabulary the ADR never names**: `reserve_serve_model` /
  `serve_model_charge`, keyed on `doc_key` — and `0020_reservation_release.sql:213` composes that as
  `p_playlist_id::text || '/' || p_video_id`. **Verified: it carries `playlist_id`; the artifact slot
  `(workspace_id, video_id, slot)` does not.**

So one video in N playlists of one workspace ⇒ N independent serve leases against ONE model slot, with
no lease expiry required. The spec already measured this as round-1 H5 (`…-design.md:2445-2452`) and
specs the required `doc_key` re-key at `:2464` and `:2753` — **never implemented**.

Claude's probes A/B measure that `video_artifacts_inflight_uq` is what stops two paid model producers
today (`W2 → busy`), and that dropping it yields `paid_model_rows_in_one_slot = 2`.

**The sharpest sentence of the round, and I endorse it:** the load-bearing claim (*writes land on
different keys and append different rows*) is **true**, and round 5 measured that its truth is
precisely the *mechanism* of the double spend. Disjointness of writes is not absence of contention —
the contended resource was never the key, it was the money. **The ADR proves the wrong lemma and reads
it as the conclusion.**

*(I independently reached the same `doc_key`-vs-slot mismatch before either review landed, via
`jobs_idem_active`'s `playlist_id` and `workspace_videos`' `(workspace_id, video_id)` primary key at
`03_generations.sql:64`. Claude's route through `serve_model_charge` is strictly stronger, because the
serve path has no job at all.)*

### B2 — A generation-derived render address stops the key announcing its paid-ness, and §8's sweeper reads nothing else

Verified: §8 rule 1 (`…-design.md:2096-2100`) states *"the paid/free split must be derivable from the
KEY ALONE… any future key that does not announce its own paid-ness is either uncollectable or unsafe
to collect."* The discriminator is path segment 4 — a generation id, or the constant `renders`.
Uniform generation-derived addressing erases it.

`art_key_names_generation` (`04_artifacts.sql:159-161`) — which ADR-0007 never mentions, while listing
"stable addressing" under **Kept, unchanged** — forces the render key under a `<gen>/` segment.
Claude's probes C/D measure both rejections. Either the constraint changes (re-introducing a free/paid
branch into the schema of the ADR whose headline is *"no free/paid branch"*) or renders become
uncollectable.

---

## HIGH

- **H1 — "Kept, unchanged: the GC floor" is not established once `pending` is deleted.**
  `video_generations_collectable` requires `g.state = 'complete'` (`04_artifacts.sql:897`) — round 9's
  B1 fix, whose comment records the measurement (*"collectable WHILE IN FLIGHT: 1… Money spent, bytes
  queued for deletion, no error anywhere"*). Delete `pending` and nothing produces that state, so the
  predicate goes **vacuously true**: the guard stops guarding without being deleted. Retrospective B6's
  shape ("a guard that never started"), arriving by subtraction. The mutation harness will still score
  it load-bearing against a fixture no caller can produce.
- **H2 — the render hash is incomplete, and weaker than what production already ships.** There are
  **three** independent version constants (`GENERATOR_VERSION` `lib/html-doc/constants.ts:5`,
  `PDF_RENDER_VERSION` `lib/pdf/pdf-render-version.ts:10`, `DIG_GENERATOR_VERSION` `lib/dig/generate.ts:15`),
  and `pdf-render-version.ts:5-9` states that its bumps *"alter PDF bytes WITHOUT changing the HTML."*
  Under ADR-0007's hash that is **the same address for different bytes**. Codex found this too (as
  Medium); Claude's framing is stronger and I take the High.
- **H3 — the table is wrong for the job kinds too** (merged with Codex's Blocking, above).
  `jobs_idem_active` dedupes **enqueues**, not executions; at-most-once *spend* rests on
  heartbeat-abort plus `guardrail_config` bounds, and the money row is "pay-at-most-once **accounting**".
- **H4 — the "Open design question" cannot be deferred.** `source_generation_id` is read as a scalar
  by the ranking view (`04_artifacts.sql:814-816`) and by a MATCH SIMPLE FK (`:90-91`, round 5's M5).
  A set is a schema change in both. The ADR's own sentence — *"it must not be discovered during
  implementation"* — is not satisfied by deferring it to the implementing slice.

## MEDIUM

M1 append-only trigger keeps permitted-transition branches for a deleted state (fail-open by
subtraction) · M2 round-12 H1 dissolves *conditional on M1* · M3 guard-ratchet blind spots survive and
a ~600-line deletion is exactly when a stale ratchet gets re-baselined instead of fixed · M4 the
population ratchet worsens in importance, since "two callers on one slot" becomes the *designed* state
· M5 the per-kind attempt ceiling is deleted with no successor and the numbers disagree
(`summary_max_attempts=1` vs `jobs.max_attempts=5`) · M6 (coordinator) ADR-0006 is itself
`status: proposed`, so ADR-0007 rests on an unaccepted decision — my round-13 brief wrongly told both
reviewers it was accepted and non-re-litigable.

## LOW

L1 falsifier #1 as worded fires on the replicator the ADR is defending; reword to *"a generation
another writer is concurrently creating."*

---

## Round-12 leftovers

Adjudicated in full in the Claude review's table and endorsed here: **H1 dissolves** (conditional on
M1 — `service_role` does not bypass triggers, only RLS), **H2 dissolves** but its SHAPE/SEQUENCE
verdict must be **re-derived rather than inherited**, **H3 dissolves**, the free-slot and `pending`
biconditional Mediums **dissolve**, and the two ratchet Mediums **survive** (M3, M4).

---

## What round 13 could NOT break — recorded so round 14 does not re-run it

- **Producer × replicator disjointness holds.** `transferClassA` (`lib/cloud-sync/sync-run.ts:372-394`)
  copies a body it did not produce, makes no Gemini call, mints no generation id.
- **No third paid cloud producer beyond the model.** Full sweep of `generateSummary` /
  `generateMagazineModel` / `generateDig` / `extractQuickView` call sites; the two other Gemini callers
  (`app/api/videos/[id]/regenerate/route.ts:66`, `app/api/quick-view/backfill/route.ts:62`) are
  local-only. No `scripts/*.ts` writes an artifact.
- **The retrospective's central diagnosis is correct.** The reservation was designed for a world with
  one mutable address per slot; stable addressing removed that world.

---

## The one fork this round cannot settle autonomously

**B2/H2/H4 converge on a single fix both reviewers recommend** — a render's identity is
`sha256(rendered bytes)`, keeping the `renders/` prefix, with provenance in a
`video_artifact_sources` join table. It is deterministic, complete by construction, needs no version
enumeration, is already in production for PDFs (`lib/pdf/pdf-render-version.ts:22`), and leaves §8
untouched. `…-design.md:893` permits content-hash ids on the free side. **Taken as settled.**

**B1 does not have an obviously-superior option, and it is a product decision:**

1. **Name `serve_model_charge` in the table** and ship the `doc_key` re-key to `(workspace_id,
   video_id)` in the same slice as the deletion. Small, keeps serving synchronous.
2. **Route model generation through `jobs`** and make the table true as written. Note ADR-0007 rejects
   this for *sync* — but that rejection does not transfer, because sync replicates while the serve
   path genuinely produces. Cost: an HTTP GET would wait on a queued job, changing serve latency and
   the user-visible flow.

Option 2 changes product behaviour, so it is the human's call, not the coordinator's.
**Escalated per the Conditional-AFK policy: a genuine fork the spec did not settle.**
