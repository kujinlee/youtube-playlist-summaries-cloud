<!-- codex-review: model=gpt-5.5 -->

**Blocking**
1. CAS predicate is not equivalent to the system’s current serial semantics.

Spec: [docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:206) proposes:

```sql
v.data->'serialNumber' = to_jsonb(p_expected_serial)
```

But current DB code treats JSON number `7` and JSON string `"7"` as the same serial because it reads through text then casts:

- [reserve_video_slot](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:86): `(v.data->>'serialNumber')::int`
- [claim_video_slot](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0023_claim_video_slot_desired_serial.sql:57): `(v.data->>'serialNumber')::int`
- collision check also casts: [0023](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0023_claim_video_slot_desired_serial.sql:83)

Concrete failure: row has `data.serialNumber = "7"` as JSON string. That can enter through direct Supabase `.update({ data })` / `.upsertVideo()` paths, which do not validate zod on write: [supabase-metadata-store.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/supabase/supabase-metadata-store.ts:115). `reserveVideoSlot` returns numeric `7`; proposed CAS compares JSON string `"7"` to JSON number `7`, returns false, and rejects a legitimate write forever unless the recovery path normalizes the row. The spec calls jsonb equality “total”; it is total, but not correct against the repo’s own serial access semantics.

This must be resolved by either enforcing/migrating numeric JSON serials before the CAS, or by making the predicate match existing semantics while still handling malformed rows deliberately.

2. The recovery loop can publish “promoted” before the new blob is promoted because key-scoped monotonic status interacts badly with re-addressing.

Current `persist_summary` preserves promoted on a committed write when the key is unchanged: [0021](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:142). A3 relocation writes the new key as already promoted: [reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:293). The spec’s recovery sequence does `persist committed` before `promote`: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:266).

Concrete failure:

1. Worker generated new MD for old base `007_alpha.md`.
2. Sync relocates row to `003_alpha.md` and sets `artifacts.summaryMd.status = promoted`.
3. Worker CAS fails, re-addresses to `003_alpha.md`, stages new content.
4. Worker calls `persistSummary(..., 'committed')`.
5. Existing row key is already `003_alpha.md` and status is `promoted`, so SQL preserves `promoted` before the staged blob is promoted.
6. If `promote(ref)` fails, row metadata from the new summary can be committed while the durable blob at `003_alpha.md` is still the relocated old content.

That violates the stage → committed → promote → promoted ordering that [summary-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:172) currently relies on.

**High**
3. The spec misses the dig worker, which has the same stale-base exposure but does not go through `persist_summary`.

The dig handler reads the current summary key, derives `base`, then spends on transcript/dig before writing under that base:

- read key/base: [dig-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/dig-handler.ts:51)
- billable generation: [dig-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/dig-handler.ts:100)
- write blob under pinned base: [dig-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/dig-handler.ts:119), [write-dig-section-blob.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/dig/cloud/write-dig-section-blob.ts:45)

The current in-flight probe explicitly includes dig jobs because of this: [in-flight-job.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/in-flight-job.ts:69), with an integration test at [in-flight-job-probe.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/in-flight-job-probe.test.ts:129).

Concrete failure: A3 probes and sees no job, then enters the copy phase. A dig job is enqueued/claimed during that copy window, reads old base `007_alpha`, spends Gemini, then A3 relocates row to `003_alpha` and deletes old-base blobs. The dig worker writes `dig/007_alpha/<section>.rV.md`. The row now derives `003_alpha`, so the paid dig is unreachable. `persist_summary` CAS never runs, so this spec does not close the residual window it claims to close.

4. Section 5’s two-outcome taxonomy is itself racy.

Spec says after zero affected rows, re-probe row existence and raise “row absent” vs “serial differs”: [spec](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/docs/superpowers/specs/2026-08-04-cas-fence-persist-summary-design.md:241).

That second probe observes a later state than the failed `UPDATE`.

Concrete failure A: CAS update affects zero rows because row existed with serial `3` while worker expected `7`. Before the re-probe, playlist deletion cascades the video row. Re-probe says absent, caller treats it as fatal/non-retryable, but the actual cause was recoverable address movement.

Concrete failure B: CAS update affects zero rows because row was absent. Before re-probe, another worker/sync recreates or claims the row with serial `8`. Re-probe says “serial differs,” caller retries and may write into a row that did not exist at the time of the guarded update.

If the caller behavior depends on this distinction, the distinction has to be made under a lock or inside one statement whose result reflects a single snapshot. The proposed post-failure probe does not prove why the update failed.

**Medium**
5. Required arity change breaks more than the spec’s “one production caller” framing accounts for.

Production wrapper/caller is narrow: [worker-persistence.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/storage/worker-persistence.ts:18), [summary-handler.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/job-queue/summary-handler.ts:177). But tests and helpers call the RPC directly:

- [worker-persistence-rpcs.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/worker-persistence-rpcs.test.ts:59) and many later direct calls
- [helpers/cloud.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/helpers/cloud.ts:118)
- [worker-storage-bundle.test.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/integration/worker-storage-bundle.test.ts:87)

That is not a design blocker, but the spec’s migration plan should explicitly require updating direct RPC fixtures and helper APIs. Otherwise the test suite will fail for arity reasons before it verifies the behavioral CAS.

**Not Findings**
I do not see a real deadlock from re-calling `reserveVideoSlot` in the recovery loop. `reserve_video_slot` takes `playlists FOR UPDATE`: [0009](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:84). Sync’s ordinary metadata writes use `merge_video_data` without `FOR UPDATE`: [0021](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79). `runSync` is also not one giant DB transaction; it calls store methods separately: [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:547). I would still test contention, but the lock-ordering deadlock concern is not proven by this code.
