import type { BlobStore } from '@/lib/storage/blob-store';
import type { MetadataStore } from '@/lib/storage/metadata-store';
import type { Principal } from '@/lib/storage/principal';

export type ArtifactKind = 'summaryMd' | 'slide' | 'html' | 'pdf' | 'modelJson';

const SOURCE_KINDS: ArtifactKind[] = ['summaryMd', 'slide', 'modelJson'];

export const isSourceKind = (k: ArtifactKind): boolean => SOURCE_KINDS.includes(k);

/**
 * Ordered write: ensures blob and metadata stay consistent by using a
 * staging area with an explicit verification step before promoting.
 *
 * Sequence: putStaged → verify temp exists → updateVideoFields(committed) → promote → updateVideoFields(promoted)
 */
export async function writeArtifact(opts: {
  meta: MetadataStore;
  blob: BlobStore;
  principal: Principal;
  videoId: string;
  kind: ArtifactKind;
  key: string;
  bytes: Buffer;
  contentType: string;
}): Promise<void> {
  const ref = await opts.blob.putStaged(opts.principal, opts.key, opts.bytes, opts.contentType);

  if (!(await opts.blob.exists(opts.principal, ref.tempKey))) {
    throw new Error('staged upload not verified');
  }

  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'committed' } },
  } as any);

  await opts.blob.promote(ref);

  await opts.meta.updateVideoFields(opts.principal, opts.videoId, {
    artifacts: { [opts.kind]: { key: opts.key, status: 'promoted' } },
  } as any);
}

/**
 * Read-time classification of a missing blob.
 * Source kinds (summaryMd, slide, modelJson) require manual repair — they cannot
 * be regenerated. Cache kinds (html, pdf) can be regenerated on demand.
 */
export async function resolveMissing(opts: {
  kind: ArtifactKind;
  regenerate: () => Promise<void>;
  markRepair: () => Promise<void>;
}): Promise<'regenerated' | 'repair_needed'> {
  if (isSourceKind(opts.kind)) {
    await opts.markRepair();
    return 'repair_needed';
  }
  await opts.regenerate();
  return 'regenerated';
}
