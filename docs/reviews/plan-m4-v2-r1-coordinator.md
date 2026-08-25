# M4 plan v2 — round 1 COORDINATOR adjudication

**Subject:** `docs/superpowers/plans/2026-08-25-m4-promote-the-schema-v2.md` @ `7faade5`
**Halves:** `plan-m4-v2-r1-codex.md` (**NOT CONVERGED**, 7B/3H/2M) · `plan-m4-v2-r1-claude.md` (**NOT CONVERGED**, 6B/…)

**Anchor:** stable-blob-addressing · **ADR:** 0006, 0007, 0011

---

## Verdict: NOT CONVERGED. Both halves agree, and they agree on the same defect.

**The plan is not executable as written.** Both reviewers independently reached that conclusion, and
the Claude half proved it by **executing** the plan's own SQL.

---

## ⭐ THE FINDING: the rollback would cause the outage it exists to prevent, and my gate blesses it

`0028` — the recovery mechanism — **does not run**, and the fix Postgres itself suggests makes it
catastrophic. Chain, every link measured:

1. **It fails on its own first statement.** `drop view video_artifacts_current` errors: *"cannot drop
   view … because other objects depend on it — view `video_generations_collectable` depends on it"*.
   The plan drops the dependency before the dependent `[04:918 selects from 04:728]`.
2. **Reorder those and it fails again**, independently: *"cannot drop column `workspace_id` of table
   `playlists` because … trigger `playlists_resolve_workspace_upd_trg` depends on it"*. A column-list
   trigger `[03:201-203]` is a hard dependency on the column.
3. **Postgres' own `HINT` on both errors is "Use DROP … CASCADE"** — the fix an implementer reaches
   for at 2am.
4. **COORDINATOR-VERIFIED INDEPENDENTLY, and worse than the review reported.** I ran
   `drop table workspaces cascade` against a freshly-built 01+03+04 in a rolled-back transaction.
   **All seven workspace triggers survive** — not just the four the review found; the `_upd_` ones
   survive the *table* drop too, because only the *column* drop cascades them:

   ```
   SURVIVING: jobs_resolve_workspace_ins_trg / _upd_trg        on jobs
   SURVIVING: playlists_resolve_workspace_ins_trg / _upd_trg   on playlists
   SURVIVING: profiles_ensure_workspace_trg                    on profiles
   SURVIVING: videos_resolve_workspace_ins_trg / _upd_trg      on videos
   ```

5. **Every one of them references `public.workspaces`, which is gone.** The review measured the
   consequence on a real signup:

   > `ERROR: relation "public.workspaces" does not exist` … in `ensure_workspace_for_profile()` …
   > called from `handle_new_user()`

   **No user can sign up.** Playlist creation and every enqueue break identically, via
   `resolve_workspace_from_playlist()` `[03:162, :168]`.

6. **And `check-live-schema.py --expect-absent` returns EXIT 0 on that database.** Its `verdict()`
   checks five tables and three columns; both sets are empty, so it passes — over a database where
   the product is dead.

**The recovery mechanism causes the outage, and the instrument written to verify recovery reports
success.** This is the architecture review's finding 3 (*gates that cannot see live state*) reproduced
inside the very task written to fix it — one week's lesson, re-learned one task later.

---

## What both halves found, and where they agree

| # | Finding | Codex | Claude | Coordinator |
|---|---|---|---|---|
| `0028` drop order fails | B2 | B1 | **VERIFIED** — reproduced both errors |
| `0028` leaves functions / type / live-table triggers | B2 | B2 ⭐ | **VERIFIED, and broader** — 7 triggers survive, not 4 |
| `check-live-schema.py` too narrow to prove absence | B7 | B2 | **VERIFIED** — 5 tables + 3 columns cannot see 13 functions, 1 type, 7 triggers |
| Gate polarity unsatisfiable after `0027` | B1 | B6 | **VERIFIED** — `check-schema-gates.sh:22-27` fails on any non-zero; Task 3 hard-wires `--expect-absent` |
| `05_assert.sql` still references corrections | B3 | B3 | **VERIFIED** — 52 refs; Task 8 says "classification comments only" |
| Line citations invalidated by Task 1's own steps | H1 | B4 | **VERIFIED** — 89→87, 183→181, 227→225, 253→251 after deleting `:52,:61` |
| Task 8's `awk` selector | B6 | B5 | selects nothing today, exits 0, prints "passed" — **fail-open** |
| Seed corpus violates `NOT NULL` | B5 | — | **VERIFIED** — `playlists.playlist_url` is `not null` `[0001:14]` |
| Task 5 misses `sync_corrections_to_workspace_video` in the ratchets | H3 | — | to verify at fold-in |

**Coordinator-found, before either half reported:** Task 1 Step 1 expects
`grep -c "corrections" 03_generations.sql` = **20**; it is **50**. I carried a comment-filtered count
into an unfiltered command. **The plan's very first verification step fails.**

---

## The complete inventory, derived rather than listed

Neither the plan nor either review had this. Generated from the schema:

**44 objects** — 5 tables · 3 views · 14 functions · 15 triggers · 1 enum · **3 indexes** (not 1 —
two are `create unique index`) · 5 policies. After ADR-0011: **13 functions, 13 triggers**.

**The distinction that makes `0028` writable:** triggers on M4's **own** tables die with
`drop table`; the **7 on live tables** must be named explicitly, because their tables survive.
Working order, measured: live-table triggers → `video_generations_collectable` →
`video_artifacts_current` → `video_summary_current` → tables → columns → `workspaces` → functions →
type. Reaches `DROP_OK` with **no `cascade`**.

---

## Hygiene

The Claude half executed real DDL. **Coordinator-verified afterwards:** 0 stray M4 tables, 0 stray
`workspace_id` columns, counts unchanged at `playlists=5124 videos=3547`, working tree clean apart
from the two review files. Clean.

## Disposition

**v2.1 folds all of it.** This is round 1 of a fresh plan — the findings are dense but they are
*first-round* findings on a document that has never been reviewed, not the fix-induced kind that
fired Phase 6. **The standing condition still applies**: if round 2 returns new Blockings caused by
v2.1's own fixes, that is the signal, not the count.

⚠ **Verified against `7faade5`.** Both reviews target that commit.
