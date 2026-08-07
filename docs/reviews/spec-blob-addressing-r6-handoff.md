# Handoff — stable blob addressing, round-6 design items

**Task #15.** Branch `docs/blob-addressing-decisions`, **PR #51** (open, do not merge — human gate).
Everything is committed, `check-docs.py` green, `verify-schema.sh` green with **48 assertions**.

## Read these first, in this order

1. `docs/reviews/spec-blob-addressing-r6-claude.md` — 5 Blocking / 5 High, nearly all MEASURED.
2. `docs/reviews/spec-blob-addressing-r6-codex.md` — 3 Blocking / 2 High; overlaps heavily.
3. `docs/reviews/spec-blob-addressing-r5-cross-derivation.md` — the method, plus six findings recorded
   as **open** at the end.
4. `docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/` + `verify-schema.sh`.

**Where prose and schema disagree, the schema is the design.** Run the verifier before reading
anything: it executes against the live local Postgres in a rollback, and it is the only artifact here
a machine checks.

## What is already done (do not redo)

Rounds 1–6 of dual adversarial review. The whole round-6 **security/mechanical** half is applied and
mutation-checked: the `PUBLIC EXECUTE` hole, the `anon` TRUNCATE hole, the `LIKE`-as-pattern key
guard, and the missing cross-tenant coverage. See `c5db900` and `3fb6970`.

**`3fb6970` is the one to understand before trusting anything else.** `assert_raises` caught
`when others`, so six negatives were passing on a `[42601]` arity error rather than on the constraint
they named — and round 5's Blocking B1 and High H5 shipped unverified while the suite printed green.
The harness now demands an expected SQLSTATE and constraint name. **Any "verified" claim from round 5
or earlier predates this and is not trustworthy.**

## The four items to decide

Each needs a decision, not a patch. That is why they were split out.

### 1. `detached` is an unfenced state (r6 Claude B3 + H1, Codex B1) — MEASURED

`video_artifacts_append_only()` gates its whole body on `old.state = 'recorded'`, so a `detached` row
is unprotected, and `recorded → detached` is permitted for **every** paid kind. Measured consequences:

- DELETE of a detached paid row succeeds (the serial-coherence orphaning defect, PR #42, in two statements).
- detach → rewrite `blob_key` → re-record succeeds (shape #3, in the trigger written to prevent it).
- detach → collect → the summary slot has **0** current rows (defeats round 5's H3 fix; I measured 1 → 0).
- A **detached dig** is collectable, which is exactly the paid content §6.2 promises is never deleted.

**Decide:** (a) is `detached` dig-only? §6.2 only ever describes detached digs — if yes, add
`check (state <> 'detached' or kind = 'dig')`. (b) The GC guard currently asks *"is this generation
current?"*; it needs to ask *"is anything still pointing at these bytes?"* — that is a different
question and the reviewer is right that currency is the wrong property. (c) Codex H5: freeze
`source_generation_id`, `start_sec`, `end_sec` too, or a stale model can rewrite its provenance to win
the ranking without regenerating anything.

These interact — do them as one change with a cross-derivation pass, and cross-derive the two triggers
**against each other**. I cross-derived the append-only trigger against the reclaim and against rule
19 and skipped the GC trigger I had added in the same batch. That omission is exactly what B3/H1 are.

### 2. Rung 1 diverges from `reconcileClassA` for the entire corpus (r6 Claude B4) — MEASURED

Two causes:

- `03_generations.sql` seeds `workspace_videos` from `select distinct workspace_id, video_id from
  videos` and never backfills `corrections`/`corrections_hash`. Measured: **2903 of 2904 rows NULL**,
  while **99 live videos carry real corrections**. The migration drops them.
- The two sides spell "no corrections" differently. `pipeline.ts:272` stamps `mdCorrectionsHash:
  mdHash('')` — a real 64-hex string, never null — and `sync-run.ts:651` does the same.

**This reverses a decision I made in round 5** (cross-derivation C2): I argued the card's
`mdCorrectionsHash` must be allowed to be JSON-null because "null is the correct answer for a video
with no corrections." Against the merged producer that premise is **false**. Consequence measured:
view says corrections-current = FALSE, sync says TRUE ⇒ `copyToCloud` on **every sync, forever** —
verbatim the failure round 5 B3 was written to remove, one rung above where it was fixed.

**Decide:** one representation of "no corrections", used on both sides, plus the backfill from
`videos.data`. Then re-derive `gen_card_complete`'s null allowance against whichever you pick.

### 3. `md_hash` has no producer (r6 Claude B5, Codex B3)

`gen_summary_has_hash` makes it mandatory; nothing computes it; `record_artifact`'s signature in §5.1
does not carry it, `card`, or `doc_version_major`; and **§10.0 — the section that exists to prevent
exactly this — does not mention it**. Its own stated failure mode applies verbatim: every cloud
summarize fails its insert *after* the paid Gemini call.

The mechanism exists (`core.mdContent` is in scope at `summary-handler.ts:172`,
`lib/cloud-sync/content-hash.ts:16` exports `mdHash()`), so this is a contract gap, not a research
problem. **Three producers, not one**: `lib/job-queue/summary-handler.ts`, `lib/cloud-sync/sync-run.ts`
(the one §5.3 now requires to emit `md_hash`), `lib/storage/worker-persistence.ts`.

**Decide:** the generation-write API. It probably wants to create the generation row and the `pending`
artifact row in one transaction — which also resolves item 4. Re-specify it **last**, after the table
is settled; it has now been specified-before-the-table-changed twice (round 2 N-B3, round 5).

### 4. The reclaim is not a protocol (r6 Claude H5, Codex B2) — MEASURED

Three defects in ten lines: `coalesce(v_attempts, 0)` conflates *absent* with *zero attempts* (shape
#1, on the money path); reclaim and reserve are two round trips so the attempt bound is resettable
under concurrency (unbounded paid retries); and reclaim does not **fence** the reclaimed writer —
measured, W1's lease expired, W2 reclaimed and reserved, and W1 then recorded anyway: **two paid
Gemini calls in one slot**.

**This is backlog #17 (worker-vs-sync fencing) in a new costume**, and that was deferred after five
rounds on its own slice. Treat it as its own design, not as a patch here.

**Decide:** one `reserve_artifact_slot(...)` RPC returning a typed
`reserved(token) | busy | exhausted`, with a `lease_token` the record-flip must match. Note the
reviewer's separate point that a raw `23505` from the unique index is **shape #8** — a policy that
errors rather than denies — so callers currently parse a constraint name to tell busy from broken.

## Then

Round 7, both reviewers. Reuse
`…/scratchpad/review-r6-prompt.md` as the template; keep the standing root-cause shapes list and
**update the counts** (shape #9 is at eight, shape #10 at six). Keep the instruction telling reviewers
to distrust the coordinator's own claims — it is the only reason §5.3's false claim and the harness bug
were ever found.

## Process notes worth carrying (all learned the hard way this session)

- **Commit before mutating.** `git checkout` reverted uncommitted fixes three times.
- **Two agents cannot mutation-test one file.** Mutation testing is a write. Give the reviewer a copy.
- **A mutation harness must distinguish three outcomes**, not two: INVALID (broke the SQL) / RED / GREEN.
  Mine reported its own broken regex as an untested guard.
- **A "sees 0 rows" test cannot detect a removed RLS policy** — removing one makes a force-RLS table
  *more* restrictive. Only an owner-side positive catches it.
- **Resolve fixture ids before `set local role`.** An assertion that reads a temp table after switching
  role fails on the temp table and never reaches what it claims to test.

## Skills

`superpowers:brainstorming` for items 1–4 (each is a design decision). Then
`codex:rescue` + a fresh Claude subagent for round 7. `verification-before-completion` before asking
for the merge.
