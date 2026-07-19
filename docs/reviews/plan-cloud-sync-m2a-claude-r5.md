# Adversarial Plan Re-Review (Round 5) — Stage 3 Cloud Sync M2a (Claude)

Re-reviewed v5 (c1bb069) against round-4 findings, v10 spec, and REAL storage source on BOTH backends (supabase-metadata-store.ts, local-metadata-store.ts, index-store.ts, principal.ts, registry/manifest helpers). Traced setPlaylistMeta/claimVideoSlot/upsertVideo/readIndex line-by-line for publish AND hydrate directions.

## Mandate A — Round-4 closure audit
- Codex H1 (additive publish never created cloud row): CLOSED for CLOUD/publish, source-verified. ensureReceiverSlot→cloud.setPlaylistMeta upserts playlist (:73-82); cloud.readIndex returns emptyPlaylistIndex when absent (:36, no throw); claimVideoSlot appends reservation (:88-100) so upsertVideo UPDATE lands (:105-113); step-4 readIndex verify before report.created++/writeVideoBaseline (plan:2017-2019). ✓
- Codex M1 (promoted before blob): CLOSED. Blob put+verify (step2) precedes promoted set (step3), only if verified. ✓
- Claude L4 (direction-agnostic promoted): CLOSED. ✓
- Claude L5 (keep annotationsEditedAt, drop sender ordering): CLOSED — override vs sanitize consistent, no double-handling. ✓

## Mandate B — New defect exposed by the round-4 fix

### HIGH H1 — cloud→local hydrate to a fresh root throws; nothing creates the hydration-root directory
For a cloud-only playlist, dataRoot=hydrationRoot=path.join(dataRoots[0],key) — a <key> subdir never created. Additive branch → local.setPlaylistMeta → indexStore.readIndex, which on ENOENT does lstatSync(outputFolder) → throws "Output folder does not exist" (index-store.ts:70-78). Even if readIndex tolerant, writeIndex → writeFileSync(<dataRoot>/…tmp) throws ENOENT (missing parent, :83-96). AND enumerateVideoIds → local.readIndex throws BEFORE ensureReceiverSlot is even reached. Breaks the entire cloud→local hydrate direction (spec R2/Behavior #8, plan's own first integration test "hydrates an empty local replica", plan:1868). readManifest degrades silently (never mkdirs, manifest.ts:1430-1437); writeVideoBaseline's mkdir runs only AFTER copyAdditiveVideo throws. Cloud backend hides this (DB upsert + empty-index-on-absent); local FS has no such tolerance.
Residual risk: if harness seedLocalPlaylist pre-creates the <key> dir, test goes green while real fresh machines fail 100%.
Fix: mkdir -p the hydration root before the first local read (in ensureReceiverSlot for local, or runSync before enumerateVideoIds). Add integration assertion using a genuinely non-existent root.
Source: local-metadata-store.ts:13-21; index-store.ts:70-78,83-96; plan 1951,1955,1989,2017.

### LOW L1 — ensureReceiverSlot returning null loses position/serialNumber on subsequent upsert
sanitizeAdditiveVideo drops position/serialNumber; step3 re-applies only if(slot). When slot=null (row exists), sanitized upserted with undefined ordering; local upsertVideo full-replaces (index-store.ts:106-111), erasing ordering. Effectively unreachable on additive path (entered only when !base and readVideo null → readIndex inside ensureReceiverSlot can't contain id in single non-concurrent run), so not a live bug — but latent trap. Consider fallback to existing position/serial when slot null, or document null cannot occur.

## Verified clean
Presence-branch tuple direction (no transposition, no NPE); playlistMetaFor both directions resolve URL; baselineFromOneSided args match; counter semantics correct (created++ after step-4 verify); money path clean; readManifest degrades on missing root.

**Verdict: NOT CONVERGED** — 1 source-verified High (fresh-root hydrate throws, breaks a spec-required core direction; one-line fix but real). Add hydration-root mkdir + a genuinely-non-existent-root integration test.
