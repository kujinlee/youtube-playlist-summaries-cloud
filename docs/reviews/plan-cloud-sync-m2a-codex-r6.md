# Round-6 Adversarial Re-Review: Stage 3 Cloud Sync M2a

Reviewed v6 against the round-6 brief, the v10 spec, both round-5 reviews, and the real local store source (`lib/index-store.ts`, `lib/storage/local/local-metadata-store.ts`). I focused on the fresh-device cloud-to-local hydrate path, the only remaining High from round 5, plus regressions that could have been introduced by the new `mkdir -p` step.

## Round-5 Closure Audit

- **Codex H1 / Claude H1 - cloud-only hydrate reads or creates local metadata before the local root exists: CLOSED.** v6 defines `ensureHydrationRoot(dataRoot)` as `fs.mkdir(dataRoot, { recursive: true })` and calls it at the top of the per-playlist loop before constructing principals, `readManifest`, and `enumerateVideoIds` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1952`, `1990-1996`). Against the real source, that is the right boundary: `indexStore.readIndex` throws only when the directory itself is missing, but returns `{ playlistUrl: '', outputFolder, videos: [] }` when the directory exists and `playlist-index.json` is absent (`lib/index-store.ts:64-78`). After the mkdir, `enumerateVideoIds` can read an empty local index and the real cloud index; the one-sided cloud video takes the additive branch; `copyAdditiveVideo` calls `ensureReceiverSlot`; local `setPlaylistMeta` reads the empty-index sentinel and then `writeIndex` can write into the existing directory (`lib/storage/local/local-metadata-store.ts:13-20`, `lib/index-store.ts:83-96`). `claimVideoSlot`/`upsertVideo` also use the now-existing root (`lib/storage/local/local-metadata-store.ts:22-31`). The local blob put was already parent-creating; the metadata path is now unblocked. This satisfies the spec's fresh-device pull requirement (`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:246-248`, `269-273`).
- **Codex L1 - `claimVideoSlot` idempotency wording: CLOSED.** v6 now states the RPC uses `on conflict ... do nothing`, keeps the guard before claiming, and explains why a repeated claim result is not useful (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1956`). Non-gating.
- **Claude L1 - null-slot fallback loses receiver ordering: CLOSED.** v6 documents that if `ensureReceiverSlot` returns `null`, `copyAdditiveVideo` re-reads and preserves the receiver's existing `position`/`serialNumber` instead of writing sanitized `undefined` ordering (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1960`). Non-gating and effectively unreachable on the single-run additive path, but the trap is now covered.

## Fresh-Device Hydrate Trace

For a cloud-only playlist on a fresh device, `unionPlaylistKeys` includes the cloud key; `dataRoot` resolves to `hydrationRoot(deps.dataRoots, key)`; v6 immediately creates that root (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1983-1996`). `readManifest` still degrades to an empty manifest if absent or corrupt (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1430-1437`). Local `readIndex` now sees an existing directory with no index file and returns the empty sentinel, so `enumerateVideoIds` can union the cloud video ids. In the additive branch, the receiver tuple for cloud-to-local is `[cloudP, deps.cloudBlob, deps.local, localP, deps.localBlob]`, so the local metadata and local blob stores are passed in the correct receiver positions (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:2011-2019`). `ensureReceiverSlot` writes the real playlist URL/title before claiming the local slot, `copyAdditiveVideo` writes/verifies the MD blob before advertising promoted status, verifies the receiver row exists, and only then does the caller increment `created` and write the baseline (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1956-1963`, `2019-2022`). The round-5 failure no longer occurs end to end.

## Regression Check

- Unconditional `mkdir -p` does not harm local-only or already-two-sided playlists: if `dataRoot` already exists, recursive mkdir is a no-op before the same local reads that were already happening.
- Creating a fresh root does not poison later metadata with the sentinel `playlistUrl: ''`: `setPlaylistMeta` overwrites it with `playlistMetaFor(...)` before the receiver row is claimed, and the cloud-only metadata source comes from `listPlaylists` (`docs/superpowers/plans/2026-07-17-stage3-cloud-sync-m2a.md:1955-1956`, `2016-2019`).
- I found no remaining local read on the fresh hydrate root before `ensureHydrationRoot`. `discoverLocalPlaylists` scans only existing roots and skips absent/non-indexed directories; the cloud-only key is introduced from `cloudSummaries`, then the root is created before local `readIndex`.
- No new T12 arg-order/type/NPE defect found. The one-sided presence branch continues before any two-sided dereference, and the receiver blob store remains explicitly threaded in both additive directions.

## New Findings

None.

## Implementability Judgment

The remaining round-5 High is genuinely closed against the real local filesystem store. The fix is narrow, has the required fresh-root integration guard (T14 row 17), and does not introduce a new Blocking/High/Medium/Low issue. The plan is ready for a fresh engineer to implement task-by-task.

**CONVERGED**
