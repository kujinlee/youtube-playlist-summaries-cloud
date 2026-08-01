// lib/cloud-sync/reconcile-serial.ts
//
// A3 of the serial-coherence slice — repair a two-sided video whose replicas derive DIFFERENT
// `base` values, before any Class-A transfer touches it.
//
// WHY THIS EXISTS. `base` = `<serial>_<slug>` is the address of every derived blob:
// `models/<base>.json`, `dig/<base>/<sectionId>.r<V>.md`, and the summary MD itself. `transferClassA`
// writes the WINNER's `summaryMd` key onto the loser and never touches the loser's `serialNumber`,
// so a diverged video has its row re-pointed at the winner's base while its own dig and model blobs
// — real Gemini spend — are left behind unreferenced. A1 stops new divergence from being created;
// this repairs the divergence that every earlier sync already wrote.
//
// BASE, NOT ONLY SERIAL. The plan named the serial, but the serial is only the first half of the
// address. The slug can diverge on its own (the video's title changed between the two ingests, or
// one side took a `-2` collision suffix). Reconciling to local's full base costs the same code and
// makes the `transferClassA` key-write that follows a no-op instead of a second orphaning event.
//
// LOCAL IS AUTHORITATIVE; only the cloud replica is mutated. Local filenames live in the user's
// Obsidian vault, where a rename breaks hand-made wiki-links and bookmarks that nothing can repair;
// cloud blob keys are invisible. That asymmetry is why this takes the local VIDEO but no local
// replica — it has nothing to write there.
//
// ORDERING (behaviors row 26): copy every blob (sources RETAINED) -> the copies are verified by
// `copyBlob` -> advance the metadata -> delete the old base best-effort. Any failure before the
// metadata write leaves the old blobs intact and still serving the current row; any failure after it
// is leftovers, not loss. This is why the seam grew `copy` in A4 rather than a destructive rename:
// Supabase `move()` is copy+delete and non-atomic, and no rename is atomic across N objects.

import type { BlobStore, CopyResult } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { Video } from '@/types';
import { applySerial } from '@/lib/serial-filename';
import { MODEL_KEY } from '@/lib/html-doc/model-store';

export interface CloudReplica {
  store: MetadataStore;
  p: Principal;
  blob: BlobStore;
}

/** The honest outcome of a reconciliation. Granular for the same reason `CopyResult` is: the caller
 *  must be able to tell "nothing to do" from "refused" from "tried and failed", and a refusal must
 *  name what it collided with so the report tells the user something actionable. */
export type SerialReconcileResult =
  | { ok: true; action: 'agreed' }
  | { ok: true; action: 'relocated'; from: string; to: string; copied: number; cleanupFailures: number }
  | { ok: false; reason: 'target-occupied'; want: number; heldBy: string }
  | { ok: false; reason: 'copy-failed'; key: string; detail: CopyResult }
  | { ok: false; reason: 'unmappable-key'; key: string }
  | { ok: false; reason: 'unsupported-artifacts'; kinds: string[] }
  | { ok: false; reason: 'metadata-failed'; cause: unknown }
  | { ok: false; reason: 'metadata-unverified'; found: string | null };

/** `<base>` from a `<base>.md` key. */
function baseOf(summaryMd: string): string {
  return summaryMd.replace(/\.md$/, '');
}

/** Every blob key that is addressed by `base` AND is irreplaceable.
 *
 *  Deliberately excludes the render caches (`summaryHtml`, `digDeeperHtml`, `pdfs/<base>…`): those
 *  are deterministic re-renders costing no Gemini spend, and their pointers are nulled below so the
 *  serve path rebuilds them at the new base. Copying them would double the work for no protection.
 *  `digDeeperMd` IS included — it is not a render cache but a paid dig-deeper markdown artifact
 *  (lib/dig/generate.ts), and nulling it orphans content the user already paid for (H-R2-2). */
async function paidKeysUnder(
  blob: BlobStore, p: Principal, video: Video, base: string,
): Promise<string[]> {
  const keys = [`${base}.md`, MODEL_KEY(base)];
  const digDeeperMd = (video as { digDeeperMd?: string | null }).digDeeperMd;
  if (digDeeperMd) keys.push(digDeeperMd);
  // Digs are enumerated, not guessed: the section ids and the `.r<V>` suffix are not derivable here.
  keys.push(...await blob.list(p, `dig/${base}/`));
  return [...new Set(keys)];
}

/** Map an old-base key to the same key under the new base, or `null` if the key is not a shape this
 *  module knows how to move.
 *
 *  FAILS CLOSED on an unrecognised shape rather than guessing. The first version ended in a generic
 *  `key.replace(oldBase, newBase)`, which rewrites only the FIRST occurrence wherever it happens to
 *  sit: a key like `x/<oldBase>/<oldBase>-dig-deeper.md` would have its directory rewritten and its
 *  basename left carrying the old base, producing a row that points at a file that does not exist
 *  while cleanup deletes the one that does. Every shape below is enumerated deliberately; a new
 *  base-addressed artifact must be added here, and until it is, the reconciliation refuses to move
 *  the record at all. (Codex branch review, Medium #1.) */
function remap(key: string, oldBase: string, newBase: string): string | null {
  if (key === `${oldBase}.md`) return `${newBase}.md`;
  if (key === MODEL_KEY(oldBase)) return MODEL_KEY(newBase);
  const digPrefix = `dig/${oldBase}/`;
  if (key.startsWith(digPrefix)) return `dig/${newBase}/${key.slice(digPrefix.length)}`;
  // `digDeeperMd`, matched EXACTLY rather than by prefix. A `startsWith(oldBase)` test looks
  // equivalent and is not: with `oldBase = '003_a'` it also matches `003_ab-dig-deeper.md`, which is
  // a DIFFERENT video's artifact (or this one's stale pointer from an earlier base), and would
  // rewrite it into `003_newb-dig-deeper.md` — a path pointing at nothing, while cleanup deletes the
  // real file. One base being a prefix of another is ordinary: slugs are free text.
  if (key === `${oldBase}-dig-deeper.md`) return `${newBase}-dig-deeper.md`;
  return null;
}

/** The bases the two replicas derive for one video, and whether they disagree.
 *
 *  Split out because the corrections-unresolved path (behaviors row 21c) must REPORT a divergence it
 *  deliberately does not repair. That path performs no transfer, so nothing is orphaned by waiting —
 *  but staying silent would hide a data-loss condition behind an unrelated conflict, which is the
 *  one thing that makes it unsafe. */
export function describeDivergence(
  localVideo: Video, cloudVideo: Video,
): { diverged: boolean; from?: string; to?: string } {
  if (localVideo.serialNumber == null || !cloudVideo.summaryMd) return { diverged: false };
  const from = baseOf(cloudVideo.summaryMd);
  const to = localVideo.summaryMd
    ? baseOf(localVideo.summaryMd)
    : baseOf(applySerial(cloudVideo.summaryMd, localVideo.serialNumber));
  return from === to ? { diverged: false } : { diverged: true, from, to };
}

/**
 * Bring the cloud replica's `base` for one video into agreement with local's, or refuse.
 *
 * `cloudIndex` is the caller's already-read cloud index — passed in rather than re-read so a whole
 * playlist's reconciliation sees ONE consistent snapshot. That is what makes a swap
 * (`A: local=3,cloud=7` and `B: local=7,cloud=3`) abort on both halves instead of letting the first
 * one move and the second see a world the first just changed.
 */
export async function reconcileCloudBase(args: {
  cloud: CloudReplica;
  cloudIndex: Video[];
  localVideo: Video;
  cloudVideo: Video;
}): Promise<SerialReconcileResult> {
  const { cloud, cloudIndex, localVideo, cloudVideo } = args;

  // Nothing to reconcile TO. A legacy row with no serial, or a cloud row with no MD, has no base to
  // move and no authority to move toward — leave it for the Class-A transfer, which is additive.
  if (localVideo.serialNumber == null || !cloudVideo.summaryMd) return { ok: true, action: 'agreed' };

  // Prefer local's ACTUAL base (serial and slug); fall back to renumbering cloud's own slug when
  // local advertises no MD of its own.
  const d = describeDivergence(localVideo, cloudVideo);
  if (!d.diverged) return { ok: true, action: 'agreed' };
  const oldBase = d.from!;
  const newBase = d.to!;

  // Row 21 — refuse if any OTHER cloud video holds the target serial or the target base. Renumbering
  // that video instead would just move the divergence; renumbering local is forbidden. Aborting is
  // not merely the cautious option: it stops transferClassA writing the winner's key onto this row,
  // which is the write that does the orphaning. The video stays visibly diverged on every run
  // instead of silently losing its dig content once.
  const holder = cloudIndex.find((v) =>
    v.id !== cloudVideo.id &&
    (v.serialNumber === localVideo.serialNumber ||
      (v.summaryMd != null && baseOf(v.summaryMd) === newBase)));
  if (holder) {
    return { ok: false, reason: 'target-occupied', want: localVideo.serialNumber, heldBy: holder.id };
  }

  // REFUSE if the record carries any artifact kind other than `summaryMd`. The cloud artifact write
  // is an additive jsonb merge (merge_video_data, 0007:89-93), so a subkey this patch omits keeps its
  // old-base value while cleanup deletes the blob underneath it — and remapping the POINTER without
  // also copying the BLOB is no better, since `paidKeysUnder` only knows the MD, the model, the digs
  // and digDeeperMd. Refusing is the smallest correct behaviour: it cannot half-move anything, and
  // the day this becomes reachable it fails loudly at exactly the code that must be extended.
  //   It is unreachable today, in both directions: `writeArtifact` is the only writer of the other
  // kinds and has zero production callers (architecture finding #2), and every sync write shapes
  // artifacts down to `{ summaryMd }` (sanitizeAdditiveVideo, transferClassA).
  // (Codex branch review High #1 — severity adjudicated down after verifying the writers, and the
  // suggested pointer-remap replaced with a refusal for the reason above.)
  const artifacts = (cloudVideo as { artifacts?: Record<string, unknown> }).artifacts;
  const unsupported = Object.keys(artifacts ?? {}).filter((k) => k !== 'summaryMd');
  if (unsupported.length > 0) {
    return { ok: false, reason: 'unsupported-artifacts', kinds: unsupported };
  }

  // ── Copy phase. Sources are retained throughout, so every failure here is recoverable by re-running.
  const sources = await paidKeysUnder(cloud.blob, cloud.p, cloudVideo, oldBase);
  let copied = 0;
  for (const from of sources) {
    const to = remap(from, oldBase, newBase);
    if (to == null) {
      return { ok: false, reason: 'unmappable-key', key: from };
    }
    const res = await cloud.blob.copy(cloud.p, from, to);
    if (res.ok) { if (!res.already) copied += 1; continue; }
    // A derived artifact that genuinely does not exist is nothing to copy — most videos have no
    // model and no digs. The advertised MD is different: advancing the row without it would publish
    // a servable-looking record backed by nothing. `source-absent` is a PROOF of absence;
    // `source-unreadable` is not, and must never be treated as one.
    if (res.reason === 'source-absent' && from !== `${oldBase}.md`) continue;
    return { ok: false, reason: 'copy-failed', key: to, detail: res };
  }

  // ── Metadata phase. Only now does anything become visible at the new base.
  const patch: Record<string, unknown> = {
    serialNumber: localVideo.serialNumber,
    summaryMd: `${newBase}.md`,
    artifacts: { summaryMd: { key: `${newBase}.md`, status: 'promoted' } },
    // Render caches are keyed on the OLD base, so their pointers are now wrong. Nulling forces a
    // free re-render at the new base; remapping them would mean copying bytes we can regenerate.
    summaryHtml: null,
    digDeeperHtml: null,
  };
  const digDeeperMd = (cloudVideo as { digDeeperMd?: string | null }).digDeeperMd;
  if (digDeeperMd) {
    const to = remap(digDeeperMd, oldBase, newBase);
    if (to == null) return { ok: false, reason: 'unmappable-key', key: digDeeperMd };
    patch.digDeeperMd = to;
  }

  try {
    await cloud.store.updateVideoFields(cloud.p, cloudVideo.id, patch as Partial<Video>);
  } catch (cause) {
    // The copies are durable and harmless — the row still points at the old base, which is still
    // intact. A re-run resumes via the identical-bytes path rather than deadlocking.
    return { ok: false, reason: 'metadata-failed', cause };
  }

  // VERIFY THE WRITE LANDED before deleting anything. The cloud `updateVideoFields` is
  // `merge_video_data` (0021:79), a bare `UPDATE ... WHERE playlist_id = .. AND video_id = ..`
  // returning void: zero rows affected raises NOTHING and the adapter only inspects `error`. So a
  // row deleted or replaced by another client between the read and this write leaves the metadata
  // untouched — and the cleanup below would then delete paid blobs the surviving row still points
  // at. This is the same silent-zero-row hazard already documented for additive creates
  // (sync-run.ts, round-4 H1); the fix is the same shape: read it back and prove it.
  // (Codex round-2 re-review, High #1.)
  const after = (await cloud.store.readIndex(cloud.p)).videos.find((v) => v.id === cloudVideo.id);
  if (after?.summaryMd !== `${newBase}.md`) {
    return { ok: false, reason: 'metadata-unverified', found: after?.summaryMd ?? null };
  }

  // ── Cleanup phase. Best-effort by definition: every blob now exists at the new base AND the row
  // points there, so a failure leaves leftovers, not loss. It must never undo durable work.
  let cleanupFailures = 0;
  for (const from of sources) {
    const to = remap(from, oldBase, newBase);
    if (to == null || to === from) continue;   // null is unreachable — the copy loop already refused
    try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
  }

  return { ok: true, action: 'relocated', from: oldBase, to: newBase, copied, cleanupFailures };
}
