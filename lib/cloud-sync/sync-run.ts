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
  // WB-H1 — a video advertising a summaryMd whose blob body is unreadable (null: storage drift /
  // corruption / RLS miss) is an anomaly. THROW (per-video, caught by the caller) so the baseline is
  // NOT advanced — a re-run heals once the body is readable. Advertising promoted with no blob would
  // strand the receiver with a servable-looking row backed by nothing.
  // H-R2-1 (round 2) — this guard MUST run BEFORE ensureReceiverSlot, not after. Claiming the slot
  // first left a BARE receiver row behind on the throw; the next run then saw a TWO-SIDED video whose
  // sides both derive mdHash === null (bare row has no body, source body still unreadable), so
  // reconcileClassA returned 'skip' (!lHas && !cHas) and runSync wrote a manifest baseline —
  // laundering the corruption into a false "seen and agreed no-MD" state. Validating first means no
  // partial state is ever created, so there is nothing to roll back.
  if (video.summaryMd && mdBody == null) {
    throw new Error(`additive: summaryMd present but MD body unreadable for ${video.id}`);
  }

  const slot = await ensureReceiverSlot(to, toP, playlistMeta, video);

  let wroteBlob = false;
  if (video.summaryMd && mdBody != null) {
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
    // readIndex reads falsy → forces re-render.
    //
    // H-R2-2 (round 2) — ONLY the two HTML caches are cleared here. Do NOT add `digDeeperMd: null`
    // back: digDeeperMd is not a render cache, it is the filename pointer to a PAID Gemini-generated
    // dig-deeper markdown file (lib/dig/generate.ts, written by lib/dig/dig-section.ts). Nulling it
    // orphans that file and darkens the dig-state route, VideoMenu, build-doc-html and pdf-path;
    // recovery costs fresh Gemini spend for content already paid for (and dig is out of scope for
    // M2a). digDeeperHtml re-renders for free FROM the preserved digDeeperMd.
    // The round-1 premise "matches sanitizeAdditiveVideo, which already nulls these" was the flaw:
    // sanitizeAdditiveVideo shapes a record for a receiver with NO existing row (nothing to destroy),
    // whereas transferClassA PATCHES a row that already holds its own state.
    summaryHtml: null,
    digDeeperHtml: null,
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
        //
        //    Class-A signals are derived HERE (before the guard) because the guard needs them; the
        //    derivation is PURE (it only reads the record + the MD body), so hoisting it changes no
        //    behavior. Bodies are needed for hashing regardless — Behavior #1.
        const la = deriveClassASignals(lv, await readMdBody(deps.localBlob, localP, lv));
        const ca = deriveClassASignals(cv, await readMdBody(deps.cloudBlob, cloudP, cv));

        //    M-R2-2 — the skip is narrowed to the genuinely DESTRUCTIVE case: BOTH sides actually hold
        //    an MD body. When one side has none, the Class-A copy is purely ADDITIVE hydration —
        //    nothing can be destroyed and no false agreement about competing bodies is possible — so
        //    skipping would strand the video with no MD forever (safe-but-stuck until a human edits
        //    corrections). The corrections conflict is still logged by Class B and still flags
        //    needsRegen via reconcileClassA (the hydrated MD is corrections-stale).
        const correctionsUnresolved = merges.corrections.winner === 'equal' && merges.corrections.conflict;
        if (correctionsUnresolved && la.mdHash != null && ca.mdHash != null) {
          report.needsRegen += 1;
          if (lv.archived !== cv.archived) report.archivedNotSynced += 1; // R10 — do NOT sync archived
          await writeVideoBaseline(dataRoot, key, id, buildCorrectionsUnresolvedBaseline(merges, base));
          continue;
        }

        // ── Class A (la/ca derived above the WB-B1 guard, which needs them — Behavior #1).
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
