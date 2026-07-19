# Whole-branch re-review (ROUND 5) — Claude, adversarial

Branch `feat/stage3-cloud-sync`, HEAD `66fe6e5`. Scope: shipped state at HEAD.
Trail: R1 `32a164c` → R2 `1f54c60` → R3 `3bc8cc7` (B1) → R4 `66fe6e5` (H1/H2/H3).

---

## Part A — verdicts on the round-4 fixes

### A1. H1 — `decideCompanion` tri-state / `readSenderModel` — **INCOMPLETE**

The mechanical change is present and correct as written: `companion.ts:34` returns `{kind:'noop'}`
for `unknown`, `sync-run.ts:392-396` maps a null envelope to `none` only when
`sender.blob.provesAbsence`, and `sync-run.ts:378` returns `shareNeedsOwnerServe: false` on noop.
The specific money bug R4 targeted (a transient cloud 5xx deleting the local model) is genuinely
closed, and the integration test at `tests/integration/cloud-sync/e2e.int.test.ts:665-694` asserts
it across two runs.

But the two questions the lead asked both come back negative, and they share one cause: **the fix
reads the wrong side.** The destructive question is "is the RECEIVER's model stale?" — which is
answerable exactly and reliably from the receiver's own envelope plus `winnerMdHash`. The fix
instead keeps deciding from the SENDER's readability, which answers a different question.

**(a) The `noop` inconsistency is real, and the stated safety net does not exist.**

`companion.ts:26-28` justifies noop with: *"the serve path's sourceSections drift guard
(lib/html-doc/read-model.ts) rejects a mismatched one for free."* That is false for the case that
matters. The guard is `sameTitles` (`read-model.ts:12-18`) — it compares **section titles only**.
`sourceMdHash` is read by **nothing** except `decideCompanion` itself (verified: the only
non-test hits are the writers `generate.ts:59` / `serve-doc.ts:110` and the schema). So a
prose-only MD change — which is precisely the recency-tiebreak case the branch itself calls out in
`sync-run.ts:337-341` — leaves `sourceSections` identical, `sameTitles` returns true, and the stale
model is treated as current.

The model is not layout metadata. `MagazineModelSchema` (`lib/html-doc/types.ts`) is
`sections[].{lead, bullets[].{label,text}}` — Gemini-rewritten **prose**, rendered verbatim at
`render.ts:84-99` and `render-dig-deeper.ts:319`.

Reachability is not exotic — **`noop` is now the default outcome of the common cloud→local
transfer.** `unknown` requires a null from a `provesAbsence === false` backend, i.e. the Supabase
sender. A cloud model blob exists only if that video was previously served through
`serve-doc.ts:103`; a cloud video that has never been HTML-served has none. So a *genuine* 404
produces `unknown` → noop on essentially every `copyToLocal`.

Trace (input → wrong outcome):
1. Video V in both replicas; cloud MD wins on recency; headings unchanged, prose changed.
2. Local holds `models/<base>.json` with `sourceMdHash = H(old local body)`; cloud holds no model.
3. `transferClassA` overwrites the local body and clears `summaryHtml` (`sync-run.ts:352`).
4. `readSenderModel` → cloud `get` → null → `provesAbsence` false → `unknown` → noop.
5. Local dig-deeper view: `mergeDigDoc` (`dig-merge.ts:57-59, 86-94`) trusts the envelope on
   `sameTitles` alone → renders the **old summary's** leads and bullets beside the new MD.
6. Baseline advanced; run 2 sees equal hashes → `skip` → `companionTransfer` never runs again.
   Silent (no `report.errors`) and sticky.

Blast radius is bounded and worth stating plainly: the local **summary** view self-heals, because
`runHtmlDoc` (`generate.ts:40-60`) unconditionally regenerates and overwrites the envelope, and it
is gated on the `summaryHtml` that step 3 just cleared. The **dig-deeper** view does not — it
merges the cached envelope with no regeneration. Pre-R4 this path deleted the model, so the gist
column degraded to an honest skeleton (`gist = null`); post-R4 it shows stale prose as current.

**(b) Corrupt-vs-absent on the local sender.** The lead asked whether collapsing them is right.
Here it happens to be, but for a reason the code does not state. `companionTransfer` runs only when
`decision.action !== 'skip'` (`sync-run.ts:601`), so the receiver's body was just replaced; a corrupt
sender envelope means nothing shippable either way. The residual defect is the opposite one —

**(c) `none` deletes receiver models that are still valid.** `decideCompanion` never inspects the
receiver. When the local sender provably has no model, it returns `deleteReceiverModel` even if the
cloud receiver's envelope already carries `sourceMdHash === winnerMdHash`. Recovery on the cloud is
`resolveMagazineModel → reserve_serve_model → spend_ledger` — real money. Reachability is the honest
caveat: it needs `reconcileClassA`'s identical-hash fall-through (`reconcile-class-a.ts:32-36`) —
byte-identical bodies with disagreeing `mdCorrectionsHash` or `docVersionMajor`. I could construct
it (a record predating a `docVersion` bump) but not show it arising naturally, so I rate this Low on
its own. It matters because the *fix* for (a) removes it for free.

**Recommended fix (closes (a) and (c) together).** Decide from the receiver:

```
receiverEnvelope.sourceMdHash === winnerMdHash  → keep  (already correct, whatever the sender says)
otherwise                                        → delete (provably stale: its source body is gone)
```

and let the sender read decide only whether a *replacement* can be shipped (`ship` when it matches,
otherwise delete-only). `unknown` then stops being a decision at all. Deleting a provably-stale
receiver model is not a money loss — it is a cache whose backing body no longer exists; the money
bug R4 fixed was deleting one that was still *good*, and receiver-side reasoning never does that.

If instead the noop is kept deliberately, the false claim in `companion.ts:26-28`,
`sync-run.ts:376-377` and `tests/lib/cloud-sync/companion.test.ts:27-32` must be corrected, and
`mergeDigDoc` must gate the gist on `sourceMdHash` rather than titles alone.

→ **Finding H-R5-1 (High).**

### A2. H2 — B1 guard scoped by `provesAbsence` — **GENUINELY FIXED**

`sync-run.ts:557-562` adds `&& !deps.localBlob.provesAbsence` / `&& !deps.cloudBlob.provesAbsence`.
I checked every way a local `get` can return null:

- `LocalFsBlobStore.get` (`local-blob-store.ts:22-25`) returns null **only** on `ENOENT`; every
  other errno rethrows. EACCES, EIO, ELOOP, EISDIR all propagate out of `readMdBody` and are caught
  by the per-video `try/catch` at `sync-run.ts:610` → `report.errors`, no baseline. Fail-closed.
- `assertLogicalKey` (`blob-store.ts:38-42`) throws, it does not return null. Same path.
- So on the local store a null body does prove the file is gone, and routing it to `copyToLocal`
  hydration is safe: the local record's pointer is dangling, there is nothing to destroy.

**The empty-file case does not reach this guard at all**, and behaves correctly. A 0-byte file
returns `Buffer.alloc(0)`, which is truthy, so `readMdBody` (`sync-run.ts:59-63`) yields `''`, and
`mdHash('') = sha256('\n')` — non-null. `deriveClassASignals` therefore reports a real hash and the
guard is not consulted. Downstream: both sides "have" MD, hashes differ, and with `mdGeneratedAt`
unchanged by truncation the tiebreak `newer(a,b)` on equal timestamps is false →
`copyToLocal` → the cloud's intact body overwrites the empty local file. It heals.

One asymmetry worth recording (not a finding, and pre-existing): that same equal-timestamp
tiebreak is deterministic in the **cloud's** favour, so a divergent body with an unchanged
`mdGeneratedAt` — a hand-edited local `.md` — is silently replaced by the cloud's. That is the
documented recency-tiebreak semantics and hand-editing MD is not a supported edit path
(`corrections` is), so I am not raising it.

**Both B1 regression tests still assert the cloud side.** `e2e.int.test.ts:585-616` (P1,
corrections conflict) and `:619-649` (P2, format downgrade) both seed the *cloud* blob as absent,
both assert `errors` non-empty / `updatedCloud === 0` / `updatedLocal === 0` / local bytes
preserved / **no baseline** / no spend, and both loop over two runs. Unaffected by the local-side
scoping. The new H2 test at `:707-731` covers the local side.

### A3. H3 — three layers — **LAYERS 1+2 FIXED; LAYER 3 IS UNREACHABLE (dead code)**

- **Layer 1** (`registry.ts:10-12, 36-40`) — `LocalPlaylist.playlistTitle` carried, conditionally
  spread so an absent title stays absent. Correct.
- **Layer 2** (`sync-run.ts:102-110`) — merges instead of first-wins. Correct, and this is the layer
  that actually stops the wipe.
- **Layer 3** (`sync-run.ts:152-157`) — `playlistMeta.playlistTitle ?? idx.playlistTitle`.
  **I could not find a reachable input**, which explains the lead's null mutation-test result.
  It is dead defense-in-depth, not a coverage gap — I do not recommend inventing a fixture for it.

  I enumerated each candidate the lead named:
  - *Cloud playlist absent from `listPlaylists`* — `listPlaylists`
    (`supabase-metadata-store.ts:230-243`) selects `playlist_title` and is unfiltered beyond RLS
    (`owner_id = auth.uid()`), and `runSync` snapshots it once at `:461` before the loop, so within a
    run every cloud playlist the receiver could hold is in `cloudSummaries` with its title.
  - *Zero-video playlist* — irrelevant; `playlistMetaFor` keys off the registries, not the videos.
  - *Local-only data root* — a local index with a title is discovered by `discoverLocalPlaylists`
    reading that same index, so `lp.playlistTitle` is populated whenever `idx.playlistTitle` is.
  - *Title in the cloud row but not in the summary* — the row and the summary read the same column.

  Recommendation: **document it as deliberate dead defense-in-depth** rather than drop it (the
  `readIndex` call is needed anyway for the row-exists check, so the carry-forward is free), and
  soften the comment, which currently reads as though it were load-bearing.

- **`readIndex` before `setPlaylistMeta`, snapshot reused for the row-exists check — no TOCTOU or
  ordering regression.** `setPlaylistMeta` touches only the `playlists` row (cloud:
  `supabase-metadata-store.ts:73-81`; local: `local-metadata-store.ts:13-21`, which spreads
  `...idx` and so preserves `videos`), never the video set, so the snapshot stays authoritative for
  `idx.videos.some(...)`. Single-run, single-writer per the spec's model.

  One inaccuracy in the claim it defends: the commit message and `sync-run.ts:147` state a sync
  *"can only ever FILL a title, never clear one."* Clearing is fixed, but **overwriting is not** —
  `playlistMetaFor` prefers `lp?.playlistTitle`, so a stale local title propagates over a newer
  cloud one on every additive local→cloud create. Titles have no LWW; this is unconditional
  local-wins. Cosmetic and repaired by re-ingest → **Finding L-R5-2 (Low)**.

---

## Part B — new findings

### H-R5-1 (High) — `noop` preserves a provably-stale model that the drift guard does not catch; `none` deletes ones that are still valid

`lib/cloud-sync/companion.ts:29-39`, `lib/cloud-sync/sync-run.ts:366-396`,
`lib/html-doc/read-model.ts:12-18`, `lib/html-doc/dig-merge.ts:57-59`.
Full trace, evidence and fix in **A1** above. This is the fourth appearance of the R4 root cause
(a reading that means "absent" also being what a failure produces), one layer up: R4 made the
*sender* read honest but left the *decision* keyed to it, when the receiver holds the exact answer.

### L-R5-2 (Low) — a stale local playlist title overwrites a newer cloud title

`lib/cloud-sync/sync-run.ts:108` — `lp?.playlistTitle ?? cp?.playlistTitle`. See A3. No data or
money loss; fix is either to prefer the cloud title or to route the write through
`setPlaylistTitleIfNull` semantics. Also correct the "can only ever FILL" comment at `:147`.

### L-R5-3 (Low) — `readManifest` swallows unreadable as absent, which can resurrect deleted videos

`lib/cloud-sync/manifest.ts:15-22` — `catch { }` → `{version:1, videos:{}}` covers EACCES/EIO
identically to ENOENT. With no baseline, `sync-run.ts:486-501` reads a one-sided video as a **new
additive create** instead of a delete, so a video deleted on one replica is copied back. The
direction is the safe one (resurrect, never delete) and §8 explicitly specifies degrade-on-corrupt,
so I am recording it rather than pressing it — but it is the same `catch → default` shape the branch
has now been bitten by four times, and it is the last one in the sync path.

### Swept and clean (no findings)

- **`readIndex` on both backends is fail-closed and correct.** Local (`lib/index-store.ts:81-98`)
  returns the sentinel only for a missing *file* inside an existing dir, throws
  `Output folder does not exist` for a missing dir, and rethrows any non-ENOENT errno or JSON
  parse error. Cloud (`supabase-metadata-store.ts:29-56`) throws on `plErr`/`vErr` and returns
  `emptyPlaylistIndex` only on `!pl` from a successful `maybeSingle()`. An absent playlist **is**
  distinguishable from a failed read on both. `ensureHydrationRoot` (`sync-run.ts:88-90`) correctly
  precedes the first local read, so the missing-dir throw cannot fire on the hydrate path.
- **No other `BlobStore` implementation silently inherits `provesAbsence === undefined`.** The only
  implementations are `LocalFsBlobStore` (`true`), `SupabaseBlobStore` (`false`), and the test
  `FailPromoteBlobStore` (`tests/integration/helpers/cloud.ts:165`), which *delegates*
  (`get provesAbsence() { return this.inner.provesAbsence; }`) rather than defaulting — the one
  place a silent `false` would have mattered. `tests/lib/storage/consistency.test.ts:38` builds a
  literal without the field, but it is not on a sync path, and fail-closed is the right default
  there. `model-store.ts:47` defaults to `localBlobStore`, which declares `true` correctly.
- **`?? null` siblings in write payloads.** The only explicit-null-into-a-write in the sync path
  besides H3's is `setPlaylistMeta`'s `playlist_title: meta.playlistTitle ?? null`
  (`supabase-metadata-store.ts:78`), whose sole sync caller is now `ensureReceiverSlot`.
  `merge_video_data` / `update_video_annotations` / `upsertVideo` / `updateVideoFields` all take
  caller-shaped payloads with no `?? null` coercion of their own. `transferClassA`'s
  `mdGeneratedAt ?? null` / `mdCorrectionsHash ?? null` (`sync-run.ts:327-328`) can null a loser
  value the winner lacks, but the signal degrades to the `processedAt` fallback on both sides and
  the bodies are identical by then, so it converges — and it is inside the known/deferred
  Codex-R2-Medium (absent companion scalars), so not re-raised.
- **Money safety.** No producer/enqueue/`spend_ledger` import anywhere under `lib/cloud-sync/`.
  `sanitizeAdditiveVideo` (`:116-133`) clears `summaryHtml`/`digDeeperHtml`/`digDeeperMd` and keeps
  only `artifacts.summaryMd`; `transferClassA` (`:352-353`) clears the two HTML caches and
  deliberately preserves `digDeeperMd`. `needsRegen` is report-only (`:580`). Both B1 tests and the
  H1/H2 tests assert `spendLedgerTotal()` unchanged across two runs. The one path that *forces* a
  re-spend is H-R5-1(c), folded into that finding.
- **Atomicity / baseline advance.** Every mutating helper throws on fault and the baseline write is
  the last statement on each branch: additive (`:495-500`, guard at `:181` precedes any state
  creation per H-R2-1), corrections-unresolved (`:571-576`, Class A preserved), transfer
  (`:601-609`). `transferClassA` stages → verifies the hash → `put` (overwrite, not the
  create-if-absent `promote`) → finalizes, so promoted is never advertised before durable.
  `copyAdditiveVideo:216-229` re-reads and asserts both row existence and the promoted artifact key
  before the caller advances.
- **Idempotency across two runs.** Traced for each branch: skip is stable; transfer converges to
  equal hashes → run 2 `skip`; corrections-unresolved preserves the previous Class-A baseline so
  run 2 re-evaluates; additive is guarded by the `readIndex` row-exists check. The only two-run
  asymmetry is H-R5-1's stickiness (the run-2 `skip` is exactly what makes the stale model
  permanent).
- **RLS / no service-role.** `cloudP = { id: deps.ownerId, indexKey: key }` (`:472`) with the F1
  comment; `SyncDeps` exposes no raw client, so `persist_summary` is unreachable; the cloud writes
  go through the `owner_id = auth.uid()`-guarded RPCs; `setPlaylistMeta`/`resolvePlaylistId` derive
  `ownerId` from `auth.getUser()` and throw without a session.

---

## Verdict

**NOT CONVERGED** — one new High (H-R5-1). H2 and H3-layers-1/2 are genuinely fixed; H3 layer 3 is
unreachable dead code (document, do not test); H1 is incomplete and should be re-fixed on the
receiver side, which closes the stale-model and the delete-a-valid-model cases together.
