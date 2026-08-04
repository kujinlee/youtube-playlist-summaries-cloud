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
import { assertLogicalKey } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';
import type { Video } from '@/types';
import path from 'path';
import { applySerial } from '@/lib/serial-filename';
import { MODEL_KEY } from '@/lib/html-doc/model-store';

export interface CloudReplica {
  store: MetadataStore;
  p: Principal;
  blob: BlobStore;
}

/** Backlog #17 guard — "is a job that will write this video's blobs still pending?"
 *
 *  A summary job pins `baseName` from the serial it reserved (`summary-handler.ts:95-96`) and then
 *  spends MINUTES in transcript + Gemini before persisting (`:156`). `dig-handler.ts:51-57` pins
 *  `base` the same way. A relocation inside that window is silently undone by the stale persist,
 *  which wins on the key — `persist_summary` resolves it as
 *  `coalesce(p_video->>'summaryMd', v.data->>'summaryMd')` (0021:135) while `serialNumber` is
 *  restored from the row. The row then advertises `007_alpha.md` beside serial 3, and the paid digs
 *  copied to `dig/003_alpha/` are unreachable because cleanup already removed `dig/007_alpha/*`.
 *
 *  **A union, not a boolean.** "No job is pending" and "the job table could not be read" are
 *  different facts, and collapsing them is the exact shape that produced 1 Blocking + 3 Highs in
 *  Stage 3: a value meaning ABSENT is also what a FAILURE produces. An unreadable probe must refuse,
 *  never proceed.
 *
 *  **Not a lease fence.** The worker's lease stays valid throughout and this function never touches
 *  the job; what goes stale is the SERIAL. Fencing on `lease_token` would not detect this at all. */
export type InFlightJobProbe = (playlistKey: string, videoId: string) => Promise<
  | { ok: true; inFlight: boolean }
  | { ok: false; cause: unknown }
>;

/** The honest outcome of a reconciliation. Granular for the same reason `CopyResult` is: the caller
 *  must be able to tell "nothing to do" from "refused" from "tried and failed", and a refusal must
 *  name what it collided with so the report tells the user something actionable. */
export type SerialReconcileResult =
  | { ok: true; action: 'agreed' }
  | { ok: true; action: 'relocated'; from: string; to: string; copied: number; cleanupFailures: number }
  | { ok: false; reason: 'target-occupied'; want: number; heldBy: string }
  | { ok: false; reason: 'job-in-flight'; videoId: string }
  | { ok: false; reason: 'job-probe-unreadable'; cause: unknown }
  | { ok: false; reason: 'copy-failed'; key: string; detail: CopyResult }
  | { ok: false; reason: 'unmappable-key'; key: string }
  | { ok: false; reason: 'ambiguous-mapping'; to: string }
  | { ok: false; reason: 'unsupported-artifacts'; kinds: string[] }
  | { ok: false; reason: 'metadata-failed'; cause: unknown }
  | { ok: false; reason: 'metadata-unverified'; found: string | null }
  | { ok: false; reason: 'verification-unreadable'; cause: unknown };

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
  // `digDeeperMd`, matched on the BASENAME and never by prefix.
  //
  //  - Not by prefix: with `oldBase = '003_a'`, `startsWith` also matches `003_ab-dig-deeper.md`,
  //    which is a DIFFERENT video's artifact, and would rewrite it to a path pointing at nothing
  //    while cleanup deleted the real file. One base being a prefix of another is ordinary — slugs
  //    are free text.
  //  - But not on the whole key either: `dig-section.ts:83` builds the name from
  //    `path.basename(summaryMdName)`, so a video whose `summaryMd` is `raw/275_x.md` gets a BARE
  //    `275_x-dig-deeper.md`. Comparing whole keys refuses that pair and strands the video where the
  //    old code could move it. The `raw/` layout is real and supported (tests/lib/pdf/pdf-path.test.ts,
  //    and buildDocHtml derives `relDir` from exactly these fields).
  // (Codex round-3 re-review, Medium #1.)
  if (path.posix.basename(key) === `${path.posix.basename(oldBase)}-dig-deeper.md`) {
    const dir = path.posix.dirname(key);
    const moved = `${path.posix.basename(newBase)}-dig-deeper.md`;
    return dir === '.' ? moved : `${dir}/${moved}`;
  }
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
  /** Backlog #17. REQUIRED, deliberately: an optional probe does not propagate, and every caller
   *  that forgot it would silently inherit the unguarded behaviour. */
  inFlightJob: InFlightJobProbe;
}): Promise<SerialReconcileResult> {
  const { cloud, cloudIndex, localVideo, cloudVideo, inFlightJob } = args;

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

  // ── Backlog #17 — REFUSE while a job that will write this video is still pending.
  //
  // Placed here deliberately: after every in-memory refusal above (which cost nothing and would
  // refuse anyway) and BEFORE the copy phase, so a refusal never leaves a half-moved base. It is
  // also after the two early returns, so the overwhelmingly common case — a video whose replicas
  // already agree — never pays for this round-trip at all.
  //
  // Refusing is the whole mitigation. The window it closes is the MINUTES a job spends in Gemini
  // holding a `base` it computed before this run started; nothing here can shorten that window, so
  // the only safe move is to leave the video diverged and repair it on a later run when the job has
  // landed. That is already a supported outcome — the caller surfaces it per video and advances no
  // baseline, so the next sync re-evaluates from scratch.
  //
  // WHAT THIS DOES NOT CLOSE, measured rather than assumed. The residual window is NOT
  // "milliseconds": the copy phase below is a loop of N sequential blob round-trips (MD + model +
  // one per dig), and the metadata write happens only after all of them. A job enqueued and claimed
  // inside that span still reads the pre-relocation serial. So the guard shrinks the exposure from
  // "the whole minutes-long Gemini run of an already-active job" to "the duration of this
  // relocation's copy phase" — a large reduction, not an elimination.
  // Closing it properly needs a compare-and-swap on the serial in `persist_summary` — backlog #17's
  // durable fix, deliberately out of scope here.
  let probe: Awaited<ReturnType<InFlightJobProbe>>;
  try {
    // Scoped to THIS playlist: `base` is per-playlist (the serial is allocated per playlist), so a
    // job for the same video under a different playlist writes a different address and cannot
    // collide with this relocation.
    probe = await inFlightJob(cloud.p.indexKey, cloudVideo.id);
  } catch (cause) {
    // A throwing probe is the same situation as one reporting failure, and must NOT escape: an
    // exception here would abort the entire sync run instead of this one video.
    return { ok: false, reason: 'job-probe-unreadable', cause };
  }
  if (!probe.ok) return { ok: false, reason: 'job-probe-unreadable', cause: probe.cause };
  if (probe.inFlight) return { ok: false, reason: 'job-in-flight', videoId: cloudVideo.id };

  // ── Copy phase. Sources are retained throughout, so every failure here is recoverable by re-running.
  const sources = await paidKeysUnder(cloud.blob, cloud.p, cloudVideo, oldBase);

  // PLAN THE WHOLE RELOCATION BEFORE COPYING ANYTHING. Validating inside the copy loop meant a key
  // that only fails on inspection — a `..` traversal that `assertLogicalKey` rejects, or two sources
  // landing on ONE destination — was discovered after earlier blobs had already been written, leaving
  // duplicates at the new base that every re-run recreated. Deciding up front keeps the refusal a
  // genuine no-move. (Codex round-4 re-review, Medium #1 + Medium #2.)
  const plan: { from: string; to: string }[] = [];
  const destinations = new Set<string>();
  for (const from of sources) {
    const to = remap(from, oldBase, newBase);
    if (to == null) return { ok: false, reason: 'unmappable-key', key: from };
    try {
      assertLogicalKey(from);
      assertLogicalKey(to);
    } catch {
      return { ok: false, reason: 'unmappable-key', key: from };
    }
    // Two distinct sources mapping to one destination is unresolvable here: whichever is copied
    // second sees `destination-exists` on bytes the FIRST one just wrote, and the relocation cannot
    // be resumed without a human deciding which is which.
    if (destinations.has(to)) return { ok: false, reason: 'ambiguous-mapping', to };
    destinations.add(to);
    plan.push({ from, to });
  }

  let copied = 0;
  for (const { from, to } of plan) {
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

  // NARROW THE WINDOW before writing. The copy phase above is long (N blob round-trips), and the
  // record in hand was read before it. Re-reading immediately before the write shrinks the race with
  // a concurrent sync of the same playlist from the whole copy phase to the gap between these two
  // statements. It is NOT a compare-and-swap — see `metadata-unverified` below and the round-3
  // adjudication for what remains and why it is not unique to this function.
  try {
    const fresh = (await cloud.store.readIndex(cloud.p)).videos.find((v) => v.id === cloudVideo.id);
    if (fresh?.summaryMd !== cloudVideo.summaryMd) {
      return { ok: false, reason: 'metadata-unverified', found: fresh?.summaryMd ?? null };
    }
  } catch (cause) {
    return { ok: false, reason: 'metadata-failed', cause };
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
  //   The verification READ can itself fail, and that is a different situation from a failed write:
  // the row may well have moved, so the old-base blobs may already be unreferenced. Returning a
  // typed `verification-unreadable` rather than throwing lets the caller distinguish "nothing
  // happened" from "something happened and we cannot see what" — the absent-vs-unreadable rule
  // applied to metadata instead of blobs. Cleanup is skipped either way; a later run re-reads and
  // finishes it. (Codex round-3 re-review, Low #1.)
  let after;
  try {
    after = (await cloud.store.readIndex(cloud.p)).videos.find((v) => v.id === cloudVideo.id);
  } catch (cause) {
    return { ok: false, reason: 'verification-unreadable', cause };
  }
  if (after?.summaryMd !== `${newBase}.md`) {
    return { ok: false, reason: 'metadata-unverified', found: after?.summaryMd ?? null };
  }

  // ── Cleanup phase. Best-effort by definition: every blob now exists at the new base AND the row
  // points there, so a failure leaves leftovers, not loss. It must never undo durable work.
  let cleanupFailures = 0;
  for (const { from, to } of plan) {
    if (to === from) continue;
    try { await cloud.blob.delete(cloud.p, from); } catch { cleanupFailures += 1; }
  }

  return { ok: true, action: 'relocated', from: oldBase, to: newBase, copied, cleanupFailures };
}
