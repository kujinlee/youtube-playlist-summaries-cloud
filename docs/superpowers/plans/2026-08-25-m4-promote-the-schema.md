# M4 — Promote the schema as migrations

> **Anchor:** `stable-blob-addressing` — **ADR:** 0006, 0007
> **Goal:** A blob's address stops moving when a title or a serial number changes. M4 is the step that makes the accepted schema EXECUTE, for the first time outside a review's rollback.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development
> (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Milestone spine:** [`2026-08-22-append-only-generations-roadmap.md`](2026-08-22-append-only-generations-roadmap.md) → M4.
**Source of truth:** the design spec + its `schema/`, **ADR-0006** and **ADR-0007**, accepted 2026-08-24 (M3).

**v5 — four adversarial rounds, all NOT CONVERGED.** Reviews:
`docs/reviews/plan-m4-promote-schema-r{1,2}-codex.md`, `…-r3-claude.md`, `…-r4-codex.md`,
`…-r4-claude.md`, adjudicated in `…-r4-coordinator.md`. Rounds 1–3 each refuted the previous round's
*fix*, which is why the refutations are kept below rather than tidied away.

⛔ **ROUND 4 SPLIT THE HALVES: codex CONVERGED (0B/0H), claude NOT CONVERGED (2B/2H/4M/4L).** The
coordinator adjudicated **NOT CONVERGED** and hand-verified all four Blocking/High; every one
survived. `dual-review-disagreement-is-the-signal` again: the finding-reviewer was right.

⚠ **PHASE 6 FIRED ON THE COUNT AND WAS OVERRULED — deliberately, by the user, 2026-08-25.** Four
non-converging rounds is `dev-process.md`'s trigger. It was examined against the failure it was
bought to catch and **did not match**: the blob-addressing episode's signature was *fixes introducing
new Blockings, four rounds running*, whereas **exactly one** of round 4's nine findings (the `:120`
residue below) was caused by a previous round's fix. Six of the nine are things this document does
not **say** — missing paperwork, not composition defects — and the one genuinely architectural
question belongs to ADR-0006/0007, which Phase 6 is forbidden to re-litigate.
**The standing condition:** if round 5 returns **new Blockings caused by v5's own fixes**, Phase 6
fires and is not argued again.

---

## ⛔ THE FIVE THINGS A READER MUST NOT SKIP

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
in two playlists yet, not because corrections agree.** ⟳ **v5.1: T2's in-transaction guard RECORDS
the collision and lets the migration proceed — it does NOT abort**, because the pre-M4 state it
replaces is *already* incoherent (corrections are per-playlist and unsynced), so aborting would block
a fix on the grounds that the fix is lossy. See T1 for the full reasoning and for why union is
unavailable (`corrections` is free text; backlog #23 would change that). `distinct on` picks a row; the ordering only prefers *non-empty* over empty, never
one correction over another. Corrections are user-authored and, since M2 slice A, **paid**. No gate
in v1–v3 would have reported it.

**3 — v3 TOLD AN IMPLEMENTER TO SHIP `05_assert.sql` INTO PRODUCTION.** ⟳ *Round 3 B1.* v3 said
*"promote all four spec files as migrations"*. The fourth is the assertion harness, and it contains
`delete from profiles where id = p;` `[VERIFIED: schema/05_assert.sql:2207]` and `execute p_sql;` — an
**unrevoked arbitrary-SQL executor** `[VERIFIED: :37]`. "Four files" was a count written without
asking what the fourth one does.

**4 — AFTER M4-β, DELETING A PLAYLIST STRANDS PAID CORRECTIONS, AND RE-ADDING THE VIDEO BRINGS THEM
BACK.** ⟳ *Round 4 M2, **raised Medium → High by the coordinator** after confirming the path is one a
user reaches on purpose.* The mechanism, every link read:

| Step | Evidence |
|---|---|
| `videos` becomes the **child** of `workspace_videos` | `03_generations.sql:96-97` |
| `workspace_videos` cascades **only** from `workspaces` | `03_generations.sql:48` |
| deleting a playlist cascades to `videos` — and stops there | `0001_core_schema.sql:32` |
| re-ingest **keeps the orphan**: `on conflict … do nothing` | `03_generations.sql:183-187` |
| and it is a **button**, not a theoretical caller | `DeletePlaylistDialog.tsx:16` → `app/api/playlists/[id]/route.ts:74` |

Corrections are paid content since M2 slice A `[0026_record_correction_spend.sql]`. **This is the one
finding in round 4 that is not missing paperwork** — it is a design question about what deletion
*means* when the body is shared, and it is carried to *Open questions* below rather than patched
here. ⚠ It is **not** a licence to re-litigate ADR-0006/0007's shared-body semantics, accepted at M3.

**5 — THE ONE-TRANSACTION GUARANTEE IS A PROPERTY OF THE APPLY COMMAND, NOT OF THE SQL.** ⟳ *Round 4
M3.* `psql -f 0027.sql` without `--single-transaction`, or a paste into the dashboard SQL editor, does
**not** have it — and both are natural things to reach for on a hosted project at 2am. T6 now names
the command. ⚠ **And there is no `down`-shaped way back:** `supabase migration down` **exists**
(measured, CLI 2.115.0 — an earlier review claimed otherwise) but it *resets* — drop-and-recreate —
and accepts `--linked`. **It is not the rollback mechanism. T9 is.**

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
| **v4** | One transaction, three files, against a **LOCAL** stack seeded with production-shaped data | **r4-claude B1**: the one-transaction property is real (verified at the wire level) and covers the *wrong failure* — nothing addresses *applies cleanly, then is found wrong*. **B2**: no behavioural suite gates it. **H1**: M4-α is not a step you schedule |
| **v5** | Same migration; the plan now carries what it did not **say** — a rollback, a behavioural gate, an honest order, and the named apply command | — |

**v4's staging answer, corrected by r3:** M4-α runs against the **local Supabase stack the gates can
already reach**, not a hosted throwaway. The `staging-supabase-project` memory names a *hosted*
project and is the wrong pattern here — v2 cited it from the shape of the problem rather than from
what the gates can do.

---

## Tasks

- [ ] **T0 — Correct the spine, before any SQL. ⚠ MUST BE FIRST**
      Fix the M4 entry in the spine: it is not inert, it is one transaction, and it excludes
      `05_assert.sql`. A plan that corrects a document at the end leaves a window where the wrong
      sentence is the one on `master`.
      ⚠ **Gate — and v4 got this wrong twice.** ⟳ *r3 M1 said T0's gate cannot fail for T0's
      subject; v4 did not fix it, and r4-codex caught the same thing again.* `check-docs.py:447-472`
      only checks the advisory count in `roadmap-to-launch.md` — **it never reads the M4 spine.**
      The gate for T0 is therefore a **quoted diff**: the spine's M4 entry must contain the words
      *one transaction* and *not inert*, and must not contain *lands inert*. Grep for those three
      strings. A gate that cannot fail for its own subject is the thing this plan keeps writing.

- [x] **T1 — ✅ MEASURED AGAINST PRODUCTION 2026-08-25, read-only as `claude_ro`**
      Subject named before the verdict: `db=postgres user=claude_ro server=aws-0-us-east-1.pooler…`,
      `videos.workspace_id_exists=0` (confirming this is the pre-M4 world). SQL in a file — now **committed** at `docs/superpowers/specs/m4/t1-blast-radius.sql` so the
      measurement is re-runnable; 0 write statements; `psql` exit 0. ⟳ *r4-codex Low: v4 said
      "in a file" while the file was in `/tmp`. Codex independently re-ran the measurement and
      matched every figure — but a query nobody else can run is a claim, not a measurement.*

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
      **So H3 is closed for a migration run TODAY and is not closed as a property.** T2 keeps a guard,
      **and v5.1 changed what that guard DOES — it RECORDS, it does not abort.** See the decision
      immediately below.

      ⭐ **DECIDED 2026-08-25 (user) — THE COLLISION GUARD WARNS AND RECORDS; IT MUST NOT ABORT.**
      The reasoning that changed it, and it is the strongest argument anyone has made on this point:

      - **The status quo is ALREADY incoherent.** Pre-M4, corrections live per-playlist in
        `videos.data` with **no sync between rows**. Correct a video in playlist A, open it from
        playlist B, and the correction is not there. **M4 does not create the divergence — it is the
        first thing that resolves it**, and resolving it means some value wins.
      - So an **abort** blocks a fix on the grounds that the fix is lossy, **while the state it
        replaces is lossy too**. That is the wrong instrument. `a-checklist-item-can-be-an-
        unfalsifiable-guard` has a sibling: *a guard that fails closed against an improvement*.
      - **Losing a correction silently is the defect. Losing it legibly is acceptable.**

      **So T2's guard emits a row per collided `(workspace_id, video_id)` — the group key, the
      competing values, and which one won — and the migration PROCEEDS.**

      ⚠ **WHY NOT UNION, which would dissolve the question entirely: `corrections` is FREE TEXT.**
      MEASURED 2026-08-25: `types/index.ts:74` is `corrections: z.string().optional()`; the column is
      `corrections text` `[03_generations.sql:52]`; the hash takes
      `corrections_hash_of(p_corrections text)` `[:37]`; and real local values are opaque strings
      (`fix-v2`, `B`). **There is nothing to merge on.** Backlog **#23** (*corrections as deterministic
      `{from,to}` pairs*) is the **target representation, not today's** — and if it lands, union
      becomes a two-line `select` and this guard can be deleted outright. **Re-open this decision when
      #23 ships.**

      ⚠ **What generation-addressing does and does NOT cover.** Summaries, dig sections and assets are
      generation-addressed — concurrent writes land as separate `video_generations` rows and both are
      retained, so there is genuinely no collision there. **`corrections` has no generation
      dimension**: it is one mutable `text` column, written by a plain
      `update … set corrections = …` `[03:227-234]`, so last write wins. The two live on opposite
      sides of the same schema, and the append-only argument does not reach this column.
      ⚠ Also note the collision is **one owner**, not two users — `workspaces.id = profiles.id` is 1:1
      `[01_workspaces.sql:33]`, so it is one person who corrected the same video differently in two of
      their own playlists.

      **The prospective `workspace_id` is `owner_id`** — `workspaces.id = profiles.id` `[:33]`,
      `playlists.workspace_id` resolves by `owner_id` `[:37]`, `videos.workspace_id` from its
      playlist `[:42]`. Grouping by `owner_id` is therefore the correct pre-M4 translation of the
      post-M4 key, and getting that wrong would have answered a different question.

      ⭐ **What the numbers change:** 30 rows total across the three tables. **T5's work *after* the
      locks are acquired is seconds, not minutes** — which makes option (b), a stated `lock_timeout`,
      clearly the cheaper of the two. ⚠ **It does NOT bound lock ACQUISITION, and therefore does not
      retire the maintenance window — see T5.** *(⟳ r4-claude: this block asserted that it did, which
      is the sentence T5 `:167-173` had already retracted. Two copies of one inference, one of them
      corrected — the defect shape `true-about-the-name-silent-about-the-layer` names.)* Re-measure
      before M4-β; these figures decay with every ingest.

- [ ] **T2 — `0027_stable_blob_addressing.sql` — THREE files, ONE transaction**
      Promote `01_workspaces.sql`, `03_generations.sql`, `04_artifacts.sql` — **not**
      `05_assert.sql` — into **one** migration file in dependency order, removing nothing else.
      ⛔ **Splitting it is an outage** (r2): columns, backfills, `NOT NULL` promotions, both FKs and
      all nine triggers commit together or not at all. Readability is not worth an outage window.
      **Add the missing guard:** `revoke all on workspaces from anon, authenticated`. ⟳ *r3 H1:
      `workspaces` is the **only** new table with **0** revokes, against 8 in `03` and 12 in `04`.
      Supabase grants at CREATE time, so an absent revoke is not neutral —
      `anon-execute-is-the-default-not-a-decision`.* ✅ **Re-confirmed by the coordinator at r4:**
      5 tables created across `01/03/04`, 4 revoked; `01_workspaces.sql` carries **zero**.

      ⛔ **WRITING THIS FILE *IS* M4-α — IT IS NOT A STEP YOU SCHEDULE.** ⟳ *r4-claude H1.*
      `tests/integration/global-setup.ts:43-51` runs `npx supabase migration up` on **every**
      integration run and **throws rather than skip** (*"the suite would be testing an UNKNOWN
      schema"*). So the moment `0027` exists on the branch, the next `npm run test:integration` on
      **any** machine applies the whole of M4 to that machine's stack — unseeded, ungated, before T4
      has decided what seeding means. **The order block below is written to match that reality
      rather than to contradict it.** Anyone running the suite on this branch should expect it.

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
      extend its `MONEY_TABLES` to **all five** new tables — **`workspaces`, `workspace_videos`,
      `video_generations`, `video_artifacts`, `video_artifact_sources`** — **before** M4-β, so the
      baseline is set against the pre-M4 world. ⟳ *r3 H1; **corrected by r4-claude H2**, which caught
      that v4 said "the new **manifest** tables" — and `workspaces` is the tenancy root, not a
      manifest table. Read literally, v4 added the four that were already safe and skipped the only
      one that was not.* **Name the five; do not name a category.**
      ⚠ **`--local` and `--prod` are NOT one check at two times.** The script's own docstring records
      the class (`:27-33`), and it re-measures as **5** anon-executable definer functions locally
      against **10** in production. **`--prod` at M4-β is the gate; `--local` is a smoke test.**
      ⟳ *r4-claude H2 reports a second instance — prod's default ACL carries `arwdDxtm` where local
      carries `Dxtm`.* ⚠ **The local half is coordinator-MEASURED; the production half is the
      reviewer's figure and was NOT independently re-measured** (no `CLAUDE_RO_DATABASE_URL` in the
      coordinator's environment). **Re-measure before this drives work.**

- [ ] **T4 — Give `05_assert.sql` a home that is not a migration**
      It cannot run standalone `[VERIFIED: scripts/check-schema-gates.sh:14-16]`, and it asserts M4-β
      behaviour — it reads `videos.workspace_id` `[:893-911]` and checks that plain inserts derive
      `workspace_id` `[:1843-1859]`.
      ⟳ **r3 B4: state which assertions are vacuous on an unseeded database and what covers them
      instead** — or seed M4-α with production-shaped data. "Run the assertions" is not a gate until
      that is answered.

      ⭐ **MEASURED 2026-08-25 (v5) — "PRODUCTION-SHAPED" IS NOT ENOUGH, AND THE LOCAL STACK PROVES
      IT.** Local holds far more data than prod (`playlists=5124 videos=3547 jobs=87`, **108** videos
      with corrections) and **45** video ids sitting in more than one playlist. It still measures:

      ```
      LOCAL multi_row_groups=0        LOCAL CONFLICTING_GROUPS=0
      ```

      Because those 45 are the same video under **different owners** — and the collision that destroys
      content needs two rows in **one workspace**. So the corrections-collision assertion is
      **vacuous on the local stack too**, for the same reason it reads zero in production.
      ⛔ **T4's seeding must CONSTRUCT that case deliberately** — two `videos` rows, one `owner_id`,
      one `video_id`, two *different* non-empty corrections — or M4-α will report a green assertion
      that never evaluated anything. Copying production shape reproduces production's *blind spot*.
      ⟳ **v5.1 — the constructed case now tests a DIFFERENT thing, and it matters more.** Since the
      guard records rather than aborts, the seed no longer proves "the migration refuses"; it proves
      **the collision report is emitted, names the right group, and states which value won**. A
      warn-path that nobody has triggered is worth less than an abort nobody has triggered, because
      its output is the entire deliverable. **Assert the report's CONTENT, not just its existence.**
      ⟳ **r4-claude M1 — AND THE RE-RUNNABLE HOME NEEDS A SECOND ANSWER, FOR A *DRIFTED* DATABASE.**
      v4 said *"whichever home is chosen, `check-schema-gates.sh` runs it"* — i.e. repeatedly, against
      whatever state the DB is in. But the backfill assertion's own precondition, three lines above it,
      is *"the subject here is the MIGRATION'S OUTPUT, so nothing may have touched the table yet"*
      `[05_assert.sql:56-58]`, and its two sides **diverge permanently after any ordinary deletion** —
      the same orphan mechanism as item 4 above. So its first failure in production will be
      **`ASSERTION FAILED — backfill lost corrections`** about a backfill that ran correctly weeks
      earlier. **Classify every assertion as MIGRATION-ONLY or RE-RUNNABLE, and let the re-runnable
      home execute only the second class.** A gate that cries wolf is retired by the third person who
      sees it.
      **Gate:** whichever home is chosen, `./scripts/check-schema-gates.sh` runs it, and the
      cannot-run case exits **non-zero** saying *treat this as NOT RUN* — never 0.

- [ ] **T5 — Pick ONE production strategy for the migration window. ⚠ NOT "either/or"**
      ⟳ **r3 H2: Codex r2's lock finding survived v3 unaddressed, and the consequence was never
      stated — the app and worker stall for the whole M4-β window.**
      ⟳ **DECIDED by T1's measurement: option (b).** Production holds `playlists=3 videos=12
      jobs=15` — 30 rows across the three tables — so the rewrite and the `NOT NULL` promotions are
      a matter of seconds and a maintenance window would cost more than it buys. **Set an explicit
      `lock_timeout` (start at `5s`) and `statement_timeout`, and let the migration ABORT rather than
      queue behind a long-running worker transaction.**
      ⟳ **r4-codex Medium — the inference was overstated and is corrected here.** 30 rows bounds the
      **work after the locks are acquired**; it says nothing about **time to acquire
      `ACCESS EXCLUSIVE`** on three tables a live worker writes to. So the position is *"try without
      a maintenance window, abort safely, and have a pause-the-worker runbook for the case where
      lock acquisition fails"* — **not** *"a maintenance window is unnecessary"*. **Write that
      runbook as part of T5**; a strategy whose failure branch is undefined is half a strategy. ⚠ Re-measure at M4-β: this decision is a
      function of the row counts, and it flips if they grow by orders of magnitude.

- [ ] **T6 — M4-α, then M4-β — ⚠ NAME THE COMMAND, because the atomicity depends on it**
      **M4-α:** apply `0027` to the **local** Supabase stack, seeded per T4; run all six gates plus
      `check-anon-exposure --local`. ⚠ Per T2, an unseeded M4-α has **already happened** on any
      machine that ran the integration suite after `0027` landed; this is the *deliberate, seeded*
      one.
      **M4-β:** the same migration against production, applied with **exactly**:

      ```
      supabase link --project-ref <ref>
      supabase db push --dry-run     # read it
      supabase db push --linked
      ```

      ⟳ **r4-claude M3.** v4 said only *"the same migration against production"*. `supabase migration
      up` is documented as applying to the **local** database; the repo's production path is
      `db push` `[docs/deploy.md:30-31]`, and the last real prod apply is recorded as
      `supabase db push --linked` `[docs/roadmap-to-launch.md:162]`.
      ⛔ **The one-transaction guarantee is VOID for any other apply method** — `psql -f` without
      `--single-transaction`, or a dashboard paste, gives no such property. **Record the CLI version
      used** (2.115.0 at time of writing); the guarantee was verified against that batching behaviour,
      not against SQL semantics.
      ⚠ **Two human gates — one to merge, one to apply.** Blocked on T1's corrections-collision count
      being zero, or on a merge step existing.

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

- [ ] **T9 — Ship a rollback in the same PR as the migration ⚠ NEW IN v5 (r4-claude B1)**
      ⛔ **The plan had no recovery path — not a heading, not a sentence.** Its whole argument was
      T2's *"commit together or not at all"*, which is real (verified at the wire level) and answers
      the **wrong failure**. The case that matters is **`0027` applies cleanly and is then found
      wrong**, and this schema has produced that outcome **twice**, by executing, both times leaving
      production unable to ingest `[03_generations.sql:98-107]`.
      **Write `0028_rollback_stable_blob_addressing.sql`, in the same PR as `0027`.**
      **State the property that makes it lossless, as a falsifiable sentence:** *every column and row
      `0027` creates is a function of state that predates it, and nothing in `lib/ app/ worker/`
      writes any of it.* **T7's repo-wide grep is already the command that tests it** — reuse it, do
      not write a second one.
      ⚠ **This property EXPIRES AT M5**, the moment `record_artifact` gets a caller. Say so in
      `0028`'s own header, where the person reaching for it will be looking.
      ⛔ **`supabase migration down` is NOT this.** It exists (measured, CLI 2.115.0) but *resets* —
      drop-and-recreate — and takes `--linked`. **Say that in the header too**, because the reviewer
      who first raised B1 believed the command did not exist at all, and the person at 2am will find
      it in `--help` and reach for it.
      **Gate:** `0028` applies cleanly to the M4-α stack **after** `0027`, and the six schema gates go
      **red** afterwards — proving it actually removed the schema rather than reporting success over
      an empty set. A rollback nobody has executed is a paragraph.

- [ ] **T10 — Put a behavioural suite in the gate list ⚠ NEW IN v5 (r4-claude B2)**
      ⛔ **No gate anywhere would notice `0027` breaking an existing write path.** The words
      *integration*, *e2e* and *test suite* appear **nowhere** in v4, and
      `.github/workflows/ci.yml:6-10` excludes `test:integration` in its own words. The six schema
      gates test the schema **against itself**; they never call an application RPC.
      **What is uncovered:** the nine new triggers sit on the insert path of `claim_video_slot`
      `[0023:87]`, `persist_summary` / `reserve_video_slot` `[0009:94-96]`, `enqueue_job`
      `[0009:26-27]`, and the direct PostgREST writes at `supabase-metadata-store.ts:183-191` and
      `summary-handler.ts:132-134`. Measured in prod today the four tables carry **2** triggers; M4
      takes them to **11**.
      **Add `npm run test:integration` as an M4-α gate**, run against a named commit, plus
      `test:e2e:cloud` if the stack is up. ⚠ Per `CLAUDE.md`, **if the stack is unavailable the gate
      exits non-zero saying *treat this as NOT RUN*** — a skipped suite must never read as a pass.
      ⚠ **This is the gate H1 makes urgent:** the unseeded auto-apply already happens on every
      developer's machine, so the suite is the only thing standing between that and a silent break.

---

## Order

```
T0 ─▶ T1 ─▶ T4(seeding decision) ─▶ T2 ═╤═▶ T3 ─▶ T9 ─▶ T10 ─▶ T5 ─▶ M4-α(deliberate, seeded)
                                        ║
                                        ╚═▶ ⚡ UNSEEDED M4-α FIRES HERE, on every machine that
                                              runs `npm run test:integration` from now on
      ─▶ PR ─▶ (human merge) ─▶ M4-β ─▶ (second human gate)
T7, T8 ── any time before the PR
```

⟳ **v5 REORDERED THIS, because v4's order was not true** (r4-claude H1). Two changes:

- **T4's seeding decision moves BEFORE T2.** v4 put it after, but T2 is the step that creates the
  file, and creating the file is what triggers the unseeded apply. Deciding what seeding means
  *after* the first apply has happened is deciding it too late.
- **The unseeded M4-α is drawn as a branch, not omitted.** It is not optional and not scheduled —
  it is a consequence of `global-setup.ts:43-51`. A diagram that shows only the intended path is the
  same defect as a gate that only reports success.

T0 first, T1 before any SQL. T3 lands in the same PR as T2, or `master` carries a green gate reading
a directory the schema has left. **T9 and T10 land in that same PR** — a rollback that arrives after
the migration, and a test gate that arrives after the triggers, are both artifacts that missed the
only moment they were worth having.

## Gates for the milestone

1. `./scripts/check-schema-gates.sh` — six green **against the migration**, after T3's rewrite.
2. `check-anon-exposure.py --local` (smoke), then **`--prod` at M4-β (the real gate)** — they measure
   different worlds, 5 findings vs 10. ⟳ *r4-claude H2.*
2b. **`npm run test:integration` green against a named commit** — the only gate that calls an
   application RPC. Unavailable stack ⇒ **exit non-zero, "treat this as NOT RUN"**. ⟳ *T10, r4-claude B2.*
2c. **`0028` applies after `0027`, and the schema gates then go RED** — proving the rollback removed
   the schema instead of passing over an empty set. ⟳ *T9, r4-claude B1.*
3. `check-docs`, `check-anchors`, `check-review-rounds`, `check-roadmap-consistency`,
   `check-test-counts`, `check-arch-findings`, `check-ratchet-contract`,
   `check-gate-falsifiability` — all 0.
4. Dual adversarial review to convergence — **both halves**, per `check-review-rounds.py`.
5. **Merging is a human gate. Applying M4-β to production is a second one.**

## Open questions this plan does NOT settle

### ⭐ THE ONE THAT NEEDS A HUMAN DECISION — what does DELETING mean when the body is shared and PAID?

⟳ *Round 4 M1 + M2, one root cause. **The only finding in round 4 that is not missing paperwork.***
Full mechanism in item 4 of the must-not-skip block above; in short: after M4-β, deleting a playlist
strands the `workspace_videos` row — corrections included — and re-adding the video silently
reattaches them, because the derive trigger is `on conflict … do nothing`.

**This is deliberately NOT patched in v5.** Picking a behaviour here is a product decision about paid
content, and three of the four options are defensible:

| Option | What it does | Cost |
|---|---|---|
| **(a) Cascade the delete** | orphaned `workspace_videos` rows go when the last referencing `videos` row goes | destroys paid corrections the user may want back on re-add — *irreversibly*, and it is the behaviour they did not ask for |
| **(b) Clear on delete, keep the row** | blank `corrections` but keep the shared body | same content loss, less structural churn |
| **(c) Keep and DOCUMENT it as a feature** | "your corrections survive removing and re-adding a video" | free, arguably the nicest behaviour — but it must be **stated**, or it is a surprise |
| **(d) Keep and say nothing** | today's accidental behaviour | ⛔ **rejected** — an unstated behaviour on a paid path is how this repo defines a defect |

⚠ **v5.1 — THE ORPHAN IS UNRECONSTRUCTABLE, WHICH RAISES THE STAKES ON THIS DECISION AND ON T9.**
`corrections` is **free text** (`types/index.ts:74`, `03_generations.sql:52` — MEASURED 2026-08-25),
and the sync is one-way `videos → workspace_videos` `[03:227-234]`. So once the `videos` rows are
deleted, the orphaned `workspace_videos.corrections` value exists **nowhere else and cannot be
derived from anything**. Consequences, both load-bearing:
- option **(a)** does not merely "destroy paid corrections" — it destroys them **irrecoverably**;
- **T9's lossless-rollback proof fails on exactly this row.** `0028` would drop a table holding the
  only copy of paid content. ⟳ *This is the counterexample behind r5's Blocking; the two findings are
  one defect seen from opposite ends, and v5 filed them separately without noticing.*

**Recommendation: (c).** It preserves content the user paid for, it costs nothing to implement, and
the defect is entirely that nobody wrote it down. ⚠ **It needs one guard either way:** no gate in
this plan compares corrections **values** across a delete/re-add — `05_assert.sql` compares *counts*
(r3 H3) — so whichever option wins, the assertion that enforces it does not exist yet.

⚠ **Not a licence to reopen ADR-0006/0007.** The shared body is accepted design (M3). The question is
only what *deletion* does to it, which no ADR settles.

### The rest

- **Does `workspaces` stay 1:1 with `profiles`?** `:33` seeds it that way and §11.1 disclaims team
  concurrency. If the answer is "yes for now", it is a rename in waiting and someone should say so.
- **What happens to `videos.playlist_id` once `workspace_videos` exists?** Two parents for one row is
  the shape ADR-0002's cross-tenant guard depends on.
- **T4's answer depends on whether CI gets a Postgres**, a dev-infrastructure decision with its own cost.
- ⟳ *r3 L1 REFUTED the "can this run in one transaction?" worry in advance — `01/03/04` contain no
  statement that cannot. Recorded so it is not re-raised.*
