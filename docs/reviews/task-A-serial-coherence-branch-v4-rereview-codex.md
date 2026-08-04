<!-- codex-review: model=gpt-5.5 -->

**Blocking**

None.

**High**

1. `lib/cloud-sync/reconcile-serial.ts:229` + `lib/cloud-sync/sync-run.ts:711`

Pre-write freshness mismatch can leave `cloudSnapshot` stale, and `sync-run` continues the playlist as if nothing changed.

Scenario: initial snapshot says `A` holds serial 7 and `B` holds serial 9. Local wants `A -> 3` and `B -> 5`. While `A` is copying, another sync moves `A` to serial 5 / `005_alpha.md`. The new pre-write read sees only `fresh.summaryMd !== cloudVideo.summaryMd` and returns `metadata-unverified` at `reconcile-serial.ts:230-233`. `sync-run` turns every non-ok result into a thrown per-video error at `sync-run.ts:711-714`, catches it at `sync-run.ts:770-772`, and continues without updating `cloudSnapshot`; `noteCloudRow` only runs after `rec.action === 'relocated'` at `sync-run.ts:716-725`. Later `B` sees serial 5 as free in the stale snapshot and can relocate there, ending with two cloud rows at serial 5.

Fix: on any pre-write freshness mismatch, either abort the rest of that playlist for this run, or re-read the full cloud index and replace/fold `cloudSnapshot` before processing later videos. The current `metadata-unverified` payload only carries `found` summaryMd, not the full row/serial, so it is insufficient to repair the occupancy view.

**Medium**

1. `lib/cloud-sync/reconcile-serial.ts:107`

The basename-only `digDeeperMd` remap now accepts invalid relative paths and lets the blob layer throw after earlier copies have already happened.

Scenario: cloud row has `summaryMd: "007_alpha.md"` and `digDeeperMd: "../007_alpha-dig-deeper.md"`. `paidKeysUnder` copies `007_alpha.md` to `003_alpha.md` first. Then basename remap accepts the traversal key because `path.posix.basename("../007_alpha-dig-deeper.md") === "007_alpha-dig-deeper.md"` and returns `"../003_alpha-dig-deeper.md"` at `reconcile-serial.ts:107-110`. `copyBlob` rejects `..` via `assertLogicalKey` at `lib/storage/blob-store.ts:87-90` / `132-133`, throwing past the typed `SerialReconcileResult`. Metadata is unchanged, but the relocation has left duplicate destination blobs and future runs repeat the same partial state.

Fix: validate `digDeeperMd` source and destination as logical blob keys before copying, and return `unmappable-key` or `copy-failed` instead of letting `copy()` throw. Better: precompute all source→destination mappings before any copy and reject invalid keys up front.

2. `lib/cloud-sync/reconcile-serial.ts:90`

`remap()` can map two different valid source keys to the same destination.

Scenario: `oldBase = "007_alpha"`, `newBase = "003_alpha"`, `cloudVideo.digDeeperMd = "dig/003_alpha/007_alpha-dig-deeper.md"`, and the blob listing under `dig/007_alpha/` includes `dig/007_alpha/003_alpha-dig-deeper.md`. The dig-deeper pointer maps to `dig/003_alpha/003_alpha-dig-deeper.md` by basename preservation at `reconcile-serial.ts:107-110`; the listed dig blob maps to the same destination via the `digPrefix` rule at `reconcile-serial.ts:93-94`. If bytes differ, the second copy reports `destination-exists` after the first copy has already created the destination, making the relocation non-resumable without manual cleanup.

Fix: build the complete mapping list before copying and require destination uniqueness for distinct sources. If duplicate destinations appear, return `unmappable-key` before writing any blob.

**Low**

Round-3 High #1 adjudication: I do not overturn it. The surrounding transfers do have the same unconditional metadata-write exposure: `transferClassA` writes the loser row with `updateVideoFields` at `lib/cloud-sync/sync-run.ts:427`, and `copyAdditiveVideo` finalizes with `upsertVideo` at `lib/cloud-sync/sync-run.ts:281`, both backed by bare update/RPC paths that do not compare against the row originally read (`lib/storage/supabase/supabase-metadata-store.ts:113-120`, `131-144`; SQL update at `supabase/migrations/0021_cloud_sync_signals.sql:79-90`). A3 is still special because it may clean up old-base blobs afterward, but the core lost-update exposure is genuinely not unique to A3.

---

## Adjudication (round 4) — coordinator, 2026-07-31

All three findings **accepted as stated**. No severity changed.

### High #1 — a pre-write mismatch left `cloudSnapshot` stale → **CONFIRMED, fixed**

Correct and precise: `noteCloudRow` runs only on `action === 'relocated'`, so a *detected concurrent
change* — the one moment we have hard proof the cloud moved under us — updated nothing. A later
video then read occupancy from a view already known to be wrong.

Fixed by refreshing the snapshot on `metadata-unverified` / `verification-unreadable`, and by
degrading safely when even that read fails: an `occupancyTrusted` flag stops reconciliation for the
rest of the playlist, and each still-diverged video is reported. Aborting the whole playlist (the
other suggested option) was not taken — every other step is safe, and skipping reconciliation only
defers repairs to the next run, whereas aborting would also drop unrelated additive creates and
Class-A/B merges.

### Medium #1 — traversal key throws past the typed result after earlier copies → **CONFIRMED, fixed**
### Medium #2 — two sources can map to one destination → **CONFIRMED, fixed**

One change fixes both: the relocation is now **planned in full before anything is written**. Every
source→destination pair is computed, `assertLogicalKey`-validated on both ends, and checked for
destination uniqueness, before the first `copy`. A refusal is therefore a genuine no-move again
rather than a partial write every re-run recreated.

### Low — round-3 High #1 adjudication upheld

Codex independently verified the claim rather than deferring to it: `transferClassA` finalizes via
`updateVideoFields` (`sync-run.ts:427`) and `copyAdditiveVideo` via `upsertVideo`
(`sync-run.ts:281`), both bare update/RPC paths that never compare against the row originally read
(`supabase-metadata-store.ts:113-120, 131-144`; SQL at `0021:79-90`). The lost-update exposure is
genuinely not unique to A3. Its one distinguishing property is noted and stands: A3 may *delete
old-base blobs* afterward, which is why it — and only it — now verifies before cleaning up.

### Round-4 outcome

1 High + 2 Medium, all fixed and mutation-checked. 255 suites / 2581 tests green, tsc clean.
**Round 5 required** — the plan-before-copy restructure and the occupancy-refresh path are new,
unreviewed design on the money path.
