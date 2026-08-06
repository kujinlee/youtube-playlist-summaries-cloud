<!-- codex-review: model=gpt-5.5 -->

DDL execution note: I could not run live Postgres from this sandbox. `psql` is absent, Docker socket access is denied, and TCP to `127.0.0.1:54322` is denied. I did not mark any new finding `MEASURED`.

**JOB 1 — Physical Rules**

**BLOCKING**

1. `workspaces` seeding still has two incompatible migrations: first inserts random ids, then later inserts `id = owner_id`, which violates `unique(owner_id)` if both are applied.
Failure: existing profile `U` gets workspace `(random, U)` at lines 399-406, then line 543 tries `(U, U)` and aborts.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:399), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:541).
Change: make the only backfill `insert into workspaces (id, owner_id) select id, id from profiles`, then backfill playlists from that.

2. `videos.workspace_id` repeats physical rule 4: it is added `not null` on a populated table, with no backfill and no `workspace_videos` population before the composite FK.
Failure: any existing `videos` row aborts on `alter table videos add column workspace_id uuid not null`; if made nullable, the FK still fails until `(workspace_id, video_id)` rows exist.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:496), [current schema]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0001_core_schema.sql:23).
Change: add nullable, backfill from `playlists.workspace_id`, insert distinct `workspace_videos`, add FK, then set not null.

3. The `video_artifacts` FK still has no executable matching target: the only `video_generations` shape shown has a 3-column PK and `kind text`, while the FK references a 4-tuple ending in `artifact_kind`.
Failure: Postgres rejects the FK because the exact referenced tuple is not unique and, if copied from the shown schema, `text` and enum are not FK-compatible.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:613), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1070), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:657).
Change: include complete executable DDL for `artifact_kind`, `slot_kind`, and `video_generations(kind artifact_kind, unique(workspace_id, video_id, generation_id, kind))` before `video_artifacts`.

**HIGH**

4. The physical sweep is not reproducible from the spec because multiple SQL fences are pseudo-signatures or partial fragments.
Failure: an implementer cannot execute “every DDL block” without guessing omitted definitions like `artifact_record_result`, `video_generations`, and `slot_kind`.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:694), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:643).
Change: split executable migration DDL from illustrative prose and make the migration block runnable end to end.

**JOB 2 — Invariants**

**BLOCKING**

5. Rule 19’s record-first order moves double-spend into permanent `busy`: `pending` has no lease, expiry, reclaim, or stale-row semantics.
Failure: writer inserts `pending`, crashes before bytes, and every future spender sees an indeterminate row forever; if callers ignore it, double-spend returns.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:752), [inventory]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/reviews/spec-blob-addressing-rules-inventory.md:184).
Change: make `pending` a leased reservation with expiry/reclaim, or keep pending out of the authoritative table and model it as a separate reservation table.

6. Derived `current` cannot be a function of the generation set while `video_artifacts` has exactly one row per `(workspace, video, slot)`.
Failure: a second recorded summary must overwrite the first slot row, so the old generation is no longer referenced, cannot be ranked, cannot be recovered, and starts looking like an orphan.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:612), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:837).
Change: key artifact records by `(workspace_id, video_id, slot, generation_id)` or introduce an append-only generation-slot table, then expose `current` as a view/query.

**HIGH**

7. Rule 14’s floor is contradicted by the later eligibility text, which reintroduces gates beyond `state = 'recorded'`.
Failure: a corrections edit can again make all generations non-current/empty because line 884 gates on corrections hash despite line 868 saying recorded is the whole serve test.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:868), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:884).
Change: separate “servable floor” from “preferred/current rank”; stale recorded generations must remain servable until state changes to non-servable.

8. Rule 13 still overclaims replica independence: `created_at default now()` is explicitly clock-derived, and local has no generation set to exchange.
Failure: two replicas importing/recording the same logical artifact can assign different timestamps and rank different winners after sync.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:837), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:846).
Change: preserve a production timestamp as data, use deterministic tie-breakers, and define sync’s local-to-cloud translation before claiming convergence.

9. Declaring rules 12/13 cloud-only makes §5.3 under-specified, not solved.
Failure: §5.3 says sync compares two artifact manifests, but the local side has no artifact manifest, no generations, and no sweeper.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:356), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1142).
Change: replace §5.3 with an explicit adapter story: how local files become cloud generations, how cloud current materializes locally, and what is copied.

**JOB 3 — Round-3 Fixes**

**BLOCKING**

10. New prose depends on `source_generation_id` and `body_collected`, but the DDL has neither column.
Failure: model drift and collected-body exclusion are impossible to enforce; readers can still serve a model for the wrong summary or a card for a collected body.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:791), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:884), [spec DDL]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:594).
Change: add those fields or remove the claims and redesign the dependent rules.

11. The “all workspaces take `id = owner_id`” fix is not genuine across the document.
Failure: line 573 still says a new user’s workspace is a random UUID, and ADR-0006 still says the slice uses an independent UUID, so implementers can recreate the round-3 new-user unreadability bug.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:556), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:573), [ADR]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/adr/0006-stable-blob-addressing.md:61).
Change: make the slice consistently say `id = owner_id` for migrated and future users, with random ids only after `Principal` becomes workspace-aware.

**HIGH**

12. The concurrency table still claims conditional manifest writes and loser retries after the design removed the mutable pointer.
Failure: a planner following the table builds a CAS/retry protocol the invariant section says no longer exists.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1495), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1536).
Change: rewrite §9 around append-only generation insertion plus deterministic current resolution.

13. The closed Q3 text regresses the overlap rule from “both ratios” to “threshold 0.8 of the dig’s own span.”
Failure: implementer using §14 reintroduces the merge misattachment that §6.1 fixed.
Evidence: [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1206), [spec]( /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1856).
Change: update Q3 to require both `overlap/dig_span >= 0.8` and `overlap/section_span >= 0.8`.

Sixth “fix moved defect”: record-first removed the no-record/no-key double-spend hole, but moved it into a `pending` row with no lifecycle and no recovery.

Verdict: NOT CONVERGED.
