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

exec
/bin/bash -lc "sed -n '280,680p' lib/cloud-sync/sync-run.ts" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
    summaryHtml: null,
    digDeeperHtml: null,
    digDeeperMd: null,
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
        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
        if (correctionsUnresolved) {
          report.needsRegen += 1;
          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
          continue;
        }

        // ── Class A (needs the MD bodies for hashing — Behavior #1).
        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
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

exec
/bin/bash -lc "git rev-parse --short HEAD && git status --short && rg -n \"buildCorrectionsUnresolvedBaseline|winner === 'equal'|needsRegen|transferClassA|sanitizeAdditiveVideo|ensureReceiverSlot|merge_video_data|persist_summary|summaryHtml|digDeeperHtml|digDeeperMd|spend_ledger\" lib supabase tests docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
32a164c
 M docs/local-validation-findings.md
 M supabase/config.toml
?? .codex-tasks/
?? docs/reviews/task-12-sync-run-behaviors-codex.md
?? docs/reviews/whole-branch-cloud-sync-codex.md
?? docs/reviews/whole-branch-cloud-sync-v2-rereview-codex.md
?? scratchpad/
lib/serial-migrate.ts:8:  'summaryHtml', 'digDeeperMd', 'digDeeperHtml',
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:127:- **Stamping:** `mdGeneratedAt` + `mdCorrectionsHash` on MD generation (`persist_summary` `0009`; local
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:129:  (`update_video_annotations` `0016`; `merge_video_data`/`updateVideoFields` for `corrections` — **conditional
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:201:  routes through the metered enqueue `lib/job-queue/producer.ts`, never consumes `spend_ledger`, never
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:224:- **`merge_video_data` restamp is CONDITIONAL** on a Class-B key in the patch (it is a blind generic merge also
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:227:- **`persist_summary` / local `pipeline.ts`** stamp `mdGeneratedAt` + `mdCorrectionsHash` on generation, and
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:322:  `merge_video_data` MD-finalize does NOT bump it — round-v7 L-1); membership writers do not.
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:375:7. **Per-playlist manifest**; every MD/human-field SQL writer restamps its timestamp (incl. `merge_video_data`).
lib/index-store.ts:19: *  that is simply absent from `fields` (e.g. a bare `{ summaryHtml: null }` write) is not
tests/e2e/html-doc.spec.ts:7://   - one video that is CURRENT (summaryHtml set AND docVersion: {major:2,minor:0})
tests/e2e/html-doc.spec.ts:9://   - one video that is PRE-FEATURE (summaryHtml set but NO docVersion)
tests/e2e/html-doc.spec.ts:11://   - one video with summaryHtml: null (no docVersion)
tests/e2e/html-doc.spec.ts:13://   - one KO video with summaryHtml: null — used in KO round-trip test
tests/e2e/html-doc.spec.ts:38:    summaryHtml: null,
tests/e2e/html-doc.spec.ts:117:test('a CURRENT video (summaryHtml + docVersion:{2,0}) shows a single HTML doc link — no Generate/Regenerate/View labels', async ({ page }) => {
tests/e2e/html-doc.spec.ts:121:    summaryHtml: 'htmls/deep-dive-into-llms.html',
tests/e2e/html-doc.spec.ts:151:test('a PRE-FEATURE video (summaryHtml set, no docVersion) shows "HTML doc" as a button that starts the job', async ({ page }) => {
tests/e2e/html-doc.spec.ts:152:  // Fixture: summaryHtml set but NO docVersion → treat as stale → button
tests/e2e/html-doc.spec.ts:155:    summaryHtml: 'htmls/deep-dive-into-llms.html',
tests/e2e/html-doc.spec.ts:192:test('a video with no summaryHtml shows "HTML doc" as a button that starts the job and reveals the View link', async ({ page }) => {
tests/e2e/html-doc.spec.ts:193:  // Fixture: EN video with summaryHtml: null (not yet generated)
tests/e2e/html-doc.spec.ts:194:  const video = makeVideo({ id: 'vid-hd1', summaryHtml: null });
tests/e2e/html-doc.spec.ts:230:  // Fixture: EN video with summaryHtml: null; transform stub returns error event
tests/e2e/html-doc.spec.ts:231:  const video = makeVideo({ id: 'vid-hd3', summaryHtml: null });
tests/e2e/html-doc.spec.ts:253:  // The menu still shows "HTML doc" as a button (no file written — summaryHtml still null)
tests/e2e/html-doc.spec.ts:263:  // Fixture: KO video with summaryHtml: null
tests/e2e/html-doc.spec.ts:268:    summaryHtml: null,
tests/e2e/html-doc.spec.ts:323:    summaryHtml: 'htmls/deep-dive-into-llms.html',
supabase/migrations/0016_update_video_annotations.sql:4:-- Distinct from merge_video_data (UNCHANGED, left untouched by this migration):
tests/e2e/batch-docs.spec.ts:10:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
tests/e2e/batch-docs.spec.ts:45:      videos: [v('a', { summaryHtml: 'a.html', docVersion: { major: 3, minor: 3 }, digDeeperMd: null })],
tests/components/VideoList.selection.test.tsx:19:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
tests/components/VideoList.selection.test.tsx:57:    v('a', { summaryHtml: null }),                                   // needs work
tests/components/VideoList.selection.test.tsx:58:    v('b', { summaryHtml: 'b.html', docVersion: { major: 3, minor: 3 } }), // current
tests/components/VideoList.selection.test.tsx:68:  const videos = [v('a', { summaryHtml: null })];
tests/e2e/dig-deeper.spec.ts:185:  summaryHtml: string,
tests/e2e/dig-deeper.spec.ts:200:        body: summaryHtml,
tests/e2e/dig-deeper.spec.ts:266:  const summaryHtml = makeSummaryHtml(VIDEO_ID_SLIDES, START_SEC_SLIDES);
tests/e2e/dig-deeper.spec.ts:269:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:312:  const summaryHtml = makeSummaryHtml(VIDEO_ID_SLIDES, START_SEC_SLIDES);
tests/e2e/dig-deeper.spec.ts:315:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:356:  const summaryHtml = makeSummaryHtml(VIDEO_ID_SLIDES, START_SEC_SLIDES);
tests/e2e/dig-deeper.spec.ts:358:  await stubHtmlRoutes(page, VIDEO_ID_SLIDES, summaryHtml, companionHtml);
tests/e2e/dig-deeper.spec.ts:416:    const summaryHtmlRel = `htmls/${baseName}.html`;
tests/e2e/dig-deeper.spec.ts:432:        summaryHtml: summaryHtmlRel,
tests/e2e/dig-deeper.spec.ts:486:    fs.writeFileSync(path.join(tmpDir, summaryHtmlRel), staleHtml, 'utf-8');
lib/dig/dig-section.ts:104:  // Step 11: Update index with digDeeperMd (HTML is rendered fresh by GET)
lib/dig/dig-section.ts:106:    digDeeperMd: digDeeperFilename,
lib/dig/generate.ts:125:   *  the local dig-section path, which never reserves/releases a spend_ledger entry. */
supabase/migrations/0011_cost_guardrails.sql:12:create table spend_ledger (                                          -- global, one row per UTC day
supabase/migrations/0011_cost_guardrails.sql:17:alter table spend_ledger enable row level security; alter table spend_ledger force row level security;
supabase/migrations/0011_cost_guardrails.sql:18:grant select, insert, update, delete on spend_ledger to service_role;   -- no client access (global infra)
supabase/migrations/0011_cost_guardrails.sql:112:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0011_cost_guardrails.sql:113:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0011_cost_guardrails.sql:188:    from spend_ledger where day = v_day;
tests/e2e/pdf-export.spec.ts:22:    summaryHtml: 'htmls/deep-dive-into-llms.html',
tests/e2e/pdf-export.spec.ts:85:  const video = makeVideo({ id: 'vid-pdf2', digDeeperMd: 'deep-dive-into-llms-dig-deeper.md' });
supabase/migrations/0018_enqueue_dig.sql:61:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0018_enqueue_dig.sql:62:      update spend_ledger set reserved_cents = reserved_cents + v_est, updated_at = now()
supabase/migrations/0014_serve_owner_budget.sql:5:-- 1. Per-owner counter (analog of spend_ledger). force-RLS + service_role-only (no client policy).
supabase/migrations/0014_serve_owner_budget.sql:73:      --     Over-budget owners fail here without ever locking the global spend_ledger money row.
supabase/migrations/0014_serve_owner_budget.sql:81:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0014_serve_owner_budget.sql:82:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0012_serve_model_charge.sql:5:-- 1. Lease/charge marker. force-RLS + service_role-only grants (mirrors spend_ledger, 0011):
supabase/migrations/0012_serve_model_charge.sql:85:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0012_serve_model_charge.sql:86:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
lib/storage/local/local-metadata-store.ts:38:  // `{ summaryHtml: null }` / mdGeneratedAt/mdCorrectionsHash from the regenerate route) must
supabase/migrations/0007_storage_and_rpcs.sql:76:-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
supabase/migrations/0007_storage_and_rpcs.sql:81:create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
supabase/migrations/0007_storage_and_rpcs.sql:97:revoke all on function merge_video_data(uuid, text, jsonb) from public;
supabase/migrations/0007_storage_and_rpcs.sql:98:grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:100:-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
supabase/migrations/0007_storage_and_rpcs.sql:102:create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
supabase/migrations/0007_storage_and_rpcs.sql:121:revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
supabase/migrations/0007_storage_and_rpcs.sql:122:grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:6:--     update_video_annotations / merge_video_data with `create or replace` would create a
supabase/migrations/0021_cloud_sync_signals.sql:12:--     defaulted function. (persist_summary keeps its 5-arg signature unchanged → no drop needed.)
supabase/migrations/0021_cloud_sync_signals.sql:14:drop function if exists merge_video_data(uuid, text, jsonb);
supabase/migrations/0021_cloud_sync_signals.sql:60:-- (2) merge_video_data: conditional annotationsEditedAt restamp when a Class-B key is
supabase/migrations/0021_cloud_sync_signals.sql:62:create or replace function merge_video_data(
supabase/migrations/0021_cloud_sync_signals.sql:92:revoke all on function merge_video_data(uuid, text, jsonb, timestamptz) from public;
supabase/migrations/0021_cloud_sync_signals.sql:93:grant execute on function merge_video_data(uuid, text, jsonb, timestamptz) to authenticated, service_role;
supabase/migrations/0021_cloud_sync_signals.sql:95:-- (3) persist_summary: SAME 5-arg signature (no drop needed). Body copied VERBATIM from 0009
supabase/migrations/0021_cloud_sync_signals.sql:99:create or replace function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0021_cloud_sync_signals.sql:111:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0021_cloud_sync_signals.sql:152:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0021_cloud_sync_signals.sql:154:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0021_cloud_sync_signals.sql:155:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
tests/api/pdf-route.test.ts:25:    overallScore: 4, summaryMd: 'raw/275_x.md', summaryHtml: 'htmls/275_x.html',
tests/api/pdf-route.test.ts:26:    digDeeperMd: 'raw/275_x-dig-deeper.md', processedAt: '2026-06-09T00:00:00.000Z', ...extra,
supabase/migrations/0020_reservation_release.sql:2:-- Reserve→release lifecycle for spend_ledger. Money path — see
supabase/migrations/0020_reservation_release.sql:9:-- Locked down exactly like spend_ledger (0011:17-18): force RLS + NO policy blocks
supabase/migrations/0020_reservation_release.sql:22:grant select, insert on ledger_audit to service_role;  -- the ONLY grant; mirrors spend_ledger
supabase/migrations/0020_reservation_release.sql:80:    update spend_ledger
supabase/migrations/0020_reservation_release.sql:121:    update spend_ledger set reserved_cents = reserved_cents - v_old_amt, updated_at = now()
supabase/migrations/0020_reservation_release.sql:164:    update spend_ledger sl
supabase/migrations/0020_reservation_release.sql:243:      insert into spend_ledger (day) values (v_day) on conflict do nothing;
supabase/migrations/0020_reservation_release.sql:244:      update spend_ledger set reserved_cents = reserved_cents + v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:267:-- released=true also guarded-decrement serve_owner_budget + spend_ledger by magazine_est_cents.
supabase/migrations/0020_reservation_release.sql:290:    update spend_ledger set reserved_cents = reserved_cents - v_cfg.magazine_est_cents, updated_at = now()
supabase/migrations/0020_reservation_release.sql:295:                'settle_serve_model spend_ledger '||p_token::text, now());
supabase/migrations/0015_video_updated_at_trigger.sql:6:-- update — idempotent alongside the RPCs (merge_video_data,
supabase/migrations/0015_video_updated_at_trigger.sql:7:-- merge_video_data_bulk, reconcile_membership) that already set it explicitly
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:104:create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:155:  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:157:revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:158:grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
lib/serial-migrate-exec.ts:128:      if (op.field === 'summaryHtml' || op.field === 'digDeeperHtml') {
lib/archive.ts:84:async function updateIndexIfKnown(principal: Principal, store: MetadataStore, videoId: string, fields: Partial<{ archived: boolean; summaryHtml: string | null }>): Promise<void> {
lib/archive.ts:108:  await updateIndexIfKnown(principal, store, videoId, { archived: true, summaryHtml: null });
lib/archive.ts:124:  await updateIndexIfKnown(principal, store, videoId, { archived: false, summaryHtml: null });
lib/pdf/pdf-path.ts:11: * - dig-deeper: `pdfs/{basename(digDeeperMd) with -dig-deeper.md -> -dig-deeper}.pdf`
lib/pdf/pdf-path.ts:19:    if (!video.digDeeperMd) throw new Error('no dig-deeper doc for this video');
lib/pdf/pdf-path.ts:20:    const b = path.basename(video.digDeeperMd);
tests/components/AskGeminiMenuItem.test.tsx:12:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
lib/cloud-sync/sync-run.ts:8://  - A sync copy NEVER charges: no producer/enqueue import, no spend_ledger touch, no regenerable
lib/cloud-sync/sync-run.ts:9://    cache (summaryHtml/dig/PDF) copied.
lib/cloud-sync/sync-run.ts:14://    so persist_summary is unreachable) and advance the manifest baseline ONLY after the receiver
lib/cloud-sync/sync-run.ts:48:  shareNeedsOwnerServe: number; needsRegen: number; archivedNotSynced: number;
lib/cloud-sync/sync-run.ts:104: *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
lib/cloud-sync/sync-run.ts:107:function sanitizeAdditiveVideo(video: Video): Video {
lib/cloud-sync/sync-run.ts:109:  v.summaryHtml = null;
lib/cloud-sync/sync-run.ts:110:  v.digDeeperHtml = null;
lib/cloud-sync/sync-run.ts:111:  v.digDeeperMd = null;
lib/cloud-sync/sync-run.ts:131:async function ensureReceiverSlot(
lib/cloud-sync/sync-run.ts:142: *  ensureReceiverSlot → stage+verify+promote the MD blob → upsert the sanitized record (advertising
lib/cloud-sync/sync-run.ts:150:  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
lib/cloud-sync/sync-run.ts:171:  const sanitized: any = sanitizeAdditiveVideo(video);
lib/cloud-sync/sync-run.ts:241:        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
lib/cloud-sync/sync-run.ts:245:    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
lib/cloud-sync/sync-run.ts:269:async function transferClassA(
lib/cloud-sync/sync-run.ts:274:    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
lib/cloud-sync/sync-run.ts:282:    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
lib/cloud-sync/sync-run.ts:309:    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
lib/cloud-sync/sync-run.ts:312:    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
lib/cloud-sync/sync-run.ts:313:    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
lib/cloud-sync/sync-run.ts:314:    summaryHtml: null,
lib/cloud-sync/sync-run.ts:315:    digDeeperHtml: null,
lib/cloud-sync/sync-run.ts:316:    digDeeperMd: null,
lib/cloud-sync/sync-run.ts:317:    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
lib/cloud-sync/sync-run.ts:356:    if (m.winner === 'equal' && m.conflict) {
lib/cloud-sync/sync-run.ts:387:function buildCorrectionsUnresolvedBaseline(
lib/cloud-sync/sync-run.ts:404:    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
lib/cloud-sync/sync-run.ts:471:        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
lib/cloud-sync/sync-run.ts:473:          report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:475:          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
lib/cloud-sync/sync-run.ts:483:        if (decision.needsRegen) report.needsRegen += 1;
lib/cloud-sync/sync-run.ts:493:          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
lib/cloud-sync/sync-run.ts:497:          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
lib/storage/supabase/supabase-metadata-store.ts:118:  // Stage 3 (§5.1/§5.7): merge_video_data (0021) stamps annotationsEditedAt server-side
lib/storage/supabase/supabase-metadata-store.ts:130:    const { error } = await this.client.rpc('merge_video_data', {
lib/storage/supabase/supabase-metadata-store.ts:148:    const { error } = await this.client.rpc('merge_video_data_bulk', {
lib/storage/supabase/supabase-metadata-store.ts:248:  // updateVideoAnnotations: distinct write path from updateVideoFields/merge_video_data
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
lib/storage/metadata-store.ts:44:   *  this is a distinct write path from updateVideoFields/merge_video_data, which is
tests/api/regenerate.test.ts:159:  it('clears summaryHtml in the index update on success', async () => {
tests/api/regenerate.test.ts:164:      expect.objectContaining({ summaryHtml: null }),
tests/api/regenerate.test.ts:168:  it('includes summaryHtml: null in the JSON response on success', async () => {
tests/api/regenerate.test.ts:172:    expect(body).toEqual(expect.objectContaining({ summaryHtml: null }));
lib/paths/assert-within.ts:10: * Use this before every read of an index-supplied relative path (summaryMd, digDeeperMd,
lib/storage/worker-persistence.ts:16:/** Thin wrapper over the persist_summary RPC (Task 2). Merges `video` into
lib/storage/worker-persistence.ts:22:  const { error } = await client.rpc('persist_summary', {
lib/html-doc/generate.ts:48:  // re-render is gated on summaryHtml (set only on full success), and a retry overwrites it atomically.
lib/html-doc/generate.ts:72:    await store.updateVideoFields(principal, videoId, { summaryHtml: htmlFilename });
lib/html-doc/ensure.ts:16: * cheap re-render; no HTML yet → full build; already current → nothing. Leaves summaryHtml + docVersion
lib/html-doc/ensure.ts:54:  } else if (!video.summaryHtml) {
tests/components/VideoMenu.test.tsx:23:  renderMenu(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 3, minor: 3 } } as any} />);
tests/components/VideoMenu.test.tsx:30:  renderMenu(<VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} />);
tests/components/VideoMenu.test.tsx:35:  renderMenu(<VideoMenu {...props} busy video={{ ...base, summaryHtml: 'htmls/base.html', docVersion: { major: 3, minor: 3 } } as any} />);
tests/components/VideoMenu.test.tsx:71:it('shows "Save summary PDF" only when summaryHtml is present', () => {
tests/components/VideoMenu.test.tsx:73:  expect(screen.queryByText(/Save summary PDF/i)).toBeNull(); // summaryMd only, no summaryHtml
tests/components/VideoMenu.test.tsx:74:  rerender(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} /></ScopeProvider>);
tests/components/VideoMenu.test.tsx:78:it('shows "Save dig-deeper PDF" only when digDeeperMd is present', () => {
tests/components/VideoMenu.test.tsx:79:  const { rerender } = render(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html' } as any} /></ScopeProvider>);
tests/components/VideoMenu.test.tsx:81:  rerender(<ScopeProvider scope={LOCAL_SCOPE}><VideoMenu {...props} video={{ ...base, summaryHtml: 'htmls/base.html', digDeeperMd: 'base-dig-deeper.md' } as any} /></ScopeProvider>);
tests/components/VideoMenu.test.tsx:89:    video={{ ...base, summaryHtml: 'htmls/base.html', digDeeperMd: 'base-dig-deeper.md' } as any} />);
tests/components/VideoMenu.test.tsx:98:  renderMenu(<VideoMenu {...props} busy video={{ ...base, summaryHtml: 'htmls/base.html' } as any} />);
tests/components/VideoMenu.test.tsx:109:  summaryHtml: 'htmls/base.html',
tests/components/VideoMenu.test.tsx:110:  digDeeperMd: 'base-dig-deeper.md',
lib/html-doc/rerender.ts:11:  | { status: 'skipped-not-eligible' }   // no video / no summaryMd / no summaryHtml — nothing to refresh
lib/html-doc/rerender.ts:40:  if (!video || !video.summaryMd || !video.summaryHtml) return { status: 'skipped-not-eligible' };
lib/job-queue/summary-handler.ts:167:    // don't start the irreversible blob/persist sequence. (Full lease-fencing of persist_summary is
lib/html-doc/build-doc-html.ts:41:    const htmlFile = video.summaryHtml;
lib/html-doc/build-doc-html.ts:75:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:77:      digDeeperPath = assertIndexRelPathWithin(outputFolder, video.digDeeperMd);
lib/html-doc/build-doc-html.ts:86:  if (video.digDeeperMd) {
lib/html-doc/build-doc-html.ts:87:    const digRel = video.digDeeperMd;
lib/html-doc/batch.ts:35:  const companionRel = video.digDeeperMd ?? `${path.basename(video.summaryMd, '.md')}-dig-deeper.md`;
lib/html-doc/eligibility.ts:12:  return !!v.summaryMd && (!v.summaryHtml || isOlder(v.docVersion ?? { major: 1, minor: 0 }, CURRENT_DOC_VERSION));
lib/html-doc/eligibility.ts:23:  return summaryNeedsWork(v) || (!!v.summaryMd && !v.digDeeperMd);
tests/api/dig-state.test.ts:33:    digDeeperMd: null,
tests/api/dig-state.test.ts:91:it('returns { sectionIds: [] } when digDeeperMd is null on the video', async () => {
tests/api/dig-state.test.ts:92:  writeIndex(video({ digDeeperMd: null }));
tests/api/dig-state.test.ts:100:it('returns { sectionIds: [] } when digDeeperMd is absent on the video', async () => {
tests/api/dig-state.test.ts:101:  // digDeeperMd omitted entirely
tests/api/dig-state.test.ts:111:  writeIndex(video({ digDeeperMd: 'test-video-dig-deeper.md' }));
tests/api/dig-state.test.ts:122:  writeIndex(video({ digDeeperMd: 'test-video-dig-deeper.md' }));
tests/api/dig-state.test.ts:132:  writeIndex(video({ digDeeperMd: 'test-video-dig-deeper.md' }));
tests/components/CorrectionsPanel.test.tsx:118:    it('calls onSuccess with tldr, takeaways, corrections, and summaryHtml:null on success', async () => {
tests/components/CorrectionsPanel.test.tsx:125:        summaryHtml: null,
tests/integration/schema.test.ts:11:                              'usage_counters','spend_ledger','quota_allowance','guardrail_config')
tests/integration/schema.test.ts:24:      { relname: 'spend_ledger', relrowsecurity: true, relforcerowsecurity: true },
tests/integration/schema.test.ts:65:  it('defines ZERO policies on the service-role-only tables spend_ledger and guardrail_config (1D-1)', async () => {
tests/integration/schema.test.ts:72:              and tablename in ('spend_ledger','guardrail_config')
tests/api/html-doc-pipeline.test.ts:60:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
tests/api/html-doc-pipeline.test.ts:106:  expect(before.status).toBe(404); // summaryHtml is null until generation runs
tests/integration/serve-model-charge.test.ts:16:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-model-charge.test.ts:34:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:45:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:61:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:104:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:105:  expect(led ?? []).toEqual([]); // the spend_ledger insert (step 5) rolled back with the claim — no row for the day
tests/integration/serve-model-charge.test.ts:121:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:196:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:211:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:235:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-model-charge.test.ts:251:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/cost-guardrails.test.ts:41:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01'); // clear all ledger days
tests/integration/cost-guardrails.test.ts:70:it('lets an owner read only their own usage_counters and denies spend_ledger/guardrail_config reads', async () => {
tests/integration/cost-guardrails.test.ts:78:  const led = await sa.from('spend_ledger').select('*'); // no client grant → error, not []
tests/integration/cost-guardrails.test.ts:207:  const before = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/cost-guardrails.test.ts:210:  const after = await svc.from('spend_ledger').select('day,reserved_cents').order('day');
tests/integration/video-updated-at.test.ts:4:// `updated_at` on EVERY row update — not just the RPC paths (merge_video_data,
tests/integration/video-updated-at.test.ts:5:// merge_video_data_bulk, reconcile_membership) that already set it explicitly.
tests/integration/video-updated-at.test.ts:39:it('trigger bumps videos.updated_at on the merge_video_data RPC path AND the direct upsertVideo(.update) path; readIndex surfaces it as Video.updatedAt', async () => {
tests/integration/video-updated-at.test.ts:49:  // --- Path 1: updateVideoFields → merge_video_data RPC (already sets updated_at explicitly;
tests/integration/metadata-store.test.ts:156:    // merge_video_data does a plain shallow merge (no special write-once guard at the DB
tests/integration/metadata-store.test.ts:191:    // deep-merge in merge_video_data must preserve both keys
tests/integration/pdf-cloud.test.ts:20://    and spend_ledger is unchanged — proven against a mutation control (same request shape, no
tests/integration/pdf-cloud.test.ts:212:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/pdf-cloud.test.ts:216:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/pdf-cloud.test.ts:319:  it('money: fresh model -> PDF request makes NO reserve_serve_model RPC on EITHER a cache-MISS or a genuine cache-HIT; spend_ledger unchanged', async () => {
tests/integration/pdf-cloud.test.ts:323:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/pdf-cloud.test.ts:347:      const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/api/dig-post.test.ts:99:  digDeeperMd: null,
tests/api/dig-post.test.ts:100:  digDeeperHtml: null,
tests/api/dig-post.test.ts:306:  it('calls updateVideoFields with digDeeperMd only (no digDeeperHtml stamp)', async () => {
tests/api/dig-post.test.ts:313:        digDeeperMd: expect.any(String),
tests/api/dig-post.test.ts:316:    // digDeeperHtml must NOT be stamped — GET renders the HTML fresh on every request
tests/api/dig-post.test.ts:318:    expect(call).not.toHaveProperty('digDeeperHtml');
tests/integration/annotations-rpc.test.ts:7:// This RPC is a DISTINCT write path from merge_video_data (unchanged): it allowlists
tests/integration/annotations-rpc.test.ts:144:  // (f) an existing merge_video_data write of summaryHtml:null still stores null
tests/integration/annotations-rpc.test.ts:145:  // (regression guard: merge_video_data itself is UNCHANGED by this migration).
tests/integration/annotations-rpc.test.ts:146:  it('merge_video_data (unchanged) still stores an explicit null for summaryHtml', async () => {
tests/integration/annotations-rpc.test.ts:153:    await store.updateVideoFields(p, videoId, { summaryHtml: null } as any);
tests/integration/annotations-rpc.test.ts:157:    expect(v.summaryHtml).toBeNull();
tests/integration/reservation-release.test.ts:22:  // ledger_audit and spend_ledger rows scoped by day. A far-past FIXED date can never collide
tests/integration/reservation-release.test.ts:64:  if (error) throw error;   // 150¢ reserved on today's spend_ledger
tests/integration/reservation-release.test.ts:91:  const { data } = await adminClient().from('spend_ledger').select('reserved_cents').eq('day', day).maybeSingle();
tests/integration/reservation-release.test.ts:151:    await adminClient().from('spend_ledger').update({ reserved_cents: 10 }).eq('day', day);
tests/integration/reservation-release.test.ts:171:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:232:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:274:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 150 });
tests/integration/reservation-release.test.ts:309:    await adminClient().from('spend_ledger').upsert({ day: yday, reserved_cents: 10 });
tests/integration/reservation-release.test.ts:364:    // NOTE: spend_ledger is a single row PER DAY shared by every test in this file (Tasks 1-4 leave
tests/integration/reservation-release.test.ts:366:    // freshly-created owner's row is genuinely isolated — asserted absolutely. spend_ledger uses a
tests/integration/reservation-release.test.ts:379:    expect(await ledgerFor(day)).toBe(ledgerBefore);            // spend_ledger -=6 (back to baseline)
tests/integration/reservation-release.test.ts:476:    expect(await ledgerFor(day)).toBe(before);           // reaper touches jobs, never spend_ledger — KEEP
tests/integration/reservation-release.test.ts:530:    // re-claim itself does NOT add a second reservation (claim_next_job never touches spend_ledger).
tests/integration/reservation-release.test.ts:610:    expect(await ledgerFor(day)).toBe(before);              // spend_ledger unchanged — accepted §2.4b residual (KEPT forever, no reaper release)
tests/integration/reservation-release.test.ts:622:    // Deterministic baseline: this file's shared "today" spend_ledger row accumulates residue
tests/integration/reservation-release.test.ts:625:    await svc.from('spend_ledger').update({ reserved_cents: 0 }).eq('day', day);
tests/integration/share-route.test.ts:107:    const { data: ledger } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/share-route.test.ts:127:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/serve-doc-materialize.test.ts:42:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-doc-materialize.test.ts:49:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-doc-materialize.test.ts:270:// release rule). beforeEach fully clears spend_ledger/serve_owner_budget/serve_model_charge, so any
tests/integration/cloud-sync/cloud-stamping.int.test.ts:21:  it('cloud store forwards opts.editedAt through updateVideoFields (merge_video_data)', async () => {
tests/integration/dig-cloud.test.ts:54:  await admin.from('spend_ledger').delete().neq('day', '1970-01-01');
tests/integration/dig-cloud.test.ts:114:    const { data: slBefore } = await admin.from('spend_ledger').select('*'); // spend_ledger is global-by-day
tests/integration/dig-cloud.test.ts:120:    // The dedup (200-ready) path must also leave the global spend_ledger untouched — a spurious
tests/integration/dig-cloud.test.ts:122:    const { data: slAfter } = await admin.from('spend_ledger').select('*');
tests/integration/dig-serve-interactive.test.ts:81:    const { data: before } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/dig-serve-interactive.test.ts:89:    const { data: after } = await admin.from('spend_ledger').select('amount_cents');
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:55:  //    Two-sided, DIVERGENT bodies → reconcileClassA returns copyToCloud → transferClassA runs.
tests/integration/cloud-sync/e2e.int.test.ts:77:    // transferClassA promote→finalize genuinely ran: the loser (cloud) blob holds the WINNER bytes.
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:228:  // ── Row 8 — additive create never calls the metered enqueue (spend_ledger unchanged).
tests/integration/cloud-sync/e2e.int.test.ts:229:  it('row 8: additive hydrate never charges (spend_ledger unchanged)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:268:  // ── Row 11 — additive create excludes regenerable cache (summaryHtml/PDF null/absent on receiver).
tests/integration/cloud-sync/e2e.int.test.ts:269:  it('row 11: additive create excludes regenerable cache (no summaryHtml/pdf copied)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:273:      summaryHtml: '<html>cached</html>',
tests/integration/cloud-sync/e2e.int.test.ts:274:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:280:    expect(local?.summaryHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:332:  // ── Row 15 — additive publish CREATES the receiver row (ensureReceiverSlot); re-run is not a delete.
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:455:  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
tests/integration/cloud-sync/e2e.int.test.ts:456:  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:462:      summaryHtml: '<html>STALE rendered from the old local body</html>',
tests/integration/cloud-sync/e2e.int.test.ts:472:    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
tests/integration/cloud-sync/stamping.int.test.ts:4:// behavior: per-field annotationsEditedAt on update_video_annotations/merge_video_data,
tests/integration/cloud-sync/stamping.int.test.ts:6:// persist_summary's mdGeneratedAt/mdCorrectionsHash passthrough.
tests/integration/cloud-sync/stamping.int.test.ts:64:    // Same for merge_video_data's 3-key call:
tests/integration/cloud-sync/stamping.int.test.ts:65:    await ctx.rpc('merge_video_data', { p_playlist_id: playlistId, p_video_id: videoId, p_fields: { corrections: 'z' } });
tests/integration/cloud-sync/stamping.int.test.ts:80:  it('merge_video_data does NOT stamp annotationsEditedAt for a non-Class-B (MD-finalize) write', async () => {
tests/integration/cloud-sync/stamping.int.test.ts:83:    await ctx.rpc('merge_video_data', {
tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
tests/integration/cloud-sync/stamping.int.test.ts:90:  it('persist_summary stamps mdGeneratedAt + mdCorrectionsHash', async () => {
tests/api/html-serve.test.ts:25:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
tests/api/html-serve.test.ts:47:  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
tests/api/html-serve.test.ts:54:  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
tests/api/html-serve.test.ts:60:it('404s on a path-traversal summaryHtml value (Codex BLOCKING)', async () => {
tests/api/html-serve.test.ts:61:  writeIndex(video({ summaryHtml: '../../../../etc/passwd' }));
tests/api/html-serve.test.ts:67:it('404s when summaryHtml is unset', async () => {
tests/api/html-serve.test.ts:68:  writeIndex(video({ summaryHtml: null }));
tests/api/html-serve.test.ts:74:  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
tests/api/html-serve.test.ts:84:  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
tests/api/html-serve.test.ts:97:  writeIndex(video({ summaryHtml: koFile }));
tests/api/html-serve.test.ts:166:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
tests/api/html-serve.test.ts:176:it('dig-deeper B2: digDeeperMd null → skeleton 200 (all summary sections rendered)', async () => {
tests/api/html-serve.test.ts:178:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
tests/api/html-serve.test.ts:189:  writeIndex(video({ summaryMd: 'wiki/nonexistent.md', digDeeperMd: null }));
tests/api/html-serve.test.ts:199:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: null }));
tests/api/html-serve.test.ts:209:it('dig-deeper B5: path-traversal digDeeperMd → 400', async () => {
tests/api/html-serve.test.ts:210:  // The base derived from a crafted digDeeperMd with ".." would escape outputFolder
tests/api/html-serve.test.ts:214:    digDeeperMd: '../../../etc/video-dig-deeper.md',
tests/api/html-serve.test.ts:244:  writeIndex(video({ summaryMd: summaryRel, digDeeperMd: 'wiki/video-dig-deeper.md' }));
tests/api/html-serve.test.ts:252:it('dig-deeper B7: digDeeperMd set but file absent on disk → skeleton 200 (not 500)', async () => {
tests/api/html-serve.test.ts:258:    digDeeperMd: 'wiki/video-dig-deeper.md', // set in index, but NOT written to disk
tests/api/html-serve.test.ts:271:  // summaryMd is safe; digDeeperMd escapes → companion assertWithin fires → 400.
tests/api/html-serve.test.ts:275:    digDeeperMd: '../../../etc/companion.md',      // escapes outputFolder immediately
tests/api/html-serve.test.ts:282:  writeIndex(video({ summaryHtml: 'htmls/a.html' }));
tests/api/html-serve.test.ts:303:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:314:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:328:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:343:    writeIndex(video({ summaryHtml: 'htmls/a.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:353:    writeIndex(video({ summaryHtml: 'htmls/missing.html', summaryMd: 'wiki/a.md' }));
tests/api/html-serve.test.ts:361:  it('B6: null summaryHtml → 404', async () => {
tests/api/html-serve.test.ts:362:    writeIndex(video({ summaryHtml: null }));
tests/integration/serve-owner-budget.test.ts:21:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/serve-owner-budget.test.ts:41:  led: (await svc.from('spend_ledger').select('*').order('day')).data ?? [],
tests/integration/serve-owner-budget.test.ts:58:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/serve-owner-budget.test.ts:176:  const { data: led } = await svc.from('spend_ledger').select('reserved_cents');
tests/integration/html-download.test.ts:50:  // Supabase stack persists across test runs, so a stale spend_ledger row from an earlier file/run
tests/integration/html-download.test.ts:54:  await svc.from('spend_ledger').delete().neq('day', '1900-01-01');
tests/integration/html-download.test.ts:122:  it('C2: owner GET format=md&download=1 → 200 text/markdown, attachment filename="<base>.md"; no reserve_serve_model call; spend_ledger unchanged', async () => {
tests/integration/html-download.test.ts:125:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:134:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:143:    const { data: ledgerBefore } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/html-download.test.ts:152:    const { data: ledgerAfter } = await svc.from('spend_ledger').select('*').order('day');
tests/integration/worker-persistence-rpcs.test.ts:59:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:60:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:67:test('persist_summary preserves a sibling artifact kind (deepDiveMd) across a summaryMd status write', async () => {
tests/integration/worker-persistence-rpcs.test.ts:71:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:74:  // deep-dive artifact) so we can assert persist_summary never touches other artifact kinds.
tests/integration/worker-persistence-rpcs.test.ts:86:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:94:test('persist_summary status is monotonic — a committed write never downgrades a promoted artifact', async () => {
tests/integration/worker-persistence-rpcs.test.ts:99:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:100:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:105:test('persist_summary preserves operational fields owned by other features (archived) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:109:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:118:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T', archived: false }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:126:test('persist_summary preserves ALL concurrent non-summary state (membership order + other-feature fields) against the stale payload', async () => {
tests/integration/worker-persistence-rpcs.test.ts:130:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3 }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:132:  // A concurrent writer (reconcile_membership / merge_video_data / dig pipeline) reorders the video
tests/integration/worker-persistence-rpcs.test.ts:135:  const updated = { ...before.data!.data, playlistIndex: 9, digDeeperMd: 'dd.md' };
tests/integration/worker-persistence-rpcs.test.ts:139:  // The stale enqueue-time payload still carries playlistIndex:3 and no digDeeperMd — persist_summary
tests/integration/worker-persistence-rpcs.test.ts:141:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_t.md', playlistIndex: 3, ratings: { usefulness: 5 } }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:145:  expect(row.data!.data.digDeeperMd).toBe('dd.md');    // other-feature field preserved
tests/integration/worker-persistence-rpcs.test.ts:156:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: full, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:159:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, title: 'T' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:168:test('persist_summary monotonic status is KEY-SCOPED — a committed write with a NEW key is allowed through', async () => {
tests/integration/worker-persistence-rpcs.test.ts:172:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_old.md' }, p_artifact_status: 'promoted' });
tests/integration/worker-persistence-rpcs.test.ts:175:  await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid, summaryMd: '1_new.md' }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:192:test('persist_summary raises when there is no video row', async () => {
tests/integration/worker-persistence-rpcs.test.ts:195:  const res = await admin.rpc('persist_summary', { p_owner_id: userId, p_playlist_id: pl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
tests/integration/worker-persistence-rpcs.test.ts:211:test('persist_summary rejects an owner mismatch', async () => {
tests/integration/worker-persistence-rpcs.test.ts:218:  const res = await admin.rpc('persist_summary', { p_owner_id: aid, p_playlist_id: victimPl, p_video_id: vid, p_video: { id: vid }, p_artifact_status: 'committed' });
tests/integration/helpers/cloud.ts:69:  /** Sum of reserved_cents + actual_cents across spend_ledger (money-safety assertions).
tests/integration/helpers/cloud.ts:70:   *  spend_ledger is GLOBAL (one row per UTC day, NO owner_id) → whole-table total; money-safety
tests/integration/helpers/cloud.ts:72:   *  spend_ledger grants NO client access. */
tests/integration/helpers/cloud.ts:118:      const { error } = await userClient.rpc('persist_summary', {
tests/integration/helpers/cloud.ts:149:        .from('spend_ledger').select('reserved_cents,actual_cents');
tests/integration/helpers/cloud.ts:199:    // ensureReceiverSlot creates the cloud playlist row during the run.
tests/integration/helpers/cloud.ts:283:// the e2e scenarios can drive the divergent-MD Class-A COPY path (transferClassA
tests/integration/helpers/cloud.ts:315:  summaryHtml?: string;
tests/integration/helpers/cloud.ts:316:  digDeeperHtml?: string;
tests/integration/helpers/cloud.ts:369:    ...(f.summaryHtml !== undefined ? { summaryHtml: f.summaryHtml } : {}),
tests/integration/helpers/cloud.ts:370:    ...(f.digDeeperHtml !== undefined ? { digDeeperHtml: f.digDeeperHtml } : {}),
tests/integration/helpers/seed.ts:19: *  persist_summary 0009). Sets top-level owner_id (NOT NULL + composite FK) and a `data` jsonb
tests/lib/serial-migrate-exec.test.ts:151:        summaryHtml: 'htmls/alpha.html',
tests/lib/serial-migrate.test.ts:40:      summaryHtml: 'htmls/foo.html',
tests/lib/serial-migrate.test.ts:47:    field: 'summaryHtml',
tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
tests/lib/archive-html.test.ts:24:    summaryHtml: 'htmls/a.html', processedAt: '2026-06-09T00:00:00.000Z',
tests/lib/archive-html.test.ts:29:it('deletes cached summary HTML and clears summaryHtml on archive', async () => {
tests/lib/archive-html.test.ts:33:  expect(idx.videos[0].summaryHtml).toBeNull();
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
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
tests/lib/cloud-sync/regenerate-stamp.test.ts:5:// that persists refreshed tldr/takeaways/summaryHtml — also stamps mdGeneratedAt and
tests/lib/html-doc/eligibility.test.ts:10:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
tests/lib/html-doc/eligibility.test.ts:20:  it('needs work when summaryHtml missing', () => {
tests/lib/html-doc/eligibility.test.ts:21:    expect(summaryNeedsWork(v({ summaryHtml: null }))).toBe(true);
tests/lib/html-doc/eligibility.test.ts:24:    expect(summaryNeedsWork(v({ summaryHtml: 'h.html', docVersion: { major: 2, minor: 0 } }))).toBe(true);
tests/lib/html-doc/eligibility.test.ts:27:    expect(summaryNeedsWork(v({ summaryHtml: 'h.html', docVersion: { major: 3, minor: 3 } }))).toBe(false);
tests/lib/html-doc/eligibility.test.ts:30:    expect(summaryNeedsWork(v({ summaryMd: null, summaryHtml: null }))).toBe(false);
tests/lib/html-doc/eligibility.test.ts:36:    expect(videoNeedsBatchWork(v({ summaryHtml: null }), 'summary')).toBe(true);
tests/lib/html-doc/eligibility.test.ts:37:    expect(videoNeedsBatchWork(v({ summaryHtml: 'h.html', docVersion: { major: 3, minor: 3 } }), 'summary')).toBe(false);
tests/lib/html-doc/eligibility.test.ts:40:    expect(videoNeedsBatchWork(v({ summaryHtml: 'h.html', docVersion: { major: 3, minor: 3 }, digDeeperMd: null }), 'summary-dig')).toBe(true);
tests/lib/html-doc/eligibility.test.ts:41:    expect(videoNeedsBatchWork(v({ summaryHtml: 'h.html', docVersion: { major: 3, minor: 3 }, digDeeperMd: 'x-dig-deeper.md' }), 'summary-dig')).toBe(false);
tests/lib/html-doc/eligibility.test.ts:42:    expect(videoNeedsBatchWork(v({ summaryMd: null, summaryHtml: null, digDeeperMd: null }), 'summary-dig')).toBe(false); // no summary → nothing
tests/lib/pdf/pdf-path.test.ts:17:    expect(pdfRelPath(v({ digDeeperMd: 'raw/275_google-okf-dig-deeper.md' }), 'dig-deeper')).toBe(
tests/lib/pdf/pdf-path.test.ts:26:  it('dig-deeper without digDeeperMd throws', () => {
tests/lib/serial-invariant.test.ts:58:    const v = makeVideo({ serialNumber: 7, summaryMd: null, summaryHtml: null });
tests/lib/serial-invariant.test.ts:63:    const v = makeVideo({ serialNumber: 7, summaryHtml: 'htmls/x.html' });
tests/lib/serial-invariant.test.ts:66:    expect(out[0]).toMatchObject({ field: 'summaryHtml', reason: 'prefix', expected: 'htmls/007_x.html' });
tests/lib/serial-invariant.test.ts:70:    const v = makeVideo({ serialNumber: 7, summaryMd: '007_x.md', digDeeperMd: 'x-dig-deeper.md' });
tests/lib/serial-invariant.test.ts:73:    expect(out[0]).toMatchObject({ field: 'digDeeperMd', reason: 'prefix' });
tests/lib/serial-invariant.test.ts:94:      summaryHtml: 'x.html',
tests/lib/serial-invariant.test.ts:95:      digDeeperMd: 'x-dig-deeper.md',
tests/lib/serial-invariant.test.ts:98:    expect(fields).toEqual(['digDeeperMd', 'summaryHtml']);
tests/lib/serial-invariant.test.ts:108:      summaryHtml: 'e.html',
tests/lib/serial-invariant.test.ts:109:      digDeeperMd: 'g.md',
tests/lib/serial-invariant.test.ts:110:      digDeeperHtml: 'h.html',
tests/lib/html-doc/build-doc-html.test.ts:16:    overallScore: 4, summaryMd: 'a.md', summaryHtml: null,
tests/lib/html-doc/build-doc-html.test.ts:26:  it('current summaryHtml → { ok:true, html }', async () => {
tests/lib/html-doc/build-doc-html.test.ts:30:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/a.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:35:  it('no summaryHtml → { ok:false, missing-html }', async () => {
tests/lib/html-doc/build-doc-html.test.ts:36:    const r = await buildDocHtml(video({ summaryHtml: null }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:40:  it('summaryHtml not under htmls/ (secret.html) → not served', async () => {
tests/lib/html-doc/build-doc-html.test.ts:42:    const r = await buildDocHtml(video({ summaryHtml: 'secret.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:46:  it('summaryHtml traversal (htmls/../secret.html) → not served', async () => {
tests/lib/html-doc/build-doc-html.test.ts:47:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/../secret.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:51:  it('summaryHtml file missing on disk → { ok:false, missing-html }', async () => {
tests/lib/html-doc/build-doc-html.test.ts:52:    const r = await buildDocHtml(video({ summaryHtml: 'htmls/a.html' }), dir, 'summary');
tests/lib/html-doc/build-doc-html.test.ts:58:  it('crafted digDeeperMd traversal → { ok:false, invalid-path }', async () => {
tests/lib/html-doc/build-doc-html.test.ts:59:    const r = await buildDocHtml(video({ digDeeperMd: '../../../etc/x-dig-deeper.md' }), dir, 'dig-deeper');
tests/lib/html-doc/build-doc-html.test.ts:64:    const r = await buildDocHtml(video({ digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
tests/lib/html-doc/build-doc-html.test.ts:71:    const r = await buildDocHtml(video({ summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' }), dir, 'dig-deeper');
tests/lib/html-doc/generate.test.ts:65:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',
tests/lib/html-doc/generate.test.ts:78:it('transforms, writes htmls/<base>.html, and records summaryHtml', async () => {
tests/lib/html-doc/generate.test.ts:93:  expect(idx.videos[0].summaryHtml).toBe('htmls/a-title.html');
tests/lib/html-doc/generate.test.ts:103:  expect(idx.videos[0].summaryHtml).toBeNull();
tests/lib/storage/supabase-metadata-store.test.ts:321:  test('calls merge_video_data RPC with correct args', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:327:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
tests/lib/storage/supabase-metadata-store.test.ts:343:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data');
tests/lib/storage/supabase-metadata-store.test.ts:355:  test('calls merge_video_data_bulk with mapped { video_id, fields } shape', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:365:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/storage/supabase-metadata-store.test.ts:380:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/storage/supabase-metadata-store.test.ts:394:    const rpc = client.rpcCalls.find((c) => c.name === 'merge_video_data_bulk');
tests/lib/html-doc/rerender.test.ts:61:    summaryHtml: 'htmls/a-title.html', processedAt: '2026-06-09T00:00:00.000Z',
tests/lib/html-doc/rerender.test.ts:116:  it('skips when the video has no summaryHtml (nothing existing to refresh)', async () => {
tests/lib/html-doc/rerender.test.ts:118:    writeIndex([baseVideo({ summaryHtml: null })]);
tests/lib/html-doc/rerender.test.ts:181:    // video B: summaryMd + summaryHtml set but NO model → skipped-no-model
tests/lib/html-doc/rerender.test.ts:183:    const vidB = baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' });
tests/lib/html-doc/rerender.test.ts:198:    const vidC = baseVideo({ id: 'vidC', summaryMd: null, summaryHtml: null });
tests/lib/html-doc/rerender.test.ts:211:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
tests/lib/html-doc/rerender.test.ts:224:    writeIndex([baseVideo(), baseVideo({ id: 'vidB', summaryMd: 'b-title.md', summaryHtml: 'htmls/b-title.html' })]);
tests/lib/html-doc/ensure.test.ts:37:    withVideo({ docVersion: undefined, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:49:    withVideo({ docVersion: { major: 3, minor: 3 }, summaryHtml: null });
tests/lib/html-doc/ensure.test.ts:56:    withVideo({ docVersion: { major: 2, minor: 0 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:65:    withVideo({ docVersion: { major: 3, minor: 3 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:73:    withVideo({ docVersion: { major: 3, minor: 0 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:89:    withVideo({ docVersion: { major: 2, minor: 0 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:102:    withVideo({ docVersion: { major: 3, minor: 3 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/ensure.test.ts:110:    withVideo({ docVersion: { major: 3, minor: 3 }, summaryHtml: 'htmls/base.html' });
tests/lib/html-doc/batch.test.ts:33:    summaryHtml: null, processedAt: '2026-06-29T00:00:00.000Z', docVersion: { major: 3, minor: 3 },
tests/lib/html-doc/batch.test.ts:51:    indexWith([v('a', { summaryHtml: null }), v('b', { summaryHtml: 'b.html', docVersion: { major: 3, minor: 3 } })]);
tests/lib/html-doc/batch.test.ts:105:    indexWith([v('a', { summaryHtml: 'a.html', docVersion: { major: 3, minor: 3 } })]);
tests/lib/html-doc/batch.test.ts:130:    indexWith([v('x', { summaryHtml: null, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:143:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: 'x-dig-deeper.md' })]);
tests/lib/html-doc/batch.test.ts:154:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:164:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md' })]);
tests/lib/html-doc/batch.test.ts:173:    indexWith([v('x', { summaryHtml: 'x.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'x.md', digDeeperMd: null })]);
tests/lib/html-doc/batch.test.ts:185:      v('bad', { summaryHtml: 'bad.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'bad.md', digDeeperMd: null }),
tests/lib/html-doc/batch.test.ts:186:      v('ok', { summaryHtml: 'ok.html', docVersion: { major: 3, minor: 3 }, summaryMd: 'ok.md', digDeeperMd: null }),
tests/lib/dig/dig-section.test.ts:49:  expect(jest.mocked(indexStore.updateVideoFields)).toHaveBeenCalledWith(OF, 'v', { digDeeperMd: 'v-dig-deeper.md' });
tests/lib/ask-gemini.test.ts:13:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z', ...extra,
tests/lib/index-store.test.ts:162:    updateVideoFields(dir, 'vid333333333', { summaryMd: 'vid333333333.md', digDeeperMd: 'vid333333333-dig-deeper.md' });
tests/lib/index-store.test.ts:166:    expect(result.videos[0].digDeeperMd).toBe('vid333333333-dig-deeper.md');
tests/lib/index-store.test.ts:202:  it('carries digDeeperMd/digDeeperHtml fields', () => {
tests/lib/index-store.test.ts:206:      digDeeperMd: 'x-dig-deeper.md',
tests/lib/index-store.test.ts:207:      digDeeperHtml: 'x-dig-deeper.html',
tests/lib/index-store.test.ts:209:    expect(parsed.digDeeperMd).toBe('x-dig-deeper.md');
tests/lib/index-store.test.ts:210:    expect(parsed.digDeeperHtml).toBe('x-dig-deeper.html');

codex
HEAD is `32a164c`; the worktree has unrelated local modifications, so I’ll avoid treating those as branch changes. I’ve located the rewritten hot path; next I’m tracing the storage backends because the null and post-write semantics decide whether the fixes are real.
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
/bin/bash -lc "nl -ba lib/cloud-sync/sync-run.ts | sed -n '90,540p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
   150	  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);
   151	
   152	  let wroteBlob = false;
   153	  if (video.summaryMd) {
   154	    // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
   155	    // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
   156	    // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
   157	    // strand the receiver with a servable-looking row backed by nothing.
   158	    if (mdBody == null) {
   159	      throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
   160	    }
   161	    // stage → verify (readable + hashes) → promote — never advertise promoted before durable.
   162	    const ref = await toBlob.putStaged(toP, video.summaryMd, Buffer.from(mdBody, 'utf8'), 'text/markdown');
   163	    const staged = await toBlob.get(toP, ref.tempKey);
   164	    if (!staged || mdHash(staged.toString('utf8')) !== mdHash(mdBody)) {
   165	      throw new Error(`additive staged MD verify failed for ${video.id}`);
   166	    }
   167	    await toBlob.promote(ref);
   168	    wroteBlob = true;
   169	  }
   170	
   171	  const sanitized: any = sanitizeAdditiveVideo(video);
   172	  if (slot) {
   173	    sanitized.serialNumber = slot.serialNumber;
   174	    sanitized.playlistIndex = slot.position + 1;
   175	  }
   176	  if (wroteBlob) {
   177	    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
   178	  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
   179	    // WB-H1 belt-and-suspenders — no blob written → the receiver must NOT advertise a summaryMd
   180	    // artifact. A summary-less video (row 13, summaryMd == null) legitimately reaches here and must NOT
   181	    // throw and must NOT advertise promoted; strip any residual summaryMd pointer.
   182	    delete sanitized.artifacts.summaryMd;
   183	  }
   184	  await to.upsertVideo(toP, sanitized as Video);
   185	
   186	  // round-4 H1 — the baseline is written by the caller ONLY after this confirms the row landed
   187	  // (an update against an absent row silently no-ops; never advance a baseline for that).
   188	  const after = await to.readIndex(toP);
   189	  const rec = after.videos.find((v) => v.id === video.id);
   190	  if (!rec) {
   191	    throw new Error(`additive create did not persist receiver row for ${video.id}`);
   192	  }
   193	  // WB-H1 (upgrades the deferred T12-M2) — when a blob was written, verify the receiver record
   194	  // actually advertises the PROMOTED summaryMd at the right key (not merely that the row exists), so a
   195	  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
   196	  if (wroteBlob) {
   197	    const art = (rec as any).artifacts?.summaryMd;
   198	    if (art?.status !== 'promoted' || art?.key !== video.summaryMd) {
   199	      throw new Error(`additive create did not advertise promoted summaryMd for ${video.id}`);
   200	    }
   201	  }
   202	}
   203	
   204	/** Manifest baseline for a fresh additive create (no reconcile): both replicas now hold the present
   205	 *  side's values, so this is a true agreed baseline. */
   206	function baselineFromOneSided(
   207	  classA: ClassASignals, mdHashVal: string | null, snapshot: HumanSnapshot,
   208	): VideoBaseline {
   209	  const classB = {} as VideoBaseline['classB'];
   210	  for (const f of FIELDS) classB[f] = { value: snapshot[f].value, editedAt: snapshot[f].editedAt };
   211	  return {
   212	    classA: {
   213	      docVersionMajor: classA.docVersionMajor,
   214	      mdGeneratedAt: classA.mdGeneratedAt,
   215	      mdCorrectionsHash: classA.mdCorrectionsHash,
   216	      mdHash: mdHashVal,
   217	    },
   218	    classB,
   219	  };
   220	}
   221	
   222	/** Behaviors #12 + F3 — apply each Class-B winner to the LOSER side, carrying the SOURCE timestamp
   223	 *  (never now()). A conflict is logged and, when the merge picked no winner (winner==='equal'), the
   224	 *  loser value is skipped (not written). Every write MUST land (found:true) or it throws — a no-op
   225	 *  write on an absent row would let buildBaseline record a false agreement. */
   226	async function applyClassBWinners(args: {
   227	  deps: SyncDeps; localP: Principal; cloudP: Principal; videoId: string;
   228	  merges: Record<HumanField, FieldMerge>; localSnap: HumanSnapshot; cloudSnap: HumanSnapshot;
   229	  dataRoot: string; key: string;
   230	}): Promise<{ merged: number; conflicts: number }> {
   231	  const { deps, localP, cloudP, videoId, merges, localSnap, cloudSnap, dataRoot, key } = args;
   232	  let merged = 0;
   233	  let conflicts = 0;
   234	
   235	  for (const f of FIELDS) {
   236	    const m = merges[f];
   237	    if (m.conflict) {
   238	      await appendConflict(dataRoot, key, {
   239	        video_id: videoId, class: 'B', field: f,
   240	        valueL: localSnap[f].value, valueR: cloudSnap[f].value,
   241	        reason: m.winner === 'equal' ? 'both-changed-skip' : 'both-changed-lww',
   242	      });
   243	      conflicts += 1;
   244	    }
   245	    if (m.winner === 'equal') continue; // truly-equal or conflict-skip → no write
   246	
   247	    // winner is on one side → the OTHER (loser) side receives the winning value.
   248	    const target: Side = m.winner === 'local'
   249	      ? { store: deps.cloud, p: cloudP, blob: deps.cloudBlob }
   250	      : { store: deps.local, p: localP, blob: deps.localBlob };
   251	    const set: Record<string, string | number> = {};
   252	    const clear: HumanField[] = [];
   253	    if (m.value === undefined) clear.push(f);
   254	    else set[f] = m.value;
   255	
   256	    const { found } = await target.store.updateVideoAnnotations(
   257	      target.p, videoId, set as any, clear as any, { editedAt: m.editedAt },
   258	    );
   259	    if (!found) throw new Error(`Class-B write for ${videoId}.${f} landed on no row`);
   260	    merged += 1;
   261	  }
   262	  return { merged, conflicts };
   263	}
   264	
   265	/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
   266	 *  hashes to the expected mdHash → promote → finalize the receiver record in ONE updateVideoFields
   267	 *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
   268	 *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
   269	async function transferClassA(
   270	  winner: Side, loser: Side, winnerVideo: Video, videoId: string,
   271	): Promise<{ mdHash: string; verified: boolean }> {
   272	  const body = await readMdBody(winner.blob, winner.p, winnerVideo);
   273	  if (body == null || !winnerVideo.summaryMd) {
   274	    throw new Error(`transferClassA: winner ${videoId} has no MD body to copy`);
   275	  }
   276	  const h = mdHash(body);
   277	  const key = winnerVideo.summaryMd;
   278	
   279	  const ref = await loser.blob.putStaged(loser.p, key, Buffer.from(body, 'utf8'), 'text/markdown');
   280	  const staged = await loser.blob.get(loser.p, ref.tempKey);
   281	  if (!staged || mdHash(staged.toString('utf8')) !== h) {
   282	    throw new Error(`transferClassA: staged MD verify failed for ${videoId}`);
   283	  }
   284	  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
   285	  // promote() is NOT uniform across backends here: local rename overwrites, but SupabaseBlobStore
   286	  // .promote() is create-if-absent (it idempotently SKIPS the move when the final already exists,
   287	  // to tolerate concurrent same-key promoters) — so on the cloud winner-copy path the loser's stale
   288	  // body would survive. Commit the VERIFIED staged bytes to the final key with an atomic upsert
   289	  // (BlobStore.put, overwrite on both backends), THEN drop the staging temp. Durable-before-finalize
   290	  // is preserved: put returns only once the winner body is the live object, and updateVideoFields
   291	  // (below) advertises promoted only after this resolves.
   292	  await loser.blob.put(loser.p, key, staged, 'text/markdown');
   293	  await loser.blob.delete(loser.p, ref.tempKey).catch(() => { /* best-effort temp cleanup */ });
   294	
   295	  const wv: any = winnerVideo;
   296	  const completeTuple: any = {
   297	    summaryMd: key,
   298	    docVersion: wv.docVersion,
   299	    mdGeneratedAt: wv.mdGeneratedAt ?? null,
   300	    mdCorrectionsHash: wv.mdCorrectionsHash ?? null,
   301	    ratings: wv.ratings,
   302	    overallScore: wv.overallScore,
   303	    videoType: wv.videoType,
   304	    audience: wv.audience,
   305	    tags: wv.tags,
   306	    tldr: wv.tldr,
   307	    takeaways: wv.takeaways,
   308	    // WB-H2 — invalidate the loser's stale regenerable cache. Overwriting the loser's MD body without
   309	    // clearing these leaves summaryHtml/digDeeper* pointing at HTML rendered from the PRE-SYNC body;
   310	    // the serve path (buildDocHtml/ensureHtmlDoc) checks generator-version, NOT MD-body freshness, so a
   311	    // same-format prose change (the recency-tiebreak case) would serve stale HTML indefinitely (§5.1
   312	    // "sync moves MD, not HTML"). merge_video_data stores JSON null / local shallow-merge overrides →
   313	    // readIndex reads falsy → forces re-render. Matches sanitizeAdditiveVideo, which already nulls these.
   314	    summaryHtml: null,
   315	    digDeeperHtml: null,
   316	    digDeeperMd: null,
   317	    // Deep-merged (cloud merge_video_data / local index write). No Class-B key here → no spurious
   318	    // annotationsEditedAt stamp (F2). Never advertise promoted before the blob is durable (above).
   319	    artifacts: { summaryMd: { key, status: 'promoted' } },
   320	  };
   321	  await loser.store.updateVideoFields(loser.p, videoId, completeTuple as Partial<Video>);
   322	
   323	  return { mdHash: h, verified: true };
   324	}
   325	
   326	/** Behavior #5 — ship the winner's summary MODEL to the loser iff it was generated from the winning
   327	 *  MD; otherwise delete the loser's stale model (best-effort, OUTSIDE the atomic commit) and flag
   328	 *  that the owner must re-serve to regenerate the share model. */
   329	async function companionTransfer(
   330	  winner: Side, loser: Side, winnerMdHash: string, winnerVideo: Video,
   331	): Promise<{ shareNeedsOwnerServe: boolean }> {
   332	  if (!winnerVideo.summaryMd) return { shareNeedsOwnerServe: false };
   333	  const base = winnerVideo.summaryMd.replace(/\.md$/, '');
   334	  const senderEnvelope = await readModelEnvelope(winner.p, base, winner.blob);
   335	  const decision = decideCompanion({ winnerMdHash, senderEnvelope });
   336	  if (decision.kind === 'ship') {
   337	    await writeModelEnvelope(loser.p, base, decision.envelope, loser.blob);
   338	    return { shareNeedsOwnerServe: false };
   339	  }
   340	  // deleteReceiverModel — best-effort; a missing model blob is not an error.
   341	  try { await loser.blob.delete(loser.p, `models/${base}.json`); } catch { /* best-effort */ }
   342	  return { shareNeedsOwnerServe: true };
   343	}
   344	
   345	/** The manifest baseline written AFTER a verified reconcile — the AGREED post-reconcile state, not a
   346	 *  winner. Class A = the winning signals + verified mdHash (or the shared state on skip). Class B —
   347	 *  per field: advance to the resolved (value, editedAt) EXCEPT a no-write conflict
   348	 *  (winner==='equal' && conflict), which carries the PREVIOUS baseline unchanged (round-3 H2:
   349	 *  recording the winner there would be a false agreement → next-run silent overwrite). */
   350	function buildClassBBaseline(
   351	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   352	): VideoBaseline['classB'] {
   353	  const classB = {} as VideoBaseline['classB'];
   354	  for (const f of FIELDS) {
   355	    const m = merges[f];
   356	    if (m.winner === 'equal' && m.conflict) {
   357	      classB[f] = previousBaseline?.classB?.[f] ?? { value: undefined, editedAt: undefined };
   358	    } else {
   359	      classB[f] = { value: m.value, editedAt: m.editedAt };
   360	    }
   361	  }
   362	  return classB;
   363	}
   364	
   365	function buildBaseline(
   366	  winnerSignals: ClassASignals, winnerMdHash: string | null,
   367	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   368	): VideoBaseline {
   369	  return {
   370	    classA: {
   371	      docVersionMajor: winnerSignals.docVersionMajor,
   372	      mdGeneratedAt: winnerSignals.mdGeneratedAt,
   373	      mdCorrectionsHash: winnerSignals.mdCorrectionsHash,
   374	      mdHash: winnerMdHash,
   375	    },
   376	    classB: buildClassBBaseline(merges, previousBaseline),
   377	  };
   378	}
   379	
   380	/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
   381	 *  Class A must NOT advance to a winner (that would record a false agreement → next-run silent
   382	 *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
   383	 *  re-evaluates the currency-based transfer from the live signals. On a first sync (no previous
   384	 *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
   385	 *  is write-only (never read by reconcileClassA), so next run re-derives from the actual bodies
   386	 *  regardless. Class B carries the preserved conflict (buildClassBBaseline). */
   387	function buildCorrectionsUnresolvedBaseline(
   388	  merges: Record<HumanField, FieldMerge>, previousBaseline: VideoBaseline | undefined,
   389	): VideoBaseline {
   390	  return {
   391	    classA: previousBaseline?.classA
   392	      ?? { docVersionMajor: 0, mdGeneratedAt: null, mdCorrectionsHash: null, mdHash: null },
   393	    classB: buildClassBBaseline(merges, previousBaseline),
   394	  };
   395	}
   396	
   397	export async function runSync(
   398	  deps: SyncDeps, opts: { playlistKey?: string } = {},
   399	): Promise<SyncReport> {
   400	  resetConflictDedup();
   401	  const report: SyncReport = {
   402	    created: 0, updatedLocal: 0, updatedCloud: 0, skippedIdentical: 0,
   403	    mergedFields: 0, conflictsLogged: 0, removed: 0,
   404	    shareNeedsOwnerServe: 0, needsRegen: 0, archivedNotSynced: 0, errors: [],
   405	  };
   406	
   407	  const localPlaylists = await discoverLocalPlaylists(deps.dataRoots);
   408	  const cloudSummaries = await deps.cloud.listPlaylists(deps.ownerId);
   409	  const cloudKeys = cloudSummaries.map((p) => p.playlistKey);
   410	  let keys = unionPlaylistKeys(localPlaylists, cloudKeys);
   411	  if (opts.playlistKey) keys = keys.filter((k) => k === opts.playlistKey);
   412	
   413	  for (const key of keys) {
   414	    const dataRoot = localPlaylists.find((l) => l.playlistKey === key)?.dataRoot
   415	      ?? hydrationRoot(deps.dataRoots, key);
   416	    await ensureHydrationRoot(dataRoot); // mkdir -p BEFORE any local read/write (fresh-device hydrate)
   417	
   418	    const localP = localPrincipal(dataRoot);
   419	    const cloudP: Principal = { id: deps.ownerId, indexKey: key }; // F1 — auth.uid(), NOT 'cloud'
   420	    const localSide: Side = { store: deps.local, p: localP, blob: deps.localBlob };
   421	    const cloudSide: Side = { store: deps.cloud, p: cloudP, blob: deps.cloudBlob };
   422	    const playlistMeta = playlistMetaFor(key, localPlaylists, cloudSummaries);
   423	    const manifest = await readManifest(dataRoot, key);
   424	
   425	    for (const id of await enumerateVideoIds(deps.local, deps.cloud, localP, cloudP)) {
   426	      try {
   427	        const lv = await readVideo(deps.local, localP, id);
   428	        const cv = await readVideo(deps.cloud, cloudP, id);
   429	        const base = manifest.videos[id];
   430	
   431	        // ── Presence / deletes (§5.6, Behaviors #3/#7/#8) — resolve one-sided videos and CONTINUE
   432	        //    before any two-sided reconcile (deriveHumanSnapshot(null) would NPE).
   433	        if (!lv || !cv) {
   434	          const present = (lv ?? cv)!;
   435	          const presentIsLocal = lv != null;
   436	          if (base) {
   437	            report.removed += 1; // in baseline + absent other side → deleted there; no propagation (M2b)
   438	          } else {
   439	            const from: Side = presentIsLocal ? localSide : cloudSide;
   440	            const to: Side = presentIsLocal ? cloudSide : localSide;
   441	            const body = await readMdBody(from.blob, from.p, present);
   442	            await copyAdditiveVideo(to.store, to.p, to.blob, playlistMeta, present, body);
   443	            report.created += 1; // reached only after the receiver row is confirmed
   444	            await writeVideoBaseline(dataRoot, key, id, baselineFromOneSided(
   445	              deriveClassASignals(present, body), body ? mdHash(body) : null,
   446	              deriveHumanSnapshot(present),
   447	            ));
   448	          }
   449	          continue;
   450	        }
   451	
   452	        // ── Both present — reconcile. Class B FIRST (produces the reconciled corrections).
   453	        const localSnap = deriveHumanSnapshot(lv);
   454	        const cloudSnap = deriveHumanSnapshot(cv);
   455	        const merges = reconcileHuman(localSnap, cloudSnap, base?.classB ?? EMPTY_CLASSB);
   456	        const applied = await applyClassBWinners({
   457	          deps, localP, cloudP, videoId: id, merges, localSnap, cloudSnap, dataRoot, key,
   458	        });
   459	        report.mergedFields += applied.merged;
   460	        report.conflictsLogged += applied.conflicts;
   461	        const reconciledCorrectionsHash = mdHash(String(merges.corrections.value ?? ''));
   462	
   463	        // ── WB-B1 — corrections is an UNRESOLVED no-write conflict (both sides changed, ≥1 backfilled →
   464	        //    Class B logs+skips, §5.5). Its value is NOT a settled winner, so it must NOT drive a
   465	        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
   466	        //    and copy its MD body over the loser's (different-correction) body — DESTROYING the loser's
   467	        //    corrected MD and recording a false agreement (sticky: the copied bodies then match forever).
   468	        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance
   469	        //    Class A (so the next run re-evaluates once the human resolves corrections). The video stays
   470	        //    "seen" for delete-inference (baseline present).
   471	        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
   472	        if (correctionsUnresolved) {
   473	          report.needsRegen += 1;
   474	          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   475	          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
   476	          continue;
   477	        }
   478	
   479	        // ── Class A (needs the MD bodies for hashing — Behavior #1).
   480	        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
   481	        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));
   482	        const decision = reconcileClassA({ local: la, cloud: ca, reconciledCorrectionsHash });
   483	        if (decision.needsRegen) report.needsRegen += 1;
   484	
   485	        let winnerMdHash: string | null = null;
   486	        let winnerSignals: ClassASignals = la;
   487	        let winnerSide: Side | null = null;
   488	        let loserSide: Side | null = null;
   489	        let winnerVideo: Video = lv;
   490	
   491	        if (decision.action === 'copyToCloud') {
   492	          winnerSide = localSide; loserSide = cloudSide; winnerVideo = lv; winnerSignals = la;
   493	          winnerMdHash = (await transferClassA(localSide, cloudSide, lv, id)).mdHash;
   494	          report.updatedCloud += 1;
   495	        } else if (decision.action === 'copyToLocal') {
   496	          winnerSide = cloudSide; loserSide = localSide; winnerVideo = cv; winnerSignals = ca;
   497	          winnerMdHash = (await transferClassA(cloudSide, localSide, cv, id)).mdHash;
   498	          report.updatedLocal += 1;
   499	        } else {
   500	          report.skippedIdentical += 1;
   501	          winnerMdHash = la.mdHash; winnerSignals = la; // skip: sides already agree
   502	        }
   503	
   504	        if (decision.action !== 'skip' && winnerMdHash && winnerSide && loserSide) {
   505	          const c = await companionTransfer(winnerSide, loserSide, winnerMdHash, winnerVideo);
   506	          if (c.shareNeedsOwnerServe) report.shareNeedsOwnerServe += 1;
   507	        }
   508	        if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
   509	
   510	        // ── Manifest AFTER the verified commit (Behavior #10); advance even on skip (N4). Pass the
   511	        //    PREVIOUS baseline so a no-write Class-B conflict is NOT falsely advanced (round-3 H2).
   512	        await writeVideoBaseline(dataRoot, key, id, buildBaseline(winnerSignals, winnerMdHash, merges, base));
   513	      } catch (e: any) {
   514	        report.errors.push({ videoId: id, message: e?.message ?? String(e) }); // Behaviors #11/#13
   515	      }
   516	    }
   517	  }
   518	
   519	  return report;
   520	}

exec
/bin/bash -lc "nl -ba supabase/migrations/0021_cloud_sync_signals.sql | sed -n '1,180p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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
/bin/bash -lc "nl -ba lib/storage/supabase/supabase-metadata-store.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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

exec
/bin/bash -lc "nl -ba supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql | sed -n '90,170p' && nl -ba supabase/migrations/0007_storage_and_rpcs.sql | sed -n '70,130p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    90	    raise exception 'reserve_video_slot: existing video %/% has no serialNumber (invariant)', p_playlist_id, p_video_id;
    91	  end if;
    92	  select coalesce(max(v.position) + 1, 0), coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    93	    into v_pos, v_serial from videos v where v.playlist_id = p_playlist_id;
    94	  insert into videos (playlist_id, owner_id, video_id, position, data)
    95	    values (p_playlist_id, p_owner_id, p_video_id, v_pos, jsonb_build_object('id', p_video_id, 'serialNumber', v_serial))
    96	    on conflict (playlist_id, video_id) do nothing;
    97	  select (v.data->>'serialNumber')::int into v_serial
    98	    from videos v where v.playlist_id = p_playlist_id and v.video_id = p_video_id;
    99	  return v_serial;
   100	end $$;
   101	revoke all on function reserve_video_slot(uuid,uuid,text) from public;
   102	grant execute on function reserve_video_slot(uuid,uuid,text) to authenticated, service_role;
   103	
   104	create function persist_summary(p_owner_id uuid, p_playlist_id uuid, p_video_id text, p_video jsonb, p_artifact_status text)
   105	  returns void language plpgsql security invoker set search_path = public as $$
   106	declare v_count int;
   107	begin
   108	  if not (p_owner_id = auth.uid() or auth.role() = 'service_role') then raise exception 'not authorized'; end if;
   109	  perform 1 from playlists where id = p_playlist_id and owner_id = p_owner_id;
   110	  if not found then raise exception 'playlist % not owned by %', p_playlist_id, p_owner_id; end if;
   111	  -- Whitelist: a summary persist writes ONLY summary-owned fields and preserves EVERYTHING else.
   112	  -- Layering (right wins): (1) p_video defaults — used only for keys the existing row lacks, i.e. a
   113	  -- first-time write off a bare reserve row; (2) the existing row's NON-summary fields win back over
   114	  -- those defaults, so a possibly-stale job payload can never revert operational/membership/metadata/
   115	  -- other-feature state (archived, removedFromPlaylist, playlistIndex, title, timestamps, dig
   116	  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
   117	  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
   118	  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
   119	  -- monotonic status. The UPDATE's row lock serializes concurrent persists (Task-2 lost-update fix).
   120	  update videos v set
   121	    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
   122	      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
   123	                                                              --     state AND never drop existing summary fields on a
   124	                                                              --     status-only persist (p_video omits them)
   125	      || jsonb_strip_nulls(jsonb_build_object(                -- (3) re-apply ONLY the summary-owned fields p_video PROVIDES
   126	           'language', p_video->'language',                   --     (present ones win; absent → existing preserved by (2))
   127	           'ratings', p_video->'ratings',
   128	           'overallScore', p_video->'overallScore',
   129	           'processedAt', p_video->'processedAt',
   130	           'videoType', p_video->'videoType',
   131	           'audience', p_video->'audience',
   132	           'tags', p_video->'tags',
   133	           'tldr', p_video->'tldr',
   134	           'takeaways', p_video->'takeaways',
   135	           'docVersion', p_video->'docVersion'))
   136	      || jsonb_strip_nulls(jsonb_build_object('summaryMd', coalesce(p_video->>'summaryMd', v.data->>'summaryMd')))
   137	      || jsonb_build_object('artifacts',
   138	           coalesce(v.data->'artifacts', '{}'::jsonb)
   139	           || jsonb_build_object('summaryMd', jsonb_build_object(
   140	                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
   141	                -- Monotonic status, KEY-SCOPED: preserve 'promoted' against a stale 'committed' write
   142	                -- ONLY when the artifact key is unchanged. A different key is a genuinely new artifact
   143	                -- that IS in committed state, so it must be allowed through (else the row would claim a
   144	                -- promoted artifact for a blob that has not been promoted yet).
   145	                'status', case
   146	                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
   147	                                 and p_artifact_status = 'committed'
   148	                                 and v.data->'artifacts'->'summaryMd'->>'key'
   149	                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
   150	                              then 'promoted'
   151	                            else p_artifact_status end))),
   152	    updated_at = now()
   153	   where v.playlist_id = p_playlist_id and v.video_id = p_video_id and v.owner_id = p_owner_id;
   154	  get diagnostics v_count = row_count;
   155	  if v_count = 0 then raise exception 'persist_summary: no video row for %/%', p_playlist_id, p_video_id; end if;
   156	end $$;
   157	revoke all on function persist_summary(uuid,uuid,text,jsonb,text) from public;
   158	grant execute on function persist_summary(uuid,uuid,text,jsonb,text) to authenticated, service_role;
    70	      and (video_id = any(p_present))
    71	      and coalesce((data->>'removedFromPlaylist')::boolean, false) = true;
    72	end $$;
    73	revoke all on function reconcile_membership(uuid, text[]) from public;
    74	grant execute on function reconcile_membership(uuid, text[]) to authenticated, service_role;
    75	
    76	-- merge_video_data: owner-guarded jsonb field merge. ARTIFACTS-AWARE (F6): the top-level
    77	-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
    78	-- sibling kinds); every other key is a plain shallow merge. Write-once fields (videoPublishedAt/
    79	-- addedToPlaylistAt) are preserved by the caller passing the already-`??`-guarded value (F2b);
    80	-- the accompanying integration test (Task 11) proves re-sync does not overwrite them.
    81	create function merge_video_data(p_playlist_id uuid, p_video_id text, p_fields jsonb)
    82	  returns void language plpgsql security invoker set search_path = public as $$
    83	begin
    84	  perform 1 from playlists
    85	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
    86	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    87	
    88	  update videos set
    89	    data = (data || (p_fields - 'artifacts'))
    90	      || case when p_fields ? 'artifacts'
    91	           then jsonb_build_object('artifacts',
    92	                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
    93	           else '{}'::jsonb end,
    94	    updated_at = now()
    95	   where playlist_id = p_playlist_id and video_id = p_video_id;
    96	end $$;
    97	revoke all on function merge_video_data(uuid, text, jsonb) from public;
    98	grant execute on function merge_video_data(uuid, text, jsonb) to authenticated, service_role;
    99	
   100	-- merge_video_data_bulk: apply merge_video_data semantics to many videos in ONE transaction.
   101	-- p_patches = jsonb array of { "video_id": text, "fields": jsonb }.
   102	create function merge_video_data_bulk(p_playlist_id uuid, p_patches jsonb)
   103	  returns void language plpgsql security invoker set search_path = public as $$
   104	declare it jsonb;
   105	begin
   106	  perform 1 from playlists
   107	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role');
   108	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
   109	
   110	  for it in select * from jsonb_array_elements(p_patches) loop
   111	    update videos set
   112	      data = (data || ((it->'fields') - 'artifacts'))
   113	        || case when (it->'fields') ? 'artifacts'
   114	             then jsonb_build_object('artifacts',
   115	                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
   116	             else '{}'::jsonb end,
   117	      updated_at = now()
   118	     where playlist_id = p_playlist_id and video_id = it->>'video_id';
   119	  end loop;
   120	end $$;
   121	revoke all on function merge_video_data_bulk(uuid, jsonb) from public;
   122	grant execute on function merge_video_data_bulk(uuid, jsonb) to authenticated, service_role;

exec
/bin/bash -lc "nl -ba lib/index-store.ts | sed -n '1,120p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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
/bin/bash -lc 'rg -n "buildCorrectionsUnresolvedBaseline|correctionsUnresolved|additive: summaryMd present|did not advertise promoted|summaryHtml: null|digDeeperMd: null|digDeeperHtml: null|archivedNotSynced|needsRegen" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/e2e.int.test.ts:129:  // ── Row 3 — neither side corrections-current (identical stale bodies) → needsRegen counted, MD kept.
tests/integration/cloud-sync/e2e.int.test.ts:130:  it('row 3: identical stale MDs on both sides → needsRegen counted, MD unchanged', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:139:    expect(report.needsRegen).toBeGreaterThanOrEqual(1);
tests/integration/cloud-sync/e2e.int.test.ts:392:  //    After the fix: no copy, needsRegen flagged, both corrections + both bodies preserved, twice.
tests/integration/cloud-sync/e2e.int.test.ts:411:    expect(r1.needsRegen).toBeGreaterThanOrEqual(1);
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
tests/integration/cloud-sync/stamping.int.test.ts:84:      p_playlist_id: playlistId, p_video_id: videoId, p_fields: { summaryHtml: null },
tests/lib/cloud-sync/local-stamping.test.ts:78:    await localMetadataStore.updateVideoFields(p, 'a', { summaryHtml: null });
tests/lib/cloud-sync/model-writer-hash.test.ts:57:    summaryHtml: null, processedAt: '2026-06-09T00:00:00.000Z',

codex
The backend trace is favorable for WB-H2 so far: `merge_video_data` uses `data || p_fields`, which preserves JSON nulls, and the local path writes `null` through the JSON index. I’m now looking for behavior holes around additive failures and baseline advancement rather than just matching comments.
exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '360,455p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
   438	  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
   439	    const ctx = await makeOwnerContext();
   440	    // summaryMd key set + artifacts.summaryMd promoted, but NO mdBody → seedSummaryBlob is skipped.
   441	    await seedCloudVideo(ctx, { /* mdBody omitted → blob absent */ });
   442	
   443	    const report = await runSync(ctx.syncDeps());
   444	
   445	    expect(report.errors.some((e) => e.videoId === ctx.videoId)).toBe(true);
   446	    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).
   447	    const local = await localVideoRecord(ctx);
   448	    expect(artifactsOf(local)?.summaryMd?.status).not.toBe('promoted');
   449	    // Baseline not advanced — the throw aborted before writeVideoBaseline.
   450	    expect((await ctx.readManifest()).videos[ctx.videoId]).toBeUndefined();
   451	  });
   452	
   453	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
   454	  //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
   455	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.

exec
/bin/bash -lc "nl -ba lib/index-store.ts | sed -n '116,190p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
/bin/bash -lc 'rg -n "summaryMd present but MD body unreadable|did not advertise promoted|stale HTML|digDeeperHtml|summary-less|summaryMd == null|bare receiver|slot|promoted summaryMd" tests/lib/cloud-sync tests/integration/cloud-sync' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/e2e.int.test.ts:274:      digDeeperHtml: '<html>dig</html>',
tests/integration/cloud-sync/e2e.int.test.ts:281:    expect(local?.digDeeperHtml == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:308:  // ── Row 13 — additive create of a summary-less video: metadata copied, no blob put, no throw.
tests/integration/cloud-sync/e2e.int.test.ts:309:  it('row 13: additive create of a summary-less video copies metadata with no blob write', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:318:    expect(local?.summaryMd == null).toBe(true);
tests/integration/cloud-sync/e2e.int.test.ts:438:  it('WB-H1: additive create with a promoted summaryMd but no blob throws; no promoted row, no baseline', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:446:    // The local receiver must not advertise a promoted summaryMd (bare slot at most; no blob copied).

exec
/bin/bash -lc 'rg -n "claim_video_slot|create function claim_video_slot|upsertVideo|artifacts" supabase/migrations tests/lib/storage/supabase-metadata-store.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/lib/storage/supabase-metadata-store.test.ts:243:  test('calls claim_video_slot RPC with playlist_id and video_id, returns position+serialNumber', async () => {
tests/lib/storage/supabase-metadata-store.test.ts:246:      rpcResults: { claim_video_slot: [{ position: 2, serial_number: 3 }] },
tests/lib/storage/supabase-metadata-store.test.ts:251:    const rpc = client.rpcCalls.find((c) => c.name === 'claim_video_slot');
tests/lib/storage/supabase-metadata-store.test.ts:265:// upsertVideo
tests/lib/storage/supabase-metadata-store.test.ts:267:describe('upsertVideo', () => {
tests/lib/storage/supabase-metadata-store.test.ts:274:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:291:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:307:    await store.upsertVideo(p, video);
tests/lib/storage/supabase-metadata-store.test.ts:534:      errors: { 'rpc.claim_video_slot': 'rpc failed' },
supabase/migrations/0012_serve_model_charge.sql:44:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:116:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:117:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:118:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:121:    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:122:      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:137:      || jsonb_build_object('artifacts',
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:138:           coalesce(v.data->'artifacts', '{}'::jsonb)
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:140:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:146:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:148:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0009_job_playlist_identity_and_worker_persistence.sql:149:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
supabase/migrations/0015_video_updated_at_trigger.sql:3:-- Closes the gap where SupabaseMetadataStore.upsertVideo() does a direct
supabase/migrations/0017_share_token_id_return.sql:23:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0020_reservation_release.sql:204:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0021_cloud_sync_signals.sql:80:    data = (data || (p_fields - 'artifacts'))
supabase/migrations/0021_cloud_sync_signals.sql:81:      || case when p_fields ? 'artifacts'
supabase/migrations/0021_cloud_sync_signals.sql:82:           then jsonb_build_object('artifacts',
supabase/migrations/0021_cloud_sync_signals.sql:83:                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
supabase/migrations/0021_cloud_sync_signals.sql:111:  -- artifacts, personal notes, …) that a concurrent writer (reconcile_membership / merge_video_data /
supabase/migrations/0021_cloud_sync_signals.sql:112:  -- upsertVideo) may have changed while this job ran; (3) the top-level summaryMd key resolved from
supabase/migrations/0021_cloud_sync_signals.sql:113:  -- payload-or-existing; (4) the artifacts.summaryMd merge with a lock-consistent, KEY-SCOPED
supabase/migrations/0021_cloud_sync_signals.sql:116:    data = (p_video - 'artifacts')                            -- (1) payload defaults — fill keys a first-time bare row lacks
supabase/migrations/0021_cloud_sync_signals.sql:117:      || (v.data - 'artifacts')                               -- (2) ALL existing fields win back: never clobber non-summary
supabase/migrations/0021_cloud_sync_signals.sql:134:      || jsonb_build_object('artifacts',
supabase/migrations/0021_cloud_sync_signals.sql:135:           coalesce(v.data->'artifacts', '{}'::jsonb)
supabase/migrations/0021_cloud_sync_signals.sql:137:                'key', coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key'),
supabase/migrations/0021_cloud_sync_signals.sql:143:                            when v.data->'artifacts'->'summaryMd'->>'status' = 'promoted'
supabase/migrations/0021_cloud_sync_signals.sql:145:                                 and v.data->'artifacts'->'summaryMd'->>'key'
supabase/migrations/0021_cloud_sync_signals.sql:146:                                     = coalesce(p_video->>'summaryMd', v.data->'artifacts'->'summaryMd'->>'key')
supabase/migrations/0007_storage_and_rpcs.sql:3:-- Private bucket for all artifacts.
supabase/migrations/0007_storage_and_rpcs.sql:4:insert into storage.buckets (id, name, public) values ('artifacts', 'artifacts', false)
supabase/migrations/0007_storage_and_rpcs.sql:12:create policy "artifacts_owner_rw" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:14:  using (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text)
supabase/migrations/0007_storage_and_rpcs.sql:15:  with check (bucket_id = 'artifacts' and split_part(name, '/', 1) = auth.uid()::text);
supabase/migrations/0007_storage_and_rpcs.sql:16:create policy "artifacts_service_all" on storage.objects
supabase/migrations/0007_storage_and_rpcs.sql:17:  for all to service_role using (bucket_id = 'artifacts') with check (bucket_id = 'artifacts');
supabase/migrations/0007_storage_and_rpcs.sql:19:-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
supabase/migrations/0007_storage_and_rpcs.sql:20:create function claim_video_slot(p_playlist_id uuid, p_video_id text)
supabase/migrations/0007_storage_and_rpcs.sql:43:revoke all on function claim_video_slot(uuid, text) from public;
supabase/migrations/0007_storage_and_rpcs.sql:44:grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;
supabase/migrations/0007_storage_and_rpcs.sql:77:-- `artifacts` object is deep-merged one level (so writing one artifact kind never clobbers
supabase/migrations/0007_storage_and_rpcs.sql:89:    data = (data || (p_fields - 'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:90:      || case when p_fields ? 'artifacts'
supabase/migrations/0007_storage_and_rpcs.sql:91:           then jsonb_build_object('artifacts',
supabase/migrations/0007_storage_and_rpcs.sql:92:                  coalesce(data->'artifacts', '{}'::jsonb) || (p_fields->'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:112:      data = (data || ((it->'fields') - 'artifacts'))
supabase/migrations/0007_storage_and_rpcs.sql:113:        || case when (it->'fields') ? 'artifacts'
supabase/migrations/0007_storage_and_rpcs.sql:114:             then jsonb_build_object('artifacts',
supabase/migrations/0007_storage_and_rpcs.sql:115:                    coalesce(data->'artifacts', '{}'::jsonb) || ((it->'fields')->'artifacts'))
supabase/migrations/0014_serve_owner_budget.sql:38:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'
supabase/migrations/0013_share_tokens.sql:36:  select (v.data->'artifacts'->'summaryMd'->>'status') = 'promoted'

codex
One concrete regression candidate has emerged: `copyAdditiveVideo` still creates the receiver slot before it knows the source MD blob is readable. I’m checking whether that partial slot is self-healing or whether it changes the next run’s branch classification.
exec
/bin/bash -lc "nl -ba lib/cloud-sync/backfill.ts | sed -n '1,220p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
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
/bin/bash -lc "nl -ba supabase/migrations/0007_storage_and_rpcs.sql | sed -n '19,45p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
    19	-- claim_video_slot: append a reservation row under a playlist row-lock; returns position + serial.
    20	create function claim_video_slot(p_playlist_id uuid, p_video_id text)
    21	  returns table("position" int, serial_number int)
    22	  language plpgsql security invoker set search_path = public as $$
    23	declare v_pos int; v_serial int;
    24	begin
    25	  perform 1 from playlists
    26	    where id = p_playlist_id and (owner_id = auth.uid() or auth.role() = 'service_role')
    27	    for update;
    28	  if not found then raise exception 'not authorized for playlist %', p_playlist_id; end if;
    29	
    30	  select coalesce(max(v.position) + 1, 0),
    31	         coalesce(max((v.data->>'serialNumber')::int) + 1, 1)
    32	    into v_pos, v_serial
    33	    from videos v where v.playlist_id = p_playlist_id;
    34	
    35	  insert into videos (playlist_id, owner_id, video_id, position, data)
    36	    select p_playlist_id, pl.owner_id, p_video_id, v_pos,
    37	           jsonb_build_object('id', p_video_id, 'serialNumber', v_serial)
    38	      from playlists pl where pl.id = p_playlist_id
    39	    on conflict (playlist_id, video_id) do nothing;   -- idempotent claim
    40	
    41	  return query select v_pos, v_serial;
    42	end $$;
    43	revoke all on function claim_video_slot(uuid, text) from public;
    44	grant execute on function claim_video_slot(uuid, text) to authenticated, service_role;
    45	

exec
/bin/bash -lc "nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '250,335p' && nl -ba tests/integration/cloud-sync/e2e.int.test.ts | sed -n '453,510p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
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
   453	  // ── WB-H2 — a two-sided transfer must invalidate the loser's stale rendered-HTML cache. copyToLocal
   454	  //    wins (cloud higher-major, both corrections-current) and overwrites local's MD body; local's
   455	  //    pre-existing summaryHtml (rendered from the OLD body) must be nulled so the serve path re-renders.
   456	  it('WB-H2: a copyToLocal transfer nulls the local loser stale summaryHtml and copies the winner body', async () => {
   457	    const ctx = await makeOwnerContext();
   458	    const bodyLocalOld = '# LocalOld\n\nlower-major stale-format body\n';
   459	    const bodyCloudWin = '# CloudWin\n\nhigher-major winner body\n';
   460	    await seedLocalVideoFull(ctx, {
   461	      mdBody: bodyLocalOld, docVersion: { major: 1, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   462	      summaryHtml: '<html>STALE rendered from the old local body</html>',
   463	    });
   464	    await seedCloudVideo(ctx, {
   465	      mdBody: bodyCloudWin, docVersion: { major: 2, minor: 0 }, mdCorrectionsHash: H_NO_CORRECTIONS,
   466	    });
   467	
   468	    const report = await runSync(ctx.syncDeps());
   469	    expect(report.updatedLocal).toBeGreaterThanOrEqual(1);
   470	
   471	    const local = await localVideoRecord(ctx);
   472	    expect(local?.summaryHtml == null).toBe(true);                                  // stale cache invalidated
   473	    expect((await localBlobBytes(ctx, key(ctx)))!.toString('utf8')).toBe(bodyCloudWin); // winner body copied
   474	  });
   475	});

exec
/bin/bash -lc 'rg -n "summaryPdf|deepDive|modelJson|pdf|slide|artifacts" types lib/cloud-sync docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md | head -120' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:27:- **M2b — later slice (own spec):** deep-dive/dig **+ slide images** via the cloud-tokens → local-capture →
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:35:**Out of scope (M2a):** deep-dive/dig + slide images (M2b, §13); tombstone delete propagation; background
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:379:## 13. M2b forward-notes (deep-dive + slide images) — captured, not in scope
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:390:- **Local resolves tokens → pixels** (`lib/dig/slides.ts`: `yt-dlp --download-sections` + `ffmpeg`, anchored
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:392:- **The M2b pipeline** is therefore: **cloud generates dig text + slide tokens → sync to local → local
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:393:  resolves tokens into real slides → sync the images back to cloud.** Cloud ends up with pixels it could
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:396:  `DIG_GENERATOR_VERSION` axis); the resolved **slide images** are a **local-authoritative asset layer**
types/index.ts:82:  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
lib/cloud-sync/sync-run.ts:104: *  advertises artifacts whose blobs were not copied. Clears summaryHtml/digDeeperHtml/digDeeperMd,
lib/cloud-sync/sync-run.ts:105: *  drops every artifacts.* except summaryMd, drops the sender's replica-local ordering. KEEPS
lib/cloud-sync/sync-run.ts:112:  // Keep ONLY artifacts.summaryMd (blob we actually copy); drop html/pdf/slide/modelJson pointers.
lib/cloud-sync/sync-run.ts:113:  if (v.artifacts && typeof v.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:114:    v.artifacts = v.artifacts.summaryMd ? { summaryMd: v.artifacts.summaryMd } : {};
lib/cloud-sync/sync-run.ts:177:    sanitized.artifacts = { summaryMd: { key: video.summaryMd, status: 'promoted' } };
lib/cloud-sync/sync-run.ts:178:  } else if (sanitized.artifacts && typeof sanitized.artifacts === 'object') {
lib/cloud-sync/sync-run.ts:182:    delete sanitized.artifacts.summaryMd;
lib/cloud-sync/sync-run.ts:195:  // silently-dropped artifacts field payload is caught BEFORE the caller advances the baseline.
lib/cloud-sync/sync-run.ts:197:    const art = (rec as any).artifacts?.summaryMd;
lib/cloud-sync/sync-run.ts:319:    artifacts: { summaryMd: { key, status: 'promoted' } },

codex
The partial-slot path is not just cosmetic: after the first failed additive copy, the next run no longer enters the additive branch because both indexes contain the video id. I’m going to run the focused sync tests to confirm shipped behavior, then I’ll finish the re-review with that scenario called out if it holds.
exec
/bin/bash -lc "rg -n \"jest|vitest|test\" package.json && sed -n '1,140p' package.json" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
9:    "test": "jest",
10:    "test:watch": "jest --watch",
11:    "test:e2e": "playwright test",
18:    "test:integration": "jest --config jest.integration.config.ts --runInBand",
39:    "@playwright/test": "^1.60.0",
41:    "@testing-library/dom": "^10.4.1",
42:    "@testing-library/jest-dom": "^6.9.1",
43:    "@testing-library/react": "^16.3.2",
44:    "@types/jest": "^30.0.0",
49:    "jest": "^30.4.2",
50:    "jest-environment-jsdom": "^30.4.1",
52:    "ts-jest": "^29.4.9",
{
  "name": "youtube-playlist-summaries",
  "version": "0.1.0",
  "private": true,
  "scripts": {
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
  },
  "dependencies": {
    "@google/generative-ai": "^0.24.1",
    "@supabase/ssr": "^0.12.0",
    "@supabase/supabase-js": "^2.109.0",
    "googleapis": "^171.4.0",
    "markdown-it": "^14.2.0",
    "next": "16.2.6",
    "playwright": "^1.60.0",
    "react": "19.2.4",
    "react-dom": "19.2.4",
    "server-only": "^0.0.1",
    "youtube-transcript": "^1.3.1",
    "zod": "^4.4.3"
  },
  "devDependencies": {
    "@playwright/test": "^1.60.0",
    "@tailwindcss/postcss": "^4",
    "@testing-library/dom": "^10.4.1",
    "@testing-library/jest-dom": "^6.9.1",
    "@testing-library/react": "^16.3.2",
    "@types/jest": "^30.0.0",
    "@types/markdown-it": "^14.1.2",
    "@types/node": "^20",
    "@types/react": "^19",
    "@types/react-dom": "^19",
    "jest": "^30.4.2",
    "jest-environment-jsdom": "^30.4.1",
    "tailwindcss": "^4",
    "ts-jest": "^29.4.9",
    "ts-node": "^10.9.2",
    "tsconfig-paths": "^4.2.0",
    "typescript": "^5"
  }
}

exec
/bin/bash -lc 'npm test -- --runTestsByPath tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/local-stamping.test.ts tests/integration/cloud-sync/stamping.int.test.ts tests/integration/cloud-sync/e2e.int.test.ts --runInBand' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 3948ms:

> youtube-playlist-summaries@0.1.0 test
> jest --runTestsByPath tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/local-stamping.test.ts tests/integration/cloud-sync/stamping.int.test.ts tests/integration/cloud-sync/e2e.int.test.ts --runInBand


Test Suites: 2 passed, 2 total
Tests:       17 passed, 17 total
Snapshots:   0 total
Time:        0.589 s, estimated 2 s
Ran all test suites within paths "tests/lib/cloud-sync/reconcile-class-a.test.ts", "tests/lib/cloud-sync/local-stamping.test.ts", "tests/integration/cloud-sync/stamping.int.test.ts", "tests/integration/cloud-sync/e2e.int.test.ts".

exec
/bin/bash -lc "nl -ba types/index.ts | sed -n '1,130p'" in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
     1	import { z } from 'zod';
     2	
     3	// --- Rating value: integer 1–5 ---
     4	export const RatingValueSchema = z.union([
     5	  z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5),
     6	]);
     7	export type RatingValue = z.infer<typeof RatingValueSchema>;
     8	
     9	// --- Ratings ---
    10	export const RatingsSchema = z.object({
    11	  usefulness: RatingValueSchema,
    12	  depth: RatingValueSchema,
    13	  originality: RatingValueSchema,
    14	  recency: RatingValueSchema,
    15	  completeness: RatingValueSchema,
    16	});
    17	export type Ratings = z.infer<typeof RatingsSchema>;
    18	
    19	// --- VideoType and Audience: Gemini-classified fields ---
    20	export const VideoTypeSchema = z.enum([
    21	  'Tutorial', 'Analysis', 'Case Study', 'Framework', 'Demo', 'Interview',
    22	]);
    23	export type VideoType = z.infer<typeof VideoTypeSchema>;
    24	
    25	export const AudienceSchema = z.enum(['Beginner', 'Intermediate', 'Advanced']);
    26	export type Audience = z.infer<typeof AudienceSchema>;
    27	
    28	// --- VideoMeta: intermediate shape from YouTube API, before ratings/summary exist ---
    29	export const VideoMetaSchema = z.object({
    30	  videoId: z.string(), // YouTube video ID (not the playlist item ID)
    31	  title: z.string(),
    32	  youtubeUrl: z.string().url(),
    33	  durationSeconds: z.number().int().nonnegative(),
    34	  channelTitle: z.string().optional(),
    35	  videoPublishedAt: z.string().datetime().optional(),
    36	  addedToPlaylistAt: z.string().datetime().optional(),
    37	  liveBroadcastContent: z.string().optional(),
    38	});
    39	export type VideoMeta = z.infer<typeof VideoMetaSchema>;
    40	
    41	export const DocVersionSchema = z.object({
    42	  major: z.number().int().nonnegative(),
    43	  minor: z.number().int().nonnegative(),
    44	});
    45	
    46	// --- Video: one entry in playlist-index.json ---
    47	export const VideoSchema = z.object({
    48	  id: z.string(),
    49	  title: z.string(),
    50	  youtubeUrl: z.string().url(),
    51	  language: z.enum(['en', 'ko']),
    52	  durationSeconds: z.number().int().nonnegative(),
    53	  archived: z.boolean(),
    54	  ratings: RatingsSchema,
    55	  overallScore: z.number().min(1).max(5), // average of 5 ratings, may be fractional
    56	  summaryMd: z.string().nullable(),
    57	  summaryHtml: z.string().nullable().optional(),
    58	  digDeeperMd: z.string().nullable().optional(),
    59	  digDeeperHtml: z.string().nullable().optional(),
    60	  processedAt: z.string().datetime(),
    61	  videoType: VideoTypeSchema.optional(),
    62	  audience: AudienceSchema.optional(),
    63	  channel: z.string().optional(),
    64	  tags: z.array(z.string()).optional(),
    65	  removedFromPlaylist: z.boolean().optional(),
    66	  playlistIndex: z.number().int().positive().optional(),
    67	  serialNumber: z.number().int().positive().optional(),
    68	  videoPublishedAt: z.string().datetime().optional(),
    69	  addedToPlaylistAt: z.string().datetime().optional(),
    70	  personalScore: z.number().int().min(1).max(5).optional(),
    71	  personalNote: z.string().max(500).optional(),
    72	  tldr: z.string().optional(),
    73	  takeaways: z.array(z.string()).optional(),
    74	  corrections: z.string().optional(),
    75	  docVersion: DocVersionSchema.optional(), // absent ⇒ pre-feature {1,0}; stamped to CURRENT_DOC_VERSION on (re)generation
    76	  // Cloud-only (Stage 2a Task 1): sourced from videos.updated_at (readIndex), never persisted
    77	  // in the local FS JSON, so it must stay optional for back-compat. `{ offset: true }` is
    78	  // required (not just `Z`) because PostgREST serializes timestamptz as e.g.
    79	  // "2026-07-11T01:12:57.796832+00:00" — an offset suffix, not "Z" — so the default
    80	  // Z-only datetime() would reject every real DB-sourced value.
    81	  updatedAt: z.string().datetime({ offset: true }).optional(),
    82	  // Stage 2c: cloud-only readiness flag, derived from artifacts.summaryMd.status === 'promoted'.
    83	  // Optional → the local path never sets it (same back-compat pattern as updatedAt). Gates the
    84	  // cloud View/Download/Share menu items; the serving route enforces the same predicate server-side.
    85	  summaryReady: z.boolean().optional(),
    86	  // Stage 3 Cloud Sync (§5.1): generated-MD signals — stamped on (re)generation.
    87	  mdGeneratedAt: z.string().datetime({ offset: true }).optional(),
    88	  mdCorrectionsHash: z.string().optional(),
    89	  // Per-field human-edit timestamps (§5.1). A clear stamps the timestamp while removing the value.
    90	  annotationsEditedAt: z
    91	    .object({
    92	      personalNote: z.string().datetime({ offset: true }).optional(),
    93	      personalScore: z.string().datetime({ offset: true }).optional(),
    94	      corrections: z.string().datetime({ offset: true }).optional(),
    95	    })
    96	    .optional(),
    97	});
    98	export type Video = z.infer<typeof VideoSchema>;
    99	
   100	// --- PlaylistIndex: root of playlist-index.json ---
   101	export const PlaylistIndexSchema = z.object({
   102	  playlistUrl: z.union([z.string().url(), z.literal('')]),   // '' = absent-index sentinel (empty read)
   103	  playlistTitle: z.string().optional(),
   104	  outputFolder: z.string(),
   105	  videos: z.array(VideoSchema),
   106	});
   107	export type PlaylistIndex = z.infer<typeof PlaylistIndexSchema>;
   108	
   109	// --- ProgressEvent: discriminated union for SSE events ---
   110	export const ProgressEventSchema = z.discriminatedUnion('type', [
   111	  z.object({
   112	    type: z.literal('start'),
   113	    total: z.number().int().nonnegative().optional(),
   114	    log: z.string().optional(),
   115	  }),
   116	  z.object({
   117	    type: z.literal('step'),
   118	    videoId: z.string().optional(),
   119	    title: z.string().optional(),
   120	    step: z.string(),
   121	    current: z.number().int().positive().optional(),
   122	    total: z.number().int().positive().optional(),
   123	  }),
   124	  z.object({
   125	    type: z.literal('done'),
   126	    current: z.number().int().positive().optional(),
   127	    total: z.number().int().nonnegative().optional(),
   128	    succeeded: z.number().int().nonnegative().optional(),
   129	    failed: z.number().int().nonnegative().optional(),
   130	    log: z.string().optional(), // optional terminal detail, e.g. the saved PDF filename

exec
/bin/bash -lc 'rg -n "ratings|overallScore|videoType|audience|tags|tldr|takeaways|complete tuple|companion scalars|Class-A" docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md lib/cloud-sync tests/integration/cloud-sync/e2e.int.test.ts' in /Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud
 succeeded in 0ms:
tests/integration/cloud-sync/e2e.int.test.ts:6:// here drive the TWO-SIDED Class-A COPY path (transferClassA + companionTransfer) with DIVERGENT
tests/integration/cloud-sync/e2e.int.test.ts:54:  // ── Row 1 — Class-A anti-recency: higher-major MD beats a NEWER-timestamp lower-major MD.
tests/integration/cloud-sync/e2e.int.test.ts:63:      mdCorrectionsHash: H_NO_CORRECTIONS, ratings: winnerRatings, overallScore: 3,
tests/integration/cloud-sync/e2e.int.test.ts:64:      tldr: 'the-tldr', takeaways: ['a', 'b'], tags: ['x', 'y'],
tests/integration/cloud-sync/e2e.int.test.ts:83:    // updateVideoFields finalize carried the winner's docVersion + companion scalars verbatim.
tests/integration/cloud-sync/e2e.int.test.ts:86:    expect(cloud?.ratings).toEqual(winnerRatings);
tests/integration/cloud-sync/e2e.int.test.ts:87:    expect(cloud?.overallScore).toBe(3);
tests/integration/cloud-sync/e2e.int.test.ts:88:    expect(cloud?.tldr).toBe('the-tldr');
tests/integration/cloud-sync/e2e.int.test.ts:89:    expect(cloud?.takeaways).toEqual(['a', 'b']);
tests/integration/cloud-sync/e2e.int.test.ts:90:    expect(cloud?.tags).toEqual(['x', 'y']);
tests/integration/cloud-sync/e2e.int.test.ts:107:      ratings: winnerRatings, tldr: 'keep-me', takeaways: ['k1'], tags: ['t1'],
tests/integration/cloud-sync/e2e.int.test.ts:125:    expect(local?.ratings).toEqual(winnerRatings);
tests/integration/cloud-sync/e2e.int.test.ts:126:    expect(local?.tldr).toBe('keep-me');
tests/integration/cloud-sync/e2e.int.test.ts:146:  // ── Row 4 — companion scalars carried VERBATIM (not reconstructed/flattened) on an additive hydrate.
tests/integration/cloud-sync/e2e.int.test.ts:147:  it('row 4: carries the 5 real ratings + tldr/takeaways/tags verbatim (not reconstructed)', async () => {
tests/integration/cloud-sync/e2e.int.test.ts:149:    const ratings = { usefulness: 5, depth: 2, originality: 4, recency: 1, completeness: 3 }; // NON-flat
tests/integration/cloud-sync/e2e.int.test.ts:151:      mdBody: '# S\n\nbody\n', ratings, overallScore: 3,
tests/integration/cloud-sync/e2e.int.test.ts:152:      tldr: 'the tldr', takeaways: ['t1', 't2'], tags: ['x', 'y'], docVersion: { major: 3, minor: 3 },
tests/integration/cloud-sync/e2e.int.test.ts:157:    expect(local?.ratings).toEqual(ratings);
tests/integration/cloud-sync/e2e.int.test.ts:158:    expect(local?.overallScore).toBe(3);
tests/integration/cloud-sync/e2e.int.test.ts:159:    expect(local?.tldr).toBe('the tldr');
tests/integration/cloud-sync/e2e.int.test.ts:160:    expect(local?.takeaways).toEqual(['t1', 't2']);
tests/integration/cloud-sync/e2e.int.test.ts:161:    expect(local?.tags).toEqual(['x', 'y']);
tests/integration/cloud-sync/e2e.int.test.ts:311:    await seedCloudVideo(ctx, { summaryMd: null, ratings: { usefulness: 3, depth: 3, originality: 3, recency: 3, completeness: 3 } });
tests/integration/cloud-sync/e2e.int.test.ts:388:  // ── WB-B1 — an UNRESOLVED corrections no-write conflict must NOT drive a destructive Class-A copy.
tests/integration/cloud-sync/e2e.int.test.ts:409:    expect(r1.updatedCloud).toBe(0);            // no Class-A copy in either direction
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:69:- **Class A-companion scalars — CARRIED with the winning MD (NOT re-derived — round-v8 B-1):** `ratings`
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:70:  (the 5 per-dimension values), `overallScore`, `videoType`, `audience`, `tags`, `tldr`, `takeaways`. These
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:73:  recover them (the MD frontmatter stores only the *average* `score`, so the 5 real `ratings` would be
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:74:  fabricated as flat copies; `tldr`/`takeaways`/`tags` live in the MD-body quick-ref callout it never parses;
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:80:  restored to full by a regen — residual R9). They are part of the atomic Class-A
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:105:- On a Class-A MD-transfer: ship the sender's model as a companion **iff** `sourceMdHash == mdHash(winning
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:161:**Every Class-A transfer carries the sender's companion scalars** (§4.1: `ratings`, `overallScore`,
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:162:`videoType`, `audience`, `tags`, `tldr`, `takeaways`) **verbatim with the winning MD** — a pure, uncharged
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:164:in the same atomic Class-A record (§7 step 4) so cards/sort/filter never drift. No data-loss: a losing MD is
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:188:propagates). A human field is **never** lost to a Class-A format change (they reconcile independently).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:194:timestamp **never drives a destructive overwrite**: a same-format Class-A tie with a backfilled
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:228:  the Class-A record write must carry the **companion scalars** (§4.1) so a synced MD lands with its own
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:229:  correct `ratings`/`tldr`/… (round-v8 B-1).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:255:   carried companion scalars** (§4.1) — so currency and cards/sort/filter never lag the MD (round-v8 M-2/L-1).
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:261:   **whole Class-A tuple** (`mdHash` + `mdCorrectionsHash` + `docVersion`), not `mdHash` alone, plus the
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:284:the Class-A tie baseline, and the Class-B 3-way-merge baseline. Lost/corrupt manifest degrades to a direct
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:307:  recent (both converge, no churn); **companion scalars (`ratings`/`tldr`/`tags`/…) are CARRIED verbatim with
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:308:  the winning MD, NOT re-derived** — assert the 5 real ratings + tldr/takeaways/tags land intact on the
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:335:- **R4 — Clock skew (now minor):** only a Class-A same-format tie-break and a Class-B same-field tie lean on
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:348:  (`reconstructVideo`, MD survived but the index was lost) carries flattened `ratings` + absent `tldr`/
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:349:  `takeaways`/`tags` — the best derivable from the MD alone. If such a record wins Class A, sync carries those
docs/superpowers/specs/2026-07-17-stage3-cloud-sync-design.md:369:   fetched, no author-edit path → replica-local). Companion scalars (`ratings`/`tldr`/`videoType`/…) are
lib/cloud-sync/types.ts:13:/** The companion scalars carried verbatim with a winning MD (§4.1). */
lib/cloud-sync/types.ts:16:  'ratings' | 'overallScore' | 'videoType' | 'audience' | 'tags' | 'tldr' | 'takeaways'
lib/cloud-sync/sync-run.ts:106: *  identity, Class-A scalars, summaryMd (the key), md signals, human fields + annotationsEditedAt. */
lib/cloud-sync/sync-run.ts:265:/** Behaviors #4/#10/#11 — the atomic Class-A transfer. stage the winner MD to the loser → verify it
lib/cloud-sync/sync-run.ts:267: *  carrying the complete tuple (summaryMd key + promoted artifact status + docVersion + md signals +
lib/cloud-sync/sync-run.ts:268: *  the 7 companion scalars). Throws on any fault so the caller does NOT advance the baseline. */
lib/cloud-sync/sync-run.ts:284:  // A two-sided Class-A transfer must OVERWRITE the loser's existing (divergent) blob at `key`.
lib/cloud-sync/sync-run.ts:301:    ratings: wv.ratings,
lib/cloud-sync/sync-run.ts:302:    overallScore: wv.overallScore,
lib/cloud-sync/sync-run.ts:303:    videoType: wv.videoType,
lib/cloud-sync/sync-run.ts:304:    audience: wv.audience,
lib/cloud-sync/sync-run.ts:305:    tags: wv.tags,
lib/cloud-sync/sync-run.ts:306:    tldr: wv.tldr,
lib/cloud-sync/sync-run.ts:307:    takeaways: wv.takeaways,
lib/cloud-sync/sync-run.ts:380:/** WB-B1 — the manifest baseline for a corrections NO-WRITE conflict (§5.5). No Class-A copy ran, so
lib/cloud-sync/sync-run.ts:382: *  overwrite around an unresolved conflict). Preserve the PREVIOUS Class-A baseline so the next run
lib/cloud-sync/sync-run.ts:384: *  baseline) record an HONEST unresolved placeholder (mdHash null → "no agreed MD"); Class-A baseline
lib/cloud-sync/sync-run.ts:465:        //    currency-based Class-A transfer: reconcileClassA would read one side as corrections-current
lib/cloud-sync/sync-run.ts:468:        //    Skip the Class-A copy entirely, flag for regen, and write a baseline that does NOT advance

codex
**Part A**

WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.

WB-H1: INCOMPLETE. The promoted-without-blob advertisement is fixed for the first failing run: unreadable `summaryMd` throws before `upsertVideo`, and the post-write promoted artifact assertion is valid for both local replacement and Supabase direct row update. However, the throw happens after `ensureReceiverSlot`, leaving a bare receiver row that changes the next run’s branch classification. Finding below.

WB-H2: GENUINELY FIXED. `transferClassA` writes `summaryHtml`, `digDeeperHtml`, and `digDeeperMd` as JSON/null fields in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:314). Supabase `merge_video_data` preserves those nulls via `data || (p_fields - 'artifacts')` in [0021_cloud_sync_signals.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79); local shallow merge also persists nulls through `updateVideoFields`. The null list matches `sanitizeAdditiveVideo`’s regenerable top-level cache fields, and clearing `digDeeperMd` is consistent with M2a not syncing dig/deep-dive assets.

**Findings**

High: partial additive failure creates a receiver slot, then a later run can falsely baseline a video whose source MD blob is still missing.  
File: [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:150)

Scenario: cloud-only video advertises `summaryMd`, but the MD blob is absent. Run 1 calls `ensureReceiverSlot` before the unreadable-body check, creating a bare local row, then throws at line 159 and does not write a baseline. Run 2 now sees both sides present, not an additive create. Since both MD body reads are null, `reconcileClassA` returns `skip`; `runSync` writes a manifest baseline at line 512 even though no receiver summary was ever durably copied and the source still advertises an unreadable summary. This masks the original corruption after one report and turns a failed additive copy into a false “seen/agreed no-MD” state.

Fix: validate `video.summaryMd`/`mdBody` before `ensureReceiverSlot`, or wrap `copyAdditiveVideo` in rollback that deletes the claimed receiver slot and any staged/final blob if any later step fails. The baseline should not be able to advance from a bare receiver slot created by a failed additive copy.

Medium: Class-A transfer does not clear absent companion scalars, so stale loser metadata can survive beside the winner MD.  
File: [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:301)

Scenario: winner MD comes from a reconstructed/pre-feature record with no `tldr`, `takeaways`, or `tags`; loser has stale values for those fields. `completeTuple` includes `wv.tldr`, `wv.takeaways`, and `wv.tags`, but when those are `undefined` they are effectively omitted from the durable write. Supabase receives no key in JSON; local writes drop `undefined` on JSON serialization. The loser keeps stale companion scalars even though the spec requires carrying the winning Class-A companion scalars verbatim with the MD.

Fix: add an explicit clear mechanism for absent companion scalar keys on `updateVideoFields`/`merge_video_data`, or normalize the data model to a valid persisted clear value and make readers tolerate it.

Targeted tests run: `npm test -- --runTestsByPath tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/local-stamping.test.ts tests/integration/cloud-sync/stamping.int.test.ts tests/integration/cloud-sync/e2e.int.test.ts --runInBand`. Jest only executed the two non-integration suites under the default config; they passed.

NOT CONVERGED.
tokens used
70,737
**Part A**

WB-B1: GENUINELY FIXED. The guard is before Class-A signal derivation, transfer, companion transfer, normal archived counter, and normal baseline advance in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:471). It still logs Class-B conflicts before the guard, increments `needsRegen`, increments `archivedNotSynced` only for archived divergence, writes a baseline so delete inference has seen the video, then continues. `reconcileClassA` takes only live `ClassASignals`, not manifest Class-A baselines, so the `{ docVersionMajor: 0, mdHash: null }` placeholder is not read by the Class-A decision code.

WB-H1: INCOMPLETE. The promoted-without-blob advertisement is fixed for the first failing run: unreadable `summaryMd` throws before `upsertVideo`, and the post-write promoted artifact assertion is valid for both local replacement and Supabase direct row update. However, the throw happens after `ensureReceiverSlot`, leaving a bare receiver row that changes the next run’s branch classification. Finding below.

WB-H2: GENUINELY FIXED. `transferClassA` writes `summaryHtml`, `digDeeperHtml`, and `digDeeperMd` as JSON/null fields in [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:314). Supabase `merge_video_data` preserves those nulls via `data || (p_fields - 'artifacts')` in [0021_cloud_sync_signals.sql](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/supabase/migrations/0021_cloud_sync_signals.sql:79); local shallow merge also persists nulls through `updateVideoFields`. The null list matches `sanitizeAdditiveVideo`’s regenerable top-level cache fields, and clearing `digDeeperMd` is consistent with M2a not syncing dig/deep-dive assets.

**Findings**

High: partial additive failure creates a receiver slot, then a later run can falsely baseline a video whose source MD blob is still missing.  
File: [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:150)

Scenario: cloud-only video advertises `summaryMd`, but the MD blob is absent. Run 1 calls `ensureReceiverSlot` before the unreadable-body check, creating a bare local row, then throws at line 159 and does not write a baseline. Run 2 now sees both sides present, not an additive create. Since both MD body reads are null, `reconcileClassA` returns `skip`; `runSync` writes a manifest baseline at line 512 even though no receiver summary was ever durably copied and the source still advertises an unreadable summary. This masks the original corruption after one report and turns a failed additive copy into a false “seen/agreed no-MD” state.

Fix: validate `video.summaryMd`/`mdBody` before `ensureReceiverSlot`, or wrap `copyAdditiveVideo` in rollback that deletes the claimed receiver slot and any staged/final blob if any later step fails. The baseline should not be able to advance from a bare receiver slot created by a failed additive copy.

Medium: Class-A transfer does not clear absent companion scalars, so stale loser metadata can survive beside the winner MD.  
File: [sync-run.ts](/Users/kujinlee/code/agentic-ai-docs/youtube-playlist-summaries-cloud/lib/cloud-sync/sync-run.ts:301)

Scenario: winner MD comes from a reconstructed/pre-feature record with no `tldr`, `takeaways`, or `tags`; loser has stale values for those fields. `completeTuple` includes `wv.tldr`, `wv.takeaways`, and `wv.tags`, but when those are `undefined` they are effectively omitted from the durable write. Supabase receives no key in JSON; local writes drop `undefined` on JSON serialization. The loser keeps stale companion scalars even though the spec requires carrying the winning Class-A companion scalars verbatim with the MD.

Fix: add an explicit clear mechanism for absent companion scalar keys on `updateVideoFields`/`merge_video_data`, or normalize the data model to a valid persisted clear value and make readers tolerate it.

Targeted tests run: `npm test -- --runTestsByPath tests/lib/cloud-sync/reconcile-class-a.test.ts tests/lib/cloud-sync/local-stamping.test.ts tests/integration/cloud-sync/stamping.int.test.ts tests/integration/cloud-sync/e2e.int.test.ts --runInBand`. Jest only executed the two non-integration suites under the default config; they passed.

NOT CONVERGED.
