<!-- codex-review: model=gpt-5.5 -->

**Blocking**

No blocking findings. I specifically checked absent-vs-unreadable handling in `copyBlob`, copy-before-metadata/delete-after-metadata ordering, 0023 RPC locking/reselect/grants, and remaining 2-arg `claim_video_slot` call sites. I did not find a direct paid-byte overwrite/delete-before-pointer-move path.

**High**

1. [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:159) leaves stale `artifacts.*` pointers after a cloud base move.

Scenario: cloud row has `summaryMd: "007_alpha.md"` and `artifacts.modelJson: { key: "models/007_alpha.json", status: "promoted" }`. A3 copies `models/007_alpha.json` to `models/003_alpha.json`, then patches only `artifacts.summaryMd`. Supabase `merge_video_data` deep-merges artifacts, so `artifacts.modelJson` remains at `models/007_alpha.json`. Cleanup then deletes `models/007_alpha.json`, leaving metadata advertising a missing paid/source artifact.

Fix: make A3 remap or explicitly tombstone every base-addressed artifact subkey, not only top-level fields. Because cloud artifact merge is additive, this likely needs either a full artifact replacement RPC mode or null/tombstone handling in `merge_video_data`.

2. [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:561) uses a pre-loop `cloudSnapshot` for A3 occupancy, but rows created earlier in the same run are invisible.

Scenario: local has one-sided `A` with `serialNumber: 5`, `summaryMd: "005_alpha.md"`; cloud lacks it. The loop creates cloud `A`. Later in the same playlist, two-sided `B` has local serial 5 but cloud serial 9 and base `009_beta`. `reconcileCloudBase` checks the stale snapshot, does not see newly-created `A`, and moves `B` to serial 5 if `005_beta.md` is free. Result: cloud now has two videos with `serialNumber: 5`.

Fix: keep the consistent initial snapshot for swap detection, but also track serials/bases claimed during this run and include them in the holder check. Do not rely on `destination-exists`; same-serial/different-slug collisions do not create the same blob key.

**Medium**

1. [lib/cloud-sync/reconcile-serial.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/reconcile-serial.ts:77) has an unsafe `remap()` fallback for `digDeeperMd`.

Scenario: `digDeeperMd` is `backup/007_alpha/007_alpha-dig-deeper.md`. `remap()` does a first `replace`, yielding `backup/003_alpha/007_alpha-dig-deeper.md`; the basename still carries the old base. The row is updated to a path that violates the serial/base invariant, while cleanup deletes the original paid file.

Fix: remove the generic fallback. Handle known key shapes structurally: summary root, model path, `dig/<base>/...`, and `digDeeperMd` by replacing the basename’s base prefix, preserving directory. If a key is not one of those shapes, fail closed and do not move metadata.

**Low**

No low findings. I checked `sanitizeAdditiveVideo` for accidentally retaining `digDeeperMd`/cache artifacts, the 0023 drop/recreate/grants/security-invoker shape, and remaining callers of the 2-arg metadata method; nothing else rose above test/documentation risk.

---

## Adjudication (round 1) — coordinator, 2026-07-31

Every finding was adjudicated by reading the code, per `docs/dev-process.md`
("Reviewer disagreement is the signal ... adjudicate by reading the code, and record the
adjudication in the review doc"). Two of three changed severity; all three produced a code change.

### High #1 — stale `artifacts.*` pointers → **DOWNGRADED to latent; fixed anyway, differently**

**Not reachable.** The premise is that a cloud row can carry `artifacts.modelJson`. Nothing writes
it. `writeArtifact` (`lib/storage/supabase/consistency.ts:17`) is the ONLY writer of any artifact
kind other than `summaryMd`, and it has **zero production callers** — it is the orphan module of
architecture-review finding #2. Every other artifacts write in the tree shapes the object down to
`{ summaryMd }` (`sanitizeAdditiveVideo`, `transferClassA`, `reconcileCloudBase`). Verified by
grepping every `artifacts` write site.

**The suggested fix was also rejected.** Remapping the pointer without copying the blob is a
half-move: `paidKeysUnder` only knows the MD, the model, the digs and `digDeeperMd`, so a `slide` or
`pdf` pointer would be advanced to a key holding nothing. `reconcileCloudBase` now **refuses**
(`unsupported-artifacts`) when the record carries any non-`summaryMd` kind. That cannot half-move
anything, and the day the case becomes reachable it fails loudly at the code that must be extended.

### High #2 — pre-loop `cloudSnapshot` misses same-run claims → **CONFIRMED, fixed**

Correct, and it falsified a safety claim the code itself made: the comment argued that a serial
taken during the run is caught downstream by the copy phase's fail-closed `destination-exists`.
That only holds when the two videos share a KEY — same serial with a different slug produces
different keys, nothing collides, and the run ends with two cloud rows at one `serialNumber`.

Codex's scenario needs two local videos at serial 5 (local corruption). A **simpler reachable** one
was used for the regression test: a local video with NO serial is created on cloud at `max + 1`,
which can be exactly the serial a later two-sided video is relocated onto. No pre-existing
corruption required.

Fixed as suggested — the snapshot is kept for swap detection and now maintained: every cloud row the
run creates or relocates is folded back in (`noteCloudRow`).

### Medium #1 — unsafe `remap()` fallback → **scenario corrected; fix accepted**

The stated shape (`digDeeperMd = 'backup/007_alpha/007_alpha-dig-deeper.md'`) does not occur:
`digDeeperMd` is always a bare basename, `${summaryBasename}-dig-deeper.md`
(`lib/dig/dig-section.ts:84`), with no directory component. The *reasoning* is right regardless — a
first-occurrence `String.replace` is a guess. `remap()` now enumerates every known shape and returns
`null` for anything else, and every caller treats `null` as a refusal (`unmappable-key`).

### Found by the coordinator's own pass (not in the Codex review)

**Additive create collided on SERIAL but not on KEY.** A legacy receiver row carrying `003_alpha.md`
with no `serialNumber` — the shape `backfillOrder` exists to repair — passed the serial-only check,
and the additive blob write then put the sender's body over it. On the local FS adapter `promote` is
a rename, which overwrites: a summary destroyed. `ensureReceiverSlot` now refuses on either.

**Migration 0023 was a rolling-deploy break.** Dropping `claim_video_slot(uuid, text)` turns every
ingest and sync on in-flight old app instances into "function does not exist" for the length of the
rollout. A `DEFAULT` does not fix it — PostgREST resolves an RPC by the named arguments in the
request body, so a 2-arg call does not match a 3-arg signature. The migration now creates two
distinct, non-defaulted signatures; the 2-arg one is a wrapper passing `null`.

### Round-1 outcome

3 Codex findings + 2 coordinator findings, all addressed. 255 suites / 2572 tests green, tsc clean.
Round 2 required: every fix above is new, unreviewed design, and two of them touch the money path.
