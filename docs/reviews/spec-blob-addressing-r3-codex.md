<!-- codex-review: model=gpt-5.5 -->

**JOB A Findings**

**BLOCKING [10]**: UID-seeding fixes migrated users but breaks new users because `Principal.id` is still `auth.uid()`, while new workspaces are random ids.
Scenario: a post-migration anonymous/registered user writes `userId/playlistKey/key`; `workspace_readable(userId)` finds no workspace with `id = userId`, so the user cannot read their own blobs, while the `service_role` worker can still write them.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:491`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:530`, `lib/storage/resolve.ts:93`, `lib/storage/supabase/supabase-blob-store.ts:15`.
Change: either seed every one-per-user workspace with `id = owner_id` until `Principal` construction is workspace-aware, or make every cloud `Principal` lookup carry `workspace_id`, including worker paths.

**BLOCKING [13]**: Derived `current` does not define sync convergence when replicas have different generation sets.
Scenario: local has eligible generation A and cloud has eligible generation B; each derives a different current and neither is wrong, while §5.3 says sync “produces one” without copying bytes or reconciling generation rows.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:744`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1012`, `lib/cloud-sync/sync-run.ts:367`.
Change: define sync as generation-set reconciliation, including blob transfer and recorded-fact merge, or add an explicit synced/pinned selection state that replicas agree on.

**HIGH [13]**: “Newest eligible wins” makes creation time a silent quality and spend policy.
Scenario: a cheaper/free correction re-render or lower-quality regeneration created later supersedes a better paid generation with no user intent, and a paid generation can lose immediately because it is older.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:744`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:766`.
Change: add an explicit selection rank, user pin, or “supersedes_generation_id” rule instead of ordering only by `(created_at, generation_id)`.

**HIGH [14]**: Record-time readability cannot detect later blob disappearance.
Scenario: a bucket lifecycle rule, manual storage delete, or failed migration cleanup removes `summary.md` after `record_artifact`; resolve still selects it from recorded facts, and the user sees permanent repair-needed/busy rather than an invalidated generation.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:754`, `lib/html-doc/serve-summary-core.ts:66`.
Change: keep resolve blob-free, but add a background integrity probe that marks `body_lost/body_collected` and exposes repair state.

**BLOCKING [15,18]**: “Assets are sources, explicit delete only” is not reachable for videos that leave playlists without being deleted.
Scenario: `reconcile_membership` archives removed videos instead of deleting rows; with `pruneSectionAssets` removed and no age sweep, a heavy user’s slide captures accumulate forever unless they delete the whole playlist.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1300`, `supabase/migrations/0007_storage_and_rpcs.sql:52`, `supabase/migrations/0007_storage_and_rpcs.sql:60`, `lib/dig/slides.ts:185`.
Change: add an asset lifecycle rooted in video membership/removal, such as source-asset rows plus explicit video delete, or a grace-period sweep for assets of videos no longer present anywhere in the workspace.

**HIGH [17]**: The key classifier is underspecified for the current nine key families.
Scenario: the sweeper sees `htmls/...`, `pdfs/...`, `<base>-dig-deeper.md`, `_staging/<uuid>/<finalKey>`, and assets, but §4 only defines four new shapes, so paid/free/source/render classification still requires guessing.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:151`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:181`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1320`.
Change: specify a total `classify_blob_key()` inventory for all current and migrated shapes, including staging and legacy keys, and make unknown shapes fail closed.

**HIGH [19]**: The spend boundary still depends on callers not reaching paid generation through old nullable reads.
Scenario: `readModelEnvelope()` collapses absent, malformed, schema-invalid, and unreadable to `null`; any path that calls it before the explicit `tryGet` guard can still turn a transient read fault into a paid model generation.
Evidence: `lib/html-doc/model-store.ts:54`, `lib/html-doc/model-store.ts:60`, `lib/html-doc/serve-doc.ts:56`, `lib/html-doc/serve-doc.ts:70`.
Change: replace nullable model reads on spend paths with a typed read result, and make the two-read rule an API boundary rather than a caller convention.

**MEDIUM [20]**: Bidirectional-only attachment forbids recoverable UI with provenance and strands paid digs on ordinary section edits.
Scenario: a section split leaves a useful paid dig detached forever even though the UI could label it as “from an earlier section span” instead of silently misrepresenting it.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1032`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:1042`.
Change: keep strict auto-attach, but add a separate “provenance attach/suggested attach” state rather than binary attached/detached.

**JOB B Findings**

**BLOCKING**: `workspace_videos` migration is missing the populated-table backfill before adding the FK from existing `videos`.
Scenario: any existing DB has `videos` rows keyed by `(playlist_id, video_id)`; adding `(workspace_id, video_id) references workspace_videos` fails unless distinct workspace-video rows are inserted first.
Evidence: `supabase/migrations/0001_core_schema.sql:23`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:460`, `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:468`.
Change: make this a phased migration: add nullable `videos.workspace_id`, backfill it, insert distinct `workspace_videos`, then add the FK and `not null`.

**HIGH**: The asset physical key and markdown reference diverge under the new path template.
Scenario: the spec stores assets at `<workspaceId>/videos/<videoId>/assets/...`, but generated markdown embeds `assets/<videoId>/<file>` and the renderer resolves relative to the document directory, so migrated cloud/local renders look in the wrong place unless a translation layer is specified.
Evidence: `docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:185`, `lib/dig/slides.ts:185`, `lib/dig/slides.ts:190`, `lib/html-doc/render-dig-deeper.ts:104`.
Change: keep embedded asset refs as logical refs and define a resolver from logical ref to blob key, or keep the stored key layout aligned with the markdown-relative layout.

**Verdict: NOT CONVERGED**. New Blocking and High findings remain.
