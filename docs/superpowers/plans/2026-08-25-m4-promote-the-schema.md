# M4 — Promote the schema as migrations

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes. M4 is the step that makes the accepted schema EXECUTE, for the first time outside a review's rollback.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended)
> or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Milestone spine:** [`2026-08-22-append-only-generations-roadmap.md`](2026-08-22-append-only-generations-roadmap.md) → M4.
**Source of truth:** `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md` + its
`schema/` (4,108 lines), **ADR-0006** and **ADR-0007**, both `accepted` 2026-08-24 (M3).

---

## ⛔ READ THIS FIRST — M4 IS NOT "INERT". THE SPINE'S ONE-LINE DESCRIPTION IS WRONG.

The spine says the schema *"lands inert. No application caller yet."* The first half of that is false,
and it was found by reading the SQL rather than the sentence describing it.

`01_workspaces.sql` **alters three live production tables and rewrites every row of each**
`[VERIFIED: schema/01_workspaces.sql:36-48]`:

```sql
alter table playlists add column workspace_id uuid references workspaces(id);
update playlists p set workspace_id = w.id from workspaces w where w.owner_id = p.owner_id;
alter table playlists alter column workspace_id set not null;     -- and the same for videos, jobs
```

Plus a data migration that invents a row per account
`[VERIFIED: :33]` — `insert into workspaces (id, owner_id) select id, id from profiles` — **two** FKs — `videos_workspace_video_fk` `[VERIFIED: schema/03_generations.sql:96-97]` and
⟳ *round 1 Medium:* `jobs_workspace_owner_fk` `[VERIFIED: schema/01_workspaces.sql:50-51]`, which
v1 counted but did not name — plus a backfill into `workspace_videos` `[VERIFIED: :89]`, and
**9 triggers on live tables** `[VERIFIED: schema/03_generations.sql:152-215, :253-262]`.

**So "no caller reaches `record_artifact`" is TRUE and it is NOT the property that matters.** The
risk of M4 was never a dormant table; it is three `NOT NULL` promotions and two FK additions against
tables that hold paid Gemini content, executed by a migration that has never run outside a
`begin; … rollback;`.

> ⚠ **This is the fifth instance this week of a claim that is true about the object it NAMES and
> silent about the layer that decides the outcome** — see the memory `true-about-the-name-silent-about-the-layer`.
> The spine's sentence is corrected by T0 below rather than left to mislead the next reader.

### ⟳ v2 — THE M4a/M4b SPLIT PROPOSED IN v1 IS REFUTED. It is not executable.

Round 1 (Codex, `docs/reviews/plan-m4-promote-schema-r1-codex.md`) returned **4 Blocking**, and every
one survived hand-verification. The plan's central idea — promote the new tables first, defer the
live-table changes — **cannot be built**, because the accepted schema interleaves the two:

| Refuted claim (v1) | What the SQL says |
|---|---|
| "M4a is new objects only" | **9 triggers attach to LIVE tables** — `profiles` ×1, `playlists` ×2, `videos` ×4, `jobs` ×2 `[VERIFIED: schema/03_generations.sql:152-215, :253-262]`. They change write behaviour the instant they land |
| "create `workspace_videos` with every `videos` reference removed" | its backfill **selects `workspace_id` FROM `videos`** `[VERIFIED: :89-95]`, and the FK at `:96-97` references `videos(workspace_id, video_id)`. The new table cannot exist before the new column |
| "all six gates green, against the migrations" | **mechanically false.** Gates 1 and 2 are `verify-schema.sh` and `mutate-schema.py`, both hardwired to the spec directory — `verify-schema.sh:8` (`DIR=…/schema`) and `mutate-schema.py:25` (`SPEC = Path(__file__).parent`). Re-pointing two *ratchets* does not re-point the *gates* |
| "`check-guard-coverage` re-points cleanly" | its inventory already expects M4b guards — `videos_workspace_video_fk`, `jobs_workspace_owner_fk` and the live-table trigger functions `[VERIFIED: scripts/check-guard-coverage.py:111-150]`. Against a new-tables-only migration it fails, or silently changes subject |

**THE CORRECTION, and it is the whole lesson of round 1: you cannot split the DDL. You can only
split the ENVIRONMENTS it runs against.**

The accepted schema is one interdependent unit — that is what "accepted" bought. So M4's stages are:

| | What | Blast radius |
|---|---|---|
| **M4-α** | ⟳ *round 1 Low: not "reversible by `drop`" — it creates functions, types, policies, grants, views and RLS state as well.* The complete promotion — all five tables, 9 live-table triggers, three `workspace_id` columns, backfills, `NOT NULL` promotions, both FKs — applied to a **throwaway Supabase project**, with all six gates run against it | Zero. A project that gets deleted |
| **M4-β** | The same migrations, applied to **production** | Every row of `playlists`, `videos`, `jobs`. Not reversible without a restore |

⚠ **Do not read M4-α as a rehearsal that makes M4-β safe.** It proves the DDL executes and the
assertions hold; it says nothing about production's *data*, which is what T1 measures. Two different
questions, and the throwaway project can only answer the first.

---

## What M4 does NOT do

Stated up front because the previous three milestones each lost a round to scope creep.

- **No application caller.** Nothing in `lib/ app/ worker/` calls `record_artifact` or reads
  `video_artifacts_current` when M4 lands. That is M5.
- **No blob re-keying.** Not one object in Storage moves. That is M5/M7.
- **No GC, no sweeper, no backfill of generations.** That is M7.
- **No render addressing.** Out of scope by user decision 2026-08-09 (backlog #25).

---

## Tasks

### T0 — Correct the spine, before writing any SQL ⚠ MUST BE FIRST

The finding above is worth more than the migration. Fix `2026-08-22-append-only-generations-roadmap.md`'s
M4 entry to say what M4 actually does, and split it into M4a/M4b there too.

- **Gate:** `check-docs` 0. No code.
- **Why first:** a plan that corrects a document at the end leaves a window where the wrong sentence
  is the one on `master`.

### T1 — Measure the blast radius against PRODUCTION, read-only

Before any migration is written, get the numbers M4b's risk assessment needs.

- Row counts for `profiles`, `playlists`, `videos`, `jobs` in prod (read-only, `claude_ro`).
- **The falsifier for the backfill:** how many `videos` rows have a `playlist_id` that resolves to no
  `playlists` row, and how many `playlists` rows have an `owner_id` with no `profiles` row? Either
  makes an `UPDATE … FROM` leave `NULL` behind, and the next statement is
  `set not null`, which then **fails the migration mid-flight**.
- ⟳ *Round 1 High — v1 said `jobs.playlist_id` is nullable in some paths. **It is not:**
  `0009_job_playlist_identity_and_worker_persistence.sql:4` adds it `not null`. The query was
  harmless; reasoning from an outdated schema fact is not.* The live question for `jobs` is
  instead whether every `jobs.playlist_id` resolves to a `playlists` row that itself resolved a
  `workspace_id`.
- ⟳ **Round 1 High — CONCURRENT WRITES, which v1 did not mention at all.** `SET NOT NULL` can be
  defeated by a row inserted between `ADD COLUMN`, the backfill and the promotion. The plan must
  state a **transaction and lock strategy** — one transaction holding to commit, an explicit
  `lock_timeout` and `statement_timeout`, and either write quiescence or a re-check inside the
  same transaction. On a live worker queue this is the likeliest way M4-β fails.
- **Gate:** the numbers land in this file, each with the query that produced it. A count without its
  query is the defect round 1 of the spine's review already caught once.
- ⚠ **Read-only. No writes to prod in M4 at all.**

### T2 — `0027`+ — the COMPLETE promotion, in dependency order (M4-α)

Promote all four spec files as migrations starting at **`0027`** (`0026` is `record_correction_spend`),
**without removing anything**.

⛔ **v3 / round 2 Blocking — ONE FILE, ONE TRANSACTION. Splitting it is an OUTAGE.**
v2 permitted splitting into `workspaces` → columns + `NOT NULL` → `workspace_videos` → triggers.
**MEASURED refutation:** `enqueue_job` inserts into `jobs` *without* `workspace_id`
`[VERIFIED: supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:26-27]`, while
the trigger that derives it is created later `[VERIFIED: schema/03_generations.sql:156, :200-215]`.
Commit the `NOT NULL` in one migration and the trigger in the next, and **every job enqueue in
production fails for the interval between them.** A live outage, produced by v2's own fix for round 1.
T1's "one transaction" saves nothing when the chain is several *committed* files.

**Therefore: the columns, backfills, `NOT NULL` promotions, both FKs and all nine triggers are ONE
migration file in ONE transaction.** Readability is not worth an outage window. Only objects that
touch no live table may go in a separate file.

- **Applied to a throwaway Supabase project first.** See the `staging-supabase-project` memory for
  the pattern; delete it when M4 closes.
- **Gate:** `./scripts/check-schema-gates.sh` green **against that project** — which requires T3.
- ⚠ **`05_assert.sql` cannot run standalone** `[VERIFIED: scripts/check-schema-gates.sh:14-16]`, and
  ⟳ *round 1 Medium:* it also **asserts M4b behaviour** — it reads `videos.workspace_id`
  `[VERIFIED: 05_assert.sql:893-911]` and checks that plain inserts derive `workspace_id` for
  `videos` and `jobs` `[VERIFIED: :1843-1859]`. Under v1's split it would have been testing a state
  the migration had not created. Under M4-α it is testing the real thing.

### T3 — Re-point ALL SIX gates, not two ratchets ⚠ LANDS WITH T2

⟳ **v1 said "re-point the two red ratchets" and called that the six gates. It is not.**

| Gate | Today reads | Must read |
|---|---|---|
| 1 `verify-schema.sh` | `…/schema/*.sql` concatenated in one transaction `[VERIFIED: :8-10]` | the migrations, applied in order |
| 2 `mutate-schema.py` | `SPEC = Path(__file__).parent` `[VERIFIED: :25]` | the migrations |
| 3 `check-guard-coverage.py` | `:44` the spec dir | the migrations |
| 4 `check-sentinel-meanings.py` | `:43` the spec dir | the migrations |
| 5 `check-vocabulary-collisions.py` | `:46` (`SCHEMA`) and `:96` (the glob). ⟳ *Round 2 Medium: v2 wrote `:44,88`, **copied from ADR-0007 without re-verifying** — line 44 is blank, 88 is allowlist prose. ADR-0007 carries the same stale tag; correct it when M5 touches that ADR. A citation that resolves without supporting is the failure that document names about itself* | the migrations **plus** `supabase/migrations/` |
| 6 `check-docs.py` | unaffected | unaffected |

⛔ **v3 / round 2 Blocking — GATES 1 AND 2 CANNOT BE "RE-POINTED"; THEY MUST BE REWRITTEN.**
`verify-schema.sh` concatenates spec files inside ONE rollback transaction `[VERIFIED: :8-10]`;
`mutate-schema.py` hardwires two named spec files and copies `schema/` **and the verifier** into a
temp dir, then runs the copy `[VERIFIED: mutate-schema.py:25-27, :875-884]`. A gate that applies
*committed* migrations sequentially is a different harness with different failure modes. v2 wrote
"Must read: the migrations" as if it were mechanical — round 1's refuted split, one layer down.
**T3 is a rewrite, and must be estimated as one.**

- **Gate for T3 itself:** each rewritten gate goes **red on a mutation** — delete one guard from the
  migration and confirm it fails. A gate that passes because it now reads an empty set is the
  measured failure mode this project already has two instances of.
- ⚠ **Gate 5 is the one to think about:** widening it to `supabase/migrations/` will surface the
  `serve_model_charge` ⟷ `jobs` duplication ADR-0007 documents as a *standing exception*. Decide
  whether it is justified-and-suppressed or a finding, **before** the widening makes it noise.
  ⟳ *Round 2 High: v2's "decide whether…" was a deferral wearing an instruction — no artifact, no
  owner, no acceptance criterion, which `CLAUDE.md` says to rename rather than tick.* **Required
  artifact: either an explicit `ALLOWED` entry naming `serve_model_charge` with ADR-0007's reason, or
  a filed finding that keeps the gate RED.** No third option, and no widening until one exists.

### T4 — Give `05_assert.sql` a home

The spine says *"`05_assert.sql` gets a home in CI or `check-schema-gates.sh`"* and does not decide
which. Decide it here.

- The constraint that settles it: the assertions need the tables **in the same transaction**, and CI
  has no Postgres today (`docs/dev-process.md`: *"Not yet in CI: … the schema gates (need a live
  Postgres)"*).
- **Gate:** whichever home is chosen, `./scripts/check-schema-gates.sh` still runs it, and the
  "cannot run" case exits **non-zero** with *treat this as NOT RUN* — never 0.

### T5 — ⛔ DISSOLVED by round 1 — folded into T2

The `workspace_id` columns cannot be a later task: `workspace_videos`'s own backfill reads
`videos.workspace_id` `[VERIFIED: schema/03_generations.sql:89-95]`. **Four findings, one deletion** —
the same shape ADR-0007 records as the tell that a dissolution is right rather than a patch.

The *procedure* T5 described survives inside T2 and is the money step of M4-β:
`add column` (nullable) → backfill → **assert zero NULLs** → `set not null`, in one transaction with
an explicit `lock_timeout`, and the assertion must be able to abort the migration.

### T6 — The `doc_key` re-key ⟷ `inflight_uq` coupling (task #45)

ADR-0007 is explicit: *"`doc_key` is re-keyed to `(workspace_id, video_id)` in the SAME slice that
deletes `video_artifacts_inflight_uq`. Shipping the deletion without the re-key is a money
regression."*

- **DECISION FOR THIS PLAN: `video_artifacts_inflight_uq` is NOT deleted in M4.** It guards the live
  `model` path, the re-key needs `workspace_id` (T5), and the data migration carries the
  `least(sum(attempt_count), max_serve_attempts - 1)` clamp that ADR-0007 spent three rounds getting
  right. Bundling it into a promotion milestone is how M4 acquires a money path it does not need.
- ⟳ **Round 1 High refutes the framing.** There is nothing to *defer*: promoting `04_artifacts.sql`
  as written already ships the post-deletion protocol — the index is absent by design
  `[VERIFIED: schema/04_artifacts.sql:269-288]` and `record_artifact` is created and granted to
  `service_role` `[VERIFIED: :354-360, :628-633]`. **M4 does not get to decline the coupling; it
  gets to decide whether the shipped `serve_model_charge` path still holds while the new one is
  callerless.** Answer that with a measurement, not a sentence.
- **T6 is therefore: establish, by reading the live serve path, that no caller can reach
  `record_artifact` for a paid kind after M4-β** — and write the `doc_key` re-key coupling into
  M5's entry where the deletion becomes observable. Backlog **#26** and task **#45** both hang
  here.

### T7 — Arm backlog #26, loudly

The spine: *"**Arms backlog #26** — from here on, a caller reaching `record_artifact` is a 5× spend
ceiling nobody chose."*

- M4 ships no caller, so #26 is not yet a money regression — it is armed, not fired.
- **Gate:** #26's row states the trigger in terms of an observable — *"fails the moment a non-test
  caller reaches `record_artifact` for a paid kind"* — and, if it is cheap, a check script that
  greps for exactly that. A trigger nobody can observe is a decision wearing a checkbox.

---

## Order, and what may run in parallel

```
T0 ──▶ T1 ──▶ T2 ──▶ T3 ──▶ T4 ──▶  M4-α  (throwaway project, six gates)  ──▶ PR ──▶ (human merge)
                                        └──▶ T6 measurement ──▶ M4-β (prod apply, SECOND human gate)
T7 ── independent, any time before the PR
```

- **T0 first, always.** T1 before any SQL is written.
- **T3 must land in the same PR as T2**, or `master` carries a green gate reading a directory the
  schema has left.
- ⟳ **There is no longer a task that can run without T5's columns** — T5 is folded into T2, because
  round 1 proved the split it depended on does not exist.

## Gates for the milestone as a whole

1. `./scripts/check-schema-gates.sh` — six green, against the migrations.
2. `check-docs`, `check-anchors`, `check-roadmap-consistency`, `check-test-counts`,
   `check-arch-findings`, `check-ratchet-contract`, `check-gate-falsifiability` — all 0.
3. Dual adversarial review to convergence (`docs/review-method.md`).
4. **Merging is a human gate. Applying M4b to production is a SECOND human gate.**

## Open questions this plan does NOT settle

Named rather than discovered later:

- **Does `workspaces` stay 1:1 with `profiles` forever?** `:33` seeds it that way; §11.1 of the spec
  disclaims team concurrency. If the answer is "yes for now", the table is a rename in waiting and
  someone should say so.
- **What happens to `videos.playlist_id` once `workspace_videos` exists?** Two parents for one row is
  the shape ADR-0002's cross-tenant guard depends on; M4 must not quietly create a second path.
- **T4's answer depends on whether CI gets a Postgres**, which is a dev-infrastructure decision with
  its own cost.
