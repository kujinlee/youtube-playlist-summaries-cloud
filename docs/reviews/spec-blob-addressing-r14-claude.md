# Round 14 — adversarial design review of ADR-0007 (revised)

**Subject:** `docs/adr/0007-artifacts-are-an-append-only-log.md` @ `fix/adr-0007-round-13-findings` (474 lines, PR #65)
**Reviewer:** Claude (adversarial)  **Date:** 2026-08-09
**Target per brief:** round 13's own fixes, not round 13's findings.

## Gate status — the suite RAN (not a downgraded gate)

`docs/superpowers/specs/2026-08-03-stable-blob-addressing/verify-schema.sh` executed against live local
Postgres (`supabase_db_youtube-playlist-summaries-cloud`) inside a rollback:

```
NOTICE:  ok (coverage): every artifact_kind has a slot written twice — the SEQUENCE case is exercised
ASSERTIONS_OK
ALL_STATEMENTS_OK
ROLLBACK
✅ schema verified (rolled back)
```

Finding **B3** below is additionally backed by a measured transcript against the same live Postgres.
No repo-tracked file was modified; the probe ran in a throwaway schema inside `begin … rollback`.

**Verdict: NOT CONVERGED — 4 Blocking, 4 High, 4 Medium, 1 Low.**

---

## Blocking

### B1 — The ADR contains TWO contradictory copies of its central table, and the second is the pre-round-13 version round 13 proved false

`## What already serves each concern` appears **twice**: at `0007-…md:71` (corrected) and again at
`0007-…md:98` (uncorrected). The `We decided this because the reservation protocol…` paragraph is
likewise duplicated verbatim at `:24-28` and `:30-34`.

The second table is not a stale duplicate of the same content — it is the version whose rows round 13's
B1 refuted, reinstated at equal authority:

| ADR line | Second table says | What round 13 established (`:92-96`) |
|---|---|---|
| `:105` | producer **exclusivity** ← `jobs_idem_active` | *"`jobs_idem_active` dedupes **enqueues**; it says nothing about how many workers execute the one job it admits, so it could never have provided execution exclusivity"* |
| `:107` | pay at most once ← `ever_metered` + `reserved_cents` | *"`ever_metered`/`reserved_cents` govern accounting, not spend"* |

`:100-101` also states the rule with **no exception** — *"Every concern has exactly one mechanism, and
every mechanism serves exactly one concern"* — directly contradicting `:78`'s *"`model` is a standing
exception"*, which is the ADR's own headline qualification at `:17-19`.

This is a normative document. An implementing slice that reads §"What already serves each concern" has
even odds of reading the refuted one, and `:113-116` then tells it the reservation *"re-implemented rows
1–4"* — row numbers that only resolve against the false table.

**Introduced by round 13, measured:**

```
$ git show master:docs/adr/0007-…md | grep -c "^## What already serves each concern"   → 1
$ grep -c "^## What already serves each concern" docs/adr/0007-…md                      → 2
$ git show master:docs/adr/0007-…md | grep -c "We decided this because the reservation" → 1
$ grep -c "We decided this because the reservation" docs/adr/0007-…md                   → 2
```

**Why it matters beyond tidiness — the doc gate is GREEN on it:**

```
$ python3 scripts/check-docs.py
Documentation integrity OK
```

`scripts/check-docs.py` is the documentation-integrity gate and it does not detect a duplicated `##`
heading carrying contradictory content. This is the retrospective's own shape — *an instrument whose
success line claims more than its input covers* — arriving in the document that names that shape, one
day after the ADR itself documented the identical failure in `check-vocabulary-collisions.py` at
`:189-209`.

**Fix:** delete `:98-116` and `:30-34`. Add a duplicate-`##`-heading check to `scripts/check-docs.py`.

---

### B2 — The GC-floor successor cannot cover `model`: round 13's fix #7 is inapplicable to round 13's fix #4

`0007-…md:368-371` names the successor to the GC floor:

> *"The candidate is the existing staged-write order — `putStaged` → `exists` verify →
> `persistSummary('committed')` → `promote` `[VERIFIED: lib/job-queue/summary-handler.ts:173-179]`"*

That citation is correct — `summary-handler.ts:173-179` is exactly that sequence. But `model` — the kind
the *same ADR* carves out at `:118-187` as the standing exception, the one paid producer with no job —
**does not use staged→promote at all**:

```
lib/html-doc/model-store.ts:51    await blobStore.put(principal, MODEL_KEY(base), serialize(envelope), 'application/json');
```

and its docblock says so deliberately:

```
lib/html-doc/model-store.ts:42-43  (The staged→promote protocol is create-if-absent and stays
                                    on the BlobStore for the worker's multi-blob MD commit — it
                                    is NOT used for the model.)
```

confirmed independently at `lib/html-doc/serve-doc.ts:102-104`: *"The model uses writeModelEnvelope
(plain `put` → `upload(upsert:true)`), **NOT** staged→promote"* — and that is a **requirement**, not an
accident: a regenerated model must overwrite the stale blob or *"re-reserve + re-charge every view until
K, then 503"*.

So the chain is:

1. Delete `pending` (ADR `:346-347`) ⇒ nothing produces a `pending` generation
   (`schema/04_artifacts.sql:307-312` is the only producer — verified) ⇒
2. `video_generations_collectable`'s floor `and g.state = 'complete'`
   (`schema/04_artifacts.sql:897` — verified) goes **vacuously true**; the ADR states this itself at
   `:363-366` ⇒
3. the named successor covers `summary` (and `dig`, via the same handler shape) but **not `model`** ⇒
4. a `model` generation is collectable *while its paid Gemini call is in flight* — precisely round 9's
   B1, whose measured transcript is preserved in the schema comment at
   `schema/04_artifacts.sql:888-892`: *"Money spent, bytes queued for deletion, no error anywhere."*

`model` is the worst kind to leave uncovered: no job, no staging, no lease renewal RPC
(`0012_serve_model_charge.sql:24`, 180 s TTL), and a paid Gemini call on an HTTP GET.

Two of round 13's own fixes are mutually inconsistent, and **neither section references the other** —
the `model` section never mentions the GC floor, and the GC-floor section never mentions `model`. This
is the signature failure mode, occurring *within a single round's fix set* rather than between rounds.

**Fix:** the successor must be stated per-kind, and `model`'s cannot be staged-write ordering. Either
give the serve path a durable in-flight marker the sweeper honours (`serve_model_charge`'s live lease is
the obvious candidate — it already exists and is already the `model` arbiter), or reinstate §8's grace
period with an age predicate for keys the staged protocol does not cover.

---

### B3 — `video_artifact_sources … on delete restrict` makes a workspace, and therefore a user account, undeletable — MEASURED

`0007-…md:416-417` introduces the join table with *"FK'd to `video_generations` the same way,
`on delete restrict`."*

The live cascade chain, quoted:

```
schema/01_workspaces.sql:13    owner_id   uuid not null references profiles(id) on delete cascade,
schema/03_generations.sql:49   workspace_id uuid not null references workspaces(id) on delete cascade,
schema/03_generations.sql:362-363   foreign key (workspace_id, video_id)
                                      references workspace_videos (workspace_id, video_id) on delete cascade,
```

A `RESTRICT` child aborts a parent delete **even when that parent delete is itself a cascade step**.
Measured against live Postgres (throwaway schema, `begin … rollback`, structural analogue of the four
FKs above):

```
--- attempting: delete the workspace (cascade must reach gens, which RESTRICT guards) ---
NOTICE:  RESULT: workspace DELETE FAILED [23503] update or delete on table "gens"
         violates foreign key constraint "art_sources_gen_id_fkey" on table "art_sources"
 workspaces_remaining
----------------------
                    1
```

Once **any** render carries a provenance row, `delete from workspaces` fails, and because
`workspaces.owner_id` cascades from `profiles`, `delete from profiles` fails too. Account deletion —
an intended operation, given the `on delete cascade` the schema already spends a column on — breaks.

**The caller is real:** this is the account-erasure path, not a hypothetical.

**Fix:** `on delete cascade` on `video_artifact_sources`. Provenance is meaningless once the generation
is gone. `RESTRICT` was chosen to stop GC collecting a referenced generation, but the ADR *already*
provides that protection by a different mechanism at `:428` — *"`video_generations_collectable` gains a
second `not exists` over the join table."* Keeping `RESTRICT` as well is two mechanisms for one concern
in a table introduced by a fix, and the redundant one is the one that breaks a live path.

---

### B4 — `render_id` appears nowhere in the address, so renders stay overwritable and the founding conflation does not dissolve

This is the brief's item 1, and the mechanical answer is: **nothing distinguishes two renders of one
slot at the blob layer.**

The ADR fixes render identity at `:253-254`:

> *"A render's identity is `sha256(rendered bytes)`, carried in a `render_id` column, and the key keeps
> its existing `<ws>/videos/<vid>/renders/…` prefix."*

Trace it:

- **Nothing binds `render_id` to `blob_key`.** The only key/column constraint is
  `schema/04_artifacts.sql:159-160`:
  ```sql
  constraint art_key_names_generation check (
    generation_id is null or split_part(blob_key, '/', 4) = generation_id)
  ```
  For a render `generation_id is null`, so this is **vacuously true**. `art_key_names_workspace`
  (`:154-157`) constrains segments 1–3 only.
- **The replacement uniqueness permits N rows on one key.** `:329-330` replaces
  `video_artifacts_free_uq` with uniqueness on `(workspace_id, video_id, slot, render_id)`. Two renders
  with different bytes ⇒ two `render_id`s ⇒ two rows — **both free to carry the same `blob_key`**.
- **The blob write overwrites.** Renders are written with `put`: `lib/pdf/generate-doc-pdf.ts:96`
  `await blobStore.put(principal, key, buf, 'application/pdf')`, where `key` is the caller-supplied
  parameter at `:48`.

Today, `video_artifacts_free_uq` (`schema/04_artifacts.sql:164-165`, *one row per slot, overwritable*)
at least keeps row and blob **1:1**, so "overwritable" is coherent. The proposal multiplies rows while
leaving the address mutable: N rows per slot, one key, only the last write's bytes present, and N−1 rows
pointing at bytes that no longer exist. For an **append-only log** that is strictly worse than the
status quo it replaces.

This falsifies the load-bearing sentence of the dissolution argument at `:320-323`:

> *"A render addressed by `sha256(rendered bytes)` is immutable: re-rendering identical bytes lands on
> the same address (nothing to overwrite) and any byte change lands on a new one (a new row). So renders
> stop being overwritable…"*

A render is **not** "addressed by" `sha256(rendered bytes)` under this proposal — it is *identified* by
it in a column, while remaining *addressed* by an unchanged key. The sentence silently swaps address for
identity, and everything at `:310-337` — the re-answer to why `generation_id IS NULL` now means exactly
one thing, i.e. the ADR's stated reason for existing — rests on it.

**Secondary, same root:** `:254` says the key keeps its *"existing"* `renders/…` prefix.
`grep -rn "renders/" --include=*.ts lib/ app/ worker/` returns **zero hits**. Production render keys are
`pdfs/${base}.r${PDF_RENDER_VERSION}.${hash}.pdf` (`lib/pdf/pdf-render-version.ts:22`) and
`models/${base}.json` (`lib/html-doc/model-store.ts:31`). `renders/` exists only in the spec table
(`…-design.md:280-281`) and the assertion fixtures (`schema/05_assert.sql:162, 266, 367, …`). "Existing"
is true of the spec, not of the code the sentence appears to describe.

**Fix:** put the render identity **in the address** — `…/renders/<name>.<render_id>.<ext>` — and add the
free-side mirror of `art_key_names_generation` binding segment 5 to `render_id`, so the uniqueness index
and the key agree. That also resolves the ordering objection: the bytes exist before the final key is
chosen, so the render must be written staged-then-named (or written to a temp key and copied), which is
a real cost the ADR must state rather than a property it can assert. See H1 — the cache-probe consequence
is the reason production does not do this today.

---

## High

### H1 — The evidence cited for "content addressing is complete by construction" contradicts the claim

`0007-…md:287-291`:

> **"Content addressing is complete by construction, and production already does it."**
> `[VERIFIED: lib/pdf/pdf-render-version.ts:22]` keys PDFs as
> `pdfs/${base}.r${PDF_RENDER_VERSION}.${sha256(html)[:16]}.pdf` … **"It subsumes every version
> constant, present and future, without anyone maintaining a list."**

The citation resolves, but it does not support the claim — it refutes it:

- The hash is of the **input HTML**, not the rendered output:
  `lib/pdf/pdf-render-version.ts:21` — `crypto.createHash('sha256').update(htmlNonceFree, 'utf8')`,
  called at `app/api/pdf/[id]/route.ts:54` on the output of `renderMagazineHtml(...)` (`:53`), which is
  the PDF renderer's **input**.
- `.r${PDF_RENDER_VERSION}` is a **separate literal segment in the same key**, present precisely because
  the hash does *not* subsume it.
- The same file's docblock — which the ADR quotes two paragraphs earlier at `:281-283` to reject the
  enumeration approach — says so: `lib/pdf/pdf-render-version.ts:5-9`, *"Bump when ANY PDF render setting
  … OR the pinned Playwright/Chromium version changes — these alter PDF bytes WITHOUT changing the HTML
  … The unit test cannot detect a MISSED bump … treat bumping as a review-time checklist item."*

So production is **input-addressing plus a hand-maintained version constant** — verbatim the enumeration
the ADR rejects as *"only as complete as the enumeration"* (`:284-285`). The ADR cites the codebase's
clearest example of the failure mode as proof of the cure.

**This is load-bearing, not a footnote.** It is the entire warrant for choosing `sha256(rendered bytes)`
over the round-13-rejected alternative, and it is the reason the ADR believes the choice is free. It is
not free: `app/api/pdf/[id]/route.ts:60` (`blobStore.get(principal, key)`) is a **cache probe that must
compute the key before rendering**, and `generateDocPdf(html, principal, key, …)`
(`lib/pdf/generate-doc-pdf.ts:45-50`) takes the key as an *input*. An identity that cannot be computed
until the bytes exist cannot be the cache key of a path whose whole purpose is to avoid producing the
bytes.

**Fix:** delete the "production already does it" claim, and state the real trade: output-hash addressing
requires rendering before naming, so the render cache needs a **two-level** scheme — an input-derived
probe key (what production has) plus an output-derived identity (what the log needs). Say which is the
`blob_key` and which is the `render_id`, and say what the probe costs.

### H2 — The rewritten concern-table row 2 claims *exclusivity* from a mechanism whose own comment says it is a bounded window

`0007-…md:83`:

> | producer **execution** exclusivity | lease + heartbeat → `leaseLost.abort()`, re-checked immediately
> before the irreversible write | `[VERIFIED: worker-runner.ts:48-51, :30-32]` +
> `[VERIFIED: summary-handler.ts:170]` |

Both tags resolve correctly (`worker-runner.ts:48-51` is the heartbeat→`leaseLost.abort()` interval;
`summary-handler.ts:170` is `if (ctx.signal.aborted) throw new DOMException(…)`). But the comment
**immediately above** the cited line states the opposite of "exclusivity":

```
lib/job-queue/summary-handler.ts:166-169
  // Shrink the stale-worker write window: if the lease was lost / SIGTERM fired during summarize,
  // don't start the irreversible blob/persist sequence. (Full lease-fencing of persist_summary is
  // deferred — after FIX 1/FIX 2 a stale write is idempotent and non-corrupting; the double-Gemini
  // charge on reclaim is the known AbortSignal-does-not-stop-billing limitation, tracked to 1D.)
```

It is a TOCTOU window-narrowing: nothing prevents the lease from being lost between the check at `:170`
and the writes at `:173-179`. The code says full fencing is **deferred** and that stale writes are
tolerated because they are *idempotent*, which is a different guarantee — merge-safety, not exclusivity.

Round 13's B1 corrected two rows for exactly this — claiming a guarantee the mechanism does not make —
and the row written to replace them carries the same defect. The ADR is honest about this elsewhere
(`:85` *"Bounded, not zero"*; `:463-465` *"They may still double-charge"*), which makes row 2's flat
"exclusivity" a local regression against the ADR's own standard, and it is the row falsifier #2 (`:440`)
is checked against.

**Fix:** reword to what the code provides — *"producer execution: stale-writer window bounded by
lease+heartbeat abort; stale writes are idempotent, not excluded (full fencing deferred, 1D)"* — and
recheck falsifier #2 against the weaker statement.

### H3 — SUM can 503 a document that renders today, and the rule quoted to license SUM does not govern this question

`0007-…md:156-160` justifies the `attempt_count` merge:

> *"The governing rule is the serve path's own: 'over-count is safe, under-count is the bug'
> `[VERIFIED: lib/html-doc/serve-doc.ts:105-109]`."*

The tag resolves, but the quoted rule is scoped to **settle-time refunding of a single attempt whose
metering status is uncertain** — `serve-doc.ts:105-109` reads *"a throw refunds ONLY a positively-not-
metered class-A failure under an open gate … Anything else (metered, non-class-A, gate closed) keeps the
charge."* That is "when in doubt, do not refund." It says nothing about **merging independent counters**,
where over-count does not cost money — it **denies service**.

Measured consequences:

- `max_serve_attempts` defaults to **5** and is per `(owner_id, doc_key, day)`
  (`0012_serve_model_charge.sql:21`, `:12-13`).
- Re-keying `doc_key` from `playlist/video` (`0012_serve_model_charge.sql:53`) to `workspace/video`
  collapses N playlist rows into one. A video in 3 playlists at 2 attempts each SUMs to 6 > 5.
- The resulting outcome is `attempts_exhausted` → **HTTP 503**:
  `lib/html-doc/serve-summary-core.ts:121` — *"503, 'temporarily unavailable, try later'"*.
- That is the **one serve outcome with no stale fallback.** D5's title-stable stale serve is reachable
  only from `owner_over_budget` (`lib/html-doc/serve-doc.ts:90-95`). The ADR itself lists that D5
  fallback at `:173-175` as a reason the serve path deserves its exception — then picks the merge rule
  that routes users into the sibling branch which lacks it.

**Bounded, and I state the bound honestly:** a fresh model short-circuits before the reserve
(`lib/html-doc/serve-doc.ts:56-57` — *"B1 — no Gemini, no reserve"*), so only documents whose model is
absent/drifted/stale-version are affected; and rows are per-day, so it clears at UTC midnight. So this
is a migration-day 503 on documents already needing regeneration — real, not catastrophic.

**Answer to "is there a caller for whom over-counting is NOT safe?"** Yes — the serve path itself, in
the one branch that fails hard instead of degrading.

**Fix:** state the clamp and the user-visible outcome. `least(sum(attempt_count), max_serve_attempts - 1)`
preserves the ADR's "no under-count" intent while guaranteeing at least one attempt survives the
migration; or run the data migration such that merged rows land on a fresh `day`.

### H4 — The ADR adds `video_artifact_sources` without saying whether `source_generation_id` dies, which is the one-mechanism rule it is enforcing elsewhere

`:404-409` establishes that `source_generation_id` is load-bearing in two places —
the ranking rung (`schema/04_artifacts.sql:814-816`) and the MATCH SIMPLE FK
(`schema/04_artifacts.sql:91-92`) — and `:416-417` then adds a join table answering the same question.
`:427-429` rewrites the rung and `art_summary_has_no_source` to read the join table. **The column's fate
is never stated.**

If it stays, provenance has two representations and the ranking view and the join table can disagree —
which is *"two mechanisms for one concern"*, the root cause the retrospective names and the reason
`scripts/check-vocabulary-collisions.py` exists. If it goes, `art_summary_has_no_source`
(`schema/04_artifacts.sql:107`) and the round-5 M5 FK go with it, and the ADR should say so because both
were bought with review rounds.

**Fix:** state explicitly that `source_generation_id` is dropped in the same change, and that the FK's
guarantee migrates to the join table's FK. One sentence; its absence is the seam.

---

## Medium

### M1 — After the re-key, `owner_id` is functionally redundant, and the schema records the date that stops being true

With `doc_key = workspace/video`, `unique (owner_id, doc_key, day)`
(`0012_serve_model_charge.sql:13`) degenerates: `workspaces` has `unique (owner_id)`
(`schema/01_workspaces.sql:15`) and `id = owner_id` by construction (`:33`), so workspace ≡ owner today.
Harmless now — **but the schema names the expiry itself**:

```
schema/01_workspaces.sql:32   -- EXPIRY: the day multiple workspaces per user ship, id can no longer equal owner_id.
```

On that day `owner_id` becomes a genuine second tenancy axis in the *same unique index* as
`workspace_id`, and the "N leases against one model slot" defect the re-key exists to kill returns along
the owner axis. **Fix:** drop `owner_id` from the uniqueness (keep it as a denormalised FK for G1's
budget if needed) and say which column is the tenancy key.

### M2 — §8's "paid-ness from the KEY ALONE" argument is made against a key shape production does not use

The B2 rebuttal at `:256-262` leans on `…-design.md:2096-2100` — *"the paid/free split must be derivable
from the KEY ALONE"* — with the discriminator being path segment 4 ∈ {generation-id, `renders`}
(`…-design.md:275-282`). Production keys are `pdfs/{base}…` and `models/{base}.json`
(`lib/pdf/pdf-render-version.ts:22`, `lib/html-doc/model-store.ts:31`) — neither matches any row of that
table, so both fall to `…-design.md:283`: *"Anything else | **unknown** | fail closed: never delete, and
report."* The classifier today classifies **nothing** live.

This is a pre-existing spec↔production gap (ADR-0006's key migration presumably closes it), not round
13's defect — but the ADR's justification for *keeping* the `renders/` prefix is argued as though the
classifier were operating on live keys. **Fix:** one sentence stating that the classifier's premises hold
only after ADR-0006's key relocation, and that `renders/` is the post-migration shape.

### M3 — `art_summary_has_no_source` cannot remain a CHECK once provenance moves to another table

`:429`: *"`art_summary_has_no_source` `[VERIFIED: schema/04_artifacts.sql:107]` becomes a cardinality-zero
rule on the join table rather than a NULL check."* A CHECK constraint cannot reference another table, so
this becomes a trigger or a constraint trigger. `schema/04_artifacts.sql:104-106` records why the CHECK
exists in the first place — *"Guards the DATA; the rung below separately guards the QUERY. Both, because
they fail independently (service_role bypasses policies, not constraints)"* — and a trigger has a
different bypass profile than a constraint. **Fix:** name the mechanism, and confirm the
service_role-bypass reasoning still holds (per `:392-393`, triggers do survive `service_role`, so this is
likely fine — but it must be said, not assumed).

### M4 — Round 13's own fix list is not internally cross-referenced

B2 and H4 above are both "two sections of one ADR that must agree and never mention each other" (GC floor
↔ `model`; join table ↔ `source_generation_id`). Structural, not a single defect: the revision grew by
339 lines in one pass with no pass reconciling the new sections against each other. **Fix:** before round
15, do one read whose only question is *"which two of these new sections constrain each other?"*

---

## Low

### L1 — The dependency note is right and the front matter does not reflect it

`:469-474` correctly records that ADR-0007 rests on ADR-0006, itself `status: proposed`. The front matter
at `:2` says only *"proposed — supersedes the reservation protocol of ADR-0006's spec"*. **Fix:** add
*"and depends on ADR-0006 being accepted"* to the status line, so the coupling is visible where a reader
starts.

---

## What I could not break — do not re-run these in round 15

- **The load-bearing disjointness claim (`:40-52`) holds.** `transferClassA`
  (`lib/cloud-sync/sync-run.ts:371-395`) reads a body, verifies its hash, and `put`s it; no Gemini call,
  no generation id minted. The ADR's own §`:54-69` — *"the claim is TRUE and it is NOT sufficient"* — is
  a genuine strengthening and I could not find a way past it.
- **Brief item 8's two-column rule is TOTAL.** `artifact_kind` is exactly
  `('summary','model','dig','digDeeper','render')` (`schema/03_generations.sql:264`), and
  `art_paid_has_generation` (`schema/04_artifacts.sql:94-95`) puts exactly the first four in the paid
  set. So *"exactly one of `generation_id`/`render_id` is non-null"* holds for **every** kind, including
  `model` and `digDeeper`. The partition is sound. (It is the *address*, not the partition, that fails —
  B4.)
- **Brief item 2's tenancy fear is not live.** Workspace ≡ owner today
  (`schema/01_workspaces.sql:15, :33`); the re-key does not create a second tenancy axis now. Deferred
  risk only — recorded as M1.
- **Brief item 5's coverage fear does not apply.** `dig-handler.ts:117` carries the same pre-write abort
  re-check as `summary-handler.ts:170`, and `lib/job-queue/dispatch.ts:8-11` fans by kind with no third
  handler. The row is true of **every** job handler. The defect is the word "exclusivity" (H2), not the
  coverage.
- **The ADR's self-indictment of the vocabulary gate (`:189-209`) is accurate.**
  `scripts/check-vocabulary-collisions.py:44` sets `SCHEMA` to the spec schema dir and `:88` globs
  `0*.sql` within it; `supabase/migrations/` is genuinely outside. Run today it prints
  *"✅ no unjustified duplicate mechanism"*. Honest and correctly characterised.
- **The `check-sentinel-meanings.py` quote (`:316-317`) is accurate.** `scripts/check-sentinel-meanings.py:90`
  reads verbatim *"Delete this entry when renders get a derived generation id."*
- **The GC-floor and trigger citations are accurate.** `schema/04_artifacts.sql:897` is
  `and g.state = 'complete'`; `:898-900` the `not exists`; `:911-913` the trigger's permitted
  transitions; `:307-312` is indeed the only producer of a `pending` generation.
- **The `model`-is-a-paid-producer-with-no-job finding stands.** `lib/html-doc/serve-doc.ts:112` calls
  `generateMagazineModel` from an HTTP GET; `slot_kind` maps `'model'` → `'model'`
  (`schema/04_artifacts.sql:26`) and `art_paid_has_generation` (`:95`) puts it in the paid set. Round 13
  was right, and the exception is correctly *stated*; what fails is its interaction with the GC floor (B2).

---

## `[VERIFIED:]` tag audit — the tags are sound; the *inferences* from them are not

The brief asks for a spot-check, on the grounds that a wrong tag in a document whose method is those
tags is a serious finding. **I found no wrong tag.** Personally resolved and read, all accurate:

`sync-run.ts:372-394` · `worker-runner.ts:48-51, :30-32` · `summary-handler.ts:170` · `:166-169` ·
`:173-179` · `serve-doc.ts:112` · `:105-109` · `:80-98` · `serve-summary-core.ts:105` ·
`html-doc/constants.ts:1-5` · `pdf/pdf-render-version.ts:10, :22, :5-9` · `dig/generate.ts:15` ·
`app/api/pdf/[id]/route.ts:54` · `app/s/[token]/route.ts:81` · `0008_jobs_queue.sql:14` ·
`0009_…:11-13` · `0012_serve_model_charge.sql:7-13, :24, :53` · `0020_reservation_release.sql:25-32,
:213` · `schema/01_workspaces.sql` (via M1) · `schema/03_generations.sql:64` ·
`schema/04_artifacts.sql:20, :26, :94-95, :107, :154-157, :159-161, :162-163, :164, :307-312, :897,
:898-900, :911-913` · `scripts/check-vocabulary-collisions.py:44, :88` ·
`scripts/check-sentinel-meanings.py:90`.

**That is the more interesting result, not a clean bill.** The revision's failures are one level up from
citation accuracy: **the tag resolves, and the cited code does not support the sentence it is attached
to.** Three of this round's findings have that exact shape —

- **H1** — `pdf-render-version.ts:22` is quoted correctly and *refutes* "it subsumes every version
  constant"; the refutation is in the same file at `:5-9`, which the ADR also quotes, two paragraphs
  earlier, for the opposite purpose.
- **H2** — `summary-handler.ts:170` is quoted correctly and the comment at `:166-169` directly above it
  says the mechanism is a bounded window, not the "exclusivity" the row claims.
- **H3** — `serve-doc.ts:105-109` is quoted correctly and its rule is scoped to settle-time refunds, not
  to merging counters.

A `[VERIFIED:]` discipline that checks *"do these lines exist and say roughly this"* cannot catch that
class. The check that would is the one the ADR applies to itself at `:69` and then does not run
everywhere: **for each tag, does the cited code entail the claim, or merely coexist with it?**

---

## Verdict

**NOT CONVERGED.**

**Blocking reason:** two of round 13's own fixes are mutually inconsistent on the money path — the GC
floor's named successor (staged-write ordering) does not cover the `model` kind that the same revision
carves out as its standing exception (**B2**) — and the render change does not achieve the immutability
it is the ADR's stated purpose to achieve, because `render_id` appears nowhere in the address (**B4**).
Additionally the document ships two contradictory copies of its central table, the second being the
version round 13 refuted (**B1**), and the new provenance table breaks account deletion by measurement
(**B3**).

The **decision** — delete the reservation, treat artifacts as an append-only log — still looks right to
me, and I could not break the disjointness claim it rests on. What is not yet right is the *replacement
addressing scheme for renders* and the *per-kind* discharge of the guarantees the deletion removes. Those
are fixable without reopening the decision.

**Recommended for round 15:** verify only that B2's per-kind successor table and B4's key-carries-the-
identity change are stated, and re-run the cascade probe. Do not re-run the "could not break" list.
