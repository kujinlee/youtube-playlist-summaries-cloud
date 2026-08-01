<!-- codex-review: model=gpt-5.5 -->

**Blocking**

No blocking findings. I checked the round-1 adjudicated items around swap aborts, unsupported artifact reachability, `remap()` null handling, receiver serial/key collisions, and the 0023 wrapper shape.

**High**

1. [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:210) treats a non-conditional metadata write as proof that the pointer moved, then deletes the old-base blobs.

Scenario: sync reads cloud video `V` at `summaryMd: "007_alpha.md"`, copies `007_alpha.md`, `models/007_alpha.json`, and `dig/007_alpha/...` to `003_alpha`. Before line 211 runs, another client deletes or rewrites the cloud row. Supabase `updateVideoFields` calls `merge_video_data`, whose SQL `update videos ... where playlist_id = ... and video_id = ...` returns void and does not raise when it updates zero rows ([0021_cloud_sync_signals.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79)). `reconcileCloudBase` then proceeds to cleanup at line 224. In the delete case, it deletes old-base paid blobs even though no row was moved. In the concurrent rewrite case, it can overwrite a newer pointer and orphan the other writer’s newly addressed content.

Fix: make the relocation metadata write conditional and observable. Either add a dedicated RPC that locks the video row and updates only if the current `summaryMd`/serial/artifact key still match the `cloudVideo` read, returning the updated row or `not-found/stale`; or change the store seam to return affected-row state and re-read/verify `summaryMd === newBase.md` before cleanup. Do not delete sources unless the row is proven to point at the new base.

**Medium**

1. [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:158) performs blob copies before checking `unsupported-artifacts` at line 204.

Scenario: a cloud row has `artifacts.slide` plus normal `summaryMd`, model, and dig blobs. The function copies all known paid keys to the new base, then refuses at line 207. Metadata is not advanced and cleanup does not run, so the run leaves unreferenced duplicate blobs even though the refusal is supposed to be a fail-closed no-move. Re-runs keep reporting the refusal; the copied blobs are harmless for content integrity, but this is still a non-atomic half-state introduced by the fix.

Fix: compute and reject unsupported artifact kinds before `paidKeysUnder()` and before any `blob.copy()` calls.

**Low**

1. [tests/lib/storage/delayed-async-fake.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/storage/delayed-async-fake.ts:19) drops the new `desiredSerial` argument.

Scenario: any async-discipline test that wraps a real `MetadataStore` with `delayedStore` and exercises additive sync will call `claimVideoSlot(p, videoId, desiredSerial)`, but the wrapper forwards only `(p, videoId)`. That makes the wrapped store allocate `max + 1` instead of adopting the sender serial, producing false serial-mismatch failures or leaving this wrapper unable to cover the new contract.

Fix: forward the third parameter: `claimVideoSlot: (p, v, desiredSerial) => wrap(() => inner.claimVideoSlot(p, v, desiredSerial))`.

Round-1 verification: `noteCloudRow` covers cloud additive creates, cloud relocations, and `copyToCloud` writes; the current mutation scheme does not break the two-video swap abort because neither side of a direct swap can move first. The `remap()` prefix bug is genuinely fixed by the exact `digDeeperMd` match. The 0023 two-signature migration is not ambiguous by arity, the SQL wrapper’s `select *` is valid for `returns table`, and grants are present on both signatures.

---

## Adjudication (round 2) — coordinator, 2026-07-31

All three findings **accepted as stated**. No severity changed this round.

### High #1 — metadata write treated as proof → **CONFIRMED, fixed**

Verified: `merge_video_data` (`0021:79`) is a bare `UPDATE ... WHERE playlist_id = .. AND
video_id = ..` returning void. Zero rows affected raises nothing, and
`SupabaseMetadataStore.updateVideoFields` inspects only `error`. So a row deleted or replaced by
another client between the read and the write leaves the metadata untouched while the call
"succeeds" — and the cleanup then deletes paid blobs the surviving row still points at.

This is the **same silent-zero-row hazard the codebase already documented** for additive creates
(`sync-run.ts`, round-4 H1: *"bare UPDATEs of a row pre-created by claimVideoSlot: they silently
affect 0 rows (no throw)"*). A3 walked straight into a known trap.

Fixed with the same shape as that guard and as A4's verify-after-write: read the row back and
require `summaryMd === <newBase>.md` before any delete (`metadata-unverified`). The heavier
locking-RPC option was not taken — the re-read uses existing primitives and matches the discipline
already established on this path.

### Medium #1 — copies happen before the artifacts refusal → **CONFIRMED, fixed**

Correct: a refusal that is supposed to be a fail-closed no-move was leaving duplicate blobs at the
new base on every run. The check now runs before `paidKeysUnder` and before any `copy`.

### Low #1 — `delayedStore` drops `desiredSerial` → **CONFIRMED, fixed**

Real, and worse than cosmetic: the wrapper would silently downgrade every claim to "no preference",
manufacturing the exact serial mismatch it is meant to be transparent to.

### Round-2 verification of round 1

Codex independently confirmed: `noteCloudRow` covers all three cloud-mutation sites; mutating the
snapshot does not break the swap abort (neither side of a direct swap can move first); the `remap()`
prefix bug is genuinely fixed by the exact `digDeeperMd` match; the 0023 two-signature migration is
unambiguous by arity, the `language sql` wrapper's `select *` is valid for a `returns table`
function, and grants are present on both signatures.

### Also found by the coordinator this round (before the Codex result landed)

- `remap()` matched `digDeeperMd` by PREFIX. With `oldBase = '003_a'` that also matches
  `003_ab-dig-deeper.md` — a different video's paid artifact — rewriting it to a path pointing at
  nothing while cleanup deleted the real file. One base being a prefix of another is ordinary, since
  slugs are free text. Now an exact match; anything else refuses.
- `noteCloudRow` was missing at the `copyToCloud` transfer, which rewrites the cloud row's key.

### Round-2 outcome

1 High, 1 Medium, 1 Low from Codex + 2 from the coordinator, all fixed. Every fix is
mutation-checked. **Round 3 is required** — High #1 changed the failure model of the money path, and
a Blocking/High fix is itself new, unreviewed design.
