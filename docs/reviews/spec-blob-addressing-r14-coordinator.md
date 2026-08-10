# Round 14 — coordinator adjudication

**Verdict: NOT CONVERGED.** 4 Blocking, 4 High, 5 Medium, 1 Low. Round 15 mandatory.

Round 14 was aimed at **round 13's own fixes**, because this spec's measured signature is that each
round's fix causes the next round's defect. The aim was correct: **every Blocking is in a change made
yesterday**, and two of them are round-13 fixes that contradict each other.

Gate strength: **not downgraded.** Both reviewers executed `verify-schema.sh` against live Postgres
inside a rollback. Claude additionally measured B3 with a structural probe in a throwaway schema, and
a separate pass audited all 57 `[VERIFIED:]` tags against the real files. Tree clean throughout.
Codex reached `gpt-5.5` after three HTTP 400s — wrapper fallthrough working.

**Both reviewers independently affirm the core decision.** Neither could break the disjointness claim;
both say the remaining defects are fixable without reopening "delete the reservation protocol." That
claim has now survived two design reviews.

---

## The headline: I made the same class of error the round I was fixing

Round 13's B1 was: *the ADR proved a true lemma about writes and read it as a conclusion about money.*
Round 14 found me doing it twice more, in the fixes for that very finding.

- **H3 (both reviewers).** I justified `attempt_count` merging by SUM with the serve path's rule
  *"over-count is safe, under-count is the bug"* `[VERIFIED: lib/html-doc/serve-doc.ts:105-109]`. That
  rule is scoped to **refunding one attempt whose metering is uncertain** — "when in doubt do not
  refund." It says nothing about merging independent counters, where over-counting costs no money and
  instead **denies service**. A true rule about spend, read as a conclusion about availability.
- **H1 (Claude).** I wrote *"content addressing is complete by construction, and production already
  does it"* and cited `lib/pdf/pdf-render-version.ts:22`. **Verified by me:** `:21` hashes
  `htmlNonceFree` — the **input** HTML, not the rendered PDF — and `.r${PDF_RENDER_VERSION}` is a
  separate literal key segment *precisely because the hash does not subsume it*. Production is
  input-addressing **plus a hand-maintained version constant**: verbatim the enumeration approach the
  ADR rejects two paragraphs earlier. **I cited the codebase's clearest instance of the failure mode
  as proof of the cure.**

Recording this plainly because the retrospective's B7 says mutation testing proves a test is
load-bearing, never that it tests the property you meant — and the same is true of a citation. All
three of these tags *resolve*. Resolving is not supporting.

---

## BLOCKING — all four verified by me against the code

### B1 — the ADR ships two contradictory copies of its central table (Claude Blocking / Codex High)

`## What already serves each concern` appears at `:71` (corrected) **and `:98` (uncorrected)**, the
second being the version round 13 refuted, at equal authority. `:100-101` also restates the
one-mechanism rule **with no exception**, contradicting the ADR's own headline at `:17-19`.

**Adjudicated at Blocking, with Claude.** Codex ranked it High as editorial residue. It is not: this
is a normative document, an implementer has even odds of reading the refuted table, and `:113-116`
refers to *"rows 1–4"* — row numbers that only resolve against the false table. My editing error.

**`scripts/check-docs.py` does not detect a duplicated `##` heading with contradictory content** —
the same "instrument whose success line claims more than its input covers" shape, now in the document
that names the shape.

### B2 — the GC-floor successor cannot cover `model` (Claude only; the deepest finding of the round)

Round 13 fix #7 names staged-write ordering as the successor to the vacated GC floor
`[VERIFIED: lib/job-queue/summary-handler.ts:173-179]`. Round 13 fix #4 carves `model` out as the
standing exception. **They are incompatible, and neither section mentions the other.**

**Verified by me:** `lib/html-doc/model-store.ts:51` writes the model with a plain `put`, and its
docblock at `:42-43` says the staged→promote protocol *"is NOT used for the model"* — deliberately,
because a regenerated model must overwrite or the serve path re-charges every view until K, then 503s
(`lib/html-doc/serve-doc.ts:102-104`).

So: delete `pending` ⇒ `g.state = 'complete'` goes vacuously true ⇒ the named successor covers
`summary`/`dig` ⇒ **`model` is uncovered** ⇒ a `model` generation is collectable while its paid Gemini
call is in flight. That is round 9's B1 exactly, whose measured transcript survives in the schema
comment: *"Money spent, bytes queued for deletion, no error anywhere."*

`model` is the worst kind to leave uncovered — no job, no staging, no renewal RPC, 180 s TTL, paid
Gemini call on an HTTP GET.

**This is the signature failure mode occurring *within a single round's fix set*.**

### B3 — the new provenance table breaks account deletion (Claude, MEASURED; Codex M1, reasoned)

`on delete restrict` on `video_artifact_sources → video_generations` aborts the cascade
`profiles → workspaces → workspace_videos → video_generations` (verified: `01:13`, `03:49`,
`03:362-363`). A RESTRICT child aborts a parent delete **even when the parent delete is a cascade
step**. Once any render carries a provenance row, `delete from profiles` fails — the account-erasure
path, which is a real caller.

**Adjudicated at Blocking, with Claude.** Codex called it "underspecified" (Medium); Claude measured
it. The standing rule holds — prefer the reviewer with the transcript.

Fix is `on delete cascade`. RESTRICT was there to stop GC collecting a referenced generation, but
`:428` already provides that by a second `not exists` over the join table — two mechanisms for one
concern, in a table introduced by a fix, and the redundant one breaks a live path.

### B4 — `render_id` is nowhere in the address (Claude B4 / Codex B1 / found independently by me)

Nothing binds `render_id` to `blob_key`: `art_key_names_generation` is vacuously true when
`generation_id is null` `[VERIFIED: schema/04_artifacts.sql:159-160]`, and `art_key_names_workspace`
constrains segments 1–3 only. New uniqueness on `(ws, video, slot, render_id)` therefore permits **N
rows on one key**, and renders are written with `put` — an overwrite.

Today `video_artifacts_free_uq` at least keeps row↔blob 1:1, so "overwritable" is *coherent*. The
proposal gives N rows, one key, and N−1 rows pointing at bytes that no longer exist. **For an
append-only log that is strictly worse than the status quo it replaces.**

Claude's precise statement of the error, which I endorse: a render is not *addressed by*
`sha256(rendered bytes)` under this proposal — it is *identified* by it in a column while remaining
*addressed* by an unchanged key. **The sentence silently swaps address for identity**, and the entire
re-answer to the founding conflation rests on it.

Also true and mine to own: I wrote that the key keeps its *"existing"* `renders/` prefix.
`grep -rn "renders/" --include=*.ts` returns **zero hits** — `renders/` exists in the spec table and
the assertion fixtures, never in code. "Existing" was true of the spec, not of the code the sentence
appeared to describe.

---

## HIGH

- **H1 — the production-does-it warrant is refuted by its own citation** (see headline). Consequence
  beyond the wording: `app/api/pdf/[id]/route.ts:54` computes the key from the HTML and `:60` probes
  the blob store **before** rendering. **An identity that cannot be computed until the bytes exist
  cannot be the cache key of a path whose purpose is to avoid producing the bytes.** Any render
  scheme needs *two* keys — an input-derived probe key and an output-derived identity — and the ADR
  must say which is `blob_key` and which is `render_id`.
- **H2 — the replacement concern-table row claims "exclusivity" from a window-narrowing mechanism.**
  `summary-handler.ts:166-169` says full lease-fencing is **deferred** and stale writes are tolerated
  because they are *idempotent* — merge-safety, not exclusivity. Nothing prevents lease loss between
  the check at `:170` and the writes at `:173-179`. Round 13 corrected two rows for claiming a
  guarantee the mechanism does not make; the replacement row does the same thing.
- **H3 — SUM can 503 a document that renders today** (both reviewers; see headline). Claude states
  the bound honestly: only documents whose model is absent/drifted/stale-version are affected, and it
  clears at UTC midnight — a migration-day 503 on documents already needing regeneration. Claude's
  fix is better than Codex's MAX: `least(sum(attempt_count), max_serve_attempts - 1)` keeps the
  no-under-count intent while guaranteeing one attempt survives.
- **H4 — `source_generation_id`'s fate is never stated.** The ADR adds a join table answering the
  same question and rewrites two consumers to read it, but never says whether the column dies. If it
  stays, provenance has two representations that can disagree — the exact root cause the retrospective
  names.

## MEDIUM

M1 `owner_id` becomes functionally redundant in `serve_model_charge`'s uniqueness after the re-key,
and `schema/01_workspaces.sql:32` **names the date that stops being true** ("the day multiple
workspaces per user ship") — on which the N-leases defect returns along the owner axis ·
M2 §8's key-alone argument is made against a key shape production does not use (`pdfs/…`,
`models/…` both fall to *"unknown → fail closed"*) · M3 `art_summary_has_no_source` cannot stay a
CHECK once provenance moves tables (a CHECK cannot reference another table) · M4 the round-13 revision
grew 339 lines in one pass with no pass reconciling its new sections against each other — B2 and H4
are both "two sections that must agree and never mention each other" · M5 (coordinator) the citation
audit: **1 wrong tag** (`0012:24` for the 180 s TTL — it is `:22`), 1 partial-wrong (`0008:96-130`
does not contain `sweep_expired_leases`; it is `0008:167-188`), 3 off-by-N (`04:245-252`→`257-262`,
`04:253-260`→`263-270`, `04:90-91`→`91-92`), and one claim-vs-code mismatch: `jobs_idem_active` is
described as *"one **non-terminal** job"* but its predicate includes `'completed'`, which is terminal.

## LOW

L1 the front matter should say ADR-0007 depends on ADR-0006 being accepted, where a reader starts.

---

## What round 14 could NOT break — do not re-run in round 15

- **The load-bearing disjointness claim holds**, and round 13's *"the claim is TRUE and it is NOT
  sufficient"* strengthening survived attack.
- **The two-column partition is TOTAL.** `artifact_kind` is exactly the five kinds
  (`03_generations.sql:264`) and `art_paid_has_generation` puts exactly four in the paid set, so
  "exactly one of `generation_id`/`render_id` is non-null" holds for every kind. It is the *address*,
  not the partition, that fails.
- **The tenancy fear is not live** — workspace ≡ owner today. Deferred risk only (M1).
- **The heartbeat row's coverage is fine** — `dig-handler.ts:117` carries the same pre-write re-check,
  and `dispatch.ts:8-11` fans by kind with no third handler. The defect is the word "exclusivity"
  (H2), not the coverage.
- **The ADR's self-indictment of the vocabulary gate is accurate**, as is the `check-sentinel-meanings`
  quote and every GC-floor/trigger citation.

---

## The pattern round 15 must confront, and the scope question it raises

**Render identity has now failed design review twice in two rounds:**

| Round | Proposal | Why it failed |
|---|---|---|
| 13 | `hash(source_generation_ids, GENERATOR_VERSION)` | incomplete enumeration (3 version constants + a Chromium pin); key shape breaks §8's classifier |
| 14 | `sha256(rendered bytes)` + unchanged key | identity never reaches the address; cannot be a cache probe key |

By this project's own stop condition — *two consecutive rounds whose findings were caused by the
previous round's fixes ⇒ escalate from fix to redesign* — **the render sub-problem has now met the
escalation criterion in its own right.** A third patch is the move the condition exists to prevent.

Note what is *not* in that table: the reservation deletion, the `model` exception, the disjointness
claim, and the concern table have all now survived a design review. **The core decision is converging;
the render addressing is not.** They are bundled only because the `generation_id IS NULL` conflation
touches both.

**Scope question for the human (not a coordinator call):** split ADR-0007 so the reservation deletion
proceeds on its own, and give render addressing its own ADR with its own design pass — or keep them
together and take a third swing at renders inside this round. The first respects the stop condition;
the second keeps one document. Everything else found this round (B1, B3, H2, H3, H4, the Mediums, the
citation errors) is unambiguous and can be fixed either way.
