<!-- codex-review: model=gpt-5.5 -->

**Verdict: NOT CONVERGED.** There are new Blocking and High defects.

**BLOCKING**

1. `video_artifacts.kind` still permits slots to assert over the wrong artifact family, just in a new way: every non-`dig:%` slot is forced to `summary`, including `model`, `digDeeper`, `pdf:*`, and `slide:*`.
Scenario: publishing slot `model` either fails if `kind='model'`, or lies by storing `kind='summary'` and referencing a summary generation/card for model bytes.
Evidence: [spec lines 400-416](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:400), slot vocabulary at [lines 80](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:80), generation `kind` only `summary | dig` at [lines 631-636](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:631).
Change: define a slot-kind matrix for every slot family, separate artifact kind from generation kind where needed, and make blob key shape generated or checked per family.

2. The workspace migration as written fails on existing data.
Scenario: production already has `playlists` rows; `alter table playlists add column workspace_id uuid not null references workspaces(id)` has no default/backfill, so the migration aborts before any app code lands.
Evidence: existing `playlists` table has no workspace column at [0001 lines 10-19](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0001_core_schema.sql:10); proposed direct `not null` add at [spec line 354](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:354).
Change: two-phase migration: create/backfill one workspace per existing profile, add nullable column, update all playlists, then set `not null`; add `unique(owner_id)` if one workspace per user is a rule.

3. The design still has no workspace-scoped video entity, so one shared blob can be described by multiple per-playlist video rows.
Scenario: P1 and P2 in one workspace both contain V; P1 has corrections and publishes the shared body with them applied, while P2’s `videos.data.corrections` remains null and now describes the same body incorrectly.
Evidence: `videos` is keyed per playlist at [0001 lines 23-32](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0001_core_schema.sql:23); artifact manifest is keyed `(workspace_id, video_id, slot)` at [spec lines 400-414](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:400); corrections update is playlist-row scoped at [0021 lines 48-53](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:48).
Change: add `workspace_videos(workspace_id, video_id)` as the parent of generations/artifacts and move shared body-affecting fields there, or restrict dedup to cases where per-playlist fields cannot affect the blob.

**HIGH**

1. The transactional unreference fix says “lock the reference set” but does not specify a lock that excludes concurrent ingest.
Scenario: delete P1 computes no surviving V rows while ingest inserts V into P2; unless both paths take the same workspace/video or workspace-playlist lock, the manifest can still be removed under P2.
Evidence: proposed rule at [spec lines 1117-1128](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1117); ingest today locks only one playlist row at [0009 lines 79-96](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:79).
Change: specify the exact shared lock, e.g. advisory lock `(workspace_id, video_id)` in both ingest and delete, or lock all workspace playlist rows before either path mutates `videos`.

2. Re-keying `serve_model_charge.doc_key` is not enough; the reserve RPC still verifies readiness from the old playlist video JSON.
Scenario: after summary authority moves to `video_artifacts`, `reserve_serve_model` still checks `videos.data.artifacts.summaryMd.status`, sees no promoted JSON, and returns `denied` for every model generation.
Evidence: current reserve predicate at [0020 lines 204-213](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0020_reservation_release.sql:204); spec only says re-key `doc_key` at [lines 1135-1151](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1135).
Change: rewrite the full reserve/settle protocol around SlotRead/artifact manifest resolution, not only `doc_key`.

3. `SlotRead` fixes manifest unreadability, but readers still need blob-level `tryGet` after a present slot.
Scenario: manifest says model exists, but the blob read is a transient 5xx; treating that like absence regenerates and charges again, the exact existing 6¢→12¢ defect.
Evidence: `BlobStore.tryGet` requirement at [blob-store lines 46-56](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:46); current money guard uses it at [serve-doc lines 59-71](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/serve-doc.ts:59); `SlotRead` only covers manifest rows at [spec lines 451-468](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:451).
Change: require `SlotRead` plus `BlobRead` on every billable/source-of-truth serve path; only manifest-absent and blob-provably-absent may drive regeneration where regeneration is allowed.

4. Card completeness is stated as a rule but contradicted by the schema.
Scenario: first cloud generation writes a nullable or partial `card`; sync tiebreak sees `mdGeneratedAt = null` and deterministically prefers older local content.
Evidence: proposed `card jsonb` is nullable at [spec lines 631-636](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:631); rule says not-null later at [lines 677-680](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:677); current cloud worker omits `mdGeneratedAt`/`mdCorrectionsHash` at [summary-handler lines 149-164](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:149); recency null behavior at [reconcile-class-a lines 8-10](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-class-a.ts:8).
Change: make summary generation card columns typed and `not null` individually, with `card is null` allowed only for non-summary kinds via a check.

5. Corrections CAS and “loser retries” are still not a complete publish protocol.
Scenario: worker generates with C1, user saves C2, publish CAS fails, job is marked terminal; because completed jobs are dedup roots, nothing republishes or reapplies C2.
Evidence: CAS rule at [spec lines 606-615](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:606); retry wording at [lines 487-496](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:487); completed jobs are in the idempotency index at [0009 lines 10-13](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:10).
Change: define publish CAS failure as a non-terminal job outcome with a concrete requeue/republish path, or a separate pending-publication table swept by a worker.

6. Asset re-keying omits migration and compatibility for old `sectionId-start-end.jpg` assets.
Scenario: existing slide bytes remain under `assets/<videoId>/<sectionId>-<start>-<end>.jpg`; new readers ask for `assets/<videoId>/<start>-<end>.jpg`, so old paid/source assets become invisible.
Evidence: current writer includes sectionId at [slides lines 170-188](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/slides.ts:170); spec drops sectionId at [spec lines 951-953](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:951); source-of-truth classification at [CONTEXT line 44](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/CONTEXT.md:44).
Change: add an asset migration or dual-read fallback until rewritten; disable old prefix pruning during the transition.

**MEDIUM**

1. The predicate decision is still internally inconsistent in two places.
Scenario: an implementer reading §2 or §11.0 uses `workspaceId == auth.uid()` despite §5.0 requiring independent UUIDs.
Evidence: stale text at [spec line 77](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:77) and [line 1079](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1079); corrected rule at [lines 345-377](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:345).
Change: replace all `auth.uid()` value claims with “one independent workspace UUID per user.”

2. `handle_new_user()` provisioning is under-specified for the existing `set search_path = ''` trigger.
Scenario: the migration adds `insert into workspaces ...` unqualified inside `handle_new_user`; with empty search path it errors and breaks signup.
Evidence: current trigger qualifies `public.profiles` under empty search path at [0003 lines 2-8](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0003_provisioning.sql:2); spec says “two-line addition” but does not show schema qualification at [spec lines 357-359](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:357).
Change: specify `insert into public.workspaces ...`, plus signup regression tests for registered and anonymous users.

**Round-1 Fix Verification**

Not genuinely fixed or incomplete:

- B1: fixed incompletely. Carry-forward judgments closes regeneration if the writer gets prior judgments, but direct row edits still make the current body/frontmatter disagree until a rewrite/regeneration. First generation is fine.
- B2: fixed incompletely. Anonymous users are covered by the existing trigger shape, but existing users/playlists need a backfill and the `not null` migration currently fails.
- B3: reworded but inconsistent text survives at §2 and §11.0.
- Codex B1: not fixed. The check only handles `dig:%` vs summary and fails every other defined slot.
- Codex B2: fixed incompletely. The RPC shape is right, but the actual lock that excludes concurrent ingest is unspecified.
- H1: fixed incompletely. `SlotRead` is necessary, but blob-level `tryGet` remains required after a present slot.
- H2: not fixed. The schema still has nullable `card jsonb`; producer completeness remains a convention.
- H5: fixed incompletely. Re-keying is named, but the reserve predicate and 0020 protocol are not re-derived against the manifest.
- H6: fixed incompletely. New key shape is plausible and timestamp collisions are acceptable dedup, but old-key migration/dual-read is missing.
- H7: fixed incompletely. Lifecycle is stated, but schema/status/on-delete behavior is not specified.
- Codex H1 and M4: fixed incompletely. CAS and re-read/republish are named, but no terminal job/requeue protocol exists.

Actually fixed: B5 survives a crash after DB commit because manifest rows are unreferenced transactionally and the sweeper’s no-manifest root set can later collect the bytes. §6.1/§6.2’s both-direction threshold, detached state, and persisted spans are genuinely fixed.
