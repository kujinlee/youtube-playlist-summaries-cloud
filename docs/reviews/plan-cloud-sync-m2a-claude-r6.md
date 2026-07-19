# Adversarial Plan Re-Review (Round 6) — Stage 3 Cloud Sync M2a (Claude)

Re-reviewed v6 (95bf22a) against round-5 findings, v10 spec, and REAL local store source (index-store.ts, local-metadata-store.ts). Traced the fresh-device cloud→local hydrate end to end.

## Mandate A — Round-5 closure audit
**Fresh-device hydrate High (both reviewers): CLOSED — source-verified end to end.**
v6 adds ensureHydrationRoot(dataRoot)=fs.mkdir(dataRoot,{recursive:true}), called at the top of the per-playlist loop before readManifest/enumerateVideoIds (plan:1952,1991). Trace for cloud-only playlist, fresh device:
1. dataRoot=hydrationRoot=path.join(dataRoots[0],key) — absent.
2. ensureHydrationRoot mkdir -p creates it (dir exists, index file absent).
3. enumerateVideoIds→local.readIndex: readFileSync ENOENT → lstatSync(dataRoot) now SUCCEEDS → empty-index sentinel {playlistUrl:'',outputFolder,videos:[]} (index-store.ts:72-77). No throw. (Pre-fix lstatSync threw.)
4. Additive→copyAdditiveVideo→ensureReceiverSlot→local.setPlaylistMeta→readIndex(sentinel), then writeIndex into existing dir SUCCEEDS (local-metadata-store.ts:13-20, index-store.ts:83-96). (Pre-fix writeIndex threw ENOENT.)
5. claimVideoSlot→upsertVideo into existing dir. Blob put creates own parents; step-4 readIndex verify finds video.id; writeVideoBaseline writes manifest.
Every local read/write on dataRoot now preceded by ensureHydrationRoot (first statement in loop body). T14 row 17 requires a genuinely non-existent root (forbids masking harness dir). CLOSED.
Round-5 Lows: null-slot fallback (plan:1960) + claimVideoSlot wording (plan:1956) both CLOSED, non-gating.

## Mandate B — Defects introduced by the round-5 fix
- Unconditional mkdir on existing root (local-only/both-sided): fs.mkdir recursive is a documented no-op. Harmless. ✓
- Empty-index sentinel playlistUrl:'' consumed before setPlaylistMeta: only readManifest (different file, degrades) + enumerateVideoIds (reads idx.videos=[]) run between; readVideo→null; '' never consumed; setPlaylistMeta overwrites with real URL from playlistMetaFor(cloudSummaries). ✓
- Any local read before ensureHydrationRoot: discoverLocalPlaylists runs before loop but only readdir's existing roots (catch continue on missing; resolveRootShape null when index absent); never touches the not-yet-created hydration root. Inside loop, ensureHydrationRoot is first. ✓
- Empty hydration dir left on partial hydrate: dir with no index → next-run discoverLocalPlaylists resolveRootShape returns null, skips → treated cloud-only, re-hydrated. Self-healing. ✓
- Arg-order/NPE/money: presence tuple direction, blob-before-promoted, receiver blob threading unchanged from v5's verified-clean state; only mkdir line + null-slot fallback added. Clean. ✓

## New findings
None (Blocking/High/Medium/Low).

## Verdict
The one High both round-5 reviewers agreed on is genuinely fixed — verified against real index-store.ts sentinel/lstatSync + local-metadata-store.ts setPlaylistMeta, traced through the complete fresh-device hydrate with no throw. No new defect. Core (reconcile/migration/auth/companion/manifest) clean for multiple rounds; additive-create/hydrate covered both directions + fresh-root with a pinned regression (T14 row 17). Blocking 4→0→0→0→0→0; High 3→5→2→1→1→0. Ready for a fresh engineer to implement task-by-task, no task-blocking placeholders.

**CONVERGED**
