# M4 — Promote the schema as migrations

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes. M4 is the step that makes the accepted schema EXECUTE, for the first time outside a review's rollback.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Milestone spine:** [`2026-08-22-append-only-generations-roadmap.md`](2026-08-22-append-only-generations-roadmap.md) → M4.
**Source of truth:** the design spec + its `schema/`, **ADR-0006** and **ADR-0007**, accepted 2026-08-24 (M3).

**v4 — three adversarial rounds, all NOT CONVERGED.** Reviews:
`docs/reviews/plan-m4-promote-schema-r{1,2}-codex.md`, `…-r3-claude.md`. Each round refuted the
previous round's *fix*, which is why the refutations are kept below rather than tidied away.

---

## ⛔ THE THREE THINGS A READER MUST NOT SKIP

**1 — M4 IS NOT "INERT".** The spine says the schema *"lands inert. No application caller yet."* The
second half is true; the first is false. `01_workspaces.sql:36-48` adds `workspace_id` to
**`playlists`, `videos`, `jobs`**, backfills every row, and sets each `NOT NULL`; `03_generations.sql`
attaches **nine triggers to live tables** and adds two FKs. *"No caller"* was never the property that
mattered.

**2 — THE BACKFILL CAN DESTROY USER CONTENT, SILENTLY.** ⟳ *Round 3 H3.*
`03_generations.sql:89-95` fills `workspace_videos` with:

```sql
select distinct on (workspace_id, video_id) …, nullif(data->>'corrections', ''), …
  from videos order by workspace_id, video_id, (coalesce(data->>'corrections','') <> '') desc;
```

**One video in two playlists of one workspace, with different corrections in each, keeps ONE and
drops the other.** ✅ **MEASURED 0 in production 2026-08-25 (T1) — but zero because no video is
in two playlists yet, not because corrections agree.** T2 carries an in-transaction assertion. `distinct on` picks a row; the ordering only prefers *non-empty* over empty, never
one correction over another. Corrections are user-authored and, since M2 slice A, **paid**. No gate
in v1–v3 would have reported it.

**3 — v3 TOLD AN IMPLEMENTER TO SHIP `05_assert.sql` INTO PRODUCTION.** ⟳ *Round 3 B1.* v3 said
*"promote all four spec files as migrations"*. The fourth is the assertion harness, and it contains
`delete from profiles where id = p;` `[VERIFIED: schema/05_assert.sql:2207]` and `execute p_sql;` — an
**unrevoked arbitrary-SQL executor** `[VERIFIED: :37]`. "Four files" was a count written without
asking what the fourth one does.

---

## What M4 does NOT do

- **No application caller.** Nothing in `lib/ app/ worker/` calls `record_artifact` or reads
  `video_artifacts_current` when M4 lands. That is M5.
- **No blob re-keying, no GC, no generation backfill.** M5 and M7.
- **No render addressing** — out of scope by user decision 2026-08-09 (backlog #25).
- **`05_assert.sql` is NEVER a migration.** ⟳ *Round 3 B1.* It is a harness; T4 gives it a home that
  is not `supabase/migrations/`.

---

## The refutation trail — kept, because each fix caused the next finding

| Version | Central idea | Killed by |
|---|---|---|
| **v1** | Split M4a (new tables) / M4b (live-table changes) | **r1**: `workspace_videos`' backfill selects `workspace_id` **FROM `videos`** `[:89-95]`; the FK at `:96-97` references it. The new tables cannot exist before the new columns |
| **v2** | *"You cannot split the DDL, only the ENVIRONMENTS"* — M4-α on a throwaway **hosted** project | **r3 B2**: five of six gates reach Postgres by `docker exec` into a hardcoded container `[verify-schema.sh:9-12]`, so a hosted project is unreachable. **r3 B4**: gate 1's assertions need a *populated* corpus, so an empty project hard-fails or passes vacuously |
| **v3** | Split the promotion across migration files | **r2**: `enqueue_job` inserts into `jobs` without `workspace_id` `[0009:26-27]` and the derive-trigger lands later `[03:156, :200-215]` — **every enqueue fails between the two commits** |
| **v4** | One transaction, three files, against a **LOCAL** stack seeded with production-shaped data | — |

**v4's staging answer, corrected by r3:** M4-α runs against the **local Supabase stack the gates can
already reach**, not a hosted throwaway. The `staging-supabase-project` memory names a *hosted*
project and is the wrong pattern here — v2 cited it from the shape of the problem rather than from
what the gates can do.

---

## Tasks

- [ ] **T0 — Correct the spine, before any SQL. ⚠ MUST BE FIRST**
      Fix the M4 entry in the spine: it is not inert, it is one transaction, and it excludes
      `05_assert.sql`. A plan that corrects a document at the end leaves a window where the wrong
      sentence is the one on `master`. **Gate:** `check-docs` 0. No code.

- [x] **T1 — ✅ MEASURED AGAINST PRODUCTION 2026-08-25, read-only as `claude_ro`**
      Subject named before the verdict: `db=postgres user=claude_ro server=aws-0-us-east-1.pooler…`,
      `videos.workspace_id_exists=0` (confirming this is the pre-M4 world). SQL in a file; 0 write
      statements; `psql` exit 0.

      | Question | Answer | Query |
      |---|---|---|
      | **CONFLICTING corrections groups (r3 H3)** | **0** | `group by owner_id, video_id … having count(distinct data->>'corrections') > 1` |
      | videos carrying a non-empty corrections value | 1 | `where coalesce(data->>'corrections','') <> ''` |
      | same video twice under one prospective workspace | **0** | `group by owner_id, video_id having count(*) > 1` |
      | a video in 2+ playlists at all | **0** | `group by video_id having count(distinct playlist_id) > 1` |
      | orphans that defeat `SET NOT NULL` | **0 / 0 / 0** | three `left join … is null` counts |
      | rows the `NOT NULL` promotions rewrite | `playlists=3 videos=12 jobs=15` | `count(*)` each |
      | `pgcrypto` / `digest` in prod | installed=1, callable=2 | `pg_extension`, `pg_proc` |

      ⚠ **READ WHY IT IS ZERO, NOT JUST THAT IT IS.** The conflicting-corrections count is zero
      **because the precondition does not exist yet** — no video sits in two playlists at all
      (`multi_row_groups = 0`). It is *not* zero because two corrections happened to agree. Adding
      one video to a second playlist is an ordinary user action, and it makes the count able to move.
      **So H3 is closed for a migration run TODAY and is not closed as a property.** T2 keeps a guard:
      the migration asserts the count is still zero **inside the same transaction**, immediately
      before the `workspace_videos` backfill, and aborts if it is not.

      **The prospective `workspace_id` is `owner_id`** — `workspaces.id = profiles.id` `[:33]`,
      `playlists.workspace_id` resolves by `owner_id` `[:37]`, `videos.workspace_id` from its
      playlist `[:42]`. Grouping by `owner_id` is therefore the correct pre-M4 translation of the
      post-M4 key, and getting that wrong would have answered a different question.

      ⭐ **What the numbers change:** 30 rows total across the three tables. **T5's lock window is
      seconds, not minutes** — which makes option (b), a stated `lock_timeout`, clearly the cheaper
      of the two, and removes the case for a maintenance window at this data size. Re-measure before
      M4-β; these figures decay with every ingest.

- [ ] **T2 — `0027_stable_blob_addressing.sql` — THREE files, ONE transaction**
      Promote `01_workspaces.sql`, `03_generations.sql`, `04_artifacts.sql` — **not**
      `05_assert.sql` — into **one** migration file in dependency order, removing nothing else.
      ⛔ **Splitting it is an outage** (r2): columns, backfills, `NOT NULL` promotions, both FKs and
      all nine triggers commit together or not at all. Readability is not worth an outage window.
      **Add the missing guard:** `revoke all on workspaces from anon, authenticated`. ⟳ *r3 H1:
      `workspaces` is the **only** new table with **0** revokes, against 8 in `03` and 12 in `04`.
      Supabase grants at CREATE time, so an absent revoke is not neutral —
      `anon-execute-is-the-default-not-a-decision`.*

- [ ] **T3 — REPAIR the guard inventory, then re-point the gates ⚠ LANDS WITH T2**
      ⟳ **r3 B3: gate 3 is RED against the schema M4 promotes, before any re-pointing.**
      `check-guard-coverage.py` names `art_pending_is_leased`, `art_pending_has_token` and
      `art_pending_has_reserved_at` — **verified absent** from the schema outside comments — and has
      **zero** entries for `video_artifact_sources`. Repair the inventory first; re-pointing a stale
      one changes what it measures without saying so.
      ⛔ **Gates 1 and 2 are a REWRITE, not a re-point** (r2): `verify-schema.sh` concatenates spec
      files inside one rollback transaction `[:8-10]`; `mutate-schema.py` hardwires two named spec
      files and copies the verifier into temp `[:25-27, :875-884]`. Estimate accordingly.
      **Gate for T3 itself:** each rewritten gate goes **red on a mutation** — delete one guard from
      the migration and confirm failure. A gate that passes because it now reads an empty set is a
      measured failure mode of this repo, twice.
      **Add to the gate list:** `check-anon-exposure.py --local` (M4-α) and `--prod` (M4-β), and
      extend its `MONEY_TABLES` to the new manifest tables **before** M4-β, so the baseline is set
      against the pre-M4 world. ⟳ *r3 H1.*

- [ ] **T4 — Give `05_assert.sql` a home that is not a migration**
      It cannot run standalone `[VERIFIED: scripts/check-schema-gates.sh:14-16]`, and it asserts M4-β
      behaviour — it reads `videos.workspace_id` `[:893-911]` and checks that plain inserts derive
      `workspace_id` `[:1843-1859]`.
      ⟳ **r3 B4: state which assertions are vacuous on an unseeded database and what covers them
      instead** — or seed M4-α with production-shaped data. "Run the assertions" is not a gate until
      that is answered.
      **Gate:** whichever home is chosen, `./scripts/check-schema-gates.sh` runs it, and the
      cannot-run case exits **non-zero** saying *treat this as NOT RUN* — never 0.

- [ ] **T5 — Pick ONE production strategy for the migration window. ⚠ NOT "either/or"**
      ⟳ **r3 H2: Codex r2's lock finding survived v3 unaddressed, and the consequence was never
      stated — the app and worker stall for the whole M4-β window.**
      ⟳ **DECIDED by T1's measurement: option (b).** Production holds `playlists=3 videos=12
      jobs=15` — 30 rows across the three tables — so the rewrite and the `NOT NULL` promotions are
      a matter of seconds and a maintenance window would cost more than it buys. **Set an explicit
      `lock_timeout` (start at `5s`) and `statement_timeout`, and let the migration ABORT rather than
      queue behind a long-running worker transaction.** ⚠ Re-measure at M4-β: this decision is a
      function of the row counts, and it flips if they grow by orders of magnitude.

- [ ] **T6 — M4-α, then M4-β**
      **M4-α:** apply `0027` to the **local** Supabase stack, seeded per T4; run all six gates plus
      `check-anon-exposure --local`.
      **M4-β:** the same migration against production. ⚠ **Two human gates — one to merge, one to
      apply.** Blocked on T1's corrections-collision count being zero, or on a merge step existing.

- [ ] **T7 — The `doc_key` ⟷ `inflight_uq` coupling (task #45)**
      ⟳ *r2 High / r3 M3:* there is nothing to *defer* — promoting `04_artifacts.sql` already ships
      the post-deletion protocol (the index is absent by design `[:269-288]`, `record_artifact` is
      granted to `service_role` `[:354-360, :628-633]`).
      **Establish REPO-WIDE, by search and not by reading one file, that no caller reaches
      `record_artifact` for a paid kind after M4-β**, and record the grep with its count. ⟳ *r3 M3:
      v3 said "by reading the live serve path", which proves something about `serve-doc.ts` and
      nothing about the repo.* Then write the coupling into M5's entry.

- [ ] **T8 — Arm backlog #26 with an observable trigger**
      ⟳ *r3 M2: v3's own paragraph called this "a decision wearing a checkbox" and then wrote one.*
      #26's trigger must be something a command can see — *"fails the moment a non-test caller
      reaches `record_artifact` for a paid kind"* — and T7's grep is that command. Wire it.

---

## Order

```
T0 ─▶ T1 ─▶ T2 ─▶ T3 ─▶ T4 ─▶ T5 ─▶ M4-α ─▶ PR ─▶ (human merge) ─▶ M4-β ─▶ (second human gate)
T7, T8 ── any time before the PR
```

T0 first, T1 before any SQL. T3 lands in the same PR as T2, or `master` carries a green gate reading
a directory the schema has left.

## Gates for the milestone

1. `./scripts/check-schema-gates.sh` — six green **against the migration**, after T3's rewrite.
2. `check-anon-exposure.py --local`, then `--prod` at M4-β.
3. `check-docs`, `check-anchors`, `check-review-rounds`, `check-roadmap-consistency`,
   `check-test-counts`, `check-arch-findings`, `check-ratchet-contract`,
   `check-gate-falsifiability` — all 0.
4. Dual adversarial review to convergence — **both halves**, per `check-review-rounds.py`.
5. **Merging is a human gate. Applying M4-β to production is a second one.**

## Open questions this plan does NOT settle

- **Does `workspaces` stay 1:1 with `profiles`?** `:33` seeds it that way and §11.1 disclaims team
  concurrency. If the answer is "yes for now", it is a rename in waiting and someone should say so.
- **What happens to `videos.playlist_id` once `workspace_videos` exists?** Two parents for one row is
  the shape ADR-0002's cross-tenant guard depends on.
- **T4's answer depends on whether CI gets a Postgres**, a dev-infrastructure decision with its own cost.
- ⟳ *r3 L1 REFUTED the "can this run in one transaction?" worry in advance — `01/03/04` contain no
  statement that cannot. Recorded so it is not re-raised.*
