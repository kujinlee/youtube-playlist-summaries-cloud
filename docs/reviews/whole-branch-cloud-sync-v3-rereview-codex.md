Reading prompt from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f75eb-ae97-7bc2-bdc4-c70f6cf5dab9
--------
user
You are an adversarial WHOLE-BRANCH RE-REVIEWER (ROUND 3) for the Stage 3 Cloud Sync (M2a) branch `feat/stage3-cloud-sync`. HEAD is `1f54c60`.

Convergence trail so far:
- Round 1 (`docs/reviews/whole-branch-cloud-sync-codex.md`) → 1 Blocking + 2 High → fixed in `32a164c`.
- Round 2 (`docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md` and `-claude.md`) → confirmed WB-B1/WB-H2 fixed, found WB-H1 INCOMPLETE (H-R2-1) plus a REGRESSION introduced by the WB-H2 fix (H-R2-2) and a Medium (M-R2-2) → fixed in `1f54c60`.

Read `git show 1f54c60` and both round-2 review docs first. Note the "Coordinator adjudication" section appended to the Claude round-2 doc — round 2's two reviewers disagreed on severity and the code settled it; do not re-open that.

## Part A — verify each round-2 fix is GENUINELY fixed, not reworded
1. **H-R2-1** — the unreadable-MD-body guard moved ABOVE `ensureReceiverSlot` in `copyAdditiveVideo` (`lib/cloud-sync/sync-run.ts`). VERIFY: is there now NO path that creates partial receiver state before a possible throw (consider `setPlaylistMeta` inside `ensureReceiverSlot`, the staged-blob put, and `claimVideoSlot`)? Does the two-run e2e assertion actually fail if the guard is moved back? Is the residual `if (video.summaryMd && mdBody != null)` condition at the staging block dead/redundant given the guard above, and if so does that redundancy hide anything?
2. **H-R2-2** — `digDeeperMd: null` removed from `transferClassA`'s `completeTuple`. VERIFY: with `digDeeperMd` preserved but the MD BODY replaced by the winner's, is the retained dig doc now semantically stale in a way that misleads a consumer (`lib/html-doc/build-doc-html.ts:75,86`, `app/api/videos/[id]/dig-state/route.ts`, `lib/pdf/pdf-path.ts`)? Specifically: dig sections are anchored to summary section timestamps/anchors — if the winner MD has different sections, does merging the preserved dig produce wrong or orphaned anchors? Weigh that against the cost of destroying paid content. Is `digDeeperHtml: null` sufficient to force the re-merge? Is the additive path (`sanitizeAdditiveVideo`, which still nulls `digDeeperMd`) still correct given it targets a receiver with no existing row?
3. **M-R2-2** — the corrections guard narrowed to `correctionsUnresolved && la.mdHash != null && ca.mdHash != null`, with `deriveClassASignals` hoisted above the guard. VERIFY: the hoist claims to be behavior-neutral because derivation is pure — confirm `readMdBody` has no side effects and that moving TWO blob reads earlier cannot change ordering/error behavior (e.g. a blob read that throws now aborts the video BEFORE the Class-B baseline would have been written — is that a behavior change, and is it the right one?). Confirm the WB-B1 intent still holds exactly for the both-have-MD case. Confirm the one-sided hydration case cannot destroy anything or record a false agreement.

## Part B — hunt for NEW defects the round-2 fixes introduced or exposed
- Baseline-advance correctness across ALL branches (additive / transfer / skip / corrections-unresolved / one-sided-hydration-under-conflict, which is NEW). Any branch advancing a baseline without a durable write, or failing to advance for a "seen" video (→ spurious delete inference next run)?
- The NEW one-sided-hydration-under-corrections-conflict path: what baseline does it write, and is that baseline honest? Could it record agreement about corrections that are still in conflict?
- Money-safety: no enqueue, no `spend_ledger` consumption, no regenerable-cache resurrection; `needsRegen` report-only. ALSO: any path that forces the USER to re-spend (the H-R2-2 class of bug) counts as a money finding.
- Atomicity: durable-before-advertise, manifest-after-commit on every path.
- Idempotency: run each branch twice — same outcome, no oscillation, no sticky false agreement.
- Cross-backend local-vs-Supabase semantic mismatches.
- RLS / no-service-role unchanged.

## Scope
SHIPPED state at HEAD. Files: `lib/cloud-sync/*.ts` (esp. `sync-run.ts`), `supabase/migrations/0021_cloud_sync_signals.sql` + `0009_*`, `lib/storage/local/*`, `lib/storage/supabase/*`, `lib/html-doc/*`, `lib/dig/*`, tests under `tests/lib/cloud-sync/` and `tests/integration/cloud-sync/`. Spec: `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

KNOWN-and-ACCEPTED / DEFERRED — do NOT re-report unless you prove they mask a real bug: T14-M1, T14-M2, T5 coverage gaps, T4 automock comment; Claude-R2-M1 (stale non-`summaryMd` artifact pointers on transfer); Codex-R2-Medium (absent/undefined companion scalars not explicitly cleared). Also do NOT report `tests/integration/reservation-release.test.ts` failures — verified pre-existing on a clean tree (local Supabase state pollution), tracked separately.

## Output
Per finding: severity (Blocking/High/Medium/Low), `file:line`, concrete failure scenario (inputs → wrong outcome), fix. For Part A, state per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.

codex
I’ll use the review posture here: first read the prior review artifacts and the fixing commit, then inspect the touched sync paths and targeted tests before judging convergence.
exec
/bin/bash -lc "sed -n '1,260p' docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
Reading prompt from stdin...
OpenAI Codex v0.142.5
--------
workdir: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
model: gpt-5.5
provider: openai
approval: never
sandbox: danger-full-access
reasoning effort: none
reasoning summaries: none
session id: 019f75da-54b1-7903-9517-148b4b5d1c7b
--------
user
You are an adversarial WHOLE-BRANCH RE-REVIEWER (ROUND 2) for the Stage 3 Cloud Sync (M2a) branch `feat/stage3-cloud-sync`.

Round 1 found 1 Blocking + 2 High. They were fixed in commit `32a164c` (the branch HEAD). Your job has TWO explicit parts:

## Part A — verify each round-1 fix is GENUINELY fixed, not reworded
1. **WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy.** Fix: in `runSync` (`lib/cloud-sync/sync-run.ts`), when `merges.corrections.winner === 'equal' && merges.corrections.conflict`, skip the Class-A copy entirely, count `needsRegen`, and write `buildCorrectionsUnresolvedBaseline` (carries the PREVIOUS classA baseline, or an honest `{docVersionMajor:0, mdGeneratedAt:null, mdCorrectionsHash:null, mdHash:null}` placeholder on first sync). VERIFY: is the guard placed BEFORE every write path (including the companion transfer and any archived/delete handling)? Does the `continue` skip anything that MUST still run (delete-inference "seen" marking, report counters, companion, archived sync)? Is `report.archivedNotSynced` incremented correctly and only there? Does the placeholder baseline (docVersionMajor 0) cause a wrong decision anywhere that DOES read the Class-A baseline — confirm reconcileClassA truly never reads it.
2. **WB-H1 (High) — additive create could advertise `promoted` with no blob.** Fix: throw when `video.summaryMd` is set but `mdBody == null`; strip `sanitized.artifacts.summaryMd` when no blob was written; post-write verify that the receiver row advertises `status==='promoted'` at the right key. VERIFY: does the throw leave PARTIAL state (a bare receiver slot created by `ensureReceiverSlot`, a staged blob orphaned) that a later run mishandles? Is the summary-less video (summaryMd == null) path still correct? Does the strict post-write assert produce false failures on the local store (shallow-merge) vs the cloud store (`merge_video_data` deep-merge) — a cross-backend semantic mismatch?
3. **WB-H2 (High) — two-sided transfer left stale rendered HTML.** Fix: `transferClassA` sets `summaryHtml/digDeeperHtml/digDeeperMd` to `null` in the update payload. VERIFY: does `merge_video_data` (migration 0021 / 0009) actually STORE a JSON null (invalidating) rather than treating null as "no change" and skipping the key — trace the RPC body. Same question for the local store's shallow merge. If null is dropped by either backend, the fix is cosmetic and the stale-HTML bug survives. Also: are there OTHER regenerable-cache fields that should have been nulled (compare against `sanitizeAdditiveVideo`'s strip list — any field it strips that transferClassA does not null is a gap), and does nulling `digDeeperMd` orphan or strand a dig-deeper blob / dig state?

## Part B — hunt for NEW defects the fixes introduced or exposed
The fix commit is a non-trivial rewrite of the reconcile write path. Look for:
- Baseline-advance correctness across ALL branches now (advance / carry-previous / placeholder / skip) — any branch that advances a baseline without a corresponding durable write, or fails to advance for a "seen" video (breaking delete-inference → a spurious delete next run).
- Money-safety: no new path enqueues, consumes `spend_ledger`, or resurrects regenerable cache. `needsRegen` must be a REPORT flag only, never a trigger.
- Atomicity: durable-before-advertise, manifest-after-commit still holds on every path.
- Idempotency: run sync twice on each new branch — does run 2 do the same thing (no oscillation, no sticky false agreement)?
- Cross-backend (local vs Supabase) semantic mismatches — the round-1 `transferClassA` promote-vs-put bug is the archetype; the null-invalidation question above is a live candidate sibling.
- RLS / no-service-role on the sync path is unchanged.

## Scope
Review the SHIPPED final state at HEAD (`32a164c`), not intermediate commits. Key files: `lib/cloud-sync/*.ts` (esp. `sync-run.ts`), `supabase/migrations/0021_cloud_sync_signals.sql` and `0009_*` (persist_summary / merge_video_data bodies), `lib/storage/local/local-metadata-store.ts`, `lib/storage/supabase/supabase-metadata-store.ts`, `lib/html-doc/*`, tests under `tests/lib/cloud-sync/` and `tests/integration/cloud-sync/`. Spec (authoritative): `docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

KNOWN-and-ACCEPTED (do NOT re-report unless you show they mask a real bug): T14-M1 (put→updateVideoFields two non-txn writes, self-healing), T14-M2 (no failCloudPut fault test for two-sided transfer), T5 test-coverage gaps, T4 automock comment inaccuracy.

## Output
For each finding: severity (Blocking/High/Medium/Low), `file:line`, the concrete failure scenario (inputs → wrong outcome), and the fix. Money-path or atomicity holes are Blocking/High. For Part A, state explicitly per fix: GENUINELY FIXED / INCOMPLETE / NOT FIXED with evidence. End with **CONVERGED** (no new Blocking/High) or **NOT CONVERGED**.

codex
I’m using the diagnose/review posture here: first I’ll verify the three named fixes against HEAD and the authoritative spec, then I’ll do a second pass for regressions across the rewritten sync paths.
exec
/bin/bash -lc "sed -n '1,280p' lib/cloud-sync/sync-run.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
// lib/cloud-sync/sync-run.ts
//
// Stage 3 Cloud Sync (§7) — the sync-run orchestrator. Composes the reconcile primitives (T1/T5–T9,
// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
// cloud, one playlist at a time, under an authenticated USER session (never service-role).
//
// Invariants (any violation = money/data bug):
//  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
//    cache (summaryHtml/dig/PDF) copied.
//  - Cloud Principal.id = deps.ownerId (= auth.uid()): Supabase Storage RLS (0007) requires the
//    first object-path segment to equal auth.uid(); the metadata RPCs are owner_id = auth.uid()
//    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
//  - Transfers finalize the receiver record via updateVideoFields (SyncDeps exposes no raw client,
//    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
//    tuple is verified durable — stage → verify → promote → finalize → verify → baseline (F2).
//  - Class B is reconciled BEFORE Class A (Class A consumes the reconciled corrections hash);
//    a Class-B loser write is asserted to have landed (found:true) or it throws (F3).

import { promises as fs } from 'fs';
import path from 'path';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { BlobStore } from '@/lib/storage/blob-store';
import type { Principal } from '@/lib/storage/principal';
import { localPrincipal } from '@/lib/storage/principal';
import type { Video } from '@/types';
import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
import { reconcileHuman, type FieldMerge } from './reconcile-class-b';
import { reconcileClassA } from './reconcile-class-a';
import { decideCompanion } from './companion';
import {
  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
} from './manifest';
import { discoverLocalPlaylists, unionPlaylistKeys, type LocalPlaylist } from './registry';
import { mdHash } from './content-hash';
import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
import type { PlaylistSummary } from '@/lib/storage/metadata-store';
import type { ClassASignals, HumanField, HumanSnapshot, VideoBaseline } from './types';

export interface SyncDeps {
  local: MetadataStore; cloud: MetadataStore;
  localBlob: BlobStore; cloudBlob: BlobStore;
  dataRoots: string[]; ownerId: string;
}

export interface SyncReport {
  created: number; updatedLocal: number; updatedCloud: number; skippedIdentical: number;
  mergedFields: number; conflictsLogged: number; removed: number;
  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
  errors: { videoId: string; message: string }[];
}

const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
const EMPTY_CLASSB = {} as VideoBaseline['classB'];

/** One replica's write surface for a video (store + its principal + its blob store). */
interface Side { store: MetadataStore; p: Principal; blob: BlobStore; }

/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
  if (!video.summaryMd) return null;
  const buf = await blob.get(p, video.summaryMd);
  return buf ? buf.toString('utf8') : null;
}

/** Union of video ids across both replicas' indexes. */
async function enumerateVideoIds(
  local: MetadataStore, cloud: MetadataStore, localP: Principal, cloudP: Principal,
): Promise<string[]> {
  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
  return [...new Set([...l.videos.map((v) => v.id), ...c.videos.map((v) => v.id)])];
}

/** Read one video record (or null if absent) from a store's index. */
async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
  const idx = await store.readIndex(p);
  return idx.videos.find((v) => v.id === id) ?? null;
}

/** Deterministic local root for a cloud-only playlist (fresh-device hydrate target). */
function hydrationRoot(dataRoots: string[], key: string): string {
  return path.join(dataRoots[0], key);
}

/** mkdir -p the playlist's local root BEFORE any local read/write (round-5 H1). On a fresh device a
 *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
 *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
 *  writeIndex ENOENT into a missing parent. */
async function ensureHydrationRoot(dataRoot: string): Promise<void> {
  await fs.mkdir(dataRoot, { recursive: true });
}

/** Resolve the playlist url/title for `key` from whichever registry holds it. */
function playlistMetaFor(
  key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
): { playlistUrl: string; playlistTitle?: string } {
  const lp = localPlaylists.find((l) => l.playlistKey === key);
  if (lp) return { playlistUrl: lp.playlistUrl };
  const cp = cloudSummaries.find((c) => c.playlistKey === key);
  if (cp) return { playlistUrl: cp.playlistUrl, ...(cp.playlistTitle ? { playlistTitle: cp.playlistTitle } : {}) };
  return { playlistUrl: '' };
}

/** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
 *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
function sanitizeAdditiveVideo(video: Video): Video {
  const v: any = { ...video };
  v.summaryHtml = null;
  v.digDeeperHtml = null;
  v.digDeeperMd = null;
  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
  if (v.artifacts && typeof v.artifacts === 'object') {
    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
  }
  // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
  delete v.serialNumber;
  delete v.playlistIndex;
  delete v.removedFromPlaylist;
  // DB-computed read-only fields must never round-trip into a write.
  delete v.updatedAt;
  delete v.summaryReady;
  return v as Video;
}

/** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
 *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
 *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
 *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
async function ensureReceiverSlot(
  to: MetadataStore, toP: Principal,
  playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
): Promise<{ position: number; serialNumber: number } | null> {
  await to.setPlaylistMeta(toP, playlistMeta);
  const idx = await to.readIndex(toP);
  if (idx.videos.some((v) => v.id === video.id)) return null;
  return to.claimVideoSlot(toP, video.id);
}

/** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
 *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
 *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
 *  never copies regenerable cache. */
async function copyAdditiveVideo(
  to: MetadataStore, toP: Principal, toBlob: BlobStore,
  playlistMeta: { playlistUrl: string; playlistTitle?: string },
  video: Video, mdBody: string | null,
): Promise<void> {
  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);

  let wroteBlob = false;
  if (video.summaryMd) {
    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
    // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
    // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
    // strand the receiver with a servable-looking row backed by nothing.
    if (mdBody == null) {
      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
    }
    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
    const staged = await toBlob.get(toP, ref.tempKey);
    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
      throw new Error(`additive staged MD verify failed for ${video.id}`);
    }
    await toBlob.promote(ref);
    wroteBlob = true;
  }

  const sanitized: any = sanitizeAdditiveVideo(video);
  if (slot) {
    sanitized.serialNumber = slot.serialNumber;
    sanitized.playlistIndex = slot.position + 1;
  }
  if (wroteBlob) {
    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
    delete sanitized.artifacts.summaryMd;
  }
  await to.upsertVideo(toP, sanitized as Video);

  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
  // (an update against an absent row silently no-ops; never advance a baseline for that).
  const after = await to.readIndex(toP);
  const rec = after.videos.find((v) => v.id === video.id);
  if (!rec) {
    throw new Error(`additive create did not persist receiver row for ${video.id}`);
  }
  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
  if (wroteBlob) {
    const art = (rec as any).artifacts?.summaryMd;
    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
    }
  }
}

/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
 *  side's values, so this is a true agreed baseline. */
function baselineFromOneSided(
  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
): VideoBaseline {
  const classB = {} as VideoBaseline['classB'];
  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
  return {
    classA: {
      docVersionMajor: classA.docVersionMajor,
      mdGeneratedAt: classA.mdGeneratedAt,
      mdCorrectionsHash: classA.mdCorrectionsHash,
      mdHash: mdHashVal,

exec
/bin/bash -lc "sed -n '1,320p' docs/reviews/whole-branch-cloud-sync-v2-rereview-claude.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
# Whole-branch re-review (ROUND 2, Claude adversarial) — `feat/stage3-cloud-sync`

Scope: shipped state at HEAD `32a164c`. Read-only review. Authoritative spec:
`docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md`.

Test baseline at HEAD: `npx jest tests/lib/cloud-sync tests/integration/cloud-sync` →
**15 suites / 85 tests passed**.

Known-and-accepted (not re-reported): T14-M1, T14-M2, T5 coverage gaps, T4 automock comment.

---

## Part A — verification of the round-1 fixes

### WB-B1 (Blocking) — corrections no-write conflict drove a destructive Class-A copy
**Verdict: GENUINELY FIXED.**

Guard at `lib/cloud-sync/sync-run.ts:471-477`.

- **Precision of the trigger.** `merges.corrections.winner === 'equal' && merges.corrections.conflict`
  is reachable from exactly one place: `lib/cloud-sync/reconcile-class-b.ts:43-45`, which is guarded by
  `local.value !== cloud.value` (line 27 returns early on equal values, always with `conflict: false`).
  So the guard cannot false-fire on identical corrections. Correct.
- **Is the guard before every write path?** Yes. The `continue` at line 476 precedes `deriveClassASignals`
  (480-481), `reconcileClassA` (482), both `transferClassA` calls (493, 497) and `companionTransfer` (505).
  There is no other write surface between line 461 and the end of the loop body. `applyClassBWinners`
  (456) runs *before* the guard, which is correct and intentional — Class B is a separate class and a
  `winner === 'equal'` field is skipped inside `applyClassBWinners` at line 245 anyway.
- **Does `continue` skip anything that must still run?**
  - Delete-inference "seen" marking: preserved — `writeVideoBaseline` runs at line 475, so `manifest.videos[id]`
    exists next run and the video is not mis-inferred as a delete. ✅
  - Archived reporting: explicitly re-added at line 474 (mirrors line 508). ✅
  - Companion transfer: correctly skipped — no MD moved, so the loser's model is not stale. ✅
  - Report counters: `skippedIdentical` is not incremented. That is defensible (nothing was compared),
    and no consumer branches on it (`app/.../cloud-sync` CLI only prints). Not a defect.
- **Does the first-sync placeholder baseline mislead a consumer?** No. I grepped every reader of
  `VideoBaseline.classA`: the only references are the three *writers* in `sync-run.ts` (207-217, 370-375,
  391-392) and the type declaration at `lib/cloud-sync/types.ts:32`. `reconcileClassA`
  (`lib/cloud-sync/reconcile-class-a.ts:11-15`) takes only `{local, cloud, reconciledCorrectionsHash}` —
  no baseline parameter. `reconcileHuman` consumes only `base?.classB`. **The Class-A baseline is
  write-only.** The `docVersionMajor: 0 / mdHash: null` placeholder is therefore inert; next run
  re-derives from the live bodies. The code comment at 384-386 is accurate.
- **Idempotency:** second run re-derives the same conflict → same skip → same baseline. The e2e test at
  `tests/integration/cloud-sync/e2e.int.test.ts:392-437` asserts exactly this across two runs, including
  that both MD blobs and both `corrections` values are byte-preserved and `spendLedgerTotal` is unchanged.

### WB-H1 (High) — additive create could advertise `promoted` with no blob
**Verdict: GENUINELY FIXED** (with one Low on residual partial state, below).

`lib/cloud-sync/sync-run.ts:153-201`. Three layers, all real:
throw on `summaryMd && mdBody == null` (158-160); strip a residual `artifacts.summaryMd` when no blob was
written (178-183); post-write assert that the persisted row advertises `status === 'promoted'` at the
**right key** (196-201).

- **`summaryMd == null` path still correct.** `video.summaryMd` falsy → no throw, `wroteBlob` stays false →
  the `else if` strips any residual pointer → row lands with no summary artifact. Row 13 (summary-less
  video) behaves as specified.
- **Does the strict post-write assert behave differently across backends?** No — and this is the
  right shape for both. Local: `LocalFsMetadataStore.upsertVideo` → `indexStore.upsertVideo`, and
  `sanitized.artifacts` is a whole-object replace, so `artifacts.summaryMd` lands verbatim. Cloud:
  `upsertVideo` goes through `.update({ data: stripComputed(video) })`
  (`lib/storage/supabase/supabase-metadata-store.ts:109`) — a **whole-`data` replace**, not
  `merge_video_data`, so there is no deep-merge asymmetry on this path. The assert reads back via
  `readIndex` on both, so it verifies the *persisted* representation either way. ✅
- **Partial state after the throw** — see Part B L1. It is self-healing; not a High.

### WB-H2 (High) — two-sided transfer left stale rendered HTML
**Verdict: FIXED for `summaryHtml`/`digDeeperHtml`, but the fix OVERREACHES on `digDeeperMd` → see
Part B **H1** (new High).**

I traced whether a JSON `null` actually persists on each backend, as instructed:

- **Cloud.** `transferClassA` → `loser.store.updateVideoFields` →
  `supabase-metadata-store.ts:123-137` → `stripComputed(fields)`, which is a destructuring rest
  (`:18-21`) that removes only `updatedAt`/`summaryReady` — **it does not drop nulls**. PostgREST
  serializes the JSON null through. In `merge_video_data`
  (`supabase/migrations/0021_cloud_sync_signals.sql`), the first term is
  `data || (p_fields - 'artifacts')`. Postgres `jsonb ||` **sets the key to JSON null** rather than
  dropping it (`'{"a":1}'::jsonb || '{"a":null}'::jsonb` → `{"a": null}`). Only `jsonb_strip_nulls`
  drops nulls, and it is used in `persist_summary`, not here. **Null is stored.** ✅
- **Local.** `LocalFsMetadataStore.updateVideoFields` → `indexStore.updateVideoFields`
  (`lib/index-store.ts:132-146`), which does `{ ...index.videos[i], ...safeFields }` — a shallow spread,
  so `summaryHtml: null` overwrites — then `writeIndex` → `JSON.stringify`, which preserves `null`
  (only `undefined` is dropped). **Null is stored.** ✅
- **Consumers read it as falsy.** `lib/html-doc/eligibility.ts:12` (`!v.summaryHtml`) and
  `lib/html-doc/ensure.ts:54` (`else if (!video.summaryHtml)`) both branch on falsiness, so a JSON null
  forces a full re-render. The fix is **not** cosmetic. ✅
- **Comparison against `sanitizeAdditiveVideo`'s strip list** (`sync-run.ts:107-124`), as instructed:

  | field | `sanitizeAdditiveVideo` | `transferClassA` | assessment |
  |---|---|---|---|
  | `summaryHtml` | null | null (314) | ✅ match |
  | `digDeeperHtml` | null | null (315) | ✅ match |
  | `digDeeperMd` | null | null (316) | ❌ **wrong on this path** — Part B H1 |
  | `artifacts.*` except `summaryMd` | dropped (113-115) | **not cleared** (319) | see Part B M1 |
  | `serialNumber`/`playlistIndex`/`removedFromPlaylist` | deleted | not sent | ✅ correct (replica-local) |

  The commit comment "Matches `sanitizeAdditiveVideo`, which already nulls these" is the flawed premise:
  `sanitizeAdditiveVideo` shapes a record for a receiver that has **no row yet** (nothing to destroy),
  while `transferClassA` patches a receiver row that **already holds its own state**. The two are not
  interchangeable, and `digDeeperMd` is where that difference bites.

---

## Part B — new findings

### H1 (High) — `transferClassA` nulls `digDeeperMd`, orphaning the loser's paid dig-deeper doc
**`lib/cloud-sync/sync-run.ts:316`**

`digDeeperMd` is not a regenerable render cache — on the local backend it is the **filename pointer to a
Gemini-generated dig-deeper markdown file**, written by `lib/dig/dig-section.ts:104-106`, produced by
`lib/dig/generate.ts` against `gemini-2.5-pro` (`generate.ts:23`, and note `:115` — "Local dig (no opts)
stays on gemini-2.5-pro"). It is **paid content**. `summaryHtml` and `digDeeperHtml` are free re-renders;
`digDeeperMd` is not.

**Scenario (concrete):**
1. A user digs several sections locally → `index.json` has `digDeeperMd: "foo-dig-deeper.md"` and the file
   exists on disk.
2. The same video is regenerated in the cloud at a higher `docVersion.major` (an ordinary, expected event).
3. `reconcileClassA` (`reconcile-class-a.ts:43-46`, format axis, "never downgrade") returns `copyToLocal`.
4. `transferClassA(cloudSide, localSide, …)` sends `digDeeperMd: null` in `completeTuple` (316) →
   `indexStore.updateVideoFields` shallow-spread → `index.json` now has `digDeeperMd: null`.

**Wrong outcome:** every consumer of the local dig doc goes dark while the file sits orphaned on disk —
`app/api/videos/[id]/dig-state/route.ts:92-93` returns "no dig", `components/VideoMenu.tsx:174`
(`!cloudMode && video.digDeeperMd`) hides the menu entry, `lib/html-doc/build-doc-html.ts:75,86` stops
merging it, `lib/pdf/pdf-path.ts:19` throws `no dig-deeper doc for this video`. To recover, the user must
re-dig → **fresh Gemini spend for content they already paid for**. Recovery is not automatic: nothing in
the sync path ever re-derives `digDeeperMd` from the filesystem.

This also violates scope: the spec puts dig **out of scope for M2a** (`§ line 35`, "Out of scope (M2a):
deep-dive/dig + slide images (M2b, §13)"). Sync must leave dig state untouched, not destroy it.

Note this is a **regression introduced by the WB-H2 fix** — before `32a164c` the field was not sent at all.

**Fix:** delete the `digDeeperMd: null` line (316). Keep `summaryHtml: null` and `digDeeperHtml: null` —
those are correct: `digDeeperHtml` is the *rendered merge* of summary + dig, so a summary-body change does
stale it, and `lib/html-doc/eligibility.ts:23` (`!!v.summaryMd && !v.digDeeperMd`) plus
`build-doc-html.ts:86` re-render it for free **from the preserved `digDeeperMd`**. Add a regression test —
there is currently zero coverage: `grep -rn digDeeperMd tests/lib/cloud-sync tests/integration/cloud-sync`
returns nothing.

### M1 (Medium) — `transferClassA` leaves stale non-`summaryMd` artifact pointers on the loser
**`lib/cloud-sync/sync-run.ts:319`**

`merge_video_data` deep-merges `artifacts` by design
(`0021_cloud_sync_signals.sql`: `coalesce(data->'artifacts','{}') || (p_fields->'artifacts')`), so sending
`artifacts: { summaryMd: … }` **preserves** every other key already on the loser row. Any non-`summaryMd`
artifact the loser holds (written via `lib/storage/supabase/consistency.ts:34,40`, whose `opts.kind` is
generic) survives a transfer that replaced the MD body it was derived from.
`sanitizeAdditiveVideo:113-115` drops exactly these; `transferClassA` does not.

Today the practical blast radius is small — the artifacts map is dominated by `summaryMd`, and the
regenerable HTML is gated on the top-level `summaryHtml`, which *is* nulled. Hence Medium, not High. But
the asymmetry with `sanitizeAdditiveVideo` is unintentional and will become a real staleness bug as soon
as a second artifact kind (pdf/slide/modelJson) is populated on the cloud path. Either clear the
non-`summaryMd` keys explicitly or record the divergence as a deliberate, documented decision.

### M2 (Medium) — the WB-B1 guard also blocks purely-additive (non-destructive) MD hydration
**`lib/cloud-sync/sync-run.ts:471-477`**

The guard skips Class A **unconditionally**, including the sub-case where the loser has no MD at all.

**Scenario:** cloud row has `summaryMd` + a promoted blob; the local row exists (so this is the two-sided
path, not the additive path) but has `summaryMd == null`; both sides carry a *backfilled* corrections
conflict (legacy records, per §5.5). Pre-fix, `reconcileClassA:22` (`if (!lHas) return copyToLocal`) would
hydrate local. Post-fix the video is skipped every run, forever, until a human edits corrections on one
side to produce a real `annotationsEditedAt`.

Nothing is destroyed and `needsRegen` is reported each run, so this is safe-but-stuck rather than a
correctness bug — Medium. Consider narrowing the guard to the genuinely destructive case (both sides have
an MD body, i.e. `la.mdHash != null && ca.mdHash != null`), which preserves the WB-B1 fix's intent exactly
while letting one-sided hydration through.

### L1 (Low) — the WB-H1 throw leaves a bare receiver slot; converges, but via a different code path
**`lib/cloud-sync/sync-run.ts:150` then `158-160`**

`ensureReceiverSlot` runs (150) *before* the new throw (158), so `claimVideoSlot` has already inserted a
minimal row (`local-metadata-store.ts:27`: `{ id: videoId, serialNumber } as Video`). The throw is caught
at 513-515, no baseline is written.

I traced the next run and it **does not corrupt anything**: both sides now read as present, so the video
takes the two-sided path; `deriveClassASignals` on the bare row yields `mdHash: null`, so
`reconcile-class-a.ts:22` returns `copyToLocal`, and `transferClassA:273-275` throws again
(`winner … has no MD body to copy`) while the cloud blob is still unreadable — then heals cleanly once it
is. No zod validation runs on `readIndex` (`lib/index-store.ts:81-98` is a bare `JSON.parse`), so the bare
row does not poison the index read. Delete-inference is safe (both sides present, no baseline).

Residual cosmetic effects only: `report.created` is never incremented for this video (it heals via the
two-sided path), and a permanently-missing cloud blob produces one `report.errors` entry per run — which
is the desired surfacing. Worth a comment at 158 noting the deliberate slot-then-throw ordering.

---

## Items explicitly checked and found clean

- **Money-safety.** No `enqueue`/producer import, no `spend_ledger` touch, no reserve/release anywhere in
  `lib/cloud-sync/*`. `needsRegen` is written only to `report.needsRegen` (483, 473) and never read as a
  trigger. The WB-B1 e2e test asserts `spendLedgerTotal()` is unchanged across the run.
  *(H1 above is a money finding of a different kind — it forces the user to re-spend, rather than the sync
  spending itself.)*
- **Baseline-advance across all four branches.** additive (444-447, after the row-existence + promoted
  asserts), transfer (512, after `transferClassA` resolves), skip (512, N4), corrections-unresolved (475).
  Every advance is preceded by a durable write or a verified no-op. No branch advances a baseline for an
  unwritten change, and every "seen" video gets a baseline, so no spurious delete inference.
- **Durable-before-advertise.** `transferClassA:279-292` stages → verifies the hash → `put`s the verified
  bytes at the final key (with the documented rationale for `put` over `promote`, given
  `SupabaseBlobStore.promote` is create-if-absent) → only then `updateVideoFields` advertises `promoted`.
  Manifest strictly after. Unchanged and still correct.
- **Cross-backend semantics.** Checked the three write paths that differ (`upsertVideo` = whole-`data`
  replace on cloud vs object replace on local; `updateVideoFields` = `merge_video_data` deep-merge on
  cloud vs shallow spread on local; null persistence on both). The only surviving mismatch is M1 above.
- **RLS / no service-role.** `SyncDeps` exposes no raw client; `cloudP.id = deps.ownerId` (419);
  `merge_video_data` and `update_video_annotations` are `security invoker` with `auth.uid()` guards.
  Unchanged by `32a164c`.
- **Idempotency.** Ran each new branch twice mentally; WB-B1 is additionally covered by an explicit
  two-run assertion in the e2e test. No oscillation, no sticky false agreement.

---

**NOT CONVERGED** — 1 new High (H1: `digDeeperMd: null` destroys the local loser's paid dig-deeper doc, a
regression introduced by the WB-H2 fix), plus 2 Mediums and 1 Low. Another round is required after H1 is
fixed.

---

## Coordinator adjudication (post-review, 2026-07-18)

The two round-2 reviewers DISAGREED on the severity of the additive slot-ordering defect:
Codex rated it **High**; this review rated it **L1 (Low)**. I adjudicated against the code.

**Codex is correct; L1 above is WRONG and is superseded.**

L1 reasons that on run 2 the video takes `reconcile-class-a.ts:22` (`if (!lHas) return copyToLocal`)
and throws again in `transferClassA`. That requires `cHas === true`. It is not: `deriveClassASignals`
derives `mdHash` from the **MD body**, not the key —
`lib/cloud-sync/backfill.ts:11`: `mdHash: mdBody != null ? mdHash(mdBody) : null`.
The premise of the scenario is that the cloud blob is UNREADABLE, so `readMdBody` returns null and the
cloud side hashes to `null` as well. Both sides null → `reconcile-class-a.ts:21`
(`if (!lHas && !cHas) return { action: 'skip' }`) → `runSync` WRITES a manifest baseline (~:512).

Net effect: the corruption is surfaced in `report.errors` exactly once, then laundered into a false
"seen and agreed no-MD" baseline — the video is thereafter treated as reconciled. That is a
**High**, tracked as **H-R2-1**, and is being fixed by validating the MD body BEFORE
`ensureReceiverSlot` claims the slot (no partial state → nothing to roll back).

Lesson for round 3: the single-run WB-H1 e2e test passed while this bug was live. Assertions about
baseline/idempotency effects require running `runSync` TWICE — as the WB-B1 test already does.

exec
/bin/bash -lc 'git show --stat --oneline --decorate --no-renames 1f54c60 && git show --no-ext-diff --unified=80 --no-renames 1f54c60 -- lib/cloud-sync/sync-run.ts tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
1f54c60 (HEAD -> feat/stage3-cloud-sync) fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
 docs/reviews/whole-branch-cloud-sync-codex.md      | 7531 ++++++++++++++++++++
 .../whole-branch-cloud-sync-v2-rereview-claude.md  |  248 +
 .../whole-branch-cloud-sync-v2-rereview-codex.md   | 3174 +++++++++
 lib/cloud-sync/sync-run.ts                         |   55 +-
 tests/integration/cloud-sync/e2e.int.test.ts       |   86 +-
 5 files changed, 11076 insertions(+), 18 deletions(-)
commit 1f54c60e6ff86d9191bc6601defa5a2a890c852c
Author: Kujin Lee <kujinlee@gmail.com>
Date:   Sat Jul 18 08:49:27 2026 -0700

    fix(cloud-sync): round-2 whole-branch re-review — validate before slot claim, preserve paid digDeeperMd, narrow corrections guard (H-R2-1/H-R2-2/M-R2-2)
    
    Round-2 dual adversarial re-review of the round-1 fixes (32a164c). Part A confirmed
    WB-B1 and WB-H2 genuinely fixed; WB-H1 was INCOMPLETE and WB-H2 introduced a regression.
    
    H-R2-1 (High) — copyAdditiveVideo claimed the receiver slot BEFORE validating the MD
    body, so an unreadable source blob left a bare row behind on the throw. The next run
    then saw a two-sided video whose both sides derive mdHash === null, reconcileClassA
    returned 'skip', and runSync wrote a manifest baseline — laundering the corruption into
    a false "seen and agreed no-MD" state. The guard now runs first, so no partial state is
    created. The e2e test now runs sync TWICE; the single-run assertions all passed while
    the bug was live.
    
    H-R2-2 (High, regression from the WB-H2 fix) — transferClassA nulled digDeeperMd, which
    is not a render cache but the pointer to a PAID Gemini-generated dig-deeper doc. An
    ordinary higher-docVersion transfer orphaned the file and darkened dig-state/VideoMenu/
    build-doc-html/pdf-path, costing fresh spend to recover. Only the two HTML caches are
    cleared now; digDeeperHtml re-renders free from the preserved digDeeperMd.
    
    M-R2-2 (Medium) — the WB-B1 corrections guard skipped Class A unconditionally, stranding
    purely-additive hydration (loser holds no MD) forever. Narrowed to the destructive case
    (both sides hold an MD body); signal derivation hoisted above the guard (pure).
    
    Deferred with owner: stale non-summaryMd artifact pointers on transfer; absent companion
    scalars not explicitly cleared.
    
    Verification: tsc clean; 2421 unit / 245 suites green; cloud-sync integration 35/35
    (4 suites). Pre-existing, unrelated: reservation-release.test.ts fails identically on a
    clean tree (local Supabase state pollution) — tracked separately.
    
    Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>
    Claude-Session: https://claude.ai/code/session_01EfbFViKSSM27WJ5dSchemY

diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index b771403..a031c2a 100644
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -70,451 +70,478 @@ async function enumerateVideoIds(
   return [...new Set([...l.videos.map((v) => v.id), ...c.videos.map((v) => v.id)])];
 }
 
 /** Read one video record (or null if absent) from a store's index. */
 async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
   const idx = await store.readIndex(p);
   return idx.videos.find((v) => v.id === id) ?? null;
 }
 
 /** Deterministic local root for a cloud-only playlist (fresh-device hydrate target). */
 function hydrationRoot(dataRoots: string[], key: string): string {
   return path.join(dataRoots[0], key);
 }
 
 /** mkdir -p the playlist's local root BEFORE any local read/write (round-5 H1). On a fresh device a
  *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
  *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
  *  writeIndex ENOENT into a missing parent. */
 async function ensureHydrationRoot(dataRoot: string): Promise<void> {
   await fs.mkdir(dataRoot, { recursive: true });
 }
 
 /** Resolve the playlist url/title for `key` from whichever registry holds it. */
 function playlistMetaFor(
   key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
 ): { playlistUrl: string; playlistTitle?: string } {
   const lp = localPlaylists.find((l) => l.playlistKey === key);
   if (lp) return { playlistUrl: lp.playlistUrl };
   const cp = cloudSummaries.find((c) => c.playlistKey === key);
   if (cp) return { playlistUrl: cp.playlistUrl, ...(cp.playlistTitle ? { playlistTitle: cp.playlistTitle } : {}) };
   return { playlistUrl: '' };
 }
 
 /** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
  *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
  *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
  *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
 function sanitizeAdditiveVideo(video: Video): Video {
   const v: any = { ...video };
   v.summaryHtml = null;
   v.digDeeperHtml = null;
   v.digDeeperMd = null;
   // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
   if (v.artifacts && typeof v.artifacts === 'object') {
     v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
   }
   // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
   delete v.serialNumber;
   delete v.playlistIndex;
   delete v.removedFromPlaylist;
   // DB-computed read-only fields must never round-trip into a write.
   delete v.updatedAt;
   delete v.summaryReady;
   return v as Video;
 }
 
 /** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
  *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
  *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
  *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
  *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
 async function ensureReceiverSlot(
   to: MetadataStore, toP: Principal,
   playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
 ): Promise<{ position: number; serialNumber: number } | null> {
   await to.setPlaylistMeta(toP, playlistMeta);
   const idx = await to.readIndex(toP);
   if (idx.videos.some((v) => v.id === video.id)) return null;
   return to.claimVideoSlot(toP, video.id);
 }
 
 /** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
  *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
  *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
  *  never copies regenerable cache. */
 async function copyAdditiveVideo(
   to: MetadataStore, toP: Principal, toBlob: BlobStore,
   playlistMeta: { playlistUrl: string; playlistTitle?: string },
   video: Video, mdBody: string | null,
 ): Promise<void> {
+  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
+  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
+  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
+  // strand the receiver with a servable-looking row backed by nothing.
+  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
+  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
+  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
+  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
+  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
+  // partial state is ever created, so there is nothing to roll back.
+  if (video.summaryMd && mdBody == null) {
+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
+  }
+
   const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
 
   let wroteBlob = false;
-  if (video.summaryMd) {
-    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
-    // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
-    // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
-    // strand the receiver with a servable-looking row backed by nothing.
-    if (mdBody == null) {
-      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
-    }
+  if (video.summaryMd && mdBody != null) {
     // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
     const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
     const staged = await toBlob.get(toP, ref.tempKey);
     if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
       throw new Error(`additive staged MD verify failed for ${video.id}`);
     }
     await toBlob.promote(ref);
     wroteBlob = true;
   }
 
   const sanitized: any = sanitizeAdditiveVideo(video);
   if (slot) {
     sanitized.serialNumber = slot.serialNumber;
     sanitized.playlistIndex = slot.position + 1;
   }
   if (wroteBlob) {
     sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
     // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
     // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
     // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
     delete sanitized.artifacts.summaryMd;
   }
   await to.upsertVideo(toP, sanitized as Video);
 
   // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   // (an update against an absent row silently no-ops; never advance a baseline for that).
   const after = await to.readIndex(toP);
   const rec = after.videos.find((v) => v.id === video.id);
   if (!rec) {
     throw new Error(`additive create did not persist receiver row for ${video.id}`);
   }
   // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   if (wroteBlob) {
     const art = (rec as any).artifacts?.summaryMd;
     if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
       throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
     }
   }
 }
 
 /** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
  *  side's values, so this is a true agreed baseline. */
 function baselineFromOneSided(
   classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
 ): VideoBaseline {
   const classB = {} as VideoBaseline['classB'];
   for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   return {
     classA: {
       docVersionMajor: classA.docVersionMajor,
       mdGeneratedAt: classA.mdGeneratedAt,
       mdCorrectionsHash: classA.mdCorrectionsHash,
       mdHash: mdHashVal,
     },
     classB,
   };
 }
 
 /** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
  *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
  *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
  *  write on an absent row would let buildBaseline record a false agreement. */
 async function applyClassBWinners(args: {
   deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   dataRoot: string; key: string;
 }): Promise<{ merged: number; conflicts: number }> {
   const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   let merged = 0;
   let conflicts = 0;
 
   for (const f of FIELDS) {
     const m = merges[f];
     if (m.conflict) {
       await appendConflict(dataRoot, key, {
         video_id: videoId, class: 'B', field: f,
         valueL: localSnap[f].value, valueR: cloudSnap[f].value,
         reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
       });
       conflicts += 1;
     }
     if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
 
     // winner is on one side → the OTHER (loser) side receives the winning value.
     const target: Side = m.winner === 'local'
       ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
       : { store: deps.local, p: localP, blob: deps.localBlob };
     const set: Record<string, string | number> = {};
     const clear: HumanField[] = [];
     if (m.value === undefined) clear.push(f);
     else set[f] = m.value;
 
     const { found } = await target.store.updateVideoAnnotations(
       target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
     );
     if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
     merged += 1;
   }
   return { merged, conflicts };
 }
 
 /** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
  *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
  *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
  *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
 async function transferClassA(
   winner: Side, loser: Side, winnerVideo: Video, videoId: string,
 ): Promise<{ mdHash: string; verified: boolean }> {
   const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   if (body == null || !winnerVideo.summaryMd) {
     throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   }
   const h = mdHash(body);
   const key = winnerVideo.summaryMd;
 
   const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   const staged = await loser.blob.get(loser.p, ref.tempKey);
   if (!staged || mdHash(staged.toString('utf8')) !== h) {
     throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   }
   // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   // (below) advertises promoted only after this resolves.
   await loser.blob.put(loser.p, key, staged, 'text/markdown');
   await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
 
   const wv: any = winnerVideo;
   const completeTuple: any = {
     summaryMd: key,
     docVersion: wv.docVersion,
     mdGeneratedAt: wv.mdGeneratedAt ?? null,
     mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
     ratings: wv.ratings,
     overallScore: wv.overallScore,
     videoType: wv.videoType,
     audience: wv.audience,
     tags: wv.tags,
     tldr: wv.tldr,
     takeaways: wv.takeaways,
     // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
     // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
     // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
     // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
     // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
-    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
+    // readIndex reads falsy → forces re-render.
+    //
+    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
+    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
+    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
+    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
+    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
+    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
+    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
+    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
+    // whereas transferClassA PATCHES a row that already holds its own state.
     summaryHtml: null,
     digDeeperHtml: null,
-    digDeeperMd: null,
     // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
     // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
     artifacts: { summaryMd: { key, status: 'promoted' } },
   };
   await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
 
   return { mdHash: h, verified: true };
 }
 
 /** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
  *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
  *  that the owner must re-serve to regenerate the share model. */
 async function companionTransfer(
   winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
 ): Promise<{ shareNeedsOwnerServe: boolean }> {
   if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
   const decision = decideCompanion({ winnerMdHash, senderEnvelope });
   if (decision.kind === 'ship') {
     await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
     return { shareNeedsOwnerServe: false };
   }
   // deleteReceiverModel — best-effort; a missing model blob is not an error.
   try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   return { shareNeedsOwnerServe: true };
 }
 
 /** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
  *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
  *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
  *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
  *  recording the winner there would be a false agreement → next-run silent overwrite). */
 function buildClassBBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline['classB'] {
   const classB = {} as VideoBaseline['classB'];
   for (const f of FIELDS) {
     const m = merges[f];
     if (m.winner === 'equal' && m.conflict) {
       classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
     } else {
       classB[f] = { value: m.value, editedAt: m.editedAt };
     }
   }
   return classB;
 }
 
 function buildBaseline(
   winnerSignals: ClassASignals, winnerMdHash: string | null,
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: {
       docVersionMajor: winnerSignals.docVersionMajor,
       mdGeneratedAt: winnerSignals.mdGeneratedAt,
       mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
       mdHash: winnerMdHash,
     },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 /** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
  *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
  *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
  *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
  *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
  *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
  *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
 function buildCorrectionsUnresolvedBaseline(
   merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
 ): VideoBaseline {
   return {
     classA: previousBaseline?.classA
       ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
     classB: buildClassBBaseline(merges, previousBaseline),
   };
 }
 
 export async function runSync(
   deps: SyncDeps, opts: { playlistKey?: string } = {},
 ): Promise<SyncReport> {
   resetConflictDedup();
   const report: SyncReport = {
     created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
     mergedFields: 0, conflictsLogged: 0, removed: 0,
     shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   };
 
   const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
 
   for (const key of keys) {
     const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
       ?? hydrationRoot(deps.dataRoots, key);
     await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
 
     const localP = localPrincipal(dataRoot);
     const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
     const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
     const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
     const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
     const manifest = await readManifest(dataRoot, key);
 
     for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
       try {
         const lv = await readVideo(deps.local, localP, id);
         const cv = await readVideo(deps.cloud, cloudP, id);
         const base = manifest.videos[id];
 
         // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
         //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
         if (!lv || !cv) {
           const present = (lv ?? cv)!;
           const presentIsLocal = lv != null;
           if (base) {
             report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
           } else {
             const from: Side = presentIsLocal ? localSide : cloudSide;
             const to: Side = presentIsLocal ? cloudSide : localSide;
             const body = await readMdBody(from.blob, from.p, present);
             await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
             report.created += 1; // reached only after the receiver row is confirmed
             await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
               deriveClassASignals(present, body), body ? mdHash(body) : null,
               deriveHumanSnapshot(present),
             ));
           }
           continue;
         }
 
         // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
         const localSnap = deriveHumanSnapshot(lv);
         const cloudSnap = deriveHumanSnapshot(cv);
         const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
         const applied = await applyClassBWinners({
           deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
         });
         report.mergedFields += applied.merged;
         report.conflictsLogged += applied.conflicts;
         const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
 
         // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
         //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
         //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
         //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
         //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
         //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
         //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
         //    "seen" for delete-inference (baseline present).
+        //
+        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
+        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
+        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
+        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
+        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
+
+        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
+        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
+        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
+        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
+        //    corrections). The corrections conflict is still logged by Class B and still flags
+        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
         const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
-        if (correctionsUnresolved) {
+        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
           report.needsRegen += 1;
           if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
           await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
           continue;
         }
 
-        // ── Class A (needs the MD bodies for hashing — Behavior #1).
-        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
-        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
+        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
         const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
         if (decision.needsRegen) report.needsRegen += 1;
 
         let winnerMdHash: string | null = null;
         let winnerSignals: ClassASignals = la;
         let winnerSide: Side | null = null;
         let loserSide: Side | null = null;
         let winnerVideo: Video = lv;
 
         if (decision.action === 'copyToCloud') {
           winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
           winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
           report.updatedCloud += 1;
         } else if (decision.action === 'copyToLocal') {
           winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
           winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
           report.updatedLocal += 1;
         } else {
           report.skippedIdentical += 1;
           winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
         }
 
         if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
           const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
           if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
         }
         if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
 
         // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
         //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
         await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
       } catch (e: any) {
         report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
       }
     }
   }
 
   return report;
 }
diff --git a/tests/integration/cloud-sync/e2e.int.test.ts b/tests/integration/cloud-sync/e2e.int.test.ts
index 6b7bebe..6f12563 100644
--- a/tests/integration/cloud-sync/e2e.int.test.ts
+++ b/tests/integration/cloud-sync/e2e.int.test.ts
@@ -358,118 +358,196 @@ describe('cloud-sync §10 end-to-end scenarios', () => {
     expect(report.errors.length).toBeGreaterThanOrEqual(1);
     // No cloud row advertises promoted without a durable MD blob.
     const cloud = await cloudVideoRecord(ctx);
     expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
     expect(cloud?.summaryReady).toBeFalsy();
     // Baseline not advanced; no charge.
     expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   });
 
   // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
   it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
     const ctx = await makeOwnerContext();
     await seedCloudVideo(ctx, { mdBody: '# Fresh\n\nhydrated to a new device\n' });
 
     // The per-playlist local root must NOT exist yet, or the ensureHydrationRoot mkdir path goes untested.
     await expect(fs.access(ctx.playlistDataRoot)).rejects.toBeDefined();
 
     const r1 = await runSync(ctx.syncDeps());
     expect(r1.created).toBeGreaterThanOrEqual(1);
     await expect(fs.access(path.join(ctx.playlistDataRoot, 'playlist-index.json'))).resolves.toBeUndefined();
     const local = await localVideoRecord(ctx);
     expect(local).not.toBeNull();
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');
 
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
     expect(await localVideoRecord(ctx)).not.toBeNull();
   });
 
   // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
   //    Both sides changed corrections (backfilled, no per-field ts) → Class B logs+skips. The buggy
   //    path fed local's corrections value into reconciledCorrectionsHash → local looked
   //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
   //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
   it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
     const bodyCloud = '# CloudCorrB\n\nMD generated for correction B\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
       docVersion: { major: 1, minor: 0 },
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
       docVersion: { major: 1, minor: 0 },
     });
     const spendBefore = await ctx.spendLedgerTotal();
 
     const r1 = await runSync(ctx.syncDeps());
 
     expect(r1.updatedCloud).toBe(0);            // no Class-A copy in either direction
     expect(r1.updatedLocal).toBe(0);
     expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
     expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
     expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
 
     // Both MD blobs untouched — each still equals its own pre-sync body, and the two DIFFER.
     const l1 = (await localBlobBytes(ctx, key(ctx)))!.toString('utf8');
     const c1 = (await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8');
     expect(l1).toBe(bodyLocal);
     expect(c1).toBe(bodyCloud);
     expect(l1).not.toBe(c1);
     // Both corrections preserved (neither overwritten).
     expect((await localVideoRecord(ctx))?.corrections).toBe('A');
     expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
 
     // Second run — the baseline was NOT falsely advanced, so still no copy.
     const r2 = await runSync(ctx.syncDeps());
     expect(r2.updatedCloud).toBe(0);
     expect(r2.updatedLocal).toBe(0);
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
     expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   });
 
   // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
   //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
   //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
   //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
   //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
-  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
+  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
+  //    otherwise run 1 leaves a BARE receiver row, run 2 sees a two-sided video whose BOTH sides derive
+  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
+  //    laundering the corruption into a false "seen and agreed no-MD" state. The single-run assertions
+  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
+  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
     const ctx = await makeOwnerContext();
     // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
     await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });
 
     const report = await runSync(ctx.syncDeps());
 
     expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
-    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
-    const local = await localVideoRecord(ctx);
-    expect(artifactsOf(local)?.summaryMd?.status).not.toBe('promoted');
+    // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
+    expect(await localVideoRecord(ctx)).toBeNull();
+    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
     // Baseline not advanced — the throw aborted before writeVideoBaseline.
     expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
+
+    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
+    // bare row present it would instead take the two-sided path and silently record agreement.
+    const r2 = await runSync(ctx.syncDeps());
+    expect(r2.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
+    expect(await localVideoRecord(ctx)).toBeNull();
+    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
+    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   });
 
   // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
   //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
   //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
   it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
     const ctx = await makeOwnerContext();
     const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
     const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
     await seedLocalVideoFull(ctx, {
       mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
       summaryHtml: '<html>STALE rendered from the old local body</html>',
     });
     await seedCloudVideo(ctx, {
       mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
     });
 
     const report = await runSync(ctx.syncDeps());
     expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
 
     const local = await localVideoRecord(ctx);
     expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
     expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
   });
+
+  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
+  //    regenerable render cache: it is the filename pointer to a PAID Gemini-generated dig-deeper
+  //    markdown file (lib/dig/generate.ts). Nulling it on an ordinary Class-A transfer orphans the file
+  //    on disk and makes the dig-state route / VideoMenu / build-doc-html / pdf-path all go dark —
+  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
+  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
+  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
+    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
+    const digKey = 'paid-dig-deeper.md';
+    await seedLocalVideoFull(ctx, {
+      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+      summaryHtml: '<html>STALE rendered from the old local body</html>',
+      digDeeperHtml: '<html>STALE dig render</html>',
+      raw: { digDeeperMd: digKey },
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
+    });
+
+    const report = await runSync(ctx.syncDeps());
+    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
+
+    const local = await localVideoRecord(ctx);
+    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
+    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
+    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
+    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
+  });
+
+  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
+  //    MD body). When the loser has NO MD at all, hydrating it is purely additive — nothing can be
+  //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
+  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
+  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
+    const ctx = await makeOwnerContext();
+    const bodyCloud = '# CloudOnly\n\nthe only MD body that exists\n';
+    await seedLocalVideoFull(ctx, {
+      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
+      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
+      docVersion: { major: 1, minor: 0 },
+    });
+    await seedCloudVideo(ctx, {
+      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
+      docVersion: { major: 1, minor: 0 },
+    });
+    const spendBefore = await ctx.spendLedgerTotal();
+
+    const report = await runSync(ctx.syncDeps());
+
+    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);           // hydration ran
+    expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged
+    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
+    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
+
+    // The cloud body is now on local, advertised promoted; both corrections still preserved.
+    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
+    const local = await localVideoRecord(ctx);
+    expect(local?.summaryMd).toBe(key(ctx));
+    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
+    expect(local?.corrections).toBe('A');
+    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
+  });
 });

codex
I’ve got the round-2 context, including the adjudication: the old low-severity slot ordering argument is superseded and should not be reopened. Next I’m checking the current HEAD implementation and consumers around dig, HTML, PDF, and backend merge semantics.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/backfill.ts lib/cloud-sync/reconcile-class-a.ts lib/cloud-sync/reconcile-class-b.ts lib/cloud-sync/types.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '1,620p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// lib/cloud-sync/sync-run.ts
     2	//
     3	// Stage 3 Cloud Sync (§7) — the sync-run orchestrator. Composes the reconcile primitives (T1/T5–T9,
     4	// T11) into runSync(deps, opts?), reconciling every union video across the local replica and the
     5	// cloud, one playlist at a time, under an authenticated USER session (never service-role).
     6	//
     7	// Invariants (any violation = money/data bug):
     8	//  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
     9	//    cache (summaryHtml/dig/PDF) copied.
    10	//  - Cloud Principal.id = deps.ownerId (= auth.uid()): Supabase Storage RLS (0007) requires the
    11	//    first object-path segment to equal auth.uid(); the metadata RPCs are owner_id = auth.uid()
    12	//    guarded. A literal 'cloud' id would read null bytes and write to no row (F1).
    13	//  - Transfers finalize the receiver record via updateVideoFields (SyncDeps exposes no raw client,
    14	//    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
    15	//    tuple is verified durable — stage → verify → promote → finalize → verify → baseline (F2).
    16	//  - Class B is reconciled BEFORE Class A (Class A consumes the reconciled corrections hash);
    17	//    a Class-B loser write is asserted to have landed (found:true) or it throws (F3).
    18	
    19	import { promises as fs } from 'fs';
    20	import path from 'path';
    21	import type { MetadataStore } from '@/lib/storage/metadata-store';
    22	import type { BlobStore } from '@/lib/storage/blob-store';
    23	import type { Principal } from '@/lib/storage/principal';
    24	import { localPrincipal } from '@/lib/storage/principal';
    25	import type { Video } from '@/types';
    26	import { deriveClassASignals, deriveHumanSnapshot } from './backfill';
    27	import { reconcileHuman, type FieldMerge } from './reconcile-class-b';
    28	import { reconcileClassA } from './reconcile-class-a';
    29	import { decideCompanion } from './companion';
    30	import {
    31	  readManifest, writeVideoBaseline, appendConflict, resetConflictDedup,
    32	} from './manifest';
    33	import { discoverLocalPlaylists, unionPlaylistKeys, type LocalPlaylist } from './registry';
    34	import { mdHash } from './content-hash';
    35	import { readModelEnvelope, writeModelEnvelope } from '@/lib/html-doc/model-store';
    36	import type { PlaylistSummary } from '@/lib/storage/metadata-store';
    37	import type { ClassASignals, HumanField, HumanSnapshot, VideoBaseline } from './types';
    38	
    39	export interface SyncDeps {
    40	  local: MetadataStore; cloud: MetadataStore;
    41	  localBlob: BlobStore; cloudBlob: BlobStore;
    42	  dataRoots: string[]; ownerId: string;
    43	}
    44	
    45	export interface SyncReport {
    46	  created: number; updatedLocal: number; updatedCloud: number; skippedIdentical: number;
    47	  mergedFields: number; conflictsLogged: number; removed: number;
    48	  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
    49	  errors: { videoId: string; message: string }[];
    50	}
    51	
    52	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    53	const EMPTY_CLASSB = {} as VideoBaseline['classB'];
    54	
    55	/** One replica's write surface for a video (store + its principal + its blob store). */
    56	interface Side { store: MetadataStore; p: Principal; blob: BlobStore; }
    57	
    58	/** Behavior #1 — read the MD BODY from the blob (video.summaryMd is a KEY, not the body). */
    59	async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
    60	  if (!video.summaryMd) return null;
    61	  const buf = await blob.get(p, video.summaryMd);
    62	  return buf ? buf.toString('utf8') : null;
    63	}
    64	
    65	/** Union of video ids across both replicas' indexes. */
    66	async function enumerateVideoIds(
    67	  local: MetadataStore, cloud: MetadataStore, localP: Principal, cloudP: Principal,
    68	): Promise<string[]> {
    69	  const [l, c] = await Promise.all([local.readIndex(localP), cloud.readIndex(cloudP)]);
    70	  return [...new Set([...l.videos.map((v) => v.id), ...c.videos.map((v) => v.id)])];
    71	}
    72	
    73	/** Read one video record (or null if absent) from a store's index. */
    74	async function readVideo(store: MetadataStore, p: Principal, id: string): Promise<Video | null> {
    75	  const idx = await store.readIndex(p);
    76	  return idx.videos.find((v) => v.id === id) ?? null;
    77	}
    78	
    79	/** Deterministic local root for a cloud-only playlist (fresh-device hydrate target). */
    80	function hydrationRoot(dataRoots: string[], key: string): string {
    81	  return path.join(dataRoots[0], key);
    82	}
    83	
    84	/** mkdir -p the playlist's local root BEFORE any local read/write (round-5 H1). On a fresh device a
    85	 *  cloud-only playlist's dir does not exist; local readIndex throws on a missing DIRECTORY (returns
    86	 *  the empty-index sentinel only when the dir exists but the file is absent), and setPlaylistMeta/
    87	 *  writeIndex ENOENT into a missing parent. */
    88	async function ensureHydrationRoot(dataRoot: string): Promise<void> {
    89	  await fs.mkdir(dataRoot, { recursive: true });
    90	}
    91	
    92	/** Resolve the playlist url/title for `key` from whichever registry holds it. */
    93	function playlistMetaFor(
    94	  key: string, localPlaylists: LocalPlaylist[], cloudSummaries: PlaylistSummary[],
    95	): { playlistUrl: string; playlistTitle?: string } {
    96	  const lp = localPlaylists.find((l) => l.playlistKey === key);
    97	  if (lp) return { playlistUrl: lp.playlistUrl };
    98	  const cp = cloudSummaries.find((c) => c.playlistKey === key);
    99	  if (cp) return { playlistUrl: cp.playlistUrl, ...(cp.playlistTitle ? { playlistTitle: cp.playlistTitle } : {}) };
   100	  return { playlistUrl: '' };
   101	}
   102	
   103	/** Behavior #3 (money-safe) — strip regenerable cache + out-of-scope pointers so the receiver never
   104	 *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
   105	 *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
   106	 *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
   107	function sanitizeAdditiveVideo(video: Video): Video {
   108	  const v: any = { ...video };
   109	  v.summaryHtml = null;
   110	  v.digDeeperHtml = null;
   111	  v.digDeeperMd = null;
   112	  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
   113	  if (v.artifacts && typeof v.artifacts === 'object') {
   114	    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
   115	  }
   116	  // Replica-local ordering is NOT synced (§4.1) — the receiver's claim supplies its own.
   117	  delete v.serialNumber;
   118	  delete v.playlistIndex;
   119	  delete v.removedFromPlaylist;
   120	  // DB-computed read-only fields must never round-trip into a write.
   121	  delete v.updatedAt;
   122	  delete v.summaryReady;
   123	  return v as Video;
   124	}
   125	
   126	/** round-4 H1 — create the receiver playlist + reservation row BEFORE any receiver write. The cloud
   127	 *  upsertVideo/updateVideoFields are bare UPDATEs of a row pre-created by claimVideoSlot: they
   128	 *  silently affect 0 rows (no throw) on an absent row, so an additive create must claim the slot
   129	 *  first. Returns the claimed replica-local {position, serialNumber}, or null if the row already
   130	 *  existed (guarded by the readIndex-absence check; single-run so the check is authoritative). */
   131	async function ensureReceiverSlot(
   132	  to: MetadataStore, toP: Principal,
   133	  playlistMeta: { playlistUrl: string; playlistTitle?: string }, video: Video,
   134	): Promise<{ position: number; serialNumber: number } | null> {
   135	  await to.setPlaylistMeta(toP, playlistMeta);
   136	  const idx = await to.readIndex(toP);
   137	  if (idx.videos.some((v) => v.id === video.id)) return null;
   138	  return to.claimVideoSlot(toP, video.id);
   139	}
   140	
   141	/** Behavior #3 (money-safe) — additive create of a one-sided video onto the receiver. Order:
   142	 *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
   143	 *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
   144	 *  never copies regenerable cache. */
   145	async function copyAdditiveVideo(
   146	  to: MetadataStore, toP: Principal, toBlob: BlobStore,
   147	  playlistMeta: { playlistUrl: string; playlistTitle?: string },
   148	  video: Video, mdBody: string | null,
   149	): Promise<void> {
   150	  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
   151	  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
   152	  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
   153	  // strand the receiver with a servable-looking row backed by nothing.
   154	  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
   155	  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
   156	  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
   157	  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
   158	  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
   159	  // partial state is ever created, so there is nothing to roll back.
   160	  if (video.summaryMd && mdBody == null) {
   161	    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
   162	  }
   163	
   164	  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
   165	
   166	  let wroteBlob = false;
   167	  if (video.summaryMd && mdBody != null) {
   168	    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
   169	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
   170	    const staged = await toBlob.get(toP, ref.tempKey);
   171	    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
   172	      throw new Error(`additive staged MD verify failed for ${video.id}`);
   173	    }
   174	    await toBlob.promote(ref);
   175	    wroteBlob = true;
   176	  }
   177	
   178	  const sanitized: any = sanitizeAdditiveVideo(video);
   179	  if (slot) {
   180	    sanitized.serialNumber = slot.serialNumber;
   181	    sanitized.playlistIndex = slot.position + 1;
   182	  }
   183	  if (wroteBlob) {
   184	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   185	  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
   186	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
   187	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
   188	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
   189	    delete sanitized.artifacts.summaryMd;
   190	  }
   191	  await to.upsertVideo(toP, sanitized as Video);
   192	
   193	  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   194	  // (an update against an absent row silently no-ops; never advance a baseline for that).
   195	  const after = await to.readIndex(toP);
   196	  const rec = after.videos.find((v) => v.id === video.id);
   197	  if (!rec) {
   198	    throw new Error(`additive create did not persist receiver row for ${video.id}`);
   199	  }
   200	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   201	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   202	  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   203	  if (wroteBlob) {
   204	    const art = (rec as any).artifacts?.summaryMd;
   205	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
   206	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
   207	    }
   208	  }
   209	}
   210	
   211	/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
   212	 *  side's values, so this is a true agreed baseline. */
   213	function baselineFromOneSided(
   214	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
   215	): VideoBaseline {
   216	  const classB = {} as VideoBaseline['classB'];
   217	  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   218	  return {
   219	    classA: {
   220	      docVersionMajor: classA.docVersionMajor,
   221	      mdGeneratedAt: classA.mdGeneratedAt,
   222	      mdCorrectionsHash: classA.mdCorrectionsHash,
   223	      mdHash: mdHashVal,
   224	    },
   225	    classB,
   226	  };
   227	}
   228	
   229	/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
   230	 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
   231	 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
   232	 *  write on an absent row would let buildBaseline record a false agreement. */
   233	async function applyClassBWinners(args: {
   234	  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   235	  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   236	  dataRoot: string; key: string;
   237	}): Promise<{ merged: number; conflicts: number }> {
   238	  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   239	  let merged = 0;
   240	  let conflicts = 0;
   241	
   242	  for (const f of FIELDS) {
   243	    const m = merges[f];
   244	    if (m.conflict) {
   245	      await appendConflict(dataRoot, key, {
   246	        video_id: videoId, class: 'B', field: f,
   247	        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
   248	        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
   249	      });
   250	      conflicts += 1;
   251	    }
   252	    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
   253	
   254	    // winner is on one side → the OTHER (loser) side receives the winning value.
   255	    const target: Side = m.winner === 'local'
   256	      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
   257	      : { store: deps.local, p: localP, blob: deps.localBlob };
   258	    const set: Record<string, string | number> = {};
   259	    const clear: HumanField[] = [];
   260	    if (m.value === undefined) clear.push(f);
   261	    else set[f] = m.value;
   262	
   263	    const { found } = await target.store.updateVideoAnnotations(
   264	      target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
   265	    );
   266	    if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
   267	    merged += 1;
   268	  }
   269	  return { merged, conflicts };
   270	}
   271	
   272	/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
   273	 *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
   274	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
   275	 *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
   276	async function transferClassA(
   277	  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
   278	): Promise<{ mdHash: string; verified: boolean }> {
   279	  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   280	  if (body == null || !winnerVideo.summaryMd) {
   281	    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   282	  }
   283	  const h = mdHash(body);
   284	  const key = winnerVideo.summaryMd;
   285	
   286	  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   287	  const staged = await loser.blob.get(loser.p, ref.tempKey);
   288	  if (!staged || mdHash(staged.toString('utf8')) !== h) {
   289	    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   290	  }
   291	  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   292	  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   293	  // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   294	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   295	  // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   296	  // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   297	  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   298	  // (below) advertises promoted only after this resolves.
   299	  await loser.blob.put(loser.p, key, staged, 'text/markdown');
   300	  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
   301	
   302	  const wv: any = winnerVideo;
   303	  const completeTuple: any = {
   304	    summaryMd: key,
   305	    docVersion: wv.docVersion,
   306	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
   307	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
   308	    ratings: wv.ratings,
   309	    overallScore: wv.overallScore,
   310	    videoType: wv.videoType,
   311	    audience: wv.audience,
   312	    tags: wv.tags,
   313	    tldr: wv.tldr,
   314	    takeaways: wv.takeaways,
   315	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
   316	    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
   317	    // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
   318	    // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
   319	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
   320	    // readIndex reads falsy → forces re-render.
   321	    //
   322	    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
   323	    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
   324	    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
   325	    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
   326	    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
   327	    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
   328	    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
   329	    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
   330	    // whereas transferClassA PATCHES a row that already holds its own state.
   331	    summaryHtml: null,
   332	    digDeeperHtml: null,
   333	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   334	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   335	    artifacts: { summaryMd: { key, status: 'promoted' } },
   336	  };
   337	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   338	
   339	  return { mdHash: h, verified: true };
   340	}
   341	
   342	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   343	 *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
   344	 *  that the owner must re-serve to regenerate the share model. */
   345	async function companionTransfer(
   346	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   347	): Promise<{ shareNeedsOwnerServe: boolean }> {
   348	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   349	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   350	  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
   351	  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
   352	  if (decision.kind === 'ship') {
   353	    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   354	    return { shareNeedsOwnerServe: false };
   355	  }
   356	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   357	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   358	  return { shareNeedsOwnerServe: true };
   359	}
   360	
   361	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   362	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   363	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   364	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   365	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   366	function buildClassBBaseline(
   367	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   368	): VideoBaseline['classB'] {
   369	  const classB = {} as VideoBaseline['classB'];
   370	  for (const f of FIELDS) {
   371	    const m = merges[f];
   372	    if (m.winner === 'equal' && m.conflict) {
   373	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   374	    } else {
   375	      classB[f] = { value: m.value, editedAt: m.editedAt };
   376	    }
   377	  }
   378	  return classB;
   379	}
   380	
   381	function buildBaseline(
   382	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   383	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   384	): VideoBaseline {
   385	  return {
   386	    classA: {
   387	      docVersionMajor: winnerSignals.docVersionMajor,
   388	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   389	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   390	      mdHash: winnerMdHash,
   391	    },
   392	    classB: buildClassBBaseline(merges, previousBaseline),
   393	  };
   394	}
   395	
   396	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
   397	 *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
   398	 *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
   399	 *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
   400	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
   401	 *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
   402	 *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
   403	function buildCorrectionsUnresolvedBaseline(
   404	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   405	): VideoBaseline {
   406	  return {
   407	    classA: previousBaseline?.classA
   408	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
   409	    classB: buildClassBBaseline(merges, previousBaseline),
   410	  };
   411	}
   412	
   413	export async function runSync(
   414	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   415	): Promise<SyncReport> {
   416	  resetConflictDedup();
   417	  const report: SyncReport = {
   418	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   419	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   420	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   421	  };
   422	
   423	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   424	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   425	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   426	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   427	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   428	
   429	  for (const key of keys) {
   430	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   431	      ?? hydrationRoot(deps.dataRoots, key);
   432	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   433	
   434	    const localP = localPrincipal(dataRoot);
   435	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   436	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   437	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   438	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   439	    const manifest = await readManifest(dataRoot, key);
   440	
   441	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   442	      try {
   443	        const lv = await readVideo(deps.local, localP, id);
   444	        const cv = await readVideo(deps.cloud, cloudP, id);
   445	        const base = manifest.videos[id];
   446	
   447	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   448	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   449	        if (!lv || !cv) {
   450	          const present = (lv ?? cv)!;
   451	          const presentIsLocal = lv != null;
   452	          if (base) {
   453	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   454	          } else {
   455	            const from: Side = presentIsLocal ? localSide : cloudSide;
   456	            const to: Side = presentIsLocal ? cloudSide : localSide;
   457	            const body = await readMdBody(from.blob, from.p, present);
   458	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   459	            report.created += 1; // reached only after the receiver row is confirmed
   460	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   461	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   462	              deriveHumanSnapshot(present),
   463	            ));
   464	          }
   465	          continue;
   466	        }
   467	
   468	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   469	        const localSnap = deriveHumanSnapshot(lv);
   470	        const cloudSnap = deriveHumanSnapshot(cv);
   471	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   472	        const applied = await applyClassBWinners({
   473	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   474	        });
   475	        report.mergedFields += applied.merged;
   476	        report.conflictsLogged += applied.conflicts;
   477	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   478	
   479	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
   480	        //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
   481	        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
   482	        //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
   483	        //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
   484	        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
   485	        //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
   486	        //    "seen" for delete-inference (baseline present).
   487	        //
   488	        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
   489	        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
   490	        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
   491	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   492	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   493	
   494	        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
   495	        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
   496	        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
   497	        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
   498	        //    corrections). The corrections conflict is still logged by Class B and still flags
   499	        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
   500	        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
   501	        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
   502	          report.needsRegen += 1;
   503	          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   504	          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
   505	          continue;
   506	        }
   507	
   508	        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
   509	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   510	        if (decision.needsRegen) report.needsRegen += 1;
   511	
   512	        let winnerMdHash: string | null = null;
   513	        let winnerSignals: ClassASignals = la;
   514	        let winnerSide: Side | null = null;
   515	        let loserSide: Side | null = null;
   516	        let winnerVideo: Video = lv;
   517	
   518	        if (decision.action === 'copyToCloud') {
   519	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   520	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   521	          report.updatedCloud += 1;
   522	        } else if (decision.action === 'copyToLocal') {
   523	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   524	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   525	          report.updatedLocal += 1;
   526	        } else {
   527	          report.skippedIdentical += 1;
   528	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   529	        }
   530	
   531	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   532	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   533	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   534	        }
   535	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   536	
   537	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   538	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   539	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   540	      } catch (e: any) {
   541	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   542	      }
   543	    }
   544	  }
   545	
   546	  return report;
   547	}

exec
/bin/bash -lc 'rg -n "digDeeperMd|digDeeperHtml|summaryHtml|artifacts|mdCorrectionsHash|needsRegen|spend_ledger|enqueue|reserve|release" lib/html-doc lib/dig lib/pdf app/api/videos lib/cloud-sync lib/storage supabase/migrations/0021_cloud_sync_signals.sql supabase/migrations/0009_* tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
lib/dig/dig-section.ts:104:  // Step 11: Update index with digDeeperMd (HTML is rendered fresh by GET)
lib/dig/dig-section.ts:106:    digDeeperMd: digDeeperFilename,
tests/integration/cloud-sync/stamping.int.test.ts:6:// persist_summary's mdGeneratedAt/mdCorrectionsHash passthrough.
tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
tests/integration/cloud-sync/stamping.int.test.ts:90:  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
tests/integration/cloud-sync/stamping.int.test.ts:94:      summaryMd: 'artifacts/v/summary.md', mdGeneratedAt: '2026-07-17T13:00:00.000Z', mdCorrectionsHash: 'h1',
tests/integration/cloud-sync/stamping.int.test.ts:100:    expect(row.mdCorrectionsHash).toBe('h1');
lib/html-doc/generate.ts:48:  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
lib/html-doc/generate.ts:72:    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
app/api/videos/[id]/quick-view/route.ts:19:// ---- LOCAL path — preserved verbatim (pre-2a Task 6 behavior, filesystem-backed) ----
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:15:drop function enqueue_job(text,int,text,text,jsonb);
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:16:create function enqueue_job(
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:25:    if v_tries > 8 then raise exception 'enqueue_job: retry limit exceeded'; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:40:        raise log 'enqueue_job: joined % with a divergent payload (kept existing)', v_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:45:revoke all on function enqueue_job(uuid,text,int,text,text,jsonb) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:46:grant execute on function enqueue_job(uuid,text,int,text,text,jsonb) to anon, authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:79:create function reserve_video_slot(p_owner_id uuid, p_playlist_id uuid, p_video_id text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:90:    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:101:revoke all on function reserve_video_slot(uuid,uuid,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:102:grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:111:  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:113:  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:121:    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:122:      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:126:           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:137:      || jsonb_build_object('artifacts',
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:138:           coalesce(v.data->'artifacts', '{}'::jsonb)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:141:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
lib/pdf/pdf-path.ts:11: * - dig-deeper: `pdfs/{basename(digDeeperMd) with -dig-deeper.md -> -dig-deeper}.pdf`
lib/pdf/pdf-path.ts:19:    if (!video.digDeeperMd) throw new Error('no dig-deeper doc for this video');
lib/pdf/pdf-path.ts:20:    const b = path.basename(video.digDeeperMd);
lib/storage/resolve.ts:24: *  CRITICAL (Codex Blocking): preserve the RAW outputFolder string — do NOT
lib/storage/resolve.ts:31:  const indexKey = outputFolder;    // raw string preserved; renamed for Principal field clarity
tests/integration/cloud-sync/e2e.int.test.ts:10:// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
tests/integration/cloud-sync/e2e.int.test.ts:31:/** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
tests/integration/cloud-sync/e2e.int.test.ts:32:const artifactsOf = (rec: { [k: string]: unknown } | null) =>
tests/integration/cloud-sync/e2e.int.test.ts:33:  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
tests/integration/cloud-sync/e2e.int.test.ts:36:/** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
tests/integration/cloud-sync/e2e.int.test.ts:43:    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
tests/integration/cloud-sync/e2e.int.test.ts:63:      mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
tests/integration/cloud-sync/e2e.int.test.ts:68:      mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:91:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:106:      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
tests/integration/cloud-sync/e2e.int.test.ts:112:      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:134:    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
tests/integration/cloud-sync/e2e.int.test.ts:135:    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:169:      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:173:      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:194:      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:198:      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:218:      mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:221:      mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:268:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
tests/integration/cloud-sync/e2e.int.test.ts:269:  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:273:      summaryHtml: '<html>cached</html>',
tests/integration/cloud-sync/e2e.int.test.ts:274:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:280:    expect(local?.summaryHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:282:    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
tests/integration/cloud-sync/e2e.int.test.ts:285:  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
tests/integration/cloud-sync/e2e.int.test.ts:290:    await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
tests/integration/cloud-sync/e2e.int.test.ts:291:    await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });
tests/integration/cloud-sync/e2e.int.test.ts:328:    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:361:    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:398:      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:402:      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:421:    // Both corrections preserved (neither overwritten).
tests/integration/cloud-sync/e2e.int.test.ts:434:  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
tests/integration/cloud-sync/e2e.int.test.ts:435:  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
tests/integration/cloud-sync/e2e.int.test.ts:445:    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
tests/integration/cloud-sync/e2e.int.test.ts:453:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:462:    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
tests/integration/cloud-sync/e2e.int.test.ts:468:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
tests/integration/cloud-sync/e2e.int.test.ts:469:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:474:      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:475:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:478:      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:485:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
tests/integration/cloud-sync/e2e.int.test.ts:493:  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:501:      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:502:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:503:      digDeeperHtml: '<html>STALE dig render</html>',
tests/integration/cloud-sync/e2e.int.test.ts:504:      raw: { digDeeperMd: digKey },
tests/integration/cloud-sync/e2e.int.test.ts:507:      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
tests/integration/cloud-sync/e2e.int.test.ts:515:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:517:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
tests/integration/cloud-sync/e2e.int.test.ts:523:  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
tests/integration/cloud-sync/e2e.int.test.ts:529:      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
tests/integration/cloud-sync/e2e.int.test.ts:533:      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
tests/integration/cloud-sync/e2e.int.test.ts:542:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:545:    // The cloud body is now on local, advertised promoted; both corrections still preserved.
tests/integration/cloud-sync/e2e.int.test.ts:549:    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
supabase/migrations/0021_cloud_sync_signals.sql:3:-- allowlisting, conditional merge restamp, and mdGeneratedAt/mdCorrectionsHash on persist.
supabase/migrations/0021_cloud_sync_signals.sql:80:    data = (data || (p_fields - 'artifacts'))
supabase/migrations/0021_cloud_sync_signals.sql:81:      || case when p_fields ? 'artifacts'
supabase/migrations/0021_cloud_sync_signals.sql:82:           then jsonb_build_object('artifacts',
supabase/migrations/0021_cloud_sync_signals.sql:83:                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
supabase/migrations/0021_cloud_sync_signals.sql:98:--     'mdGeneratedAt' and 'mdCorrectionsHash' (§5.7).
supabase/migrations/0021_cloud_sync_signals.sql:106:  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
supabase/migrations/0021_cloud_sync_signals.sql:108:  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
supabase/migrations/0021_cloud_sync_signals.sql:111:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0021_cloud_sync_signals.sql:116:    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
supabase/migrations/0021_cloud_sync_signals.sql:117:      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
supabase/migrations/0021_cloud_sync_signals.sql:121:           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
supabase/migrations/0021_cloud_sync_signals.sql:132:           'mdCorrectionsHash', p_video->'mdCorrectionsHash'))
supabase/migrations/0021_cloud_sync_signals.sql:134:      || jsonb_build_object('artifacts',
supabase/migrations/0021_cloud_sync_signals.sql:135:           coalesce(v.data->'artifacts', '{}'::jsonb)
supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0021_cloud_sync_signals.sql:138:                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
lib/dig/generate.ts:124:   *  received (before json parse) — proof-of-meter for the release-vs-keep classifier. Absent on
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
lib/cloud-sync/types.ts:9:  mdCorrectionsHash: string | null;
lib/cloud-sync/types.ts:32:  classA: { docVersionMajor: number; mdGeneratedAt: string | null; mdCorrectionsHash: string | null; mdHash: string | null };
lib/html-doc/ensure.ts:16: * cheap re-render; no HTML yet → full build; already current → nothing. Leaves summaryHtml + docVersion
lib/html-doc/ensure.ts:54:  } else if (!video.summaryHtml) {
lib/cloud-sync/backfill.ts:14:    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:9://    cache (summaryHtml/dig/PDF) copied.
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:104: *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
lib/cloud-sync/sync-run.ts:109:  v.summaryHtml = null;
lib/cloud-sync/sync-run.ts:110:  v.digDeeperHtml = null;
lib/cloud-sync/sync-run.ts:111:  v.digDeeperMd = null;
lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
lib/cloud-sync/sync-run.ts:113:  if (v.artifacts && typeof v.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
lib/cloud-sync/sync-run.ts:143: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
lib/cloud-sync/sync-run.ts:184:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
lib/cloud-sync/sync-run.ts:185:  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:189:    delete sanitized.artifacts.summaryMd;
lib/cloud-sync/sync-run.ts:202:  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
lib/cloud-sync/sync-run.ts:204:    const art = (rec as any).artifacts?.summaryMd;
lib/cloud-sync/sync-run.ts:222:      mdCorrectionsHash: classA.mdCorrectionsHash,
lib/cloud-sync/sync-run.ts:297:  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
lib/cloud-sync/sync-run.ts:307:    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
lib/cloud-sync/sync-run.ts:316:    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
lib/cloud-sync/sync-run.ts:322:    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
lib/cloud-sync/sync-run.ts:323:    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
lib/cloud-sync/sync-run.ts:327:    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
lib/cloud-sync/sync-run.ts:331:    summaryHtml: null,
lib/cloud-sync/sync-run.ts:332:    digDeeperHtml: null,
lib/cloud-sync/sync-run.ts:335:    artifacts: { summaryMd: { key, status: 'promoted' } },
lib/cloud-sync/sync-run.ts:389:      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
lib/cloud-sync/sync-run.ts:398: *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
lib/cloud-sync/sync-run.ts:402: *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
lib/cloud-sync/sync-run.ts:408:      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:499:        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
lib/cloud-sync/sync-run.ts:502:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:510:        if (decision.needsRegen) report.needsRegen += 1;
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
lib/storage/local/local-metadata-store.ts:26:    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
tests/lib/cloud-sync/reconcile-class-a.test.ts:6:  mdCorrectionsHash: 'C', backfilled: false, ...o,
tests/lib/cloud-sync/reconcile-class-a.test.ts:13:      .toEqual({ action: 'skip', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:15:  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:16:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:17:    expect(r).toEqual({ action: 'skip', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:20:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: CUR }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:21:    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:24:    const r = reconcileClassA({ local: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 2 }), cloud: S({ mdHash: 'h', mdCorrectionsHash: 'OLD', docVersionMajor: 3 }), reconciledCorrectionsHash: CUR });
tests/lib/cloud-sync/reconcile-class-a.test.ts:25:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:28:    const local = S({ mdCorrectionsHash: CUR, docVersionMajor: 2, mdHash: 'hl' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:29:    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:31:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:37:      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
tests/lib/cloud-sync/reconcile-class-a.test.ts:43:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
tests/lib/cloud-sync/reconcile-class-a.test.ts:45:  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:46:    const local = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 2, mdHash: 'hl' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:47:    const cloud = S({ mdCorrectionsHash: 'OLD', docVersionMajor: 3, mdHash: 'hc' });
tests/lib/cloud-sync/reconcile-class-a.test.ts:49:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
tests/lib/cloud-sync/reconcile-class-a.test.ts:51:  it('present only one side (current) → copy, no needsRegen (hydrate/publish)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:53:      .toEqual({ action: 'copyToLocal', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:55:      .toEqual({ action: 'copyToCloud', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:57:  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:58:    expect(reconcileClassA({ local: S({ summaryMdKey: null, mdHash: null }), cloud: S({ mdHash: 'hc', mdCorrectionsHash: 'OLD' }), reconciledCorrectionsHash: CUR }))
tests/lib/cloud-sync/reconcile-class-a.test.ts:59:      .toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:63:      .toEqual({ action: 'skip', needsRegen: false });
lib/pdf/generate-doc-pdf.ts:35: *   `PdfRendererUnavailable` (503) with the original error preserved in `cause` — a deliberate, uniform
lib/pdf/generate-doc-pdf.ts:40: *   the default preserves the original void/fire-and-forget behavior used by the local job route.
app/api/videos/[id]/review/route.ts:56:// ---- LOCAL path — preserved verbatim (pre-2a Task 7 behavior, filesystem-backed) ----
lib/cloud-sync/reconcile-class-a.ts:5:  needsRegen: boolean;
lib/cloud-sync/reconcile-class-a.ts:8:const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
lib/cloud-sync/reconcile-class-a.ts:20:  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
lib/cloud-sync/reconcile-class-a.ts:21:  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:22:  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
lib/cloud-sync/reconcile-class-a.ts:23:  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
lib/cloud-sync/reconcile-class-a.ts:33:    if (lCur && cCur) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:34:    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
lib/cloud-sync/reconcile-class-a.ts:39:  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:40:  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:45:    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
lib/cloud-sync/reconcile-class-a.ts:50:  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
lib/storage/worker-persistence.ts:4:/** Thin wrapper over the reserve_video_slot RPC (Task 2). Returns the
lib/storage/worker-persistence.ts:6:export async function reserveVideoSlot(
lib/storage/worker-persistence.ts:9:  const { data, error } = await client.rpc('reserve_video_slot', {
tests/lib/cloud-sync/manifest.test.ts:23:  const base = { classA: { docVersionMajor: 3, mdGeneratedAt: 't', mdCorrectionsHash: 'c', mdHash: 'h' },
lib/dig/cloud/resolve-summary-key.ts:3:/** Resolves the summary md KEY for a video: the artifact record's key (`artifacts.summaryMd.key`),
lib/dig/cloud/resolve-summary-key.ts:7: *  Does NOT gate on `artifacts.summaryMd.status === 'promoted'` the way `loadSummaryForServe`
lib/dig/cloud/resolve-summary-key.ts:10: *  gate: it enqueues a dig job only when `loadSummaryForServe` reports the summary promoted, so by
lib/dig/cloud/resolve-summary-key.ts:13:  const v = video as { artifacts?: { summaryMd?: { key?: string } }; summaryMd?: string | null };
lib/dig/cloud/resolve-summary-key.ts:14:  const key = v.artifacts?.summaryMd?.key ?? v.summaryMd ?? null;
tests/lib/cloud-sync/schema.test.ts:16:      mdCorrectionsHash: 'abc',
tests/lib/cloud-sync/schema.test.ts:19:    expect(v.mdCorrectionsHash).toBe('abc');
lib/storage/supabase/supabase-job-queue.ts:93:      // decided by the worker-runner in Task 10) releases the reservation.
lib/storage/supabase/supabase-job-queue.ts:96:      // so a metered-then-requeued job's later release paths (fail_job at exhaustion, or a cancel
lib/pdf/pdf-concurrency.ts:20:/** Acquire a slot or throw PdfBusyError; release ONLY IF acquired, in finally (round-3 Low). */
lib/html-doc/read-model.ts:28: *  not_ready. Never reserves spend or generates a model (no charging RPC, no LLM call). */
lib/html-doc/read-model.ts:43: *  coherent to render against current markdown. Never reserves/generates (pure blob read). */
lib/dig/cloud/enqueue-dig-core.ts:5:import type { Enqueuer } from '@/lib/job-queue/enqueuer';
lib/dig/cloud/enqueue-dig-core.ts:10:  enqueuer: Enqueuer;         // service-role — enqueue RPC only
lib/dig/cloud/enqueue-dig-core.ts:16:  enqueueIp: string | null;
lib/dig/cloud/enqueue-dig-core.ts:22: *  magazine model), validate the section, dedup on the current-version blob, preflight, enqueue.
lib/dig/cloud/enqueue-dig-core.ts:23: *  Charge happens once, inside enqueue_job, only on a fresh enqueue. */
lib/dig/cloud/enqueue-dig-core.ts:24:export async function enqueueDig(deps: EnqueueDigDeps): Promise<EnqueueDigResult> {
lib/dig/cloud/enqueue-dig-core.ts:37:  // Dedup authority = the current-version blob. Present → done, no enqueue, no charge.
lib/dig/cloud/enqueue-dig-core.ts:43:  const verdict = await deps.enqueuer.preflight(deps.enqueueIp, deps.userId);
lib/dig/cloud/enqueue-dig-core.ts:49:    const res = await deps.enqueuer.enqueue(
lib/dig/cloud/enqueue-dig-core.ts:50:      { ownerId: deps.userId, enqueueIp: deps.enqueueIp },
lib/dig/cloud/enqueue-dig-core.ts:63:    return { status: 202, body: { status: 'enqueued', jobId: res.jobId, sectionId: deps.sectionId } };
lib/storage/supabase/supabase-metadata-store.ts:11:// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
lib/storage/supabase/supabase-metadata-store.ts:14:// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
lib/storage/supabase/supabase-metadata-store.ts:53:          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
lib/storage/supabase/supabase-metadata-store.ts:54:            .artifacts?.summaryMd?.status === 'promoted',
lib/storage/supabase/supabase-metadata-store.ts:116:  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
lib/storage/supabase/supabase-metadata-store.ts:117:  // modify-write races; deep-merges the `artifacts` sub-object).
lib/storage/supabase/supabase-metadata-store.ts:171:  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
tests/lib/cloud-sync/backfill.test.ts:10:  // no mdGeneratedAt / mdCorrectionsHash / annotationsEditedAt
tests/lib/cloud-sync/backfill.test.ts:35:  const s = deriveClassASignals({ ...legacy, mdGeneratedAt: '2026-03-03T00:00:00.000Z', mdCorrectionsHash: 'h', docVersion: { major: 3, minor: 3 } }, BODY);
app/api/videos/route.ts:35:      // Preserve undefined (don't coalesce to '') so an incomplete row sorts LAST via the
app/api/videos/route.ts:85:    // Incomplete rows (a reserved slot whose summary hasn't landed, so this sort key
app/api/videos/route.ts:105:// ---- LOCAL path — preserved verbatim (pre-2a Task 5 behavior, filesystem-backed) ----
lib/storage/supabase/consistency.ts:34:    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
lib/storage/supabase/consistency.ts:40:    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
tests/lib/cloud-sync/regenerate-stamp.test.ts:5:// that persists refreshed tldr/takeaways/summaryHtml — also stamps mdGeneratedAt and
tests/lib/cloud-sync/regenerate-stamp.test.ts:6:// mdCorrectionsHash = mdHash(effectiveCorrections). This guards former-Blocking §5.3: a
tests/lib/cloud-sync/regenerate-stamp.test.ts:92:        mdCorrectionsHash: mdHash('fix name'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:104:        mdCorrectionsHash: mdHash('old corrections'),
tests/lib/cloud-sync/regenerate-stamp.test.ts:116:        mdCorrectionsHash: mdHash(''),
app/api/videos/[id]/dig-state/route.ts:92:  const digDeeperMd = video.digDeeperMd;
app/api/videos/[id]/dig-state/route.ts:93:  if (!digDeeperMd) {
app/api/videos/[id]/dig-state/route.ts:99:  const digDeeperPath = path.join(outputFolder, digDeeperMd);
lib/dig/cloud/load-dig-for-serve.ts:18: * resolveMagazineModel / reserve_serve_model (spec §2 money invariant).
app/api/videos/[id]/archive/route.ts:20:// ---- LOCAL path — preserved verbatim (pre-2a Task 8 behavior, filesystem-backed) ----
app/api/videos/[id]/regenerate/route.ts:86:      tldr, takeaways, summaryHtml: null,
app/api/videos/[id]/regenerate/route.ts:88:      mdCorrectionsHash: mdHash(effectiveCorrections),
app/api/videos/[id]/regenerate/route.ts:95:      summaryHtml: null,
app/api/videos/[id]/dig/[sectionId]/route.ts:5:import { cancelJob, createJob, deleteJob, emitJobEvent, getActiveJob, getJobSignal, releaseJobLock } from '@/lib/job-registry';
app/api/videos/[id]/dig/[sectionId]/route.ts:10:import { SupabaseEnqueuer } from '@/lib/job-queue/enqueuer';
app/api/videos/[id]/dig/[sectionId]/route.ts:11:import { enqueueDig } from '@/lib/dig/cloud/enqueue-dig-core';
app/api/videos/[id]/dig/[sectionId]/route.ts:21:// A 429 from this route (rate-limited OR quota-exhausted — enqueueDig doesn't distinguish in the
app/api/videos/[id]/dig/[sectionId]/route.ts:47:    // Authoritative anon status = profiles.is_anonymous (the SAME column enqueue_job checks at
app/api/videos/[id]/dig/[sectionId]/route.ts:55:    // challengeRequired (soft captcha-UX advisory from enqueuer.preflight) is deliberately NOT
app/api/videos/[id]/dig/[sectionId]/route.ts:59:    const result = await enqueueDig({
app/api/videos/[id]/dig/[sectionId]/route.ts:60:      supabase, enqueuer: new SupabaseEnqueuer(createServiceClient()),
app/api/videos/[id]/dig/[sectionId]/route.ts:62:      videoId, playlistId, sectionId, enqueueIp: parseClientIp(request),
app/api/videos/[id]/dig/[sectionId]/route.ts:98:      releaseJobLock(existing);
app/api/videos/[id]/dig/[sectionId]/route.ts:109:    releaseJobLock(jobId);
lib/dig/cloud/dig-blob-key.ts:5: *  distinct jobs_idem_active slot (which includes job_version), permitting a legit re-enqueue. */
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/serve-doc.ts:11:import { classifyGeminiFailure, releaseGateOpen } from '@/lib/gemini-failure';
lib/html-doc/serve-doc.ts:57:  if (fresh.status === 'ok') return { status: 'ok', model: fresh.model }; // B1 — no Gemini, no reserve
lib/html-doc/serve-doc.ts:59:  // Absent / drifted / stale-version → materialize under the reserve RPC.
lib/html-doc/serve-doc.ts:60:  const { data, error } = await supabaseClient.rpc('reserve_serve_model', {
lib/html-doc/serve-doc.ts:64:  const row = (data as Array<{ status: string; release_token: string | null }> | null)?.[0];   // table-return → data[0]
lib/html-doc/serve-doc.ts:65:  const reserveStatus = row?.status;
lib/html-doc/serve-doc.ts:66:  const releaseToken = row?.release_token ?? null;
lib/html-doc/serve-doc.ts:67:  switch (reserveStatus) {
lib/html-doc/serve-doc.ts:83:    case 'reserved': break;
lib/html-doc/serve-doc.ts:84:    default: throw new Error(`reserve_serve_model: unexpected status ${String(reserveStatus)}`);
lib/html-doc/serve-doc.ts:90:  // (create-if-absent promote could never replace it → re-reserve + re-charge every view until K, then 503).
lib/html-doc/serve-doc.ts:92:  // keeps the charge (released=false) and clears the per-attempt token; a throw refunds ONLY a
lib/html-doc/serve-doc.ts:112:    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: false });
lib/html-doc/serve-doc.ts:116:    const released = releaseGateOpen()
lib/html-doc/serve-doc.ts:117:      && classifyGeminiFailure(err, signal) === 'release'
lib/html-doc/serve-doc.ts:119:    if (releaseToken) await supabaseClient.rpc('settle_serve_model', { p_token: releaseToken, p_released: released });
lib/html-doc/dig-merge.ts:181:  // Preserve deterministic order: pre-orphans (extras from step-1 build) come last,
lib/dig/companion-doc.ts:6: * frontmatter entry in place; all other sections are preserved.
lib/dig/companion-doc.ts:510: * - Preserves all other sections.
app/api/videos/batch-docs/route.ts:5:import { createJob, deleteJob, emitJobEvent, getActiveJob, releaseJobLock, getJobSignal } from '../../../../lib/job-registry';
app/api/videos/batch-docs/route.ts:44:    releaseJobLock(jobId);
app/api/videos/[id]/html-doc/route.ts:6:import { createJob, deleteJob, emitJobEvent, getActiveJob, releaseJobLock } from '../../../../../lib/job-registry';
app/api/videos/[id]/html-doc/route.ts:50:    releaseJobLock(jobId);                       // free the lock now → a later Regenerate is allowed
lib/html-doc/nav.ts:531:  try { data = (await resp.json()) as { status?: string }; } catch { /* treat as enqueued */ }
app/api/videos/[id]/dig/[sectionId]/stream/route.ts:22:        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
app/api/videos/[id]/html-doc/stream/route.ts:22:        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
app/api/videos/[id]/pdf/route.ts:10:import { createJob, deleteJob, emitJobEvent, getActiveJob, releaseJobLock } from '../../../../../lib/job-registry';
app/api/videos/[id]/pdf/route.ts:62:    releaseJobLock(jobId);                                   // free the lock → a later re-save is allowed
app/api/videos/[id]/pdf/route.ts:66:  const abandon = () => { releaseJobLock(jobId); deleteJob(jobId); }; // no job ever started → free immediately
lib/html-doc/serve-summary-core.ts:47:  const artifact = (video as unknown as { artifacts?: { summaryMd?: { key?: string; status?: string } } })
lib/html-doc/serve-summary-core.ts:48:    .artifacts?.summaryMd;
lib/html-doc/serve-summary-core.ts:53:  // Key source: prefer artifacts.summaryMd.key (the artifact record), fall back to top-level
lib/html-doc/build-doc-html.ts:41:    const htmlFile = video.summaryHtml;
lib/html-doc/build-doc-html.ts:43:    // Preserve the stronger htmls/*.html guard (regex + htmlDir containment).
lib/html-doc/build-doc-html.ts:75:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:77:      digDeeperPath = assertIndexRelPathWithin(outputFolder, video.digDeeperMd);
lib/html-doc/build-doc-html.ts:86:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:87:    const digRel = video.digDeeperMd;
lib/html-doc/parse.ts:45:  // preserved verbatim in prose. The first chunk (before any ##) is preamble — discarded.
lib/html-doc/parse.ts:79:      // OUTSIDE a fence — fenced content is preserved verbatim.
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
app/api/videos/batch-docs/stream/route.ts:16:        controller.enqueue(chunk);
app/api/videos/[id]/pdf/stream/route.ts:22:        controller.enqueue(encoder.encode(`data: ${JSON.stringify(event)}\n\n`));
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);

exec
/bin/bash -lc 'git status --short && rg -n "H-R2-1|H-R2-2|M-R2-2|WB-H1|WB-H2|WB-B1|corrections conflict|digDeeperMd" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md
?? scratchpad/
tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
tests/integration/cloud-sync/e2e.int.test.ts:393:  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:433:  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
tests/integration/cloud-sync/e2e.int.test.ts:438:  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
tests/integration/cloud-sync/e2e.int.test.ts:443:  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:466:  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
tests/integration/cloud-sync/e2e.int.test.ts:469:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:489:  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
tests/integration/cloud-sync/e2e.int.test.ts:495:  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:504:      raw: { digDeeperMd: digKey },
tests/integration/cloud-sync/e2e.int.test.ts:515:    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
tests/integration/cloud-sync/e2e.int.test.ts:517:    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
tests/integration/cloud-sync/e2e.int.test.ts:520:  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
tests/integration/cloud-sync/e2e.int.test.ts:522:  //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
tests/integration/cloud-sync/e2e.int.test.ts:524:  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:541:    expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged

codex
The current sync path now validates before slot reservation and preserves `digDeeperMd` on transfer. I’m focusing on the new narrowed corrections guard now, because that path writes a baseline after a Class-A hydrate while Class-B corrections intentionally remains unresolved.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/reconcile-class-b.ts | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { FieldState, HumanField, HumanSnapshot, VideoBaseline } from './types';
     2	
     3	export interface FieldMerge {
     4	  winner: 'local' | 'cloud' | 'equal';
     5	  value: string | number | undefined;
     6	  editedAt: string | undefined;
     7	  conflict: boolean;
     8	}
     9	
    10	type Baseline = { value?: string | number; editedAt?: string };
    11	
    12	/** Changed vs baseline is over the (value, editedAt) PAIR, not value alone (§5.4). */
    13	function changed(side: FieldState, base: Baseline): boolean {
    14	  return side.value !== base.value || side.editedAt !== base.editedAt;
    15	}
    16	
    17	function newer(a: string | undefined, b: string | undefined): boolean {
    18	  // returns true when a is strictly newer than b; undefined sorts oldest
    19	  return (a ?? '') > (b ?? '');
    20	}
    21	
    22	export function reconcileField(local: FieldState, cloud: FieldState, baseline: Baseline): FieldMerge {
    23	  // Equal VALUES never conflict (§5.4 row 1). But if their per-field timestamps differ, CONVERGE:
    24	  // return the newer-timestamp side as a NON-conflicting winner so the older side's editedAt is
    25	  // written forward and both replicas end identical — returning 'equal' here would skip the write
    26	  // and leave baseline/live timestamp drift (round-2 H1). Truly-equal pair → 'equal' (no write).
    27	  if (local.value === cloud.value) {
    28	    if (local.editedAt === cloud.editedAt) {
    29	      return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: false };
    30	    }
    31	    return newer(local.editedAt, cloud.editedAt)
    32	      ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false }
    33	      : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
    34	  }
    35	  const lChanged = changed(local, baseline);
    36	  const cChanged = changed(cloud, baseline);
    37	
    38	  if (lChanged && !cChanged) return { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: false };
    39	  if (cChanged && !lChanged) return { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: false };
    40	
    41	  // both changed (or neither vs an absent baseline but values differ) → newer per-field ts wins.
    42	  // A backfilled timestamp must never drive a destructive overwrite (§5.5) → conflict skip.
    43	  if (local.backfilled || cloud.backfilled) {
    44	    return { winner: 'equal', value: local.value, editedAt: local.editedAt, conflict: true };
    45	  }
    46	  const localWins = newer(local.editedAt, cloud.editedAt);
    47	  return localWins
    48	    ? { winner: 'local', value: local.value, editedAt: local.editedAt, conflict: true }
    49	    : { winner: 'cloud', value: cloud.value, editedAt: cloud.editedAt, conflict: true };
    50	}
    51	
    52	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    53	
    54	export function reconcileHuman(
    55	  local: HumanSnapshot,
    56	  cloud: HumanSnapshot,
    57	  baseline: VideoBaseline['classB'],
    58	): Record<HumanField, FieldMerge> {
    59	  const out = {} as Record<HumanField, FieldMerge>;
    60	  for (const f of FIELDS) out[f] = reconcileField(local[f], cloud[f], baseline[f] ?? {});
    61	  return out;
    62	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/reconcile-class-a.ts lib/cloud-sync/backfill.ts lib/cloud-sync/content-hash.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba lib/storage/local/local-metadata-store.ts lib/storage/supabase/supabase-metadata-store.ts supabase/migrations/0021_cloud_sync_signals.sql supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '1,580p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	// tests/integration/cloud-sync/e2e.int.test.ts
     2	//
     3	// Stage 3 Cloud Sync (§10), Task 14 — the end-to-end keystone. One `it(...)` per §10 scenario,
     4	// driving the FULL runSync stack against real local FS ↔ local Supabase under an authenticated
     5	// USER session (never service-role). Where Task 12 proved the additive hydrate path, rows 1/2/7
     6	// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
     7	// MD bodies — the winner-copy path the Task-12 tests never exercised.
     8	//
     9	// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
    10	// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
    11	import { promises as fs } from 'fs';
    12	import os from 'os';
    13	import path from 'path';
    14	import { randomUUID } from 'crypto';
    15	import {
    16	  makeOwnerContext, seedCloudVideo, seedLocalVideoFull, seedManifestBaseline,
    17	  cloudVideoRecord, localVideoRecord, cloudBlobBytes, localBlobBytes, type Ctx,
    18	} from '@/tests/integration/helpers/cloud';
    19	import { runSync } from '@/lib/cloud-sync/sync-run';
    20	import { mdHash } from '@/lib/cloud-sync/content-hash';
    21	import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
    22	import type { VideoBaseline } from '@/lib/cloud-sync/types';
    23	
    24	afterAll(async () => {
    25	  const home = os.homedir();
    26	  const dirs = (await fs.readdir(home)).filter((d) => d.startsWith('.cs-syncrun-'));
    27	  await Promise.all(dirs.map((d) => fs.rm(path.join(home, d), { recursive: true, force: true })));
    28	});
    29	
    30	const key = (ctx: Ctx) => `${ctx.videoId}.md`;
    31	/** `artifacts` lives in the videos.data jsonb but is not on the Video Zod type — read it via a cast. */
    32	const artifactsOf = (rec: { [k: string]: unknown } | null) =>
    33	  (rec as { artifacts?: { summaryMd?: { status?: string } } & Record<string, unknown> } | null)?.artifacts;
    34	/** SHA-256 of the canonicalized MD BODY (matches the orchestrator's transfer verify). */
    35	const bodyHash = (b: string) => mdHash(b);
    36	/** mdCorrectionsHash value that makes a side "corrections-current" when NO corrections exist:
    37	 *  reconciledCorrectionsHash === mdHash(String(undefined ?? '')) === mdHash(''). */
    38	const H_NO_CORRECTIONS = mdHash('');
    39	
    40	/** A syntactically-complete baseline whose classA/classB are inert for the assertion under test. */
    41	function baseline(classB: VideoBaseline['classB']): VideoBaseline {
    42	  return {
    43	    classA: { docVersionMajor: 1, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
    44	    classB,
    45	  };
    46	}
    47	const EMPTY_CLASSB = {
    48	  personalNote: { value: undefined, editedAt: undefined },
    49	  personalScore: { value: undefined, editedAt: undefined },
    50	  corrections: { value: undefined, editedAt: undefined },
    51	} as VideoBaseline['classB'];
    52	
    53	describe('cloud-sync §10 end-to-end scenarios', () => {
    54	  // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
    55	  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
    56	  it('row 1: higher-major MD beats a newer lower-major (format beats recency); receiver copies it', async () => {
    57	    const ctx = await makeOwnerContext();
    58	    const bodyHi = '# HiMajor\n\nformat-3 content\n';   // local, docVersion.major=3, OLD timestamp
    59	    const bodyLo = '# LoMajor\n\nformat-1 content\n';   // cloud, docVersion.major=1, NEWER timestamp
    60	    const winnerRatings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 };
    61	    await seedLocalVideoFull(ctx, {
    62	      mdBody: bodyHi, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2020-01-01T00:00:00.000Z',
    63	      mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
    64	      tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
    65	    });
    66	    await seedCloudVideo(ctx, {
    67	      mdBody: bodyLo, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2026-06-01T00:00:00.000Z',
    68	      mdCorrectionsHash: H_NO_CORRECTIONS,
    69	    });
    70	    const spendBefore = await ctx.spendLedgerTotal();
    71	
    72	    const report = await runSync(ctx.syncDeps());
    73	
    74	    expect(report.updatedCloud).toBeGreaterThanOrEqual(1);
    75	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
    76	
    77	    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
    78	    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
    79	    expect(cloudBody).not.toBeNull();
    80	    expect(cloudBody!.toString('utf8')).toBe(bodyHi);
    81	    expect(bodyHash(cloudBody!.toString('utf8'))).toBe(bodyHash(bodyHi));
    82	
    83	    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
    84	    const cloud = await cloudVideoRecord(ctx);
    85	    expect(cloud?.docVersion?.major).toBe(3);
    86	    expect(cloud?.ratings).toEqual(winnerRatings);
    87	    expect(cloud?.overallScore).toBe(3);
    88	    expect(cloud?.tldr).toBe('the-tldr');
    89	    expect(cloud?.takeaways).toEqual(['a', 'b']);
    90	    expect(cloud?.tags).toEqual(['x', 'y']);
    91	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
    92	  });
    93	
    94	  // ── Row 2 — corrections-current lower-major MD survives over a corrections-STALE higher-major MD.
    95	  //    Currency beats format → the corrections-current body lands on BOTH sides.
    96	  //    Winner is the CLOUD side here → copyToLocal, exercising the local-overwrite transfer direction.
    97	  it('row 2: corrections-current lower-major beats stale higher-major (currency beats format)', async () => {
    98	    const ctx = await makeOwnerContext();
    99	    const bodyCurrent = '# CurrentCorrections\n\nlower-major but corrections-current\n'; // cloud (winner)
   100	    const bodyStale = '# StaleHiMajor\n\nhigher-major but corrections-stale\n';          // local (loser)
   101	    const winnerRatings = { usefulness: 5, depth: 3, originality: 2, recency: 4, completeness: 1 };
   102	    const editedAt = '2025-06-01T00:00:00.000Z';
   103	    await seedCloudVideo(ctx, {
   104	      mdBody: bodyCurrent, docVersion: { major: 1, minor: 0 }, mdGeneratedAt: '2025-01-01T00:00:00.000Z',
   105	      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
   106	      mdCorrectionsHash: mdHash('fix-v2'),  // current: matches the reconciled corrections
   107	      ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
   108	    });
   109	    await seedLocalVideoFull(ctx, {
   110	      mdBody: bodyStale, docVersion: { major: 3, minor: 0 }, mdGeneratedAt: '2026-01-01T00:00:00.000Z',
   111	      corrections: 'fix-v2', annotationsEditedAt: { corrections: editedAt },
   112	      mdCorrectionsHash: mdHash('fix-v1'),  // STALE: MD was generated against an older corrections
   113	    });
   114	
   115	    const report = await runSync(ctx.syncDeps());
   116	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   117	
   118	    // The corrections-current (lower-major) body is now on both sides; docVersion downgraded to it.
   119	    const cloudBody = await cloudBlobBytes(ctx, key(ctx));
   120	    const localBody = await localBlobBytes(ctx, key(ctx));
   121	    expect(cloudBody!.toString('utf8')).toBe(bodyCurrent);   // winner side unchanged
   122	    expect(localBody!.toString('utf8')).toBe(bodyCurrent);   // loser overwritten with the winner body
   123	    const local = await localVideoRecord(ctx);
   124	    expect(local?.docVersion?.major).toBe(1);
   125	    expect(local?.ratings).toEqual(winnerRatings);
   126	    expect(local?.tldr).toBe('keep-me');
   127	  });
   128	
   129	  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
   130	  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
   131	    const ctx = await makeOwnerContext();
   132	    const body = '# StaleBoth\n\nidentical stale content\n';
   133	    const staleHash = mdHash('stale-corrections'); // != mdHash('') → both sides corrections-stale
   134	    await seedLocalVideoFull(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
   135	    await seedCloudVideo(ctx, { mdBody: body, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: staleHash });
   136	
   137	    const report = await runSync(ctx.syncDeps());
   138	
   139	    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
   140	    expect(report.skippedIdentical).toBeGreaterThanOrEqual(1);
   141	    // MD unchanged on both sides.
   142	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
   143	    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(body);
   144	  });
   145	
   146	  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
   147	  it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
   148	    const ctx = await makeOwnerContext();
   149	    const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
   150	    await seedCloudVideo(ctx, {
   151	      mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
   152	      tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
   153	    });
   154	
   155	    await runSync(ctx.syncDeps()); // hydrate empty local from cloud
   156	    const local = await localVideoRecord(ctx);
   157	    expect(local?.ratings).toEqual(ratings);
   158	    expect(local?.overallScore).toBe(3);
   159	    expect(local?.tldr).toBe('the tldr');
   160	    expect(local?.takeaways).toEqual(['t1', 't2']);
   161	    expect(local?.tags).toEqual(['x', 'y']);
   162	  });
   163	
   164	  // ── Row 5 — Class-B: a note edit on local + a score edit on cloud → BOTH survive on both sides.
   165	  it('row 5: independent Class-B edits (note local, score cloud) both survive', async () => {
   166	    const ctx = await makeOwnerContext();
   167	    const body = '# Same\n\nidentical current MD\n';
   168	    await seedLocalVideoFull(ctx, {
   169	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   170	      personalNote: 'mynote', annotationsEditedAt: { personalNote: '2026-03-01T00:00:00.000Z' },
   171	    });
   172	    await seedCloudVideo(ctx, {
   173	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   174	      personalScore: 4, annotationsEditedAt: { personalScore: '2026-03-02T00:00:00.000Z' },
   175	    });
   176	
   177	    const report = await runSync(ctx.syncDeps());
   178	    expect(report.mergedFields).toBeGreaterThanOrEqual(2);
   179	
   180	    const local = await localVideoRecord(ctx);
   181	    const cloud = await cloudVideoRecord(ctx);
   182	    expect(local?.personalNote).toBe('mynote');
   183	    expect(local?.personalScore).toBe(4);
   184	    expect(cloud?.personalNote).toBe('mynote');
   185	    expect(cloud?.personalScore).toBe(4);
   186	  });
   187	
   188	  // ── Row 6 — Class-B cleared field is NOT resurrected (baseline-aware). Local cleared vs cloud stale.
   189	  it('row 6: a cleared Class-B field is not resurrected (baseline-aware)', async () => {
   190	    const ctx = await makeOwnerContext();
   191	    const body = '# Same6\n\nidentical current MD\n';
   192	    // Local cleared personalNote (value gone, but a NEWER edit timestamp); cloud still holds the old value.
   193	    await seedLocalVideoFull(ctx, {
   194	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   195	      annotationsEditedAt: { personalNote: '2026-05-02T00:00:00.000Z' }, // cleared: no personalNote value
   196	    });
   197	    await seedCloudVideo(ctx, {
   198	      mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS,
   199	      personalNote: 'old', annotationsEditedAt: { personalNote: '2026-05-01T00:00:00.000Z' },
   200	    });
   201	    await seedManifestBaseline(ctx, baseline({
   202	      ...EMPTY_CLASSB,
   203	      personalNote: { value: 'old', editedAt: '2026-05-01T00:00:00.000Z' },
   204	    }));
   205	
   206	    await runSync(ctx.syncDeps());
   207	
   208	    const local = await localVideoRecord(ctx);
   209	    const cloud = await cloudVideoRecord(ctx);
   210	    expect(local?.personalNote == null).toBe(true);
   211	    expect(cloud?.personalNote == null).toBe(true); // the clear propagated; 'old' not resurrected
   212	  });
   213	
   214	  // ── Row 7 — synced+shared, model missing → anon share not-ready until owner serve (counted).
   215	  it('row 7: a transferred summary with no matching model flags shareNeedsOwnerServe', async () => {
   216	    const ctx = await makeOwnerContext();
   217	    await seedLocalVideoFull(ctx, {
   218	      mdBody: '# Winner7\n\nformat-2\n', docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   219	    });
   220	    await seedCloudVideo(ctx, {
   221	      mdBody: '# Loser7\n\nformat-1\n', docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   222	    });
   223	
   224	    const report = await runSync(ctx.syncDeps()); // winner (local) has no model envelope → deleteReceiverModel
   225	    expect(report.shareNeedsOwnerServe).toBeGreaterThanOrEqual(1);
   226	  });
   227	
   228	  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
   229	  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
   230	    const ctx = await makeOwnerContext();
   231	    await seedCloudVideo(ctx, { mdBody: '# Free\n\nno charge\n' });
   232	    const spendBefore = await ctx.spendLedgerTotal();
   233	
   234	    const report = await runSync(ctx.syncDeps());
   235	
   236	    expect(report.created).toBeGreaterThanOrEqual(1);
   237	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   238	  });
   239	
   240	  // ── Row 9 — a baseline-present remote delete is NOT re-created; counted as removed.
   241	  it('row 9: a baseline-present video absent on one side is removed, not re-created', async () => {
   242	    const ctx = await makeOwnerContext();
   243	    // Cloud still holds the video; local deleted it; a baseline records they once agreed.
   244	    await seedCloudVideo(ctx, { mdBody: '# Deleted\n\ngone locally\n' });
   245	    await seedManifestBaseline(ctx, baseline(EMPTY_CLASSB));
   246	
   247	    const report = await runSync(ctx.syncDeps());
   248	
   249	    expect(report.removed).toBeGreaterThanOrEqual(1);
   250	    expect(await localVideoRecord(ctx)).toBeNull();          // not re-hydrated
   251	    expect(await cloudVideoRecord(ctx)).not.toBeNull();      // present side untouched (no propagation, M2b)
   252	    expect(report.created).toBe(0);
   253	  });
   254	
   255	  // ── Row 10 — no-session refusal + a client-forged owner_id is RLS-rejected.
   256	  it('row 10: getAuthedClient throws with no session; a forged owner_id is RLS-rejected', async () => {
   257	    const emptyStore: TokenStore = { read: async () => null, write: async () => {}, clear: async () => {} };
   258	    await expect(getAuthedClient(emptyStore)).rejects.toBeInstanceOf(NoSessionError);
   259	
   260	    const ctx = await makeOwnerContext();
   261	    const { error } = await ctx.userClient.from('playlists').insert({
   262	      owner_id: randomUUID(), // NOT auth.uid() → RLS with-check rejects
   263	      playlist_key: `k-${randomUUID()}`, playlist_url: 'https://x/forged',
   264	    });
   265	    expect(error).toBeTruthy();
   266	  });
   267	
   268	  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
   269	  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
   270	    const ctx = await makeOwnerContext();
   271	    await seedCloudVideo(ctx, {
   272	      mdBody: '# Cached\n\nhas cache\n',
   273	      summaryHtml: '<html>cached</html>',
   274	      digDeeperHtml: '<html>dig</html>',
   275	      extraArtifacts: { summaryPdf: { key: 'p.pdf', status: 'promoted' } },
   276	    });
   277	
   278	    await runSync(ctx.syncDeps());
   279	    const local = await localVideoRecord(ctx);
   280	    expect(local?.summaryHtml == null).toBe(true);
   281	    expect(local?.digDeeperHtml == null).toBe(true);
   282	    expect(artifactsOf(local)?.summaryPdf).toBeUndefined();
   283	  });
   284	
   285	  // ── Row 12 — a backfilled Class-B conflict is preserved across TWO runs (§5.5, round-3 H2).
   286	  it('row 12: backfilled divergent note logs+skips on both runs; neither side overwritten', async () => {
   287	    const ctx = await makeOwnerContext();
   288	    const body = '# Same12\n\nidentical current MD\n';
   289	    // Both sides carry a DIFFERENT personalNote with NO per-field timestamp → both backfilled.
   290	    await seedLocalVideoFull(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-local' });
   291	    await seedCloudVideo(ctx, { mdBody: body, mdCorrectionsHash: H_NO_CORRECTIONS, personalNote: 'note-cloud' });
   292	
   293	    const r1 = await runSync(ctx.syncDeps());
   294	    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
   295	    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local');
   296	    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
   297	    const m1 = await ctx.readManifest();
   298	    expect((m1.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
   299	
   300	    const r2 = await runSync(ctx.syncDeps());
   301	    expect(r2.conflictsLogged).toBeGreaterThanOrEqual(1); // re-logs (not silently skipped)
   302	    expect((await localVideoRecord(ctx))?.personalNote).toBe('note-local'); // still not overwritten
   303	    expect((await cloudVideoRecord(ctx))?.personalNote).toBe('note-cloud');
   304	    const m2 = await ctx.readManifest();
   305	    expect((m2.videos[ctx.videoId] as VideoBaseline).classB.personalNote.value).toBeUndefined();
   306	  });
   307	
   308	  // ── Row 13 — additive create of a summary-less video: metadata copied, no blob put, no throw.
   309	  it('row 13: additive create of a summary-less video copies metadata with no blob write', async () => {
   310	    const ctx = await makeOwnerContext();
   311	    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
   312	
   313	    const report = await runSync(ctx.syncDeps());
   314	    expect(report.errors).toEqual([]);
   315	    expect(report.created).toBeGreaterThanOrEqual(1);
   316	    const local = await localVideoRecord(ctx);
   317	    expect(local).not.toBeNull();
   318	    expect(local?.summaryMd == null).toBe(true);
   319	  });
   320	
   321	  // ── Row 14 — additive PUBLISH is servable: cloud row advertises promoted → summaryReady true.
   322	  it('row 14: additive publish sets promoted status → summaryReady true on the cloud', async () => {
   323	    const ctx = await makeOwnerContext();
   324	    await seedLocalVideoFull(ctx, { mdBody: '# Published\n\nservable\n' }); // local-only → publishes to cloud
   325	
   326	    await runSync(ctx.syncDeps());
   327	    const cloud = await cloudVideoRecord(ctx);
   328	    expect(artifactsOf(cloud)?.summaryMd?.status).toBe('promoted');
   329	    expect(cloud?.summaryReady).toBe(true);
   330	  });
   331	
   332	  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
   333	  it('row 15: additive publish creates the cloud playlist+video; a re-run is not read as a delete', async () => {
   334	    const ctx = await makeOwnerContext();
   335	    await seedLocalVideoFull(ctx, { mdBody: '# Create15\n\ncreated on cloud\n' });
   336	
   337	    const r1 = await runSync(ctx.syncDeps());
   338	    expect(r1.created).toBeGreaterThanOrEqual(1);
   339	    expect(await cloudVideoRecord(ctx)).not.toBeNull(); // receiver row created (not a silent no-op)
   340	    const m1 = await ctx.readManifest();
   341	    expect(m1.videos[ctx.videoId]).toBeDefined();       // baseline written only after the row landed
   342	
   343	    const r2 = await runSync(ctx.syncDeps());
   344	    expect(r2.removed).toBe(0);                          // baseline present + BOTH sides present → not a delete
   345	    expect(r2.created).toBe(0);
   346	    expect(await cloudVideoRecord(ctx)).not.toBeNull();
   347	    expect(await localVideoRecord(ctx)).not.toBeNull();
   348	  });
   349	
   350	  // ── Row 16 — promoted status never precedes a durable blob (blob promote fails mid-publish).
   351	  it('row 16: a failed blob promote leaves no promoted row and does not advance the baseline', async () => {
   352	    const ctx = await makeOwnerContext();
   353	    await seedLocalVideoFull(ctx, { mdBody: '# Crash16\n\npromote fails\n' });
   354	    const spendBefore = await ctx.spendLedgerTotal();
   355	
   356	    const report = await runSync(ctx.syncDeps({ failCloudPromote: true }));
   357	
   358	    expect(report.errors.length).toBeGreaterThanOrEqual(1);
   359	    // No cloud row advertises promoted without a durable MD blob.
   360	    const cloud = await cloudVideoRecord(ctx);
   361	    expect(artifactsOf(cloud)?.summaryMd?.status).not.toBe('promoted');
   362	    expect(cloud?.summaryReady).toBeFalsy();
   363	    // Baseline not advanced; no charge.
   364	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   365	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   366	  });
   367	
   368	  // ── Row 17 — fresh-device hydrate creates the local root (mkdir -p); re-run is not a delete.
   369	  it('row 17: a fresh-device hydrate creates the local root, writes index+video+MD; re-run is not a delete', async () => {
   370	    const ctx = await makeOwnerContext();
   371	    await seedCloudVideo(ctx, { mdBody: '# Fresh\n\nhydrated to a new device\n' });
   372	
   373	    // The per-playlist local root must NOT exist yet, or the ensureHydrationRoot mkdir path goes untested.
   374	    await expect(fs.access(ctx.playlistDataRoot)).rejects.toBeDefined();
   375	
   376	    const r1 = await runSync(ctx.syncDeps());
   377	    expect(r1.created).toBeGreaterThanOrEqual(1);
   378	    await expect(fs.access(path.join(ctx.playlistDataRoot, 'playlist-index.json'))).resolves.toBeUndefined();
   379	    const local = await localVideoRecord(ctx);
   380	    expect(local).not.toBeNull();
   381	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toContain('# Fresh');
   382	
   383	    const r2 = await runSync(ctx.syncDeps());
   384	    expect(r2.removed).toBe(0); // the just-created local root is not mis-read as a delete
   385	    expect(await localVideoRecord(ctx)).not.toBeNull();
   386	  });
   387	
   388	  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
   389	  //    Both sides changed corrections (backfilled, no per-field ts) → Class B logs+skips. The buggy
   390	  //    path fed local's corrections value into reconciledCorrectionsHash → local looked
   391	  //    corrections-current, cloud stale → copyToCloud OVERWROTE cloud's (different-correction) MD body.
   392	  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
   393	  it('WB-B1: a backfilled corrections conflict does NOT copy MD; both bodies + corrections preserved (2 runs)', async () => {
   394	    const ctx = await makeOwnerContext();
   395	    const bodyLocal = '# LocalCorrA\n\nMD generated for correction A\n';
   396	    const bodyCloud = '# CloudCorrB\n\nMD generated for correction B\n';
   397	    await seedLocalVideoFull(ctx, {
   398	      mdBody: bodyLocal, corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
   399	      docVersion: { major: 1, minor: 0 },
   400	    });
   401	    await seedCloudVideo(ctx, {
   402	      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // no annotationsEditedAt → backfilled
   403	      docVersion: { major: 1, minor: 0 },
   404	    });
   405	    const spendBefore = await ctx.spendLedgerTotal();
   406	
   407	    const r1 = await runSync(ctx.syncDeps());
   408	
   409	    expect(r1.updatedCloud).toBe(0);            // no Class-A copy in either direction
   410	    expect(r1.updatedLocal).toBe(0);
   411	    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
   412	    expect(r1.conflictsLogged).toBeGreaterThanOrEqual(1);
   413	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
   414	
   415	    // Both MD blobs untouched — each still equals its own pre-sync body, and the two DIFFER.
   416	    const l1 = (await localBlobBytes(ctx, key(ctx)))!.toString('utf8');
   417	    const c1 = (await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8');
   418	    expect(l1).toBe(bodyLocal);
   419	    expect(c1).toBe(bodyCloud);
   420	    expect(l1).not.toBe(c1);
   421	    // Both corrections preserved (neither overwritten).
   422	    expect((await localVideoRecord(ctx))?.corrections).toBe('A');
   423	    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   424	
   425	    // Second run — the baseline was NOT falsely advanced, so still no copy.
   426	    const r2 = await runSync(ctx.syncDeps());
   427	    expect(r2.updatedCloud).toBe(0);
   428	    expect(r2.updatedLocal).toBe(0);
   429	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyLocal);
   430	    expect((await cloudBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   431	  });
   432	
   433	  // ── WB-H1 — an additive create must never advertise a promoted summary whose blob was not copied.
   434	  //    Cloud advertises summaryMd (artifacts.summaryMd = promoted) but its MD blob is ABSENT →
   435	  //    readMdBody returns null. The buggy path preserved the promoted artifact and upserted a
   436	  //    promoted-but-blobless row + advanced the baseline. After the fix: per-video throw, no promoted
   437	  //    receiver row, baseline NOT advanced (a re-run heals once the body is readable).
   438	  //    H-R2-1 (round 2) upgrades this to TWO runs: the throw must happen BEFORE ensureReceiverSlot,
   439	  //    otherwise run 1 leaves a BARE receiver row, run 2 sees a two-sided video whose BOTH sides derive
   440	  //    mdHash === null, reconcileClassA returns 'skip' (!lHas && !cHas) and runSync WRITES A BASELINE —
   441	  //    laundering the corruption into a false "seen and agreed no-MD" state. The single-run assertions
   442	  //    below all passed while that bug was live; the run-2 baseline assertion is the real guard.
   443	  it('WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)', async () => {
   444	    const ctx = await makeOwnerContext();
   445	    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
   446	    await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });
   447	
   448	    const report = await runSync(ctx.syncDeps());
   449	
   450	    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   451	    // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
   452	    expect(await localVideoRecord(ctx)).toBeNull();
   453	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
   454	    // Baseline not advanced — the throw aborted before writeVideoBaseline.
   455	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   456	
   457	    // Run 2 — still one-sided, so it must report the SAME error and still write no baseline. With a
   458	    // bare row present it would instead take the two-sided path and silently record agreement.
   459	    const r2 = await runSync(ctx.syncDeps());
   460	    expect(r2.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   461	    expect(await localVideoRecord(ctx)).toBeNull();
   462	    expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
   463	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   464	  });
   465	
   466	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
   467	  //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
   468	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
   469	  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
   470	    const ctx = await makeOwnerContext();
   471	    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
   472	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   473	    await seedLocalVideoFull(ctx, {
   474	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   475	      summaryHtml: '<html>STALE rendered from the old local body</html>',
   476	    });
   477	    await seedCloudVideo(ctx, {
   478	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   479	    });
   480	
   481	    const report = await runSync(ctx.syncDeps());
   482	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   483	
   484	    const local = await localVideoRecord(ctx);
   485	    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
   486	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
   487	  });
   488	
   489	  // ── H-R2-2 — the WB-H2 cache invalidation must NOT extend to digDeeperMd. digDeeperMd is NOT a
   490	  //    regenerable render cache: it is the filename pointer to a PAID Gemini-generated dig-deeper
   491	  //    markdown file (lib/dig/generate.ts). Nulling it on an ordinary Class-A transfer orphans the file
   492	  //    on disk and makes the dig-state route / VideoMenu / build-doc-html / pdf-path all go dark —
   493	  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
   494	  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
   495	  it('H-R2-2: a copyToLocal transfer preserves the loser PAID digDeeperMd while still nulling the HTML caches', async () => {
   496	    const ctx = await makeOwnerContext();
   497	    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
   498	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   499	    const digKey = 'paid-dig-deeper.md';
   500	    await seedLocalVideoFull(ctx, {
   501	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   502	      summaryHtml: '<html>STALE rendered from the old local body</html>',
   503	      digDeeperHtml: '<html>STALE dig render</html>',
   504	      raw: { digDeeperMd: digKey },
   505	    });
   506	    await seedCloudVideo(ctx, {
   507	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   508	    });
   509	
   510	    const report = await runSync(ctx.syncDeps());
   511	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   512	
   513	    const local = await localVideoRecord(ctx);
   514	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body landed
   515	    expect(local?.summaryHtml == null).toBe(true);      // WB-H2 still holds
   516	    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
   517	    expect((local as { digDeeperMd?: string } | null)?.digDeeperMd).toBe(digKey); // PAID pointer preserved
   518	  });
   519	
   520	  // ── M-R2-2 — the WB-B1 skip must be narrowed to the genuinely DESTRUCTIVE case (both sides hold an
   521	  //    MD body). When the loser has NO MD at all, hydrating it is purely additive — nothing can be
   522	  //    destroyed — so a backfilled corrections conflict must not strand the video with no MD forever
   523	  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
   524	  it('M-R2-2: a corrections conflict still hydrates a one-sided MD (purely additive, nothing destroyed)', async () => {
   525	    const ctx = await makeOwnerContext();
   526	    const bodyCloud = '# CloudOnly\n\nthe only MD body that exists\n';
   527	    await seedLocalVideoFull(ctx, {
   528	      summaryMd: null, // local row exists but holds NO MD → nothing to destroy
   529	      corrections: 'A', mdCorrectionsHash: mdHash('A'), // no annotationsEditedAt → backfilled
   530	      docVersion: { major: 1, minor: 0 },
   531	    });
   532	    await seedCloudVideo(ctx, {
   533	      mdBody: bodyCloud, corrections: 'B', mdCorrectionsHash: mdHash('B'), // backfilled
   534	      docVersion: { major: 1, minor: 0 },
   535	    });
   536	    const spendBefore = await ctx.spendLedgerTotal();
   537	
   538	    const report = await runSync(ctx.syncDeps());
   539	
   540	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);           // hydration ran
   541	    expect(report.conflictsLogged).toBeGreaterThanOrEqual(1);        // corrections conflict still logged
   542	    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
   543	    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
   544	
   545	    // The cloud body is now on local, advertised promoted; both corrections still preserved.
   546	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloud);
   547	    const local = await localVideoRecord(ctx);
   548	    expect(local?.summaryMd).toBe(key(ctx));
   549	    expect(artifactsOf(local)?.summaryMd?.status).toBe('promoted');
   550	    expect(local?.corrections).toBe('A');
   551	    expect((await cloudVideoRecord(ctx))?.corrections).toBe('B');
   552	  });
   553	});

codex
The one-sided-hydration branch does write a Class-A baseline after the copied MD lands, while the Class-B baseline keeps the unresolved corrections conflict unadvanced. That looks intentional: on the next run both sides have the same MD body, so the narrowed guard takes over and preserves the same Class-A baseline while continuing to report `needsRegen`.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/reconcile-class-a.ts | sed -n '1,140p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { ClassASignals } from './types';
     2	
     3	export interface ClassADecision {
     4	  action: 'skip' | 'copyToLocal' | 'copyToCloud';
     5	  needsRegen: boolean;
     6	}
     7	
     8	const current = (s: ClassASignals, cur: string): boolean => s.mdCorrectionsHash === cur;
     9	const newer = (a: string | null, b: string | null): boolean => (a ?? '') > (b ?? '');
    10	
    11	export function reconcileClassA(args: {
    12	  local: ClassASignals;
    13	  cloud: ClassASignals;
    14	  reconciledCorrectionsHash: string;
    15	}): ClassADecision {
    16	  const { local, cloud, reconciledCorrectionsHash: cur } = args;
    17	  const lHas = local.mdHash != null;
    18	  const cHas = cloud.mdHash != null;
    19	
    20	  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
    21	  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
    22	  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
    23	  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
    24	
    25	  const lCur = current(local, cur);
    26	  const cCur = current(cloud, cur);
    27	  const bothStale = !lCur && !cCur;
    28	
    29	  // Equal MD bodies: skip ONLY when both corrections-current, OR both stale AND same format.
    30	  // If currency OR format disagrees (even with identical bytes), fall through so the winning
    31	  // metadata TUPLE converges onto the identical body — do NOT skip (Blocking ③, spec §5.3 row 1).
    32	  if (local.mdHash === cloud.mdHash) {
    33	    if (lCur && cCur) return { action: 'skip', needsRegen: false };
    34	    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
    35	    // else: fall through to currency/format below.
    36	  }
    37	
    38	  // corrections-currency FIRST (a stale MD never overwrites a corrections-current one)
    39	  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
    40	  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };
    41	
    42	  // format (never downgrade)
    43	  if (local.docVersionMajor !== cloud.docVersionMajor) {
    44	    const winnerIsCloud = cloud.docVersionMajor > local.docVersionMajor;
    45	    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
    46	  }
    47	
    48	  // same major, different mdHash → recency-tiebreak (unify prose)
    49	  const winnerIsLocal = newer(local.mdGeneratedAt, cloud.mdGeneratedAt);
    50	  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
    51	}

exec
/bin/bash -lc "nl -ba lib/cloud-sync/backfill.ts | sed -n '1,140p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { Video } from '@/types';
     2	import type { ClassASignals, HumanSnapshot, HumanField, FieldState } from './types';
     3	import { mdHash } from './content-hash';
     4	
     5	// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
     6	// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
     7	export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
     8	  const hasReal = video.mdGeneratedAt != null;
     9	  return {
    10	    summaryMdKey: video.summaryMd ?? null,
    11	    mdHash: mdBody != null ? mdHash(mdBody) : null,
    12	    docVersionMajor: video.docVersion?.major ?? 1,
    13	    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
    14	    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
    15	    backfilled: !hasReal,
    16	  };
    17	}
    18	
    19	const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];
    20	
    21	export function deriveHumanSnapshot(video: Video): HumanSnapshot {
    22	  const provisional = video.updatedAt ?? video.processedAt;
    23	  const out = {} as HumanSnapshot;
    24	  for (const f of FIELDS) {
    25	    const value = video[f] as string | number | undefined;
    26	    const real = video.annotationsEditedAt?.[f];
    27	    const state: FieldState<string | number> = value === undefined && real === undefined
    28	      ? { value: undefined, editedAt: undefined, backfilled: false }
    29	      : { value, editedAt: real ?? provisional, backfilled: real === undefined };
    30	    out[f] = state;
    31	  }
    32	  return out;
    33	}

exec
/bin/bash -lc "nl -ba supabase/migrations/0021_cloud_sync_signals.sql | sed -n '1,190p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	-- supabase/migrations/0021_cloud_sync_signals.sql
     2	-- Stage 3 Cloud Sync (§5.7): per-field annotationsEditedAt stamping, corrections
     3	-- allowlisting, conditional merge restamp, and mdGeneratedAt/mdCorrectionsHash on persist.
     4	
     5	-- (0) DROP the old signatures FIRST. Adding a defaulted `p_edited_at` parameter to
     6	--     update_video_annotations / merge_video_data with `create or replace` would create a
     7	--     NEW overload and LEAVE the old 4-arg / 3-arg functions in place. A caller that omits
     8	--     p_edited_at (e.g. SupabaseMetadataStore.updateVideoAnnotations' 4-key rpc call) would
     9	--     then match BOTH overloads → PostgREST error PGRST203 "could not choose the best
    10	--     candidate function" → the live Archive button + annotation/field writes break. Dropping
    11	--     the old signatures makes the 3/4-key call resolve unambiguously to the single surviving
    12	--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
    13	drop function if exists update_video_annotations(uuid, text, jsonb, text[]);
    14	drop function if exists merge_video_data(uuid, text, jsonb);
    15	
    16	-- (1) update_video_annotations: add corrections to the allowlist; stamp per-field
    17	--     annotationsEditedAt for each Class-B field set OR cleared; accept an explicit
    18	--     sync-path timestamp (defaults to now() for the user-edit path).
    19	create or replace function update_video_annotations(
    20	  p_playlist_id uuid, p_video_id text, p_set jsonb, p_clear text[],
    21	  p_edited_at timestamptz default now()
    22	) returns integer language plpgsql security invoker set search_path = public as $$
    23	declare
    24	  allow text[] := array['personalScore','personalNote','corrections','archived'];
    25	  classb text[] := array['personalScore','personalNote','corrections'];
    26	  v_set jsonb := '{}'::jsonb;
    27	  v_stamp jsonb := '{}'::jsonb;
    28	  v_clear text[] := '{}';
    29	  k text; n integer;
    30	  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    31	begin
    32	  for k in select jsonb_object_keys(coalesce(p_set,'{}'::jsonb)) loop
    33	    if k = any(allow) then
    34	      v_set := v_set || jsonb_build_object(k, p_set->k);
    35	      if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    36	    end if;
    37	  end loop;
    38	  -- clears: only allowlisted; each Class-B clear stamps its timestamp
    39	  select coalesce(array_agg(c),'{}') into v_clear
    40	    from unnest(coalesce(p_clear,'{}')) c where c = any(allow);
    41	  foreach k in array v_clear loop
    42	    if k = any(classb) then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    43	  end loop;
    44	
    45	  -- Only touch annotationsEditedAt when there IS a Class-B stamp; an archived-only
    46	  -- (or empty) write must not create an empty annotationsEditedAt:{} (§4.1 "archived-only
    47	  -- write restamps nothing").
    48	  update videos
    49	     set data = case when v_stamp <> '{}'::jsonb
    50	                  then jsonb_set((data || v_set) - v_clear, '{annotationsEditedAt}',
    51	                         coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp, true)
    52	                  else (data || v_set) - v_clear end
    53	   where playlist_id = p_playlist_id and video_id = p_video_id and owner_id = auth.uid();
    54	  get diagnostics n = row_count;
    55	  return n;
    56	end $$;
    57	revoke all on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) from public;
    58	grant execute on function update_video_annotations(uuid, text, jsonb, text[], timestamptz) to authenticated;
    59	
    60	-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
    61	--     present in the patch (a bare MD-finalize / artifact / membership write must NOT bump it).
    62	create or replace function merge_video_data(
    63	  p_playlist_id uuid, p_video_id text, p_fields jsonb,
    64	  p_edited_at timestamptz default now()
    65	) returns void language plpgsql security invoker set search_path = public as $$
    66	declare
    67	  classb text[] := array['personalScore','personalNote','corrections'];
    68	  v_stamp jsonb := '{}'::jsonb; k text;
    69	  ts text := to_char(p_edited_at at time zone 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.MS"Z"');
    70	begin
    71	  perform 1 from playlists
    72	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
    73	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    74	
    75	  foreach k in array classb loop
    76	    if p_fields ? k then v_stamp := v_stamp || jsonb_build_object(k, ts); end if;
    77	  end loop;
    78	
    79	  update videos set
    80	    data = (data || (p_fields - 'artifacts'))
    81	      || case when p_fields ? 'artifacts'
    82	           then jsonb_build_object('artifacts',
    83	                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
    84	           else '{}'::jsonb end
    85	      || case when v_stamp <> '{}'::jsonb
    86	           then jsonb_build_object('annotationsEditedAt',
    87	                  coalesce(data->'annotationsEditedAt','{}'::jsonb) || v_stamp)
    88	           else '{}'::jsonb end,
    89	    updated_at = now()
    90	   where playlist_id = p_playlist_id and video_id = p_video_id;
    91	end $$;
    92	revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
    93	grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
    94	
    95	-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
    96	--     (git show HEAD:supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql)
    97	--     with ONLY two additional keys added to the summary-owned jsonb_build_object:
    98	--     'mdGeneratedAt' and 'mdCorrectionsHash' (§5.7).
    99	create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
   100	  returns void language plpgsql security invoker set search_path = public as $$
   101	declare v_count int;
   102	begin
   103	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
   104	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
   105	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
   106	  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
   107	  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
   108	  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
   109	  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
   110	  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
   111	  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
   112	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
   113	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
   114	  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
   115	  update videos v set
   116	    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
   117	      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
   118	                                                              --     state AND never drop existing summary fields on a
   119	                                                              --     status-only persist (p_video omits them)
   120	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
   121	           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
   122	           'ratings', p_video->'ratings',
   123	           'overallScore', p_video->'overallScore',
   124	           'processedAt', p_video->'processedAt',
   125	           'videoType', p_video->'videoType',
   126	           'audience', p_video->'audience',
   127	           'tags', p_video->'tags',
   128	           'tldr', p_video->'tldr',
   129	           'takeaways', p_video->'takeaways',
   130	           'docVersion', p_video->'docVersion',
   131	           'mdGeneratedAt', p_video->'mdGeneratedAt',
   132	           'mdCorrectionsHash', p_video->'mdCorrectionsHash'))
   133	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
   134	      || jsonb_build_object('artifacts',
   135	           coalesce(v.data->'artifacts', '{}'::jsonb)
   136	           || jsonb_build_object('summaryMd', jsonb_build_object(
   137	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
   138	                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
   139	                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
   140	                -- that IS in committed state, so it must be allowed through (else the row would claim a
   141	                -- promoted artifact for a blob that has not been promoted yet).
   142	                'status', case
   143	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
   144	                                 and p_artifact_status = 'committed'
   145	                                 and v.data->'artifacts'->'summaryMd'->>'key'
   146	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
   147	                              then 'promoted'
   148	                            else p_artifact_status end))),
   149	    updated_at = now()
   150	   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
   151	  get diagnostics v_count = row_count;
   152	  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
   153	end $$;
   154	revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
   155	grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;

exec
/bin/bash -lc "nl -ba lib/storage/local/local-metadata-store.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
     2	import type { Principal } from '@/lib/storage/principal';
     3	import type { PlaylistIndex, Video } from '@/types';
     4	import * as indexStore from '@/lib/index-store';
     5	import { nextSerial } from '@/lib/serial-assign';
     6	
     7	/** Behavior-preserving local impl. Sync index-store calls wrapped in resolved Promises;
     8	 *  the new transactional methods replicate today's pipeline logic against the JSON file. */
     9	export class LocalFsMetadataStore implements MetadataStore {
    10	  async readIndex(p: Principal): Promise<PlaylistIndex> {
    11	    return indexStore.readIndex(p.indexKey);
    12	  }
    13	  async setPlaylistMeta(p: Principal, meta: { playlistUrl: string; playlistTitle?: string }): Promise<void> {
    14	    const idx = indexStore.readIndex(p.indexKey);
    15	    indexStore.writeIndex(p.indexKey, {
    16	      ...idx,
    17	      playlistUrl: meta.playlistUrl,
    18	      outputFolder: p.indexKey,
    19	      ...(meta.playlistTitle ? { playlistTitle: meta.playlistTitle } : {}),
    20	    });
    21	  }
    22	  async claimVideoSlot(p: Principal, videoId: string): Promise<{ position: number; serialNumber: number }> {
    23	    const idx = indexStore.readIndex(p.indexKey);
    24	    const position = idx.videos.length;
    25	    const serialNumber = nextSerial(idx.videos);
    26	    // reserve the slot with a minimal valid Video; real data arrives via upsertVideo
    27	    indexStore.upsertVideo(p.indexKey, { id: videoId, serialNumber } as Video);
    28	    return { position, serialNumber };
    29	  }
    30	  async upsertVideo(p: Principal, video: Video): Promise<void> {
    31	    indexStore.upsertVideo(p.indexKey, video);
    32	  }
    33	  // Stage 3 (§5.1/§5.7): the PRODUCTION Class-B write path (review + regenerate routes call
    34	  // this, not updateVideoAnnotations — see the allowlist-parity note below). When `fields`
    35	  // carries a Class-B key (set or explicit clear via `undefined`), stamp
    36	  // `annotationsEditedAt.<field>` — user path (no opts) → now(), sync path (opts.editedAt)
    37	  // → the caller-supplied source timestamp. A non-Class-B write (e.g. MD-finalize /
    38	  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
    39	  // NOT bump annotationsEditedAt — those are separate, non-human-edit signals.
    40	  async updateVideoFields(
    41	    p: Principal,
    42	    id: string,
    43	    fields: Partial<Video>,
    44	    opts?: { editedAt?: string },
    45	  ): Promise<void> {
    46	    // NOTE: filters inline against the CLASS_B_ANNOTATION_KEYS constant (not
    47	    // indexStore.classBKeysIn) — callers that `jest.mock('lib/index-store')` (auto-mock,
    48	    // no factory) replace every FUNCTION export with a bare jest.fn(), but a plain array
    49	    // constant survives untouched, so this stays correct under that mocking pattern too.
    50	    const changed = Object.keys(fields).filter((k): k is indexStore.ClassBAnnotationKey =>
    51	      (indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    52	    );
    53	    let toWrite: Partial<Video> = fields;
    54	    if (changed.length > 0) {
    55	      const idx = indexStore.readIndex(p.indexKey);
    56	      const existing = idx.videos.find((v) => v.id === id);
    57	      const editedAt = opts?.editedAt ?? new Date().toISOString();
    58	      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing?.annotationsEditedAt ?? {}) };
    59	      for (const k of changed) at[k] = editedAt;
    60	      toWrite = { ...fields, annotationsEditedAt: at };
    61	    }
    62	    indexStore.updateVideoFields(p.indexKey, id, toWrite);
    63	  }
    64	  async bulkUpdateVideoFields(p: Principal, patches: { videoId: string; fields: Partial<Video> }[]): Promise<void> {
    65	    for (const { videoId, fields } of patches) indexStore.updateVideoFields(p.indexKey, videoId, fields);
    66	  }
    67	  async deleteVideo(p: Principal, videoId: string): Promise<void> {
    68	    const idx = indexStore.readIndex(p.indexKey);
    69	    const filtered = idx.videos.filter((v) => v.id !== videoId);
    70	    if (filtered.length === idx.videos.length) return; // id not present — no-op
    71	    indexStore.writeIndex(p.indexKey, { ...idx, videos: filtered });
    72	  }
    73	  async resolvePlaylistId(): Promise<string> {
    74	    throw new Error('resolvePlaylistId is cloud-only (unsupported on the local backend)');
    75	  }
    76	  async deletePlaylist(): Promise<void> {
    77	    throw new Error('deletePlaylist is cloud-only (unsupported on the local backend)');
    78	  }
    79	  // Local parity for the cloud conditional update (Task 3): fills playlistTitle only
    80	  // when currently absent/null in the JSON index; a no-op otherwise.
    81	  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
    82	    const idx = indexStore.readIndex(p.indexKey);
    83	    if (idx.playlistTitle) return { updated: false };
    84	    indexStore.writeIndex(p.indexKey, { ...idx, playlistTitle: title });
    85	    return { updated: true };
    86	  }
    87	  async listPlaylists(): Promise<PlaylistSummary[]> {
    88	    throw new Error('listPlaylists is cloud-only');
    89	  }
    90	  // Interface-shape parity only — not on a local runtime path (the local review route
    91	  // branch is unchanged and still calls updateVideoFields directly). Allowlist applied
    92	  // in-process (the cloud impl enforces it server-side, in SQL); `undefined` values are
    93	  // dropped by JSON.stringify on write, matching updateVideoFields' existing clear-by-
    94	  // undefined convention (see app/api/videos/[id]/review/route.ts serveLocal).
    95	  //
    96	  // Stage 3 (§5.1/§5.7, round-2 N3): this IS the sync loser-write path for a Class-B field
    97	  // (e.g. corrections) — the allowlist widened to include 'corrections' (was silently
    98	  // dropped), and a set/clear of any Class-B key stamps annotationsEditedAt: user path (no
    99	  // opts) → now(), sync path (opts.editedAt) → the caller-supplied source timestamp.
   100	  async updateVideoAnnotations(
   101	    p: Principal,
   102	    videoId: string,
   103	    set: Partial<Pick<Video, 'personalScore' | 'personalNote' | 'archived' | 'corrections'>>,
   104	    clear: ('personalScore' | 'personalNote' | 'corrections')[],
   105	    opts?: { editedAt?: string },
   106	  ): Promise<{ found: boolean }> {
   107	    const idx = indexStore.readIndex(p.indexKey);
   108	    const existing = idx.videos.find((v) => v.id === videoId);
   109	    if (!existing) return { found: false };
   110	
   111	    const allow = new Set(['personalScore', 'personalNote', 'archived', 'corrections']);
   112	    const fields: Partial<Video> = {};
   113	    const changed: indexStore.ClassBAnnotationKey[] = [];
   114	    for (const [k, v] of Object.entries(set)) {
   115	      if (allow.has(k)) {
   116	        (fields as Record<string, unknown>)[k] = v;
   117	        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
   118	          changed.push(k as indexStore.ClassBAnnotationKey);
   119	        }
   120	      }
   121	    }
   122	    for (const k of clear) {
   123	      if (allow.has(k)) {
   124	        (fields as Record<string, unknown>)[k] = undefined;
   125	        if ((indexStore.CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k)) {
   126	          changed.push(k as indexStore.ClassBAnnotationKey);
   127	        }
   128	      }
   129	    }
   130	    if (changed.length > 0) {
   131	      const editedAt = opts?.editedAt ?? new Date().toISOString();
   132	      const at: Partial<Record<indexStore.ClassBAnnotationKey, string>> = { ...(existing.annotationsEditedAt ?? {}) };
   133	      for (const k of changed) at[k] = editedAt;
   134	      fields.annotationsEditedAt = at;
   135	    }
   136	    indexStore.updateVideoFields(p.indexKey, videoId, fields);
   137	    return { found: true };
   138	  }
   139	
   140	  async reconcilePlaylistMembership(p: Principal, currentPlaylistIds: string[]): Promise<void> {
   141	    const present = new Set(currentPlaylistIds);
   142	    const idx = indexStore.readIndex(p.indexKey);
   143	    for (const v of idx.videos) {
   144	      const inPlaylist = present.has(v.id);
   145	      // Mirror original pipeline logic: only touch videos whose archive state should change.
   146	      // A video with removedFromPlaylist=true that is still absent was already handled on a
   147	      // prior sync (or the user manually un-archived it) — leave it untouched.
   148	      if (!inPlaylist && !v.removedFromPlaylist) {
   149	        indexStore.updateVideoFields(p.indexKey, v.id, { archived: true, removedFromPlaylist: true } as Partial<Video>);
   150	      } else if (inPlaylist && v.removedFromPlaylist) {
   151	        indexStore.updateVideoFields(p.indexKey, v.id, { archived: false, removedFromPlaylist: false } as Partial<Video>);
   152	      }
   153	    }
   154	  }
   155	}
   156	
   157	export const localMetadataStore = new LocalFsMetadataStore();

exec
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-metadata-store.ts | sed -n '1,240p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import type { SupabaseClient } from '@supabase/supabase-js';
     2	import type { MetadataStore, PlaylistSummary } from '@/lib/storage/metadata-store';
     3	import type { Principal } from '@/lib/storage/principal';
     4	import type { PlaylistIndex, Video } from '@/types';
     5	import { emptyPlaylistIndex } from '@/lib/storage/empty-index';
     6	
     7	// ---------------------------------------------------------------------------
     8	// stripComputed: drop the DB-computed `updatedAt` and `summaryReady` keys
     9	// before any write to `videos.data`. readIndex() surfaces `updatedAt`
    10	// (sourced from the `updated_at` column/trigger) and `summaryReady` (derived
    11	// from `data.artifacts.summaryMd.status === 'promoted'`) into the Video
    12	// object for read consumers; neither must ever round-trip back into the
    13	// jsonb payload on a write — `updatedAt`'s source of truth is the column/
    14	// trigger, and `summaryReady`'s source of truth is `artifacts.summaryMd.status`
    15	// itself, so persisting a stale derived boolean would let it drift from the
    16	// artifact it's supposed to reflect.
    17	// ---------------------------------------------------------------------------
    18	function stripComputed<T extends object>(v: T): Omit<T, 'updatedAt' | 'summaryReady'> {
    19	  const { updatedAt: _u, summaryReady: _s, ...rest } = v as any;
    20	  return rest;
    21	}
    22	
    23	export class SupabaseMetadataStore implements MetadataStore {
    24	  constructor(private client: SupabaseClient) {}
    25	
    26	  // ---------------------------------------------------------------------------
    27	  // readIndex: select playlist by playlist_key; if absent → emptyPlaylistIndex.
    28	  // ---------------------------------------------------------------------------
    29	  async readIndex(p: Principal): Promise<PlaylistIndex> {
    30	    const { data: pl, error: plErr } = await this.client
    31	      .from('playlists')
    32	      .select('id, playlist_url, playlist_title')
    33	      .eq('playlist_key', p.indexKey)
    34	      .maybeSingle();
    35	    if (plErr) throw plErr;
    36	    if (!pl) return emptyPlaylistIndex(p);
    37	
    38	    const { data: rows, error: vErr } = await this.client
    39	      .from('videos')
    40	      .select('data, updated_at')
    41	      .eq('playlist_id', pl.id)
    42	      .order('position', { ascending: true });
    43	    if (vErr) throw vErr;
    44	
    45	    return {
    46	      playlistUrl: pl.playlist_url,
    47	      outputFolder: p.indexKey,
    48	      ...(pl.playlist_title ? { playlistTitle: pl.playlist_title } : {}),
    49	      videos: (rows ?? []).map((r) => ({
    50	        ...(r.data as Video),
    51	        updatedAt: r.updated_at as string,
    52	        summaryReady:
    53	          (r.data as { artifacts?: { summaryMd?: { status?: string } } })
    54	            .artifacts?.summaryMd?.status === 'promoted',
    55	      })),
    56	    };
    57	  }
    58	
    59	  // ---------------------------------------------------------------------------
    60	  // setPlaylistMeta: upsert on (owner_id, playlist_key).
    61	  // owner_id has NO column default (NOT NULL in schema); must be supplied from
    62	  // the caller's JWT via auth.getUser(). The RLS with-check enforces
    63	  // owner_id = auth.uid() — passing any other value is rejected by the DB.
    64	  // ---------------------------------------------------------------------------
    65	  async setPlaylistMeta(
    66	    p: Principal,
    67	    meta: { playlistUrl: string; playlistTitle?: string },
    68	  ): Promise<void> {
    69	    const { data: userData } = await this.client.auth.getUser();
    70	    const ownerId = userData?.user?.id;
    71	    if (!ownerId) throw new Error('setPlaylistMeta: no authenticated user');
    72	
    73	    const { error } = await this.client.from('playlists').upsert(
    74	      {
    75	        owner_id: ownerId,
    76	        playlist_key: p.indexKey,
    77	        playlist_url: meta.playlistUrl,
    78	        playlist_title: meta.playlistTitle ?? null,
    79	      },
    80	      { onConflict: 'owner_id,playlist_key' },
    81	    );
    82	    if (error) throw error;
    83	  }
    84	
    85	  // ---------------------------------------------------------------------------
    86	  // claimVideoSlot: RPC appends a reservation row and returns position + serial.
    87	  // ---------------------------------------------------------------------------
    88	  async claimVideoSlot(
    89	    p: Principal,
    90	    videoId: string,
    91	  ): Promise<{ position: number; serialNumber: number }> {
    92	    const id = await this.requirePlaylistId(p);
    93	    const { data, error } = await this.client.rpc('claim_video_slot', {
    94	      p_playlist_id: id,
    95	      p_video_id: videoId,
    96	    });
    97	    if (error) throw error;
    98	    const row = Array.isArray(data) ? data[0] : data;
    99	    return { position: row.position, serialNumber: row.serial_number };
   100	  }
   101	
   102	  // ---------------------------------------------------------------------------
   103	  // upsertVideo: UPDATE the reservation row already created by claimVideoSlot.
   104	  // ---------------------------------------------------------------------------
   105	  async upsertVideo(p: Principal, video: Video): Promise<void> {
   106	    const id = await this.requirePlaylistId(p);
   107	    const { error } = await this.client
   108	      .from('videos')
   109	      .update({ data: stripComputed(video) })
   110	      .eq('playlist_id', id)
   111	      .eq('video_id', video.id);
   112	    if (error) throw error;
   113	  }
   114	
   115	  // ---------------------------------------------------------------------------
   116	  // updateVideoFields: server-side artifacts-aware jsonb merge (avoids read-
   117	  // modify-write races; deep-merges the `artifacts` sub-object).
   118	  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
   119	  // when p_fields carries a Class-B key (personalNote/personalScore/corrections) — this
   120	  // just needs to forward the caller's sync-path timestamp (opts.editedAt) as p_edited_at
   121	  // when present; the RPC defaults to now() for the user-edit path when omitted.
   122	  // ---------------------------------------------------------------------------
   123	  async updateVideoFields(
   124	    p: Principal,
   125	    videoId: string,
   126	    fields: Partial<Video>,
   127	    opts?: { editedAt?: string },
   128	  ): Promise<void> {
   129	    const id = await this.requirePlaylistId(p);
   130	    const { error } = await this.client.rpc('merge_video_data', {
   131	      p_playlist_id: id,
   132	      p_video_id: videoId,
   133	      p_fields: stripComputed(fields),
   134	      ...(opts?.editedAt ? { p_edited_at: opts.editedAt } : {}),
   135	    });
   136	    if (error) throw error;
   137	  }
   138	
   139	  // ---------------------------------------------------------------------------
   140	  // bulkUpdateVideoFields: same merge semantics in one transaction.
   141	  // p_patches shape must match the RPC: [{ video_id, fields }].
   142	  // ---------------------------------------------------------------------------
   143	  async bulkUpdateVideoFields(
   144	    p: Principal,
   145	    patches: { videoId: string; fields: Partial<Video> }[],
   146	  ): Promise<void> {
   147	    const id = await this.requirePlaylistId(p);
   148	    const { error } = await this.client.rpc('merge_video_data_bulk', {
   149	      p_playlist_id: id,
   150	      p_patches: patches.map((x) => ({ video_id: x.videoId, fields: stripComputed(x.fields) })),
   151	    });
   152	    if (error) throw error;
   153	  }
   154	
   155	  // ---------------------------------------------------------------------------
   156	  // reconcilePlaylistMembership: archive/restore by membership in one txn.
   157	  // ---------------------------------------------------------------------------
   158	  async reconcilePlaylistMembership(
   159	    p: Principal,
   160	    currentPlaylistIds: string[],
   161	  ): Promise<void> {
   162	    const id = await this.requirePlaylistId(p);
   163	    const { error } = await this.client.rpc('reconcile_membership', {
   164	      p_playlist_id: id,
   165	      p_present: currentPlaylistIds,
   166	    });
   167	    if (error) throw error;
   168	  }
   169	
   170	  // ---------------------------------------------------------------------------
   171	  // deleteVideo: roll back a reserved-but-failed video; scoped by RLS.
   172	  // ---------------------------------------------------------------------------
   173	  async deleteVideo(p: Principal, videoId: string): Promise<void> {
   174	    const id = await this.requirePlaylistId(p);
   175	    const { error } = await this.client
   176	      .from('videos')
   177	      .delete()
   178	      .eq('playlist_id', id)
   179	      .eq('video_id', videoId);
   180	    if (error) throw error;
   181	  }
   182	
   183	  // ---------------------------------------------------------------------------
   184	  // resolvePlaylistId: upsert the (owner, playlist_key) row and return its id
   185	  // atomically. Owner-correct by construction (the upserted row carries
   186	  // owner_id); never a playlist_key-only select.
   187	  // ---------------------------------------------------------------------------
   188	  async resolvePlaylistId(p: Principal, playlistUrl: string): Promise<string> {
   189	    const { data: userData } = await this.client.auth.getUser();
   190	    const ownerId = userData?.user?.id;
   191	    if (!ownerId) throw new Error('resolvePlaylistId: no authenticated user');
   192	    const { data, error } = await this.client.from('playlists')
   193	      .upsert({ owner_id: ownerId, playlist_key: p.indexKey, playlist_url: playlistUrl },
   194	        { onConflict: 'owner_id,playlist_key' })
   195	      .select('id').single();
   196	    if (error) throw error;
   197	    return data.id as string;
   198	  }
   199	
   200	  // ---------------------------------------------------------------------------
   201	  // setPlaylistTitleIfNull: conditional update — fills playlist_title ONLY when it is
   202	  // currently null, so a concurrent ingest's real title (setPlaylistMeta, T2) is never
   203	  // clobbered. Scoped by owner_id (from auth.getUser, mirroring setPlaylistMeta) and
   204	  // playlist_key (p.indexKey) — no separate listId param. `.select('id')` on the update
   205	  // lets us derive `updated` from whether a row actually matched (and was updated), not
   206	  // just whether the statement ran — a no-op conditional update returns an empty array.
   207	  // ---------------------------------------------------------------------------
   208	  async setPlaylistTitleIfNull(p: Principal, title: string): Promise<{ updated: boolean }> {
   209	    const { data: userData } = await this.client.auth.getUser();
   210	    const ownerId = userData?.user?.id;
   211	    if (!ownerId) throw new Error('setPlaylistTitleIfNull: no authenticated user');
   212	
   213	    const { data, error } = await this.client
   214	      .from('playlists')
   215	      .update({ playlist_title: title })
   216	      .eq('owner_id', ownerId)
   217	      .eq('playlist_key', p.indexKey)
   218	      .is('playlist_title', null)
   219	      .select('id');
   220	    if (error) throw error;
   221	    return { updated: (data?.length ?? 0) > 0 };
   222	  }
   223	
   224	  // ---------------------------------------------------------------------------
   225	  // listPlaylists: cloud-only. Session client + RLS (owner_id = auth.uid()) already
   226	  // scopes this, but the explicit .eq('owner_id', ownerId) is defense-in-depth. Ordered
   227	  // by playlist_title (nulls last) then created_at — created_at MUST be in the select
   228	  // since it is both an ORDER BY column and part of the returned PlaylistSummary.
   229	  // ---------------------------------------------------------------------------
   230	  async listPlaylists(ownerId: string): Promise<PlaylistSummary[]> {
   231	    const { data, error } = await this.client
   232	      .from('playlists')
   233	      .select('id, playlist_key, playlist_url, playlist_title, created_at')
   234	      .eq('owner_id', ownerId)
   235	      .order('playlist_title', { nullsFirst: false })
   236	      .order('created_at');
   237	    if (error) throw error;
   238	    return (data ?? []).map((r) => ({
   239	      id: r.id,
   240	      playlistKey: r.playlist_key,

codex
Backend semantics line up for the fields at issue: cloud `merge_video_data` stores JSON nulls and deep-merges `artifacts`, while local shallow-spreads nulls. I’m checking whether any of that creates a round-3 finding rather than just leaving the accepted medium about non-`summaryMd` artifacts.
exec
/bin/bash -lc "nl -ba lib/index-store.ts | sed -n '1,190p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import crypto from 'crypto';
     2	import fs from 'fs';
     3	import os from 'os';
     4	import path from 'path';
     5	import type { PlaylistIndex, Video } from '../types';
     6	
     7	const INDEX_FILE = 'playlist-index.json';
     8	const VIDEO_ID_RE = /^[A-Za-z0-9_-]{1,20}$/;
     9	
    10	// Stage 3 Cloud Sync (§5.1/§5.7): Class-B ("human-edited") annotation fields — a set or a
    11	// clear of any of these stamps `annotationsEditedAt.<field>` (user path → now(), sync path
    12	// → the caller-supplied source timestamp). Shared by LocalFsMetadataStore's
    13	// updateVideoAnnotations and updateVideoFields so both write paths stamp identically.
    14	export const CLASS_B_ANNOTATION_KEYS = ['personalNote', 'personalScore', 'corrections'] as const;
    15	export type ClassBAnnotationKey = (typeof CLASS_B_ANNOTATION_KEYS)[number];
    16	
    17	/** Class-B keys present as OWN properties of `fields` (set to a value OR explicitly
    18	 *  cleared via `undefined`) — i.e. the keys that must stamp annotationsEditedAt. A key
    19	 *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
    20	 *  "changed" and must not trigger a stamp. */
    21	export function classBKeysIn(fields: Partial<Video>): ClassBAnnotationKey[] {
    22	  return Object.keys(fields).filter((k): k is ClassBAnnotationKey =>
    23	    (CLASS_B_ANNOTATION_KEYS as readonly string[]).includes(k),
    24	  );
    25	}
    26	
    27	// Fields retired by the PDF-generation removal (summaryPdf/deepDivePdf) and the
    28	// deep-dive removal (deepDiveMd/deepDiveHtml/deepDiveVersion). Index files written
    29	// before those efforts still carry these keys; strip them on read so the API never
    30	// re-serves dangling references to deleted files.
    31	const RETIRED_VIDEO_KEYS = [
    32	  'summaryPdf',
    33	  'deepDiveMd',
    34	  'deepDiveHtml',
    35	  'deepDivePdf',
    36	  'deepDiveVersion',
    37	] as const;
    38	
    39	function stripRetiredKeys(index: PlaylistIndex): PlaylistIndex {
    40	  for (const video of index.videos ?? []) {
    41	    for (const key of RETIRED_VIDEO_KEYS) {
    42	      delete (video as Record<string, unknown>)[key];
    43	    }
    44	  }
    45	  return index;
    46	}
    47	
    48	export function assertOutputFolder(outputFolder: string): void {
    49	  const resolved = path.resolve(outputFolder);
    50	  const home = os.homedir();
    51	  const withinHome = (p: string) => p === home || p.startsWith(home + path.sep);
    52	
    53	  if (!withinHome(resolved)) {
    54	    throw Object.assign(new Error(`outputFolder outside home directory: ${resolved}`), { statusCode: 400 });
    55	  }
    56	
    57	  // Also check the real path to catch symlinks that point outside home
    58	  try {
    59	    const real = fs.realpathSync.native(resolved);
    60	    if (!withinHome(real)) {
    61	      throw Object.assign(new Error(`outputFolder resolves outside home directory via symlink: ${real}`), { statusCode: 400 });
    62	    }
    63	  } catch (err: unknown) {
    64	    const nodeErr = err as NodeJS.ErrnoException;
    65	    if ((nodeErr as any).statusCode === 400) throw err;
    66	    // ENOENT means path doesn't exist yet — no symlink to follow, trust resolved path
    67	    if (nodeErr.code !== 'ENOENT') throw err;
    68	  }
    69	}
    70	
    71	export function assertVideoId(id: string): void {
    72	  if (!VIDEO_ID_RE.test(id)) {
    73	    throw Object.assign(new Error(`invalid videoId: ${id}`), { statusCode: 400 });
    74	  }
    75	}
    76	
    77	function indexPath(outputFolder: string): string {
    78	  return path.join(outputFolder, INDEX_FILE);
    79	}
    80	
    81	export function readIndex(outputFolder: string): PlaylistIndex {
    82	  assertOutputFolder(outputFolder);
    83	  const filePath = indexPath(outputFolder);
    84	  try {
    85	    const raw = fs.readFileSync(filePath, 'utf-8');
    86	    return stripRetiredKeys(JSON.parse(raw) as PlaylistIndex);
    87	  } catch (err: unknown) {
    88	    const nodeErr = err as NodeJS.ErrnoException;
    89	    if (nodeErr.code === 'ENOENT') {
    90	      // Distinguish missing file from missing directory
    91	      try { fs.lstatSync(outputFolder); } catch {
    92	        throw Object.assign(new Error(`Output folder does not exist: ${outputFolder}`), { statusCode: 400, cause: err });
    93	      }
    94	      return { playlistUrl: '', outputFolder, videos: [] };
    95	    }
    96	    throw Object.assign(new Error(`Failed to read ${filePath}: ${nodeErr.message}`), { cause: err });
    97	  }
    98	}
    99	
   100	export function writeIndex(outputFolder: string, index: PlaylistIndex): void {
   101	  assertOutputFolder(outputFolder);
   102	  for (const video of index.videos) {
   103	    assertVideoId(video.id);
   104	  }
   105	  const filePath = indexPath(outputFolder);
   106	  const tmpPath = filePath + '.' + crypto.randomUUID() + '.tmp';
   107	  try {
   108	    fs.writeFileSync(tmpPath, JSON.stringify(index, null, 2), 'utf-8');
   109	    fs.renameSync(tmpPath, filePath);
   110	  } catch (err) {
   111	    try { fs.unlinkSync(tmpPath); } catch { /* ignore cleanup error */ }
   112	    throw err;
   113	  }
   114	}
   115	
   116	export function upsertVideo(outputFolder: string, video: Video): void {
   117	  assertOutputFolder(outputFolder);
   118	  assertVideoId(video.id);
   119	  const index = readIndex(outputFolder);
   120	  const i = index.videos.findIndex((v) => v.id === video.id);
   121	  // Stamp only the single mutated video — never touch writeIndex, which
   122	  // rewrites the whole playlist file and would re-stamp every sibling video.
   123	  const stamped: Video = { ...video, updatedAt: new Date().toISOString() };
   124	  if (i === -1) {
   125	    index.videos.push(stamped);
   126	  } else {
   127	    index.videos[i] = stamped;
   128	  }
   129	  writeIndex(outputFolder, index);
   130	}
   131	
   132	export function updateVideoFields(outputFolder: string, id: string, fields: Partial<Video>): void {
   133	  assertOutputFolder(outputFolder);
   134	  assertVideoId(id);
   135	  const index = readIndex(outputFolder);
   136	  const i = index.videos.findIndex((v) => v.id === id);
   137	  if (i === -1) {
   138	    throw new Error(`Video not found in index: ${id}`);
   139	  }
   140	  // Exclude id from fields — callers must not change a video's identity
   141	  const { id: _discarded, ...safeFields } = fields;
   142	  // Stamp only the single mutated video — never touch writeIndex, which
   143	  // rewrites the whole playlist file and would re-stamp every sibling video.
   144	  index.videos[i] = { ...index.videos[i], ...safeFields, updatedAt: new Date().toISOString() };
   145	  writeIndex(outputFolder, index);
   146	}

exec
/bin/bash -lc "nl -ba lib/html-doc/build-doc-html.ts app/api/videos/[id]/dig-state/route.ts lib/pdf/pdf-path.ts lib/html-doc/dig-merge.ts lib/dig/companion-doc.ts | sed -n '1,260p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
usage: nl [-p] [-b type] [-d delim] [-f type] [-h type] [-i incr] [-l num]
          [-n format] [-s sep] [-v startnum] [-w width] [file]

exec
/bin/bash -lc 'rg -n "summaryMd|digDeeperMd|data-root|dig|M2a|out of scope|Stage 3|baseline|corrections" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
1:# Stage 3 — Cloud Sync (local ↔ cloud reconciliation) — Design Spec
7:wording. The **two-class model** (generated=format/corrections-currency; human=per-field newer-wins) is
9:Required code preconditions ship with M2a (§5.7). **Awaiting user approval → implementation plan (Phase 2).**
24:- **M2a — THIS spec:** local↔cloud reconciliation of each video's **summary** (LLM-generated MD + model) and
25:  **human edits** (rating/note/corrections), both directions, per the two-class rules (§5). Honest
26:  **additive** create with **baseline-aware** delete-suppression. Manual trigger.
27:- **M2b — later slice (own spec):** deep-dive/dig **+ slide images** via the cloud-tokens → local-capture →
31:**In scope (M2a):** summary MD + model-JSON companion; human fields (`corrections`, `personalNote`,
35:**Out of scope (M2a):** deep-dive/dig + slide images (M2b, §13); tombstone delete propagation; background
47:| **Class B — human** | Author edits: **`corrections`, `personalNote`, `personalScore`**. Reconciled **per field, newer-wins, additive**; preserved across every format (§5.4). |
63:## 4. What syncs (M2a) — three classes
66:- **Class A — generated (reconcile by corrections-currency + format, §5.3):** summary **MD** (section-timestamp
83:- **`corrections` — human field AND the MD's generation input (special):** reconciled as a human field (§5.4,
84:  newer-wins, preserved) AND tracked as the MD's **corrections-currency** — because `corrections` is *applied
89:  `summaryReady`. **`archived` is replica-local in M2a but stays fully writable** — it has *two* semantics
92:  field, M2a does **not** sync `archived` (avoids the membership flip-flop) but must **keep it in the
103:- `ModelEnvelope` gains an OPTIONAL **`sourceMdHash`** — an **MD-body-only** digest (§5.2), set going
118:- **Class A:** `docVersion.major` (format — the decider), `mdHash` (the MD-body-only §5.2 digest = the
120:  **`mdCorrectionsHash`** — the §5.2 hash of the `corrections` value this MD was generated/fixed from, for
121:  corrections-currency (§5.3). `docVersion.minor` (HTML style) is **ignored** — sync moves MD, not HTML;
123:- **Class B / `corrections`:** each field's value + a **PER-FIELD** timestamp,
124:  `annotationsEditedAt.{personalNote, personalScore, corrections}` — a same-field tie compares *that field's*
129:  (`update_video_annotations` `0016`; `merge_video_data`/`updateVideoFields` for `corrections` — **conditional
135:  `now()`) — so the baseline records true authorship and later ties compare real edit times.
138:`mdHash` is an **MD-body-only** canonical digest — a shared impl (`lib/cloud-sync/content-hash.ts`) called
143:### 5.3 Class A reconcile (generated MD + model) — corrections-currency FIRST, then format
145:"better"). But `corrections` is *applied into* the MD, so a **corrected** MD is not an equivalent variant of
146:an uncorrected one (round-v7 Codex-H1). `corrections` is reconciled **first** (§5.4); an MD is
147:**corrections-current** iff `mdCorrectionsHash == hash(reconciled corrections)`. Priority: **corrections-
150:Evaluate **corrections-currency first**, so the `mdHash`-equal skip never hides a stale summary (round-v8 H-1):
154:| `mdHash` equal **and** (both corrections-current, or both equally stale-and-format-equal) | **skip** — but if **both are stale** vs the reconciled corrections, still **flag `needs_regen`** (identical stale MDs must not bypass the R8 report) |
155:| One MD corrections-current, the other corrections-stale | **corrections-current wins** — never overwrite a corrected MD with a stale higher-format one. Copy it (+ companion §4.2 + carried scalars). |
156:| Both corrections-current (or both equally stale), `docVersion.major` differs | **higher `major` wins** (format upgrade; never downgrade) |
157:| Both corrections-current, same `major`, `mdHash` differs (equivalent LLM variants) | **unify** — newer `mdGeneratedAt` wins; copy so the prose **converges** (intention-respecting tie-break, not a quality claim; avoids undoing a deliberate re-generation) |
158:| **Neither** MD reflects the reconciled corrections (both stale) | keep the higher-major MD but **flag `needs_regen`** (report it, §7 step 6) — the author regenerates to apply the corrections at the current format; sync **never fabricates** a corrected MD (residual **R8**) |
159:| Present on only one side (never in this replica's baseline) | **copy** (hydrate / publish) |
165:corrections-stale-or-equivalent, and the `corrections` instruction survives (§5.4) and re-applies on regen.
168:### 5.4 Class B / `corrections` reconcile — per-field 3-way merge, clear-aware (runs BEFORE §5.3)
169:Human fields (`personalNote`, `personalScore`, `corrections`) are precious and **carried across every
170:format**. Each reconciles **independently** against the manifest baseline (§8). **Absence is a value** (a
171:*clear*), not "never had" (round-v7 H-2), **and "changed vs baseline" is judged on the field's
174:baseline), and a **same-value re-add** (clear then re-type the same text) counts as *changed* because its
176:as "the `(value, annotationsEditedAt)` pair differs from baseline":
178:| Per-field state vs baseline | Action |
181:| Only one side changed vs baseline (incl. a **clear** = baseline-present→absent) | take the changed side — **propagate the edit or the clear** |
182:| **Both** changed vs baseline (different values, incl. one cleared) | newer **per-field `annotationsEditedAt`** wins + log (R1) |
183:| No baseline (fresh device) + differ | newer per-field `annotationsEditedAt` wins + log |
184:| Present one side, absent other, **no baseline** | copy (additive hydration) |
187:cleared field is **not** resurrected (with a baseline, present-vs-absent is a real change → the clear
189:`corrections` reconciles here too and, because it feeds §5.3's corrections-currency, is reconciled **first**.
199:### 5.6 Presence & deletes — additive + baseline-aware (rounds 2–4)
200:- One-sided, never in this replica's baseline → additive **create** (a pure metadata/doc copy that **never**
203:- In this replica's baseline but **absent on the other side** → **remote delete**: do not re-create.
204:- In this replica's baseline but **absent on this side** (this replica deleted it) → do not re-create
206:- **Residual R2:** a replica with **no baseline** (fresh device / lost manifest) can't tell "deleted
211:The reconcile signals are new; these ship **with** M2a (round-v7 H-4/M-1/M-2 flagged that the code
214:  personalScore?, corrections?}` (datetimes). One-time backfill per §5.5.
218:- **`update_video_annotations` (`0016`) allowlist → `{personalScore, personalNote, corrections, archived}`** —
219:  **ADD** `corrections` (Class B, currently dropped); **KEEP** `archived` so the manual Archive button keeps
221:  **only the changed Class-B field's** `annotationsEditedAt` (a `corrections`/`personalNote`/`personalScore`
254:   `summaryMd`/artifact status, `mdHash`, `docVersion`, `mdGeneratedAt`, **`mdCorrectionsHash`**, and **all
257:   unadvanced baseline; re-run heals. The **companion model** blob is best-effort, outside the MD's atomic
262:   human field `(value, annotationsEditedAt)` pairs. Never advance a baseline for a partial transfer.
265:   corrections at the top format — author should regenerate, §5.3/R8) / **`archived_not_synced`** (manual
279:One git-ignored file per playlist (`<data-root>/<playlist_key>/.cloud-sync-manifest.json`), recording per
280:`video_id` the last-synced baseline: **Class A** (`docVersion`, `mdGeneratedAt`, `mdCorrectionsHash`,
281:receiver-observed `mdHash`) and **Class B** (the last-synced `corrections`/`personalNote`/`personalScore`
284:the Class-A tie baseline, and the Class-B 3-way-merge baseline. Lost/corrupt manifest degrades to a direct
303:- **Class A (corrections-currency + format):** higher-major wins over a newer-timestamp lower-major
304:  (anti-recency); **a stale higher-major MD does NOT overwrite a corrections-current lower-major MD**
312:  **cleared** field is **not** resurrected (baseline-aware clear propagates, round-v7 H-2); same-field-both-
324:  advertises a hash for a missing blob nor advances the baseline; baseline-present remote-delete not
329:## 11. Accepted residuals (M2a)
342:- **R8 — `needs_regen` (corrections/format skew):** if no replica has an MD reflecting the current
343:  `corrections` at the top format (e.g. corrections applied on an older-code replica), sync keeps the best
344:  available MD (corrections-current if any, else the highest format) but flags `needs_regen` — the summary is
346:  `corrections`). Sync never fabricates a corrected MD; nothing is lost (the instruction survives, §5.4).
351:  → accepted for M2a; a `scalarsSourceMdHash` provenance guard is a possible M2b hardening.
352:- **R10 — `archived` not synced (round-v9).** Manual Archive/Unarchive stays **per-replica** in M2a (a manual
366:3. **Class B (independent per-field merge) = `personalNote`/`personalScore`; `corrections` is special** — a
368:   corrections-currency (a stale MD never overwrites a corrected one). **`title` is NOT Class B** (YouTube-
374:6. **Deletes: additive + baseline-aware**; resurrection on a baseline-less replica = R2; tombstones = M2b.
386:- **But cloud DOES produce the capture *tokens*.** Gemini's dig output emits **`[[SLIDE:M:SS|M:SS|
387:  caption]]`** tokens (`lib/dig/generate.ts:79` — "FIRST M:SS = visual fully built; SECOND = it leaves"),
390:- **Local resolves tokens → pixels** (`lib/dig/slides.ts`: `yt-dlp --download-sections` + `ffmpeg`, anchored
392:- **The M2b pipeline** is therefore: **cloud generates dig text + slide tokens → sync to local → local
395:- **M2b reconcile shape:** dig MD (with tokens) reconciles like **Class A** (format/version, incl. a

exec
/bin/bash -lc "rg -n \"readMdBody\\(|deriveClassASignals\\(|writeVideoBaseline\\(|copyAdditiveVideo\\(|transferClassA\\(|companionTransfer\\(|needsRegen|spendLedger|spend_ledger|enqueue\" lib/cloud-sync tests/lib/cloud-sync tests/integration/cloud-sync" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/lib/cloud-sync/manifest.test.ts:25:  await writeVideoBaseline(r, 'PL1', 'v1', base as any);
tests/integration/cloud-sync/sync-run.int.test.ts:27:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:33:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/sync-run.int.test.ts:61:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/sync-run.int.test.ts:71:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/lib/cloud-sync/reconcile-class-a.test.ts:13:      .toEqual({ action: 'skip', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:15:  it('mdHash equal but BOTH stale vs reconciled corrections → skip but needsRegen (round-v8 H-1)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:17:    expect(r).toEqual({ action: 'skip', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:21:    expect(r).toEqual({ action: 'copyToCloud', needsRegen: false }); // local current tuple → cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:23:  it('mdHash equal, both stale, DIFFERENT major → higher major wins + needsRegen, NOT skip (Blocking ③ scenario 2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:25:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:31:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local (current) overwrites cloud
tests/lib/cloud-sync/reconcile-class-a.test.ts:37:      .toEqual({ action: 'copyToLocal', needsRegen: false }); // cloud (major 3) → local
tests/lib/cloud-sync/reconcile-class-a.test.ts:43:      .toEqual({ action: 'copyToCloud', needsRegen: false }); // local newer → cloud converges
tests/lib/cloud-sync/reconcile-class-a.test.ts:45:  it('neither current (both stale) → keep higher-major, flag needsRegen', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:49:    expect(r).toEqual({ action: 'copyToLocal', needsRegen: true }); // cloud higher major → local, but stale
tests/lib/cloud-sync/reconcile-class-a.test.ts:51:  it('present only one side (current) → copy, no needsRegen (hydrate/publish)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:53:      .toEqual({ action: 'copyToLocal', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:55:      .toEqual({ action: 'copyToCloud', needsRegen: false });
tests/lib/cloud-sync/reconcile-class-a.test.ts:57:  it('one-sided hydrate of a corrections-STALE MD flags needsRegen (L2)', () => {
tests/lib/cloud-sync/reconcile-class-a.test.ts:59:      .toEqual({ action: 'copyToLocal', needsRegen: true });
tests/lib/cloud-sync/reconcile-class-a.test.ts:63:      .toEqual({ action: 'skip', needsRegen: false });
lib/cloud-sync/manifest.ts:31:export async function writeVideoBaseline(
tests/integration/cloud-sync/e2e.int.test.ts:9:// Money invariant: a sync copy NEVER charges — every additive/transfer row asserts spendLedgerTotal
tests/integration/cloud-sync/e2e.int.test.ts:10:// is unchanged (or a whole-suite money check). No producer/enqueue is on the sync path.
tests/integration/cloud-sync/e2e.int.test.ts:70:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:75:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore); // sync copy never charges
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:232:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:237:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:354:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:365:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:405:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:413:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);
tests/integration/cloud-sync/e2e.int.test.ts:523:  //    (safe-but-stuck until a human edits corrections). The conflict is still logged + needsRegen.
tests/integration/cloud-sync/e2e.int.test.ts:536:    const spendBefore = await ctx.spendLedgerTotal();
tests/integration/cloud-sync/e2e.int.test.ts:542:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);             // MD is corrections-stale
tests/integration/cloud-sync/e2e.int.test.ts:543:    expect(await ctx.spendLedgerTotal()).toBe(spendBefore);          // sync copy never charges
lib/cloud-sync/backfill.ts:7:export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
tests/lib/cloud-sync/backfill.test.ts:15:  const s = deriveClassASignals(legacy, BODY);
tests/lib/cloud-sync/backfill.test.ts:22:  const s = deriveClassASignals(legacy, BODY);
tests/lib/cloud-sync/backfill.test.ts:29:  const s = deriveClassASignals({ ...legacy, summaryMd: null }, null);
tests/lib/cloud-sync/backfill.test.ts:35:  const s = deriveClassASignals({ ...legacy, mdGeneratedAt: '2026-03-03T00:00:00.000Z', mdCorrectionsHash: 'h', docVersion: { major: 3, minor: 3 } }, BODY);
lib/cloud-sync/reconcile-class-a.ts:5:  needsRegen: boolean;
lib/cloud-sync/reconcile-class-a.ts:20:  // Presence (§5.6 one-sided copy) — flag needsRegen when the SOLE MD is corrections-stale (R8, L2)
lib/cloud-sync/reconcile-class-a.ts:21:  if (!lHas && !cHas) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:22:  if (!lHas) return { action: 'copyToLocal', needsRegen: !current(cloud, cur) };
lib/cloud-sync/reconcile-class-a.ts:23:  if (!cHas) return { action: 'copyToCloud', needsRegen: !current(local, cur) };
lib/cloud-sync/reconcile-class-a.ts:33:    if (lCur && cCur) return { action: 'skip', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:34:    if (bothStale && local.docVersionMajor === cloud.docVersionMajor) return { action: 'skip', needsRegen: true };
lib/cloud-sync/reconcile-class-a.ts:39:  if (lCur && !cCur) return { action: 'copyToCloud', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:40:  if (cCur && !lCur) return { action: 'copyToLocal', needsRegen: false };
lib/cloud-sync/reconcile-class-a.ts:45:    return { action: winnerIsCloud ? 'copyToLocal' : 'copyToCloud', needsRegen: bothStale };
lib/cloud-sync/reconcile-class-a.ts:50:  return { action: winnerIsLocal ? 'copyToCloud' : 'copyToLocal', needsRegen: bothStale };
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:59:async function readMdBody(blob: BlobStore, p: Principal, video: Video): Promise<string | null> {
lib/cloud-sync/sync-run.ts:143: *  promoted status ONLY when the blob is durable) → verify the receiver row exists. Never enqueues,
lib/cloud-sync/sync-run.ts:145:async function copyAdditiveVideo(
lib/cloud-sync/sync-run.ts:276:async function transferClassA(
lib/cloud-sync/sync-run.ts:279:  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
lib/cloud-sync/sync-run.ts:345:async function companionTransfer(
lib/cloud-sync/sync-run.ts:420:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:457:            const body = await readMdBody(from.blob, from.p, present);
lib/cloud-sync/sync-run.ts:458:            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
lib/cloud-sync/sync-run.ts:460:            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
lib/cloud-sync/sync-run.ts:461:              deriveClassASignals(present, body), body ? mdHash(body) : null,
lib/cloud-sync/sync-run.ts:491:        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
lib/cloud-sync/sync-run.ts:492:        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
lib/cloud-sync/sync-run.ts:499:        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
lib/cloud-sync/sync-run.ts:502:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:504:          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
lib/cloud-sync/sync-run.ts:510:        if (decision.needsRegen) report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:520:          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
lib/cloud-sync/sync-run.ts:524:          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
lib/cloud-sync/sync-run.ts:532:          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
lib/cloud-sync/sync-run.ts:539:        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));

codex
I haven’t found a new Blocking/High so far. The only live concern is lower severity: the M-R2-2 regression test proves first-run hydration, but it does not assert second-run idempotency or manifest shape for that new branch. I’m deciding whether that is a defect or only a coverage gap.
exec
/bin/bash -lc "nl -ba lib/html-doc/build-doc-html.ts | sed -n '1,130p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import fs from 'fs';
     2	import path from 'path';
     3	import type { Video } from '@/types';
     4	import { renderDigDeeperDoc } from './render-dig-deeper';
     5	import { GENERATOR_VERSION } from './render';
     6	import { reRenderSummaryHtml } from './rerender';
     7	import { readModelEnvelope } from './model-store';
     8	import { getPrincipal } from '@/lib/storage/resolve';
     9	import { parseDugSections } from '../dig/companion-doc';
    10	import { parseSummaryMarkdown } from './parse';
    11	import { prepareSlideCropMap } from '../dig/slide-crop-map';
    12	import { assertIndexRelPathWithin } from '../paths/assert-within';
    13	
    14	export type BuildResult =
    15	  | { ok: true; html: string }
    16	  | { ok: false; reason: 'missing-html' | 'missing-summary' | 'invalid-path' | 'unparseable' };
    17	
    18	// Unicode-aware so Korean-slug filenames are admitted. The resolved-path containment check below is the
    19	// real traversal backstop; this regex still forbids slashes (no "../"). Kept verbatim from the serve
    20	// route so the stronger htmls/ guard is NOT downgraded to generic output-folder containment.
    21	const HTML_REL_RE = /^htmls\/[\p{L}\p{N}._-]+\.html$/u;
    22	
    23	const UNAVAILABLE_HTML =
    24	  `<!DOCTYPE html><html><body><p>Summary unavailable — regenerate the summary first.</p></body></html>`;
    25	
    26	/**
    27	 * Build the self-contained HTML for a doc, identically to what `GET /api/html/[id]` serves.
    28	 * Returns a domain result — callers (serve route, PDF route) map reasons to HTTP.
    29	 *
    30	 * `video` must already be resolved from the index by the caller (both routes read the index anyway).
    31	 * Input validation (outputFolder/videoId/type) stays in the route (an HTTP concern).
    32	 */
    33	export async function buildDocHtml(
    34	  video: Video,
    35	  outputFolder: string,
    36	  type: 'summary' | 'dig-deeper',
    37	): Promise<BuildResult> {
    38	  const htmlDir = path.resolve(outputFolder, 'htmls');
    39	
    40	  if (type === 'summary') {
    41	    const htmlFile = video.summaryHtml;
    42	    if (!htmlFile) return { ok: false, reason: 'missing-html' };
    43	    // Preserve the stronger htmls/*.html guard (regex + htmlDir containment).
    44	    if (!HTML_REL_RE.test(htmlFile)) return { ok: false, reason: 'missing-html' };
    45	    const abs = path.resolve(outputFolder, htmlFile);
    46	    if (abs !== htmlDir && !abs.startsWith(htmlDir + path.sep)) return { ok: false, reason: 'invalid-path' };
    47	
    48	    let cachedHtml: string;
    49	    try {
    50	      cachedHtml = fs.readFileSync(abs, 'utf-8');
    51	    } catch {
    52	      return { ok: false, reason: 'missing-html' };
    53	    }
    54	    const generatorMatch = cachedHtml.match(/<meta name="generator" content="([^"]*)">/);
    55	    const cachedVersion = generatorMatch ? generatorMatch[1] : null;
    56	    if (cachedVersion === GENERATOR_VERSION) return { ok: true, html: cachedHtml };
    57	
    58	    // Cached HTML is stale — attempt re-render; serve the stale artifact on any skip (never fail when
    59	    // a cached file exists).
    60	    const result = await reRenderSummaryHtml(video.id, outputFolder);
    61	    switch (result.status) {
    62	      case 'rerendered':
    63	        return { ok: true, html: result.html };
    64	      case 'skipped-not-eligible':
    65	        return { ok: true, html: cachedHtml };
    66	      default:
    67	        console.warn(`[html/summary] rerender skipped (${result.status}) for video ${video.id}`);
    68	        return { ok: true, html: cachedHtml };
    69	    }
    70	  }
    71	
    72	  // dig-deeper
    73	  // Companion-path containment first, so it keeps independent 400 coverage before summaryMd derivation.
    74	  let digDeeperPath: string | null = null;
    75	  if (video.digDeeperMd) {
    76	    try {
    77	      digDeeperPath = assertIndexRelPathWithin(outputFolder, video.digDeeperMd);
    78	    } catch {
    79	      return { ok: false, reason: 'invalid-path' };
    80	    }
    81	  }
    82	
    83	  // Derive base + relDir from index fields only (never from URL).
    84	  let base: string;
    85	  let relDir: string;
    86	  if (video.digDeeperMd) {
    87	    const digRel = video.digDeeperMd;
    88	    relDir = path.dirname(digRel);
    89	    const digBase = path.basename(digRel);
    90	    base = digBase.endsWith('-dig-deeper.md')
    91	      ? digBase.slice(0, -'-dig-deeper.md'.length)
    92	      : digBase.replace(/\.md$/, '');
    93	  } else if (video.summaryMd) {
    94	    const sumRel = video.summaryMd;
    95	    relDir = path.dirname(sumRel);
    96	    const sumBase = path.basename(sumRel);
    97	    base = sumBase.endsWith('.md') ? sumBase.slice(0, -'.md'.length) : sumBase;
    98	  } else {
    99	    return { ok: true, html: UNAVAILABLE_HTML };
   100	  }
   101	
   102	  let summaryMdPath: string;
   103	  try {
   104	    summaryMdPath = assertIndexRelPathWithin(outputFolder, path.join(relDir, `${base}.md`));
   105	    assertIndexRelPathWithin(outputFolder, path.join('models', `${base}.json`));
   106	  } catch {
   107	    return { ok: false, reason: 'invalid-path' };
   108	  }
   109	
   110	  let summaryMdContent: string;
   111	  try {
   112	    summaryMdContent = fs.readFileSync(summaryMdPath, 'utf-8');
   113	  } catch {
   114	    return { ok: true, html: UNAVAILABLE_HTML };
   115	  }
   116	
   117	  let parsed;
   118	  try {
   119	    parsed = parseSummaryMarkdown(summaryMdContent);
   120	  } catch {
   121	    return { ok: true, html: UNAVAILABLE_HTML };
   122	  }
   123	
   124	  const envelope = await readModelEnvelope(getPrincipal(outputFolder), base);
   125	
   126	  let dug: ReturnType<typeof parseDugSections> = [];
   127	  if (digDeeperPath !== null) {
   128	    try {
   129	      dug = parseDugSections(fs.readFileSync(digDeeperPath, 'utf8'));
   130	    } catch {

exec
/bin/bash -lc "nl -ba app/api/videos/[id]/dig-state/route.ts | sed -n '70,115p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    70	  try {
    71	    principal = getPrincipal(outputFolder);
    72	    assertVideoId(videoId);
    73	  } catch {
    74	    return new Response(JSON.stringify({ error: 'invalid request' }), { status: 400 });
    75	  }
    76	
    77	  let video;
    78	  try {
    79	    const index = await getStorageBundle().metadataStore.readIndex(principal);
    80	    video = index.videos.find((v) => v.id === videoId);
    81	    if (!video) {
    82	      return new Response(JSON.stringify({ error: 'video not found' }), { status: 404 });
    83	    }
    84	  } catch (err) {
    85	    const e = err as { statusCode?: number; message?: string };
    86	    if (e.statusCode === 400) {
    87	      return new Response(JSON.stringify({ error: e.message }), { status: 400 });
    88	    }
    89	    throw err;
    90	  }
    91	
    92	  const digDeeperMd = video.digDeeperMd;
    93	  if (!digDeeperMd) {
    94	    return new Response(JSON.stringify({ sectionIds: [] }), {
    95	      headers: { 'Content-Type': 'application/json' },
    96	    });
    97	  }
    98	
    99	  const digDeeperPath = path.join(outputFolder, digDeeperMd);
   100	  const sectionIds = await readDugSectionIds(digDeeperPath);
   101	
   102	  return new Response(JSON.stringify({ sectionIds }), {
   103	    headers: { 'Content-Type': 'application/json' },
   104	  });
   105	}

exec
/bin/bash -lc "nl -ba lib/pdf/pdf-path.ts | sed -n '1,60p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import path from 'path';
     2	import type { Video } from '@/types';
     3	
     4	/**
     5	 * Derive the PDF output path (relative to outputFolder) for a doc.
     6	 *
     7	 * Pure string derivation — path containment is enforced by the caller via
     8	 * `assertIndexRelPathWithin(outputFolder, rel)`.
     9	 *
    10	 * - summary:    `pdfs/{basename(summaryMd) sans .md}.pdf`
    11	 * - dig-deeper: `pdfs/{basename(digDeeperMd) with -dig-deeper.md -> -dig-deeper}.pdf`
    12	 *
    13	 * `base` matches how the serve route derives filenames, so the PDF sits alongside the
    14	 * htmls/{base}.html it renders.
    15	 */
    16	export function pdfRelPath(video: Video, type: 'summary' | 'dig-deeper'): string {
    17	  let base: string;
    18	  if (type === 'dig-deeper') {
    19	    if (!video.digDeeperMd) throw new Error('no dig-deeper doc for this video');
    20	    const b = path.basename(video.digDeeperMd);
    21	    base = b.endsWith('-dig-deeper.md')
    22	      ? `${b.slice(0, -'-dig-deeper.md'.length)}-dig-deeper`
    23	      : b.replace(/\.md$/, '');
    24	  } else {
    25	    if (!video.summaryMd) throw new Error('no summary for this video');
    26	    base = path.basename(video.summaryMd).replace(/\.md$/, '');
    27	  }
    28	  return `pdfs/${base}.pdf`;
    29	}

exec
/bin/bash -lc "nl -ba lib/html-doc/dig-merge.ts | sed -n '1,230p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	/**
     2	 * dig-merge.ts — pure function that merges GIST (model) + DUG (companion) data
     3	 * for a single video, producing one MergedSection per summary section in order.
     4	 *
     5	 * Keying contract (spec §3a):
     6	 *   - One MergedSection per summary.sections[i], in order.
     7	 *   - startSec = section.timeRange?.startSec ?? null.
     8	 *   - GIST trusted only if: envelope non-null AND sameTitles(parsedTitles, envelope.sourceSections)
     9	 *     AND envelope.model.sections[i] exists → { lead, bullets }; otherwise gist = null (skeleton).
    10	 *   - DUG match step 1: DugSection.sectionId === section.startSec (exact numeric match).
    11	 *     Step 2 fallback: any not-yet-consumed DugSection matched to a not-yet-dug summary section
    12	 *     by exact title.
    13	 *   - Any DugSection consumed by neither step → orphans[] (never dropped).
    14	 *
    15	 * No fs, no I/O — pure data transformation.
    16	 */
    17	
    18	import type { ParsedSummary } from './types';
    19	import type { ModelEnvelope } from './model-store';
    20	import type { DugSection } from '../dig/companion-doc';
    21	import { sameTitles } from './rerender';
    22	import { DIG_GENERATOR_VERSION } from '../dig/generate';
    23	
    24	// ── Public types ───────────────────────────────────────────────────────────────
    25	
    26	export interface MergedSection {
    27	  index: number;
    28	  numeral: string | null;
    29	  title: string;
    30	  startSec: number | null;
    31	  gist: { lead: string; bullets: { text: string }[] } | null;
    32	  dug: { bodyMarkdown: string } | null;
    33	  isStale: boolean;
    34	}
    35	
    36	export interface MergeResult {
    37	  sections: MergedSection[];
    38	  orphans: { sectionId: number; title: string; bodyMarkdown: string }[];
    39	}
    40	
    41	// ── Implementation ────────────────────────────────────────────────────────────
    42	
    43	/**
    44	 * Merge summary GIST (model envelope) and DUG (companion-doc sections) into a
    45	 * unified per-section view.
    46	 *
    47	 * @param summary  Parsed summary markdown (section list, titles, time ranges).
    48	 * @param envelope Cached model envelope (source sections + magazine-style gist).
    49	 *                 Null when no model file exists for this video.
    50	 * @param dug      Dug sections from the companion doc (may be empty).
    51	 */
    52	export function mergeDigDoc(
    53	  summary: ParsedSummary,
    54	  envelope: ModelEnvelope | null,
    55	  dug: DugSection[],
    56	): MergeResult {
    57	  const parsedTitles = summary.sections.map((s) => s.title);
    58	
    59	  // Determine whether the model is trustworthy for all sections.
    60	  // If the envelope is absent or the section titles have drifted, all gists are null.
    61	  const titlesAligned =
    62	    envelope !== null && sameTitles(parsedTitles, envelope.sourceSections);
    63	
    64	  // Track which dug sectionIds have been consumed (both step 1 and step 2).
    65	  const consumedIds = new Set<number>();
    66	
    67	  // ── Step 1: sectionId match ───────────────────────────────────────────────
    68	  // Build a lookup from sectionId → first DugSection for O(1) step-1 lookups.
    69	  // If a sectionId appears more than once, only the first entry is eligible for
    70	  // step-1 matching; all extras go directly to preOrphans so they are never dropped.
    71	  const dugBySectionId = new Map<number, DugSection>();
    72	  const preOrphans: DugSection[] = [];
    73	  for (const d of dug) {
    74	    if (dugBySectionId.has(d.sectionId)) {
    75	      preOrphans.push(d);
    76	    } else {
    77	      dugBySectionId.set(d.sectionId, d);
    78	    }
    79	  }
    80	
    81	  // For step 2: build a lookup from title → first unconsumed DugSection.
    82	  // We'll resolve this lazily after step 1 to avoid consuming a section twice.
    83	
    84	  // ── Build MergedSections ─────────────────────────────────────────────────
    85	  const sections: MergedSection[] = summary.sections.map((section, i) => {
    86	    const startSec = section.timeRange?.startSec ?? null;
    87	
    88	    // GIST: only when envelope is aligned and model has an entry at this index.
    89	    let gist: MergedSection['gist'] = null;
    90	    if (titlesAligned && envelope !== null) {
    91	      const modelSection = envelope.model.sections[i];
    92	      if (modelSection !== undefined) {
    93	        gist = { lead: modelSection.lead, bullets: modelSection.bullets };
    94	      }
    95	    }
    96	
    97	    // DUG step 1: exact sectionId match against section's startSec.
    98	    let dug_: MergedSection['dug'] = null;
    99	    let isStale_ = false;
   100	    if (startSec !== null) {
   101	      const matched = dugBySectionId.get(startSec);
   102	      if (matched !== undefined && !consumedIds.has(matched.sectionId)) {
   103	        dug_ = { bodyMarkdown: matched.bodyMarkdown };
   104	        isStale_ = matched.genVersion < DIG_GENERATOR_VERSION;
   105	        consumedIds.add(matched.sectionId);
   106	      }
   107	    }
   108	
   109	    return {
   110	      index: i,
   111	      numeral: section.numeral,
   112	      title: section.title,
   113	      startSec,
   114	      gist,
   115	      dug: dug_, // may be overwritten in step 2 pass below, but step-2 only fills null slots
   116	      isStale: isStale_,
   117	    };
   118	  });
   119	
   120	  // ── Step 2: title fallback ─────────────────────────────────────────────────
   121	  // For each summary section that did NOT get a dug match in step 1,
   122	  // try to find an unconsumed DugSection whose title exactly matches.
   123	  // Build a map from title → unconsumed DugSection for this pass.
   124	  // Per the spec: "any not-yet-consumed DugSection matched to a not-yet-dug summary section
   125	  // by exact title". This means: for each dug section not yet consumed, match the FIRST
   126	  // summary section (in order) whose title equals the dug section's title and that has no
   127	  // dug content yet.
   128	
   129	  // We need to iterate summary sections in order, matching against unconsumed dug sections.
   130	  // Build a list of unconsumed dug sections (preserving original order).
   131	  // For efficiency, use a title → array-of-dug-sections map.
   132	  const dugByTitle = new Map<string, DugSection[]>();
   133	  for (const d of dug) {
   134	    if (!consumedIds.has(d.sectionId)) {
   135	      const existing = dugByTitle.get(d.title) ?? [];
   136	      existing.push(d);
   137	      dugByTitle.set(d.title, existing);
   138	    }
   139	  }
   140	
   141	  for (const ms of sections) {
   142	    if (ms.dug !== null) continue; // already matched in step 1
   143	
   144	    const candidates = dugByTitle.get(ms.title);
   145	    if (!candidates || candidates.length === 0) continue;
   146	
   147	    // Take the first unconsumed candidate with this title.
   148	    // Filter down to unconsumed (consumedIds may have grown within this loop).
   149	    const idx = candidates.findIndex((d) => !consumedIds.has(d.sectionId));
   150	    if (idx === -1) continue;
   151	
   152	    const matched = candidates[idx];
   153	    ms.dug = { bodyMarkdown: matched.bodyMarkdown };
   154	    ms.isStale = matched.genVersion < DIG_GENERATOR_VERSION;
   155	    consumedIds.add(matched.sectionId);
   156	  }
   157	
   158	  // ── Orphans ───────────────────────────────────────────────────────────────
   159	  // Any dug section not consumed by either step becomes an orphan.
   160	  // preOrphans are duplicate-sectionId extras that were never put in the map;
   161	  // they are unconsumed by definition and must also appear here.
   162	  //
   163	  // Build postOrphans from the de-duped dugBySectionId map values (NOT from the
   164	  // raw dug array) so that a sectionId shared by two inputs that both go
   165	  // unmatched is counted exactly once here — the duplicate is already in
   166	  // preOrphans and would otherwise be appended a second time below.
   167	  const postOrphans = [...dugBySectionId.values()]
   168	    .filter((d) => !consumedIds.has(d.sectionId))
   169	    .map((d) => ({
   170	      sectionId: d.sectionId,
   171	      title: d.title,
   172	      bodyMarkdown: d.bodyMarkdown,
   173	    }));
   174	
   175	  const preOrphansMapped = preOrphans.map((d) => ({
   176	    sectionId: d.sectionId,
   177	    title: d.title,
   178	    bodyMarkdown: d.bodyMarkdown,
   179	  }));
   180	
   181	  // Preserve deterministic order: pre-orphans (extras from step-1 build) come last,
   182	  // after the unmatched entries that went through the normal matching pipeline.
   183	  const orphans = [...postOrphans, ...preOrphansMapped];
   184	
   185	  return { sections, orphans };
   186	}

exec
/bin/bash -lc "nl -ba lib/dig/companion-doc.ts | sed -n '1,140p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	/**
     2	 * Companion-doc upsert for "dig deeper" sections.
     3	 *
     4	 * Maintains a per-video `<basename>-dig-deeper.md` that accumulates dug
     5	 * sections. Idempotent: re-digging a section replaces that block and its
     6	 * frontmatter entry in place; all other sections are preserved.
     7	 *
     8	 * No YAML library dependency — hand-rolled for this fixed schema only.
     9	 * Atomic write via temp file + rename.
    10	 *
    11	 * NOTE: `generatedAt` must be supplied by the caller. This module never calls
    12	 * `Date.now()` or `new Date()` internally (testability).
    13	 *
    14	 * Body format — each section is wrapped in sentinel comments so that `## ` /
    15	 * `### ` headings inside bodyMarkdown never confuse the parser (C1 fix):
    16	 *
    17	 *   <!-- dig-section: 312 -->
    18	 *   ## <title>
    19	 *
    20	 *   <bodyMarkdown (may contain ## / ###)>
    21	 *   <!-- /dig-section -->
    22	 */
    23	
    24	import { readFile, writeFile, rename } from 'node:fs/promises';
    25	import path from 'node:path';
    26	import crypto from 'node:crypto';
    27	
    28	// ── Public types ──────────────────────────────────────────────────────────────
    29	
    30	export interface DugSection {
    31	  sectionId: number;
    32	  startSec: number;
    33	  title: string;
    34	  bodyMarkdown: string;
    35	  generatedAt: string;
    36	  genVersion: number;
    37	  slides?: Array<{ startSec: number; endSec: number; pickedSec: number }>;
    38	}
    39	
    40	// ── Internal types ────────────────────────────────────────────────────────────
    41	
    42	/** Complete in-memory representation of a companion doc. */
    43	interface CompanionDoc {
    44	  videoTitle: string;
    45	  videoId: string;
    46	  language: 'en' | 'ko';
    47	  sourceVideoUrl: string;
    48	  sections: DugSection[];
    49	}
    50	
    51	// ── YAML serialization ────────────────────────────────────────────────────────
    52	
    53	/** Escape a string for use as a double-quoted YAML scalar. */
    54	function yamlQuote(s: string): string {
    55	  // Escape backslash first, then double-quote, then control chars.
    56	  return s
    57	    .replace(/\\/g, '\\\\')
    58	    .replace(/"/g, '\\"')
    59	    .replace(/\n/g, '\\n')
    60	    .replace(/\r/g, '\\r')
    61	    .replace(/\t/g, '\\t');
    62	}
    63	
    64	function serializeFrontmatter(doc: CompanionDoc): string {
    65	  const lines: string[] = [
    66	    '---',
    67	    `title: "${yamlQuote(doc.videoTitle)}"`,
    68	    `videoId: "${yamlQuote(doc.videoId)}"`,
    69	    `language: "${doc.language}"`,
    70	    `sourceVideoUrl: "${yamlQuote(doc.sourceVideoUrl)}"`,
    71	  ];
    72	
    73	  if (doc.sections.length === 0) {
    74	    lines.push('sections: []');
    75	  } else {
    76	    lines.push('sections:');
    77	    for (const s of doc.sections) {
    78	      lines.push(`  - sectionId: ${s.sectionId}`);
    79	      lines.push(`    startSec: ${s.startSec}`);
    80	      lines.push(`    title: "${yamlQuote(s.title)}"`);
    81	      lines.push(`    generatedAt: "${yamlQuote(s.generatedAt)}"`);
    82	      lines.push(`    genVersion: ${s.genVersion ?? 0}`);
    83	      if (s.slides && s.slides.length) {
    84	        lines.push('    slides:');
    85	        for (const sl of s.slides) {
    86	          lines.push(`      - startSec: ${sl.startSec}`);
    87	          lines.push(`        endSec: ${sl.endSec}`);
    88	          lines.push(`        pickedSec: ${sl.pickedSec}`);
    89	        }
    90	      }
    91	    }
    92	  }
    93	
    94	  lines.push('---');
    95	  return lines.join('\n');
    96	}
    97	
    98	/**
    99	 * Serialize body using sentinel-delimited blocks so that `## ` / `### ` inside
   100	 * bodyMarkdown is never mistaken for a section boundary (C1 fix).
   101	 *
   102	 * Format per section (ordered by startSec):
   103	 *
   104	 *   <!-- dig-section: <sectionId> -->
   105	 *   ## <title>
   106	 *
   107	 *   <bodyMarkdown (verbatim, trimEnd)>
   108	 *   <!-- /dig-section -->
   109	 */
   110	function serializeBody(sections: DugSection[]): string {
   111	  return sections
   112	    .map((s) => {
   113	      const body = s.bodyMarkdown.trimEnd();
   114	      // Sanitize sentinel strings that could corrupt round-trip parsing.
   115	      const safeBody = body
   116	        .replace(/<!--\s*\/dig-section\s*-->/g, '<!-- /dig-section (escaped) -->')
   117	        .replace(/<!--\s*dig-section\s*:/g, '<!-- dig-section-escaped:');
   118	      return `<!-- dig-section: ${s.sectionId} -->\n## ${s.title}\n\n${safeBody}\n<!-- /dig-section -->`;
   119	    })
   120	    .join('\n\n');
   121	}
   122	
   123	function serialize(doc: CompanionDoc): string {
   124	  // sections must be sorted by startSec before serializing
   125	  const sorted = [...doc.sections].sort((a, b) => a.startSec - b.startSec);
   126	  const docSorted: CompanionDoc = { ...doc, sections: sorted };
   127	  const fm = serializeFrontmatter(docSorted);
   128	  const body = serializeBody(sorted);
   129	  return fm + '\n' + body + '\n';
   130	}
   131	
   132	// ── YAML parsing ──────────────────────────────────────────────────────────────
   133	
   134	/** Parse a double-quoted YAML scalar (removes quotes + unescapes). */
   135	function parseYamlQuotedScalar(raw: string): string {
   136	  // raw may or may not have surrounding quotes
   137	  const trimmed = raw.trim();
   138	  if (trimmed.startsWith('"') && trimmed.endsWith('"')) {
   139	    return trimmed
   140	      .slice(1, -1)

codex
The dig merge code handles changed sections by exact timestamp first, then exact title, then explicit orphans. Preserving `digDeeperMd` can surface stale/orphaned dig content after a summary replacement, but that is already the M2a boundary: sync does not reconcile dig content, and deleting the pointer is the more expensive failure.
exec
/bin/bash -lc 'npx jest tests/lib/cloud-sync --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
exec
/bin/bash -lc 'npx jest tests/integration/cloud-sync/e2e.int.test.ts --runInBand -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 exited 1 in 5036ms:
No tests found, exiting with code 1
Run with `--passWithNoTests` to exit with code 0
In /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
  905 files checked.
  testMatch: /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/lib/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/api/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/scripts/**/*.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/smoke.test.ts, /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/tests/components/**/*.test.tsx - 245 matches
  testPathIgnorePatterns: /node_modules/, /.next/ - 560 matches
  testRegex:  - 0 matches
Pattern: tests/integration/cloud-sync/e2e.int.test.ts - 0 matches

 succeeded in 10083ms:

Test Suites: 15 passed, 15 total
Tests:       85 passed, 85 total
Snapshots:   0 total
Time:        4.812 s, estimated 12 s
Ran all test suites matching tests/lib/cloud-sync.

codex
The unit cloud-sync suite is green: 15 suites, 85 tests. The direct Jest integration path is not in the default `testMatch`, so I’m checking the project scripts to invoke the integration suite the way this repo expects.
exec
/bin/bash -lc 'rg -n "integration|int.test|jest.*integration|testMatch|cloud-sync" package.json jest.config.* tests scripts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
package.json:18:    "test:integration": "jest --config jest.integration.config.ts --runInBand",
package.json:22:    "cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
jest.config.ts:11:  testMatch: [
scripts/check-service-confinement.ts:68:    // Task 10 (§6): the local cloud-sync CLI is a user-facing entrypoint whose whole point is to
scripts/check-service-confinement.ts:70:    // there (or transitively via lib/cloud-sync/*) would pass undetected — making that guarantee
scripts/check-service-confinement.ts:71:    // vacuous. Walk lib/cloud-sync/ directly (it exists now) and every scripts/*.ts file — `walk()`
scripts/check-service-confinement.ts:73:    // `scripts/cloud-sync.ts` not existing yet (it lands in Task 13) without hardcoding its path or
scripts/check-service-confinement.ts:75:    ...walk(path.join(ROOT, 'lib/cloud-sync')),
scripts/cloud-sync.ts:1:// scripts/cloud-sync.ts
scripts/cloud-sync.ts:6:// long-lived refresh token via lib/cloud-sync/auth's file-backed TokenStore; `sync` (the default)
scripts/cloud-sync.ts:13:// app/api/resolve-folder/route.ts reads, and what lib/cloud-sync/registry.ts's
scripts/cloud-sync.ts:16:import { getAuthedClient, signIn, signOut, NoSessionError } from '@/lib/cloud-sync/auth';
scripts/cloud-sync.ts:17:import { runSync, type SyncDeps } from '@/lib/cloud-sync/sync-run';
scripts/verify-gemini-release.ts:102:  line('  commit, and run:  npm run test:integration -- reservation-release   (confirm no regression).');
tests/api/delete-playlist-route.test.ts:10:// and 6 (second delete ⇒ 404) are covered by the integration test
tests/api/delete-playlist-route.test.ts:11:// (tests/integration/delete-playlist-route.test.ts) against real local Supabase/RLS.
scripts/regen-skills-doc.py:115:        "desc":  "TypeScript LSP integration for diagnostics and in-context code intelligence.",
scripts/regen-skills-doc.py:119:        "desc":  "Pyright LSP integration for Python type checking.",
tests/lib/pipeline-async.test.ts:83:describe('B2: runIngestion awaits every store call (delayed-store integration)', () => {
tests/lib/cloud-sync/auth-file-store.test.ts:4:import { makeFileTokenStore } from '@/lib/cloud-sync/auth';
tests/integration/middleware-2a.test.ts:3:// This file lives under tests/integration/ per the task brief's required path, but — like
tests/lib/cloud-sync/cli.test.ts:1:import { parseArgs } from '@/scripts/cloud-sync';
tests/lib/cloud-sync/reconcile-class-a.test.ts:1:import { reconcileClassA } from '@/lib/cloud-sync/reconcile-class-a';
tests/lib/cloud-sync/reconcile-class-a.test.ts:2:import type { ClassASignals } from '@/lib/cloud-sync/types';
tests/lib/cloud-sync/companion.test.ts:1:import { decideCompanion } from '@/lib/cloud-sync/companion';
tests/integration/delete-playlist-route.test.ts:1:// tests/integration/delete-playlist-route.test.ts
tests/integration/delete-playlist-route.test.ts:4:// tests/integration/archive-route-cloud.test.ts: mock ONLY the next/headers +
tests/integration/delete-playlist-route.test.ts:27:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/lib/cloud-sync/reconcile-class-b.test.ts:1:import { reconcileField } from '@/lib/cloud-sync/reconcile-class-b';
tests/lib/cloud-sync/registry.test.ts:1:import { playlistKeyFromUrl, unionPlaylistKeys } from '@/lib/cloud-sync/registry';
tests/lib/cloud-sync/import-guard.test.ts:5:// cloud-sync source would be skipped and the guard would pass vacuously). Assert the scan is
tests/lib/cloud-sync/import-guard.test.ts:17:const cloudSyncSources = walk(join(root, 'lib/cloud-sync')).filter((f) => existsSync(f));
tests/lib/cloud-sync/import-guard.test.ts:27:describe('Task 10 (§6) — cloud-sync auth never reaches the service-role key', () => {
tests/lib/cloud-sync/import-guard.test.ts:40:  it('scans a non-empty set of cloud-sync sources', () => {
tests/lib/cloud-sync/import-guard.test.ts:42:    expect(cloudSyncSources.some((f) => f.endsWith('lib/cloud-sync/auth.ts'))).toBe(true);
tests/integration/blob-store.test.ts:1:// tests/integration/blob-store.test.ts
tests/integration/blob-store.test.ts:5:// Run via: npm run test:integration -- blob-store
tests/integration/blob-store.test.ts:6:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/blob-store.test.ts:25: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/lib/cloud-sync/regenerate-stamp.test.ts:1:// tests/lib/cloud-sync/regenerate-stamp.test.ts
tests/lib/cloud-sync/regenerate-stamp.test.ts:27:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/model-writer-hash.test.ts:1:// tests/lib/cloud-sync/model-writer-hash.test.ts
tests/lib/cloud-sync/model-writer-hash.test.ts:16:import { mdHash } from '../../../lib/cloud-sync/content-hash';
tests/lib/cloud-sync/content-hash.test.ts:1:import { mdHash, canonicalizeMd } from '@/lib/cloud-sync/content-hash';
tests/integration/video-updated-at.test.ts:1:// tests/integration/video-updated-at.test.ts
tests/lib/cloud-sync/auth.test.ts:1:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/lib/cloud-sync/auth.test.ts:11:    await expect(getAuthedClient(memStore(null))).rejects.toThrow(/cloud-sync login/);
tests/lib/cloud-sync/local-stamping.test.ts:1:// tests/lib/cloud-sync/local-stamping.test.ts
tests/lib/cloud-sync/manifest.test.ts:1:// tests/lib/cloud-sync/manifest.test.ts
tests/lib/cloud-sync/manifest.test.ts:5:import { manifestPath, readManifest, writeVideoBaseline, appendConflict } from '@/lib/cloud-sync/manifest';
tests/lib/cloud-sync/manifest.test.ts:34:  const log = await fs.readFile(path.join(r, 'PL1', '.cloud-sync-conflicts.log'), 'utf8');
tests/lib/cloud-sync/backfill.test.ts:1:import { deriveClassASignals, deriveHumanSnapshot } from '@/lib/cloud-sync/backfill';
tests/lib/cloud-sync/backfill.test.ts:2:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/archive-route-cloud.test.ts:1:// tests/integration/archive-route-cloud.test.ts
tests/integration/archive-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/review-route-cloud.test.ts (Task 7): mock
tests/integration/archive-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/review-route-cloud.test.ts.
tests/integration/backfill-titles.test.ts:1:// tests/integration/backfill-titles.test.ts
tests/integration/backfill-titles.test.ts:4:// live local Supabase stack. Run via: npm run test:integration -- backfill-titles
tests/integration/backfill-titles.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/backfill-titles.test.ts:20:describe('setPlaylistTitleIfNull integration', () => {
tests/integration/enqueue-dig.test.ts:1:// tests/integration/enqueue-dig.test.ts
tests/integration/enqueue-dig.test.ts:5:// service client — mirrors the setup in tests/integration/summary-handler.test.ts.
tests/integration/job-queue-producer.test.ts:1:// tests/integration/job-queue-producer.test.ts
tests/integration/worker-runner-runtime.test.ts:13:// tests/integration/job-queue-worker.test.ts and job-queue-runner.test.ts.
tests/integration/storage-policy.test.ts:1:// tests/integration/storage-policy.test.ts
tests/integration/backfill-titles-route.test.ts:1:// tests/integration/backfill-titles-route.test.ts
tests/integration/backfill-titles-route.test.ts:4:// Supabase stack. Auth plumbing mocked exactly like tests/integration/playlists-route.test.ts
tests/integration/backfill-titles-route.test.ts:19:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
tests/integration/review-route-cloud.test.ts:1:// tests/integration/review-route-cloud.test.ts
tests/integration/review-route-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/quickview-route-cloud.test.ts (Task 6): mock
tests/integration/review-route-cloud.test.ts:16:// hoisted above this declaration) — same pattern as tests/integration/quickview-route-cloud.test.ts.
tests/integration/worker-main.test.ts:36:    // integration test files (e.g. job-queue-producer.test.ts intentionally leaves some
tests/integration/list-playlists.test.ts:1:// tests/integration/list-playlists.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:1:// tests/integration/cloud-sync/e2e.int.test.ts
tests/integration/cloud-sync/e2e.int.test.ts:18:} from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/e2e.int.test.ts:19:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/cloud-sync/e2e.int.test.ts:20:import { mdHash } from '@/lib/cloud-sync/content-hash';
tests/integration/cloud-sync/e2e.int.test.ts:21:import { getAuthedClient, NoSessionError, type TokenStore } from '@/lib/cloud-sync/auth';
tests/integration/cloud-sync/e2e.int.test.ts:22:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/cloud-sync/e2e.int.test.ts:53:describe('cloud-sync §10 end-to-end scenarios', () => {
tests/integration/cloud-sync/sync-run.int.test.ts:1:// tests/integration/cloud-sync/sync-run.int.test.ts
tests/integration/cloud-sync/sync-run.int.test.ts:3:// Stage 3 Cloud Sync (§7), Task 12 — the integration keystone for runSync. Runs against real local
tests/integration/cloud-sync/sync-run.int.test.ts:14:import { makeOwnerContext, seedLocalPlaylist } from '@/tests/integration/helpers/cloud';
tests/integration/cloud-sync/sync-run.int.test.ts:15:import { runSync } from '@/lib/cloud-sync/sync-run';
tests/integration/metadata-store.test.ts:1:// tests/integration/metadata-store.test.ts
tests/integration/metadata-store.test.ts:4:// Run via: npm run test:integration -- metadata-store
tests/integration/metadata-store.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/metadata-store.test.ts:21: *  validation — integration tests focus on store behaviour, not type fidelity. */
tests/integration/metadata-store.test.ts:38:describe('SupabaseMetadataStore integration', () => {
tests/integration/concurrency.test.ts:1:// tests/integration/concurrency.test.ts
tests/integration/concurrency.test.ts:5:// Run via: npm run test:integration -- concurrency
tests/integration/cost-guardrails.test.ts:1:// tests/integration/cost-guardrails.test.ts
tests/integration/cost-guardrails.test.ts:284:  // this test/file) — with the full integration suite creating real auth users across many
tests/integration/cloud-sync/cloud-stamping.int.test.ts:1:// tests/integration/cloud-sync/cloud-stamping.int.test.ts
tests/integration/cloud-sync/cloud-stamping.int.test.ts:3:// Stage 3 Cloud Sync (§5.7), Task 4. Store-layer mirror of Task 3's stamping.int.test.ts (which
tests/integration/cloud-sync/cloud-stamping.int.test.ts:7:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/pdf-cloud.test.ts:1:// tests/integration/pdf-cloud.test.ts
tests/integration/pdf-cloud.test.ts:5:// tests could only mock. Mirrors tests/integration/html-download.test.ts's auth-plumbing pattern:
tests/integration/pdf-cloud.test.ts:56:// hoisted above these declarations) — same pattern as tests/integration/html-download.test.ts.
tests/integration/rls-isolation.test.ts:1:// tests/integration/rls-isolation.test.ts
tests/integration/schema.test.ts:1:// tests/integration/schema.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:1:// tests/integration/cloud-sync/stamping.int.test.ts
tests/integration/cloud-sync/stamping.int.test.ts:8:// Runs against local Supabase (jest.integration.config.ts). Uses the shared integration
tests/integration/cloud-sync/stamping.int.test.ts:10:import { makeOwnerContext, seedVideo } from '@/tests/integration/helpers/cloud';
tests/integration/serve-doc-materialize.test.ts:33:// ── Owner-budget helpers (mirrors tests/integration/serve-owner-budget.test.ts — see that file's
tests/integration/gemini-live-gates.test.ts:3: * (Stage 1D). These are NOT part of the normal CI/integration run — they make real, billed
tests/integration/annotations-rpc.test.ts:1:// tests/integration/annotations-rpc.test.ts
tests/integration/annotations-rpc.test.ts:4:// REAL local Supabase stack. Run via: npm run test:integration -- annotations-rpc
tests/integration/annotations-rpc.test.ts:5:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/reservation-release.test.ts:502:    // guards against another integration file having mutated the shared guardrail_config singleton
tests/integration/reservation-release.test.ts:561:    // default, but guards against another integration file having mutated the shared singleton.
tests/integration/serve-config-invariant.test.ts:1:// tests/integration/serve-config-invariant.test.ts
tests/integration/serve-config-invariant.test.ts:7:// ORDER-SAFETY (Codex Critical #2): the full `test:integration --runInBand` suite shares ONE DB,
tests/integration/provisioning.test.ts:1:// tests/integration/provisioning.test.ts
tests/integration/dig-serve-interactive.test.ts:1:// tests/integration/dig-serve-interactive.test.ts
tests/integration/dig-serve-interactive.test.ts:3:// Task 6 (cloud dig-deeper frontend slice): REAL local-Supabase integration proof that the
tests/integration/dig-serve-interactive.test.ts:7:// tests/integration/archive-route-cloud.test.ts (mock next/headers + @/lib/supabase/server
tests/integration/dig-serve-interactive.test.ts:9:// blob-seeding pattern from tests/integration/dig-cloud.test.ts (writeDigSectionBlob writer,
tests/integration/dig-serve-interactive.test.ts:22:// hoisted above this declaration) — same pattern as tests/integration/archive-route-cloud.test.ts.
tests/integration/dig-serve-interactive.test.ts:58:describe('cloud dig-deeper serve (integration, real DB) — interactive + no-charge', () => {
tests/integration/playlists-route.test.ts:1:// tests/integration/playlists-route.test.ts
tests/integration/playlists-route.test.ts:8:// metadataStore.listPlaylists) runs for real. Same pattern as tests/integration/html-download.test.ts.
tests/integration/playlists-route.test.ts:18:// hoisted above this declaration) — same pattern as tests/integration/html-download.test.ts.
tests/integration/worker-storage-bundle.test.ts:1:// tests/integration/worker-storage-bundle.test.ts
tests/integration/gemini-magazine-live.test.ts:9: * mirroring tests/integration/gemini-live-gates.test.ts.
tests/e2e/cloud-library.spec.ts:9: *   - Per-route integration tests against a REAL Supabase stack with `signInAs`
tests/e2e/cloud-library.spec.ts:10: *     (tests/integration/{playlists-route,videos-route-cloud,quickview-route-cloud,
tests/e2e/cloud-library.spec.ts:21: *      client (mirror tests/integration/helpers/seed.ts), sign in via Supabase to obtain
tests/integration/cap-soundness.test.ts:1:// tests/integration/cap-soundness.test.ts
tests/integration/pdf-put-atomicity.test.ts:1:// tests/integration/pdf-put-atomicity.test.ts
tests/integration/pdf-put-atomicity.test.ts:32:// when STORAGE_BACKEND==='supabase' — same pattern as sibling *-cloud integration tests.
tests/integration/dig-cloud.test.ts:1:// tests/integration/dig-cloud.test.ts
tests/integration/dig-cloud.test.ts:3:// Task 7 (cloud dig-deeper generation slice): end-to-end integration against a REAL local
tests/integration/dig-cloud.test.ts:4:// Supabase stack. Mirrors tests/integration/pdf-cloud.test.ts for owner-isolation + spend
tests/integration/dig-cloud.test.ts:5:// mutation-control, and tests/integration/summary-handler.test.ts for the direct-handler blob
tests/integration/dig-cloud.test.ts:42:  // dig is the FIRST integration path that goes through enqueue_preflight — pin its admission
tests/integration/dig-cloud.test.ts:66:describe('dig-cloud (integration, real DB)', () => {
tests/integration/summary-handler.test.ts:1:// tests/integration/summary-handler.test.ts
tests/integration/summary-handler.test.ts:8:// Run via: npm run test:integration -- summary-handler
tests/integration/summary-handler.test.ts:9:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/worker-persistence-rpcs.test.ts:1:// tests/integration/worker-persistence-rpcs.test.ts
tests/integration/share-summary-2c.test.ts:1:// tests/integration/share-summary-2c.test.ts
tests/integration/share-summary-2c.test.ts:3:// Stage 2c Task 8 — real-Supabase integration guard proving:
tests/integration/share-summary-2c.test.ts:9:// Run: npx supabase db reset && npm run test:integration -- share-summary-2c --runInBand
tests/integration/share-summary-2c.test.ts:27:describe('share-summary-2c integration', () => {
tests/integration/supabase-blob-delete-prefix.test.ts:1:// tests/integration/supabase-blob-delete-prefix.test.ts
tests/integration/supabase-blob-delete-prefix.test.ts:7:// Run via: npm run test:integration -- supabase-blob-delete-prefix
tests/integration/supabase-blob-delete-prefix.test.ts:8:// Requires: stack up + .env.test.local present (see tests/integration/setup.ts).
tests/integration/serve-model-charge.test.ts:1:// tests/integration/serve-model-charge.test.ts
tests/integration/job-queue-store.test.ts:1:// tests/integration/job-queue-store.test.ts
tests/integration/videos-route-cloud.test.ts:1:// tests/integration/videos-route-cloud.test.ts
tests/integration/videos-route-cloud.test.ts:9:// tests/integration/playlists-route.test.ts.
tests/integration/videos-route-cloud.test.ts:17:// hoisted above this declaration) — same pattern as tests/integration/playlists-route.test.ts.
tests/integration/serve-owner-budget.test.ts:1:// tests/integration/serve-owner-budget.test.ts
tests/integration/helpers/seed.ts:1:// tests/integration/helpers/seed.ts
tests/integration/quickview-route-cloud.test.ts:1:// tests/integration/quickview-route-cloud.test.ts
tests/integration/quickview-route-cloud.test.ts:4:// stack. Mirrors tests/integration/videos-route-cloud.test.ts (Task 5): mock ONLY the
tests/integration/quickview-route-cloud.test.ts:15:// hoisted above this declaration) — same pattern as tests/integration/videos-route-cloud.test.ts.
tests/integration/html-download.test.ts:1:// tests/integration/html-download.test.ts
tests/integration/html-download.test.ts:24:// hoisted above this declaration) — same pattern as tests/integration/share-route.test.ts.
tests/integration/html-download.test.ts:90:// ── Stage 1G / Task 3 owner-budget helpers — replicated from tests/integration/serve-owner-budget.test.ts
tests/integration/helpers/cloud.ts:1:// tests/integration/helpers/cloud.ts
tests/integration/helpers/cloud.ts:3:// Shared integration harness for Stage 3 Cloud Sync (Tasks 3, 4, 12, 14). Reuses the existing
tests/integration/helpers/cloud.ts:26:import { readManifest as readManifestFile, writeVideoBaseline } from '@/lib/cloud-sync/manifest';
tests/integration/helpers/cloud.ts:27:import type { SyncDeps } from '@/lib/cloud-sync/sync-run';
tests/integration/helpers/cloud.ts:28:import type { VideoBaseline } from '@/lib/cloud-sync/types';
tests/integration/helpers/cloud.ts:77: *  every cloud-sync integration test. */
tests/lib/html-doc/serve-doc-mapping.test.ts:2:// Unlike tests/integration/serve-doc-materialize.test.ts, these do NOT hit a real Supabase project:
tests/api/dig-cloud-route.test.ts:5: * but jest.config.ts's testMatch only covers tests/lib, tests/api, tests/scripts, tests/smoke,
tests/api/dig-cloud-route.test.ts:6: * and tests/components (verified — no tests/app pattern exists). tests/integration is a SEPARATE
tests/api/dig-cloud-route.test.ts:7: * jest project (jest.integration.config.ts) that runs against a real local Supabase stack, which
tests/lib/dig/slide-crop.integration.test.ts:1:// tests/lib/dig/slide-crop.integration.test.ts
tests/lib/dig/slide-crop.integration.test.ts:7:describe('ffmpeg profile (integration — real ffmpeg)', () => {
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:8: * in supabase-job-queue.ts). Owner-guard/cascade behavior is covered by the integration
tests/lib/storage/supabase-job-queue-cancel-playlist.test.ts:9: * suite (tests/integration/cancel-playlist-jobs.test.ts, delete-playlist-store.test.ts).
tests/api/backfill-titles-route.test.ts:19:// Behaviors 3 and 7 (real backfill + owner isolation) are covered by the integration test
tests/api/backfill-titles-route.test.ts:20:// (tests/integration/backfill-titles-route.test.ts) against real local Supabase/RLS.

exec
/bin/bash -lc "node -p \"JSON.stringify(require('./package.json').scripts,null,2)\"" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
{
  "dev": "next dev",
  "build": "next build",
  "start": "next start",
  "test": "jest",
  "test:watch": "jest --watch",
  "test:e2e": "playwright test",
  "rerender-html": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/rerender-html.ts",
  "audit-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-timestamps.ts",
  "audit-summaries": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/audit-summaries.ts",
  "repair-timestamps": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/repair-timestamps.ts",
  "backfill-serial": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-serial-prefix.ts",
  "backfill-playlist-titles": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/backfill-playlist-titles.ts",
  "test:integration": "jest --config jest.integration.config.ts --runInBand",
  "check:confinement": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node scripts/check-service-confinement.ts",
  "worker": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register worker/main.ts",
  "verify:gemini-release": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/verify-gemini-release.ts",
  "cloud-sync": "TS_NODE_COMPILER_OPTIONS='{\"module\":\"commonjs\"}' ts-node -r tsconfig-paths/register scripts/cloud-sync.ts"
}

codex
I found the correct integration command. I’m running only the cloud-sync e2e file with the round-2 fix tests selected, leaving the known reservation-release pollution out of scope.
exec
/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1|H-R2-2|M-R2-2|WB-B1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 5464ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1|H-R2-2|M-R2-2|WB-B1

Test Suites: 1 passed, 1 total
Tests:       18 skipped, 4 passed, 22 total
Snapshots:   0 total
Time:        2.339 s, estimated 9 s
Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1|H-R2-2|M-R2-2|WB-B1".

codex
The targeted integration tests pass: 4 selected tests, 18 skipped in that file. To answer the specific “would it fail if moved back?” question, I’m doing a temporary mutation of `copyAdditiveVideo`, running the H-R2-1 test, then restoring the file.
apply patch
patch: completed
/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts
diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index a031c2a27c7440da2cb15f9b4be3b8eaa2efcbef..ebf9e129aed20dbf868ebd21a1d28b3b6ea57341
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -147,20 +147,6 @@
   playlistMeta: { playlistUrl: string; playlistTitle?: string },
   video: Video, mdBody: string | null,
 ): Promise<void> {
-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
-  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
-  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
-  // strand the receiver with a servable-looking row backed by nothing.
-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
-  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
-  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
-  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
-  // partial state is ever created, so there is nothing to roll back.
-  if (video.summaryMd && mdBody == null) {
-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
-  }
-
   const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
 
   let wroteBlob = false;
@@ -174,6 +160,9 @@
     await toBlob.promote(ref);
     wroteBlob = true;
   }
+  if (video.summaryMd && mdBody == null) {
+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
+  }
 
   const sanitized: any = sanitizeAdditiveVideo(video);
   if (slot) {

diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index a031c2a27c7440da2cb15f9b4be3b8eaa2efcbef..ebf9e129aed20dbf868ebd21a1d28b3b6ea57341
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -147,20 +147,6 @@
   playlistMeta: { playlistUrl: string; playlistTitle?: string },
   video: Video, mdBody: string | null,
 ): Promise<void> {
-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
-  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
-  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
-  // strand the receiver with a servable-looking row backed by nothing.
-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
-  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
-  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
-  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
-  // partial state is ever created, so there is nothing to roll back.
-  if (video.summaryMd && mdBody == null) {
-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
-  }
-
   const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
 
   let wroteBlob = false;
@@ -174,6 +160,9 @@
     await toBlob.promote(ref);
     wroteBlob = true;
   }
+  if (video.summaryMd && mdBody == null) {
+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
+  }
 
   const sanitized: any = sanitizeAdditiveVideo(video);
   if (slot) {

exec
/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
diff --git a/lib/cloud-sync/sync-run.ts b/lib/cloud-sync/sync-run.ts
index a031c2a27c7440da2cb15f9b4be3b8eaa2efcbef..ebf9e129aed20dbf868ebd21a1d28b3b6ea57341
--- a/lib/cloud-sync/sync-run.ts
+++ b/lib/cloud-sync/sync-run.ts
@@ -147,20 +147,6 @@
   playlistMeta: { playlistUrl: string; playlistTitle?: string },
   video: Video, mdBody: string | null,
 ): Promise<void> {
-  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
-  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
-  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
-  // strand the receiver with a servable-looking row backed by nothing.
-  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
-  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
-  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
-  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
-  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
-  // partial state is ever created, so there is nothing to roll back.
-  if (video.summaryMd && mdBody == null) {
-    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
-  }
-
   const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
 
   let wroteBlob = false;
@@ -174,6 +160,9 @@
     await toBlob.promote(ref);
     wroteBlob = true;
   }
+  if (video.summaryMd && mdBody == null) {
+    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
+  }
 
   const sanitized: any = sanitizeAdditiveVideo(video);
   if (slot) {

 exited 1 in 4277ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1

FAIL tests/integration/cloud-sync/e2e.int.test.ts
  ● cloud-sync §10 end-to-end scenarios › WB-H1/H-R2-1: additive create with a promoted summaryMd but no blob throws before claiming a receiver slot; no row, no baseline (2 runs)

    expect(received).toBeNull()

    Received: {"id": "vcdfa2db7a97a", "serialNumber": 1, "updatedAt": "2026-07-18T15:52:11.409Z"}

      450 |     expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
      451 |     // No partial state at all: the guard runs before ensureReceiverSlot, so there is no receiver row.
    > 452 |     expect(await localVideoRecord(ctx)).toBeNull();
          |                                         ^
      453 |     expect(artifactsOf(await localVideoRecord(ctx))?.summaryMd?.status).not.toBe('promoted');
      454 |     // Baseline not advanced — the throw aborted before writeVideoBaseline.
      455 |     expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();

      at Object.<anonymous> (tests/integration/cloud-sync/e2e.int.test.ts:452:41)

Test Suites: 1 failed, 1 total
Tests:       1 failed, 21 skipped, 22 total
Snapshots:   0 total
Time:        0.899 s, estimated 3 s
Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".

codex
The mutation check failed exactly where it should: with the guard moved back, run 1 leaves a bare local row, so the test fails on `expect(await localVideoRecord(ctx)).toBeNull()`. I’m restoring `sync-run.ts` now.
apply patch
patch: completed
/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts
codex
`sync-run.ts` is back to HEAD behavior. I’m doing one final targeted pass for worktree cleanliness and the restored H-R2-1 test.
exec
/bin/bash -lc 'git status --short' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md
?? scratchpad/

exec
/bin/bash -lc 'git diff -- lib/cloud-sync/sync-run.ts && npm run test:integration -- tests/integration/cloud-sync/e2e.int.test.ts -t "H-R2-1"' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 4169ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync/e2e.int.test.ts -t H-R2-1

Test Suites: 1 passed, 1 total
Tests:       21 skipped, 1 passed, 22 total
Snapshots:   0 total
Time:        0.924 s, estimated 1 s
Ran all test suites matching tests/integration/cloud-sync/e2e.int.test.ts with tests matching "H-R2-1".

exec
/bin/bash -lc "rg -n \"digDeeperHtml|buildDocHtml\\(|ensureHtml|reRender\" lib/html-doc app/api/videos/[id]/html-doc app/api/videos/[id]/pdf tests/lib/html-doc tests/integration | head -80" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
app/api/videos/[id]/html-doc/route.ts:4:import { ensureHtmlDoc } from '../../../../../lib/html-doc/ensure';
app/api/videos/[id]/html-doc/route.ts:30:  // `force: true` (Re-summarize) bypasses the version check in ensureHtmlDoc → always re-summarizes.
app/api/videos/[id]/html-doc/route.ts:55:  ensureHtmlDoc(videoId, outputFolder, (event: ProgressEvent) => {
lib/html-doc/ensure.ts:7:import { reRenderSummaryHtml } from './rerender';
lib/html-doc/ensure.ts:19:export async function ensureHtmlDoc(
lib/html-doc/ensure.ts:59:    const rr = await reRenderSummaryHtml(videoId, outputFolder);
tests/integration/cloud-sync/e2e.int.test.ts:274:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:493:  //    recovery costs fresh Gemini spend for content already paid for. summaryHtml/digDeeperHtml stay
tests/integration/cloud-sync/e2e.int.test.ts:494:  //    nulled (free re-renders; digDeeperHtml re-renders FROM the preserved digDeeperMd).
tests/integration/cloud-sync/e2e.int.test.ts:503:      digDeeperHtml: '<html>STALE dig render</html>',
tests/integration/cloud-sync/e2e.int.test.ts:516:    expect(local?.digDeeperHtml == null).toBe(true);    // WB-H2 still holds
app/api/videos/[id]/pdf/route.ts:71:    build = await buildDocHtml(video, outputFolder, type);
tests/integration/helpers/cloud.ts:316:  digDeeperHtml?: string;
tests/integration/helpers/cloud.ts:370:    ...(f.digDeeperHtml !== undefined ? { digDeeperHtml: f.digDeeperHtml } : {}),
tests/lib/html-doc/rerender.test.ts:5:import { reRenderSummaryHtml, reRenderAll } from '../../../lib/html-doc/rerender';
tests/lib/html-doc/rerender.test.ts:75:describe('reRenderSummaryHtml', () => {
tests/lib/html-doc/rerender.test.ts:78:    const res = await reRenderSummaryHtml(VIDEO_ID, dir);
tests/lib/html-doc/rerender.test.ts:92:    const res = await reRenderSummaryHtml(VIDEO_ID, dir);
tests/lib/html-doc/rerender.test.ts:107:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({ status: 'skipped-no-model' });
tests/lib/html-doc/rerender.test.ts:113:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({ status: 'skipped-not-eligible' });
tests/lib/html-doc/rerender.test.ts:119:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({ status: 'skipped-not-eligible' });
tests/lib/html-doc/rerender.test.ts:126:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({ status: 'skipped-no-md' });
tests/lib/html-doc/rerender.test.ts:132:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({ status: 'skipped-unparseable' });
tests/lib/html-doc/rerender.test.ts:138:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({
tests/lib/html-doc/rerender.test.ts:149:    expect(await reRenderSummaryHtml(VIDEO_ID, dir)).toEqual({
tests/lib/html-doc/rerender.test.ts:158:    expect(await reRenderSummaryHtml('nope99', dir)).toEqual({ status: 'skipped-not-eligible' });
tests/lib/html-doc/rerender.test.ts:166:    const res = await reRenderSummaryHtml(VIDEO_ID, dir, fakeBlobStore);
tests/lib/html-doc/rerender.test.ts:177:describe('reRenderAll', () => {
tests/lib/html-doc/rerender.test.ts:186:    const tally = await reRenderAll(dir);
tests/lib/html-doc/rerender.test.ts:202:    const tally = await reRenderAll(dir);
tests/lib/html-doc/rerender.test.ts:213:    const tally = await reRenderAll(dir);
tests/lib/html-doc/rerender.test.ts:232:    const tally = await reRenderAll(dir);
tests/lib/html-doc/ensure.test.ts:3:import { ensureHtmlDoc } from '../../../lib/html-doc/ensure';
tests/lib/html-doc/ensure.test.ts:35:describe('ensureHtmlDoc', () => {
tests/lib/html-doc/ensure.test.ts:38:    await ensureHtmlDoc('vid11111111', '/out', () => {});
tests/lib/html-doc/ensure.test.ts:41:    expect(rerender.reRenderSummaryHtml).not.toHaveBeenCalled();
tests/lib/html-doc/ensure.test.ts:50:    await ensureHtmlDoc('vid11111111', '/out', () => {});
tests/lib/html-doc/ensure.test.ts:57:    (rerender.reRenderSummaryHtml as jest.Mock).mockReturnValue({ status: 'rerendered', htmlPath: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:58:    await ensureHtmlDoc('vid11111111', '/out', () => {}, { major: 2, minor: 1 });
tests/lib/html-doc/ensure.test.ts:60:    expect(rerender.reRenderSummaryHtml).toHaveBeenCalled();
tests/lib/html-doc/ensure.test.ts:66:    await ensureHtmlDoc('vid11111111', '/out', () => {});
tests/lib/html-doc/ensure.test.ts:69:    expect(rerender.reRenderSummaryHtml).not.toHaveBeenCalled();
tests/lib/html-doc/ensure.test.ts:74:    (rerender.reRenderSummaryHtml as jest.Mock).mockReturnValue({ status: 'rerendered', htmlPath: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:75:    await ensureHtmlDoc('vid11111111', '/out', () => {});
tests/lib/html-doc/ensure.test.ts:77:    expect(rerender.reRenderSummaryHtml).toHaveBeenCalled();
tests/lib/html-doc/ensure.test.ts:83:    await expect(ensureHtmlDoc('vid11111111', '/out', () => {})).rejects.toThrow(/no summary/i);
tests/lib/html-doc/ensure.test.ts:88:  it('major-stale ({2,0}) with cached model → deletes models/<base>.json so fuller bullets regenerate, calls writeSummaryDoc, does NOT call reRenderSummaryHtml', async () => {
tests/lib/html-doc/ensure.test.ts:92:      await ensureHtmlDoc('vid11111111', '/out', () => {});
tests/lib/html-doc/ensure.test.ts:95:      expect(rerender.reRenderSummaryHtml).not.toHaveBeenCalled();
tests/lib/html-doc/ensure.test.ts:103:    await ensureHtmlDoc('vid11111111', '/out', () => {}, CURRENT_DOC_VERSION, true);
tests/lib/html-doc/ensure.test.ts:111:    await ensureHtmlDoc('vid11111111', '/out', () => {}, CURRENT_DOC_VERSION, false);
lib/html-doc/batch.ts:5:import { ensureHtmlDoc } from './ensure';
lib/html-doc/batch.ts:85:        await ensureHtmlDoc(item.videoId, outputFolder, () => {});
tests/lib/html-doc/build-doc-html.test.ts:21:// assertOutputFolder (via reRenderSummaryHtml) requires paths under homedir on macOS.
tests/lib/html-doc/build-doc-html.test.ts:30:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/a.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:36:    const r = await buildDocHtml(video({ summaryHtml: null }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:42:    const r = await buildDocHtml(video({ summaryHtml: 'secret.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:47:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/../secret.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:52:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/a.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:59:    const r = await buildDocHtml(video({ digDeeperMd: '../../../etc/x-dig-deeper.md' }), dir, 'dig-deeper');
tests/lib/html-doc/build-doc-html.test.ts:64:    const r = await buildDocHtml(video({ digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
lib/html-doc/rerender.ts:27:export async function reRenderSummaryHtml(
lib/html-doc/rerender.ts:97:export async function reRenderAll(outputFolder: string, blobStore?: BlobStore): Promise<ReRenderTally> {
lib/html-doc/rerender.ts:108:      const res = await reRenderSummaryHtml(video.id, outputFolder, resolvedBlob);
lib/html-doc/build-doc-html.ts:6:import { reRenderSummaryHtml } from './rerender';
lib/html-doc/build-doc-html.ts:33:export async function buildDocHtml(
lib/html-doc/build-doc-html.ts:60:    const result = await reRenderSummaryHtml(video.id, outputFolder);
tests/lib/html-doc/batch.test.ts:23:const mockEnsure = jest.mocked(ensureMod.ensureHtmlDoc);
tests/lib/html-doc/batch.test.ts:69:  it('LA4: does not leak ensureHtmlDoc internal progress', async () => {

codex
The restored H-R2-1 test passes again. I’m running the cloud-sync integration subset now for the broader branch-level check, still excluding the known reservation-release suite.
exec
/bin/bash -lc 'npm run test:integration -- tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 16286ms:

> youtube-playlist-summaries@0.1.0 test:integration
> jest --config jest.integration.config.ts --runInBand tests/integration/cloud-sync


Test Suites: 4 passed, 4 total
Tests:       35 passed, 35 total
Snapshots:   0 total
Time:        13.157 s
Ran all test suites matching tests/integration/cloud-sync.

codex
The cloud-sync integration subset is green: 4 suites, 35 tests. I’m checking the file diff one last time so the temporary mutation did not leave any code changes.
exec
/bin/bash -lc 'git diff -- lib/cloud-sync/sync-run.ts && git status --short' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-v3-rereview-codex.md
?? scratchpad/

codex
**Part A Verdicts**

H-R2-1: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.

H-R2-2: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:331) clears `summaryHtml` and `digDeeperHtml`, but no longer sends `digDeeperMd: null`. Preserving `digDeeperMd` can leave old dig sections matched or orphaned against a new summary via [lib/html-doc/dig-merge.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/dig-merge.ts:97), but that is a known M2a boundary: dig is out of scope, orphans are explicit, and destroying the pointer forces re-spend. `digDeeperHtml: null` is sufficient for the stale rendered artifact. `sanitizeAdditiveVideo` still correctly nulls `digDeeperMd` for a receiver with no existing row.

M-R2-2: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.

**Part B Findings**

No new Blocking, High, Medium, or Low defects found in the reviewed scope.

Checked baseline advancement, durable-before-advertise ordering, manifest-after-commit, money-safety, `needsRegen` report-only behavior, RLS/no-service-role usage, and local-vs-Supabase null/deep-merge semantics. The accepted stale non-`summaryMd` artifact-pointer medium remains accepted and was not re-reported.

**Verification**

`npx jest tests/lib/cloud-sync --runInBand` passed: 15 suites, 85 tests.  
`npm run test:integration -- tests/integration/cloud-sync` passed: 4 suites, 35 tests.  
Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.

**CONVERGED**
tokens used
114,731
**Part A Verdicts**

H-R2-1: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:160) now throws before `ensureReceiverSlot` at line 164, so no `setPlaylistMeta`, staged blob write, `claimVideoSlot`, receiver row, or baseline can happen after an unreadable advertised MD body. The remaining `if (video.summaryMd && mdBody != null)` at line 167 is redundant after the guard, but harmless; it does not hide a path because the only alternative is a legitimate summary-less row. I temporarily moved the guard back and the H-R2-1 integration test failed on the bare local row assertion, then restored the file.

H-R2-2: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:331) clears `summaryHtml` and `digDeeperHtml`, but no longer sends `digDeeperMd: null`. Preserving `digDeeperMd` can leave old dig sections matched or orphaned against a new summary via [lib/html-doc/dig-merge.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/html-doc/dig-merge.ts:97), but that is a known M2a boundary: dig is out of scope, orphans are explicit, and destroying the pointer forces re-spend. `digDeeperHtml: null` is sufficient for the stale rendered artifact. `sanitizeAdditiveVideo` still correctly nulls `digDeeperMd` for a receiver with no existing row.

M-R2-2: **GENUINELY FIXED**  
Evidence: [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:491) derives signals before the narrowed guard, and [lib/cloud-sync/backfill.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/backfill.ts:7) is pure over the record plus supplied MD body. The hoist can surface blob-read errors earlier, but that is the right behavior: baseline must not advance if Class-A evidence is unreadable. The both-have-MD conflict path still takes the WB-B1 skip at [lib/cloud-sync/sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:501). The one-sided hydration path writes the copied MD only after `transferClassA` lands, preserves unresolved corrections in Class-B baseline, and continues to report `needsRegen`.

**Part B Findings**

No new Blocking, High, Medium, or Low defects found in the reviewed scope.

Checked baseline advancement, durable-before-advertise ordering, manifest-after-commit, money-safety, `needsRegen` report-only behavior, RLS/no-service-role usage, and local-vs-Supabase null/deep-merge semantics. The accepted stale non-`summaryMd` artifact-pointer medium remains accepted and was not re-reported.

**Verification**

`npx jest tests/lib/cloud-sync --runInBand` passed: 15 suites, 85 tests.  
`npm run test:integration -- tests/integration/cloud-sync` passed: 4 suites, 35 tests.  
Temporary mutation of H-R2-1 failed as expected, then restored; `lib/cloud-sync/sync-run.ts` has no remaining diff.

**CONVERGED**
