import type { Video } from '@/types';
import type { ClassASignals, HumanSnapshot, HumanField, FieldState } from './types';
import { mdHash } from './content-hash';

// mdBody is the MD BODY the caller read from the blob store (BlobStore.get(p, video.summaryMd)).
// NEVER hash video.summaryMd — it is a blob key/filename, not content (§5.2, Blocking ①).
export function deriveClassASignals(video: Video, mdBody: string | null): ClassASignals {
  const hasReal = video.mdGeneratedAt != null;
  return {
    summaryMdKey: video.summaryMd ?? null,
    mdHash: mdBody != null ? mdHash(mdBody) : null,
    docVersionMajor: video.docVersion?.major ?? 1,
    mdGeneratedAt: video.mdGeneratedAt ?? video.processedAt ?? null,
    mdCorrectionsHash: video.mdCorrectionsHash ?? null,
    backfilled: !hasReal,
  };
}

const FIELDS: HumanField[] = ['personalNote', 'personalScore', 'corrections'];

export function deriveHumanSnapshot(video: Video): HumanSnapshot {
  const provisional = video.updatedAt ?? video.processedAt;
  const out = {} as HumanSnapshot;
  for (const f of FIELDS) {
    const value = video[f] as string | number | undefined;
    const real = video.annotationsEditedAt?.[f];
    const state: FieldState<string | number> = value === undefined && real === undefined
      ? { value: undefined, editedAt: undefined, backfilled: false }
      : { value, editedAt: real ?? provisional, backfilled: real === undefined };
    out[f] = state;
  }
  return out;
}
