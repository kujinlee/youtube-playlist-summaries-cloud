<!-- codex-review: model=gpt-5.5 -->

**BLOCKING**

1. `video_artifacts` can point a slot at a generation/blob that does not satisfy the slot.
Scenario: row `(workspace=W, video=V, slot='summary', generation_id=Gdig, blob_key='W/videos/V/Gdig/dig/120.md')` passes the proposed FK if `Gdig` exists, but resolving the current summary joins a `kind='dig'` generation with `card = null`.
Evidence: [spec §5 manifest](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:333) has unconstrained `slot`, `blob_key`, `generation_id`; [spec §5.2](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:456) defines `kind` and `card`, then only says `video_artifacts.generation_id references it`.
Change: make artifact rows carry/validate `kind`; use a composite FK `(workspace_id, video_id, generation_id, kind)`, slot-kind checks, and a blob-key check or generated key so the row cannot assert `summary` over dig bytes.

2. Playlist delete “reference counting” is racy as specified.
Scenario: delete playlist P1 counts zero surviving references for video V in workspace W; concurrently, ingest adds V to playlist P2 in W after the count but before P1’s manifest/blob deletion; P2 now references V, but the shared manifest/blobs were deleted.
Evidence: [spec §11.0 consequence 3](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:822) says “reference counting”; current playlist/video membership is independently insertable via [videos PK/FK](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0001_core_schema.sql:23) and [resolvePlaylistId upsert](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-metadata-store.ts:198); current delete is multi-step outside one storage transaction at [route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:73).
Change: delete through a single definer RPC that locks the workspace/video reference set, tombstones the playlist membership, computes refs under that lock, and emits exact blob keys to delete only after the DB commit.

**HIGH**

1. Corrections can change while a generation is in flight, making “current corrections applied before publish” false.
Scenario: worker starts summary generation with corrections C1; user updates corrections to C2 while Gemini runs; worker applies/stamps C1 and publishes the manifest, so the current generation is born stale.
Evidence: rule at [spec §5.2.2](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:438); corrections are mutable via [update_video_annotations](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:19); cloud summary handler does not read corrections at all at [summary-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:95).
Change: publish must CAS on `corrections` version/hash or `annotationsEditedAt.corrections`; if it changed, store the generation as unpublished and retry/apply the new corrections before manifest publish.

2. Serve-side paid model charging remains playlist-keyed, so workspace-level blob dedup still double-charges.
Scenario: two playlists in one workspace share video V and the same manifest/model blob; first playlist view reserves/generates model, second playlist view gets a distinct `serve_model_charge` row because `doc_key = playlist_id/video_id`, and charges again.
Evidence: [spec §11.0](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:802) claims playlist-independent blob sharing; [serve_model_charge doc_key](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0012_serve_model_charge.sql:7) is playlist/video; [reserve_serve_model](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0014_serve_owner_budget.sql:47) still builds that key.
Change: key serve-side charge/lease by `(workspace_id, video_id, model generation/source hash)` or explicitly declare model spend dedup out of scope alongside job dedup.

3. Asset deletion is not designed after assets move outside generations.
Scenario: hosted/local slide asset exists at `workspace/videos/V/assets/...jpg`; playlist delete cannot prefix-sweep by playlist anymore and manifest enumeration only covers `video_artifacts` slots, so source-of-truth slide bytes can survive explicit delete forever.
Evidence: asset path at [spec §4](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:185); manifest only maps slot/blob/generation at [spec §5](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:333); glossary says slide screenshots are source-of-truth at [CONTEXT.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/CONTEXT.md:44).
Change: add an asset manifest/table or define a locked, refcount-aware `videos/<videoId>/assets/` collection rule for explicit delete and GC.

4. The dig attachment rule can permanently strand legitimate content after a normal split.
Scenario: old section span 100-200 has a paid dig; new summary splits into 100-170 and 170-200; overlap fractions are 0.7 and 0.3, so clause 1 rejects forever even though the content is recoverable as the old section’s dig.
Evidence: threshold is “overlap ≥ 0.8 of the dig’s own span” at [spec §6.1](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:550); unattached presentation is explicitly unanswered at [spec §6.1](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:557).
Change: store source section id/title/span and support detached-but-visible recovery or explicit reattach; do not make span threshold the only path back to visibility.

**MEDIUM**

1. The future workspace RLS predicate is underspecified in the exact shape that previously failed: parse errors instead of denial.
Scenario: any legacy/malformed storage object with first segment not a UUID makes a policy like `split_part(name,'/',1)::uuid in (...)` error the query rather than deny that row.
Evidence: current storage policy avoids casts with text equality at [0007](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0007_storage_and_rpcs.sql:12); spec says RLS must change on day one at [§11.2](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:867).
Change: require regex-gated parsing or, better, authorize through a metadata table/object owner column without casting arbitrary path text.

2. GC correctness is assigned to a scheduled best-effort path without an audit invariant.
Scenario: scheduled sweep fails to list a prefix or classify a key; nothing on write/delete observes the missed candidate, so “90 days ceiling” and explicit-delete collection can silently become forever.
Evidence: scheduled sweep chosen at [spec §8](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:684); current delete already swallows blob cleanup at [route.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/app/api/playlists/[id]/route.ts:76); Supabase list/remove throw on storage errors at [supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:110).
Change: define a durable GC work table with attempts, last_error, and “delete requested but bytes remain” assertions; explicit delete should not be only a background hope.

**LOW**

1. ADR-0006 is now stale on the identity decision.
Scenario: implementer reads ADR instead of the 1100-line spec and uses `<tenantId> == auth.uid()` even though §11.2 says independent `workspaceId` on day one.
Evidence: [ADR-0006](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/adr/0006-stable-blob-addressing.md:7) still says `<tenantId>` and [ADR consequence](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/adr/0006-stable-blob-addressing.md:54) says equals `auth.uid()`; spec contradicts this at [§11.2](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-03-stable-blob-addressing-design.md:867).
Change: update ADR-0006 before merge or mark it superseded by the workspaceId revision.

Checked and confirmed: `jobs_idem_active` is playlist-keyed at [0009](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:11); `spend_ledger` is global/day-only and `quota_allowance` is tier/kind-only at [0011](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0011_cost_guardrails.sql:12); `share_tokens` remains playlist/video keyed at [0013](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0013_share_tokens.sql:6).
