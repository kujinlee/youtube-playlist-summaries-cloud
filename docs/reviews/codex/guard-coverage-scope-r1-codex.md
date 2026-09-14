# Adversarial review — `guard-coverage-scope` (PR #298), round 1 (Codex)

**Both halves ran CONCURRENTLY and neither was committed until both finished** — each built its own
database (`m4_codex_review_298_*` / `m4_review_gc_claude`), so they never shared a Postgres, and the
tree was frozen throughout. That is the fix for two things measured on the previous branch: a false
Blocking from two reviewers on one database, and a second half learning the first's verdict from
`git log`.

**Verdict: 1 Blocking, 1 High, 1 Medium — all three ACCEPTED and fixed.**

⭐ **The two halves found the SAME Blocking independently** — the first overlap in five rounds across
two branches, and a useful signal in itself: the enumeration gap is visible from both a
reproduce-and-execute angle and an experiment-design angle.

---

<!-- codex-review: model=gpt-5.5 -->

**Findings**

Blocking — enumeration is still incomplete. [scripts/check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:226) only reaches CHECKs on `TABLES`, FKs/triggers on `TRIGGER_TABLES`, and `_uq` indexes on `TABLES`. On a scratch DB I measured 30 guard-like objects outside that model. The tightest one is `video_artifact_sources_pkey`: [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:235) says “One row per (artifact, source)” and creates the primary key, but the script only enumerates `_uq` unique indexes on `video_artifacts`/`video_generations` at [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:239). That is another guard on the very table this PR adds, still invisible while the script prints complete.

High — the three “wholes” still disagree. `TRIGGER_TABLES` now includes `jobs`, `videos`, etc. at [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:69), so FKs/triggers there are in scope, but CHECKs remain limited to `TABLES` at [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:227). Measured outside: `jobs_kind_chk`, `jobs_progress_phase_check`, `jobs_status_chk`, and `videos_check`. If pre-existing `videos_*` FKs are classified rather than filtered, these CHECKs need an explicit scope rule too.

Medium — the success text overclaims. The money CHECKs are defensibly outside a blob-addressing-spec gate, but they are not “not guards.” Examples: `usage_counters.used >= 0`, `spend_ledger.reserved_cents >= 0`, and `guardrail_config` caps are real money guards in [0011_cost_guardrails.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0011_cost_guardrails.sql:1); serve/correction checks continue in [0012_serve_model_charge.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:7), [0014_serve_owner_budget.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0014_serve_owner_budget.sql:6), and [0026_record_correction_spend.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0026_record_correction_spend.sql:10). Leaving them out is a scope decision, not this PR’s defect, but only if the gate says “blob-addressing schema guards,” not “every guard.”

**Clean Checks**

I do not think the five new classifications are misclassified. `video_artifact_sources_append_only` rejects update/delete of provenance operations themselves at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:1108): SHAPE. `art_summary_has_no_source` reads the inserted source row’s parent kind at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:1173): SHAPE. The two VAS FKs are referential/tenant-coordinate shape guards at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:239). `video_artifact_sources_insert_once` is correctly SEQUENCE: it compares table rows against the statement transition table at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:1138).

The SEQUENCE note is true to the trigger body: split multi-source inserts across statements are rejected, and the schema comment explicitly requires one statement at [04_artifacts.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/schema/04_artifacts.sql:1126). I did not find an intended legitimate split-statement caller.

The mutation rename is clean. `mutation_labels()` parses only labels at [check-guard-coverage.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/scripts/check-guard-coverage.py:264), and the renamed labels are at [mutate-schema.py](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing/mutate-schema.py:112). I ran the mutation suite: `58/58 mutations behaved as expected`; both renamed `video_artifact_sources_insert_once` mutations went RED for the label’s claimed behavior.

Verification: built and dropped scratch DBs only (`m4_codex_review_298_*`, `m4_mutate_base_*`). No leftovers found.

---

# Coordinator response

## BLOCKING + HIGH — one root cause: four clauses, three scopes

`CATALOG_SQL` read CHECKs on `TABLES`, FKs/triggers on `TRIGGER_TABLES`, and unique indexes on
`TABLES` **filtered to names ending `_uq`**. My first commit widened one of the four. That is round
9's defect, round 11's defect, and mine — and my own commit message called it "the third time" while
adding the fourth.

⚠ **The `_uq` filter deserves its own sentence**: `video_generations` was ALREADY in `TABLES`, so the
only thing hiding `video_generations_workspace_id_video_id_generation_id_kind_key` was a **naming
convention acting as a scope rule** — a guard that declines to be called `_uq` was not a guard. Gone.

⭐ **And the PK you named is the reconciler the Claude half's HIGH is about.**
`video_artifact_sources_pkey` is why `insert_once`'s same-set retry succeeds: the retry inserts
nothing, so the transition table is empty and the trigger never fires. The gate could not see the
object its own classification rests on.

## The fix, and the scope decision it forced

Making all four clauses read one set pulled in **17** guards including `jobs_status_chk`,
`playlists_pkey`, `videos_check` — which is your MEDIUM arriving from the other direction. The line
that is defensible is the one M4's own manifest already draws:

* **OWNED** (`workspaces`, `workspace_videos`, `video_generations`, `video_artifacts`,
  `video_artifact_sources`) — M4 creates them, so all four clauses apply.
* **FOREIGN** (`videos`, `jobs`, `playlists`, `profiles`) — M4 adds only triggers and FKs, so only
  those two clauses apply. Their PKs and CHECKs predate M4.

**41 → 55 guards**, nine of them keys classified from their WRITERS: `pg_get_constraintdef` for the
shape, then the insert that can hit it. Four are SEQUENCE with the `on conflict` arbiter named; the
rest are SHAPE, three of them with the file's "no reachable case" idiom rather than a reconciler.

## MEDIUM — accepted; the success line now says what it covers

It printed *"every guard classified"*. It now prints *"every BLOB-ADDRESSING SCHEMA guard
classified"*, with the 25 money-table CHECKs named in the code beside it. You are right that they are
guards and not non-guards; "every guard" turned a scope decision into an invisible gap.

## What I could not prove, stated rather than skipped

Three of the four new SEQUENCE keys could not be mutation-covered. I wrote the mutations, ran them,
and all three reported **❌ GREEN** — the assertion corpus never exercises the path:

    workspaces_owner_id_key   a profile cannot be inserted twice (profiles_pkey fires first)
    workspace_videos_pkey     the corpus only ever creates that pair through this same trigger
    video_generations_pkey    an identical retry short-circuits on `v_existed` before re-inserting

They are in `MUTATION_EXEMPT` — which the file documents for exactly this and demands a reason for —
with the measured reason each. The fourth, `video_artifact_sources_pkey`, **does** kill, via a
mutation that removes the emptiness guard so a retry collides.
