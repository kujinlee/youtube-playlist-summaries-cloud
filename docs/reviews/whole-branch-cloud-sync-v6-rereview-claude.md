# Whole-branch re-review (round 6, Claude) — Stage 3 Cloud Sync (M2a)

Branch `feat/stage3-cloud-sync`, HEAD `12c850d`. Read-only review of the shipped state.

Gates run: `npx jest tests/lib/cloud-sync` → **15 suites / 109 tests pass**. `npx tsc --noEmit` → **clean**.

---

## Part A — verification of the round-5 fixes

### A1. The nine (sender × receiver) combinations — **GENUINELY FIXED**

`decideCompanion` (`lib/cloud-sync/companion.ts:54-93`) is exhaustive: step 1 keys on the sender,
steps 2/3 key on the receiver, and step 3's fallthrough (`return { kind: 'noop',
shareNeedsOwnerServe: true }`, :92) is total, so there is no unhandled combination.

Walking sender ∈ {env-match, env-nomatch, none, unknown} × receiver ∈ {env-match, env-stale-hash,
env-legacy-nohash, none, unknown}:

| sender | receiver | result | correct? |
|---|---|---|---|
| env-match | any | ship | yes — except one narrow case, L-R6-1 below |
| env-nomatch / none / unknown | env-match | noop, flag false | yes — paid artifact matching the winner body is kept |
| env-nomatch / none / unknown | env-stale-hash | delete, flag true | yes — provable staleness, no ambiguity |
| env-nomatch / none / unknown | env-legacy-nohash | noop, flag true | yes — unprovable, fail-safe-for-money |
| env-nomatch / none / unknown | none | noop, flag true | yes — nothing to delete, share still unready |
| env-nomatch / none / unknown | unknown | noop, flag true | yes — the R4 destructive case, now closed |

Nothing is deleted without proof, and nothing provably wrong is kept: the only "kept while wrong"
cells are legacy-no-hash and unprovable reads, where wrongness is by definition not established.
`tests/lib/cloud-sync/companion.test.ts:33-64` parametrizes all three non-shipping sender states
across all five receiver states, so the matrix is covered by tests, not just by reading.

### A2. `provablyStale` semantics — **GENUINELY FIXED**

`receiverModel.kind === 'envelope' && receiverModel.envelope.sourceMdHash !== undefined`
(:89-90) is reached only after step 2 has excluded the matching case, so "present" here already
means "present and different". `sourceMdHash` is `.optional()` in `ModelEnvelopeSchema`
(`lib/html-doc/model-store.ts:22`), so `undefined` is exactly the legacy pre-1F-a envelope, which is
correctly excluded from the delete. The reasoning is right.

**Matching-hash-but-stale-`sourceSections`/`generatorVersion` is handled sanely by the serve path.**
A matching `sourceMdHash` means the model was generated from byte-identical MD, so
`sourceSections` cannot diverge; only `generatorVersion` can (replica version skew). In that case
`isFresh` (`lib/html-doc/read-model.ts:20-25`) returns false, and both consumers degrade correctly:
the owner path (`resolveMagazineModel`, `lib/html-doc/serve-doc.ts:56-57`) falls through to
reserve → regenerate → `writeModelEnvelope` (`put`, overwrite) so the cache self-heals; the anon
share path (`app/s/[token]/route.ts:81-82`) 503s "not ready" without generating. No stale render, no
stuck cache. See L-R6-2 for the reporting nit this creates.

### A3. Receiver null mapped through `provesAbsence` — **GENUINELY FIXED**

`companionTransfer` reads both sides through the same resolver
(`lib/cloud-sync/sync-run.ts:388-390` → `readModelSide`, :415-419), and `readModelSide` keys on
`side.blob.provesAbsence` — so the receiver's null is resolved against the *receiver's* backend, not
the sender's. `SupabaseBlobStore.provesAbsence = false` / `LocalBlobStore.provesAbsence = true`
(`lib/storage/supabase/supabase-blob-store.ts:10`, `lib/storage/local/local-blob-store.ts:10`), and
`?? unknown` is the default for a store that omits the optional flag (`lib/storage/blob-store.ts:18`).
An unprovable receiver read yields `unknown` → `provablyStale` false → noop. **No delete.** Correct.

### A4. `shareNeedsOwnerServe` on `noop` — **GENUINELY FIXED, and not over-reporting**

The row-7 contract at `tests/integration/cloud-sync/e2e.int.test.ts:236-247` is preserved: local is
the format-2 winner with no model envelope; the cloud receiver has none either and cannot prove it,
so the decision is `noop + true` and `report.shareNeedsOwnerServe >= 1` still holds. (The test's
inline comment says "→ deleteReceiverModel", which is now wrong — see L-R6-3.)

On over-reporting, the bound is tighter than it first looks. `companionTransfer` is called only when
`decision.action !== 'skip'` (`sync-run.ts:624`) — i.e. only for **two-sided videos that actually
had a Class-A MD transfer**. Additive one-sided creates route through `copyAdditiveVideo` and never
reach it, so a first-device hydrate of N videos contributes **zero** to the counter. Within the
transferred set, `noop + true` fires whenever the receiver holds no model matching the new winning
body — which is precisely the set of shares that genuinely cannot render until the owner re-serves.
The counter stays meaningful.

### A5. `ensureReceiverSlot` ordering after the layer-3 removal — **GENUINELY FIXED on both backends**

`setPlaylistMeta` → `readIndex` → row-exists check → `claimVideoSlot` (`sync-run.ts:168-174`).

- **Local:** `setPlaylistMeta` does `readIndex` then `writeIndex`
  (`lib/storage/local/local-metadata-store.ts:13-21`), which materializes `playlist-index.json`
  before the subsequent `readIndex` — so on a fresh-device hydrate the file exists by the time it is
  read. Combined with `ensureHydrationRoot`'s `mkdir -p` (`sync-run.ts:88-90, 492`), the missing-dir
  throw is also covered.
- **Cloud:** `setPlaylistMeta` upserts the `playlists` row
  (`lib/storage/supabase/supabase-metadata-store.ts:73-82`); `readIndex` then finds it (:29-36,
  returning the empty-index sentinel only when the row is genuinely absent), and `claimVideoSlot`'s
  `requirePlaylistId` resolves (:92). Ordering the meta write first is load-bearing on this backend,
  not merely convenient.

The `idx.videos.some(...)` row-exists check remains authoritative: the read happens after the only
write that precedes it in this run, that write touches the playlists row only (never the video set),
and sync is single-run. The removed layer 3 was genuinely unreachable — I could not construct an
input where `playlistMetaFor` yields no title while the receiver row has one, for the reasons the
comment enumerates (`sync-run.ts:158-167).

### A6. `playlistMetaFor` cloud-title precedence (L-R5-2) — **FIXED, with a bounded and acceptable trade**

`cp?.playlistTitle ?? lp?.playlistTitle` (`sync-run.ts:115`). There *is* a case where a newer local
title loses: the user renames the playlist on YouTube and re-ingests **locally** but not in the
cloud — the local title is fresher and the cloud's stale one now wins. The effect is bounded: the
value is consumed only by `ensureReceiverSlot`'s `setPlaylistMeta` on an additive create, so the
worst outcome is that the cloud keeps a title it already had (a missed refresh, not a clobber), and
the fallback still lets a replica that holds the only title supply it. Since titles carry no LWW
timestamp, either precedence loses in one direction; the chosen one loses the *cosmetic* direction
rather than the destructive one. No change recommended.

---

## Part B — new findings

### L-R6-1 (Low) — `ship` can downgrade a receiver model that was already fresh

`lib/cloud-sync/companion.ts:63-65`. Step 1 fires before step 2, so when **both** sides hold an
envelope with `sourceMdHash === winnerMdHash` and only the **sender's** `generatorVersion` is older,
the ship overwrites a receiver model that `isFresh` accepted with one it will reject
(`lib/html-doc/read-model.ts:24`). The receiver's share flips from rendering to 503, and recovery is
an owner re-serve, which reserves and charges (`serve-doc.ts:60-113`) — the same class of
user-re-spend as H1 / H-R5-1, which is why I am filing it rather than dropping it.

Rated **Low, not High**, because reaching it needs two independent unlikely conditions at once:
(a) `GENERATOR_VERSION` skew between the local checkout and the deployed cloud image, *and* (b) the
transfer **loser** already holding a model built from the **winner's exact body** — which means the
content ping-ponged between the replicas. A guard would be one clause (prefer the receiver when its
envelope matches the winner hash and its `generatorVersion` is not older), but per the calibration
this does not justify a fix round on its own; it is a fine candidate to fold into any future edit of
this function.

### M-R6-1 (Medium) — a failed `ship` write is sticky: no re-run ever retries it

`lib/cloud-sync/sync-run.ts:392-394`. `writeModelEnvelope` is **not** wrapped (unlike the delete on
:401, which is `try`/`catch`), so a transient blob `put` failure throws out of `companionTransfer`,
past `writeVideoBaseline`, into the per-video catch on :633. The error does surface in
`report.errors`, so this is not silent — but it is **unrecoverable by re-running**: `transferClassA`
already committed the winner body to the loser (:335, :373), so the next run's `reconcileClassA`
returns `skip`, and `companionTransfer` is gated on `decision.action !== 'skip'` (:624). The ship is
never attempted again. The receiver keeps the model it had; if that model has matching section
titles and a matching generator version but was built from the pre-sync body — the prose-only-change
case that motivated H-R5-1 — it will be served as fresh indefinitely.

Not a money loss and not R5-introduced (the companion step has been outside the atomic commit since
T7), which is why it is Medium. Cheapest containment is to treat a companion-step failure the way
the delete is treated — swallow it and set `shareNeedsOwnerServe: true` — so the run reports the
share as unready instead of leaving a stale model advertised as fresh. Recommend deferring with an
owner rather than opening a fix round.

### L-R6-2 (Low) — `noop + false` under-reports a matching-hash / version-skewed receiver model

`lib/cloud-sync/companion.ts:69-71` reports `shareNeedsOwnerServe: false` for any receiver envelope
matching `winnerMdHash`, including one whose `generatorVersion` is stale — which the share route
will 503 on (`app/s/[token]/route.ts:81-82`). This is an under-report in the direction the code
comment identifies as the harmful one (:85-86). It is Low because the condition **predates the
sync** (that model was already not-fresh before the run) and `shareNeedsOwnerServe` is scoped to
shares this sync left unready, not to a general share-health audit.

### L-R6-3 (Low, comment rot) — stale inline comment on the row-7 test

`tests/integration/cloud-sync/e2e.int.test.ts:245` reads
`// winner (local) has no model envelope → deleteReceiverModel`. Under R5 that input takes the
`noop + shareNeedsOwnerServe: true` path (receiver has no model and the Supabase store cannot prove
it). The assertion is still correct; only the comment misdescribes the mechanism, and it names the
one branch a future reader would most likely trust when reasoning about deletes.

---

## Money / atomicity / idempotency sweep (no findings)

- **No charging surface reachable from sync.** `grep` over `lib/cloud-sync/*.ts` imports finds no
  `gemini`, `job-queue`, `enqueue`, or `spend` module, and no `createServiceClient` / service-role
  key anywhere in the directory. The cloud principal is `deps.ownerId` = `auth.uid()`
  (`sync-run.ts:495`), so every write stays inside RLS.
- **Regenerable cache is never resurrected.** `sanitizeAdditiveVideo` (:123-140) nulls
  `summaryHtml`/`digDeeperHtml`/`digDeeperMd` and keeps only `artifacts.summaryMd`;
  `transferClassA` clears only the two HTML caches and deliberately preserves the paid
  `digDeeperMd` (:358-367). Consistent, and the asymmetry is correctly justified.
- **`needsRegen` stays report-only** — `report.needsRegen += 1` at :603 and :595, with no
  corresponding write anywhere.
- **Baseline advance.** Every path that advances writes only after a durable, *verified* receiver
  write: additive after the row-exists + promoted-artifact re-read (:231-244) then :520; two-sided
  after `transferClassA` returns (:632); corrections-unresolved writes a non-advancing Class-A
  baseline (:463-471); `skip` advances legitimately (N4). Every throw path skips the baseline, and
  every "seen" two-sided video gets one.
- **Idempotency across two runs.** A second run over a converged state derives equal `mdHash` on
  both sides → `skip` → no transfer, no companion step, no blob write; the baseline rewrite is
  value-identical. No new "absent means failure" instance beyond the deferred `readManifest`.

---

## Verdict

Part A: all six round-5 items **GENUINELY FIXED**. Part B: one Medium (M-R6-1, pre-existing,
recommend deferring with an owner) and three Lows. **No new Blocking or High.** This is the clean
round the loop was converging toward — the remaining items are the residue that always survives, not
a signal that another fix cycle is owed.

**CONVERGED**
