<!-- codex-review: model=gpt-5.5 -->

**Blocking**

1. Row 21 is not a safe contract: it knowingly leaves a permanent split.

Evidence: the plan’s own goal is same `serialNumber` on both replicas so both derive the same `base` ([docs/superpowers/plans/2026-07-31-serial-coherence-sync.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:3)). Row 21 says when cloud target serial is occupied, cloud takes a fresh serial while local remains untouched and the two disagree ([same plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:91)). That violates the stated invariant and guarantees future key divergence for `models/<base>.json` and `dig/<base>/...` ([model-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:31), [dig-blob-key.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/dig-blob-key.ts:13)).

Change row 21 to one of these, but choose one:
`Target taken on cloud by unrelated video | local=3, cloud=7, cloud video X already owns 3 | allocate fresh serial K for BOTH this video’s local and cloud rows, and move BOTH sides’ base-keyed blobs to K; abort if either side cannot move all paid artifacts.`
If local must never be renamed, then the only coherent expectation is:
`abort and report serial collision; do not advance baseline; do not write either row.`
“Cloud gets K, local stays 3” should not be a passing test.

2. Missing behavior: serial collision can require both sides to renumber.

Evidence: row 20 only covers “cloud moves to local” ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:90)); row 21 covers cloud target taken but still forbids local rename ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:91)). There is no row for this graph:

`A: local=3, cloud=7`
`B: local=7, cloud=3`

No single “cloud renumbers” move can make both videos coherent without either temporary slots or a two-video transaction plan. `base` is a single path component used by dig keys ([dig-blob-key.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/dig-blob-key.ts:17)) and model keys ([model-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/model-store.ts:31)), so this is a real artifact relocation problem, not only metadata.

Add row:
`Serial swap / cycle | two or more videos occupy each other’s target serials across replicas | reconcile as a cycle using fresh temporary/final serials, or abort the whole cycle without row/blob changes or baseline advancement. Per-video partial success is forbidden.`

**High**

3. Row 26 is underspecified and its first alternative is wrong for non-atomic blob moves.

Evidence: row 26 says either “blobs move last, after row update” or “move verified before row advances” ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:96)). Those are different failure models. If metadata is updated before blobs, readers derive the new base while blobs still live under the old base; any mid-move failure strands the row pointing forward. If blobs move first and metadata fails, row points old while blobs are at new. Neither is healed by baseline alone unless the next run has an explicit recovery state.

Supabase `move()` is documented in the adapter comment as copy+delete and non-atomic ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:75)); local `fs.renameSync` is one-object atomic but not multi-object atomic ([local-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/local/local-blob-store.ts:52)). So row 26 must choose a recoverable protocol.

Change row 26 to:
`Metadata/blob ordering | serial/base changes | write an explicit pending-rename marker or compute rename intent from live old/new serials; copy/promote all destination blobs without deleting sources; verify destination bytes; update metadata; then delete old blobs best-effort. Any failure before metadata leaves old blobs intact and baseline unadvanced; any failure after metadata is retry-cleanup, not data loss.`
If you insist on true rename/delete-before-metadata, add rollback rows. Without rollback, row 24 is not sufficient.

4. Row 24 “abort without advancing baseline” is insufficient after destructive moves.

Evidence: row 24 allows “rename N of M blobs, then failure” and says re-run heals ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:94)). But current storage has no atomic multi-key transaction. Supabase move is non-atomic ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:78)); list/delete are also batch operations over collected paths ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:95)). If row still points old and old summary was moved away, a re-run sees `summaryMd` advertised but body missing/unreadable and may abort, not heal.

Change row 24 to distinguish:
`Failure before deleting any source | abort, baseline not advanced, sources still serve current row.`
`Failure after some source deletion | must rollback moved blobs or leave a durable rename journal that re-run completes before normal sync. Baseline alone is not a recovery mechanism.`

5. Missing behavior: corrections-unresolved override can skip serial reconciliation entirely.

Evidence: current run skips Class A when unresolved corrections conflict and both sides have MD bodies, writes a special baseline, then `continue`s ([sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:608)). Serial reconciliation is planned under A3 “two-sided path” ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:85)), but there is no row saying whether it runs before or after this guard. If implemented inside the skipped Class A path, serial divergence persists indefinitely.

Add row:
`Corrections unresolved + serials differ | both sides have MD and corrections conflict causes Class A skip | serial/base reconciliation still runs only if it can preserve both MD bodies and paid artifacts; otherwise abort/report. It must not be hidden behind the Class A copy decision.`

6. Missing behavior: one-sided local→cloud and cloud→local are materially different.

Evidence: one-sided videos use `presentIsLocal` to choose direction ([sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:524)); `copyAdditiveVideo` writes the sender’s `summaryMd` key but currently receives a receiver-allocated serial from `ensureReceiverSlot` ([sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:200), [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:216)). Row 9 says adopt when free, but does not split direction. Cloud-only hydrate is local-writing, and local filenames are user-visible per design ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:24)); local-only upload is cloud-writing and cloud may already hold derived artifacts for another video.

Add rows:
`Local-only additive | sender local has serial S and summaryMd base S | cloud claims S if free; if occupied, either abort/report or allocate K and also rewrite cloud row/key to K coherently; never write row serial K with summaryMd S.`
`Cloud-only hydrate | sender cloud has serial S and summaryMd base S | local claims S if free; if local S occupied, define whether local may renumber the cloud-only incoming video’s file or must abort. Do not silently choose receiver-local serial while copying sender key.`

**Medium**

7. The `rename()` union is not exhaustive for a paid-content reconcile.

Evidence: proposed union has only ok, source-absent, destination-exists, failed ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:43)). Existing `BlobRead` distinguishes absent from unreadable because irreversible/billable decisions need that ([blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:16)). Rename preflight needs the same distinction for both source and destination. “Destination existence probe unreadable” is not the same as “destination exists” or “backend failure during move”; it is a fail-closed precondition failure.

Change union to either:
`{ ok:false; reason:'source-unreadable' }`
`{ ok:false; reason:'destination-unreadable' }`
or keep one `failed` but require `phase: 'read-source' | 'read-destination' | 'move' | 'verify'` so callers cannot collapse it into absence.

8. Supabase `move()` cannot be the classifier; adapter must probe with `tryGet`, and row 3 needs a race contract.

Evidence: Supabase `exists()` uses `get()` ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:59)), while `get()` swallows all download failures into null ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:27)). `tryGet()` has the honest absent/unreadable split ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:44)). `promote()` currently treats destination presence as success ([supabase-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-blob-store.ts:79)), the opposite of row 3.

Add to rows 3-5:
`Supabase rename classifies by tryGet(source) and tryGet(destination), not exists()/get()/promote(). If destination appears between preflight and move, return destination-exists or failed-with-verify, and prove source remains or destination bytes equal intended source before deleting anything.`

9. Fail-closed on destination-exists is right for unknown content, but deadlocks legitimate idempotent retries unless byte identity is specified.

Evidence: row 3 says destination occupied always aborts and both untouched ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:55)); row 27 expects idempotent rerun no-op ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:97)). A previous partial run may have successfully copied/moved destination but failed before source cleanup or metadata. On rerun, strict destination-exists aborts forever even when destination bytes match source.

Add row:
`Destination occupied with identical bytes | retry after partial success; source and destination both exist and hashes match | treat as already-copied for that blob, continue, delete old source only after metadata is coherent.`
Keep row 3 for divergent bytes:
`Destination occupied with different bytes | abort/report paid-content collision; neither blob overwritten.`

10. Row 23 overreaches by asserting nothing remains under old base, including paid artifacts that may be intentionally retained until metadata is safe.

Evidence: row 23 says all derived blobs move and post-condition asserts nothing remains under old base ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:93)). But a robust protocol likely keeps source blobs until after row update and verification. Also dig missing is explicitly “swallow + report” because dig is out of M2a sync scope ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:106)).

Change row 23 to:
`all known existing blobs are present at new base before metadata advances; old-base cleanup is best-effort after metadata verification. Final steady-state should have no old-base blobs, but cleanup failure must report and must not make row/base incoherent.`

**Low**

11. `playlistIndex` rows conflict with `ensureReceiverSlot` shape unless the slot API stops returning/using position for additive sync.

Evidence: row 17 says carry sender `playlistIndex` ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:82)), but current `copyAdditiveVideo` writes `slot.position + 1` ([sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:216)). `claim_video_slot` also computes position and serial together ([0007](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0007_storage_and_rpcs.sql:30)).

Add a small row:
`Slot position is storage ordering only | additive sync with sender playlistIndex present/absent | claim may allocate DB position, but sync record payload must preserve sender playlistIndex or absence; tests assert slot.position is not used for playlistIndex.`

12. Same-key `rename()` is only safe if normalized logical keys are compared after validation.

Evidence: row 7 says `from === to` returns ok/no I/O ([plan](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/plans/2026-07-31-serial-coherence-sync.md:59)). `assertLogicalKey` only rejects leading `/`, `..` segments, and NUL ([blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/blob-store.ts:57)); local paths pass through `path.join` ([local-blob-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/local/local-blob-store.ts:12)). Add a contract that same-key is checked after both keys pass validation and after canonical logical normalization, or forbid ambiguous forms like `a/./b`.

Overall: the table has the right instinct on paid-artifact safety, but rows 21, 24, and 26 currently encode states that either violate the core invariant or rely on recovery that the storage seam does not provide. The biggest fix is to replace “local always untouched” with a coherent collision policy: either both sides converge, including both-side renumber when necessary, or the video/cycle aborts with no baseline advancement.
